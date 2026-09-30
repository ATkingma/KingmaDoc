"""The explaining-code skill's model examples follow their own notation rules.

Agents copy these examples, so every one must obey the rules its reference file states:
Simon Brown's C4 notation (reference/c4-model.md) and the UML, ER, BPMN-style, DFD and
DDD rules (reference/models.md).
"""

import re
from pathlib import Path

import pytest

FOLDER = Path(__file__).resolve().parents[1] / "skill" / "explaining-code"
C4_MODEL = FOLDER / "reference" / "c4-model.md"
MODELS = FOLDER / "reference" / "models.md"
ALL_FILES = [FOLDER / "SKILL.md", *sorted((FOLDER / "reference").glob("*.md"))]

C4_DIAGRAMS = [
    "System Context", "Container", "Component", "Code", "System Landscape", "Dynamic",
    "Deployment",
]
EDGE = re.compile(r"^\s*([\w.]+)\s*(<->|->|--)\s*([\w.]+)(?:\s*(?:->|--)\s*[\w.]+)*(.*)$")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _examples(text: str) -> list[str]:
    return re.findall(r"^```d2\n(.*?)\n```$", text, re.S | re.M)


def _without_legend(source: str) -> str:
    return re.sub(r"vars: \{\n  d2-legend: \{\n.*?\n  \}\n\}\n", "", source, flags=re.S)


def _edges(source: str) -> list[tuple[str, str, str, str]]:
    """(from, operator, to, rest of the line) for every connection outside the legend."""
    return [m.groups() for line in _without_legend(source).splitlines()
            if (m := EDGE.match(line))]


def _title(source: str) -> str:
    match = re.search(r'^title: "\[([^\]]+)\]', source, re.M)
    assert match, f"no [type] title:\n{source}"
    return match.group(1)


def _sections(path: Path) -> dict[str, str]:
    parts = re.split(r"^## (.+)$", _read(path), flags=re.M)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


# --- C4 (Simon Brown) -------------------------------------------------------------------


def test_c4_reference_covers_all_seven_diagrams_and_the_checklist() -> None:
    """Abstractions, the seven diagram types, notation rules and the review checklist."""
    text = _read(C4_MODEL)
    sections = _sections(C4_MODEL)

    for heading in ("Abstractions", "The seven diagrams", "Notation rules", "Review checklist"):
        assert heading in sections, heading
    for diagram in C4_DIAGRAMS:
        assert diagram in sections["The seven diagrams"], diagram
    for rule in ("title", "legend", "technology", "one direction", "protocol"):
        assert rule in sections["Review checklist"], rule
    assert "c4model.com" in text


C4_EXAMPLES = _examples(_read(C4_MODEL))


def test_c4_examples_exist_for_each_drawn_level() -> None:
    """Context, container, component, deployment and dynamic have a D2 example."""
    titles = {_title(example) for example in C4_EXAMPLES}
    assert {"System Context", "Container", "Component", "Deployment", "Dynamic"} <= titles


@pytest.mark.parametrize("index", range(len(C4_EXAMPLES)))
def test_c4_example_follows_the_notation(index: int) -> None:
    """Title with type, legend, typed elements, labelled one-way arrows, no "Uses"."""
    source = C4_EXAMPLES[index]
    kind = _title(source)

    assert kind in C4_DIAGRAMS
    assert "d2-legend" in source, "every C4 diagram has a legend"
    elements = re.findall(r'^\s*\w+: (?:\|md\n(.*?)\n\s*\||"([^"]*)") \{class: (\w+)',
                          _without_legend(source), re.S | re.M)
    assert elements
    for markdown, quoted, _cls in elements:
        assert "[" in (markdown or quoted), f"element without a [type]: {markdown or quoted}"
    for source_name, operator, target, rest in _edges(source):
        assert operator == "->", f"{source_name} {operator} {target}: one direction only"
        label = rest.partition(":")[2].strip().strip('"')
        assert label, f"{source_name} -> {target} has no label"
        assert label.split("\\n")[0].strip().lower() not in {"uses", "use"}
        if kind in ("Container", "Deployment"):
            assert "[" in label, f"{source_name} -> {target}: name the protocol"


