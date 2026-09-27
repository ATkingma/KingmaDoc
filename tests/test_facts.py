"""Tests for `kingmadoc explain facts`: what a branch changed, and the collected facts."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from kingmadoc.cli import cli
from kingmadoc.exceptions import FactsError
from kingmadoc.facts.branch import branch_changes

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(root: Path, name: str, text: str) -> None:
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text, encoding="utf-8")


def _repo(tmp_path: Path) -> Path:
    """main: app/models.py (Django) and Api/Api.csproj; branch feature: two commits."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    _write(tmp_path, "app/models.py", (
        "from django.db import models\n\n"
        "class Order(models.Model):\n    total = models.DecimalField()\n"
    ))
    _write(tmp_path, "Api/Api.csproj", '<ProjectReference Include="..\\Data\\Data.csproj" />')
    _write(tmp_path, "Data/Data.csproj", "<Project />")
    _write(tmp_path, "app/old.py", "x = 1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "init")
    _git(tmp_path, "checkout", "-qb", "feature")
    _write(tmp_path, "app/new.py", "a = 1\nb = 2\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "Add new module")
    _git(tmp_path, "rm", "-q", "app/old.py")
    _git(tmp_path, "commit", "-qm", "Remove old module")
    return tmp_path


def _facts(root: Path, *extra: str) -> Result:
    return CliRunner().invoke(cli, ["explain", "facts", "--root", str(root), *extra])


def test_branch_changes_lists_commits_and_files(tmp_path: Path) -> None:
    """Commits since the merge base (oldest first) and each file with its line counts."""
    root = _repo(tmp_path)

    changes = branch_changes(root, "main")

    assert changes.head == "feature" and changes.base == "main"
    assert [subject for _, subject in changes.commits] == ["Add new module", "Remove old module"]
    files = {f.path: (f.status, f.added, f.removed) for f in changes.files}
    assert files == {"app/new.py": ("A", 2, 0), "app/old.py": ("D", 0, 1)}


def test_uncommitted_changes_count_as_well(tmp_path: Path) -> None:
    """Work in progress on the branch is part of what it changes."""
    root = _repo(tmp_path)
    _write(root, "app/models.py", "changed\n")

    files = {f.path: f.status for f in branch_changes(root, "main").files}

    assert files["app/models.py"] == "M"


def test_unknown_base_is_an_error(tmp_path: Path) -> None:
    """A base git does not know is reported, not a crash."""
    root = _repo(tmp_path)

    with pytest.raises(FactsError, match="nope"):
        branch_changes(root, "nope")


def test_cli_facts_markdown(tmp_path: Path) -> None:
    """The facts in Markdown: stack, project references, data model and the branch."""
    root = _repo(tmp_path)

    result = _facts(root, "--base", "main")

    assert result.exit_code == 0, result.output
    text = result.output
    assert "## Project references" in text and "Api → Data" in text
    assert "## Data model" in text and "Order" in text and "total: DecimalField" in text
    assert "`app/models.py`" in text
    assert "## Branch feature (compared with main)" in text
    assert "Remove old module" in text and "| D | `app/old.py` | +0 | −1 |" in text


def test_cli_facts_json(tmp_path: Path) -> None:
    """--json gives the same facts for tools."""
    root = _repo(tmp_path)

    result = _facts(root, "--json", "--base", "main")

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["project_references"] == [["Api", "Data"]]
    assert data["data_model"][0]["name"] == "Order"
    assert data["data_model"][0]["fields"] == [{"name": "total", "type": "DecimalField"}]
    assert data["branch"]["commits"][1]["subject"] == "Remove old module"
    assert data["commit"] == _git(root, "rev-parse", "--short", "HEAD")


def test_cli_facts_without_a_branch_or_git(tmp_path: Path) -> None:
    """Without --base there is no branch section; outside git there is no commit."""
    _write(tmp_path, "main.py", "print(1)\n")

    result = _facts(tmp_path)

    assert result.exit_code == 0, result.output
    assert "## Branch" not in result.output
    assert "## Data model" in result.output and "none found" in result.output


def test_cli_facts_unknown_base(tmp_path: Path) -> None:
    """An unknown --base exits with 1 and says why."""
    result = _facts(_repo(tmp_path), "--base", "nope")

    assert result.exit_code == 1
    assert "nope" in result.output


def test_tests_are_not_part_of_the_data_model(tmp_path: Path) -> None:
    """Model classes in tests (fixtures, test strings) are not the project's data model."""
    _write(tmp_path, "tests/test_models.py", (
        'SOURCE = """\nclass Fake(models.Model):\n    x = models.IntegerField()\n"""\n'
    ))
    _write(tmp_path, "src/app/order.spec.ts", "@Entity()\nclass SpecOnly {\n}\n")
    _write(
        tmp_path, "src/app/models.py", "class Real(models.Model):\n    x = models.IntegerField()\n"
    )

    data = json.loads(_facts(tmp_path, "--json").output)

    assert [e["name"] for e in data["data_model"]] == ["Real"]


def test_routes_services_and_js_modules_are_reported(tmp_path: Path) -> None:
    """A .NET API with a Next.js front end: routes with access, DI services, TS imports."""
    _write(tmp_path, "Api/Program.cs", (
        "builder.Services.AddScoped<IContactNotifier, MailNotifier>();\n"
        'app.MapGet("/health", () => "OK");\n'
    ))
    _write(tmp_path, "Api/Controllers/ContactController.cs", (
        "[ApiController]\npublic class ContactController : ControllerBase\n{\n"
        '    [HttpPost("api/contact")]\n    [EnableRateLimiting("contact")]\n'
        "    public IActionResult Send() => Ok();\n}\n"
    ))
    _write(tmp_path, "web/tsconfig.json", '{"compilerOptions": {"paths": {"@/*": ["./*"]}}}')
    _write(tmp_path, "web/app/page.tsx", 'import Footer from "@/components/footer";\n')
    _write(tmp_path, "web/components/footer.tsx", "export default function Footer() {}\n")
    _write(tmp_path, "web/.next/server/app/page.js", 'import x from "./chunk";\n')

    result = _facts(tmp_path)
    data = json.loads(_facts(tmp_path, "--json").output)

    assert result.exit_code == 0, result.output
    text = result.output
    assert "## Routes and access" in text
    assert "| POST | `/api/contact` | ContactController.Send | rate limit contact |" in text
    assert "| PAGE | `/` | `web/app/page.tsx` |" in text
    assert "## Services (dependency injection)" in text
    assert "- IContactNotifier → MailNotifier (scoped, `Api/Program.cs`)" in text
    assert "## JavaScript/TypeScript module dependencies" in text
    assert "- web/app/page → web/components/footer" in text
    assert ".next" not in text
    assert data["routes"][0]["path"] == "/"
    assert data["services"][0]["contract"] == "IContactNotifier"
    assert data["js_dependencies"] == [["web/app/page", "web/components/footer"]]
