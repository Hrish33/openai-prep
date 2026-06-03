# Practice files — iterator protocol

**These are scaffolds, not finished code.** Each file has the structure laid out with `# TODO` markers and `raise NotImplementedError` where you fill in the implementation. Run as-is and you'll hit the error — that's expected. Fill in, then run.

The point is to build muscle memory for `__iter__` / `__next__` / `StopIteration` by typing the pattern, not by reading a reference.

| File | What you're implementing | Backing concept |
|------|--------------------------|-----------------|
| `01_counter.py` | Bare-minimum custom iterator — `Counter(n)` yields 0..n-1 | Concept 1 |
| `02_range.py` | Match Python's built-in `range` semantics (start, stop, step, negative step) | Concept 1 |
| `03_chunked_reader.py` | Iterator that yields fixed-size chunks of a string | Concept 1 (applied) |
| `04_one_shot_trap.py` | Demonstrate the iterable-vs-iterator distinction — *break* the assumption, then fix it | Concept 2 |
| `05_resumable_range.py` | Add `get_state` / `set_state` to your Range — the bridge to the real problem | Concept 3 |

## Workflow

For each file:

1. **Read** the docstring at the top — it tells you what "working" looks like and what the expected output is.
2. **Sketch** the state and the `__next__` logic before typing.
3. **Type** the implementation.
4. **Run** it. Compare output to the expected description in the docstring.
5. **Delete** your implementation. Re-do it from scratch the next day. Repetition is the entire point.

## How to run

```bash
cd coding/week2/04_resumable_iterator/practice
python 01_counter.py
python 02_range.py
python 03_chunked_reader.py
python 04_one_shot_trap.py
python 05_resumable_range.py
```

## Readiness bar

Once you can write `02_range.py` from a blank screen (delete everything except the imports and module docstring; re-type it) in **under 10 minutes** AND `05_resumable_range.py` in **under 15 minutes**, you're ready to attempt `../solution.py`. Not before.

## Stuck?

Re-read the relevant Concept in `../00_prereqs.md`:
- 01, 02, 03 → Concept 1 (iterator protocol)
- 04         → Concept 2 (iterable vs iterator)
- 05         → Concept 3 (state design)

Or read `../../../concepts/iterators.md` — the concept guide has more worked examples and the deeper "how CPython implements it" view.
