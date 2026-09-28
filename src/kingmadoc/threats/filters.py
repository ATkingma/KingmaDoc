"""Evaluate the Threat Modeling Tool's generation filters for one data flow.

A filter is the tool's small expression language, e.g.
``source is 'GE.EI' and target is 'GE.P' and (flow crosses 'GE.TB.L' or flow crosses
'GE.TB.B')``. Supported, as used in the knowledge base:

- ``<role> is '<type>'``: the element (``source``, ``target``) or the ``flow`` has that
  type or specialises it;
- ``flow crosses '<type>'``: the flow crosses a trust boundary of that type;
- ``<role>.<property> is '<value>'``: a property of the element or flow, else its default;
- ``and``, ``or`` (``and`` binds tighter) and parentheses.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from kingmadoc.exceptions import ThreatModelError

_TOKEN = re.compile(r"\s*(\(|\)|'[^']*'|[\w.\-]+)")
ROLES = ("source", "target", "flow")


@dataclass(frozen=True)
class Subject:
    """What a filter looks at: the flow's two ends and the flow itself.

    Attributes:
        types: Role -> the type IDs of that element, most specific first.
        properties: Role -> property name -> value (only what was set).
        crosses: Type IDs (with their parents) of the trust boundaries the flow crosses.
        default: ``default(type_id, property)``: the knowledge base default.
    """

    types: Mapping[str, tuple[str, ...]]
    properties: Mapping[str, Mapping[str, str]]
    crosses: frozenset[str]
    default: Callable[[str, str], str | None]

    def value(self, role: str, name: str) -> str:
        """A property: set on the element, else its type's default, else "Not Selected"."""
        for key, value in self.properties[role].items():
            if key.lower() == name.lower():
                return value
        return self.default(self.types[role][0], name) or "Not Selected"


def _tokens(expression: str) -> list[str]:
    tokens, position = [], 0
    expression = expression.strip()
    while position < len(expression):
        match = _TOKEN.match(expression, position)
        if not match:
            raise ThreatModelError(f"Cannot read filter at {expression[position:]!r}")
        tokens.append(match.group(1))
        position = match.end()
    return tokens


def matches(expression: str, subject: Subject) -> bool:
    """Whether the filter holds for the subject (an empty filter never holds).

    Raises:
        ThreatModelError: If the filter is not valid.
    """
    tokens = _tokens(expression)
    if not tokens:
        return False
    position = 0

    def peek() -> str | None:
        return tokens[position].lower() if position < len(tokens) else None

    def take() -> str:
        nonlocal position
        if position >= len(tokens):
            raise ThreatModelError(f"Filter ends too early: {expression!r}")
        position += 1
        return tokens[position - 1]

    def either() -> bool:
        result = both()
        while peek() == "or":
            take()
            result = both() or result
        return result

    def both() -> bool:
        result = single()
        while peek() == "and":
            take()
            result = single() and result
        return result

    def single() -> bool:
        if peek() == "(":
            take()
            result = either()
            if take() != ")":
                raise ThreatModelError(f"Missing ')' in filter {expression!r}")
            return result
        left, operator, right = take(), take().lower(), take()
        if not (right.startswith("'") and right.endswith("'")):
            raise ThreatModelError(f"Expected a quoted value in filter {expression!r}")
        value = right[1:-1]
        role, _, name = left.partition(".")
        if role.lower() not in ROLES:
            raise ThreatModelError(f"Unknown filter subject {left!r}")
        role = role.lower()
        if operator == "crosses" and role == "flow" and not name:
            return value in subject.crosses
        if operator != "is":
            raise ThreatModelError(f"Unknown filter operator {operator!r}")
        if name:
            return subject.value(role, name).lower() == value.lower()
        return value in subject.types[role]

    result = either()
    if position != len(tokens):
        raise ThreatModelError(f"Unexpected {tokens[position]!r} in filter {expression!r}")
    return result
