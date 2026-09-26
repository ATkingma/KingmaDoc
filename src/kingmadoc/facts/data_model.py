"""The data model, read from ORM code: entities, their fields and their relations.

Pattern-based ("grep"), like the rest of the analysis: EF Core, Prisma, Django,
SQLAlchemy and TypeORM. Only what the code states is returned; a relation whose side
cannot be read is ``unknown`` rather than guessed.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType

# How many instances of the target one entity holds.
RELATION_KINDS: tuple[str, ...] = ("one", "many", "unknown")


@dataclass(frozen=True)
class Field:
    """A stored attribute of an entity."""

    name: str
    type: str


@dataclass(frozen=True)
class Relation:
    """A reference from an entity to another entity."""

    name: str
    target: str
    kind: str


@dataclass(frozen=True)
class Entity:
    """One entity (table, model) and where it is defined."""

    name: str
    orm: str
    source: str
    fields: tuple[Field, ...]
    relations: tuple[Relation, ...]


def data_model(sources: Mapping[str, str]) -> tuple[Entity, ...]:
    """Return the entities defined in ``sources``, sorted by name.

    Args:
        sources: Relative POSIX path -> text of the project's source files (any
            language; each parser picks the files it understands).

    Returns:
        The entities; the first definition wins when a name appears twice.
    """
    found: dict[str, Entity] = {}
    for parser in _PARSERS:
        for entity in parser(sources):
            found.setdefault(entity.name, entity)
    return tuple(found[name] for name in sorted(found))


# --- EF Core --------------------------------------------------------------------------

_DBSET = re.compile(r"\bDbSet<\s*(\w+)\s*>")
_CS_CLASS = re.compile(r"\bclass\s+(\w+)\b[^{;]*\{")
_CS_PROPERTY = re.compile(
    r"^\s*public\s+(?:(?:required|virtual|override|new)\s+)*"
    r"([\w.]+(?:<[^>{}]+>)?\??(?:\[\])?)\s+(\w+)\s*\{\s*get\b",
    re.M,
)
_CS_COLLECTION = re.compile(
    r"^(?:ICollection|IList|List|IEnumerable|HashSet|ISet|IReadOnlyCollection|IReadOnlyList)"
    r"<\s*(\w+)\s*>\??$|^(\w+)\[\]\??$"
)


def _ef_core(sources: Mapping[str, str]) -> Iterator[Entity]:
    code = {path: text for path, text in sources.items()
            if path.endswith(".cs") and not _is_ef_generated(path)}
    names = {name for text in code.values() for name in _DBSET.findall(text)}
    for path, text in sorted(code.items()):
        for match in _CS_CLASS.finditer(text):
            if match.group(1) not in names:
                continue
            body = _braced(text, match.end() - 1)
            fields, relations = [], []
            for type_, prop in _CS_PROPERTY.findall(body):
                many = _CS_COLLECTION.match(type_)
                target = (many.group(1) or many.group(2)) if many else type_.rstrip("?")
                if target in names:
                    relations.append(Relation(prop, target, "many" if many else "one"))
                else:
                    fields.append(Field(prop, type_))
            yield Entity(match.group(1), "EF Core", path, tuple(fields), tuple(relations))


def _is_ef_generated(path: str) -> bool:
    return "/Migrations/" in f"/{path}" or path.endswith((".Designer.cs", "ModelSnapshot.cs"))


# --- Prisma ---------------------------------------------------------------------------

_PRISMA_MODEL = re.compile(r"^model\s+(\w+)\s*\{(.*?)^\}", re.M | re.S)
_PRISMA_FIELD = re.compile(r"^\s*(\w+)\s+(\w+)(\[\])?(\?)?", re.M)


def _prisma(sources: Mapping[str, str]) -> Iterator[Entity]:
    schemas = {p: t for p, t in sources.items() if p.endswith(".prisma")}
    models = {m.group(1) for text in schemas.values() for m in _PRISMA_MODEL.finditer(text)}
    for path, text in sorted(schemas.items()):
        for match in _PRISMA_MODEL.finditer(text):
            fields, relations = [], []
            for name, type_, many, optional in _PRISMA_FIELD.findall(match.group(2)):
                if type_ in models:
                    relations.append(Relation(name, type_, "many" if many else "one"))
                else:
                    fields.append(Field(name, type_ + many + optional))
            yield Entity(match.group(1), "Prisma", path, tuple(fields), tuple(relations))


# --- Django ---------------------------------------------------------------------------

_PY_CLASS = re.compile(r"^class\s+(\w+)\s*\(([^)]*)\)\s*:", re.M)
_DJANGO_FIELD = re.compile(r"^(\w+)\s*=\s*models\.(\w+)\((.*)$")
_DJANGO_RELATIONS: Mapping[str, str] = MappingProxyType(
    {"ForeignKey": "one", "OneToOneField": "one", "ManyToManyField": "many"}
)
_FIRST_ARG = re.compile(r"\s*(?:to\s*=\s*)?[\"']?([\w.]+)")


def _django(sources: Mapping[str, str]) -> Iterator[Entity]:
    for path, text in sorted(_python(sources).items()):
        for match in _PY_CLASS.finditer(text):
            if "models.Model" not in match.group(2):
                continue
            fields, relations = [], []
            for line in _class_lines(text, match.end()):
                field = _DJANGO_FIELD.match(line)
                if not field:
                    continue
                name, kind, args = field.groups()
                if kind in _DJANGO_RELATIONS:
                    target = _FIRST_ARG.match(args)
                    relations.append(Relation(
                        name, target.group(1).rsplit(".", 1)[-1] if target else "?",
                        _DJANGO_RELATIONS[kind],
                    ))
                else:
                    fields.append(Field(name, kind))
            yield Entity(match.group(1), "Django", path, tuple(fields), tuple(relations))


# --- SQLAlchemy -----------------------------------------------------------------------

_SA_ATTRIBUTE = re.compile(r"^(\w+)\s*(?::\s*Mapped\[(.+)\])?\s*=\s*(\w+)\((.*)$")
_SA_COLUMN_TYPE = re.compile(r"\s*(?:[\"'][^\"']*[\"']\s*,\s*)?([A-Z]\w*)")
_SA_MANY = re.compile(r"^(?:list|List|set|Set)\[\s*[\"']?(\w+)[\"']?\s*\]$")
_SA_ONE = re.compile(r"^(?:Optional\[)?[\"']?(\w+)[\"']?\]?(?:\s*\|\s*None)?$")


def _sqlalchemy(sources: Mapping[str, str]) -> Iterator[Entity]:
    for path, text in sorted(_python(sources).items()):
        for match in _PY_CLASS.finditer(text):
            lines = list(_class_lines(text, match.end()))
            if not any(line.startswith("__tablename__") for line in lines):
                continue
            fields, relations = [], []
            for line in lines:
                attribute = _SA_ATTRIBUTE.match(line)
                if not attribute:
                    continue
                name, mapped, call, args = attribute.groups()
                if call == "relationship":
                    relations.append(_sa_relation(name, mapped, args))
                elif call in ("Column", "mapped_column"):
                    column = _SA_COLUMN_TYPE.match(args)
                    fields.append(Field(name, mapped or (column.group(1) if column else "")))
            yield Entity(match.group(1), "SQLAlchemy", path, tuple(fields), tuple(relations))


def _sa_relation(name: str, mapped: str | None, args: str) -> Relation:
    if mapped:
        many = _SA_MANY.match(mapped.strip())
        if many:
            return Relation(name, many.group(1), "many")
        one = _SA_ONE.match(mapped.strip())
        if one:
            return Relation(name, one.group(1), "one")
    target = re.match(r"\s*[\"']?(\w+)", args)
    return Relation(name, target.group(1) if target else "?", "unknown")


# --- TypeORM --------------------------------------------------------------------------

_TS_ENTITY = re.compile(r"@Entity\([^)]*\)\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)[^{]*\{")
_TS_DECORATOR = re.compile(r"^\s*@(\w+)\((.*)$")
_TS_PROPERTY = re.compile(r"^\s*(?:public\s+|readonly\s+)*(\w+)[!?]?\s*:\s*([^;=]+?)\s*[;=]")
_TS_RELATIONS: Mapping[str, str] = MappingProxyType(
    {"ManyToOne": "one", "OneToOne": "one", "OneToMany": "many", "ManyToMany": "many"}
)


def _typeorm(sources: Mapping[str, str]) -> Iterator[Entity]:
    for path, text in sorted(sources.items()):
        if not path.endswith(".ts"):
            continue
        for match in _TS_ENTITY.finditer(text):
            fields, relations = [], []
            decorator: tuple[str, str] | None = None
            for line in _braced(text, match.end() - 1).splitlines():
                if found := _TS_DECORATOR.match(line):
                    decorator = (found.group(1), found.group(2))
                elif (prop := _TS_PROPERTY.match(line)) and decorator:
                    name, type_ = prop.group(1), prop.group(2).strip()
                    kind = _TS_RELATIONS.get(decorator[0])
                    if kind:
                        arrow = re.search(r"=>\s*(\w+)", decorator[1])
                        target = arrow.group(1) if arrow else type_.removesuffix("[]")
                        relations.append(Relation(name, target, kind))
                    elif decorator[0].endswith("Column"):
                        fields.append(Field(name, type_))
                    decorator = None
            yield Entity(match.group(1), "TypeORM", path, tuple(fields), tuple(relations))


# --- helpers --------------------------------------------------------------------------

_PARSERS: tuple[Callable[[Mapping[str, str]], Iterator[Entity]], ...] = (
    _ef_core, _prisma, _django, _sqlalchemy, _typeorm,
)


def _python(sources: Mapping[str, str]) -> dict[str, str]:
    return {p: t for p, t in sources.items() if p.endswith(".py")}


def _braced(text: str, start: int) -> str:
    """The text inside the ``{`` at ``start`` and its matching ``}``."""
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index]
    return text[start + 1 :]


def _class_lines(text: str, start: int) -> Iterator[str]:
    """The class-level statements of a Python class body, dedented (no nested blocks)."""
    indent: int | None = None
    for line in text[start:].splitlines()[1:]:
        if not line.strip():
            continue
        current = len(line) - len(line.lstrip())
        if current == 0:
            return
        if indent is None:
            indent = current
        if current == indent:
            yield line.strip()
