# Problem 3: Time-Based Key-Value Store

**Prereqs:** Work through `00_prereqs.md` first — especially the floor idiom and the out-of-order follow-up.

**Time budget:** 30 minutes for the base. The base is intentionally short; budget the rest of a 45-60 min round for follow-ups.
**Source:** [LeetCode 981](https://leetcode.com/problems/time-based-key-value-store/) + [HelloInterview community report](https://www.hellointerview.com/community/questions/time-key-value-store/cm5eguhad02rn838o3ttrkt0w) (which documents a real out-of-order-writes variant).

## Problem

Build a key-value store where each key holds a history of values stamped with timestamps. A read asks "what was the value of this key *as of* time T?" — and gets the value written at the largest timestamp `<= T`.

```python
tm = TimeMap()
tm.set("foo", "bar", 1)       # store foo=bar at t=1
tm.get("foo", 1)              # "bar"  (exact match)
tm.get("foo", 3)              # "bar"  (largest timestamp <= 3 is t=1)
tm.set("foo", "baz", 4)       # store foo=baz at t=4
tm.get("foo", 4)              # "baz"
tm.get("foo", 5)              # "baz"  (floor of 5 is t=4)
tm.get("foo", 0)              # ""     (nothing was set at or before t=0)
tm.get("nope", 1)             # ""     (key never set)
```

## Required API

- `set(key: str, value: str, timestamp: int) -> None` — store `value` for `key` at `timestamp`.
- `get(key: str, timestamp: int) -> str` — return the value for `key` at the largest stored timestamp `<= timestamp`. Return `""` if there is none (no such key, or all writes are after `timestamp`).

## Requirements

- **`get` is O(log n)** in the number of versions for that key. A linear scan is a fail — the sorted-history + binary-search structure is the point.
- **`set` is O(1)** *given the base guarantee below*. (Removing that guarantee is the first follow-up — see below.)
- **Floor semantics, inclusive of exact matches.** `get(k, t)` where `t` exactly equals a stored timestamp must return *that* write, not the one before it.
- **Multiple keys are independent.** Each key has its own version history.

## Constraints (the base problem's guarantees)

- **Timestamps for `set` are strictly increasing per key.** This is what makes `set` an O(1) append. The interviewer may remove this — be ready (`bisect.insort`).
- Keys and values are non-empty strings.
- `get` on a missing key or a timestamp before the first write returns `""`.
- Same-timestamp writes don't occur in the base (strictly increasing). Decide a policy if asked: last-write-wins is the usual answer.

## What an OpenAI interviewer is looking for

**The base is a screening filter, not the test.** Getting it clean and fast buys you the *real* conversation. They're watching:

1. **Did you state the assumption you're exploiting?** Saying "because timestamps are strictly increasing per key, `set` is a cheap append" *out loud* shows you know what your O(1) depends on — and primes you for the follow-up that removes it. Candidates who silently `append` look like they got lucky.
2. **The floor boundary, exactly right.** `bisect_right - 1`, with the empty-result case (`-1` → `""`) handled. Be able to explain why `right` not `left`.
3. **Data structure justification.** `dict[key] -> sorted list`. Parallel arrays (`times[]`, `values[]`) vs a list of `(timestamp, value)` tuples — know the trade-off (see `interviewer_notes.md`).
4. **Layered optimization under follow-up.** This is the axis this problem really grades. See the ladder below — each rung is a deliberate escalation, and they'll climb it as far as you can go.
5. **Edge-case discipline.** Empty result, missing key, exact-match timestamp, query before the first write — name these *before* coding.

## Follow-ups (don't peek until the base works)

<details>
<summary>Click to expand — this is where the round is actually decided</summary>

These are roughly in the order an interviewer escalates. Rungs 1-2 are documented for this problem; rung 3 (concurrency) is documented as a follow-up at a peer company (Google) and OpenAI tests concurrency elsewhere in the same loop (the crawler); 4-6 are the natural layered-optimization continuation. See the **Evidence** note after the follow-ups.

1. **Out-of-order writes** *(documented real variant)*. `set` can be called with timestamps in any order — you might write t=10 then later write t=8. `append` is now a bug. Fix with `bisect.insort` (O(n) insert). When is that too slow, and what do you reach for? (`SortedList` / balanced BST / skip list for O(log n) insert.)
2. **Get the boundary right under pressure.** Exact-match timestamp, query before all writes, query after all writes. Why `bisect_right` not `bisect_left`?
3. **Thread safety.** Concurrent `set` + `get`. Why does `get` need a lock too (the torn-read on `bisect` during `append`)? Global lock → per-key lock striping → reader/writer lock. (Real depth: week 3.)
4. **Bounded memory / retention.** Versions accumulate forever. How do you cap it? TTL/expiry, keep-last-N versions per key, compaction, GC of keys never read.
5. **Doesn't fit in RAM.** Billions of versions across millions of keys. Now it's a storage-engine question: in-memory index + on-disk append log, the LSM-tree / SSTable shape. (Bridges to system design — they may steer you there.)
6. **Richer queries.** Range scan: all values for a key in `[t1, t2]` — two bisects + a slice, ideally returned as a *generator*. Or "latest value across *all* keys as of T" — needs a different index.

</details>

<details>
<summary>More follow-ups — deeper extensions (all derived, none field-reported for this problem)</summary>

Mostly further escalations grouped by rubric axis. Two of these (**deletion**, and the **transactional** variant) are actually attested across interview-prep sites — they're flagged below. Use the rest as a prep bank, not a prediction.

**Richer semantics (API extensions)**
- **Deletion / tombstones.** *(Attested — cited as a common follow-up for this problem.)* `delete(key)` (or delete-as-of-T). Represent "deleted at T" with a tombstone marker so `get` returns `""` between the tombstone and the next write. Tension: when is it safe to GC a tombstone? (Cassandra-style problem.)
- **Transactions.** *(Attested — but arguably a separate "transactional KV store" question.)* `begin()` / `commit()` / `rollback()`, possibly nested. Each value carries a version number; concurrent transactions use optimistic locking — record versions read, detect conflicts at commit by comparing current versions, apply atomically if clean. This is the MVCC direction.
- **Whole-store point-in-time snapshot.** `get_all(T)` — every key's value as of T. MVCC snapshot isolation; a different access pattern than per-key floor.
- **Windowed count / aggregate.** "How many versions of K in `[t1, t2]`?" → two bisects, subtract indices, O(log n). Reuses the structure you already have.

**Python-internals depth**
- **Iterate a key's history.** Implement `__iter__` / a generator over versions. Then the trap: mutation *during* iteration — snapshot-copy vs live iterator (mimic dict's `RuntimeError` on concurrent modification?).
- **Memory micro-opts.** Intern duplicated value strings; `__slots__` on a version object.

