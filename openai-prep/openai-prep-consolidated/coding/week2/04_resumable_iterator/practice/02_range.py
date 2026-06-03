"""
Match Python's built-in `range` semantics with a custom iterator.

GOAL: MyRange(start, stop, step) behaves like the built-in range — including
negative step, zero-step error, and the "empty range" cases.

When working, expect output:
  list(MyRange(0, 5)):       [0, 1, 2, 3, 4]
  list(MyRange(2, 8, 2)):    [2, 4, 6]
  list(MyRange(5, 0, -1)):   [5, 4, 3, 2, 1]
  list(MyRange(0, 5, -1)):   []
  list(MyRange(5, 0, 1)):    []
  zero step:                  ValueError raised as expected

Two subtleties most candidates miss on the first try:
  1. The stopping condition depends on the SIGN of step.
     Positive step: stop when `current >= stop`
     Negative step: stop when `current <= stop`
     Get this with a single comparator function or by branching once on sign.
  2. `step == 0` is `ValueError`, not infinite loop. Catch it in __init__.
"""


class MyRange:
    def __init__(self, start: int, stop: int = None, step: int = 1) -> None:
        if start and stop is None:
            self.start = 0
            self.stop = start
        else:
            self.start = start
            self.stop = stop
        if step == 0:
            raise ValueError

        self.step = step
        self.cursor = start

    def __iter__(self) -> "MyRange":
        return self

    def __next__(self) -> int:
        if self.step > 0 and self.cursor >= self.stop:
            raise StopIteration
        if self.step < 0 and self.cursor <= self.stop:
            raise StopIteration

        val = self.cursor
        self.cursor += self.step
        return val




def main() -> None:
    print("list(MyRange(0, 5)):     ", list(MyRange(0, 5)))
    print("list(MyRange(2, 8, 2)):  ", list(MyRange(2, 8, 2)))
    print("list(MyRange(5, 0, -1)): ", list(MyRange(5, 0, -1)))
    print("list(MyRange(0, 5, -1)): ", list(MyRange(0, 5, -1)))
    print("list(MyRange(5, 0, 1)):  ", list(MyRange(5, 0, 1)))

    try:
        MyRange(0, 5, 0)
        print("zero step:               BUG — should have raised")
    except ValueError:
        print("zero step:               ValueError raised as expected")


if __name__ == "__main__":
    main()
