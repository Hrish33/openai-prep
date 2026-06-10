# Problem 5: Unix `cd` with Symbolic Link Resolution

**Status:** Scaffolded. Open `00_prereqs.md` to start; attempt in `solution.py`; reference in `interviewer_notes.md`.

**One-liner:** Implement `cd` command logic: handle `.`, `..`, absolute paths, symbolic links, and detect symlink cycles.

**Source:** [HelloInterview community question](https://www.hellointerview.com/community/questions/unix-cd-resolution/cmbskxz3y004n07adimbogre1)

**Key concept:** path parsing + cycle detection (with symlinks pointing in arbitrary directions)

**Likely prereqs:**
- [LeetCode 71 — Simplify Path](https://leetcode.com/problems/simplify-path/) (Medium) — path normalization with `.` and `..`, no symlinks. Warmup.
- Cycle detection (same as problem 1's prereq — if you did LC 207, you're set)
- Reading: how Unix actually resolves paths — the order of operations (resolve symlinks at each component, not just at the end)

**When to do this:** week 2, after problem 4. Builds on cycle detection muscle from problem 1.
