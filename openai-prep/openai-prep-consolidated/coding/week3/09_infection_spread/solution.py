"""
Infection spread / cellular automata. Five escalating parts.

Read problem.md first. Sketch BEFORE coding:
  - Termination condition for each part (full infection? no active cells?).
  - Per-cell state needed for Part 3 (infection_day) and 4B (death_countdown).
  - How to avoid mutating the grid in place during spread (buffer or snapshot).
  - Tick order for Part 3 (recover, THEN spread).

Suggested helper (write it once, reuse across parts):
  - in_bounds(i, j, rows, cols) — keep neighbor checks readable.

Parts 1-3 are core. Part 4 variants and Part 5 are if-time.

Encoding: 0 = healthy, 1 = infected, 2 = immune (Parts 2+).
"""

from typing import Optional


# ============================================================
# Parts 1-3 — core. These are what gets graded.
# ============================================================


def time_to_full_infection(grid: list[list[int]]) -> int:
    """
    Part 1. Multi-source BFS, 4-neighbor spread, simultaneous tick.
    Return days to full infection, or -1 if any healthy cell is permanently unreachable.

    Edge cases: empty grid, no sources, all-infected, 1x1.

    HINT: this is LC 994 (Rotting Oranges) with the encoding flipped.
    Your `healthy` counter plays the role of `fresh_oranges`.
    """
    # your code here
    raise NotImplementedError


def time_to_full_infection_with_immunity(grid: list[list[int]]) -> int:
    """
    Part 2. Value 2 = immune (wall). Don't count immune as a healthy target.
    Return days until all non-immune healthy cells are infected,
    or -1 if any healthy cell is walled off.

    Tiny upgrade from Part 1: skip value 2 when counting healthy targets;
    the neighbor check already excludes it (only flips value 0).
    """
    # your code here
    raise NotImplementedError


def time_to_stable_state(grid: list[list[int]], D: int) -> int:
    """
    Part 3. After D days infected, a cell becomes immune (value 2)
    and stops propagating. Tick order: RECOVER first, THEN spread.
    Termination: no active infected cells remain.

    Bug magnets:
      - `current_day - infection_day >= D` (NOT >).
      - Recover before spread within the same tick.
      - Don't mutate the grid mid-spread — buffer the writes.

    Edge cases: no initial infection (return 0), all-immune (return 0),
    D large enough that everyone gets infected before any recovery.
    """
    # your code here
    raise NotImplementedError


# ============================================================
# Part 4 — variants. Attempt only after Parts 1-3 are clean.
# ============================================================


def time_to_full_infection_threshold(grid: list[list[int]], K: int) -> int:
    """
    Part 4A. Healthy cell becomes infected only if it has >= K infected 4-neighbors.
    Use a SNAPSHOT to count (not the live grid — buffer would double-count).
    Return -1 if a tick produces no new infections and healthy cells remain.

    K=1 reduces to Part 1.
    """
    # your code here
    raise NotImplementedError


def time_to_end_with_death(grid: list[list[int]], K: int, N: int) -> tuple[int, int]:
    """
    Part 4B. Infected cell with >= K infected neighbors starts a death countdown;
    dies after N days. Return (days_to_end, total_deaths).

    Spec is fuzzy. Recommended interpretation:
      - "days_to_end" = days until no further changes occur (no new infections, no new deaths).
      - A dead cell is removed entirely (becomes 0 — healthy again? or a 4th state?).
        Ask the interviewer. Default: dead cell becomes a separate state, doesn't spread.

    Don't implement without confirming the spec.
    """
    # your code here
    raise NotImplementedError
