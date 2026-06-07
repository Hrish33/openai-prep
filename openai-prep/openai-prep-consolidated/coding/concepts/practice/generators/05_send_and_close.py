"""
Two-way communication and cleanup — generators as coroutines.

GOAL: Use .send(value) to inject values back INTO a running generator, and
.close() to cleanly terminate it (triggers GeneratorExit inside).

When working, expect output:
  primed
  echo got: hello
  echo got: world
  echo got: 42
  closing now
  cleanup ran
  closed cleanly

Concepts:
  1. `yield` is an EXPRESSION, not a statement. It can RECEIVE a value:
        received = yield emitted
     The `emitted` value goes to the caller. The next .send(x) makes the
     `yield` expression evaluate to `x` on resume. Plain `next(g)` is
     equivalent to `g.send(None)`.

  2. .close() injects GeneratorExit at the currently-suspended yield. The
     generator can catch it to clean up but MUST eventually exit (return
     or re-raise). Swallowing GeneratorExit and yielding again is a
     RuntimeError.

  3. The first call must be next(g) (or g.send(None)). You can't .send(value)
     into a fresh generator before it's primed — there's no yield expression
     for the value to land on. This is the "priming" step.

Why this matters: this is the foundation `async def` is built on. A
coroutine is structurally a generator where `await` is sugar for
`yield from` on a Future. Understanding send/close IS understanding what
the asyncio event loop does under the hood when it drives coroutines.
"""


def echo():
    """Receives values via .send and prints them. Cleans up on close."""
    try:
        while True:
            received = yield               # first yield primes the gen
            print("echo got:", received)
    except GeneratorExit:
        print("cleanup ran")
          # implicit return — do NOT yield inside the except block

def main() -> None:
    g = echo()
    next(g)                          # prime — advances to the first `yield`
    print("primed")

    g.send("hello")
    g.send("world")
    g.send(42)

    print("closing now")
    g.close()                        # raises GeneratorExit inside `echo`
    print("closed cleanly")


if __name__ == "__main__":
    main()
