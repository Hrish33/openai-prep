# Interviewer Notes — Infection Spread

**Read this AFTER your timed attempt.** Reference implementations, bug patterns, and how the OpenAI rubric scores each part.

---

## Reference solutions

### Part 1 — basic multi-source BFS

```python
from collections import deque


def time_to_full_infection(grid: list[list[int]]) -> int:
    if not grid or not grid[0]:
        return 0

    rows, cols = len(grid), len(grid[0])
    q = deque()
    healthy = 0
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == 1:
                q.append((i, j))
            elif grid[i][j] == 0:
                healthy += 1

    if healthy == 0:
        return 0
    if not q:
        return -1

    days = 0
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    while q and healthy > 0:
        days += 1
        for _ in range(len(q)):
            i, j = q.popleft()
            for di, dj in dirs:
                ni, nj = i + di, j + dj
                if 0 <= ni < rows and 0 <= nj < cols and grid[ni][nj] == 0:
                    grid[ni][nj] = 1
                    healthy -= 1
                    q.append((ni, nj))

    return days if healthy == 0 else -1
```

This is your LC 994 code with the encoding flipped. Mutating the grid in-place IS safe here because the level-by-level loop (`for _ in range(len(q))`) bounds each tick — cells enqueued during a tick are at the next level. The implicit buffering does the work.

### Part 2 — immune walls

```python
def time_to_full_infection_with_immunity(grid: list[list[int]]) -> int:
    if not grid or not grid[0]:
        return 0

    rows, cols = len(grid), len(grid[0])
    q = deque()
    healthy = 0
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == 1:
                q.append((i, j))
            elif grid[i][j] == 0:
                healthy += 1
            # value 2 (immune) is silently skipped — not counted as target.

    if healthy == 0:
        return 0
    if not q:
        return -1

    days = 0
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    while q and healthy > 0:
        days += 1
        for _ in range(len(q)):
            i, j = q.popleft()
            for di, dj in dirs:
                ni, nj = i + di, j + dj
                # `== 0` naturally excludes immune (2); we only flip healthy.
                if 0 <= ni < rows and 0 <= nj < cols and grid[ni][nj] == 0:
                    grid[ni][nj] = 1
                    healthy -= 1
                    q.append((ni, nj))

    return days if healthy == 0 else -1
```

Differences from Part 1: two lines. The `healthy` counter only counts `0`s. The neighbor expansion already only flips `0`s, so immune (`2`) is naturally skipped. That's it.

If the interviewer pushes back with "isn't this almost identical to Part 1?" — yes, by design. The two functions could share a `_bfs_until_targets_consumed(grid, target_value)` helper, but introducing that abstraction live, on the clock, is more risky than the duplication is costly. Mention the refactor; don't perform it.

### Part 3 — recover-then-spread

```python
def time_to_stable_state(grid: list[list[int]], D: int) -> int:
    if not grid or not grid[0]:
        return 0

    rows, cols = len(grid), len(grid[0])
    active: set[tuple[int, int]] = set()
    infection_day: dict[tuple[int, int], int] = {}

    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == 1:
                active.add((i, j))
                infection_day[(i, j)] = 0

    if not active:
        return 0

    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    current_day = 0

    while active:
        current_day += 1

        # 1. RECOVER first — these cells do NOT spread this tick.
        just_recovered = [c for c in active if current_day - infection_day[c] >= D]
        for (i, j) in just_recovered:
            active.discard((i, j))
            grid[i][j] = 2

        # 2. SPREAD from the remaining active set — BUFFER the writes.
        newly_infected = set()
        for (i, j) in active:
            for di, dj in dirs:
                ni, nj = i + di, j + dj
                if 0 <= ni < rows and 0 <= nj < cols and grid[ni][nj] == 0:
                    newly_infected.add((ni, nj))

        # 3. APPLY — stamp infection_day on today's new infections.
        for (i, j) in newly_infected:
            grid[i][j] = 1
            infection_day[(i, j)] = current_day
            active.add((i, j))

    return current_day
```

The three things to defend in code review:

