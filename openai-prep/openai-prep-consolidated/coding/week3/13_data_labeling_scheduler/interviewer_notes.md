# Interviewer notes — Data Labeling Task Scheduler

Read this **after** your attempt. Spoilers throughout.

---

## Reference solution

```python
from typing import List, Optional, Tuple

Assignment = Tuple[int, int, int]  # (task, model, human)


def _bad_input(t: int, m: int, h: int, k: int) -> bool:
    return t <= 0 or m <= 0 or h <= 0 or k > t


def build_basic_schedule(
    t: int, m: int, h: int, k: int,
) -> Optional[List[Assignment]]:
    if _bad_input(t, m, h, k):
        return None
    if k == 0:
        return []
    # Each human picks k distinct tasks via a rotation.
    # model = 0 throughout — Part 1 doesn't constrain models.
    return [
        ((u + r) % t, 0, u)
        for u in range(h)
        for r in range(k)
    ]


def build_balanced_schedule(
    t: int, m: int, h: int, k: int,
) -> Optional[List[Assignment]]:
    if _bad_input(t, m, h, k):
        return None
    if k == 0:
        return []
    # Per-task counter: each time task x is scheduled, assign the
    # next model in round-robin order. After c appearances of x,
    # each model has been used floor(c/m) or ceil(c/m) times, so
    # max - min <= 1 at every prefix.
    task_seen = [0] * t
    schedule: List[Assignment] = []
    for r in range(k):                  # round-major: full round per day (Part 3 friendly)
        for u in range(h):
            task = (u + r) % t
            model = task_seen[task] % m
            task_seen[task] += 1
            schedule.append((task, model, u))
    return schedule
```

That's it. ~25 lines counting both functions and the guard.

---

## Why this is the shape it is

### Why does each human walk `(u + r) % t`?

Three things at once:

1. **`k` distinct tasks per human.** For fixed `u`, `r` runs through `0, 1, …, k-1`, so the task sequence is `u, u+1, …, u+k-1` mod `t`. These are `k` distinct values when `k ≤ t` — exactly the precondition.
2. **`(task, human)` uniqueness.** Falls out of the previous point: each `(task, u)` appears at most once.
3. **Human quota.** Each `u` appears in exactly `k` rows. Quota of `≥ k` is met with equality.

If `k > t`, no rotation works — by pigeonhole, you'd need to revisit a task. The spec says return `None`. (A real platform would handle this by relaxing constraint 4; the spec doesn't.)

### Why `model = task_seen[task] % m`?

This is the entire trick.

Fix any task `x`. The first time `x` is scheduled, `model = 0`. Second time, `model = 1`. The `m`-th time, `model = 0` again. After `c` total appearances:

```
model 0 used ceil(c/m) times if c % m > 0, else c/m
model i used floor(c/m) or ceil(c/m) for all i
```

The spread between max and min is **always 0 or 1**. The invariant holds at every prefix because `task_seen[x]` is incremented monotonically, one row at a time.

### Why round-major (`for r: for u:`) instead of human-major (`for u: for r:`)?

Both orderings satisfy per-task model balance — the `mod m` argument is independent of the outer loop.

Round-major has nicer properties:

1. **Streaming-friendly.** Part 3 ("one task per human per day") maps cleanly: round `r` = day `r`. Same construction, persist `task_seen` across calls.
2. **Human progress is uniform.** After `r` full rounds, every human has done exactly `r` tasks. Easier to read off the human-quota invariant.
3. **Even tasking under partial completion.** If the schedule is cut off mid-row (say, machine crash), every human has nearly the same workload.

Human-major would let one human run ahead of the others. Both are correct; round-major is preferred.

### Why is `(task, human)` balance free?

Constraint 4 says each `(task, human)` pair appears at most once. Per-task human counts are therefore each 0 or 1. `max - min ≤ 1` holds trivially at every prefix — no construction work needed.

This is the line the interviewer probes: *"Why don't you need to balance humans per task?"* The answer is one sentence.

### Why brute-force greedy isn't the lead

A different valid approach: maintain three counters (`(task, model)`, `(task, human)`, `human_total`), and at each step pick the unused `(task, model, human)` that's still legal and minimizes the per-task model spread.

It works. It's `O(h·k · t·m·h)` to build. The construction is `O(h·k)`. The greedy is your safety net if you can't see the construction in 5 minutes — not your lead.

When asked "what's your time complexity," answer `O(h·k)` for the construction, and call out that the brute force is the fallback.

### Why guard `k > t` as `None` and `k == 0` as `[]`?

Both are corner cases the spec explicitly defines:

- `k > t` → unsatisfiable. By pigeonhole, no schedule can give each human `k` distinct tasks if there are only `t < k` tasks.
- `k == 0` → vacuously satisfied. No constraints to violate; output is empty.

Conflating these (returning `[]` for both, or `None` for both) is a common slip. The interviewer probes:

