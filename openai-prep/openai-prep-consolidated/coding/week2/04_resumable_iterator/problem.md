# Problem 4: Resumable Iterator

**Prereqs:** Work through `00_prereqs.md` first. Generate and read `coding/concepts/iterators.md`. Don't attempt cold — the protocol details matter and bugs in iterator code are nasty to debug.

**Time budget:** 30 minutes for the sync base. Budget the remaining time in a 45-60 min round for follow-ups — the round is won there.
**Source:** [HelloInterview community report](https://www.hellointerview.com/community/questions/resumable-iterator/cmbskz7ck004r07ad6f1jxlni). The reported version uses `async`; this scaffold splits it into a **sync base** (teaches the protocol + state design cleanly) and an **async follow-up** (the reported shape).

## Problem

Implement a `CompositeIterator` that yields items across multiple sources in order, with the ability to **pause and resume** via a serializable state object. The state must capture the exact position so that restoring it and calling `next()` produces the same value that *would* have come next without the save/restore round-trip.

```python
sources = [["a", "b", "c"], ["d", "e"], ["f", "g", "h"]]
it = CompositeIterator(sources)

next(it)                         # "a"
next(it)                         # "b"
state = it.get_state()           # snapshot — JSON-serializable dict

next(it)                         # "c"
next(it)                         # "d"

it2 = CompositeIterator(sources)
it2.set_state(state)
next(it2)                        # "c"  — resumes exactly where state was taken
next(it2)                        # "d"
```

Notice: the state survives across instances. You can persist it (write to disk, send over the network) and reconstruct iteration later, even in a different process.

## Required API

- `__init__(self, sources: list[Iterable[T]]) -> None` — sources is a list of re-iterable inputs (lists, tuples, file paths — anything you can call `iter()` on more than once).
- `__iter__(self) -> "CompositeIterator"` — returns `self`.
- `__next__(self) -> T` — yields the next item across all sources in order; raises `StopIteration` when exhausted.
- `get_state(self) -> dict` — returns a JSON-serializable dict capturing current position.
- `set_state(self, state: dict) -> None` — restores position from a previously-returned state. Subsequent `next()` calls resume from that point.

## Requirements

- **State is JSON-serializable.** `json.dumps(it.get_state())` works. No pickle, no opaque blobs. The state shape is part of your interface.
- **Resume is exact.** After `set_state(state)`, the next yielded value equals what *would* have come next at the moment `state` was captured.
- **Sources are re-iterable, not exhausted iterators.** Calling `iter(source)` twice on the same source must yield the same items both times. This is a constraint *on the input*; flag it explicitly if asked.
- **State is position-based, not snapshot-based.** Don't store remaining items. Store cursors (source index + per-source offset). This must be O(K) where K = number of sources, not O(N) in remaining items.
- **`get_state` is O(K).** Cheap snapshot — building the state dict shouldn't iterate through anything.
- **`set_state` is O(K + advance_cost)** — opening each source plus skipping to its offset. For a list source, that's O(K + offset); for a file source, O(K + bytes_to_skip).

## Constraints

- Sources are non-empty list of iterables. Individual sources may be empty (just skip them).
- Items can be any hashable or non-hashable type — your iterator should not assume.
- Restoring a state taken from a CompositeIterator with different sources is **undefined behavior**. Be ready to either validate or document that the state is paired with its sources.
- `next()` on an exhausted iterator raises `StopIteration`. State captured at exhaustion, when restored, should also raise `StopIteration` on the next `next()`.

## What an OpenAI interviewer is looking for

**The base is a screening filter.** Getting it clean and fast buys you the *real* conversation about state design and async.

1. **State design — articulate it before coding.** "Two integers per composite iterator: which source am I in, how far am I into it." Saying this out loud before touching the keyboard is the strongest single signal in this problem. Candidates who design state by accident look junior.
2. **Iterable vs. iterator — name the constraint on the input.** "I need sources I can re-iterate, because `set_state` has to seek. A consumed generator can't be rewound, so the input is a list-of-lists, not a list-of-generators." Volunteering this without prompting is senior-level.
3. **JSON-serializable, by construction.** No pickle, no opaque types. The state dict has dict, list, int, str at the leaves. If asked "what if I want to persist this to a file?" your answer is `json.dump(state, f)` — full stop.
4. **`set_state` actually seeks.** Naive implementation: copy the state ints. Correct implementation: open the current source and advance it to the offset *eagerly*, so the next `__next__` doesn't have to. Either order works, but be deliberate about which one you chose and why.
5. **The follow-up ladder.** Async, pickle, source mutation, byte-level offsets for files — they'll climb as far as you can go. See below.

## Follow-ups (don't peek until the base works)

<details>
<summary>Click to expand — this is where the round is decided</summary>

Roughly ordered by how an interviewer escalates.

1. **Async version (the reported shape).** Switch `__iter__` / `__next__` to `__aiter__` / `__anext__`, raise `StopAsyncIteration`, support `async for x in it`. What changes about state — specifically, what happens if `get_state` is called *during* an in-flight `__anext__`? Decide your snapshot policy (atomic at entry to `__anext__`? atomic at first `await`?) and defend it.
2. **Sources are file paths, not lists.** Open lazily in `__next__`; close when done with a source. State is `{source_idx, line_offset}`. What changes about `set_state`? (Skip-N lines, not random-access seek — unless you also stored byte offsets.) Why might byte offsets be wrong? (Multi-byte UTF-8.)
3. **Pickle integration.** Add `__getstate__` / `__setstate__` so `pickle.dumps(it)` / `pickle.loads(...)` work. When is pickle *not* the right answer? (Cross-language, cross-version, untrusted input — pickle executes arbitrary code on load.)
4. **Source mutation mid-iteration.** What if `sources[1]` is appended to *while* we're iterating it? Mimic `dict`'s `RuntimeError` on concurrent modification? Snapshot the lengths up-front? Document the policy.
5. **Two iterators sharing one state object.** `it1` and `it2` both restore from the same state and run in parallel. Do they interfere? (They shouldn't — state should be a value, not a reference. Confirm `get_state` returns a fresh dict, not the live one.)
6. **`get_state` mid-stream guarantees.** If you call `get_state`, `next()`, then `set_state(captured)`, is the next value exactly what it was at capture time? Write a property-based test for this.
7. **Bounded `next()` — `next_n(k)` that yields k items as a list.** Trivial composition (`[next(self) for _ in range(k)]`), but the right place to think about partial exhaustion: what if only 3 of 5 requested items are available?

</details>

<details>
<summary>More follow-ups — deeper extensions</summary>

**Performance and scale**
- **Skip ahead by N items efficiently.** For list sources, slicing is O(1); for file sources, you have to read. What's the right API? (`advance(n)` that returns items skipped?)
- **Source produces items lazily and expensively** (e.g., paginated API). Cache items already seen? Re-fetch on resume? Trade-off: memory vs. latency.
- **Many small sources.** Opening a file per source is expensive. Pool? Defer? When does the cost actually matter?

**Concurrency**
- **Thread-safe iteration.** Two threads calling `next()` on the same iterator — what breaks? (The cursor pair becomes a check-then-act race; lock around the increment.)
- **Thread-safe state.** Can `get_state` race with `next()`? (Yes — partial state read.) Fix: copy under the same lock that guards `next()`.

**Distributed**
- **State as a checkpoint** — every K items, persist `get_state()` to durable storage. Restart from latest checkpoint on crash. What's K? (Latency vs. work-lost trade-off.)
- **Multiple workers consuming one logical iterator.** Centralize the state in a coordinator; workers pull "next batch + offset" atomically. This is the Kafka consumer-group shape.

**Schema / typing**
- **Generic over item type.** `class CompositeIterator(Generic[T])`. Where does `T` come from? (The element type of the sources.)
- **Versioned state.** What if `get_state` shape changes between releases? Add a `"version"` key; reject states with unrecognized versions in `set_state`.

</details>

## Evidence (checked 2026-05-30)

- **The question is confirmed at OpenAI** — [HelloInterview community post](https://www.hellointerview.com/community/questions/resumable-iterator/cmbskz7ck004r07ad6f1jxlni), which sources real candidate reports.
- **The reported variant uses `async`** — see the community post. The sync version in this scaffold is a teaching scaffold, not the field-reported shape. Get the sync base solid first, then implement the async follow-up (#1 above) — that's what an interviewer is actually likely to ask.
- **State serialization (JSON / pickle) follow-ups** — not directly attested for this problem, but OpenAI tests serialization in a separate problem in the same loop (Problem 2 — KV serialize). High plausibility that depth on serialization shows up here too.
- **Multi-threaded iteration** — not attested for this problem; included as a general layered-optimization rung. Don't lead with it unless asked.

## Honest difficulty note

The base is **deceptively easy** if you've seen LC 251. The trap is treating it like LC 251 and not designing the state deliberately. A clean sync base in 15 minutes that you can articulate in terms of "two integers, JSON-serializable, here's why each shape I rejected" is a *strong* showing — much stronger than a 30-minute base that grew naturally without that clarity.

If you finish the base in 15 minutes, **don't celebrate** — pivot immediately to async (#1) or pickle (#3). The reported question is async, and the interviewer expects you to get there.
