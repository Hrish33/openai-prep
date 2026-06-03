# Problem 4: Resumable Iterator

**Status:** Scaffolded. Work the files in order.

**One-liner:** Build an iterator that walks a list of sources in order and exposes JSON-serializable `get_state` / `set_state` so iteration can be paused and resumed across processes.

**Source:** [HelloInterview community question](https://www.hellointerview.com/community/questions/resumable-iterator/cmbskz7ck004r07ad6f1jxlni) — reported variant uses `async`; this scaffold uses sync for the base and lists async as the primary follow-up.

**Key concept:** Python iterator protocol (`__iter__`, `__next__`, `StopIteration`) + state design for serialization.

## Files

| File | When to read |
|------|--------------|
| `00_prereqs.md` | First. 2-3 hours of iterator-protocol + state-design foundation. Read `coding/concepts/iterators.md` along the way. |
| `practice/` | Five TODO-marker drills (`01_counter.py` → `05_resumable_range.py`) that build the protocol muscle before assembly. |
| `problem.md` | Once prereqs feel solid AND drills run clean. The actual interview problem. |
| `solution.py` | Empty starter — fill in. State shape is yours to design. |
| `test_solution.py` | `pytest test_solution.py -v`. Covers cross-boundary resume and JSON round-trip. |
| `interviewer_notes.md` | **After** your attempt. Reference solution, async/pickle/file follow-ups, grading rubric, common mistakes. |

## When to do this

Week 2. **Don't skip the concept guide** — this problem is a thin shell around the iterator protocol, and missing the state-design articulation is the #1 way to under-perform on a base you "got working."
