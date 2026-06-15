"""Data Labeling Task Scheduler — see problem.md.

API:
    build_basic_schedule(t, m, h, k)    -> Optional[List[Assignment]]
    build_balanced_schedule(t, m, h, k) -> Optional[List[Assignment]]

Both return:
    None when k > t, or any of t/m/h <= 0.
    []   when k == 0.
    Otherwise a list of exactly h * k (task, model, human) tuples.

Hints (don't peek if you want a cold attempt):
- Part 1: each human just needs k distinct tasks. model can be 0 throughout.
- Part 2: per-task model balance at every prefix is automatic from
  task_seen[task] % m round-robin. (task, human) balance is free.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

Assignment = Tuple[int, int, int]  # (task, model, human)


def build_basic_schedule(
    t: int,
    m: int,
    h: int,
    k: int,
) -> Optional[List[Assignment]]:
    """Part 1: each human appears >= k times; (task, human) unique.

    No prefix-balance requirement.
    """
    if t <= 0 or m <= 0 or h <= 0 or k > t:
        return None
    if k == 0:
        return []
    res = []
    for human in range(h):
        for task in range(k):
            res.append((task, 0, human))
    return res

def build_balanced_schedule(
    t: int,
    m: int,
    h: int,
    k: int,
) -> Optional[List[Assignment]]:
    """Part 2: Part 1 + per-task model counts balanced at every prefix.

    Per-task (model) max - min <= 1 at every step.
    Per-task (human) balance is automatic from "(task, human) unique".
    Output length is exactly h * k.
    """
    if t <= 0 or m <= 0 or h <= 0 or k > t:
        return None
    if k == 0:
        return []

    schedule = []
    # how many times each model has been used on each task
    model_counts = [[0] * m for _ in range(t)]
    # which tasks each human has already reviewed
    human_done = [set() for _ in range(h)]

    for human in range(h):
        for _ in range(k):
            # 1) pick the first task this human hasn't done
            task = None
            for candidate in range(t):
                if candidate not in human_done[human]:
                    task = candidate
                    break

            # 2) pick the model with the lowest count on this task
            counts = model_counts[task]
            best_model = 0
            for model in range(m):
                if counts[model] < counts[best_model]:
                    best_model = model

            # 3) commit
            schedule.append((task, best_model, human))
            model_counts[task][best_model] += 1
            human_done[human].add(task)

    return schedule


