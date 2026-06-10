# Problem 5: Unix `cd` with symbolic link resolution

**Prereqs:** Work through `00_prereqs.md` first. Don't attempt cold.

**Time budget:** 45 minutes
**Source:** [HelloInterview community report](https://www.hellointerview.com/community/questions/unix-cd-resolution/cmbskxz3y004n07adimbogre1) — reported by an OpenAI candidate.

## Problem

Implement a Unix-style `cd` command that supports:
- absolute paths (`/foo/bar`) and relative paths (`bar/baz`)
- the special components `.` (current) and `..` (parent)
- redundant slashes (`//`, trailing `/`)
- **symbolic links**, registered ahead of time, resolved at each component
- **cycle detection** when symlinks chain back to themselves

```python
shell = Shell()
shell.pwd()                          # "/"

shell.cd("/home/user")
shell.pwd()                          # "/home/user"

shell.cd("../other")
shell.pwd()                          # "/home/other"

shell.cd("/")
shell.cd("a/b/c/../../d")
shell.pwd()                          # "/a/d"

shell.register_symlink("/usr/local", "/usr")
shell.cd("/usr/local/bin")
shell.pwd()                          # "/usr/bin"

shell.register_symlink("/loop_a", "/loop_b")
shell.register_symlink("/loop_b", "/loop_a")
shell.cd("/loop_a")                  # raises ValueError("symlink cycle ...")
```

## Required API

- `Shell()` — constructor, no args. Starting cwd is `"/"`.
- `register_symlink(link_path: str, target: str) -> None` — register a symlink. Both paths are absolute (start with `/`).
- `cd(command: str) -> str` — resolve `command` from current cwd, update cwd, return the new absolute cwd. Raises `ValueError` on symlink cycle.
- `pwd() -> str` — return current cwd. Always absolute.

## Requirements

- **Absolute paths reset.** `cd("/x/y")` discards current cwd and starts from root.
- **Relative paths extend.** `cd("x/y")` appends to current cwd, then normalizes.
- **`.` is a no-op. `..` pops one component.** `..` at root stays at root (no error).
- **Empty components are skipped.** `//`, leading `/` past root, trailing `/`, all collapse.
- **Symlinks resolve at each component.** When a regular component is pushed, check if the resulting full path is a registered symlink. If yes, replace with the target and recursively resolve the target (which is itself a path needing the same `.` / `..` normalization).
- **Cycle detection per `cd` call.** A `visited` set scoped to the current call. Two `cd` calls that both touch `/a` are fine — a single `cd` that loops `/a → /b → /a` is not.
- **On cycle: raise `ValueError`, cwd unchanged.** State must be unchanged after a rejected call.

## Constraints

- Symlinks are stored in a `dict[str, str]` you manage. Both keys and values are absolute paths.
- Symlink targets may contain `.`, `..`, and redundant slashes — normalize them through the same walker.
- Re-registering a symlink (`register_symlink` on a path already registered) replaces the target.
- Empty command (`cd("")`): treat as no-op, cwd unchanged. (Be ready to defend; "raise" is also defensible.)

## Error contract

| Condition | When | Error |
|---|---|---|
| Symlink cycle reached during resolution | `cd` | `ValueError`, cwd unchanged |
| `..` at root | `cd` | no error — silently stays at root |
| Empty / unknown component as path step | `cd` | no error — treat as regular dir name (we have no filesystem, can't validate existence) |

This problem deliberately has **no concept of "directory doesn't exist"** — there's no underlying filesystem. The shell trusts that every regular component is a valid directory. The only failure mode is a symlink cycle.

## What an OpenAI interviewer is looking for

1. **Edge cases enumerated up front.** Before writing code, list: empty command, `/`, `/../..`, self-loop symlink, two-link cycle, symlink with `..` in target, chained symlinks A→B→C, symlink registered to itself.
2. **One walker, not two.** Both `command` and a symlink's `target` are paths needing the same split/normalize logic. Strong attempts have one helper used twice; weak attempts duplicate the loop.
3. **Per-component resolution.** When the interviewer asks "what if I `cd /usr/local/bin` and `/usr/local` is a symlink to `/usr`?", the answer is "I check at every push." Not "at the end."
4. **Cycle detection in the right place.** Inside `_resolve`, scoped to the call. Not on every component, not as instance state.
5. **Atomic semantics on failure.** Cycle raises → cwd is unchanged. You either resolve fully first then commit, or you snapshot/rollback. Mention which you chose.
6. **No `os.path.realpath` / `pathlib.Path.resolve`.** Using the stdlib answer defeats the problem. Same hard-fail as `eval()` in the spreadsheet.

## Follow-ups (don't peek until base works)

<details>
<summary>Click to expand</summary>

1. **Relative symlink targets.** Right now targets are absolute. Real Unix supports `ln -s ../other link`, where `..` resolves *relative to the link's directory*. Sketch: when resolving a symlink, the starting stack is `dirname(link)`, not `[]` or cwd. Where does this slot in?

2. **A real filesystem.** Instead of `symlinks: dict`, you have `mkdir`, `ln -s`, and a tree of directories. `cd` now needs to walk the tree, validate that components exist, distinguish files from directories. Sketch: introduce an `Inode` (dir | file | symlink with target), keep the path walker, look each component up in its parent dir.

3. **Symlink depth limit.** Linux caps at ~40 link expansions to prevent pathological cases that *aren't* cycles (e.g., very long chains). Add a `max_depth` counter to `_resolve`. Why a depth limit if you already have cycle detection? (Answer: defense in depth; chains can be long without being cyclic.)

4. **Concurrent `cd` and `register_symlink`.** Two threads — one cd-ing, one registering a new symlink. What's your invariant? A `threading.Lock` around the public methods is the easy answer. Be ready to discuss whether `pwd()` needs the lock too.

5. **Persist the symlink table.** Survive restart. Serialize to JSON? Read on construction? Discuss durability vs throughput trade-offs.

6. **Reverse mapping: which symlinks point at `/usr`?** Add `who_links_to(target)`. Trivial if you keep a reverse `dict[target, set[link]]` updated on `register_symlink`. Common interviewer drill: "now what if I remove a symlink?"

7. **Globbing.** `cd /usr/*/bin` — match any subdirectory. This breaks the "no filesystem" assumption: without a directory tree, `*` has nothing to match. Discuss what needs to be true to support it.

</details>

## Honest difficulty note

If you've done LC 71 and remember the visited-set cycle pattern, the base is **30–40 minutes**. The trap is reaching for symlink resolution before you have plain `.`/`..`/empty handling rock-solid — get that working first, then bolt symlinks on top.

A strong attempt covers:
- All five path-normalization rules (15 min)
- Per-component symlink resolution with recursive target walking (10 min)
- Cycle detection scoped per-call (5 min)
- Atomic semantics: rejected cycle leaves cwd untouched (5 min)
- 2–3 enumerated edge cases tested before declaring done (5 min)

The interviewer cares about **clarity of separation** between path walking and symlink expansion, not feature count.
