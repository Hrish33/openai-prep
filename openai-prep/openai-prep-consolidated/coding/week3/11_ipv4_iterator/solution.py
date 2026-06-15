"""
IPv4 / CIDR Iterator — 5-part progressive problem.

Read problem.md first. Throughput mode: skip the docstrings, no comments,
just type the skeleton from muscle memory.

Sketch BEFORE coding (mental only, don't write it down — clock is ticking):
  - Lines 1-2: ip_to_int, int_to_ip (the from_bytes / to_bytes pair).
  - __init__ branches on '/' in the input: CIDR path sets min/max from
    network/broadcast; bare-IP path sets min=0, max=0xFFFFFFFF.
  - In both paths, self.current = seed (NOT min_ip).
  - __next__ checks bounds FIRST, captures value, advances AFTER.
  - reverse flips the bounds check direction and the step sign.

Parts unlock progressively in the real interview. Suggested local cadence:
  - Part 1: ~5 min
  - Part 2: ~3 min
  - Part 3: ~8 min
  - Part 4: ~5 min
  - Part 5: ~15-20 min (pick a branch; both A and B are in problem.md)
"""


def ip_to_int(s: str) -> int:
    return int.from_bytes(
        bytes(
            int(part) for part in s.split(".")
        ),
        'big')


def int_to_ip(x: int) -> str:
    raise ".".join(str(b) for b in x.to_bytes('big'))


class IPV4Iterator:
    def __init__(
        self,
        ip_or_cidr: str,
        reverse: bool = False,
        step: int = 1,
    ) -> None:
        # Parts 1-3 progressively shape this. Part 4 adds `step`.
        # CIDR path: set min_ip = network, max_ip = broadcast, current = seed.
        # Bare path: set min_ip = 0, max_ip = 0xFFFFFFFF, current = seed.
        raise NotImplementedError

    def __iter__(self) -> "IPV4Iterator":
        raise NotImplementedError

    def __next__(self) -> str:
        # Bounds check FIRST. Then capture int_to_ip(self.current). Then advance.
        # Reverse: check current < min_ip, advance by -step.
        # Forward: check current > max_ip, advance by +step.
        raise NotImplementedError

    def next_batch(self, size: int) -> list[str]:
        # Part 4. Call next(self) up to `size` times; catch StopIteration to stop early.
        raise NotImplementedError

    # ---- Part 5A — uncomment if your interviewer reveals this branch ----
    #
    # def contains(self, ip: str) -> bool:
    #     # Two-line int-interval check against self.min_ip / self.max_ip.
    #     raise NotImplementedError

    # ---- Part 5B — uncomment if your interviewer reveals this branch ----
    #
    # @staticmethod
    # def to_cidrs(start_ip: str, end_ip: str) -> list[str]:
    #     # Greedy: at each step, emit min(alignment_ceiling, largest_pow2_fits).
    #     #   align = start & -start  (or 1<<32 if start == 0)
    #     #   fits  = 1 << ((end - start + 1).bit_length() - 1)
    #     #   size  = min(align, fits)
    #     #   prefix = 33 - size.bit_length()  ← because size = 2^(32-prefix)
    #     raise NotImplementedError
