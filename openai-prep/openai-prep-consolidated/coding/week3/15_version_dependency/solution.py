"""Version Dependency — earliest-supported-version variant.

See ``problem.md`` for the full spec.

    Part 1 — monotone:    sort by parsed version, linear scan, first True.
    Part 2 — regressive:  scan all, return MIN of True set (can't early-exit).
    Part 3 — rate-limited: hierarchical bisection over (major, minor, patch),
                           memoized. Group representative = LATEST patch.
                           Requires suffix-monotone support within each level
                           (latest member True iff any member True).
"""

from typing import Callable, Optional


def parse_version(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def find_earliest_supported_version_v1(
    versions: list[str],
    is_supported: Callable[[str], bool],
) -> Optional[str]:
    for v in sorted(versions, key=parse_version):
        if is_supported(v):
            return v
    return None


def find_earliest_supported_version_v2(
    versions: list[str],
    is_supported: Callable[[str], bool],
) -> Optional[str]:
    best: Optional[str] = None
    best_key: Optional[tuple[int, int, int]] = None
    for v in versions:
        if not is_supported(v):
            continue
        k = parse_version(v)
        if best_key is None or k < best_key:
            best_key = k
            best = v
    return best


def find_earliest_supported_version_v3(
    versions: list[str],
    is_supported: Callable[[str], bool],
) -> Optional[str]:
    if not versions:
        return None

    cache: dict[str, bool] = {}

    def probe(v: str) -> bool:
        if v not in cache:
            cache[v] = is_supported(v)
        return cache[v]

    def bisect_leftmost_true(items: list, rep_of) -> int:
        """Leftmost index i with probe(rep_of(items[i])) True, else -1."""
        lo, hi = 0, len(items) - 1
        found = -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if probe(rep_of(items[mid])):
                found = mid
                hi = mid - 1  # keep moving left — earliest True may be further back
            else:
                lo = mid + 1
        return found

    sorted_versions = sorted(versions, key=parse_version)

    by_major: dict[int, list[str]] = {}
    for v in sorted_versions:
        by_major.setdefault(parse_version(v)[0], []).append(v)

    # Level 1 — bisect majors. Rep = latest version in that major.
    majors = sorted(by_major)
    maj_idx = bisect_leftmost_true(majors, lambda m: by_major[m][-1])
    if maj_idx < 0:
        return None

    # Level 2 — bisect minors within the chosen major.
    chosen_major = majors[maj_idx]
    by_minor: dict[int, list[str]] = {}
    for v in by_major[chosen_major]:
        by_minor.setdefault(parse_version(v)[1], []).append(v)

    minors = sorted(by_minor)
    min_idx = bisect_leftmost_true(minors, lambda mn: by_minor[mn][-1])
    if min_idx < 0:
        return None

    # Level 3 — bisect patches within the chosen (major, minor).
    patches = by_minor[minors[min_idx]]
    patch_idx = bisect_leftmost_true(patches, lambda v: v)
    if patch_idx < 0:
        return None
    return patches[patch_idx]
