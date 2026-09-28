"""Tests for the security_design and domain_design documents (roadmap WP8)."""

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc.cli import cli

FEATURES = Path("docs") / "features"


def _plan(root: Path, config: str, *extra: str) -> Result:
    (root / ".featuredoc.yml").write_text(config, encoding="utf-8")
    (root / "api").mkdir(exist_ok=True)
    (root / "api" / "main.py").write_text("import fastapi\n", encoding="utf-8")
    (root / "requirements.txt").write_text("fastapi\npsycopg2\n", encoding="utf-8")
    return CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(root), "--no-input", *extra]
    )


ALL = (
    "extra_designs:\n"
    "  functional_design: {enabled: true}\n"
    "  domain_design: {enabled: true}\n"
    "  technical_design: {enabled: true}\n"
    "  security_design: {enabled: true}\n"
)


def test_documents_are_written_in_order(tmp_path: Path) -> None:
    """All four extra designs: what (functional, domain), then how (technical, security)."""
    result = _plan(tmp_path, ALL)

    assert result.exit_code == 0, result.output
    names = [Path(line).name for line in result.stdout.splitlines()]
    assert names == [
        "add-login-plan.md",
        "add-login-functional-design.md",
        "add-login-domain-design.md",
        "add-login-technical-design.md",
        "add-login-security-design.md",
    ]


def test_disabled_by_default(tmp_path: Path) -> None:
    """Without configuration, neither new document is written."""
    result = _plan(tmp_path, "{}\n")

    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (tmp_path / FEATURES).iterdir()) == ["add-login-plan.md"]


def test_security_design_models(tmp_path: Path) -> None:
    """Threat model (Threat Modeling Tool style, inferred elements) and permissions matrix."""
    assert _plan(tmp_path, "extra_designs:\n  security_design: {enabled: true}\n").exit_code == 0

    doc = (tmp_path / FEATURES / "add-login-security-design.md").read_text(encoding="utf-8")
    assert doc.startswith("# Security design: Add login.\n")
    assert doc.index("## Threat model") < doc.index("## Permissions: who may do what")
    # Generated from Microsoft's knowledge base for the inferred data flow diagram.
    assert "| Spoofing the User External Entity | Spoofing |" in doc
    assert "| Potential SQL Injection Vulnerability for PostgreSQL | Tampering |" in doc
    assert "SDL TM Knowledge Base (Core)" in doc
    assert "| api | Web Application (Process) | Internet Boundary |" in doc  # inferred elements


@pytest.mark.parametrize(("fmt", "fence"), [("mermaid", "mermaid"), ("plantuml", "plantuml"),
                                            ("d2", "d2")])
def test_domain_design_models(tmp_path: Path, fmt: str, fence: str) -> None:
    """The domain model is a diagram in the configured format; event storming follows."""
    config = f"diagram_format: {fmt}\nextra_designs:\n  domain_design: {{enabled: true}}\n"
    assert _plan(tmp_path, config).exit_code == 0

    doc = (tmp_path / FEATURES / "add-login-domain-design.md").read_text(encoding="utf-8")
    assert doc.startswith("# Domain design: Add login.\n")
    model = doc[doc.index("## Domain model"):doc.index("## Event storming")]
    assert f"```{fence}\n" in model
    assert "Domain event (past tense)" in doc


def test_models_subset_and_empty(tmp_path: Path) -> None:
    """`models:` picks sections; an empty list says so instead of leaving a blank doc."""
    config = (
        "extra_designs:\n"
        "  security_design: {enabled: true, models: [permissions]}\n"
        "  domain_design: {enabled: true, models: []}\n"
    )
    assert _plan(tmp_path, config).exit_code == 0

    security = (tmp_path / FEATURES / "add-login-security-design.md").read_text(encoding="utf-8")
    domain = (tmp_path / FEATURES / "add-login-domain-design.md").read_text(encoding="utf-8")
    assert "## Permissions" in security and "## Threat model" not in security
    assert "_No models selected" in domain
