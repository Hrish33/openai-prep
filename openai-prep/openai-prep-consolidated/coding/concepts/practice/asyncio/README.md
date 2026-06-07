# Practice drills — asyncio

**These are scaffolds, not finished code.** Each file has the structure laid out with `# TODO` markers and `raise NotImplementedError` where you fill in the implementation. Run as-is and you'll hit the error — that's expected. Fill in, then run.

The point is to build muscle memory for `async def` / `await` / `__aiter__` / `__anext__` / `gather` / `Semaphore` by typing the patterns and watching the timing, not by reading a reference.

## Drills

| File | What you're implementing | Backing section in [`../../asyncio.md`](../../asyncio.md) |
|------|--------------------------|-----------------------------------------------------------|
| `01_coroutine_basics.py` | What `async def` returns; `asyncio.run`; `await` | §2, §3 |
| `02_async_counter.py` | `__aiter__` / `__anext__` / `StopAsyncIteration` — the protocol | §4 |
| `03_async_generator.py` | `async def` + `yield` — the sugar form | §4 |
| `04_gather_concurrent.py` | `asyncio.gather` — feel the concurrency win in your gut | §6 |
| `05_bounded_gather.py` | `asyncio.Semaphore` + gather — the Problem 8 follow-up shape | §6 |
| `06_blocking_trap.py` | `time.sleep` vs `asyncio.sleep` — observe the loop freeze | §9 mistake 2 |

## Workflow

For each file:

1. **Read** the docstring at the top — it tells you what "working" looks like and what the expected output is.
2. **Sketch** the structure before typing. The TODOs are guideposts, not copy-paste.
3. **Type** the implementation.
4. **Run** it. Compare output to the expected description in the docstring.
5. **For drills 04 / 05 / 06: feel the timing.** If the times don't match the expected wall-clock pattern, something is wrong — most likely a sync call you didn't notice.
6. **Delete** your implementation. Re-do it from scratch the next day. Repetition is the entire point.

## How to run

```bash
cd coding/concepts/practice/asyncio
python 01_coroutine_basics.py
python 02_async_counter.py
python 03_async_generator.py
python 04_gather_concurrent.py
python 05_bounded_gather.py
python 06_blocking_trap.py
```

## Readiness bar

You're ready for the **Problem 4 async follow-up** once you can write `02_async_counter.py` from a blank screen in **under 5 minutes** without checking the docstring or `asyncio.md`. The protocol is small; the bar is "instant recall," not "can derive."

You're ready for the **Problem 8 async alt path** once you can write `05_bounded_gather.py` from scratch in **under 10 minutes** and articulate why `k=2` finishes in ~3s, not 2.5s or 4s.

## Stuck?

Re-read the relevant section in `../../asyncio.md`:
- 01 → §2 (coroutines), §3 (asyncio.run)
- 02 → §4 (async iterator protocol — three traps)
- 03 → §4 (async generators)
- 04 → §6 (gather / create_task)
- 05 → §6 + §10 Exercise 4 (the bounded-gather pattern)
- 06 → §9 mistake 2 (blocking calls in async code)
