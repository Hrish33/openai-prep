"""
The iterable-vs-iterator distinction — break it, then fix it.

GOAL: Observe the one-shot trap firsthand. Then write a wrapper that handles
both re-iterable sources (lists) and one-shot sources (generators) correctly.

When working, expect output:
  list (re-iterable):
    first  pass: [1, 2, 3]
    second pass: [1, 2, 3]                   <-- works: iter() gives a fresh iterator
  generator (one-shot):
    first  pass: [1, 2, 3]
    second pass: []                          <-- BROKEN: generator is exhausted
  iter() of list returns NEW object each time: True
  iter() of generator returns SAME object:    True   (generators ARE their own iterator)
  ----
  SafeSource wraps a one-shot generator and makes it re-iterable:
    first  pass via SafeSource: [1, 2, 3]
    second pass via SafeSource: [1, 2, 3]    <-- works because we materialized

Why this matters for the real problem:
  CompositeIterator's set_state may need to RESTART a source from item 0.
  If the source is a one-shot generator, you can't — it's already past.
  Either require sources to be re-iterable (the clean answer) or wrap them
  in something that memoizes (the expensive answer).

  In the real interview: name the constraint. "Sources must be re-iterable;
  a generator passed in would break set_state because we can't rewind it.
  I'd validate this in __init__ or document the contract."
"""


def gen_123():
    """A generator function. Each call returns a fresh, one-shot generator."""
    yield 1; yield 2; yield 3


class SafeSource:
    """Wrap a possibly-one-shot iterable so it can be iterated multiple times.

    The trick: materialize what's been consumed into a buffer, then replay
    the buffer + any not-yet-consumed items on subsequent __iter__ calls.

    For simplicity here, just materialize the whole thing up-front. That's
    O(N) memory and only safe for finite sources, but it's enough for the
    drill. (For lazy materialization, see itertools.tee.)
    """

    def __init__(self, source) -> None:
        # TODO: consume `source` into a list and store it
        raise NotImplementedError

    def __iter__(self):
        # TODO: return a fresh iterator over the stored list
        raise NotImplementedError


def main() -> None:
    # A list IS an iterable but NOT an iterator. iter() gives a fresh iter.
    lst = [1, 2, 3]
    print("list (re-iterable):")
    print("  first  pass:", list(lst))
    print("  second pass:", list(lst))

    # A generator IS an iterator (and an iterable). Once consumed, done.
    g = gen_123()
    print("generator (one-shot):")
    print("  first  pass:", list(g))
    print("  second pass:", list(g))

    print("iter() of list returns NEW object each time:",
          iter(lst) is not iter(lst))
    print("iter() of generator returns SAME object:    ",
          iter(g) is iter(g))                    # generators: iter(g) IS g

    print("----")
    print("SafeSource wraps a one-shot generator and makes it re-iterable:")
    safe = SafeSource(gen_123())
    print("  first  pass via SafeSource:", list(safe))
    print("  second pass via SafeSource:", list(safe))


if __name__ == "__main__":
    main()
