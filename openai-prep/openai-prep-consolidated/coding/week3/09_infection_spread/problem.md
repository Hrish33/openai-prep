# Problem 9: Infection Spread / Cellular Automata

**Prereqs:** Skim `00_prereqs.md` if you haven't internalized the buffer-vs-snapshot pattern and the recover-then-spread tick ordering.

**Time budget:** 60 min total. Strong-signal range is **Parts 1-3 clean** in ~45 min.
**Source:** Reported very frequently in OpenAI phone screens (last seen 2026-05-16). Frequency: very high.

## Problem

You're given an M×N grid representing cells in some state. Infection propagates day-by-day under rules that escalate across 5 parts. Return the number of days until a termination condition, or -1 if unreachable.

Implement the parts one at a time. Each builds on the previous.

**Encoding (Parts 1-3):** `0 = healthy, 1 = infected, 2 = immune` (Parts 2+).

---

## Part 1 — basic multi-source spread

Each day, every infected cell simultaneously infects its 4-neighbor healthy cells (orthogonal only, no diagonals). Cells newly infected today only propagate tomorrow.

Return the number of days to full infection, or `-1` if any healthy cell is permanently unreachable (no sources, or isolated region).

```python
def time_to_full_infection(grid: list[list[int]]) -> int:
    ...
```

**Clarify before coding:** 4-neighbor or 8-neighbor (diagonal-inclusive)? Most reports are 4. Some loops slip in 8 — ask.

## Part 2 — immune cells

Add `2 = immune`: never gets infected, never propagates, acts as a wall.

Return days until all *non-immune* healthy cells are infected, or `-1` if any healthy cell is walled off behind immune cells.

```python
def time_to_full_infection_with_immunity(grid: list[list[int]]) -> int:
    ...
```

**Clarify before coding:** numeric encoding (`0/1/2`) or character (`./X/I`)? Default to numeric.

## Part 3 — recovery → immunity

After being infected for **D days**, a cell becomes immune (value `2`). Immunity takes effect *before* spread on the same tick — recovered cells do NOT propagate on the day they recover.

Termination changes: no longer "full infection." Now: **no active infected cells remain**. Some healthy cells may survive forever — that's the stable state. Return the day count.

```python
def time_to_stable_state(grid: list[list[int]], D: int) -> int:
    ...
```

**Bug magnets** (interviewer is watching for these):
- `current_day - infection_day[(i,j)] >= D` (NOT `>`).
- Recover *before* spread within the same tick.
- Don't mutate the grid in place during spread — buffer the writes.

## Part 4 — three confirmed variants

The interviewer picks one if you reach this. All three reuse the Part 3 tick skeleton with different rules.

**Variant A — threshold spread:** a healthy cell becomes infected next day only if `count_infected_4_neighbors >= K`. Use a snapshot of the grid to count; buffer would double-count cells that just got infected this tick. Return `-1` if a tick produces no new infections and healthy cells remain.

```python
def time_to_full_infection_threshold(grid: list[list[int]], K: int) -> int:
    ...
```

**Variant B — death countdown:** an infected cell that's not yet immune starts a death countdown if `>= K` infected neighbors; dies after N days. Return `(days_to_end, total_deaths)`. Spec is fuzzy — ask the interviewer what "days to end" means; assume "until no further changes."

```python
def time_to_end_with_death(grid: list[list[int]], K: int, N: int) -> tuple[int, int]:
    ...
```

**Variant C — composite:** Parts 1+2+3 + B stacked. Tick order: **recover → death-decay → spread**.

## Part 5 — burn optimization (almost no one reaches)

Each day, you choose any row or column and burn (kill) everything on it. Minimize total deaths. This is a DP/greedy problem, not BFS. Skip unless you've finished Parts 1-4 with time left.

---

## Required API

Implement the three Part 1-3 signatures above first. Parts 4-5 only if time. All take `list[list[int]]` and return `int` (or `tuple[int, int]` for Variant B).

## Requirements (Parts 1-3)

- **Multi-source BFS for Parts 1-2.** Enqueue all initial sources at level 0 before the main loop.
- **Synchronous update.** Cells newly infected this tick do NOT propagate until next tick.
- **Edge cases:** empty grid, no sources, all-infected, 1×1, multiple sources, walled-off healthy regions (immune barriers in Part 2), no-initial-infection in Part 3.
- **Part 3:** track `infection_day` per cell. Recover-then-spread within each tick. Termination = no active cells.

## What an OpenAI interviewer is looking for

1. **Edge cases up front.** Enumerate before coding: empty grid, no sources, all-infected, isolated regions, immune walls. Pay this off in 30 seconds at the start.
2. **Multi-source BFS, cleanly.** Parts 1-2 should be ~25-30 lines each. If yours is 50, you've over-thought it.
3. **Buffer/snapshot pattern in Part 3.** In-place mutation during the same tick is the bug they're watching for.
4. **`>=` vs `>` for recovery.** The classic off-by-one. State it explicitly: "I'm using `>=` because a cell infected on day 0 with D=2 becomes immune on day 2."
5. **Recover-first ordering.** Articulate why: "a recovered cell shouldn't propagate one final time on the day it heals."
6. **Termination logic per part.** Part 1: queue empty + all infected → return days. Part 2: same but only count non-immune. Part 3: active set empty → return current_day.

## Follow-ups (don't peek until base works)

<details>
<summary>Click to expand</summary>

1. **8-neighbor (diagonal) propagation.** One-line change in `dirs`. Same algorithm; day counts change because Chebyshev distance replaces Manhattan.

2. **Sources can appear mid-simulation.** Re-prime the active set at the top of each tick: `for c in pending_sources_for(current_day): active.add(c); infection_day[c] = current_day`. Nothing else changes.

3. **Sparse grid (10^6 × 10^6, few infections).** Don't store grid densely — store the infected set and immune set as dicts. Active-set BFS already only touches O(infected) per tick. Storage becomes the win.

4. **Parallelize across cores.** Each cell's next state depends only on the snapshot — embarrassingly parallel. Split rows across workers, sync at end of each tick. (In Python: `multiprocessing` because of the GIL.)

5. **Recovery faster than O(|active|) per tick.** Bucket-schedule: at infection time, `recovers_on[t + D].append((i, j))`. Each tick, pop the bucket for the current day. O(1) recovery instead of O(|active|).

6. **Animation / replay.** Append `(day, frozenset(newly_infected))` to a list each tick. No algorithm change.

7. **Probabilistic infection.** Each healthy neighbor has `p` probability of being infected. Same structure, pass an RNG; tests become statistical.

8. **Multiple strains (A and B with different rules).** Tag each infected cell with strain; separate `infection_day` per strain; spread rules dispatch on strain.

</details>

## Honest difficulty note

Part 1 is LC 994 with the encoding flipped. If you've done LC 994 recently, this is 10 min.

Part 2 is a 5-line upgrade — count immune as "not a healthy target" and the neighbor check naturally skips it.

**Part 3 is where the real signal is.** The state-tracking, the tick ordering, and the off-by-one are what the interviewer grades. Spend ~20 of your 60 minutes here.

Part 4 is variant-pick. Threshold (A) is the easiest. Composite (C) eats the rest of the hour if you take it. Part 5 is almost never reached.

A "strong hire" verdict comes from: clean Parts 1-3 with the right tick ordering in Part 3, and naming the off-by-one and the recover-first ordering *before* the interviewer prompts you.
