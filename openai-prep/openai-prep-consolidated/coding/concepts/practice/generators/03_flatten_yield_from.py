"""
yield from — flat iteration across nested sources, in 3 lines.

GOAL: flatten(sources) yields every item across every source in order.
This is what `CompositeIterator` would be if it didn't need save/restore.

When working, expect output:
  list(flatten([[1, 2, 3], [4, 5], [6]])):  [1, 2, 3, 4, 5, 6]
  list(flatten([])):                          []
  list(flatten([[], [1], [], [2, 3]])):       [1, 2, 3]
  list(flatten(("ab", "cd"))):                ['a', 'b', 'c', 'd']

Two rules:
  1. `yield from iterable` is equivalent to `for x in iterable: yield x`.
     Use it when you want to delegate iteration to another iterable wholesale.
  2. Nested generators compose: a generator can `yield from` another generator,
     stacking pipelines without managing inner iterators by hand.

This is the EXACT solution to Problem 4 if save/restore weren't required.
Three lines. The whole reason Problem 4 needs a class is because `get_state`
can't reach into the frame to read the cursor.
"""


def flatten(sources):
    for source in sources:
        yield source


def main() -> None:
    print("list(flatten([[1, 2, 3], [4, 5], [6]])): ", list(flatten([[1, 2, 3], [4, 5], [6]])))
    print("list(flatten([])):                        ", list(flatten([])))
    print("list(flatten([[], [1], [], [2, 3]])):     ", list(flatten([[], [1], [], [2, 3]])))
    print("list(flatten(('ab', 'cd'))):              ", list(flatten(("ab", "cd"))))


if __name__ == "__main__":
    main()
