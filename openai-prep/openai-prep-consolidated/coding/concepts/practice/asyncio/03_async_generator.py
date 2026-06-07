"""
Async generator — `async def` + `yield` is sugar for an async iterator.

GOAL: acounter(n) yields 0, 1, ..., n-1 via `async def` + `yield`.
No __aiter__ / __anext__ to write — Python builds them for you.

When working, expect output:
  0
  1
  2

Two rules:
  1. An `async def` whose body contains `yield` is an async generator function.
     Calling it returns an async generator object — usable with `async for`.
  2. Python auto-implements __aiter__ / __anext__ / StopAsyncIteration. You
     just write the logic and `yield` values; exhaustion is signaled when
     the function returns (just like a sync generator).

This is the same relationship as `def + yield` → sync generator,
applied to the async protocol.
"""

import asyncio


async def acounter(n: int):
    # TODO:
      for i in range(n):
          await asyncio.sleep(0)
          yield i


async def main() -> None:
    async for x in acounter(3):
        print(x)


if __name__ == "__main__":
    asyncio.run(main())
