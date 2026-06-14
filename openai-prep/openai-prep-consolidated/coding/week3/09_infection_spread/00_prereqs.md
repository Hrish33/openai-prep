# Prereqs — Infection Spread / Cellular Automata

**Don't attempt until you've internalized the three patterns below.** Estimated time: 1-2 hours, mostly because you already have multi-source BFS.

You've done LC 994 (Rotting Oranges), which IS Part 1 with a different encoding. So the BFS scaffold isn't new. What IS new for Parts 2-3:

1. **Simultaneous update without in-place mutation** — Parts 3+ need it.
2. **Per-cell state alongside the grid** — Part 3 tracks "when did this cell get infected" per cell; Part 4B tracks "death countdown."
3. **The recover-then-spread tick ordering** — Part 3's load-bearing detail.

Internalize these and Parts 1-3 are routine. The traps are mechanical, not conceptual.

---

## Concept 1: Multi-source BFS (recap from LC 994)

**You already have this.** Mental check — you should hit all four:

- Enqueue ALL initial sources at level 0 *before* the main loop./clear
- Track "remaining target cells" (your LC 994 `fresh_oranges` counter) so you can detect -1 cases.
- Level-by-level expansion via `for _ in range(len(q)):` — cells enqueued inside the inner loop only propagate next tick.
- Return -1 when the queue empties but unreached targets remain.