1. **Recover first.** A cell whose age has hit D shouldn't spread on the same tick. Recovery is processed before spread within the tick.
2. **`>= D`, not `> D`.** Infected on day 0 with D=2 → recovers on day 2. `2 - 0 >= 2` is true.
3. **Buffered writes for spread.** `newly_infected` is collected from a stable snapshot of `active`, then applied. If you mutated the grid mid-loop, you'd get same-tick cascades.

### Part 4A — threshold spread (active-set + vote count)

Same shape as Part 3: active set of infected cells, buffered writes. The new wrinkle is the **vote count** — each active cell contributes 1 vote to each healthy neighbor, then a healthy cell with `votes >= K` gets infected.

```python
from collections import defaultdict


def time_to_full_infection_threshold(grid: list[list[int]], K: int) -> int:
    if not grid or not grid[0]:
        return 0

    rows, cols = len(grid), len(grid[0])
    active = set()
    healthy = 0
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == 1:
                active.add((i, j))
            elif grid[i][j] == 0:
                healthy += 1

    if healthy == 0:
        return 0
    if not active:
        return -1

    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    days = 0

    while healthy > 0:
        days += 1

        # 1. VOTE — each active cell votes for its healthy neighbors.
        votes = defaultdict(int)
        for (i, j) in active:
            for di, dj in dirs:
                ni, nj = i + di, j + dj
                if 0 <= ni < rows and 0 <= nj < cols and grid[ni][nj] == 0:
                    votes[(ni, nj)] += 1

        # 2. DECIDE — healthy cells with >= K votes get infected this tick.
        newly_infected = []
        for cell, count in votes.items():
            if count >= K:
                newly_infected.append(cell)

        # 3. STUCK CHECK — no new infections and healthy cells remain.
        if not newly_infected:
            return -1

        # 4. APPLY — buffered writes, like Part 3.
        for (i, j) in newly_infected:
            grid[i][j] = 1
            active.add((i, j))
            healthy -= 1

    return days
```

Why active-set + vote-count instead of whole-grid snapshot:

- **Same shape as Part 3.** You already have the muscle memory: active set, iterate it, buffer writes. No new control flow to invent.
- **O(|active|) per tick, not O(rows × cols).** For a sparse grid the win is big; for a dense grid they're equivalent.
- **No snapshot copy.** The vote dict serves the same role — counts come from the *current* `active` set (which is the pre-tick world), then we apply after.

The "snapshot" framing in the prereqs doc is the textbook way to think about it (read the consistent old state, write the new state). The vote-dict implementation is the same idea expressed as "ask every active cell who they're voting for" rather than "scan every healthy cell and count their neighbors." Both correct.

### Part 4B — death countdown

Spec is fuzzy. **Clarify before coding** in the interview:
- Does a started countdown tick down unconditionally, or pause if neighbor count drops below K? (Default: unconditional.)
- Does a dead cell block spread (act like a wall), or just sit there? (Default: blocks — same as immune.)
- "days_to_end" = day of last change, or day after stability is reached? (Default: day of last change.)
- New 4th state for dead, or does it become healthy again? (Default: new state, value 3.)

```python
def time_to_end_with_death(grid: list[list[int]], K: int, N: int) -> tuple[int, int]:
    if not grid or not grid[0]:
        return 0, 0

    rows, cols = len(grid), len(grid[0])
    DEAD = 3

    active: set[tuple[int, int]] = set()
    death_countdown: dict[tuple[int, int], int] = {}
    deaths = 0

    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == 1:
                active.add((i, j))

    if not active:
        return 0, 0

    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    days = 0
    last_change_day = 0

    while True:
        days += 1
        any_change = False

        # 1. DEATH-DECAY — tick countdowns; kill those that hit 0.
        just_died = []
        for cell in list(death_countdown):
            death_countdown[cell] -= 1
            if death_countdown[cell] <= 0:
                just_died.append(cell)
        for (i, j) in just_died:
            del death_countdown[(i, j)]
            active.discard((i, j))
            grid[i][j] = DEAD
            deaths += 1
            any_change = True

        # 2. SPREAD — buffered. grid[ni][nj] == 0 naturally skips dead (3) and infected (1).
        newly_infected = set()
        for (i, j) in active:
            for di, dj in dirs:
                ni, nj = i + di, j + dj
                if 0 <= ni < rows and 0 <= nj < cols and grid[ni][nj] == 0:
                    newly_infected.add((ni, nj))

        # 3. DEATH-START — count from snapshot (current grid, pre-apply).
        for (i, j) in active:
            if (i, j) in death_countdown:
                continue
            count = 0
            for di, dj in dirs:
                ni, nj = i + di, j + dj
                if 0 <= ni < rows and 0 <= nj < cols and grid[ni][nj] == 1:
                    count += 1
            if count >= K:
                death_countdown[(i, j)] = N
                any_change = True

        # 4. APPLY new infections.
        for (i, j) in newly_infected:
            grid[i][j] = 1
            active.add((i, j))
            any_change = True

        if any_change:
            last_change_day = days

        # termination: nothing changed AND no pending countdowns
        if not any_change and not death_countdown:
            return last_change_day, deaths
```

