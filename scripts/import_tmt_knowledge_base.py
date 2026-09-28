"""Import Microsoft's threat knowledge base into KingmaDoc (repo script, not shipped).

Reads ``default.tb7`` ("SDL TM Knowledge Base (Core)") from
https://github.com/microsoft/threat-modeling-templates (MIT) and writes the parts
KingmaDoc uses to ``src/kingmadoc/threats/sdl_knowledge_base.json``: the element types
(stencils) with their properties, the STRIDE categories and the threat types with their
generation filters. Run it again only to update to a newer template:

    curl -sLO https://raw.githubusercontent.com/microsoft/threat-modeling-templates/<sha>/default.tb7
    python3 scripts/import_tmt_knowledge_base.py default.tb7 <sha>
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - parses a pinned, reviewed Microsoft file
from pathlib import Path

REPO = "https://github.com/microsoft/threat-modeling-templates"
OUTPUT = Path(__file__).resolve().parents[1] / "src/kingmadoc/threats/sdl_knowledge_base.json"
LICENSE = """MIT License

Copyright (c) Microsoft Corporation. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""


def _text(node: ET.Element, tag: str) -> str:
    return re.sub(r"\s+", " ", node.findtext(tag) or "").strip()


def _children(root: ET.Element, tag: str) -> list[ET.Element]:
    section = root.find(tag)
    return list(section) if section is not None else []


def _element(node: ET.Element) -> dict[str, object]:
    attributes = {}
    for attribute in node.iter("Attribute"):
        values = [v.text or "" for v in attribute.iter("Value")]
        attributes[_text(attribute, "Name")] = {
            "label": _text(attribute, "DisplayName"),
            "values": values,
        }
    return {
        "id": _text(node, "ID"),
        "name": _text(node, "Name"),
        "parent": _text(node, "ParentElement") or None,
        "representation": _text(node, "Representation"),
        "attributes": attributes,
    }


def convert(tb7: Path, commit: str) -> dict[str, object]:
    """Return the JSON document for one ``.tb7`` knowledge base."""
    root = ET.parse(tb7).getroot()  # noqa: S314 - see the import above
    manifest = root.find("Manifest")
    if manifest is None:
        raise SystemExit(f"{tb7}: no <Manifest>; is this a Threat Modeling Tool template?")
    elements = [
        _element(node)
        for section in ("GenericElements", "StandardElements")
        for node in _children(root, section)
    ]
    threats = [
        {
            "id": _text(node, "Id"),
            "category": _text(node, "Category"),
            "title": _text(node, "ShortTitle"),
            "description": _text(node, "Description"),
            "include": _text(node, "GenerationFilters/Include"),
            "exclude": _text(node, "GenerationFilters/Exclude"),
        }
        for node in _children(root, "ThreatTypes")
        # Threats migrated from TMT v3 are only generated for the hidden ROOT element.
        if _text(node, "GenerationFilters/Include") != "source is 'ROOT'"
    ]
    return {
        "source": {
            "name": manifest.get("name"),
            "version": manifest.get("version"),
            "url": f"{REPO}/blob/{commit}/{tb7.name}",
            "license": LICENSE,
        },
        "categories": {
            _text(node, "Id"): _text(node, "Name") for node in _children(root, "ThreatCategories")
        },
        "elements": [e for e in elements if e["id"] and e["representation"] != "Annotation"],
        "threats": threats,
    }


def main() -> None:
    """Convert the ``.tb7`` given on the command line."""
    tb7, commit = Path(sys.argv[1]), sys.argv[2]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(convert(tb7, commit), indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
