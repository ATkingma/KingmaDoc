"""Every diagram backend renders the same fixed input; outputs are compared to snapshots.

Snapshots live in ``tests/fixtures/backends/<format>/<diagram>.<ext>``. After an intended output
change, regenerate them with ``KINGMADOC_UPDATE_SNAPSHOTS=1 pytest`` and review the diff.

The snapshots were checked with the real tools. To re-check locally, put ``d2`` on
``PATH`` (or set ``D2_BIN``) and/or set ``PLANTUML_JAR`` (or put ``plantuml`` on
``PATH``); the ``*_compiles`` tests are skipped otherwise.
"""

import os
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.config import DIAGRAM_FORMATS, parse_config
from kingmadoc.diagrams import BACKENDS, get_backend
from kingmadoc.diagrams.base import DiagramBackend
from kingmadoc.exceptions import ConfigError, DiagramError

FIXTURES = Path(__file__).parent / "fixtures" / "backends"
EXTENSIONS = {"mermaid": "mmd", "plantuml": "puml", "d2": "d2"}

# One fixed input per diagram type, with characters every backend must escape:
# quotes, backslash, $, ;, #, a D2 keyword as a name ("Label"), and a container
# named like its system (edges must target the container, not the boundary).
INPUTS: dict[str, Callable[[DiagramBackend], str]] = {
    "context": lambda b: b.render_context(
        'Web "Shop"',
        [{"name": "Customer", "description": 'Buys "things" for $5; 100% #1'}],
        [{"name": "Stripe", "description": "Card payments"}, {"name": "Label"}],
        system_description="Sells C:\\stuff",
    ),
    "container": lambda b: b.render_container(
        "Shop",
        [
            {"name": "Web", "tech": "React", "description": 'Storefront, a "SPA"'},
            {"name": "API", "tech": "FastAPI", "description": "Orders; ${id}"},
            {"name": "Shop", "tech": "Python"},
        ],
        relationships=[
            ("Customer", "Web", "Visits"),
            ("Web", "API", 'Calls "/orders"'),
            ("API", "Shop", "Delegates"),
        ],
        external_actors=[{"name": "Customer"}],
    ),
    "component": lambda b: b.render_component(
        "API",
        [
            {"name": "OrderRouter", "tech": "FastAPI", "description": "HTTP routes"},
            {"name": "OrderRepo", "tech": "SQLAlchemy", "description": "Persistence"},
        ],
        relationships=[("OrderRouter", "OrderRepo", "Reads/writes")],
    ),
    "sequence": lambda b: b.render_sequence(
        'Login "flow"',
        [{"name": "Web App"}, {"name": "API"}, {"name": "Label"}],
        [
            ("Web App", "API", 'POST /login; body {"user": "a"} #1'),
            ("API", "Label", "Check $user"),
            ("API", "Web App", "200 OK"),
        ],
    ),
    "class": lambda b: b.render_class(
        "Domain",
        [
            {
                "name": "User",
                "attributes": ["+id: int", "-email: str"],
                "methods": ["+login(password: str): bool", "+logout()"],
            },
            {"name": "Admin"},
            {"name": "Session", "attributes": ["+token: str"]},
            {"name": "Mailer"},
        ],
        [
            ("Admin", "User", "inherits", ""),
            ("User", "Session", "composition", "owns"),
            ("User", "Mailer", "dependency", "uses"),
            ("Session", "Mailer", "association", ""),
            ("Admin", "Session", "aggregation", "audits"),
        ],
    ),
}

CASES = [(fmt, kind) for fmt in DIAGRAM_FORMATS for kind in INPUTS]


def _snapshot(fmt: str, kind: str) -> Path:
    return FIXTURES / fmt / f"{kind}.{EXTENSIONS[fmt]}"


def _body(output: str, fmt: str) -> str:
    """The diagram source inside the fenced block."""
    match = re.fullmatch(rf"```{fmt}\n(.*)\n```", output, re.S)
    assert match, f"not a single fenced {fmt} block:\n{output}"
    return match.group(1)


def test_registry_matches_config() -> None:
    """Every configurable format has a backend, and every backend follows the protocol."""
    assert tuple(BACKENDS) == DIAGRAM_FORMATS
    for backend in BACKENDS.values():
        assert isinstance(backend, DiagramBackend)
        assert backend.LABEL