Three things to defend:
1. **Tick order: decay → spread → death-start → apply.** Death-start must read a *consistent* snapshot — that's why it happens before the apply step, so we count from the start-of-tick world.
2. **Countdown is unconditional.** Once started, ticks down even if neighbors die. The alternative (pause/resume) creates oscillating-pause behavior that's almost always wrong.
3. **Termination = no change AND no pending countdown.** A pending countdown is a *promise* that a death is coming, so we can't stop yet even if this tick was no-op.

### Part 4C — composite (Parts 1 + 2 + 3 + B)

Stacks all rules: spread, immune walls, D-day recovery, K-threshold death countdown.

**Tick order: recover → death-decay → spread → death-start → apply.**

The full code is ~70 lines; the structure is just 4B with a recovery pass at the top. Key additions vs. 4B:

```python
# 1. RECOVER (from Part 3) — recovered cells become immune (2).
#    If a recovering cell had a pending death countdown, cancel it.
just_recovered = [c for c in active if days - infection_day[c] >= D]
for (i, j) in just_recovered:
    active.discard((i, j))
    grid[i][j] = 2
    death_countdown.pop((i, j), None)
    any_change = True

# ... then 4B's steps 1-4 below this, in order.

# in step 5 (apply new infections):
for (i, j) in newly_infected:
    grid[i][j] = 1
    infection_day[(i, j)] = days
    active.add((i, j))
```

**The recover-cancels-death thing matters.** If a cell is on the brink of recovering this tick, it should recover cleanly and not also get marked dead. Recovery beats death because recovery is processed first.

If asked to defend the order: "recover first because recovered cells shouldn't take any further actions this tick; death-decay second because dying cells shouldn't get to spread; spread third on the still-active survivors; death-start fourth using the pre-apply snapshot."

---

## What the rubric scores

| Axis | What gets graded here |
|------|------------------------|
| **Practical problem-solving** | Parts 1 + 2 should be fast and clean. 30 min on Part 1 = over-engineered. |
| **Edge case discipline up front** | Did you enumerate `no sources, all-infected, walled-off, empty grid, all-immune` *before* coding? Or did you discover them via test failures? |
| **Layered optimization** | "Multi-source BFS" → "track `healthy` counter instead of re-scanning the grid each tick" → "active-set sweep for sparse grids." |
| **Depth in Python internals** | Light here. Demonstrating `set` for the active set + `dict` for `infection_day` is enough. `collections.deque` for the BFS queue (not `list.pop(0)`) is the small-but-real signal. |
| **Targeted optimization under follow-up** | "8-neighbor → change `dirs`, nothing else." "Sources mid-simulation → re-prime each tick." "Sub-linear recovery → bucket schedule by recover-on day." |
| **Test quality** | Are your tests covering bug patterns (off-by-one, walled-off, no sources, all-immune)? Or just the happy path? |

A **"strong hire"** verdict comes from:
- Clean Parts 1-3 with the right tick ordering in Part 3.
- Naming the off-by-one and the recover-then-spread ordering *before* the interviewer prompts you.
- Articulating "I'll handle this with a buffer" or "snapshot" *as you start* Part 3, not in post-hoc bug fixing.

A **"lean hire"** verdict comes from:
- Parts 1-2 clean; Part 3 works after one or two bug-fix passes.
- You name the off-by-one when it bites you, not before.

---

## Common mistakes

