"""
Coroutine basics — what `async def` actually returns, and how to run it.

GOAL: Prove three facts by running and observing output.

When working, expect output:
  calling an async fn returns a: coroutine
  body did NOT run yet
  ---
  greet: hello world
  add(2, 3) = 5

Three rules to internalize:
  1. `async def fn(): ...` then `fn()` does NOT execute the body — it builds
     a coroutine object. The body runs only when something drives it.
  2. Coroutines need a driver: `asyncio.run(coro)` at the top-level boundary,
     `await coro` anywhere inside async code.
  3. `await x` drives the awaitable x to completion and yields its result
     to the caller. This is the suspension point.
"""

import asyncio


async def greet(name: str) -> None:
    print('heelo from async')


async def add(a: int, b: int) -> int:
    # TODO: await asyncio.sleep(0)   # forces a suspension point, no delay
    # TODO: return a + b
    await asyncio.sleep(0)
    return a + b


async def main() -> None:
    # TODO: await greet("world")
    # TODO: result = await add(2, 3); print("add(2, 3) =", result)
    coroutine = greet("world")        # NOTHING printed yet
    result = await add(2, 3)
    print('add', result)
    await coroutine
    coroutine.close()

def experiment_one() -> None:
    """Calling an async fn does NOT execute the body — observe the type."""
    coro = greet("dummy")
    print("calling an async fn returns a:", type(coro).__name__)
    print("body did NOT run yet")
    coro.close()   # silences the "coroutine was never awaited" RuntimeWarning


if __name__ == "__main__":
    experiment_one()
    print("---")
    asyncio.run(main())
