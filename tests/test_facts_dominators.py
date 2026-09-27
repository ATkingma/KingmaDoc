"""Tests for the dominator tree of a module graph: which modules are private to which."""

from hypothesis import given
from hypothesis import strategies as st

from kingmadoc.facts.dominators import immediate_dominators, private_modules


def test_a_chain_is_owned_by_its_start() -> None:
    """main -> a -> b: every path to b goes through a, and to a through main."""
    idom = immediate_dominators([("main", "a"), ("a", "b")])

    assert idom == {"main": None, "a": "main", "b": "a"}


def test_a_shared_module_belongs_to_nobody() -> None:
    """util is used by a and b: only the root reaches it on every path."""
    edges = [("main", "a"), ("main", "b"), ("a", "util"), ("b", "util"), ("a", "helper")]

    assert private_modules(edges) == (("a", ("helper",)),)


def test_a_single_entry_point_is_not_listed() -> None:
    """With one entry point, it trivially leads to everything: no information."""
    idom = immediate_dominators([("main", "a"), ("main", "b"), ("a", "util"), ("b", "util")])

    assert idom["util"] == "main"
    assert private_modules([("main", "a"), ("main", "b")]) == ()


def test_several_entry_points_share_the_root() -> None:
    """Two modules nothing imports (two entry points): what both reach is shared."""
    edges = [("cli", "core"), ("web", "core"), ("core", "db"), ("web", "views")]

    assert private_modules(edges) == (("core", ("db",)), ("web", ("views",)))


def test_cycles_are_handled() -> None:
    """Import cycles (a <-> b) do not loop forever."""
    edges = [("main", "a"), ("a", "b"), ("b", "a"), ("b", "c")]

    assert immediate_dominators(edges)["c"] == "b"


EDGES = st.lists(
    st.tuples(st.sampled_from("abcdefg"), st.sampled_from("abcdefg")).filter(
        lambda e: e[0] != e[1]
    ),
    max_size=14,
)


def _reachable(edges: list[tuple[str, str]], roots: set[str], removed: str) -> set[str]:
    seen, todo = set(), [r for r in roots if r != removed]
    while todo:
        node = todo.pop()
        if node in seen:
            continue
        seen.add(node)
        todo += [b for a, b in edges if a == node and b != removed]
    return seen


@given(EDGES)
def test_without_its_owner_a_private_module_is_unreachable(edges: list[tuple[str, str]]) -> None:
    """The definition of dominance: remove the owner and its modules cannot be reached."""
    nodes = {n for e in edges for n in e}
    roots = {n for n in nodes if not any(b == n for _, b in edges)}
    for owner, owned in private_modules(edges):
        assert not set(owned) & _reachable(edges, roots, owner), (owner, owned)
