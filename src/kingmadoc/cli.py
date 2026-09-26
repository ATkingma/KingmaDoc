"""Command-line interface: ``kingmadoc init | plan | verify``."""

from __future__ import annotations

from pathlib import Path

import click

from kingmadoc import __version__
from kingmadoc.config import CONFIG_FILENAME, default_config_yaml, load_config
from kingmadoc.exceptions import KingmaDocError
from kingmadoc.plan.analyzer import analyze
from kingmadoc.plan.generator import (
    FeatureRequest,
    build_questions,
    default_output_path,
    render_plan,
    write_document,
)

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
    """KingmaDoc: feature design docs before you build, verification docs after."""


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
@click.argument("feature_name")
@ROOT_OPTION
@click.option("-d", "--description", default="", help="One-line feature description.")
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
    help="Output file (default: <output_dir>/<feature-slug>/design.md).",
)
@click.option("--no-input", is_flag=True, help="Skip clarifying questions.")
@click.option("--stdout", "to_stdout", is_flag=True, help="Print the doc instead of writing it.")
@click.option("--force", is_flag=True, help="Overwrite an existing output file.")
def plan(
    feature_name: str,
    root: Path,
    description: str,
    config_path: Path | None,
    output: Path | None,
    no_input: bool,
    to_stdout: bool,
    force: bool,
) -> None:
    """Analyze the codebase and generate a Feature Design Doc for FEATURE_NAME."""
    try:
        config = load_config(root, config_path)
        analysis = analyze(root, config.analyzer)

        answers: list[tuple[str, str]] = []
        if not no_input:
            questions = build_questions(analysis, config)
            if questions:
                click.echo("Answer a few questions (press Enter to skip):", err=True)
            for question in questions:
                answer = click.prompt(question, default="", show_default=False, err=True)
                answers.append((question, answer.strip()))

        feature = FeatureRequest(name=feature_name, description=description, answers=answers)
        content = render_plan(feature, analysis, config)

        if to_stdout:
            click.echo(content, nl=False)
            return
        path = output or default_output_path(analysis.root, config, feature_name)
        written = write_document(content, path, overwrite=force)
    except KingmaDocError as exc:
        raise click.ClickException(str(exc)) from exc

    if analysis.truncated:
        click.echo(
            f"Warning: stopped after {config.analyzer.max_files} files; "
            "raise analyzer.max_files for a complete analysis.",
            err=True,
        )
    click.echo(f"Wrote {written}")


@cli.command()
@click.argument("plan_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@ROOT_OPTION
def verify(plan_path: Path, root: Path) -> None:
    """Compare PLAN_PATH against the code and generate a Feature Verification Doc.

    Not implemented yet (planned for phase 2).
    """
    raise click.ClickException(
        f"verify is not implemented yet (phase 2). Plan: {plan_path}, root: {root}"
    )


def main() -> None:
    """Console-script entry point."""
    cli()


if __name__ == "__main__":
    main()
