"""``kingmadoc explain check``: an explainer is only done with its pictures shown."""

from pathlib import Path

from click.testing import CliRunner

from kingmadoc.cli import cli
from kingmadoc.explain import check_explainer

PNG = b"\x89PNG\r\n\x1a\n"


def _folder(tmp_path: Path, text: str, images: tuple[str, ...] = ("figure-1.png",)) -> Path:
    folder = tmp_path / "docs" / "explain" / "0001-shop"
    (folder / "img").mkdir(parents=True)
    for image in images:
        (folder / "img" / image).write_bytes(PNG)
    (folder / "README.md").write_text(text, encoding="utf-8")
    return folder


DONE = ("# Shop\n\n<!-- kingmadoc:diagram img/figure-1.d2 -->\n![Context](img/figure-1.png)\n\n"
        "**Figure 1.** Who uses it.\n\n<details><summary>More</summary>x</details>\n")


def test_a_finished_explainer_passes(tmp_path: Path) -> None:
    assert check_explainer(_folder(tmp_path, DONE)) == []


def test_every_way_to_end_up_without_pictures_is_caught(tmp_path: Path) -> None:
    """Nothing written, unrendered D2, missing images, captions without pictures, TODOs."""
    assert check_explainer(tmp_path) == [f"{tmp_path}: no explainer documents (README.md) yet"]
    cases = {
        "": "README.md: empty",
        "# S\n\n```d2\na -> b\n```\n\n**Figure 1.** x\n": "D2 source not rendered",
        "# S\n\n![x](img/figure-9.png)\n\n**Figure 1.** x\n": "missing images: img/figure-9.png",
        "# S\n\n**Figure 1.** x\n": "has figure captions but shows no pictures",
        DONE + "\n<one line: what it is>\n":
            "1 placeholders not filled in: <one line: what it is>",
    }
    for index, (text, problem) in enumerate(cases.items()):
        folder = _folder(tmp_path / str(index), text)
        problems = check_explainer(folder)
        assert any(problem in p for p in problems), (text, problems)


def test_split_checks_every_document(tmp_path: Path) -> None:
    folder = _folder(tmp_path, "# Shop\n\n| [Functional design](functional.md) | … |\n")
    (folder / "functional.md").write_text(DONE, encoding="utf-8")
    (folder / "technical.md").write_text("# T\n\n```d2\nx\n```\n**Figure 1.** y\n",
                                         encoding="utf-8")

    assert check_explainer(folder) == [
        "technical.md: D2 source not rendered (run kingmadoc render)",
        "technical.md: has figure captions but shows no pictures",
    ]


def test_cli_fails_until_finished(tmp_path: Path) -> None:
    folder = _folder(tmp_path, "# S\n\n```d2\na\n```\n**Figure 1.** x\n")

    failed = CliRunner().invoke(cli, ["explain", "check", str(folder)])
    assert failed.exit_code == 1 and "D2 source not rendered" in failed.output

    (folder / "README.md").write_text(DONE, encoding="utf-8")
    passed = CliRunner().invoke(cli, ["explain", "check", str(folder)])
    assert passed.exit_code == 0 and "finished (1 pictures)" in passed.output


def test_code_links_and_html_are_not_placeholders(tmp_path: Path) -> None:
    """Only real `<placeholders>` fail: never generics in code spans, links or HTML."""
    text = DONE + (
        "\nThe `OrderService` returns `List<Order>` and `Task<IActionResult>`.\n"
        "See <https://arc42.org> or <team@example.com>. <kbd>Ctrl</kbd>\n"
    )
    assert check_explainer(_folder(tmp_path, text)) == []


EMBEDDED = (
    "# Shop\n\n<!-- kingmadoc:diagram img/figure-1.d2 -->\n"
    "![Context](data:image/png;base64,iVBORw0KGgo=)\n\n"
    "**Figure 1.** Who uses it.\n\n<!-- kingmadoc:diagram img/figure-2.d2 -->\n"
    "![Flow](data:image/svg+xml;base64,PHN2Zy8+)\n\n**Figure 2.** How it flows.\n"
)


def test_embedded_images_count_as_pictures(tmp_path: Path) -> None:
    """A data-URI image is there; check says how many pictures the explainer shows."""
    folder = _folder(tmp_path, EMBEDDED, images=())

    assert check_explainer(folder) == []
    passed = CliRunner().invoke(cli, ["explain", "check", str(folder)])
    assert passed.exit_code == 0 and "finished (2 pictures)" in passed.output


