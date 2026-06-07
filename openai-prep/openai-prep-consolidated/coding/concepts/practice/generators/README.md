# Practice drills — generators

**These are scaffolds, not finished code.** Each file has the structure laid out with `# TODO` markers and `raise NotImplementedError` where you fill in the implementation. Run as-is and you'll hit the error — that's expected. Fill in, then run.

The point is to build muscle memory for `yield`, `yield from`, `.send`, `.close`, and the hybrid class+generator pattern by typing the code, not reading a reference.

## Drills

| File | What you're implementing | Backing section in [`../../iterators.md`](../../iterators.md) |
|------|--------------------------|---------------------------------------------------------------|
| `01_count_to.py` | Plain `def` + `yield` — the minimal generator | §1 of "Common patterns" |
| `02_chunked.py` | Stateful generator — locals are the state | §3 (stateful generator pattern) |
| `03_flatten_yield_from.py` | `yield from` — flat composite walk in 3 lines | §4 (composite/flatten pattern) |
| `04_class_wrapping_gen.py` | Hybrid: class shell + generator body — Problem 4 alternative | §3 ("promote to a class only when...") |
| `05_send_and_close.py` | Two-way communication via `.send`, cleanup via `.close` + `GeneratorExit` | Not in iterators.md — depth-probe material; see `../../asyncio.md` §8 for the connection |

## Workflow

For each file:

1. **Read** the docstring at the top — it tells you what "working" looks like and what the expected output is.
2. **Sketch** the structure before typing. The TODOs are guideposts, not copy-paste.
3. **Type** the implementation.
4. **Run** it. Compare output to the expected description in the docstring.
5. **Delete** your implementation. Re-do it from scratch the next day. Repetition is the entire point.

## How to run

```bash
cd coding/concepts/practice/generators
python 01_count_to.py
python 02_chunked.py
python 03_flatten_yield_from.py
python 04_class_wrapping_gen.py
python 05_send_and_close.py
```

## Readiness bar

- You can write `01` and `02` in **under 3 minutes each** from a blank screen.
- You can write `03` in **under 1 minute** — it's literally one `for` + `yield from`.
- You can write `04` and have it pass the same 20 tests as `../../../week2/04_resumable_iterator/solution.py` (point pytest at this file instead). That's the proof you understand the hybrid pattern end-to-end.
- You can explain — without looking — why the first call to a fresh generator must be `next()` not `send(value)`. (Answer: there's no `yield` expression yet for the value to land on; the generator hasn't started executing.)

## Stuck?

- 01, 02, 03 → re-read `../../iterators.md` sections 1, 3, 4 of "Common patterns".
- 04 → re-read the hybrid-pattern explanation (lazy `_gen`, state-before-yield, invalidate on `set_state`). The trickiest is rule #2 (update state BEFORE yield) — get this wrong and `get_state` returns a stale cursor between yields.
- 05 → no good local reference; this is the connection point to asyncio. Read `../../asyncio.md` §8 (CPython internals) — `await` desugars to `yield from`, so understanding `send` / `close` IS understanding what the event loop is doing when it drives coroutines.
