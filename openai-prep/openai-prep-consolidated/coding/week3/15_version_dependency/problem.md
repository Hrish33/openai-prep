# Problem 15: Version Dependency (earliest-supported-version variant)

**Time budget:** 45-60 min (phone screen). Part 1 in 10 min, Part 2 in 10 min, Part 3 in 25-30 min.
**Source:** OpenAI phone screen rotation, last seen 2026-05-08. Frequency: medium. Three escalating parts; the third one is the discriminator.
**Stage:** Phone screen.

> **Note:** This is the *binary-search-over-versions* variant of "Version Dependency." A different rotation drops a dependency-graph / topological-sort problem under the same name (see followups). This file covers the API-probe variant only.

---

## The setup

You're given a sorted list of version strings — `"103.003.02"`, `"104.0.0"`, `"104.0.1"`, etc. The harness exposes a probe:

```python
def isSupported(version: str) -> bool: ...
```

It returns whether a given feature is supported on that version. It's **slow and rate-limited** — in Part 3 you minimize calls.

Your job: find the **earliest** version that supports the feature, or `None` if none does.

### Version parsing

```python
def parse_version(version: str) -> tuple[int, int, int]:
    # "103.003.02" → (103, 3, 2). Split on '.', int() each part.
```

The input list is sorted **lexicographically**, NOT numerically. `"1.10.0"` sorts *before* `"1.9.0"` as strings but *after* it numerically. Always parse before comparing.

---

## Part 1 — monotone support

Support is monotone over the sorted list: once `isSupported` returns `True` for some version, it stays `True` for all later versions.

```python
def find_earliest_supported_version_v1(
    versions: list[str],
    is_supported: Callable[[str], bool],
) -> str | None: ...
```

**Expected:** sort by parsed version, linear scan, return the first `True`, or `None` if no version supports it.

**Trap:** sort by `parse_version` key, not by the raw string. The grader will feed you lexicographically-sorted input on purpose.

---

## Part 2 — regressive support

Support may regress — the truth table can go `True → False → True` across the version list. **Guarantee:** if some version supports the feature, at least one *later* version also supports it (i.e. the very last supported version is never followed by an unsupported tail).

```python
def find_earliest_supported_version_v2(
    versions: list[str],
    is_supported: Callable[[str], bool],
) -> str | None: ...
```

**Expected:** still return the **absolute earliest** `True` version. Can't early-exit on the first `True` like Part 1 — you must scan all versions and return the minimum-parsed `True`.

**Trap:** the natural instinct after Part 1 is to return on first hit. Don't.

---

## Part 3 — rate-limited

`isSupported` is now expensive. You're scored on **number of API calls**, not wall time. Versions are structured as `major.minor.patch` and the support relation has nested monotonicity:

- If some patch in major.minor `X.Y` is supported, some later patch in `X.Y` is also supported.
- If some minor in major `X` is supported, some later minor in `X` is also supported.
- If some major is supported, some later major is also supported.

```python
def find_earliest_supported_version_v3(
    versions: list[str],
    is_supported: Callable[[str], bool],
) -> str | None: ...
```

**Expected:** hierarchical binary search. Bisect across majors (probing the *latest patch in each major* as the group representative), find the first supported major, then bisect minors inside that major, then patches. Target O(log M + log Mi + log P) probes vs Part 2's O(N).

**Cache every probe** by version string — the bisection visits the same representative multiple times across nesting levels. Memoize or you'll burn calls for nothing.

**Trap — group representative:** the representative of a `(major, minor)` group must be the **latest** patch. Probing the earliest patch may return `False` even when a later patch in the same group is `True`, breaking the bisection invariant.

**Trap — bisection termination:** when bisecting for the first `True`, keep moving left on hits. Don't return on first `True` — there may be an earlier `True` group on the left half.

---

## Edge cases to nail

- **Empty list** → `None` regardless of part.
- **No version supports it** → `None`. Part 1 burns N calls; Part 3 should burn ~log(majors) on a fully-unsupported input (every probe returns `False`, bisection runs to the end).
- **Single version, supported** → that version. Should take one call.
- **All versions supported** → the lexicographically-sorted-by-`parse_version` first one. Part 3 should still find it in O(log) calls, not O(N).
- **Mixed major/minor structure** — e.g. `2.0.0` and `2.0.1` present, but no `2.1.x`. Don't assume groups are contiguous in (major, minor) — build the group index from the input, don't enumerate all (X, Y) pairs.

---

## What an OpenAI interviewer is looking for

1. **Parse-before-compare reflex.** Sort by `parse_version`, never by raw string. If you sort raw and don't notice, the round is over.
2. **Part 2 instinct check.** Naming "the answer is the first `True` we see" out loud, then catching yourself: "wait — Part 2 says support can regress; I need the minimum across all `True`s." That self-correction is what the interviewer is watching for.
3. **Part 3 as a *call-count* problem, not a wall-clock problem.** Say it explicitly: "I'm optimizing for fewest `is_supported` calls. Every probe gets memoized." Don't talk about Python loop speed.
4. **Caching is non-negotiable.** Hierarchical bisection re-visits group representatives; uncached, you can blow your call budget on duplicates. Tests will count calls.
5. **Group representative is the *latest* in the group.** State it. The most common Part 3 failure is "probed first patch, got False, skipped the group" — and a later patch in that group was the answer.

---

## Follow-ups (don't peek)

<details>
<summary>Click to expand</summary>

1. **Parallel probing.** If `is_supported` supports concurrent calls, fan out the group-representative probes for a level in parallel (e.g. `asyncio.gather` or `ThreadPoolExecutor`) so the wall-clock is gated on the deepest level, not the sum. Cache is shared.
2. **Retry / backoff.** What if `is_supported` raises or returns `None` on timeout? Wrap in retry-with-backoff. Distinguish "unknown" from `False` in the cache.
3. **Pre-release suffixes.** Extend `parse_version` to handle `"v2.1.0-beta"` or `"2.1.0+build.5"`. PEP 440 / semver tie-breaking — pre-release < release; build metadata ignored for ordering.
4. **Return *all* supported versions.** Hierarchical bisection no longer applies — you need every `True`, which forces a full scan. Revert to Part 2 with caching.
5. **The dependency-graph variant.** A different rotation of "Version Dependency" gives you `(package, version, [(dep, constraint)])` tuples and asks for: (a) parse, (b) topological install order, (c) detect cycles, (d) backtracking resolver when constraint sets clash. Kahn's BFS + DPLL-style DFS on candidate versions. ~75 min of typing; no clever data structures needed. Separate problem — scaffold as 15b if you want it.

</details>

---

## Honest difficulty note

**Parts 1 and 2 are warm-ups.** A clean candidate burns 15 minutes total on both. The interviewer is using them to confirm you can (a) sort by parsed key, (b) catch the "first True isn't the answer in regressive mode" trap.

**Part 3 is the round.** What gets you the offer:
- Naming "hierarchical bisection over (major, minor, patch)" before coding.
- Stating the group-representative rule (latest patch) out loud.
- Caching from the first line.
- Articulating the call-count complexity — O(log M + log Mi + log P) — vs Part 2's O(N).

What loses the round:
- Sorting by raw string.
- Returning on first `True` in Part 2.
- Probing the *first* patch as the group representative in Part 3.
- Not memoizing — call count blows up and tests notice.
- Trying to bisect the *flat* sorted list in Part 3. The nested monotonicity is the whole point; a flat bisection misses it and gives no asymptotic win.
