# Interviewer notes — GPU Credit System

Read this **after** your attempt. Spoilers throughout.

---

## Reference solution

```python
import heapq


class GPUCredit:
    def __init__(self) -> None:
        # Flat event log. Out-of-order arrival means we cannot mutate
        # state incrementally — we replay on every query.
        self._events: list[tuple[int, str, object]] = []

    def add_credit(
        self,
        credit_id: str,
        amount: int,
        timestamp: int,
        expiration: int,
    ) -> None:
        self._events.append((timestamp, 'add', (credit_id, amount, expiration)))

    def subtract(self, amount: int, timestamp: int) -> None:
        self._events.append((timestamp, 'sub', amount))

    def get_balance(self, timestamp: int) -> int | None:
        grants: dict[str, list] = {}      # cid -> [remaining, start, end]
        heap: list[tuple[int, str]] = []  # min-heap of (end, cid)
        balance = 0
        has_active = False

        for ts, kind, payload in sorted(self._events, key=lambda x: x[0]):
            if ts > timestamp:
                break
            if kind == 'add':
                cid, amount, expiration = payload
                end = ts + expiration
                grants[cid] = [amount, ts, end]
                balance += amount
                heapq.heappush(heap, (end, cid))
                # ts <= timestamp is guaranteed by the break above,
                # so start <= timestamp is automatic; just check end.
                if end >= timestamp:
                    has_active = True
            else:
                amount = payload
                # Drain soonest-expiring active grant first.
                while amount > 0 and heap:
                    end, cid = heapq.heappop(heap)
                    if end < ts or grants[cid][0] == 0:
                        continue                             # expired or drained
                    take = min(grants[cid][0], amount)
                    grants[cid][0] -= take
                    amount -= take
                    balance -= take
                    if grants[cid][0] > 0:
                        heapq.heappush(heap, (end, cid))     # partial drain
                # Anything left undrained drives the balance negative.
                balance -= amount

        if not has_active:
            return None
        if balance < 0:
            return None
        return balance
```

That's it. ~40 lines.

--- 

## Why this is the shape it is

### Why a flat event log?

Out-of-order arrival kills any incremental scheme. If you store residuals on individual grants and someone hands you `add_credit('b', 3, 25, 5)` *after* you've already processed a `subtract(2, 30)`, you'd have to undo and reapply. Replay is simpler and at this scale (≤ a few hundred events) costs nothing.

### Why sort the events on every query?

Because new events can arrive at timestamps earlier than the current max. You can't pre-sort once and append in order. Alternatives:

- Insert with `bisect.insort` — `O(N)` per insert, `O(N)` per query (one pass). Same asymptote.
- Keep a `SortedList` — `O(log N)` insert. Marginally faster, requires the import.
- Sort each query — `O(N log N)` per query. Crudest, but `N` is tiny.

**Lead with `sorted()` per query.** Optimize on follow-up.

### Why a min-heap keyed by `end` for the drain?

The drain order is "soonest-expiring first." That's a priority-queue access pattern — pop the min of `end`, drain, repeat. Once you recognize the shape, a min-heap on `end` is the textbook fit:

- `heappush(heap, (end, cid))` on every `'add'`: O(log G).
- `heappop` returns the soonest-expiring active candidate: O(log G).
- Lazy deletion: when you pop and the entry is expired (`end < ts`) or drained (`remaining == 0`), just `continue` and pop the next one. No active bookkeeping to remove drained grants from the heap.

The alternative — `sorted()` of eligible grants per subtract — is `O(K log K)` per subtract where K = currently-tracked grants. The heap collapses that to `O(log G)` per heap op. Same asymptote per query overall (still dominated by `sorted(self._events)`), but a much tighter constant factor on the inner loop, and it generalizes — this is the structure interviewers expect from anyone fluent in priority problems (LC 253 Meeting Rooms II, LC 1834 Single-Threaded CPU, LC 218 Skyline).

### Why pop-decide-maybe-push-back instead of peek-and-mutate?

Two patterns work:

- **Peek-mutate**: `heap[0]` to look at the top, mutate `grants[cid][0]` in place, only `heappop` when fully drained. Fewer heap ops, but the control flow has three pop sites and a peek — harder to read fast.
- **Pop-decide-push-back** (what we use): always `heappop` at the top of the loop, `continue` if the entry's stale, drain otherwise, `heappush` back only if there's remaining. One pop site, one push site, one combined skip check.

Peek-mutate is marginally faster (no push-back on partial drains). Pop-decide is much easier to type and reason about under pressure. Take the cleaner one.

### Why two distinct `None` cases?

The spec defines two collapse rules:

1. **No active grant at the query time** — even with a positive replayed balance, you haven't actually got anything to spend, so the system says `None`.
2. **Negative balance** — over-burn from out-of-order or oversized subtracts. Real failure case; `None`.