**Durability / lifecycle**
- **Crash recovery.** Write-ahead log + replay on restart; `fsync` trade-offs. About *durability*, distinct from the doesn't-fit-in-RAM size question.
- **Lazy vs eager expiry.** For TTL: background sweep thread vs expire-on-read. CPU-vs-memory trade-off; interacts with the thread-safety rung.
- **Downsampling / rollups.** Full resolution for recent data, aggregated/downsampled for old (time-series move).

**Distributed (they'll likely steer you to system design)**
- **Clock source & skew.** Client vs server timestamp; multi-writer ordering needs Lamport or hybrid logical clocks (HLC).
- **Multi-writer conflict resolution.** Same key + same logical time on two nodes → last-write-wins with a node-id tiebreaker, or CRDT-style merge.
- **Sharding.** Partition by key; "latest across all keys as of T" becomes scatter-gather across shards.

</details>

## Evidence (checked 2026-05-27)

Where the follow-up tiers above come from, graded by source quality:

- **The question itself is confirmed at OpenAI** — it's on [HelloInterview's OpenAI question list](https://www.hellointerview.com/blog/openai-coding-questions), built from real candidate reports (the same list confirms all 8 problems in this repo). It's also reported at **Stripe** ([Glassdoor](https://www.glassdoor.com/Interview/Implement-a-key-value-store-with-history-through-timestamps-QTN_947877.htm) — "key-value store with history through timestamps"), **Meta** ([Taro](https://www.jointaro.com/interviews/meta/time-based-key-value-store/)), and **Google**.
- **Out-of-order writes** — documented on the [HelloInterview community page](https://www.hellointerview.com/community/questions/time-key-value-store/cm5eguhad02rn838o3ttrkt0w) (the MongoDB variant).
- **Multi-threaded version** — first-hand [Google interview report on LeetCode Discuss](https://leetcode.com/discuss/post/5141523/Google-Interview-How-to-implement-a-multi-thread-version-of-Time-based-Key-Value-Store/). High trust that concurrency is a real follow-up; not confirmed specifically at OpenAI.
- **Deletion, TTL, transactions** — cited across interview-prep aggregators (Taro and others). Medium trust.
- **Lock-type comparison, on-disk persistence + custom serialization, mock-timestamp testing** — these circulate on lower-trust content-farm sites and are **not** in HelloInterview's credible OpenAI write-up. Treat as *plausible* rather than confirmed. The reason they're still worth prepping: OpenAI tests both themes as **separate confirmed questions in the same loop** — the multithreaded crawler (concurrency) and KV-serialize/deserialize (custom serialization). So they're realistic cross-overs.

**Bottom line:** no credible source enumerates OpenAI's exact follow-ups to *this* problem. Out-of-order is documented; concurrency and deletion are attested at peer companies; the rest is reasoned from OpenAI's broader question bank. Prep the themes; don't memorize a script.

## Honest difficulty note

This is the **inverse** of problem 1. There, the base is hard and finishing it is a pass. Here, the base is *easy* — if you only produce the base and can't engage the follow-ups, that's a **weak** performance, because the base doesn't differentiate you from anyone who's seen LC 981. The signal is entirely in how many rungs of the follow-up ladder you can climb with real reasoning. Treat the 30-minute base as a warm-up and **spend your prep on the follow-ups.**
