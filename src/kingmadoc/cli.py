"""Command-line interface: ``kingmadoc init | analyze | plan | verify | adr | render``."""

from __future__ import annotations

import io
import json
import sys
from datetime import date, datetime
from pathlib import Path

import click

from kingmadoc.about import version_text
from kingmadoc.adr import STATUSES, adr_path, render_adr
from kingmadoc.config import CONFIG_FILENAME, MAX_FILES_LIMIT, default_config_yaml, load_config
from kingmadoc.d2_binary import ensure_d2
from kingmadoc.documents import write_document, write_documents
from kingmadoc.exceptions import KingmaDocError
from kingmadoc.explain import (
    EXPLAIN_DIR,
    EXPLAINER_FILE,
    explainer_folder,
    explainer_folders,
    freshness,
    index_markdown,
    index_path,
    is_generated_index,
    read_entries,
)
from kingmadoc.facts.branch import branch_changes
from kingmadoc.facts.collect import collect_facts, facts_markdown, facts_to_dict
from kingmadoc.git import short_head
from kingmadoc.plan.analyzer import (
    TEST_DIR_NAMES,
    CodebaseReport,
    analyze,
    format_report,
    report_to_dict,
)
from kingmadoc.plan.generator import (
    build_plan_context,
    build_questions,
    default_output_path,
    enabled_extra_designs,
    extra_design_path,
    infer_containers,
    needs_dependencies,
    render_extra_design,
    render_plan,
)
from kingmadoc.plandoc import check_plan, generated_at, parse_plan, set_status
from kingmadoc.render import dark_mode_warnings, render_file
from kingmadoc.skills import AGENT_DIRS, install_skills
from kingmadoc.verify.changes import detect_changes
from kingmadoc.verify.commands import MARKER_FILES, detect_commands, run_check
from kingmadoc.verify.deviations import (
    Deviation,
    find_deviations,
    mentioned_requirements,
    planned_containers,
)
from kingmadoc.verify.locate import find_plan, verify_output_path
from kingmadoc.verify.report import render_verify, verify_status
from kingmadoc.vscode import enable_markdown_preview, preview_enabled

ROOT_OPTION = click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Project root to analyze.",
)


@click.group()
@click.option(
    "--version",
    is_flag=True,
    expose_value=False,
    is_eager=True,
    callback=lambda ctx, _param, value: _print_version(ctx, value),
    help="Show the version (and the installed commit) and exit.",
)
def cli() -> None:
    """KingmaDoc: feature plan docs before you build, verification docs after."""


def _print_version(ctx: click.Context, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"kingmadoc, version {version_text()}")
    ctx.exit()


@cli.command()
@ROOT_OPTION
@click.option("--force", is_flag=True, help=f"Overwrite an existing {CONFIG_FILENAME}.")
def init(root: Path, force: bool) -> None:
    """Create a default .featuredoc.yml in the project root."""
    target = root / CONFIG_FILENAME
    if target.exists() and not force:
        raise click.ClickException(f"{target} already exists (use --force to overwrite)")
    target.write_text(default_config_yaml(), encoding="utf-8")
    click.echo(f"Created {target}")


@cli.command()
@click.argument("description")
@ROOT_OPTION
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=f"Config file (default: <root>/{CONFIG_FILENAME}).",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output file (default: <output_dir>/<slug>-plan.md).",
)
@click.option(
    "--no-input", is_flag=True, help="Don't ask; list the questions as open questions."
)
@click.option("--stdout", "to_stdout", is_flag=True, help="Print the doc instead of writing it.")
@click.option("--force", is_flag=True, help="Overwrite an existing output file.")
def plan(
    description: str,
    root: Path,
    config_path: Path | None,
    output: Path | None,
    no_input: bool,
    to_stdout: bool,
    force: bool,
) -> None:
    """Analyze the codebase and write a plan doc for the feature in DESCRIPTION.

    The doc goes to <output_dir>/<slug>-plan.md (slug derived from DESCRIPTION) and its
    path is printed. Extra docs enabled under extra_designs in the config
    (<slug>-functional-design.md, <slug>-technical-design.md) are written next to it,
    one printed path per line. To see only the codebase analysis, use `kingmadoc analyze`.
    """
    try:
        config = load_config(root, config_path)
        report = analyze(root, config.analyzer, with_dependencies=needs_dependencies(config))
        _warn_if_truncated(report)

        questions = build_questions(report, config)
        answers = [(q, "") for q in questions] if no_input else _ask(questions)
        context = build_plan_context(
            description, report, config, now=datetime.now().astimezone(), answers=answers
        )
        path = output or default_output_path(report.root, config, description)
        documents = [(path, render_plan(context, config))]
        documents += [
            (
                extra_design_path(design, path),
                render_extra_design(design, context, config, path),
            )
            for design in enabled_extra_designs(config)
        ]

        if to_stdout:
            # Extra docs follow the plan, separated by a horizontal rule.
            click.echo("\n---\n\n".join(content for _, content in documents), nl=False)
            return
        written = write_documents(documents, overwrite=force)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc

    for written_path in written:
        click.echo(written_path)


