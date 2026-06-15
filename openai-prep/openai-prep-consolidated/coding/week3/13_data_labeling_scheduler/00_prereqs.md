# Prereqs — Data Labeling Task Scheduler

Estimated prep time: **30-45 min**. There's no advanced data structure here — the trap is in *understanding the constraint*, not implementing it. Most candidates over-engineer.

Three things to internalize:

1. **What "prefix balance" actually means** — per-task, not global.
2. **The round-robin construction** — why `model = task_seen[task] % m` works.
3. **Greedy-with-counters as the brute-force fallback** — when the construction doesn't fit, just track counts and pick the min.

---

## Concept 1: What "prefix balance" means

**The constraint, spelled out**:

> For any prefix of the output schedule, for each task `x`, the counts of `(x, model=0), (x, model=1), …, (x, model=m-1)` satisfy `max − min ≤ 1`.

Three things easy to misread:

1. **Per task, not global.** You don't balance "model 0 vs model 1 across the whole schedule." You balance per-task. Task A's models can be `[2, 2, 2]` while task B's are `[5, 5, 4]` — both fine.
2. **Every prefix, not just the end.** If the final schedule ends balanced but at row 7 some task has counts `[3, 1, 1]`, you've already failed. The balance has to hold at *every* index as you walk down the list.
3. **Tasks that haven't appeared yet are vacuously balanced.** If task C never appears in the prefix, its counters are all zero — `max − min = 0`. Don't count empty tasks against yourself.

**Same rule for `(task, human)`** — but here it's free. Each `(task, human)` appears at most once (Part 1 constraint), so per-task human counts are all 0 or 1. `max − min ≤ 1` always.

**The only nontrivial balance to engineer is per-task model balance at every prefix.**

---

## Concept 2: The round-robin construction

**The key insight**: if each time a task is scheduled you assign the next model in a cycle `0, 1, ..., m-1, 0, 1, ...`, then after `c` total appearances of that task, each model has been used either `⌊c/m⌋` or `⌈c/m⌉` times. The difference is always 0 or 1.

```python
task_seen = [0] * t  # how many times each task has appeared
for u in range(h):           # human
    for r in range(k):       # round
        task = (u + r) % t
        model = task_seen[task] % m
        task_seen[task] += 1
        schedule.append((task, model, u))
```

Wait — that loop nesting matters for the prefix-balance argument. Reverse it:

```python
task_seen = [0] * t
for r in range(k):           # round (outer)
    for u in range(h):       # human (inner)
        task = (u + r) % t
        model = task_seen[task] % m
        task_seen[task] += 1
        schedule.append((task, model, u))
```

Both orderings satisfy the per-task model balance (the `mod m` argument is independent of the outer loop). But the **round-major order** has a nicer property: at the end of each round, every human has done exactly the same number of tasks. This makes the human-fairness invariant easy to read off and is the natural ordering for the Part 3 streaming variant ("one round = one day").

**Done when:** you can write this 8-line loop from a blank screen and explain why `mod m` is what makes the per-task model balance hold.

---

## Concept 3: Why each human sees `k` distinct tasks

The construction `task = (u + r) % t` for fixed `u`, `r ∈ {0, ..., k-1}` produces the values `u, u+1, ..., u+k-1` (mod `t`). These are distinct **iff `k ≤ t`** — which is guaranteed by the problem's precondition (`k > t` returns `None`).

So `(task, human)` uniqueness comes for free from the construction, and each human is in exactly `k` rows. Constraint 1 (`≥ k`) and constraint 4 (at most once) both hold.

**Done when:** you can prove uniqueness using "the cycle `(u+0), (u+1), …, (u+k-1)` mod `t` has `k` distinct values when `k ≤ t`."

---

## Concept 4: The brute-force greedy alternative

The problem note says "No complexity requirement, so brute force is encouraged." If you can't see the construction under pressure, the fallback is **greedy-with-counters**:

```python
from collections import Counter
task_model_count = Counter()  # (task, model) -> count
task_human_count = Counter()  # (task, human) -> count

# at each step: find the (task, model, human) that's:
# - human still needs more tasks (count < k)
# - (task, human) not yet used
# - (task, model) count minimizes the per-task model spread
```

This works but is `O(h·k · t·m·h)` to build. Fine at interview scale, ugly to write. Lead with the construction unless time pressure forces you to fall back.

**Done when:** you can articulate "the greedy is a safety net, but the construction is `O(h·k)` and cleaner."

---

## What to clarify on the call

Constraints differ between loops. Before you code, ask:

1. **Is Part 1 just the count+uniqueness rules, or does it also require prefix balance?** The spec says Part 1 ignores prefix balance, but interviewers wobble — confirm.
2. **Does prefix-balance hold over all `(task, model)` globally, or per-task?** The canonical answer is per-task. Re-state it back.
3. **What does "balance" mean for tasks that don't appear yet in the prefix?** Vacuously balanced (all-zero counters) — confirm.
4. **Part 3 streaming: one task per human per day, or per round?** Synonyms in the spec; nail it down.

Three open questions in 60 seconds beats coding the wrong problem.

---

## Recall template — type this from a blank screen

If you can get this in <3 minutes, you're ready.

```python
from typing import List, Optional, Tuple

Assignment = Tuple[int, int, int]  # (task, model, human)


def build_basic_schedule(
    t: int, m: int, h: int, k: int,
) -> Optional[List[Assignment]]:
    if t <= 0 or m <= 0 or h <= 0 or k < 0 or k > t:
        return None if (t <= 0 or m <= 0 or h <= 0 or k > t) else []
    if k == 0:
        return []
    schedule: List[Assignment] = []
    for u in range(h):
        for r in range(k):
            schedule.append(((u + r) % t, 0, u))
    return schedule


def build_balanced_schedule(
    t: int, m: int, h: int, k: int,
) -> Optional[List[Assignment]]:
    if t <= 0 or m <= 0 or h <= 0 or k < 0 or k > t:
        return None if (t <= 0 or m <= 0 or h <= 0 or k > t) else []
    if k == 0:
        return []
    task_seen = [0] * t
    schedule: List[Assignment] = []
    for r in range(k):                     # round-major: full round per day
        for u in range(h):                 # human within the round
            task = (u + r) % t
            model = task_seen[task] % m
            task_seen[task] += 1
            schedule.append((task, model, u))
    return schedule
```

---

## Suggested schedule

| Session | What |
|---------|------|
| Session 1 (20 min) | Read this doc + `problem.md`. Type the recall template from blank 2x. |
| Session 2 (35 min) | Cold attempt under timer. `timer started, 35 min`. |
| Session 3 (20 min) | `review mode`. Walk through `interviewer_notes.md`. |

When you can type the recall template cold in under 3 minutes and articulate "per-task model balance via mod m" out loud, set a **35-min timer** and open `problem.md`.
