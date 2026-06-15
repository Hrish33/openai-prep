# Problem 12: GPU Credit System

**Prereqs:** Skim `00_prereqs.md` if you haven't internalized replay-from-scratch semantics and the "earliest-expiring first" greedy with a sorted-by-expiration structure.

**Time budget:** 35 min (phone screen).
**Source:** OpenAI phone screen, last seen 2026-05-14. Frequency: medium.
**Stage:** Phone screen.

---

## The problem

You're simulating a GPU credit grant system. Three operations:

1. **`add_credit`** — issue a credit grant with a unique id, an amount, an activation timestamp, and a relative expiration duration. The grant is valid through `timestamp + expiration` **inclusive**.
2. **`subtract`** — consume credit at a given timestamp. Burns from the grant expiring **soonest** first, draining across multiple grants if needed. Never raises. The running balance is allowed to go negative.
3. **`get_balance`** — query the balance at a given timestamp. Implemented as a **full replay from scratch** of every event with `timestamp <= query_time`, then sum the surviving credit.

Events can arrive **out of order**: a `subtract` at t=30 can be called before the `add_credit` that activates at t=20. The replay model handles this — `get_balance` re-derives everything from the full event log each call.

**Invariant:** at most one event (add_credit or subtract) per timestamp. No tie-breaking needed within a single tick.

---

## Required API

```python
class GPUCredit:
    def add_credit(
        self,
        credit_id: str,   # unique
        amount: int,
        timestamp: int,   # grant becomes active at `timestamp`
        expiration: int,  # grant is valid through `timestamp + expiration` INCLUSIVE
    ) -> None: ...

    def subtract(self, amount: int, timestamp: int) -> None: ...

    def get_balance(self, timestamp: int) -> int | None: ...
```

### `get_balance` return semantics — the trap

`get_balance(t)` returns:
- An **integer balance** when there's an active grant at `t` and the replayed balance is `>= 0`.
- `0` (not `None`) when the replayed balance is **exactly 0** but at least one grant is currently active.
- `None` when **either** (a) no grant is active at `t`, **or** (b) the replayed balance is **negative**.

The candidate trap is conflating the two `None` cases. Exact zero from real cancellation is **0**, not `None`. Only a truly negative replay (e.g., `-90`) collapses to `None`.

---

## Examples

```python
# Burn the soonest-expiring credit first
gpu = GPUCredit()
gpu.add_credit('a', 4, 20, 40)   # valid 20–60
gpu.add_credit('b', 3, 30, 10)   # valid 30–40 (expires sooner)
gpu.subtract(2, 30)
assert gpu.get_balance(30) == 5  # b has 1 left, a has 4
assert gpu.get_balance(40) == 5
assert gpu.get_balance(41) == 4  # b expired at t=41 (40 was inclusive)

# Out-of-order arrival
gpu = GPUCredit()
gpu.subtract(4, 30)              # arrives before any grant exists
gpu.add_credit('a', 4, 20, 30)   # valid 20–50
assert gpu.get_balance(20) == 4  # subtract hasn't happened yet at t=20
assert gpu.get_balance(30) == 0  # exact zero → 0, not None
assert gpu.get_balance(50) == 0  # still valid, still 0

# Negative balance → None
gpu = GPUCredit()
gpu.add_credit('openai', 10, 10, 30)
gpu.subtract(100, 20)
assert gpu.get_balance(10) == 10
assert gpu.get_balance(20) is None  # balance is −90 → None
```

---

## Edge cases to nail

- `subtract` arrives before any `add_credit` (out-of-order).
- Query at a time **before** any grant's activation.
- Query at a time **after** every grant has expired.
- One `subtract` drains across multiple grants ordered by expiration.
- Two grants with the **same expiration** — pick a tie-breaker and stick to it (insertion order or id are both fine).
- A grant whose expiration window doesn't cover the `subtract` timestamp: the subtract still drains other eligible grants; the expired grant is ignored.
- The query timestamp lands **exactly on** the expiration boundary — the grant is valid through `timestamp + expiration` **inclusive**.

---

## What an OpenAI interviewer is looking for