@cli.command("analyze")
@ROOT_OPTION
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=f"Config file (default: <root>/{CONFIG_FILENAME}).",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as JSON.")
def analyze_command(root: Path, config_path: Path | None, as_json: bool) -> None:
    """Analyze the codebase and print the report (languages, entry points, stack, ...)."""
    try:
        config = load_config(root, config_path)
        report = analyze(root, config.analyzer, with_dependencies=True)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc
    _warn_if_truncated(report)
    if as_json:
        click.echo(json.dumps(report_to_dict(report), indent=2))
    else:
        click.echo(format_report(report))


def _warn_if_truncated(report: CodebaseReport) -> None:
    if report.truncated:
        click.echo(
            f"Warning: stopped after {report.file_count} files; the analysis is "
            f"incomplete (analyzer.max_files, at most {MAX_FILES_LIMIT}).",
            err=True,
        )


def _ask(questions: list[str]) -> list[tuple[str, str]]:
    """Prompt for each question on stderr; unasked questions keep an empty answer."""
    if questions:
        click.echo("Answer a few questions (press Enter to skip):", err=True)
    answers: list[tuple[str, str]] = []
    for question in questions:
        try:
            answer = click.prompt(question, default="", show_default=False, err=True)
        except click.Abort:
            # EOF on non-interactive stdin (e.g. an AI agent): keep going.
            if sys.stdin.isatty():
                raise
            click.echo("\nstdin closed; skipping remaining questions.", err=True)
            break
        answers.append((question, answer.strip()))
    return answers + [(q, "") for q in questions[len(answers):]]


@cli.command()
@click.argument("slug")
@ROOT_OPTION
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=f"Config file (default: <root>/{CONFIG_FILENAME}).",
)
@click.option("--force", is_flag=True, help="Overwrite an existing verification doc.")
@click.option(
    "--run-checks",
    is_flag=True,
    help="Also run the project's build, test and lint commands (runs the repository's code).",
)
def verify(
    slug: str, root: Path, config_path: Path | None, force: bool, run_checks: bool
) -> None:
    """Compare the code with plan SLUG and write SLUG-verify.md next to it.

    Looks at every file changed since the plan was generated (git, including uncommitted
    work): expected files never touched, changes outside the plan, requirements no test or
    commit mentions, and containers added or gone. Sets the plan's status to implemented
    or partial. Build, test and lint commands only run with --run-checks.
    """
    try:
        config = load_config(root, config_path)
        root = root.resolve()
        plan_path = find_plan(root, config, slug)
        output = verify_output_path(plan_path)
        if output.exists() and not force:
            raise KingmaDocError(f"{output} already exists; use --force to overwrite it")
        text = plan_path.read_text(encoding="utf-8")
        problems = check_plan(text, slug=slug)
        meta = None if problems else parse_plan(text)
        report = analyze(root, config.analyzer)
        docs_dir = plan_path.parent.relative_to(root).as_posix()
        changes = detect_changes(
            root, generated_at(text), ignore=(docs_dir + "/",),
            plan=plan_path.relative_to(root).as_posix(),
        )
        mentioned = mentioned_requirements(
            [changes.messages, *(_read_quietly(root / f) for f in report.files if _is_test(f))]
        )
        project_name = config.project.name or root.name
        current = tuple(c["name"] for c in infer_containers(report, project_name))
        deviations = find_deviations(
            meta, changes, mentioned, planned_containers(text), current
        )
        if problems:
            deviations = (
                Deviation("Process", "the plan passes `kingmadoc check`", problems[0], "Medium"),
                *deviations,
            )
        commands = detect_commands(_marker_files(root), {
            "build": config.verify.build, "test": config.verify.test, "lint": config.verify.lint,
        })
        timeout = config.verify.timeout
        results = [run_check(root, c, timeout) for c in commands] if run_checks else []
        plan_problem = "the plan has no valid frontmatter" if problems else None
        status = verify_status(changes, deviations, results, plan_problem)
        documents = [(output, render_verify(
            slug, plan_path.relative_to(root).as_posix(), now=datetime.now().astimezone(),
            status=status, changes=changes, deviations=deviations, commands=commands,
            results=results, plan_problem=plan_problem,
        ))]
        if meta is not None and meta.status != "draft" and status != "Not verified":
            new = "implemented" if status == "Matches plan" else "partial"
            documents.append((plan_path, set_status(text, new)))
        write_documents(documents, overwrite=True)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc

    failed = sum(r.passed is False for r in results)
    summary = f"{status}: {len(deviations)} deviation(s)"
    summary += f", {failed} failed check(s)" if results else ", checks not run (--run-checks)"
    click.echo(summary, err=True)
    click.echo(output)


