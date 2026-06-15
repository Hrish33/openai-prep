# Problem 13: Data Labeling Task Scheduler

**Prereqs:** Skim `00_prereqs.md` if "prefix balance" doesn't immediately mean "per-task, every-step model count spread ≤ 1." That's the entire problem.

**Time budget:** 45-60 min (onsite coding); 30-35 min for Part 1 alone (phone screen).
**Source:** OpenAI onsite + phone screen, last seen 2026-05-12. Frequency: medium-high. Tied with infection-spread as the hottest "new question."
**Stage:** Phone screen (Part 1) → onsite coding (Parts 1+2 → Part 3 if time).

---

## The problem

You're scheduling work for a **data labeling platform**. There are:

- `t` **tasks** — pieces of data that need labeling
- `m` **models** — AI models that have already produced candidate labels for each task
- `h` **human labelers** — people who verify/correct what a model produced

You need to emit a **schedule**: a list of `(task, model, human)` triples. Each triple says *"human H reviews model M's labels for task T."*

The schedule must be **fair** under multiple lenses (see below).

---

## Required API

```python
from typing import List, Optional, Tuple

Assignment = Tuple[int, int, int]  # (task, model, human)


def build_basic_schedule(
    t: int, m: int, h: int, k: int,
) -> Optional[List[Assignment]]: ...


def build_balanced_schedule(
    t: int, m: int, h: int, k: int,
) -> Optional[List[Assignment]]: ...
```

### Return contract for both

- Returns `None` when `k > t` or any of `t, m, h <= 0`. The constraints are unsatisfiable.
- Returns `[]` when `k == 0`. Vacuously satisfied — no work to schedule.
- Otherwise returns a list of exactly `h * k` assignments.

---

## Part 1 — `build_basic_schedule`

Constraints to satisfy:

1. **Human quota.** Each human appears in **at least `k`** assignments.
2. **Task uniqueness.** No `(task, human)` pair appears twice — each human reviews each task at most once.

That's it. No model balance, no prefix balance. The simplest construction assigns `model = 0` for every row. It still passes Part 1.

**Why so easy?** Part 1 isolates the bookkeeping piece: pick `k` distinct tasks per human. Most candidates pass it in 5-10 minutes; the interviewer uses the remaining time on Part 2.

---

## Part 2 — `build_balanced_schedule`

All Part 1 constraints, plus:

3. **Per-task prefix balance over models.** For every task `x` and every prefix of the schedule:
   ```
   max_i  count_prefix(task=x, model=i)
   − min_i count_prefix(task=x, model=i)
   ≤ 1
   ```
4. **Per-task prefix balance over humans.** Same rule, with humans instead of models. *(This holds automatically given constraint 2 — counts are 0 or 1.)*

The schedule has length exactly `h * k` (no wasted rows).

### What "prefix balance" means — the trap

It is **per-task**, not global. You do not balance "model 0 vs model 1 across the whole schedule." You balance per-task: for task A, the counts of `(A, model=0), (A, model=1), …` differ by ≤ 1 at every prefix. Task B has its own independent counter.

It is **every prefix**, not just at the end. Walk down the schedule index by index — the invariant has to hold at every step, not just at row `h*k`.

Tasks that haven't appeared in the prefix yet are **vacuously balanced** (all-zero counters → `max − min = 0`).

---

## Examples

```python
# Part 1 — basic, no model balance required.
out = build_basic_schedule(t=4, m=2, h=3, k=2)
# 6 assignments. Every human appears ≥ 2 times.
# No (task, human) pair repeats. model=0 throughout is legal.
assert len(out) == 6
humans = [u for _, _, u in out]
assert all(humans.count(u) >= 2 for u in range(3))
assert len({(task, u) for task, _, u in out}) == 6  # all unique

# Part 2 — balanced. Same shape, but model counts on each task differ by ≤ 1 at every step.
out = build_balanced_schedule(t=4, m=2, h=3, k=2)
assert len(out) == 6
# At every prefix, for every task: max model count − min model count ≤ 1.

# Edge: k = 0 → empty schedule
assert build_basic_schedule(t=4, m=2, h=3, k=0) == []
assert build_balanced_schedule(t=4, m=2, h=3, k=0) == []

# Edge: k > t → unsatisfiable (cannot pick k distinct tasks per human)
assert build_basic_schedule(t=2, m=2, h=3, k=3) is None
assert build_balanced_schedule(t=2, m=2, h=3, k=3) is None
```

### Sanity-checking Part 2 by hand

For `(t=2, m=2, h=2, k=2)`:

```
Round 0: human 0 → task 0, model 0     (task 0 counter: 1 → model = 0%2 = 0)
         human 1 → task 1, model 0     (task 1 counter: 1 → model = 0%2 = 0)
Round 1: human 0 → task 1, model 1     (task 1 counter: 2 → model = 1%2 = 1)
         human 1 → task 0, model 1     (task 0 counter: 2 → model = 1%2 = 1)
```

After row 1: task 0 has model counts `[1, 0]`, spread = 1. ✓
After row 2: task 0 `[1, 0]`, task 1 `[1, 0]`. ✓
After row 3: task 0 `[1, 0]`, task 1 `[1, 1]`. ✓
After row 4: task 0 `[1, 1]`, task 1 `[1, 1]`. ✓