def test_c4_examples_share_one_palette() -> None:
    """Colours are consistent across all figures (same class, same colour)."""
    palettes: dict[str, set[str]] = {}
    for source in C4_EXAMPLES:
        pattern = r"^  (\w+): \{(shape: [\w-]+; style: \{[^}]*\})(?:; width: \d+)?\}$"
        for name, style in re.findall(pattern, source, re.M):
            palettes.setdefault(name, set()).add(style)
    assert palettes
    assert all(len(styles) == 1 for styles in palettes.values()), palettes


# --- Other models -----------------------------------------------------------------------

GENERAL = {"Which model for which code", "Rules for every model", "Review checklist"}
MODEL_SECTIONS = {k: v for k, v in _sections(MODELS).items() if k not in GENERAL}


def test_every_model_has_rules_one_example_and_a_row_in_the_decision_table() -> None:
    """The agent picks a model from the table, then follows that model's rules."""
    table = _sections(MODELS)["Which model for which code"].lower()

    assert len(MODEL_SECTIONS) >= 10
    for heading, body in MODEL_SECTIONS.items():
        assert "Rules:" in body, heading
        assert len(_examples(body)) == 1, heading
        assert heading.split()[0].lower() in table, heading


def _model(prefix: str) -> str:
    """The D2 example of the one model section whose heading starts with ``prefix``."""
    matches = [_examples(b)[0] for h, b in MODEL_SECTIONS.items() if h.startswith(prefix)]
    assert len(matches) == 1, prefix
    return matches[0]


def test_every_model_example_has_a_title_naming_the_model() -> None:
    """`[<Model>] <scope>`, like the C4 titles."""
    for heading, body in MODEL_SECTIONS.items():
        assert _title(_examples(body)[0]), heading


def test_sequence_replies_are_dashed_and_groups_named() -> None:
    """UML: calls solid, replies dashed; alt/opt/loop groups carry their condition."""
    source = _model("Sequence")

    assert "shape: sequence_diagram" in source
    assert "stroke-dash: 3" in source
    # draw.io colours: light-blue actors, black messages, grey groups.
    assert '"#dae8fc"' in source and 'stroke: "#000000"' in source and '"#f5f5f5"' in source
    groups = re.findall(r'^\w+: "(\w+) \[', source, re.M)
    assert groups and set(groups) <= {"alt", "opt", "loop"}


def test_state_machine_has_initial_and_final_states_and_labelled_transitions() -> None:
    """UML: filled circle, bullseye, `event [guard] / action` on every transition."""
    source = _model("State machine")

    assert re.search(r'^start: "" \{shape: circle;.*fill: black', source, re.M)
    assert re.search(r'^end: "" \{shape: circle;.*double-border: true', source, re.M)
    for source_name, _op, target, rest in _edges(source):
        if target != "end":
            assert rest.startswith(":"), f"{source_name} -> {target} has no event"


def test_er_relationships_show_cardinality_at_both_ends() -> None:
    """Crow's foot: every foreign key has an arrowhead at both ends (needs `<->` in D2)."""
    source = _model("ER diagram")
    edges = _edges(source)

    assert "shape: sql_table" in source and "foreign_key" in source
    assert edges and all(op == "<->" for _s, op, _t, _r in edges)
    assert re.search(r"source-arrowhead\.shape: cf-", source)
    assert re.search(r"target-arrowhead\.shape: cf-", source)


def test_class_diagram_uses_uml_arrowheads() -> None:
    """Hollow triangle for realisation, filled diamond for composition, dashed dependency."""
    source = _model("Class diagram")

    # |md rectangles: shape: class puts white text on the stroke colour.
    assert "shape: class" not in source and "|md" in source and "&lt;" in source
    assert "shape: triangle; style.filled: false" in source
    assert "shape: diamond; style.filled: true" in source
    assert "style.stroke-dash" in source