def _is_test(path: Path) -> bool:
    return any(part in TEST_DIR_NAMES for part in path.parts[:-1]) or path.name.startswith(
        "test_"
    )


def _read_quietly(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _marker_files(root: Path) -> dict[str, str]:
    """The top-level files that name the project's commands (see detect_commands)."""
    names = [n for n in MARKER_FILES if (root / n).is_file()]
    names += [p.name for p in root.glob("*") if p.suffix in (".sln", ".csproj") and p.is_file()]
    return {name: _read_quietly(root / name) for name in names}


CONFIG_OPTION = click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=f"Config file (default: <root>/{CONFIG_FILENAME}).",
)


@cli.command()
@click.argument("slug")
@ROOT_OPTION
@CONFIG_OPTION
def check(slug: str, root: Path, config_path: Path | None) -> None:
    """Check plan SLUG: its frontmatter and requirement IDs (exit 1 on a problem)."""
    path, text = _read_plan(root, config_path, slug)
    problems = check_plan(text, slug=slug)
    if problems:
        raise click.ClickException(
            f"{path} has {len(problems)} problem(s):\n" + "\n".join(f"- {p}" for p in problems)
        )
    meta = parse_plan(text)
    count = len(meta.requirements)
    click.echo(f"{path}: OK ({meta.status}, {count} requirement{'s' if count != 1 else ''})")


@cli.command()
@click.argument("slug")
@ROOT_OPTION
@CONFIG_OPTION
def approve(slug: str, root: Path, config_path: Path | None) -> None:
    """Approve plan SLUG (status draft -> approved): the gate before writing code."""
    path, text = _read_plan(root, config_path, slug)
    problems = check_plan(text, slug=slug)
    if problems:
        raise click.ClickException(
            f"{path} is not approved; fix it first (kingmadoc check {slug}):\n"
            + "\n".join(f"- {p}" for p in problems)
        )
    status = parse_plan(text).status
    if status != "draft":
        raise click.ClickException(f"{path} is already {status}")
    try:
        write_document(path, set_status(text, "approved"), overwrite=True)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"{path}: approved")


def _read_plan(root: Path, config_path: Path | None, slug: str) -> tuple[Path, str]:
    try:
        config = load_config(root, config_path)
        path = find_plan(root.resolve(), config, slug)
        return path, path.read_text(encoding="utf-8")
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc
    except OSError as exc:
        raise click.ClickException(f"Cannot read the plan: {exc}") from exc