> *"What if k is zero?"* → `[]`.
> *"What if k is larger than t?"* → `None`.

State both rules before coding.

---

## Honest weaknesses to acknowledge

1. **Part 2-Plus (`(model, human)` balance) is not solved by this construction.** If the interviewer asks "now also balance across `(model, human)` globally," the rotation will repeat assignments — e.g., human 0 always gets model 0 first on every task. You'd need a Latin-square shift: `model = (task_seen[task] + u) % m` to decouple. State this honestly if asked, then attempt the shift.

2. **The schedule length is exactly `h*k`.** If the interviewer wants a longer schedule (e.g., "fill until every `(task, model)` pair is covered"), this construction stops early. Generalization: keep looping rounds until the coverage condition is met. Re-derive the precondition (`k > t` → unsat).

3. **No tie-breaker is exposed.** The `(u + r) % t` rotation pins a specific order. If the interviewer wants a randomized or shuffled order, you'd permute humans/tasks once at the top of the function and run the same construction on the permuted indices.

4. **The "per-task" interpretation is the canonical one but some interview reports use a global interpretation.** The spec note says to clarify on the call. If the interviewer means "global `(task, model)` balance across all rows," the construction still satisfies it (a stronger guarantee than needed), but the rationale shifts.

5. **No streaming variant implemented.** Part 3 is sketched as a follow-up but not built. If asked, the answer is: same construction, persist `task_seen` and `task_human_seen` across `next_day()` calls, and skip rows that would violate "≤1 task per human per day."

---

## Self-grading against the OpenAI rubric

| Axis | Grade | Notes |
|------|-------|-------|
| Practical problem-solving | A | Construction is `O(h·k)` and ~12 lines. Recognized the round-robin shape; didn't reach for backtracking. |
| Edge case discipline up front | A | Four-line list: `k=0`, `k>t`, degenerate sizes, `m=1`. None-vs-`[]` rule stated before coding. |
| Layered optimization | A- | Brute-force greedy is the natural fallback; named but not led with. Streaming variant sketched. |
| Depth in Python internals | B | Problem doesn't probe Python internals heavily. Comp-style list comp for Part 1 shows fluency. |
| Targeted optimization under follow-up | A | Part 3 streaming → "persist `task_seen`." Part 2-Plus → "Latin-square shift `(task_seen[task] + u) % m`." |
| Test quality | A | `_prefix_balanced` helper walks every prefix; `_basic_invariants` enforces quota, range, and uniqueness in one place. |

---

## The probe an interviewer will run

**Probe 1: "Why does the model balance hold at every prefix, not just at the end?"**
- Correct answer: `task_seen[x] % m` is incremented monotonically, one row at a time. After `c` appearances of task `x`, each model count is `⌊c/m⌋` or `⌈c/m⌉`. The spread is always 0 or 1. The invariant is maintained inductively: each new row increments exactly one `(x, model_i)` counter.
- Wrong answer: "because I sort at the end" — you don't sort, and sorting would break per-prefix balance.

**Probe 2: "Why don't you need to balance humans per task?"**
- Correct answer: constraint 4 forces `(task, human)` to be unique, so per-task human counts are each 0 or 1. Spread is ≤ 1 trivially.
- Wrong answer: "I balance them manually" — wasteful, the spec gives it to you free.

**Probe 3: "Add a Part 2-Plus: `(model, human)` also balanced globally. What changes?"**
- Correct answer: the current rotation pins `(u, model)` patterns — human 0 always sees model 0 on round 0. To decouple, shift: `model = (task_seen[task] + u) % m`. Now each human cycles through models in a different offset per task. Sketch a Latin-square style argument.
- Acceptable answer: "I'd fall back to greedy with three counters and check `(model, human)` spread at every step." Less elegant; works.

**Probe 4: "Part 3 — new tasks arrive each day, ≤1 per human per day. Streaming."**
- Correct answer: persist `task_seen` and a "today's humans used" set across `next_day()` calls. New tasks join the rotation when they arrive. Each call emits up to `h` rows. The per-task model balance is preserved because `task_seen` carries across days.

**Probe 5: "Concurrency — two threads call `next_day()` simultaneously."**
- Correct answer: mutex around the `task_seen` mutation and the per-day human set. Reads (schedule queries) can be lock-free if the schedule is appended to atomically.

**Probe 6: "What if `k > t`?"**
- Correct answer: return `None`. Pigeonhole — can't give each human `k` distinct tasks if `t < k`. Relaxed variant: allow repeats up to `⌈k/t⌉` times.

---

## Common candidate mistakes

