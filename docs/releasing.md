# Releasing

KingmaDoc takes its version from the git tag (`hatch-vcs`, see `pyproject.toml`): tag
`v0.2.0` builds `0.2.0`; commits after it on `main` are `0.3.0.devN`, so every install from
git has a higher version than the one before. Never set the version by hand.

## One-time setup

1. On [pypi.org](https://pypi.org/manage/account/publishing/), add a *pending trusted
   publisher* for project `kingmadoc`: owner `ATkingma`, repository `KingmaDoc`, workflow
   `release.yml`, environment `pypi`. No API token is needed or stored.
2. In the GitHub repository settings, create the environment `pypi` (optionally with a
   required reviewer, so a release waits for approval).

## Each release

1. Move the `[Unreleased]` entries in `CHANGELOG.md` to `## [X.Y.Z] - <date>` and commit.
2. `git tag -a vX.Y.Z -m "KingmaDoc X.Y.Z" && git push origin vX.Y.Z`.
3. `.github/workflows/release.yml` builds the sdist and wheel, checks that their version
   is the tag, installs the wheel and runs it (plan, skills install), publishes to PyPI,
   and creates the GitHub release with the changelog section and the built files.

## Beta channel

`release.yml` also runs after every successful CI run on `main` and publishes that
commit's development version (`0.3.0.devN`) to PyPI with the same trusted publisher;
it creates no GitHub release. pip installs development versions only with `--pre`, so
`pipx install kingmadoc` keeps getting releases, and
`pipx install --pip-args=--pre kingmadoc` follows the beta. A re-run of the same commit
skips the upload (`skip-existing`). Pull requests never publish.

## Supply chain

- `uv.lock` pins the development dependencies; CI fails when it is out of date
  (`uv lock --check`, update with `uv lock`).
- CI runs `pip-audit` on the locked dependencies and Ruff's `S` (bandit) rules on the
  code; justified exceptions carry a `# noqa: S…` with the reason.
- GitHub Actions are pinned to commit SHAs.
