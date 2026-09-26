"""Regression test: stdout is UTF-8 even when the locale encoding is not (fix 3).

CliRunner always uses UTF-8, so this runs the real entry point in a subprocess with
``PYTHONIOENCODING=cp1252``: the Windows default whenever output is piped, which is how
agents read it.
"""

import os
import subprocess
import sys
from pathlib import Path

DESCRIPTION = "Add login für 日本語 users — with “quotes”."


def test_plan_stdout_is_utf8_under_cp1252(tmp_path: Path) -> None:
    """`plan --stdout` exits 0 and writes UTF-8 bytes, including the tree characters."""
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    (tmp_path / "app.py").write_text("", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "kingmadoc.cli", "plan", DESCRIPTION,
         "--root", str(tmp_path), "--no-input", "--stdout"],
        capture_output=True,
        env=env,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    text = result.stdout.decode("utf-8")  # raises if the bytes are not UTF-8
    text = text.replace("\r\n", "\n")  # Windows text mode writes CRLF; not what we test here
    assert f"# Feature: {DESCRIPTION}\n" in text
    assert "└── app.py" in text
