"""Version Dependency — dep-graph variant, DUMB reference.

Canonical 4-part shape (OpenAI rotation, last seen 2026-05-08):

    Part 1 — parse:         "A 1.0.0 requires B >= 2.0.0" → catalog dict.
    Part 2 — query:          direct + transitive deps for a (pkg, version).
    Part 3 — install order:  topological sort over resolved (pkg, version)
                             nodes (Kahn's BFS). Returns None on cycle.
    Part 4 — resolver:       DFS+backtrack over version candidates so every
                             constraint is mutually satisfied. None on UNSAT.

This is the BRUTE force. No clause learning, no version-set propagation,
no "fail early when constraint set empties" beyond the trivial check.
Just iterate candidates, recurse, backtrack on conflict. Plenty fast for
phone-screen-sized inputs (handful of packages, handful of versions each).
"""

from collections import deque
from typing import Optional

Version = tuple[int, int, int]
Constraint = tuple[str, Version]                  # (op, target) e.g. ('>=', (2,0,0))
Requirement = tuple[str, str, Version]            # (pkg, op, target)
Catalog = dict[str, dict[Version, list[Requirement]]]


# ---------------------------------------------------------------------------
# Part 1 — parse
# ---------------------------------------------------------------------------

_OPS = (">=", "<=", "==", "!=", ">", "<")


def parse_version(s: str) -> Version:
    a, b, c = s.split(".")
    return int(a), int(b), int(c)


def _parse_constraint(token: str) -> tuple[str, Version]:
    for op in _OPS:
        if token.startswith(op):
            return op, parse_version(token[len(op):])
    raise ValueError(f"no operator in {token!r}")


def parse_catalog(lines: list[str]) -> Catalog:
    """Each line is either:
        "A 1.0.0"                       — package version with no deps
        "A 1.0.0 requires B>=2.0.0"     — single requirement
        "A 1.0.0 requires B>=2.0.0, C==1.5.0"  — multiple, comma-separated
    """
    catalog: Catalog = {}
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        head, _, tail = line.partition(" requires ")
        pkg, ver_str = head.split()
        ver = parse_version(ver_str)
        reqs: list[Requirement] = []
        if tail:
            for tok in tail.split(","):
                tok = tok.strip()
                dep_pkg, rest = tok[0], tok[1:]
                # Find where the operator starts. Cleanest: scan for first OP char.
                # Simpler: package name is letters/digits, ops start at first <>= or !.
                for i, ch in enumerate(tok):
                    if ch in "<>=!":
                        dep_pkg = tok[:i]
                        op, target = _parse_constraint(tok[i:])
                        reqs.append((dep_pkg, op, target))
                        break
        catalog.setdefault(pkg, {})[ver] = reqs
    return catalog


# ---------------------------------------------------------------------------
# Part 2 — queries
# ---------------------------------------------------------------------------


def _satisfies(version: Version, op: str, target: Version) -> bool:
    if op == "==": return version == target
    if op == "!=": return version != target
    if op == ">=": return version >= target
    if op == "<=": return version <= target
    if op == ">":  return version >  target
    if op == "<":  return version <  target
    raise ValueError(op)


def direct_dependencies(
    catalog: Catalog, pkg: str, version: Version,
) -> list[Requirement]:
    return list(catalog[pkg][version])


def _latest_satisfying(catalog: Catalog, pkg: str, op: str, target: Version) -> Optional[Version]:
    """Pick the highest version of `pkg` satisfying op/target. None if none fit."""
    candidates = [v for v in catalog.get(pkg, {}) if _satisfies(v, op, target)]
    return max(candidates) if candidates else None


def transitive_dependencies(
    catalog: Catalog, pkg: str, version: Version,
) -> set[tuple[str, Version]]:
    """BFS over deps using latest-version-wins. Raises if a constraint can't be met."""
    seen: set[tuple[str, Version]] = {(pkg, version)}
    queue: deque[tuple[str, Version]] = deque([(pkg, version)])
    while queue:
        p, v = queue.popleft()
        for dep_pkg, op, target in catalog[p][v]:
            chosen = _latest_satisfying(catalog, dep_pkg, op, target)
            if chosen is None:
                raise ValueError(f"unsatisfiable: {p}@{v} needs {dep_pkg}{op}{target}")
            node = (dep_pkg, chosen)
            if node not in seen:
                seen.add(node)
                queue.append(node)
    return seen


