"""Command-line interface: ``kingmadoc init | analyze | plan | verify | adr | render``."""

from __future__ import annotations

import io
import json
import sys
from datetime import date, datetime
from pathlib import Path

import click

from kingmadoc import __version__
from kingmadoc.adr import STATUSES, adr_path, render_adr
from kingmadoc.config import CONFIG_FILENAME, MAX_FILES_LIMIT, default_config_yaml, load_config
from kingmadoc.d2_binary import ensure_d2
from kingmadoc.documents import write_document, write_documents
from kingmadoc.exceptions import KingmaDocError
from kingmadoc.plan.analyzer import CodebaseReport, analyze, format_report, report_to_dict
from kingmadoc.plan.generator import (
    build_plan_context,
    build_questions,
    default_output_path,
    enabled_extra_designs,
    extra_design_path,
    needs_dependencies,
    render_extra_design,
    render_plan,
)
from kingmadoc.render import render_file
from kingmadoc.verify.stub import find_plan, render_verify_stub, verify_output_path

ROOT_OPTION = click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Project root to analyze.",
)


@click.group()
@click.version_option(__version__, prog_name="kingmadoc")
def cli() -> None:
    """KingmaDoc: feature plan docs before you build, verification docs after."""


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
def verify(slug: str, root: Path, config_path: Path | None, force: bool) -> None:
    """[WORK IN PROGRESS] Write a placeholder verification doc for plan SLUG.

    Reads <output_dir>/SLUG-plan.md and writes SLUG-verify.md next to it, then prints
    its path. The comparison against the code is not implemented yet (phase 2).
    """
    try:
        config = load_config(root, config_path)
        root = root.resolve()
        plan_path = find_plan(root, config, slug)
        content = render_verify_stub(
            slug,
            plan_path.relative_to(root).as_posix(),
            now=datetime.now().astimezone(),
        )
        written = write_document(verify_output_path(plan_path), content, overwrite=force)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo("verify is a work-in-progress stub: nothing was checked.", err=True)
    click.echo(written)


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
def render_command(documents: tuple[Path, ...]) -> None:
    """Render the D2 diagrams in DOCUMENTS to SVG images and embed them.

    Images go to img/<document>-<n>.svg next to each document; the D2 source stays in the
    document, collapsed below the image. D2 is downloaded once (pinned, checksum-verified)
    unless it is on PATH or in KINGMADOC_D2. Prints the written image paths.
    """
    try:
        d2 = ensure_d2(lambda message: click.echo(message, err=True))
        for document in documents:
            images = render_file(document, d2)
            if not images:
                click.echo(f"No D2 diagrams in {document}", err=True)
            for image in images:
                click.echo(image)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc


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