1. **Coding global model balance instead of per-task.** Misreads the constraint. A schedule that balances "model 0 vs model 1 across all rows" is over-constrained and harder to build; the spec asks for per-task only.
2. **Reaching for backtracking or constraint propagation.** The construction is `O(h·k)`. Backtracking wastes 20 minutes.
3. **Manually balancing `(task, human)`.** It's free. The interviewer will ask why.
4. **Returning `[]` for `k > t` or `None` for `k == 0`.** Swapped corner-case returns.
5. **Mutating `task_seen` then resetting it per-round.** Resetting breaks the model balance across rounds. `task_seen` must persist for the whole schedule.
6. **Picking the model with the lowest *global* count instead of per-task count.** A `Counter()` keyed by `model` alone would give a globally-balanced (but per-task lopsided) schedule. Has to be keyed by `(task, model)` or stored as `[m]`-length list per task.
7. **Off-by-one in the rotation.** `(u + r) % t` vs `(u * k + r) % t` vs `(u + r * h) % t` — the first is right; the others either repeat tasks or skip them.

---

## Follow-up sketches

### Part 2-Plus: also balance `(model, human)`

```python
def build_doubly_balanced(t, m, h, k):
    if _bad_input(t, m, h, k):
        return None
    if k == 0:
        return []
    task_seen = [0] * t
    schedule = []
    for r in range(k):
        for u in range(h):
            task = (u + r) % t
            # Latin-square shift: each human sees a different model offset.
            model = (task_seen[task] + u) % m
            task_seen[task] += 1
            schedule.append((task, model, u))
    return schedule
```

The shift `+ u` decouples human-to-model pairing. Per-task model balance still holds (the increment is still by 1 per row); `(model, human)` is now spread out.

**Caveat**: doesn't guarantee strict global `(model, human)` balance — it just reduces correlation. A rigorous Part 2-Plus needs a real Latin-square or BIBD (balanced incomplete block design). State this honestly in the interview.

### Part 3: streaming schedule

```python
class StreamingScheduler:
    def __init__(self, t: int, m: int, h: int):
        self.m = m
        self.h = h
        self.task_seen: list[int] = [0] * t      # extends as tasks arrive
        self.task_human_seen: list[set] = [set() for _ in range(t)]
        self.day = 0

    def add_task(self) -> int:
        new_id = len(self.task_seen)
        self.task_seen.append(0)
        self.task_human_seen.append(set())
        return new_id

    def next_day(self) -> list[Assignment]:
        """Emit up to h rows, one per human, distinct tasks per human."""
        rows: list[Assignment] = []
        used_today: set[int] = set()
        t = len(self.task_seen)
        for u in range(self.h):
            # find a task this human hasn't seen, that's free today
            for offset in range(t):
                task = (u + self.day + offset) % t
                if task in used_today:
                    continue
                if u in self.task_human_seen[task]:
                    continue
                model = self.task_seen[task] % self.m
                self.task_seen[task] += 1
                self.task_human_seen[task].add(u)
                used_today.add(task)
                rows.append((task, model, u))
                break
        self.day += 1
        return rows
```

Per-task model balance carries across days (same `task_seen` counter). The streaming version handles "≤1 task per human per day" with the `used_today` set; the search loop ensures `(task, human)` uniqueness.

### Brute-force greedy

```python
from collections import Counter

def build_balanced_greedy(t, m, h, k):
    if _bad_input(t, m, h, k):
        return None
    if k == 0:
        return []
    schedule = []
    human_total = Counter()
    task_human = set()
    task_model = [[0] * m for _ in range(t)]

    for _ in range(h * k):
        best = None
        best_key = None
        for u in range(h):
            if human_total[u] >= k:
                continue
            for x in range(t):
                if (x, u) in task_human:
                    continue
                # pick the model with the lowest count on this task
                model = min(range(m), key=lambda i: task_model[x][i])
                key = (task_model[x][model], human_total[u])
                if best_key is None or key < best_key:
                    best_key = key
                    best = (x, model, u)
        if best is None:
            return None
        x, model, u = best
        schedule.append(best)
        task_model[x][model] += 1
        task_human.add((x, u))
        human_total[u] += 1
    return schedule
```

Slower (`O(h·k · h·t·m)`) but the natural fallback if the construction doesn't click. Worth knowing for the off-script follow-up where the construction doesn't generalize.

---

## Sidebar: why this problem is easier than it looks

Many candidates panic at "every prefix" and reach for a priority queue or backtracking. The insight that flips it: **the round-robin increment maintains the invariant by construction**. You're not searching; you're following a recipe that can't fall out of balance.

The same pattern appears in:

- **Round-robin load balancing** (web servers): per-backend request counts within ±1.
- **Scheduling fairness** (CFS in Linux): per-process runtime within ±1 of others.
- **Card dealing**: dealing one card at a time around the table keeps player hand sizes within ±1.

Once you've seen the pattern once, it shows up everywhere. The OpenAI interviewer is probing whether you recognize it on first sight or whether you blunder into backtracking.

---

## When you're done

If you cleared Part 1 in <10 minutes and Part 2 with `_prefix_balanced` passing in <25 minutes, that's a passing onsite coding round. If you also sketched Part 3 streaming and answered Probe 3 with the Latin-square shift, that's a strong signal toward hire.
