"""The design docs' own diagrams compile with the real tools (skipped when absent).

The use case diagram (functional design) and the threat model's data flow diagram
(technical and security design) are written per diagram format; this renders every
diagram block of a generated plan with Mermaid CLI (``MMDC_BIN`` or ``mmdc``),
PlantUML (``PLANTUML_JAR`` or ``plantuml``) and D2 (``D2_BIN`` or ``d2``), including a
project name with quotes and a dollar sign.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from kingmadoc.cli import cli

EXTENSIONS = {"mermaid": "mmd", "plantuml": "puml", "d2": "d2"}


def _tool(fmt: str) -> list[str] | None:
    if fmt == "mermaid":
        mmdc = os.environ.get("MMDC_BIN") or shutil.which("mmdc")
        return [mmdc] if mmdc else None
    if fmt == "plantuml":
        jar = os.environ.get("PLANTUML_JAR")
        if jar and shutil.which("java"):
            return ["java", "-jar", jar]
        return [shutil.which("plantuml")] if shutil.which("plantuml") else None
    d2 = os.environ.get("D2_BIN") or shutil.which("d2")
    return [d2] if d2 else None


def _command(fmt: str, tool: list[str], source: Path) -> list[str]:
    if fmt == "mermaid":
        return [*tool, "-q", "-i", str(source), "-o", f"{source}.svg"]
    if fmt == "plantuml":
        return [*tool, "-tsvg", "-failfast2", str(source)]
    return [*tool, str(source), f"{source}.svg"]


@pytest.mark.parametrize("fmt", list(EXTENSIONS))
def test_every_design_diagram_compiles(tmp_path: Path, fmt: str) -> None:
    tool = _tool(fmt)
    if tool is None:
        pytest.skip(f"{fmt} tool not available")
    (tmp_path / ".featuredoc.yml").write_text(
        f"diagram_format: {fmt}\n"
        "project: {name: 'Bob \"The\" Shop $1'}\n"
        "extra_designs:\n  functional_design: {enabled: true}\n"
        "  technical_design: {enabled: true}\n  security_design: {enabled: true}\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        cli, ["plan", "Add login.", "--root", str(tmp_path), "--no-input", "--stdout"]
    )
    assert result.exit_code == 0, result.output
    blocks = re.findall(rf"^```{fmt}\n(.*?)\n```$", result.stdout, re.S | re.M)
    assert len(blocks) >= 6  # context, container, use cases, flow, ER, data flow (x2)

    for index, block in enumerate(blocks):
        source = tmp_path / f"diagram-{index}.{EXTENSIONS[fmt]}"
        source.write_text(block + "\n", encoding="utf-8")
        done = subprocess.run(_command(fmt, tool, source), capture_output=True, text=True,  # noqa: S603
                              check=False, timeout=180)
        assert done.returncode == 0, f"{block.splitlines()[0]}: {done.stderr or done.stdout}"
