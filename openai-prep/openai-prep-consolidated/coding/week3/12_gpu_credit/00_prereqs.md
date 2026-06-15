# Prereqs — GPU Credit System

Estimated prep time: **30-45 min** if you've already done time-based KV (week1/03). The architecture is closely related: event log + replay.

Three things to internalize before you attempt:

1. **The replay model** — why this problem demands it (out-of-order events) and what it costs.
2. **Sorted-by-expiration access** — `SortedList`, heap with lazy delete, or `sorted()`-per-replay. Pick one.
3. **The `None`-vs-`0` discipline** — the silent-failure case the interviewer is probing.

---

## Concept 1: The replay-from-scratch model

**What you're learning:** when the problem says "events can arrive out of order," your storage layer should be a flat event log, and reads should re-derive state by replaying the log in timestamp order. Don't mutate residual state on individual grants.

**Why replay, not incremental mutation:**

Imagine you stored residual balance on each grant:
```python
self.grants['a'] = {'amount_left': 4, 'start': 20, 'end': 60}
gpu.subtract(2, 30)
# tempting: self.grants['a']['amount_left'] -= 2
```

Now an out-of-order event arrives:
```python
gpu.add_credit('b', 3, 25, 5)  # valid 25–30, expires before 'a'
```

Grant `b` should have absorbed the subtract at t=30 (it expires sooner). But you already mutated `a`. To fix it, you'd have to undo the mutation on `a` and re-apply to `b`. That's replay, but harder. Just store events and replay.

**The shape:**

```python
class GPUCredit:
    def __init__(self):
        self.events = []  # list of (timestamp, kind, payload) tuples

    def add_credit(self, credit_id, amount, timestamp, expiration):
        self.events.append((timestamp, 'add', (credit_id, amount, expiration)))

    def subtract(self, amount, timestamp):
        self.events.append((timestamp, 'sub', amount))

    def get_balance(self, query_time):
        # replay every event with ts <= query_time, in ts order, then sum
        ...
```

**The cost:** each `get_balance` is `O(N log N)` if you re-sort the event log every call (or `O(N)` if you keep it sorted on insert). At interview scale (6 test cases, <100 events), this is fine. If they push on performance in the follow-up, you discuss caching with watermark invalidation.

**Done when:** you can articulate "I'm storing events, not state, because events arrive out of order and replays are cheap at this scale."

---

## Concept 2: Sorted-by-expiration access

**What you're learning:** the drain loop needs to walk active grants in expiration order, soonest first. Three options:

### Option A: `sortedcontainers.SortedList`

```python
from sortedcontainers import SortedList
active = SortedList(key=lambda g: g['expire_at'])
```

`O(log N)` insert, `O(1)` pop-min by index. Best ergonomics. Available in OpenAI's environment per recent reports — but if you don't know whether it's available, fall back to one of the others.

### Option B: Min-heap on `(expire_at, insertion_order, grant)`

```python
import heapq
heapq.heappush(heap, (expire_at, ins_order, grant))
```

