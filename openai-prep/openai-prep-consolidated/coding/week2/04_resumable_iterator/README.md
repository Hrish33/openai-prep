# Problem 4: Resumable Iterator

**Status:** Not yet scaffolded. Tell Claude Code "scaffold problem 4" when you're ready.

**One-liner:** Create an iterator that can pause and resume across multiple calls, maintaining state.

**Source:** [HelloInterview community question](https://www.hellointerview.com/community/questions/resumable-iterator/cmbskz7ck004r07ad6f1jxlni)

**Key concept:** the Python iterator protocol (`__iter__`, `__next__`, `StopIteration`)

**Likely prereqs:**
- **This is a Python-internals problem.** No LC primer — instead, read the local concept guide: `coding/concepts/iterators.md` (to be generated when you reach this problem).
- After reading the guide, practice writing iterators from scratch: a `Range`, a `Fibonacci`, a `ChunkedReader`.
- Then `__getstate__`/`__setstate__` for the "resumable across calls" requirement — what does it mean to pause and resume? The iterator's state has to be re-creatable.

**When to do this:** week 2. This is the load-bearing Python skill OpenAI tests directly. Don't skip the concept guide.
