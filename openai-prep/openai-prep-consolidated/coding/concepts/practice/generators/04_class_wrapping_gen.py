"""
The hybrid pattern — class shell + generator body — applied to Problem 4.

GOAL: Re-implement CompositeIterator using a generator for the iteration
body, while keeping the class shell to expose get_state / set_state.

When working, expect output:
  [1, 2, 3]
  ['a', 'b', 'c', 'd', 'e', 'f']
  []
  []
  [1, 2, 3]
  state after 2 yields: {'source_index': 0, 'index': 2}
  resume from {0, 2}: ['c', 'd', 'e']

Three patterns to internalize:
  1. **Lazy generator.** Build self._gen on the first __next__, NOT in
     __init__. Why: set_state must be able to "rewind" — easiest way is to
     null _gen and let __next__ rebuild from the new state.
  2. **State updated BEFORE yield, not after.** If get_state is called
     between yields, the cursor must already point at "next item to yield",
     not at the item just yielded. Update-before-yield enforces this.
  3. **set_state invalidates the generator.** Setting self._gen = None
     forces the next __next__ to rebuild from the new self.state.

Compare to your week2/04_resumable_iterator/solution.py. Same observable
behavior; different shape. Decide for yourself which is clearer for this
problem.
"""


class CompositeIterator:
    def __init__(self, sources):
        self.sources = sources
        self.state = {"source_index": 0, "index": 0}
        self._gen = None

    def __iter__(self):
        return self

    def _make_gen(self):
        src_index = self.state["source_index"]
        index = self.state["index"]
        while src_index < len(self.sources):
            while index < len(self.sources[src_index]) :
                item = self.sources[src_index][index]
                index += 1
                self.state = {"source_index": src_index, "index": index + 1}
                yield item
            src_index += 1
            index = 0
        self.state = {"source_index": src_index, "index": 0}

    def __next__(self):
        if self._gen is None:
            self._gen = self._make_gen()
        return next(self._gen)   # propagates StopIteration naturally

    def get_state(self):
        return dict(self.state)   # fresh copy, not a reference

    def set_state(self, state):
        self.state = dict(state)
        self._gen = None         # invalidate; rebuild on next __next_

def main() -> None:
    print(list(CompositeIterator([[1, 2, 3]])))
    print(list(CompositeIterator([["a", "b"], ["c"], ["d", "e", "f"]])))
    print(list(CompositeIterator([])))
    print(list(CompositeIterator([[], [], []])))
    print(list(CompositeIterator([[], [1, 2], [], [3], []])))

    # save / restore round-trip
    sources = [["a", "b", "c"], ["d", "e"]]
    it = CompositeIterator(sources)
    next(it); next(it)                          # consume "a", "b"
    state = it.get_state()
    print("state after 2 yields:", state)

    it2 = CompositeIterator(sources)
    it2.set_state(state)
    print("resume from {0, 2}:", list(it2))


if __name__ == "__main__":
    main()

#
# src_index = self.state["source_index"]
# index =  self.state["index"]
# while src_index < len(self.sources):
#     source = self.sources[src_index]
#     while index < len(source):
#         item = source[index]
#         index += 1
#         self.state = {"source_index" : src_index, "index" : index}
#         yield item
#     src_index += 1
#     index = 0
#     self.state = {"source_index" : src_index, "index" : index}