Your LC 994 solution does all four. Part 1 is the same code with the encoding flipped (`0=healthy, 1=infected` instead of LC's `1=fresh, 2=rotten`) and the `healthy` counter playing the role of `fresh_oranges`.

**Done when:** you can write the multi-source BFS template from a blank screen in under 10 minutes.

---

## Concept 2: Simultaneous update — buffer vs in-place

**What you're learning:** the only way to correctly advance a cellular automaton one tick. Parts 3, 4A, 4B all need this.

**The bug — in-place mutation during the same tick:**

```python
# WRONG for Part 3+
for (i, j) in active:
    for (ni, nj) in neighbors(i, j):
        if grid[ni][nj] == 0:
            grid[ni][nj] = 1   # ← now (ni,nj) acts infected for OTHER cells in this same loop
            active.add((ni, nj))
```

A cell infected on *this* tick should only start spreading *next* tick. Mutating in place means iteration order changes the result, and you get same-tick cascades.

**Two fixes, both equivalent:**

**Fix A — Buffer the writes.** Collect changes, apply at the end of the tick:

```python
newly_infected = set()
for (i, j) in active:
    for (ni, nj) in neighbors(i, j):
        if grid[ni][nj] == 0:
            newly_infected.add((ni, nj))

for (i, j) in newly_infected:
    grid[i][j] = 1
    active.add((i, j))
```

**Fix B — Read from snapshot, write to live grid.** Better when rules need to *count* neighbors (Part 4A threshold), since you read the *consistent* old state:

```python
snapshot = [row[:] for row in grid]
for i in range(rows):
    for j in range(cols):
        if should_infect(snapshot, i, j):
            grid[i][j] = 1
```

Pick by rule shape: **buffer for binary "infect/don't"**, **snapshot for "count infected neighbors"**.

**Why your Part 1 LC 994 code doesn't hit this bug:** the level-by-level BFS pattern (`for _ in range(len(q))`) does buffering *implicitly* — the queue's "current level" is frozen at the start of each inner loop; cells enqueued inside go to the next level. You can keep that pattern for Parts 1 and 2. Part 3 breaks it because recovery is a separate event from spread, so you need explicit buffering.

**Done when:** you can spot the in-place-mutation bug in a 10-line snippet on sight, and pick the right fix for the rule shape.

---

## Concept 3: Per-cell state + recover-then-spread

**What you're learning:** how to track per-cell history alongside the grid, and the exact tick ordering for Part 3. This is the strong-signal part of the problem.

**The new state — each cell needs to know *when* it got infected:**

```python
infection_day: dict[tuple[int, int], int] = {}   # (i, j) -> day infected
# (alternative: a parallel int grid with -1 sentinel for "never infected")
```

A cell becomes immune when `current_day - infection_day[(i, j)] >= D`. **`>=`, not `>`.** The off-by-one is a magnet.

**The tick — RECOVER first, THEN spread:**

```python
current_day = 0
while active:
    current_day += 1

    # 1. RECOVER — these cells do NOT spread this tick.
    just_recovered = [c for c in active if current_day - infection_day[c] >= D]
    for (i, j) in just_recovered:
        active.discard((i, j))
        grid[i][j] = 2   # immune

    # 2. SPREAD — buffer the writes.
    newly_infected = set()
    for (i, j) in active:
        for (ni, nj) in neighbors(i, j):
            if grid[ni][nj] == 0:
                newly_infected.add((ni, nj))

    # 3. APPLY — stamp infection_day with TODAY's date.
    for (i, j) in newly_infected:
        grid[i][j] = 1
        infection_day[(i, j)] = current_day
        active.add((i, j))

return current_day   # day when active became empty
```

**Why recover comes first:** a cell whose D-day age has elapsed self-heals — it "no longer propagates." If you let it spread one final time on the day it recovers, you've spread one tick too long.

**Why `>= D` not `> D`:** infected on day 0, `D=2` → should be immune on day 2. `2 - 0 >= 2` is true. With `> D` you'd recover on day 3 (one day late).

**Why the new infection's `infection_day` is `current_day` not `current_day + 1`:** the cell is infected on the current tick; the "day t" in `current_day - t >= D` should be the day it actually became infected. With this stamping, infected on day 5 with D=2 → recovers on day 7. Sanity check: that's 2 full days of being infected (days 5 and 6 it was actively spreading; day 7 it recovers before spreading). ✓

**Done when:** you can write the tick loop above from memory, and articulate (in one sentence each) why recover comes before spread and why it's `>=`.

---

## Concept 4 (skim, for Part 4): threshold + death countdown

You don't need to drill these unless you've cleared Parts 1-3 cold and have time left.

**Variant A — threshold spread:** healthy cell flips only if `count_infected_4_neighbors(snapshot) >= K`. **Switch from buffer-writes to snapshot-read** because you're counting across multiple neighbors — buffer would let you double-count cells that just got infected this tick. Termination: if a tick produces no new infections and there are still healthy cells, return -1.

**Variant B — death countdown:** add per-cell `death_countdown[(i, j)] = N` when surrounded; decrement each tick; remove cell when it hits 0. Return `(days_to_end, total_deaths)`. Spec is fuzzy here — ask the interviewer what "days to end" means (probably "until equilibrium: no more death-starts, no more spread").

**Variant C — composite:** Parts 1+2+3 + B stacked. Tick order: **recover → death-decay → spread**. Same recover-first principle applied twice.

---

## Concept 5 (almost certainly skippable): Part 5 — row/column burn optimization

Different problem entirely — DP / greedy over rows and columns. Almost no one reaches it. If you cleanly finish Parts 1-3 in under 30 min, glance at it; otherwise ignore.

---

## Recall templates — type these from a blank screen

If you can type these three, you can derive Parts 1-3 in the interview.

**1. Multi-source level BFS** (Parts 1, 2):
```python
q = deque((i, j) for ... if source(i, j))
healthy = count_healthy_cells()
if healthy == 0: return 0
if not q: return -1

days = 0
while q and healthy > 0:
    days += 1
    for _ in range(len(q)):
        i, j = q.popleft()
        for di, dj in dirs:
            ni, nj = i+di, j+dj
            if in_bounds(ni, nj) and grid[ni][nj] == 0:
                grid[ni][nj] = 1
                healthy -= 1
                q.append((ni, nj))

return days if healthy == 0 else -1
```

**2. Buffered tick** (Part 3 spread step):
```python
newly = set()
for (i, j) in active:
    for (ni, nj) in neighbors(i, j):
        if grid[ni][nj] == 0:
            newly.add((ni, nj))
# only after the loop:
for c in newly:
    grid[c[0]][c[1]] = 1
    infection_day[c] = current_day
    active.add(c)
```

**3. Recover-then-spread tick** (Part 3 full loop):
```python
while active:
    current_day += 1
    # recover
    for c in [c for c in active if current_day - infection_day[c] >= D]:
        active.discard(c); grid[c[0]][c[1]] = 2
    # spread (buffered, as above)
return current_day
```

---

## Suggested schedule

| Session | What |
|---------|------|
| Session 1 (30 min) | Read this whole doc. Re-do LC 994 if it's been a week. |
| Session 2 (45 min) | Cold attempt Parts 1-3 against `test_solution.py`. Time-box ~15 min/part. |
| Session 3 (30 min) | Read `interviewer_notes.md`. Re-do Part 3 from scratch the next day. |

## How to use Claude Code during this

- "explain the buffer vs snapshot pattern with a small example"
- "walk me through Part 3's tick ordering one more time"
- "what's the bug in this Part 3 attempt?" — paste your code

Don't ask Claude to solve Parts 1-3 for you. The muscle is in writing the tick loop yourself.

## When you're ready

When you can type the three recall templates from a blank screen, set a 45-minute timer and open `problem.md`.