A balance of **exactly zero with an active grant** is `0`, not `None`. This is the trap. The grant exists, it's just been precisely cancelled. Real-world analogue: an active billing window with a zero balance is still an active window.

The minority variant note in the source mentions some older framings collapsed zero to `None` in the keyed variant. Clarify at the start; modern canonical is `0`.

### Why one merged `grants` dict instead of separate `remaining` and `grants`?

Both are keyed by `credit_id`; splitting them was leftover habit (separating "what the grant is" from "what's left of it"). The list-as-value form `[remaining, start, end]` lets you mutate `remaining` in place without reassigning. If you don't like magic indices like `grants[c][2]` for the end, swap to a `@dataclass` — same shape, named fields.

### Why track `has_active` inline instead of looping at the end?

Every `'add'` event we process has `ts <= timestamp` (the `if ts > timestamp: break` guarantees it), so `start <= timestamp` is automatic. The only remaining check is `ts + expiration >= timestamp` — flip the flag right there in the add branch. Drops the final O(G) walk and keeps the function single-pass.

Drained grants still count as active for this check (the spec defines "active" as "window contains timestamp," not "remaining > 0"), so the inline test correctly doesn't look at `remaining`.

### Why keep expired grants in the dict during replay?

The eligibility check `start <= ts <= end and remaining > 0` filters them naturally during the drain. Pruning them out adds bookkeeping for no measurable win at interview scale.

---

## Honest weaknesses to acknowledge

1. **`O(N log N)` per query is wasteful if `get_balance` is called often.** Mitigation: cache the replay result keyed by `(max_event_ts_seen, query_time)`, invalidate when an event arrives at a timestamp ≤ max-seen. The interviewer often probes here.

2. **Heap entries for drained grants stay until they reach the top.** Lazy deletion is fine at this scale but means the heap can grow to N pushes total. If memory matters, switch to a `SortedList` keyed by `(end, cid)` and `.remove()` drained entries actively.

3. **No tie-breaker spec for grants with identical expirations.** This solution falls back to dict insertion order through `sorted()`'s stable sort. Document the choice if the interviewer asks.

4. **No `revoke`.** If the system needs grant cancellation, you'd add a `revoke(credit_id)` that filters the event log. Straightforward extension.

5. **No watermark/online interface.** Pure replay model — every query touches every event. Fine here; would need rework for high-volume systems.

---

## Self-grading against the OpenAI rubric

| Axis | Grade | Notes |
|------|-------|-------|
| Practical problem-solving | A | Replay model is the right call given out-of-order. Stated up front, not retrofitted. |
| Edge case discipline up front | A | Four-line corner-case list before coding: pre-grant query, post-expire query, out-of-order subtract, drain across grants. |
| Layered optimization | A- | Min-heap on `end` for the inner drain — recognizes priority-queue shape. Cache + watermark is the next follow-up if 1M queries. |
| Depth in Python internals | C | This problem doesn't probe internals heavily. Show off `sorted()` stability if asked about tie-breakers. |
| Targeted optimization under follow-up | A- | "How would you handle 10M events?" → cache invalidation by watermark. "How would you handle concurrent subtracts?" → single mutex around event-log mutation, RWLock if reads dominate. |
| Test quality | A | Tests split the `None` rule into its two distinct cases; tests cover out-of-order; tests cover drain-across-grants. |

---

## The probe an interviewer will run

**Probe 1: "If `get_balance(50)` returns 0, what does that mean?"**
- Correct answer: there's an active grant at t=50, and after replaying all events up to t=50 the balance is exactly 0. Could mean (a) no grants have been used and an empty grant was issued, (b) a grant was issued and an equal subtract cancelled it, or (c) multiple grants and subtracts net to 0.
- Wrong answer: "no balance" — that's `None`.

**Probe 2: "If I call `get_balance(50)` and then `add_credit('z', 5, 30, 100)`, does the first answer change?"**
- Correct answer: the first answer is a snapshot; the second `add_credit` is in the past relative to t=50 (activates at t=30), so a *new* call to `get_balance(50)` would include it. This is why the replay model matters.

**Probe 3: "Optimize for 1M events, 1M queries."**
- Correct answer: cache the replay state keyed by max-event-timestamp; invalidate when an event arrives at a timestamp ≤ current max. Most queries become incremental against the cached state.
- Follow-up: "What if events arrive at strictly increasing timestamps?" → drop the cache invalidation, maintain a single rolling state; queries are `O(1)` against the most recent snapshot.

**Probe 4: "Concurrency model — two threads call `subtract` simultaneously."**
- Correct answer: mutex around the event-log mutation. Reads (`get_balance`) can be lock-free if you swap the event log atomically or use an RWLock. The replay itself reads a snapshot — safe by construction if the snapshot is immutable.