`O(log N)` push, `O(log N)` pop-min. `insertion_order` breaks ties deterministically (compares before falling through to the dict, which doesn't compare). Lazy deletion: when a grant's remaining amount is zero, leave it on the heap; skip it when you encounter it next.

### Option C: `sorted()` per replay

```python
for e in sorted(self.events, key=lambda x: x[0]):  # by timestamp
    ...
# inside the drain, sort active grants by expire_at fresh each subtract
```

`O(N log N)` per query. Crude but legitimate at this scale. **Lead with this** if you're not sure what's available — it always works.

**The lead-with-simplest rule:** open with `sorted()` per replay, then offer "if you want this fast under load, swap to SortedList or a heap." Don't lead with the optimization.

**Done when:** you can write the drain loop in any of these three forms in <2 minutes.

---

## Concept 3: The drain loop — earliest expiring first

**What you're learning:** consume from the grant expiring soonest. Span multiple grants if needed. Track per-grant remaining amount only during the replay (not persisted on the grant object).

```python
def replay(self, query_time):
    # Build per-event grant state from the log, ts-ordered.
    remaining = {}  # credit_id -> int remaining
    grants = {}     # credit_id -> (start, end)
    balance = 0

    for ts, kind, payload in sorted(self.events, key=lambda x: x[0]):
        if ts > query_time:
            break
        if kind == 'add':
            cid, amount, expiration = payload
            grants[cid] = (ts, ts + expiration)
            remaining[cid] = amount
            balance += amount
        else:  # sub
            amount = payload
            # drain from grants active at `ts`, soonest-expiring first
            active = []
            for cid, (start, end) in grants.items():
                if start <= ts <= end and remaining[cid] > 0:
                    active.append(cid)
            active.sort(key=lambda c: grants[c][1])

            for cid in active:
                take = min(remaining[cid], amount)
                remaining[cid] -= take
                amount -= take
                balance -= take
                if amount == 0:
                    break
            # if amount > 0 still, balance goes negative — that's allowed
            balance -= amount

    return balance, remaining, grants
```

**The key trap:** the drain only sees grants whose `[start, end]` window contains the subtract's timestamp. A grant that expired before the subtract is **not** eligible; the subtract goes negative against the system, not against expired grants. Same for grants that activate after.

**Done when:** you can trace the example with grants `a` (4@20-60) and `b` (3@30-40) and subtract `2@30` and arrive at `a=4, b=1, balance=5`.

---

## Concept 4: The `None`-vs-`0` discipline

**What you're learning:** `get_balance(t)` collapses to `None` in two distinct cases. Conflating them or missing one is the interviewer's probe.

```python
def get_balance(self, query_time):
    balance, remaining, grants = self.replay(query_time)

    # Case 1: no grant is active at query_time → None
    has_active = False
    for start, end in grants.values():
        if start <= query_time <= end:
            has_active = True
            break
    if not has_active:
        return None

    # Case 2: replayed balance is negative → None
    if balance < 0:
        return None

    # Exact zero with an active grant → 0, not None
    return balance
```

**Two questions to ask out loud at the interview:**

1. *"If the only grant activates at t=10 and I query at t=5, the answer is `None`, right? Not `0`?"* — Yes.
2. *"If a grant of 10 is fully cancelled by a subtract of 10, query returns `0`, not `None`?"* — Yes.

The minority-variant note in the spec mentions some framings collapse zero to `None`. **Clarify before coding** — the modern canonical answer is `0` for exact zero.

**Done when:** you have a test for each of these four cases:
- Active grant, balance > 0 → integer.
- Active grant, balance == 0 → `0`.
- Active grant, balance < 0 → `None`.
- No active grant → `None`.

---

## Recall template — type this from a blank screen

If you can get this in <3 minutes, you're ready to attempt the problem cold.

```python
class GPUCredit:
    def __init__(self):
        self.events = []  # (ts, kind, payload)

    def add_credit(self, credit_id, amount, timestamp, expiration):
        self.events.append((timestamp, 'add', (credit_id, amount, expiration)))

    def subtract(self, amount, timestamp):
        self.events.append((timestamp, 'sub', amount))

    def get_balance(self, query_time):
        remaining = {}
        grants = {}  # cid -> (start, end)
        balance = 0
        for ts, kind, payload in sorted(self.events, key=lambda x: x[0]):
            if ts > query_time:
                break
            if kind == 'add':
                cid, amount, exp = payload
                grants[cid] = (ts, ts + exp)
                remaining[cid] = amount
                balance += amount
            else:
                amount = payload
                active = []
                for cid, (start, end) in grants.items():
                    if start <= ts <= end and remaining[cid] > 0:
                        active.append(cid)
                active.sort(key=lambda c: grants[c][1])

                for cid in active:
                    take = min(remaining[cid], amount)
                    remaining[cid] -= take
                    amount -= take
                    balance -= take
                    if amount == 0:
                        break
                balance -= amount  # remaining unmet drain goes negative

        has_active = False
        for start, end in grants.values():
            if start <= query_time <= end:
                has_active = True
                break
        if not has_active:
            return None
        if balance < 0:
            return None
        return balance
```

---

## Suggested schedule

| Session | What |
|---------|------|
| Session 1 (20 min) | Read this doc. Type the recall template from blank 2x. |
| Session 2 (35 min) | Cold attempt under timer. `timer started, 35 min`. |
| Session 3 (20 min) | `review mode`. Walk through `interviewer_notes.md`. |

When you can type the recall template cold in under 3 minutes and articulate the `None`-vs-`0` rule out loud, you're ready. Set a **35-min timer** and open `problem.md`.
