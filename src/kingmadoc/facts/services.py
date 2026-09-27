"""Services registered for dependency injection (.NET), read from the code (pure)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# Registration method -> lifetime shown in the facts.
LIFETIMES: Mapping[str, str] = MappingProxyType({
    "AddScoped": "scoped",
    "AddSingleton": "singleton",
    "AddTransient": "transient",
    "AddDbContext": "scoped",
    "AddDbContextFactory": "singleton",
    "AddHttpClient": "http client",
    "AddHostedService": "hosted",
})
_REGISTRATION = re.compile(
    r"\.(" + "|".join(LIFETIMES) + r")<\s*([\w.]+)\s*(?:,\s*([\w.]+)\s*)?>"
)


@dataclass(frozen=True)
class Service:
    """One registration: lifetime, the type asked for, the type that is made, and where."""

    lifetime: str
    contract: str
    implementation: str
    source: str


def services(sources: Mapping[str, str]) -> tuple[Service, ...]:
    """Return the DI registrations in the project's C# files, in file and code order.

    Args:
        sources: Relative POSIX path -> text of the project's source files.

    Returns:
        The registrations.
    """
    return tuple(
        Service(LIFETIMES[method], contract, implementation or contract, path)
        for path, text in sorted(sources.items())
        if path.endswith(".cs")
        for method, contract, implementation in _REGISTRATION.findall(text)
    )