def test_activity_diagram_has_lanes_start_end_and_labelled_decisions() -> None:
    """One lane per role; decision exits are labelled."""
    source = _model("Activity diagram")
    decisions = re.findall(r"^\s+(\w+): .*\{shape: diamond\}", source, re.M)

    assert "fill: black" in source and "double-border: true" in source
    assert decisions
    for decision in decisions:
        exits = [e for e in _edges(source) if e[0].endswith(f".{decision}")]
        assert exits and all(rest.startswith(":") for *_x, rest in exits), decision


def test_use_case_lines_have_no_arrowheads() -> None:
    """UML use case: actors connect to goals with plain lines."""
    source = _model("Use case")

    assert "shape: oval" in source and "shape: person" in source
    assert all(op == "--" for _s, op, _t, _r in _edges(source))


def test_data_flow_labels_every_flow_and_marks_trust_boundaries() -> None:
    """DFD: process circles, data stores, labelled flows, dashed red trust boundaries."""
    source = _model("Data flow")

    for shape in ("shape: circle", "shape: stored_data", "stroke: red", "stroke-dash"):
        assert shape in source, shape
    assert "d2-legend" in source
    assert all(rest.startswith(":") for *_x, rest in _edges(source))


def test_event_flow_and_context_map_explain_their_notation() -> None:
    """Sticky colours need a legend; context-map arrows name upstream/downstream patterns."""
    assert "d2-legend" in _model("Event flow")
    for *_x, rest in _edges(_model("Context map")):
        assert "U:" in rest and "D:" in rest


def test_package_diagram_uses_packages() -> None:
    """Packages of the project itself, arrows mean imports."""
    source = _model("Package")

    assert "shape: package" in source
    assert all("imports" in rest for *_x, rest in _edges(source))


# --- D2 pitfalls that silently break a notation -----------------------------------------


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_start_arrowheads_are_only_used_on_two_headed_edges(path: Path) -> None:
    """D2 drops a `source-arrowhead` on `->` without an error, losing e.g. ER cardinality."""
    for source in _examples(_read(path)):
        lines = source.splitlines()
        for number, line in enumerate(lines):
            if "source-arrowhead" in line:
                edge = next((ln for ln in reversed(lines[: number + 1]) if EDGE.match(ln)), "")
                assert edge, f"{path.name}: source-arrowhead outside a connection: {line}"
                assert "<->" in edge, f"{path.name}: {edge}"


# --- Dark mode ----------------------------------------------------------------------------


def _enclosing_map(source: str, position: int) -> tuple[int, int]:
    """Start and end of the innermost {...} around ``position``."""
    depth, start = 0, position
    while start > 0:
        start -= 1
        if source[start] == "}":
            depth += 1
        elif source[start] == "{":
            if depth == 0:
                break
            depth -= 1
    depth, end = 0, position
    while end < len(source):
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            if depth == 0:
                break
            depth -= 1
        end += 1
    return start, end + 1


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_filled_shapes_stay_readable_in_dark_mode(path: Path) -> None:
    """`kingmadoc render` also draws a dark theme; a fixed fill needs a fixed text colour.

    Otherwise the dark theme's light text lands on a light fill. Unlabelled black dots
    (UML start and end) get a grey stroke so they show on a dark background.
    """
    problems = []
    for source in _examples(_read(path)):
        for match in re.finditer(r"\bfill: *([^;}\n]+)", source):
            start, end = _enclosing_map(source, match.start())
            block = source[start:end]
            line = source[source.rfind("\n", 0, match.start()) + 1 : match.start()]
            if re.match(r'\s*[\w.]+: ""', line):
                if match.group(1).strip() == "black" and "stroke" not in block:
                    problems.append(f"black dot without stroke: {line.strip()} {block}")
            elif "font-color" not in block and match.group(1).strip() != "transparent":
                problems.append(f"fill without font-color: {line.strip()} {block}")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_text_on_the_background_follows_the_theme(path: Path) -> None:
    """A fixed text colour only on a fixed fill; boxes that hold other shapes stay see-through.

    Black title text or a white boundary look right on white and wrong in dark mode: the
    boundary stays white while the labels inside it turn light.
    """
    problems = []
    for source in _examples(_read(path)):
        for match in re.finditer(r"\bfont-color: *[^;}\n]+", source):
            start, end = _enclosing_map(source, match.start())
            block = source[start:end]
            fill = re.search(r"\bfill: *([^;}\n]+)", block)
            if not fill or fill.group(1).strip().strip('"') == "transparent":
                line = source[source.rfind("\n", 0, match.start()) + 1 : match.start()]
                problems.append(f"font-color without a fill: {line.strip()} {block}")
        for fill in re.finditer(r"\bfill: *\"?(#fff\b|#ffffff|white)\"?", source, re.I):
            problems.append(f"white fill (use transparent): {fill.group(0)}")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_a_sequence_diagram_has_no_stray_label(path: Path) -> None:
    """shape: sequence_diagram at the top level, or in a container labelled "" (else its
    key, e.g. "seq", shows as a heading)."""
    for source in _examples(_read(path)):
        for match in re.finditer(r"^( +)shape: sequence_diagram", source, re.M):
            opening = source[: match.start()].rstrip().rsplit("\n", 1)[-1]
            assert re.search(r':\s*""\s*\{$', opening), f"{path.name}: {opening.strip()}"