@cli.command()
@click.argument("title")
@ROOT_OPTION
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=f"Config file (default: <root>/{CONFIG_FILENAME}).",
)
@click.option(
    "--status",
    type=click.Choice(STATUSES),
    default="proposed",
    show_default=True,
    help="Initial status of the decision.",
)
def adr(title: str, root: Path, config_path: Path | None, status: str) -> None:
    """Write an Architecture Decision Record to docs/adr/<NNNN>-<slug>.md.

    NNNN is one above the highest existing ADR number. Requires
    adr.enabled: true in the config. Prints the path.
    """
    try:
        config = load_config(root, config_path)
        number, path = adr_path(root.resolve(), config, title)
        content = render_adr(
            root, number, title, status=status, today=date.today(), template=config.adr.template
        )
        written = write_document(path, content)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(written)


@cli.command("render")
@click.argument(
    "documents",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--light", is_flag=True, help="Light images only (by default they follow dark mode too)."
)
def render_command(documents: tuple[Path, ...], light: bool) -> None:
    """Render the D2 diagrams in DOCUMENTS to SVG images and embed them.

    Images go to img/<document>-<n>.svg next to each document (img/figure-<n>.svg for a
    README.md), their D2 sources to img/*.d2. D2 is downloaded once (pinned,
    checksum-verified) unless it is on PATH or in KINGMADOC_D2. Prints the image paths.
    """
    try:
        d2 = ensure_d2(lambda message: click.echo(message, err=True))
        hinted = False
        for document in documents:
            images = render_file(document, d2, dark=not light)
            index = index_path(document)
            if index is not None:
                _write_explain_index(index.parent)
                project = index.parent.parent.parent
                if images and not hinted and not preview_enabled(project):
                    hinted = True
                    click.echo(
                        "VS Code shows the pictures in the preview: open the file and press "
                        "Ctrl+Shift+V (macOS: Cmd+Shift+V), or run `kingmadoc skills install "
                        "--vscode` to always open explainers as a preview.",
                        err=True,
                    )
            if not images:
                click.echo(f"No D2 diagrams in {document}", err=True)
            for image in images:
                click.echo(image)
                if not light:
                    source = image.with_suffix(".d2")
                    for warning in dark_mode_warnings(source.read_text(encoding="utf-8")):
                        click.echo(f"{source}: {warning} (dark mode)", err=True)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.group("explain")
def explain_group() -> None:
    """Explainer folders for the explaining-code skill (docs/explain/<ID>-<name>/)."""


@explain_group.command("new")
@click.argument("name")
@ROOT_OPTION
def explain_new(name: str, root: Path) -> None:
    """Create (or reuse) the folder for explaining NAME and print its README.md path.

    Each subject gets a unique ID that is never reused; NAME may also be an existing ID.
    Also updates the index docs/explain/README.md.
    """
    try:
        folder, created = explainer_folder(root, name)
        _write_explain_index(folder.parent)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc
    if not created:
        click.echo(f"Reusing {folder.name} (explained before).", err=True)
    click.echo(folder / EXPLAINER_FILE)


@explain_group.command("facts")
@ROOT_OPTION
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=f"Config file (default: <root>/{CONFIG_FILENAME}).",
)
@click.option("--base", default=None, help="Also show what this branch changed since BASE.")
@click.option("--json", "as_json", is_flag=True, help="Print the facts as JSON.")
def explain_facts(root: Path, config_path: Path | None, base: str | None, as_json: bool) -> None:
    """Print what can be read from the code without guessing, to explain it from.

    The stack, the project references (.NET), the Python module dependencies, the data
    model from ORM code (EF Core, Prisma, Django, SQLAlchemy, TypeORM) and, with --base,
    the branch's commits and changed files.
    """
    try:
        config = load_config(root, config_path)
        report = analyze(root, config.analyzer, with_dependencies=True)
        branch = branch_changes(root, base) if base else None
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc
    _warn_if_truncated(report)
    facts = collect_facts(report, short_head(root), branch)
    if as_json:
        click.echo(json.dumps(facts_to_dict(facts), indent=2, ensure_ascii=False))
    else:
        click.echo(facts_markdown(facts), nl=False)