---

## Edge cases to nail

- `k == 0` → return `[]`. No work, but valid input.
- `k > t` → return `None`. Each human needs `k` distinct tasks; impossible.
- `t == 0`, `m == 0`, or `h == 0` → return `None`. Degenerate input.
- `k == t` → each human covers **every** task exactly once. Construction still works.
- `m > t * k / m` — meaning some models never appear on some tasks. The balance rule only constrains existing counters; a model that never appears on a task is fine.
- `m == 1` → trivial: every row has `model = 0`. Balance trivially holds.
- `h == 1` → one human does `k` tasks; one-row prefixes are always balanced.
- A model never appears on a given task (because the task is scheduled fewer than `m` times). The spread is still ≤ 1: counts are all 0 or all 1.

---

## What an OpenAI interviewer is looking for

1. **Clarify what "balance" means up front.** Before writing a single line, restate the constraint: *"per task, the model counts differ by at most 1 at every prefix — right?"* Three open questions in 60 seconds. The candidates who skip this and start coding the global-balance interpretation lose 20 minutes.

2. **Recognize the construction.** The `(u + r) mod t` rotation + `task_seen[task] mod m` round-robin is the canonical Part 2 answer. Strong candidates name "per-task round-robin" out loud. Weaker candidates write greedy-with-counters that works but takes 30+ minutes.

3. **Prove correctness verbally.** Two arguments:
   - *Task uniqueness*: human `u` visits tasks `u, u+1, …, u+k-1` mod `t` — `k` distinct values iff `k ≤ t`.
   - *Model balance*: after `c` appearances of task `x`, each model has been used `⌊c/m⌋` or `⌈c/m⌉` times.
   Don't hand-wave. The interviewer will probe.

4. **Edge case readout before coding.** Four-line list: `k=0`, `k>t`, degenerate sizes, `m=1`. Saying these out loud saves you from None-vs-`[]` confusion later.

5. **Don't over-engineer.** This is **O(h·k) and ~15 lines**. If you reach for a priority queue or backtracking, the interviewer is going to ask why. The construction is the answer.

6. **Test quality.** Write a `verify_balanced` helper that walks every prefix and asserts the invariant. Don't trust eyeballing.

---

## Follow-ups (don't peek until both parts work)

<details>
<summary>Click to expand</summary>

1. **Part 2-Plus: `(model, human)` also balanced.** Add: for every prefix, `(model, human)` pair counts also satisfy max − min ≤ 1 globally. *Significantly* harder — pairwise balance over three axes simultaneously. Solution sketch: extend to a Latin-square construction; rotate humans and models in coupled cycles.

2. **Part 3 streaming.** `build_streaming_schedule(initial_t, m, h, k)` returns an object with `add_task() -> int` (new task id) and `next_day() -> list[Assignment]`. Each day, ≤1 task per human, balance invariants extend across days. State: per-task model counter (persists), per-task human-seen set (persists), per-day human-used set (resets daily). Round-robin scheduling within the day.

3. **Prioritized humans.** Each human has a "want at least `k_i` tasks" with `k_i` varying. Construction generalizes: sum over `k_i` rows, route to humans round-robin weighted by `k_i`.

4. **Disallowed combinations.** Some `(task, model)` pairs are forbidden (model can't label that task). Falls back to the brute-force greedy: at each step pick the legal triple that maximizes balance.

5. **Validation as a separate API.** `is_valid_schedule(schedule, t, m, h, k) -> bool` that checks all constraints. The verifier is half the test suite anyway; expose it.

6. **Online insertions.** Given a partial valid schedule, append rows for an additional `k' < k` rounds without rebuilding. The construction supports it: keep the `task_seen` counters across calls, just continue rounds.

7. **What if `k > t`?** Spec says return `None`. Realistic alternative: relax "each human reviews each task at most once" and instead say "each human reviews each task at most `⌈k/t⌉` times." Solution: schedule in `⌈k/t⌉` super-rounds.

</details>

---

## Honest difficulty note

**Looks like a hard combinatorial problem, is actually ~15 lines IF you see the construction.** The trap is interpretation:

- **The "every prefix" clause feels like it needs backtracking or a priority queue.** It doesn't. Round-robin auto-satisfies it.
- **Candidates over-interpret "balance."** Some try to balance globally across all tasks; some try to balance `(model, human)` in Part 2 (that's Part 2-Plus).
- **The greedy-with-counters fallback works** but eats your time budget. Worth writing as a backup, not the lead.

**A strong attempt covers:**
- Restates the constraint precisely before coding (per-task, every-prefix).
- Writes Part 1 in <8 minutes.
- Identifies the round-robin construction within 5 minutes of seeing Part 2.
- Verifies prefix balance with a helper, not by eyeball.
- Names Part 3 streaming as "same construction, persist `task_seen` across days."

**A failing attempt typically:**
- Codes a greedy that balances globally instead of per-task.
- Misses that `(task, human)` balance is free.
- Spends 20 minutes on backtracking or constraint propagation.
- Returns `None` for `k == 0` (should be `[]`).
- Returns `[]` for `k > t` (should be `None`).