def test_algorithm_model_explains_with_formula_trace_and_complexity() -> None:
    """Flowchart + short pseudocode + formula ($$) + invariant + complexity + trace table."""
    body = next(b for h, b in MODEL_SECTIONS.items() if h.startswith("Algorithm"))
    source = _examples(body)[0]

    assert "shape: diamond" in source
    assert re.search(r'-> \w+: "?(yes|no)', source)
    assert re.search(r"^\$\$\n.+\n\$\$$", body, re.M), "a display formula in $$ … $$"
    assert "```text" in body and "Invariant" in body
    assert re.search(r"\bO\(.+\) time", body)
    assert re.search(r"^\| Step \|", body, re.M), "a trace table, one row per step"


def test_c4_boundaries_keep_their_label_out_of_the_arrows() -> None:
    """Boundary and node labels sit top-left in a small font, so arrows do not cross them."""
    for line in re.findall(r"^\s*(?:boundary|node): \{.*$", _read(C4_MODEL), re.M):
        assert "label.near: top-left" in line and "font-size: 15" in line, line


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_diagrams_flow_down(path: Path) -> None:
    """Every example with arrows (except sequence diagrams) sets one flow direction:
    down, or right for timelines and swimlanes."""
    for source in _examples(_read(path)):
        if _edges(source) and "sequence_diagram" not in source and "grid-" not in source:
            assert re.search(r"^direction: (down|right)$", source, re.M), (
                f"{path.name}:\n{source[:120]}"
            )


def test_c4_examples_keep_the_same_actors_on_every_level() -> None:
    """The container, component and deployment examples repeat the context's actors."""
    from kingmadoc.explain import c4_actor_warnings

    figures = [(str(n), source) for n, source in enumerate(C4_EXAMPLES)]
    assert c4_actor_warnings(figures) == []
    text = re.sub(r"\s+", " ", _read(C4_MODEL))
    assert "The same actors on every level" in text and "stakeholders table" in text


def test_sequence_lifelines_are_one_code_element_each() -> None:
    """No merged `A / B` lifelines in the example; the rule and its one exception are stated."""
    from kingmadoc.explain import lifeline_warnings

    section = re.sub(r"\s+", " ", MODEL_SECTIONS["Sequence diagram (UML)"])
    assert lifeline_warnings([("sequence.d2", _model("Sequence"))]) == []
    assert "One lifeline is one class, one file or one external system." in section
    assert "`index.html / index.js`" in section and "`par [...]`" in section
    assert "no `A / B` lifelines" in _read(MODELS)


def test_sequence_example_has_activation_bars_but_not_on_the_database() -> None:
    from kingmadoc.explain import sequence_warnings

    source = _model("Sequence")
    assert sequence_warnings([("sequence.d2", source)]) == []
    for span in ("web.main", "api.c1", "svc.c1"):
        assert span in source, span
    assert "db." not in source
    section = re.sub(r"\s+", " ", MODEL_SECTIONS["Sequence diagram (UML)"])
    assert "Never abbreviate a call" in section and "One round trip is one message" in section
    assert "no abbreviated calls (`Get...Async`)" in re.sub(r"\s+", " ", _read(MODELS))