1. **Mutating the grid in-place during Part 3 spread.** You iterate `active`, infect a neighbor, and *that* neighbor enters the iteration (or affects another active cell's neighbor count). Same-tick cascade. Pull `newly_infected` into a buffer first.

2. **`> D` instead of `>= D`.** Recovery happens one day late. Tests with D=2 catch it cleanly.

3. **Recovering AFTER spreading within the same tick.** A cell at the recovery threshold spreads one final time, then recovers. Off by one full tick.

4. **Counting immune cells as healthy targets in Part 2.** Then `healthy` never hits zero and you wrongly return -1.

5. **Forgetting `if not q: return -1` early-out in Part 1.** If there are no sources and at least one healthy cell, it's -1. Easy to miss when you focus on the main loop.

6. **Per-cell DFS instead of multi-source BFS.** DFS gives wrong day counts because it doesn't respect simultaneous spread. Multi-source BFS with the level-batch idiom is canonical.

7. **Reaching for 8-neighbor without asking.** Most reports are 4-neighbor. Confirm before coding.

8. **`list.pop(0)` instead of `collections.deque.popleft()`.** `list.pop(0)` is O(n). Small in practice for typical grids; named as a real signal in code review.

---

## Follow-up sketches

**"What if propagation is 8-neighbor?"**
```python
dirs = [(di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di, dj) != (0, 0)]
```
Two-line change. Same algorithm. Day counts use Chebyshev distance.

**"Sources can appear mid-simulation."**
Re-prime at the top of each tick:
```python
while active or pending_sources_for(current_day):
    current_day += 1
    for c in pending_sources_for(current_day):
        active.add(c)
        infection_day[c] = current_day
    # ... recover, spread, apply
```

**"Recovery faster than O(|active|) per tick."**
Bucket-schedule at infection time. O(1) per tick recovery:
```python
recovers_on: dict[int, list[tuple[int, int]]] = defaultdict(list)
# at infection time:
recovers_on[current_day + D].append((i, j))
# at tick start:
for c in recovers_on.pop(current_day, []):
    active.discard(c)
    grid[c[0]][c[1]] = 2
```

**"10^6 × 10^6 but sparse."**
Don't store the grid densely. Store `infected: set`, `immune: set`, `infection_day: dict`. The active-set BFS already only touches O(infected) per tick. Storage is the win — O(infected + immune) instead of O(M × N).

**"Parallelize across cores."**
Each cell's next state depends only on the snapshot — embarrassingly parallel. Split rows across workers, sync at end of each tick. In Python that's `multiprocessing` because of the GIL (you saw this in the crawler chapter); `threading` would serialize the CPU work.

---

## Honest weaknesses to acknowledge

- The reference implementations mutate the input grid. In production you'd probably want to copy it. Mention this if pressed.
- Parts 1 and 2 are nearly identical. In a real codebase, factor `_bfs_until_targets_consumed(grid, target_value)`. In an interview, duplication is cheaper than a botched refactor mid-clock.
- Per-tick `for c in active if current_day - infection_day[c] >= D` is O(|active|). The bucket trick above is the fix if asked.
- Part 4A's snapshot copy is O(R × C) per tick. For dense grids that's fine; for huge sparse grids you'd want a "dirty cells" frontier (cells with at least one infected neighbor) — but that's a real-deal optimization, not interview-scope.

---

## Self-grading prompt (do this honestly)

After your attempt, score yourself 1-3 on each axis:

| Axis | 1 = missed | 2 = ok | 3 = strong |
|------|------------|--------|-----------|
| Edge cases enumerated up front | Discovered via test failure | Listed 3-4 | Listed 5+ including walled-off |
| Part 1 in under 15 min | >25 min | 15-25 min | <15 min, clean |
| Part 2 in under 5 min from Part 1 | Re-derived from scratch | <10 min | <5 min, "5-line upgrade" |
| Part 3 tick ordering correct | Recovered after spread | Right after one bugfix | Right first time, articulated |
| Used `>= D` not `> D` | `> D` | `>= D` after thinking | Stated it explicitly while coding |
| Buffered spread writes | In-place | Buffered after bugfix | Buffered from first line |

A 12+ total here lines up with "strong hire" on Parts 1-3.
