# Problem 9: Infection Spread / Cellular Automata

**Status:** Scaffolded 2026-06-09. Cold-attempt Parts 1-3 in a 45-min block when ready.

**One-liner:** Multi-source BFS on a grid with escalating rules — immune walls, recovery countdowns, threshold spread.

**Source:** Reported very frequently in OpenAI phone screens (last seen 2026-05-16). 5 sub-parts in 60 min; strong signal is **Parts 1-3 clean**.

**Key concept:** multi-source BFS → simultaneous-update + per-cell state tracking.

**Likely prereqs:**
- LeetCode 994 (Rotting Oranges) — Part 1 is literally this with the encoding flipped.
- Concept: simultaneous update without in-place mutation (buffer/snapshot patterns).
- Concept: per-cell state alongside the grid + the recover-then-spread tick ordering.

**When to do this:** week 3, after 08 (multithreaded crawler). This problem should feel like a graceful descent from crawler — algorithm-only, no threads. Budget: 45 min for Parts 1-3 cold.