---

## Common candidate mistakes

1. **Mutating residual amounts on grants directly** during `subtract`. Works on the example, breaks on out-of-order.
2. **Returning `None` for exact zero.** Misreading the spec — only negative balance collapses to `None`.
3. **Returning `0` when no grants are active.** Reverse of the above — the rule says "no active grant → `None`."
4. **Forgetting inclusive expiration.** `<=` is correct, not `<`. The spec says "valid through `timestamp + expiration` INCLUSIVE."
5. **Draining grants that expired before the subtract.** Subtract at t=30 should not touch a grant that ended at t=20, even if the grant has residual. The expired-grant burn is silently absorbed by the system → negative balance.
6. **Comparing `balance` before checking active-grant status.** A balance of 0 from "no grants exist yet" should still hit the no-active-grant `None` path, not the exact-zero `0` path. The order in `get_balance` matters.

---

## Follow-up sketches

### Revoke a grant

```python
def revoke(self, credit_id: str) -> None:
    self._events = [
        e for e in self._events
        if not (e[1] == 'add' and e[2][0] == credit_id)
    ]
```

`O(N)` to revoke; replays then exclude the grant naturally.

### Cache with watermark invalidation

```python
class GPUCredit:
    def __init__(self):
        self._events = []
        self._sorted_until = -1        # max ts where order is finalized
        self._cache = None             # cached state up to _sorted_until

    def _record(self, ts, ev):
        self._events.append((ts, *ev))
        if ts <= self._sorted_until:
            self._cache = None         # out-of-order; invalidate
        # otherwise: cache stays valid; new event can be applied incrementally
```

Cache invalidation is the hard part — interviewer will probe whether your invalidation rule is sound. "Did an event arrive earlier than the cache's high-water mark?" is the right invariant.

### Concurrent subtracts

```python
import threading
class GPUCredit:
    def __init__(self):
        self._events = []
        self._lock = threading.Lock()

    def subtract(self, amount, timestamp):
        with self._lock:
            self._events.append((timestamp, 'sub', amount))
```

Reads can grab a snapshot of `self._events` under the lock, then replay outside it — the replay reads a list slice, which is safe once captured.

---

## Sidebar: the same pattern in LC 218 (Skyline)

Cross-reference. The GPU drain loop and the LC 218 sweep are structurally the same animal: walk events in time order, maintain a heap over the active set, lazy-pop stale entries off the top. Spelling them out side-by-side makes the pattern click — if you see one in an interview, you should see the other.

The cleanest LC 218 form uses an event list (each building → one start event + one end marker), no separate "critical xs" collection:

```python
import heapq
from typing import List

class Solution:
    def getSkyline(self, buildings: List[List[int]]) -> List[List[int]]:
        # Two events per building: a start (carries -height, end_x) and
        # an end marker (just an x where we need to tick the loop past).
        events = []
        for left, right, height in buildings:
            events.append((left, -height, right))   # start
            events.append((right, 0, 0))             # end marker

        events.sort()

        heap = []
        result = []
        prev_max = 0

        for x, neg_h, right in events:
            if neg_h < 0:                            # start event → push
                heapq.heappush(heap, (neg_h, right))

            while heap and heap[0][1] <= x:          # lazy-pop expired
                heapq.heappop(heap)

            current_max = -heap[0][0] if heap else 0

            if current_max != prev_max:
                result.append([x, current_max])
                prev_max = current_max

        return result
```

**Concept-by-concept mapping:**

| GPU credit | LC 218 Skyline |
|---|---|
| `self._events` sorted by `ts` | `events` sorted by `x` |
| Heap of `(end, cid)`, min on `end` | Heap of `(-height, end_x)`, max on `height` |
| Drain consumes from soonest-expiring | Skyline shows tallest-active |
| Lazy delete: drained (`remaining == 0`) or expired (`end < ts`) | Lazy delete: expired (`end_x <= x`) |
| Emit happens implicitly via balance | Emit only when `current_max != prev_max` |
| `has_active` flag tracks if any grant covers `timestamp` | Skyline DOES drop to 0 between buildings; no equivalent gate |

**Why this matters for the GPU credit interview:**

If the interviewer asks "have you seen this pattern before?" — naming LC 218 (and LC 1834, LC 253) signals that you recognize the priority-queue-over-active-set shape as reusable, not a one-off. That's the difference between "got the problem" and "understand the technique."

---

## When you're done

If you cleared the 6 spec test cases plus the `None`-vs-`0` discipline tests in under 25 minutes, that's a passing phone screen. If you also articulated the replay model out loud before coding and answered probe 3 with cache invalidation, that's a strong signal toward onsite.