# ---------------------------------------------------------------------------
# Part 3 — install order (Kahn's BFS)
# ---------------------------------------------------------------------------


def install_order(
    catalog: Catalog, pkg: str, version: Version,
) -> Optional[list[tuple[str, Version]]]:
    """Topological install order rooted at (pkg, version). None on cycle."""
    nodes = transitive_dependencies(catalog, pkg, version)

    # Build adjacency: edge node → dep means "node requires dep" so dep installs first.
    # Indegree of node X = number of nodes that depend on X. Kahn pops zero-indegree.
    # We want deps first → reverse the relation: predecessor[X] = things X depends on.
    indegree: dict[tuple[str, Version], int] = {n: 0 for n in nodes}
    edges: dict[tuple[str, Version], list[tuple[str, Version]]] = {n: [] for n in nodes}
    for p, v in nodes:
        for dep_pkg, op, target in catalog[p][v]:
            chosen = _latest_satisfying(catalog, dep_pkg, op, target)
            assert chosen is not None  # transitive_dependencies would have raised
            dep_node = (dep_pkg, chosen)
            edges[dep_node].append((p, v))  # dep → dependent
            indegree[(p, v)] += 1

    queue: deque[tuple[str, Version]] = deque(
        n for n, d in indegree.items() if d == 0
    )
    order: list[tuple[str, Version]] = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for m in edges[n]:
            indegree[m] -= 1
            if indegree[m] == 0:
                queue.append(m)

    if len(order) != len(nodes):
        return None  # cycle
    return order


# ---------------------------------------------------------------------------
# Part 4 — resolver (DFS + backtrack over version candidates)
# ---------------------------------------------------------------------------


def resolve(
    catalog: Catalog, requirements: list[Requirement],
) -> Optional[dict[str, Version]]:
    """Find an assignment {pkg: version} satisfying every requirement
    transitively and consistently. None if UNSAT.

    Dumb strategy: DFS over packages, try each candidate version (latest
    first) of the next package, accumulate that version's requirements
    into the working set, recurse. Backtrack on any conflict.
    """
    constraints_per_pkg: dict[str, list[Constraint]] = {}
    for pkg, op, target in requirements:
        constraints_per_pkg.setdefault(pkg, []).append((op, target))

    assignment: dict[str, Version] = {}

    def _candidates(pkg: str) -> list[Version]:
        # Latest-first so the "happy path" finds an answer fast.
        if pkg not in catalog:
            return []
        return sorted(catalog[pkg], reverse=True)

    def _consistent(pkg: str, version: Version) -> bool:
        return all(_satisfies(version, op, t) for op, t in constraints_per_pkg.get(pkg, ()))

    def _dfs() -> bool:
        # Pick any unassigned constrained package. If all constrained packages
        # are assigned, we're done — extending to their transitive deps below.
        for pkg in constraints_per_pkg:
            if pkg in assignment:
                continue
            for cand in _candidates(pkg):
                if not _consistent(pkg, cand):
                    continue
                # Snapshot the constraint table so we can revert on backtrack.
                snapshot = {p: list(cs) for p, cs in constraints_per_pkg.items()}
                assignment[pkg] = cand
                # Add this version's requirements to the constraint set.
                ok = True
                for dep_pkg, op, target in catalog[pkg][cand]:
                    constraints_per_pkg.setdefault(dep_pkg, []).append((op, target))
                    # If the dep is already assigned, check compatibility now.
                    if dep_pkg in assignment and not _satisfies(assignment[dep_pkg], op, target):
                        ok = False
                        break
                if ok and _dfs():
                    return True
                # backtrack
                del assignment[pkg]
                constraints_per_pkg.clear()
                constraints_per_pkg.update(snapshot)
            return False  # no candidate worked for this package
        return True  # all constrained packages assigned consistently

    if not _dfs():
        return None
    return dict(assignment)