@explain_group.command("status")
@ROOT_OPTION
@click.option("--check", is_flag=True, help="Exit with 1 when an explainer is outdated (CI).")
def explain_status(root: Path, check: bool) -> None:
    """Show which explainers the code has changed under since they were written.

    Compares the files an explainer names (or the whole project) with the commit in its
    Based on row, including uncommitted changes.
    """
    directory = root / EXPLAIN_DIR
    names = {entry.link.split("/")[0]: entry.name for entry in read_entries(directory)}
    folders = explainer_folders(directory)
    if not folders:
        click.echo(f"No explainers in {directory}.", err=True)
        return
    outdated = 0
    for folder in folders:
        result = freshness(root, folder)
        label = f"{folder.name.partition('-')[0]} {names.get(folder.name, folder.name)}"
        if result.problem:
            click.echo(f"{label}: cannot tell ({result.problem})")
        elif result.changed:
            outdated += 1
            count = len(result.changed)
            shown = ", ".join(result.changed[:5]) + (", …" if count > 5 else "")
            scope = " in the project" if result.whole_project else ""
            noun = "file" if count == 1 else "files"
            click.echo(f"{label}: {count} {noun} changed{scope} since {result.commit}: {shown}")
        else:
            click.echo(f"{label}: up to date (since {result.commit})")
    if check and outdated:
        raise SystemExit(1)


def _write_explain_index(directory: Path) -> None:
    index = directory / EXPLAINER_FILE
    if index.is_file() and not is_generated_index(index.read_text(encoding="utf-8")):
        click.echo(
            f"{index} was not written by KingmaDoc, so the index was not updated.", err=True
        )
        return
    write_document(index, index_markdown(read_entries(directory)), overwrite=True)


@cli.group("skills")
def skills_group() -> None:
    """Agent skills bundled with KingmaDoc (plan/verify, and explaining existing code)."""


@skills_group.command("install")
@ROOT_OPTION
@click.option(
    "--agent",
    type=click.Choice(list(AGENT_DIRS)),
    default="claude",
    show_default=True,
    help="Agent whose skills directory to install into.",
)
@click.option(
    "--force", is_flag=True, help="Also replace skill files you edited locally."
)
@click.option(
    "--vscode/--no-vscode",
    default=None,
    help="Make VS Code open explainers as a rendered preview (.vscode/settings.json), or "
    "not. Without either, a terminal asks; other runs only print a tip.",
)
def skills_install(root: Path, agent: str, force: bool, vscode: bool | None) -> None:
    """Install the KingmaDoc skills into the project for AGENT (Agent Skills standard).

    Also offers to make VS Code open docs/explain/ as a rendered preview, so the pictures
    show right away (asked in a terminal; --vscode / --no-vscode decide up front).
    """
    try:
        result = install_skills(root, agent, force)
        if vscode is None and not preview_enabled(root) and _interactive():
            vscode = click.confirm(
                "Make VS Code open explainers (docs/explain/) as a rendered preview, so the "
                "pictures show right away?", default=True, err=True,
            )
        preview = enable_markdown_preview(root) if vscode else None
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc
    for path in result.written:
        click.echo(path)
    for path in result.removed:
        click.echo(f"Removed {path} (no longer part of the skill).", err=True)
    if result.up_to_date:
        click.echo(f"{len(result.up_to_date)} skill file(s) already up to date.", err=True)
    if preview:
        click.echo(preview, err=True)
    elif vscode is None and not preview_enabled(root):
        click.echo(
            "Tip: --vscode makes VS Code open explainers (docs/explain/) as a rendered preview.",
            err=True,
        )


def _interactive() -> bool:
    """A person at a terminal (not an agent or a pipe) can answer a question."""
    return sys.stdin.isatty()


def main() -> None:
    """Console-script entry point."""
    _utf8_stdout()
    cli()


def _utf8_stdout() -> None:
    """Make stdout UTF-8 whatever the locale, so piped output never crashes.

    On Windows, a piped stdout uses the ANSI code page (e.g. cp1252), which cannot
    encode the tree characters or most non-Latin text. Documents are UTF-8 files, so
    stdout gets the same encoding. stderr keeps the locale encoding (it is shown to a
    human) but replaces what it cannot encode instead of crashing.
    """
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(errors="replace")


if __name__ == "__main__":
    main()
