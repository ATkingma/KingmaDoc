"""HTTP routes and who may call them, read from the code (pure, pattern-based).

ASP.NET Core (controllers and minimal APIs), Next.js (app and pages router), Django,
FastAPI, Flask and Express. ``access`` is what the code states (an attribute, a
decorator, a middleware name); an empty ``access`` means the route declares nothing.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import MappingProxyType


@dataclass(frozen=True)
class Route:
    """One endpoint: method (``PAGE`` for a page), path, handler, file and access rule."""

    method: str
    path: str
    handler: str
    source: str
    access: str


def routes(sources: Mapping[str, str]) -> tuple[Route, ...]:
    """Return every route found in ``sources``, sorted by path and method.

    Args:
        sources: Relative POSIX path -> text of the project's source files.

    Returns:
        The routes.
    """
    found = [route for parser in _PARSERS for route in parser(sources)]
    return tuple(sorted(dict.fromkeys(found), key=lambda r: (r.path, r.method, r.handler)))


def _path(*parts: str) -> str:
    joined = "/".join(p.strip("/") for p in parts if p and p.strip("/"))
    return "/" + joined


# --- ASP.NET Core ---------------------------------------------------------------------

_CS_CLASS = re.compile(r"\bclass\s+(\w+)\b[^{;]*\{")
_ATTRIBUTE = re.compile(r"^\s*\[(.+)\]\s*$")
_HTTP = re.compile(r"^Http(Get|Post|Put|Delete|Patch)(?:\(\s*\"([^\"]*)\"[^)]*\))?$")
_ROUTE = re.compile(r"^Route\(\s*\"([^\"]*)\"\s*\)$")
_METHOD = re.compile(r"^\s*public\s+[\w<>\[\],.? ]+?\s+(\w+)\s*\(")
_MAP = re.compile(r"\b\w+\.Map(Get|Post|Put|Delete|Patch)\(\s*\"([^\"]+)\"\s*,\s*([^;]*);")


def _aspnet(sources: Mapping[str, str]) -> Iterator[Route]:
    for path, text in sorted(sources.items()):
        if not path.endswith(".cs"):
            continue
        yield from _minimal_api(path, text)
        previous_end = 0
        for match in _CS_CLASS.finditer(text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            class_attrs = _trailing_attributes(text[previous_end:line_start])
            body = _braced(text, match.end() - 1)
            previous_end = match.end() - 1 + len(body) + 2
            if not any(_HTTP.match(a) for a in _all_attributes(body)):
                continue
            yield from _controller(path, match.group(1), class_attrs, body)


def _controller(path: str, name: str, class_attrs: list[str], body: str) -> Iterator[Route]:
    prefix = next((m.group(1) for a in class_attrs if (m := _ROUTE.match(a))), "")
    prefix = prefix.replace("[controller]", name.removesuffix("Controller"))
    pending: list[str] = []
    for line in body.splitlines():
        attribute = _ATTRIBUTE.match(line)
        if attribute:
            pending.append(attribute.group(1).strip())
            continue
        method = _METHOD.match(line)
        if method:
            for attr in pending:
                http = _HTTP.match(attr)
                if http:
                    template = http.group(2) or ""
                    route_path = (_path(template) if template.startswith(("/", "~/"))
                                  else _path(prefix, template))
                    yield Route(http.group(1).upper(), route_path.replace("/~", ""),
                                f"{name}.{method.group(1)}", path,
                                _access(pending, class_attrs))
        if line.strip() and not line.strip().startswith("//"):
            pending = []


def _access(method_attrs: list[str], class_attrs: list[str]) -> str:
    def rule(attrs: list[str]) -> str | None:
        for attr in attrs:
            if attr.startswith("AllowAnonymous"):
                return "anonymous"
            if attr.startswith("Authorize"):
                args = attr.removeprefix("Authorize").strip("()").replace('"', "").strip()
                return f"Authorize ({args})" if args else "Authorize"
        return None

    parts = [rule(method_attrs) or rule(class_attrs) or ""]
    limits = [a for a in method_attrs + class_attrs if a.startswith("EnableRateLimiting")]
    if limits:
        policy = re.search(r"\"([^\"]+)\"", limits[0])
        parts.append(f"rate limit {policy.group(1) if policy else ''}".strip())
    return "; ".join(p for p in parts if p)


def _minimal_api(path: str, text: str) -> Iterator[Route]:
    for match in _MAP.finditer(text):
        statement = match.group(3)
        handler = re.match(r"\s*(\w+)\s*\)", statement)
        requires = re.search(r"\.RequireAuthorization\(([^)]*)\)", statement)
        access = ""
        if requires:
            args = requires.group(1).replace('"', "").strip()
            access = f"RequireAuthorization ({args})" if args else "RequireAuthorization"
        elif ".AllowAnonymous()" in statement:
            access = "anonymous"
        yield Route(match.group(1).upper(), _path(match.group(2)),
                    handler.group(1) if handler else "(inline)", path, access)


def _trailing_attributes(text: str) -> list[str]:
    attrs: list[str] = []
    for line in reversed(text.rstrip().splitlines()):
        attribute = _ATTRIBUTE.match(line)
        if not attribute:
            break
        attrs.insert(0, attribute.group(1).strip())
    return attrs


def _all_attributes(body: str) -> list[str]:
    return [m.group(1).strip() for line in body.splitlines() if (m := _ATTRIBUTE.match(line))]


# --- Next.js --------------------------------------------------------------------------

_NEXT_PAGE = re.compile(r"(?:^|/)(app|pages)/(.*?)(page|route|[^/]+)\.(tsx|ts|jsx|js)$")
_EXPORTED_METHOD = re.compile(
    r"^export\s+(?:async\s+)?(?:function\s+|const\s+)(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b",
    re.M,
)


def _nextjs(sources: Mapping[str, str]) -> Iterator[Route]:
    for path, text in sorted(sources.items()):
        match = _NEXT_PAGE.search(path)
        if not match or "/node_modules/" in f"/{path}":
            continue
        router, folder, stem = match.group(1), match.group(2), match.group(3)
        # Route groups, "(marketing)/", are not part of the URL.
        segments = [s for s in folder.split("/") if s and not re.fullmatch(r"\(.*\)", s)]
        if router == "app":
            if stem == "page":
                yield Route("PAGE", _path(*segments), path, path, "")
            elif stem == "route":
                for method in dict.fromkeys(_EXPORTED_METHOD.findall(text)):
                    yield Route(method, _path(*segments), path, path, "")
        elif not stem.startswith("_"):
            parts = [*segments, "" if stem == "index" else stem]
            is_api = bool(segments) and segments[0] == "api"
            yield Route("ANY" if is_api else "PAGE", _path(*parts), path, path, "")


# --- Python ---------------------------------------------------------------------------

_DJANGO_PATH = re.compile(r"\b(?:re_)?path\(\s*r?[\"']([^\"']*)[\"']\s*,\s*([\w.]+)")
_DECORATED_DEF = re.compile(r"((?:^[ \t]*@.+\n)+)[ \t]*(?:async\s+)?def\s+(\w+)\s*\(", re.M)
_AUTH_DECORATORS = ("login_required", "permission_required", "staff_member_required",
                    "user_passes_test", "jwt_required", "roles_required")
_HTTP_DECORATORS: Mapping[str, str] = MappingProxyType(
    {"require_POST": "POST", "require_GET": "GET", "require_safe": "GET"}
)
_FASTAPI = re.compile(r"^@\w+\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"'](.*)\)\s*$")
_FLASK = re.compile(r"^@\w+\.route\(\s*[\"']([^\"']+)[\"'](.*)\)\s*$")


def _python(sources: Mapping[str, str]) -> Iterator[Route]:
    python = {p: t for p, t in sources.items() if p.endswith(".py")}
    views = {name: decorators for text in python.values()
             for decorators, name in _DECORATED_DEF.findall(text)}
    for path, text in sorted(python.items()):
        if PurePosixPath(path).name == "urls.py":
            for route_path, view in _DJANGO_PATH.findall(text):
                decorators = views.get(view.rsplit(".", 1)[-1], "")
                method = next((m for d, m in _HTTP_DECORATORS.items() if f"@{d}" in decorators),
                              "ANY")
                access = [d for d in _AUTH_DECORATORS if f"@{d}" in decorators]
                yield Route(method, _path(route_path) + ("/" if route_path.endswith("/") else ""),
                            view, path, ", ".join(access))
        for decorators, name in _DECORATED_DEF.findall(text):
            lines = [line.strip() for line in decorators.splitlines()]
            access = [d for d in _AUTH_DECORATORS
                      if any(line == f"@{d}" or line.startswith(f"@{d}(") for line in lines)]
            for line in lines:
                fastapi, flask = _FASTAPI.match(line), _FLASK.match(line)
                if fastapi:
                    depends = re.findall(r"Depends\(\s*\w+\s*\)", fastapi.group(3))
                    yield Route(fastapi.group(1).upper(), _path(fastapi.group(2)), name, path,
                                ", ".join(depends + access))
                elif flask:
                    listed = re.search(r"methods\s*=\s*\[([^\]]*)\]", flask.group(2))
                    methods = re.findall(r"[\"'](\w+)[\"']", listed.group(1)) if listed else []
                    yield Route(", ".join(m.upper() for m in methods) or "GET",
                                _path(flask.group(1)), name, path, ", ".join(access))


# --- Express --------------------------------------------------------------------------

_EXPRESS = re.compile(
    r"\b(?:app|router|\w+Router)\.(get|post|put|delete|patch|all)\(\s*['\"`]([^'\"`]+)['\"`]\s*,(.*)$",
    re.M,
)


def _express(sources: Mapping[str, str]) -> Iterator[Route]:
    for path, text in sorted(sources.items()):
        if not path.endswith((".js", ".mjs", ".cjs", ".ts")) or _NEXT_PAGE.search(path):
            continue
        for method, route_path, rest in _EXPRESS.findall(text):
            args = [a.strip() for a in rest.rstrip(");").split(",")]
            middleware = [a for a in args[:-1] if re.fullmatch(r"[A-Za-z_$][\w$]*", a)]
            named = args and re.fullmatch(r"[A-Za-z_$][\w$.]*", args[-1])
            handler = args[-1] if named else "(inline)"
            yield Route(method.upper(), _path(route_path), handler, path, ", ".join(middleware))


# --- helpers --------------------------------------------------------------------------

_PARSERS: tuple[Callable[[Mapping[str, str]], Iterator[Route]], ...] = (
    _aspnet, _nextjs, _python, _express,
)


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
