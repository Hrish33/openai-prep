"""Memory Allocator (LC 2502).

Implement an allocator over a fixed pool of `n` bytes. See ``problem.md``
for the API contract, return-value rules, and edge cases. Lead with the
O(n) interval-list version; once tests pass, refactor to a SortedDict-
based representation for O(log n) on the free path.

Suggested data structures (pick whichever you want to lead with — do NOT
treat these as prescriptive):

    # Baseline:
    #   self.free  : list[tuple[start, size]]  sorted by start, coalesced
    #   self.alloc : dict[mID, list[tuple[start, size]]]

    # Optimized:
    #   from sortedcontainers import SortedDict
    #   self.free  : SortedDict  # start -> size, coalesced
    #   self.alloc : dict[mID, list[tuple[start, size]]]

The merge logic in ``free`` has four cases — none / left / right / both.
Draw them before you write code.
"""

from typing import Dict, List, Tuple

from sortedcontainers import SortedDict


#
#
# class Allocator:
#     def __init__(self, n: int) -> None:
#         self.free = [(0, n)]
#         #mID : [startIndex, size]
#         self.alloc = {}
#
#     def allocate(self, size: int, mID: int) -> int:
#         """Reserve `size` contiguous bytes for `mID`, leftmost-first.
#
#         Returns the starting address, or -1 if no contiguous free block of
#         `size` bytes exists. Multiple allocations may share the same mID.
#         """
#         #look for first free block, and allocate
#         for i, (start, gap) in enumerate(self.free):
#             if gap >= size :
#                 if gap == size :
#                     self.free.pop(i)
#                 else :
#                     self.free[i] = (start + size, gap - size)
#
#                 self.alloc.setdefault(mID, []).append((start, size))
#                 return start
#         return -1
#
#
#
#     def freeMemory(self, mID: int) -> int:
#         """Free every block currently allocated under `mID`, coalescing.
#
#         Returns the total bywow this tes freed (0 if mID is unknown).
#         """
#
#         if mID not in self.alloc:
#             return 0
#         total_size = 0
#
#         for start, block in self.alloc[mID] :
#             total_size += block
#
#         self.free.extend(self.alloc[mID])
#         self.free.sort()
#
#         del self.alloc[mID]
#
#         merged = []
#         for start, size in self.free:
#             if merged and merged[-1][0] + merged[-1][1] == start:
#                 merged[-1] = (merged[-1][0], merged[-1][1] + size)
#             else:
#                 merged.append((start, size))
#         self.free = merged
#
#         return total_size
#



from sortedcontainers import SortedDict

class Allocator:
    def __init__(self, n: int) -> None:
        self.n = n
        #invariats is contigous only
        self.free : SortedDict = SortedDict({0:n})
        #mID : [startIndex, size]
        self.alloc = {}

    def allocate(self, size: int, mID: int) -> int:
        """Reserve `size` contiguous bytes for `mID`, leftmost-first.

        Returns the starting address, or -1 if no contiguous free block of
        `size` bytes exists. Multiple allocations may share the same mID.
        """
        #look for first free block, and allocate
        for start, gap in self.free.items():
            if gap >= size :
                del self.free[start]
                if gap > size:
                    self.free[start+size] = gap - size
                self.alloc.setdefault(mID, []).append((start, size))
                return start
        return -1



    def freeMemory(self, mID: int) -> int:
        """Free every block currently allocated under `mID`, coalescing.

        Returns the total bytes freed (0 if mID is unknown).
        """

        if mID not in self.alloc:
            return 0
        blocks = self.alloc.pop(mID)
        total_size = 0
        for start, block in blocks:
            total_size += block
            self.insert_free_block(start, block)
        return total_size

    def insert_free_block(self, start : int, size : int):
        end = start+size
        keys = self.free.keys()

        #see where I should insert this.

        # RIGHT: is there a free block starting at `end`?
        if end in self.free:
            size += self.free.pop(end)

        # largest free key < start
        li = self.free.bisect_right(start) - 1
        if li >= 0:
            left_start, left_size = keys[li], self.free[keys[li]]
            if left_start + left_size == start:
                size += left_size
                start = left_start
                del self.free[left_start]

        self.free[start] = size
