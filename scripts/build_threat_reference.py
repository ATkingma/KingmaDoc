"""Write skill/explaining-code/reference/threats.md from the bundled knowledge base.

Run after ``scripts/import_tmt_knowledge_base.py``; ``tests/test_threats.py`` fails when
the reference is stale.
"""

from pathlib import Path

from kingmadoc.threats.knowledge_base import load_knowledge_base
from kingmadoc.threats.report import catalog_markdown

TARGET = Path(__file__).resolve().parents[1] / "skill/explaining-code/reference/threats.md"

if __name__ == "__main__":
    TARGET.write_text(catalog_markdown(load_knowledge_base()), encoding="utf-8")
    print(f"wrote {TARGET}")
