"""Shared test setup."""

import pytest

from kingmadoc import vscode


@pytest.fixture(autouse=True)
def _no_real_vscode_user_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Tests never read or write the developer's own VS Code user settings."""
    user = tmp_path_factory.mktemp("vscode-user") / "settings.json"
    monkeypatch.setattr(vscode, "user_settings_path", lambda platform=None: user)
