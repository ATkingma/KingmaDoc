"""The dominator tree of a module dependency graph (pure).

Module A dominates B when every import path from an entry point to B goes through A:
B is then private to A, and A is the only reason B is in the program. The dominator
tree groups a codebase into the parts that really belong together (Falke and Klein,
"The Dominance Tree in Visualizing Software Dependencies"). Entry points are the modules
that nothing imports; a virtual root sits above them, so what several entry points
share belongs to no single module.
"""

from __future__ import annotations

from collections.abc import Iterable

Edge = tuple[str, str]
_ROOT = "\x00root"


def immediate_dominators(edges: Iterable[Edge]) -> dict[str, str | None]:
    """Return each reachable module's immediate dominator (None: only the entry points).

    Uses the iterative algorithm of Cooper, Harvey and Kennedy ("A Simple, Fast
    Dominance Algorithm"), which handles cycles.

    Args:
        edges: ``(importer, imported)`` pairs.

    Returns:
        Module -> its immediate dominator, or None when that is the virtual root.
    """
    edge_list = [(a, b) for a, b in edges if a != b]
    nodes = {n for edge in edge_list for n in edge}
    imported = {b for _, b in edge_list}
    successors: dict[str, list[str]] = {n: [] for n in nodes | {_ROOT}}
    for a, b in sorted(set(edge_list)):
        successors[a].append(b)
    successors[_ROOT] = sorted(nodes - imported)

    order = _postorder(successors)
    index = {node: i for i, node in enumerate(order)}
    predecessors: dict[str, list[str]] = {n: [] for n in order}
    for a, targets in successors.items():
        for b in targets:
            if a in index and b in index:
                predecessors[b].append(a)

    idom: dict[str, str] = {_ROOT: _ROOT}
    changed = True
    while changed:
        changed = False
        for node in reversed(order):  # reverse postorder
            if node == _ROOT:
                continue
            ready = [p for p in predecessors[node] if p in idom]
            if not ready:
                continue
            new = ready[0]
            for other in ready[1:]:
                new = _intersect(other, new, idom, index)
            if idom.get(node) != new:
                idom[node] = new
                changed = True
    return {n: (None if d == _ROOT else d) for n, d in idom.items() if n != _ROOT}


def private_modules(edges: Iterable[Edge]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return each module with the modules only it leads to (its dominator-tree children).

    Args:
        edges: ``(importer, imported)`` pairs.

    Returns:
        ``(owner, (private module, ...))`` pairs, sorted; owners without private
        modules, the modules the entry points share, and a single entry point (which
        trivially leads to everything) are left out.
    """
    idom = immediate_dominators(edges)
    entries = [node for node, owner in idom.items() if owner is None]
    children: dict[str, list[str]] = {}
    for node, owner in idom.items():
        if owner is not None and not (len(entries) == 1 and owner == entries[0]):
            children.setdefault(owner, []).append(node)
    return tuple((owner, tuple(sorted(kids))) for owner, kids in sorted(children.items()))


def _postorder(successors: dict[str, list[str]]) -> list[str]:
    """Nodes reachable from the root, children before parents (iterative DFS)."""
    order: list[str] = []
    seen = {_ROOT}
    stack = [(_ROOT, iter(successors[_ROOT]))]
    while stack:
        node, children = stack[-1]
        child = next(children, None)
        if child is None:
            stack.pop()
            order.append(node)
        elif child not in seen:
            seen.add(child)
            stack.append((child, iter(successors[child])))
    return order


def _intersect(a: str, b: str, idom: dict[str, str], index: dict[str, int]) -> str:
    while a != b:
        while index[a] < index[b]:
            a = idom[a]
        while index[b] < index[a]:
            b = idom[b]
    return a
