"""Authored world-data transport (gm-portal-s4-world-data §5).

Thin HTTP shells over :mod:`web.gm.readers.world` and
:mod:`web.gm.readers.sources`: parse, dispatch, render the shared envelope.
Every route is read-only except :func:`prompts_reload`, the one S4 action. It
lives here, outside the readers, because it changes the in-memory prompt
library: it resets then reloads through the prompt owner's own loader, so a
failed load leaves exactly what the loader's startup semantics leave. It
writes no source file and no persistent state. Django's CSRF middleware runs
before the view, so a missing or invalid token never reaches the loader.
"""

from __future__ import annotations

from pathlib import Path

from django.http import HttpRequest, HttpResponse

from web.gm import pagination, responses
from web.gm.access import account_label
from web.gm.readers import sources, world
from web.gm.readers.errors import ReaderError
from world.observability import log_error, log_info
from world.prompts.loader import load_prompt_library, reset_prompt_library


def _safe_only(request: HttpRequest) -> HttpResponse | None:
    if request.method in ("GET", "HEAD"):
        return None
    response = responses.error("method_not_allowed", 405)
    response["Allow"] = "GET, HEAD"
    return response


def _failure(error: Exception) -> HttpResponse:
    if isinstance(error, ReaderError):
        return responses.error(error.code, error.status, error.message)
    if isinstance(error, pagination.PaginationError):
        return responses.error(error.code, 400, error.message)
    raise error


def registry_root(request: HttpRequest) -> HttpResponse:
    """``GET /gm/api/registry/`` — inventory, or cross-registry search with ``q``."""
    rejected = _safe_only(request)
    if rejected is not None:
        return rejected
    try:
        query = world.normalize_query(request.GET.get("q"))
        data = world.search(query) if query else world.inventory()
    except (ReaderError, pagination.PaginationError) as error:  # observability: ignore R2: a lookup/paging refusal is the response; gm_request records its status
        return _failure(error)
    return responses.ok(data)


def registry_list(request: HttpRequest, registry: str) -> HttpResponse:
    """``GET /gm/api/registry/<registry>?cursor=&limit=&q=``"""
    rejected = _safe_only(request)
    if rejected is not None:
        return rejected
    try:
        data = world.build_list(registry, request.GET)
    except (ReaderError, pagination.PaginationError) as error:  # observability: ignore R2: a lookup/paging refusal is the response; gm_request records its status
        return _failure(error)
    return responses.ok(data)


def registry_entry(request: HttpRequest, registry: str, key: str) -> HttpResponse:
    """``GET /gm/api/registry/<registry>/<key>``"""
    rejected = _safe_only(request)
    if rejected is not None:
        return rejected
    try:
        data = world.detail(registry, key)
    except (ReaderError, pagination.PaginationError) as error:  # observability: ignore R2: a lookup/paging refusal is the response; gm_request records its status
        return _failure(error)
    return responses.ok(data)


def sources_list(request: HttpRequest) -> HttpResponse:
    """``GET /gm/api/sources/`` — the allowlist, rebuilt per request."""
    rejected = _safe_only(request)
    if rejected is not None:
        return rejected
    return responses.ok(sources.list_sources())


def source_text(request: HttpRequest, name: str) -> HttpResponse:
    """``GET /gm/api/sources/<name>`` — one allowlisted file's disk text."""
    rejected = _safe_only(request)
    if rejected is not None:
        return rejected
    try:
        data = sources.read_source(name)
    except ReaderError as error:  # observability: ignore R2: a lookup refusal is the response; gm_request records its status
        return _failure(error)
    return responses.ok(data)


def _root_label(root: str) -> str:
    path = Path(root)
    try:
        return path.relative_to(sources.game_dir()).as_posix()
    except ValueError:  # observability: ignore R2: a prompt root outside the repository is reported verbatim
        return path.as_posix()


def _diagnostics(library) -> dict:
    from world.prompts.registry import PROMPT_SPECS

    unavailable = [
        {"key": key, "file": error.file, "problem": error.problem}
        for key, error in sorted(library.errors.items())
    ]
    return {
        "outcome": "degraded" if unavailable else "ok",
        "available": len(library.texts),
        "total": len(PROMPT_SPECS),
        "root": _root_label(library.root),
        "unavailable": unavailable,
    }


def prompts_reload(request: HttpRequest) -> HttpResponse:
    """``POST /gm/api/sources/prompts/reload`` — re-read ``prompts/`` into memory."""
    if request.method != "POST":
        response = responses.error("method_not_allowed", 405)
        response["Allow"] = "POST"
        return response
    account = account_label(request.user)
    try:
        reset_prompt_library()
        library = load_prompt_library()
    except Exception as error:
        log_error(
            "gm_prompts_reloaded",
            exc=error,
            context={"account": account, "outcome": "failed"},
        )
        log_info(
            "gm_action",
            context={"account": account, "action": "prompts_reload", "target": "prompts", "outcome": "failed"},
        )
        return responses.error("prompt_reload_failed", 500)
    data = _diagnostics(library)
    log_info(
        "gm_prompts_reloaded",
        context={
            "account": account,
            "outcome": data["outcome"],
            "available": data["available"],
            "total": data["total"],
            "unavailable": [item["key"] for item in data["unavailable"]],
        },
    )
    log_info(
        "gm_action",
        context={"account": account, "action": "prompts_reload", "target": "prompts", "outcome": data["outcome"]},
    )
    return responses.ok(data)


__all__ = [
    "prompts_reload",
    "registry_entry",
    "registry_list",
    "registry_root",
    "source_text",
    "sources_list",
]
