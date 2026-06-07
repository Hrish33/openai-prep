"""
Bare-minimum custom iterator.

GOAL: Counter(n) yields 0, 1, 2, ..., n-1, then raises StopIteration.

You're proving you can write `__iter__` + `__next__` from memory. This is the
smallest possible iterator — everything else in this folder builds on it.

When working, expect output:
  list:  [0, 1, 2, 3, 4]
  manual: 0
  manual: 1
  manual: 2
  exhausted as expected
  reset: 0
  reset: 1

Three rules to get right:
  1. __iter__ returns self (this iterator IS the iterator)
  2. __next__ either returns the next item OR raises StopIteration
  3. Returning None on exhaustion is a BUG — the protocol is "raise to signal"
"""
from datetime import time, datetime
from random import randint
import threading

class AsyncCounter:
    def __init__(self, n: int) -> None:
        self.i = 0
        self.n = n

    def __aiter__(self):
        return self

    async def __anext__(self) -> int:
        if self. i == self.n :
            raise StopAsyncIteration
        await asyncio.sleep(randint(1, 2))
        num = self.i
        self.i += 1
        return num

    def reset(self)->None:
        self.i = 0

async def printCounter(num, name):
    async for x in AsyncCounter(num):
        print(name, x)

async def main() -> None:
    # Used by `for` loops and `list()`
    # print("list: ", list(AsyncCounter(5)))
    # await asyncio.gather(printCounter(5, "a"), printCounter(10, "b"))
    await asyncio.gather(*(printCounter(i, 'a' * i) for i in range(1, 6)))


import asyncio

if __name__ == "__main__":
    asyncio.run(main())