def test_screen_wireframe_texts_must_come_from_the_view(tmp_path: Path) -> None:
    """A [Screen] figure's labels are compared with the view its caption names."""
    from kingmadoc.explain import screen_warnings

    text = EMBEDDED.replace("Who uses it.", "Wireframe of `views/contact.html`.")
    folder = _folder(tmp_path, text, images=())
    (folder / "img" / "figure-1.d2").write_text(
        'title: "[Screen] Contact" {shape: text}\n'
        'screen: "/contact" {\n  name: "Name [ ___ ]"\n'
        "  send: Send message\n  extra: Subscribe\n}\n",
        encoding="utf-8",
    )
    view = tmp_path / "views" / "contact.html"
    view.parent.mkdir()
    view.write_text("<label>Name</label><button>Send message</button>", encoding="utf-8")

    warnings = screen_warnings(folder, tmp_path)

    assert warnings == ["README.md: img/figure-1.d2: `Subscribe` is not in views/contact.html"]
    result = CliRunner().invoke(cli, ["explain", "check", str(folder)])
    assert result.exit_code == 0 and "`Subscribe` is not in" in result.output


CONTEXT = '''title: "[System Context] Shop" {shape: text}
customer: |md
  **Customer**\\
  [Person]
| {class: person}
shop: "Shop [Software System]" {class: system}
pay: "Payment provider [Software System]" {class: external}
mail: "E-mail service [Software System]" {class: external}
erp: "ERP [Software System]" {class: external}
customer -> shop: "Places orders using"
'''
# Misses `pay` (while it has an arrow to it), renames the customer, swaps mail and erp.
CONTAINER = '''title: "[Container] Shop" {shape: text}
customer: |md
  **Buyer**\\
  [Person]
| {class: person}
web: "Web app [Container: Django]" {class: container}
erp: "ERP [Software System]" {class: external}
mail: "E-mail service [Software System]" {class: external}
customer -> web: "Places orders [HTTPS]"
web -> pay: "Pays using [HTTPS]"
web -> mail: "Sends e-mails [SMTP]"
web -> erp: "Books orders [SOAP]"
'''


def test_c4_levels_keep_the_contexts_actors() -> None:
    """One missing, one renamed, one reordered actor: three warnings, and none when equal."""
    from kingmadoc.explain import c4_actor_warnings

    warnings = c4_actor_warnings([("img/figure-1.d2", CONTEXT), ("img/figure-2.d2", CONTAINER)])

    assert len(warnings) == 3, warnings
    assert "`Payment provider` from the context is missing" in warnings[0]
    assert "person `Buyer` is called `Customer` in the context" in warnings[1]
    assert "another order than in the context" in warnings[2]
    fixed = CONTEXT.replace("[System Context]", "[Container]")
    assert c4_actor_warnings([("a", CONTEXT), ("b", fixed)]) == []
    extra = CONTEXT + 'dev: "Reviewer [Person]" {class: person}\n'
    assert "not in the context" in c4_actor_warnings(
        [("a", CONTEXT), ("b", extra.replace("[System Context]", "[Component]"))])[0]


def test_explain_check_warns_about_c4_actors(tmp_path: Path) -> None:
    folder = _folder(tmp_path, EMBEDDED, images=())
    (folder / "img" / "figure-1.d2").write_text(CONTEXT, encoding="utf-8")
    (folder / "img" / "figure-2.d2").write_text(CONTAINER, encoding="utf-8")

    result = CliRunner().invoke(cli, ["explain", "check", str(folder)])

    assert result.exit_code == 0  # warnings, not failures
    assert result.output.count("(warning)") == 3


SEQUENCE = '''title: "[Sequence] Dashboard - loading" {shape: text}
shape: sequence_diagram
page: "index.html / index.js"
charts: charts.js
api: "DatasetEndpoints / DashboardEndpoints"
svc: DatasetService
page -> api: GET /datasets
'''


def test_merged_lifelines_are_warned_about_except_a_page_and_its_script(tmp_path: Path) -> None:
    """One class, file or system per lifeline; `x.html / x.js` is the one allowed pair."""
    from kingmadoc.explain import lifeline_warnings

    warnings = lifeline_warnings([("img/figure-3.d2", SEQUENCE)])

    assert warnings == ["figure-3.d2: lifeline 'DatasetEndpoints / DashboardEndpoints' merges "
                        "two classes; give each its own lifeline"]
    other_page = SEQUENCE.replace("index.html / index.js", "index.html / charts.js")
    assert len(lifeline_warnings([("f.d2", other_page)])) == 2
    not_sequence = SEQUENCE.replace("shape: sequence_diagram\n", "")
    assert lifeline_warnings([("f.d2", not_sequence)]) == []

    folder = _folder(tmp_path, EMBEDDED, images=())
    (folder / "img" / "figure-1.d2").write_text(SEQUENCE, encoding="utf-8")
    result = CliRunner().invoke(cli, ["explain", "check", str(folder)])
    assert result.exit_code == 0 and "merges two classes" in result.output
