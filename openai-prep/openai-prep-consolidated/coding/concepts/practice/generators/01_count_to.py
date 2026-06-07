"""
Plain def + yield — the minimal generator.

GOAL: count_to(n) yields 0, 1, 2, ..., n-1, then stops.

When working, expect output:
  list: [0, 1, 2, 3, 4]
  manual: 0
  manual: 1
  manual: 2
  exhausted as expected

Three rules to internalize:
  1. A `def` body containing `yield` is a generator function. Calling it
     returns a GENERATOR OBJECT — the body does NOT run yet.
  2. The first `next()` runs the body until the first `yield`. Subsequent
     `next()` calls resume from just after that yield, until the next one.
  3. The function returning (or falling off the end) raises StopIteration
     implicitly. You don't raise it yourself — that's the win over the class
     form, where you write `raise StopIteration` by hand.
"""


def count_to(n):
      for i in range(n):
          yield i

def main() -> None:
    # Used by for-loops and list()
    print("list:", list(count_to(5)))

    # Used by next()
    g = count_to(3)
    print("manual:", next(g))
    print("manual:", next(g))
    print("manual:", next(g))
    try:
        next(g)
        print("BUG — should have raised")
    except StopIteration:
        print("exhausted as expected")


if __name__ == "__main__":
    main()
