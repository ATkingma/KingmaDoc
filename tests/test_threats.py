"""Threat models from Microsoft's SDL TM Knowledge Base (``kingmadoc threats``)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.exceptions import ThreatModelError
from kingmadoc.threats.filters import Subject, matches
from kingmadoc.threats.knowledge_base import load_knowledge_base
from kingmadoc.threats.model import STATES, generate_threats, parse_threat_model
from kingmadoc.threats.report import render_diagram, render_report

KB = load_knowledge_base()

CONTACT_FORM = {
    "title": "Contact form",
    "elements": [
        {"name": "Visitor", "type": "Human User"},
        {"name": "Contact API", "type": "Web Application"},
        {"name": "Messages", "type": "SQL Database"},
    ],
    "boundaries": [{"name": "Internet Boundary", "contains": ["Contact API", "Messages"]}],
    "flows": [
        {"name": "Form post", "from": "Visitor", "to": "Contact API"},
        {"name": "Store message", "from": "Contact API", "to": "Messages", "type": "Binary"},
    ],
}


def _threats(data: dict) -> dict[str, list[str]]:
    """Flow name -> the knowledge base IDs of its threats."""
    model = parse_threat_model(data, KB)
    result: dict[str, list[str]] = {}
    for threat in generate_threats(model, KB):
        result.setdefault(threat.flow.name, []).append(threat.type_id)
    return result


def test_knowledge_base_is_microsofts_with_its_license() -> None:
    """Imported from microsoft/threat-modeling-templates; the MIT notice travels along."""
    assert KB.name == "SDL TM Knowledge Base (Core)"
    assert "github.com/microsoft/threat-modeling-templates" in KB.url
    assert "Copyright (c) Microsoft Corporation" in KB.license
    assert set(KB.categories) >= {"S", "T", "R", "I", "D", "E"}
    assert len(KB.threats) >= 40
    assert KB.element_type("web application").id == "SE.P.TMCore.WebApp"
    assert KB.ancestors("SE.P.TMCore.WebApp") == ("SE.P.TMCore.WebApp", "GE.P")


def _subject(source: str = "GE.EI", target: str = "GE.P", crosses: frozenset = frozenset(),
             **properties: str) -> Subject:
    return Subject(
        types={"source": KB.ancestors(source), "target": KB.ancestors(target),
               "flow": KB.ancestors("GE.DF")},
        properties={"source": {}, "target": {}, "flow": properties},
        crosses=crosses, default=KB.default,
    )


def test_filters_follow_the_tools_language() -> None:
    """Types include their parents; `and` binds tighter than `or`; defaults apply."""
    subject = _subject("SE.EI.TMCore.User", crosses=frozenset({"GE.TB.L"}))

    assert matches("source is 'GE.EI' and target is 'GE.P'", subject)
    assert not matches("source is 'GE.P'", subject)
    assert matches("source is 'GE.P' and target is 'GE.DS' or target is 'GE.P'", subject)
    assert not matches("source is 'GE.P' and (target is 'GE.DS' or target is 'GE.P')", subject)
    assert matches("(flow crosses 'GE.TB.L' or flow crosses 'GE.TB.B')", subject)
    assert matches("flow.authenticatesSource is 'Not Selected'", subject)  # generic default
    http = Subject(types={**subject.types, "flow": KB.ancestors("SE.DF.TMCore.HTTP")},
                   properties=subject.properties, crosses=subject.crosses, default=KB.default)
    assert matches("flow.authenticatesSource is 'No'", http)  # the HTTP stencil's default
    assert matches("flow.authenticatesSource is 'Yes'", _subject(authenticatesSource="Yes"))
    assert not matches("", subject)


@pytest.mark.parametrize("bad", ["source is", "source is GE.P", "who is 'GE.P'",
                                 "(source is 'GE.P'", "source likes 'GE.P'",
                                 "source is 'GE.P' target"])
def test_invalid_filters_raise(bad: str) -> None:
    with pytest.raises(ThreatModelError):
        matches(bad, _subject())


def test_threats_per_interaction_like_the_tool() -> None:
    """A browser form over HTTPS into a web app, and the app writing to SQL."""
    threats = _threats(CONTACT_FORM)

    # Spoofing, XSS, repudiation, crash, interruption, impersonation, RCE, flow change, CSRF.
    assert threats["Form post"] == [
        "S3", "T13.1", "R6", "D3", "D4", "E5", "E6", "E7",
        "8404dcf5-bdd8-4902-abc2-3b6c967b0261",
    ]
    # HTTPS provides confidentiality and integrity: no sniffing or input validation threat.
    assert "I6" not in threats["Form post"] and "T1" not in threats["Form post"]
    assert threats["Store message"] == ["S7.1", "T7", "D2"]


def test_properties_and_flow_types_change_the_threats() -> None:
    """Plain HTTP can be sniffed; an authenticated source is not spoofed."""
    data = {**CONTACT_FORM, "flows": [
        {"name": "Form post", "from": "Visitor", "to": "Contact API", "type": "HTTP"},
    ]}
    assert {"I6", "T1"} <= set(_threats(data)["Form post"])

    visitor = {"name": "Visitor", "type": "Human User",
               "properties": {"authenticatesItself": "Yes"}}
    data["elements"] = [visitor, *CONTACT_FORM["elements"][1:]]
    assert "S3" not in _threats(data)["Form post"]


def test_no_boundary_crossed_means_fewer_threats() -> None:
    data = {**CONTACT_FORM, "boundaries": []}

    assert "D4" not in _threats(data)["Form post"]
    assert "R6" not in _threats(data)["Form post"]


@pytest.mark.parametrize("data", [
    {"elements": [{"name": "A", "type": "Toaster"}]},
    {"elements": [{"name": "A", "type": "HTTPS"}]},
    {"elements": [{"name": "A"}, {"name": "A"}]},
    {"elements": [{"name": "A"}], "flows": [{"from": "A", "to": "B"}]},
    {"elements": [{"name": "A"}, {"name": "B"}],
     "flows": [{"from": "A", "to": "B", "type": "SQL Database"}]},
    {"elements": [{"name": "A"}], "boundaries": [{"name": "X", "contains": ["B"]}]},
    {"elements": [{"name": "A"}], "boundaries": [{"name": "X", "type": "Web Server"}]},
])
def test_invalid_models_raise(data: dict) -> None:
    with pytest.raises(ThreatModelError):
        parse_threat_model(data, KB)


def test_report_has_the_tools_sections() -> None:
    model = parse_threat_model(CONTACT_FORM, KB)
    report = render_report(model, generate_threats(model, KB), KB)

    assert "| Contact API | Web Application (Process) | Internet Boundary |" in report
    assert f"| {' | '.join(STATES)} | Total |" in report
    assert "| 12 | 0 | 0 | 0 | 12 |" in report
    assert "### Interaction: Form post (Visitor → Contact API)" in report
    assert "| 1 | Spoofing the Visitor External Entity | Spoofing |" in report
    assert "| Potential SQL Injection Vulnerability for Messages | Tampering |" in report
    assert "MIT license" in report


@pytest.mark.parametrize(("fmt", "expected"), [
    ("d2", ['e1: "Visitor" {shape: person}', 'e2: "Contact API" {shape: circle}',
            "stroke: red; stroke-dash: 4", 'e1 -> b1.e2: "Form post [HTTPS]"']),
    ("mermaid", ['e2(("Contact API"))', 'e3[("Messages")]', 'subgraph b1["Internet Boundary"]',
                 "style b1 fill:none,stroke:#e00,stroke-dasharray:5 5"]),
    ("plantuml", ['usecase "Contact API" as e2', 'database "Messages" as e3',
                  "#line.dashed;line:red", 'e1 --> e2 : "Form post [HTTPS]"']),
])
def test_data_flow_diagram_in_every_format(fmt: str, expected: list[str]) -> None:
    diagram = render_diagram(parse_threat_model(CONTACT_FORM, KB), KB, fmt)

    assert diagram.startswith(f"```{fmt}\n")
    for part in expected:
        assert part in diagram, part


D2 = os.environ.get("D2_BIN") or shutil.which("d2")


@pytest.mark.skipif(D2 is None, reason="d2 not available")
def test_d2_diagram_compiles(tmp_path: Path) -> None:
    source = render_diagram(parse_threat_model(CONTACT_FORM, KB), KB, "d2")
    (tmp_path / "model.d2").write_text(source.split("\n", 1)[1].rsplit("```", 1)[0])

    subprocess.run([D2, str(tmp_path / "model.d2"), str(tmp_path / "model.svg")],  # noqa: S603
                   check=True, capture_output=True)


def test_cli_prints_diagram_and_report(tmp_path: Path) -> None:
    path = tmp_path / "threat-model.yml"
    path.write_text(
        "title: Contact form\n"
        "elements:\n  - {name: Visitor, type: Human User}\n"
        "  - {name: Contact API, type: Web Application}\n"
        "boundaries:\n  - {name: Internet Boundary, contains: [Contact API]}\n"
        "flows:\n  - {name: Form post, from: Visitor, to: Contact API}\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["threats", str(path), "--format", "mermaid"])

    assert result.exit_code == 0, result.output
    assert result.output.startswith("```mermaid\n")
    assert "### Interaction: Form post (Visitor → Contact API)" in result.output


def test_cli_lists_types_and_reports_errors(tmp_path: Path) -> None:
    listed = CliRunner().invoke(cli, ["threats", "--types"])
    assert "Process: Web Application (SE.P.TMCore.WebApp)" in listed.output
    assert "Data Flow: HTTPS (SE.DF.TMCore.HTTPS)" in listed.output
    assert "Trust Boundary: Internet Boundary (SE.TB.L.TMCore.Internet)" in listed.output

    bad = tmp_path / "bad.yml"
    bad.write_text("elements:\n  - {name: A, type: Toaster}\n", encoding="utf-8")
    result = CliRunner().invoke(cli, ["threats", str(bad)])
    assert result.exit_code == 1 and "Toaster" in result.output
    assert CliRunner().invoke(cli, ["threats"]).exit_code == 2


def test_skill_reference_is_the_current_knowledge_base() -> None:
    """skill/explaining-code/reference/threats.md equals a fresh build."""
    from kingmadoc.threats.report import catalog_markdown

    reference = (Path(__file__).resolve().parents[1] / "skill" / "explaining-code"
                 / "reference" / "threats.md").read_text(encoding="utf-8")
    assert reference == catalog_markdown(KB), "run scripts/build_threat_reference.py"
    assert "| S3 | Spoofing | Spoofing the {source.Name} External Entity |" in reference