@pytest.mark.parametrize(("fmt", "kind"), CASES)
def test_snapshot(fmt: str, kind: str) -> None:
    """Fixed input → exactly the reviewed output, as one fenced block."""
    output = INPUTS[kind](get_backend(fmt))
    _body(output, fmt)
    path = _snapshot(fmt, kind)
    if os.environ.get("KINGMADOC_UPDATE_SNAPSHOTS"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")

    assert output == path.read_text(encoding="utf-8").rstrip("\n")


@pytest.mark.parametrize("fmt", DIAGRAM_FORMATS)
def test_errors_are_the_same_for_every_backend(fmt: str) -> None:
    """Validation lives in the shared model, so all backends reject the same input."""
    backend = get_backend(fmt)
    with pytest.raises(DiagramError, match="unknown element"):
        backend.render_sequence("T", [{"name": "A"}], [("A", "B", "x")])
    with pytest.raises(DiagramError, match="without a name"):
        backend.render_container("S", [{"tech": "Python"}])
    with pytest.raises(DiagramError, match="Unknown class relationship"):
        backend.render_class("T", [{"name": "A"}, {"name": "B"}], [("A", "B", "likes", "")])


def test_unknown_format() -> None:
    """Unknown formats fail clearly, both in the config and in the registry."""
    with pytest.raises(ConfigError, match="diagram_format 'graphviz'.*mermaid, plantuml, d2"):
        parse_config({"diagram_format": "graphviz"})
    with pytest.raises(DiagramError, match="graphviz"):
        get_backend("graphviz")
    assert parse_config({}).diagram_format == "mermaid"


@pytest.mark.parametrize(("fmt", "label"), [("mermaid", "Mermaid"), ("plantuml", "PlantUML"), ("d2", "D2")])
def test_plan_uses_configured_backend(tmp_path: Path, fmt: str, label: str) -> None:
    """`plan` renders every diagram, including extra-doc placeholders, in the chosen format."""
    (tmp_path / ".featuredoc.yml").write_text(
        f"diagram_format: {fmt}\n"
        "extra_designs:\n  functional_design: {enabled: true}\n  technical_design: {enabled: true}\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input", "--stdout"]
    )

    assert result.exit_code == 0, result.output
    assert f"## C4 Context ({label})" in result.stdout
    assert f"## C4 Container ({label})" in result.stdout
    fences = re.findall(r"^```(\w+)$", result.stdout, re.M)
    diagram_fences = [f for f in fences if f != "text"]
    assert diagram_fences == [fmt] * 4  # context, container, user flow, ER


def _plantuml() -> list[str] | None:
    jar = os.environ.get("PLANTUML_JAR")
    if jar and shutil.which("java"):
        return ["java", "-jar", jar]
    return [shutil.which("plantuml")] if shutil.which("plantuml") else None


def _d2() -> str | None:
    return os.environ.get("D2_BIN") or shutil.which("d2")


@pytest.mark.skipif(_plantuml() is None, reason="PlantUML not available")
@pytest.mark.parametrize("kind", INPUTS)
def test_plantuml_compiles(tmp_path: Path, kind: str) -> None:
    """PlantUML renders the snapshot without errors (C4-PlantUML is bundled)."""
    source = tmp_path / f"{kind}.puml"
    source.write_text(_body(INPUTS[kind](get_backend("plantuml")), "plantuml"), encoding="utf-8")

    result = subprocess.run(
        [*_plantuml(), "-tsvg", "-failfast2", str(source)], capture_output=True, text=True
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(_d2() is None, reason="d2 not available")
@pytest.mark.parametrize("kind", INPUTS)
def test_d2_compiles(tmp_path: Path, kind: str) -> None:
    """D2 compiles the snapshot without errors."""
    source = tmp_path / f"{kind}.d2"
    source.write_text(_body(INPUTS[kind](get_backend("d2")), "d2"), encoding="utf-8")

    result = subprocess.run(
        [_d2(), str(source), str(tmp_path / f"{kind}.svg")], capture_output=True, text=True
    )

    assert result.returncode == 0, result.stdout + result.stderr