1. **Recognizing the replay model up front.** The out-of-order requirement + the variant note (*"a subtract continues to affect future balances"*) tell you that `subtract` should not mutate stored balances. Storing residuals on the grants will paint you into a corner when the next test sends out-of-order events. State the replay model out loud before you code.

2. **Sorted-by-expiration data discipline.** Whether you reach for `sortedcontainers.SortedList`, a heap with lazy deletion, or just `sorted(...)` on each replay (fine at this scale — it's a phone screen) — pick one and explain the trade-off.

3. **The `None`-vs-`0` discipline.** This is the silent-failure case the interviewer is probing. State the rule out loud: "Zero from real cancellation returns 0; only negative balance returns None." Then write a test for the exact-zero case.

4. **Active-grant check at query time.** `None` fires when **no grant is active at the query timestamp** — independent of the balance. A query at t=5 with the only grant activating at t=10 returns `None`, not `0`.

5. **Edge case readout before coding.** Even though this problem looks mechanical, OpenAI still rewards stating the corner cases upfront. The four-line list (out-of-order subtract, pre-grant query, post-expiration query, drain across grants) is what they want to hear.

6. **No over-engineering.** The interviewer hands you 6 test cases and stops. Don't reach for `SortedList` if `sorted()` per replay is enough at this scale. Optimize on follow-up, not preemptively.

---

## Follow-ups (don't peek until base works)

<details>
<summary>Click to expand</summary>

1. **Optimize replay cost.** Replay-from-scratch is `O(N)` per query, where N = total events. If queries dominate, can you maintain an incremental cache keyed by max-replayed-timestamp, invalidated when an out-of-order event arrives at an earlier timestamp? Discuss the invalidation logic — this is where the interviewer probes "layered optimization."

2. **Refund a grant.** Add `revoke(credit_id)` that removes a grant from the event log. Subsequent `get_balance` calls replay without it. Trivial if the event log is a list of records keyed by id.

3. **Transfers between accounts.** Generalize to a `GPUCreditMulti` with `(account_id, credit_id)` keys. Subtract drains within an account only.

4. **Concurrent grants and subtracts** — what locking strategy works? `subtract` and `add_credit` mutate the event log; `get_balance` reads it. RWLock or just a single mutex around the event-log mutation? Discuss the read-heavy assumption.

5. **Streaming/online interface** — instead of replaying every query, can you maintain the active-grant state incrementally? Caveat: out-of-order events break a pure online model. You'd need a watermark mechanism — only finalize state for timestamps below the watermark; queries above the watermark fall back to replay.

6. **Grant priority beyond expiration.** Some real billing systems prefer "burn the cheapest credit first" or "burn the credit from the customer's first purchase first." Generalize the priority function — does your code separate the comparator from the drain loop?

7. **Time-windowed reporting**: `total_consumed(start, end)` — how much credit was consumed between two timestamps. Trivial replay variant; just sum the subtract amounts in window.

8. **Partial expiration**: a grant has a per-day burn cap. Modeling this changes the subtract loop into a per-grant cap check before draining.

</details>

---

## Honest difficulty note

**The mechanical part is easy IF you've internalized the replay model.** ~30 lines of code. The hard parts are:

- **The `None`-vs-`0` rule.** Most candidates write `if balance == 0: return None` and fail the exact-zero test.
- **The "no active grant" `None` rule.** Distinct from the negative-balance `None` rule. Query at t=5 before any grant activates → `None`, not `0`.
- **Ordering the event log by `timestamp` for replay.** `add_credit` and `subtract` arrive in arbitrary order, but replay must visit them in `timestamp` order.
- **"Earliest expiring first" with ties.** Pick a deterministic tie-breaker. Insertion order or id are both defensible.

**A strong attempt covers:**
- Replay model stated before coding.
- `None` rule split into two cases out loud.
- 6 test cases pass on first run, or one debug cycle.
- One follow-up answered with code or a credible sketch (typically: optimize replay cost or revoke).

**A failing attempt typically:**
- Stores residual balance on each grant and gets stuck when an out-of-order event arrives.
- Returns `None` for the exact-zero case.
- Returns `0` when no grant is active (should be `None`).
- Gets the inclusive-expiration off-by-one wrong (uses `<` instead of `<=`).
