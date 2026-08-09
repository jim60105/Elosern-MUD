"""Startup loader: validated YAML prompt files into a frozen prompt library.

Reads every ``*.yaml`` under the prompt root, validates each key against the
code-defined ``PROMPT_SPECS`` registry, and installs a frozen mapping used by
``render_prompt``. Failures are bounded per key (design D3): a broken file marks
only its key unavailable, the named error is logged, and server startup
continues. Duplicate YAML mapping keys are detected by a custom ``SafeLoader``
subclass instead of silently keeping the last value, which would hide an admin's
edit.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging
import os
import re
from threading import Lock
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from world.prompts.registry import PROMPT_SPECS, PromptSpec

logger = logging.getLogger(__name__)

# A placeholder is an exact ``{token}`` of a Python identifier that is not
# adjacent to another brace, so ``{{name}}`` and JSON example braces such as
# ``{"name": "…"}`` pass through untouched.
_PLACEHOLDER_RE = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})")

_TOP_LEVEL_KEYS = ("schema_version", "prompts")
_SCHEMA_VERSION = 1

_LIBRARY: "PromptLibrary | None" = None
_LOCK = Lock()


class PromptLibraryError(ValueError):
    """A named prompt-library failure; carries the file, key, and problem.

    ``file`` and ``key`` are ``None`` when the problem is library-wide or
    belongs to no single key yet (e.g. a render typo); the message still names
    whatever is known.
    """

    def __init__(self, file: str | None, key: str | None, problem: str):
        self.file = file
        self.key = key
        self.problem = problem
        super().__init__(self._message())

    def _message(self) -> str:
        location = self.file or "<prompt library>"
        if self.key:
            location = f"{location} key {self.key!r}"
        return f"{location}: {self.problem}"


class UnknownPromptKeyError(PromptLibraryError):
    """Raised when a consumer renders a key absent from ``PROMPT_SPECS``."""


class UnexpectedPromptValueError(PromptLibraryError):
    """Raised when a consumer passes a value whose name is outside the allowlist."""


class PromptUnavailableError(PromptLibraryError):
    """Raised when a consumer renders a key marked unavailable at load time.

    Consumers resolve this to their deterministic degrade path: a broken prompt
    is treated exactly like an unavailable LLM (design D3).
    """

    def __init__(self, file: str | None, key: str | None, problem: str):
        super().__init__(file, key, f"prompt key unavailable: {problem}")


class _DuplicateMappingKeyError(ValueError):
    """YAML parse failure naming a repeated mapping key and its line."""

    def __init__(self, key: Any, line: int):
        self.duplicate_key = key
        self.line = line
        super().__init__(f"duplicate mapping key {key!r} at line {line}")


class _DuplicateRejectingLoader(yaml.SafeLoader):
    """SafeLoader that raises on repeated mapping keys instead of last-wins."""


def _construct_mapping(loader: yaml.Loader, node: yaml.MappingNode, deep: bool = False):
    """Mapping constructor that rejects a repeated key rather than keeping the last value."""
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise _DuplicateMappingKeyError(key, key_node.start_mark.line + 1)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_DuplicateRejectingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


@dataclass(frozen=True)
class PromptLibrary:
    """A validated, frozen snapshot of the prompt texts plus per-key failures."""

    root: str
    texts: Mapping[str, str] = dataclass_field(
        default_factory=lambda: MappingProxyType({})
    )
    errors: Mapping[str, PromptLibraryError] = dataclass_field(
        default_factory=lambda: MappingProxyType({})
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "texts", MappingProxyType(dict(self.texts)))
        object.__setattr__(self, "errors", MappingProxyType(dict(self.errors)))

    def text(self, key: str) -> str:
        """Return the loaded text for an available key (``KeyError`` otherwise)."""
        return self.texts[key]

    @property
    def unavailable(self) -> frozenset[str]:
        """The keys marked unavailable at load time."""
        return frozenset(self.errors)


def _prompt_root() -> str:
    """Return the configured ``PROMPT_ROOT``, the env override, or the repo default.

    ``settings.PROMPT_ROOT`` is the primary source (default
    ``<GAME_DIR>/prompts``); a ``PROMPT_ROOT`` environment override and finally
    the repo's own ``prompts/`` directory keep the validate CLI and pure-logic
    callers working even without a configured Django environment.
    """
    try:
        configured = getattr(settings, "PROMPT_ROOT", None)
    except (ImproperlyConfigured, AttributeError):
        configured = None
    if configured:
        return configured
    override = os.environ.get("PROMPT_ROOT")
    if override:
        return override
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(repo_root, "prompts")


def _record_file_failure(
    errors: dict[str, PromptLibraryError],
    file: str,
    spec_keys: list[str],
    problem: str,
) -> None:
    """Record the same file-level ``problem`` for every spec key in the file."""
    for key in spec_keys:
        errors[key] = PromptLibraryError(file, key, problem)


def load_prompt_library(root: str | None = None) -> PromptLibrary:
    """Validate every ``prompts/*.yaml`` under root and install the frozen library.

    Never aborts server startup: a failing key is recorded with a named error,
    logged, and marked unavailable so its consuming layer degrades. The
    ``character_creation.system`` key is logged as a warning (its layer
    degrades) and can never block startup. An explicit ``root`` installs a
    library independent of the setting (tests use fixture roots in
    ``try/finally``). The install is guarded by a lock so concurrent callers
    cannot double-load.
    """
    with _LOCK:
        return _load(_prompt_root() if root is None else root)


def _load(resolved_root: str) -> PromptLibrary:
    """Validate and install the library for ``resolved_root`` (lock held).

    This function is total: every file-system and YAML failure is recorded as
    a per-key named error so a broken prompt file can never abort server
    startup (design D3).
    """
    texts: dict[str, str] = {}
    errors: dict[str, PromptLibraryError] = {}

    root_files: set[str] = set()
    try:
        if os.path.isdir(resolved_root):
            root_files = {
                name for name in os.listdir(resolved_root) if name.endswith(".yaml")
            }
    except OSError as exc:
        for key in PROMPT_SPECS:
            errors[key] = PromptLibraryError(
                None, key, f"cannot list prompt root {resolved_root}: {exc}"
            )
        return _finish_load(resolved_root, texts, errors)

    for file in sorted({spec.file for spec in PROMPT_SPECS.values()}):
        spec_keys = [spec.key for spec in PROMPT_SPECS.values() if spec.file == file]
        if file not in root_files:
            for key in spec_keys:
                errors[key] = PromptLibraryError(
                    file, key, f"prompt file {file!r} not found under {resolved_root}"
                )
            continue

        raw: Any = None
        parse_error: PromptLibraryError | None = None
        try:
            with open(os.path.join(resolved_root, file), encoding="utf-8") as handle:
                raw = yaml.load(handle, Loader=_DuplicateRejectingLoader)
        except _DuplicateMappingKeyError as exc:
            parse_error = PromptLibraryError(
                file,
                None,
                f"duplicate mapping key {exc.duplicate_key!r} at line {exc.line}",
            )
        except (yaml.YAMLError, OSError, UnicodeError, TypeError, ValueError) as exc:
            parse_error = PromptLibraryError(file, None, f"cannot read prompt file: {exc}")

        if parse_error is not None:
            for key in spec_keys:
                errors[key] = PromptLibraryError(file, key, parse_error.problem)
            continue
        if not isinstance(raw, Mapping):
            _record_file_failure(errors, file, spec_keys, "prompt file must be a mapping")
            continue
        try:
            unknown_top = sorted(
                set(raw) - set(_TOP_LEVEL_KEYS),
                key=repr,
            )
        except TypeError as exc:
            _record_file_failure(
                errors, file, spec_keys, f"unhashable top-level key: {exc}"
            )
            continue
        if unknown_top:
            _record_file_failure(
                errors,
                file,
                spec_keys,
                f"unknown top-level key {', '.join(repr(k) for k in unknown_top)}",
            )
            continue
        if raw.get("schema_version") != _SCHEMA_VERSION:
            _record_file_failure(
                errors,
                file,
                spec_keys,
                f"schema_version must be {_SCHEMA_VERSION}",
            )
            continue
        declared = raw.get("prompts")
        if not isinstance(declared, Mapping):
            _record_file_failure(errors, file, spec_keys, "prompts must be a mapping")
            continue
        for declared_key in declared:
            if declared_key not in PROMPT_SPECS:
                errors[declared_key] = PromptLibraryError(
                    file, declared_key, "unknown prompt key (not in PROMPT_SPECS)"
                )
        for spec in PROMPT_SPECS.values():
            if spec.file != file:
                continue
            try:
                text = _validate_key(spec, declared)
            except PromptLibraryError as exc:
                errors[spec.key] = exc
                continue
            if text is None:
                errors[spec.key] = PromptLibraryError(
                    file, spec.key, f"missing prompt key {spec.key!r} in file"
                )
                continue
            texts[spec.key] = text

    return _finish_load(resolved_root, texts, errors)


def _finish_load(
    resolved_root: str,
    texts: dict[str, str],
    errors: dict[str, PromptLibraryError],
) -> PromptLibrary:
    """Build the frozen library, log every named failure, and install it."""
    library = PromptLibrary(root=resolved_root, texts=texts, errors=errors)
    for key, error in sorted(errors.items()):
        if key == "character_creation.system":
            logger.warning("%s (consuming layer degrades)", error)
        else:
            logger.error("%s", error)
    logger.info(
        "prompt library loaded: %d/%d keys available from %s",
        len(texts),
        len(PROMPT_SPECS),
        resolved_root,
    )
    global _LIBRARY
    _LIBRARY = library
    return library


def _validate_key(spec: PromptSpec, declared: Mapping[str, Any]) -> str | None:
    """Validate one declared key's text; return it or raise the named error."""
    if spec.key not in declared:
        return None
    text = declared[spec.key]
    if not isinstance(text, str):
        raise PromptLibraryError(spec.file, spec.key, "prompt text must be a text block")
    if not text.strip():
        raise PromptLibraryError(spec.file, spec.key, "prompt text is empty")
    if len(text) > spec.max_length:
        raise PromptLibraryError(
            spec.file,
            spec.key,
            f"prompt text length {len(text)} exceeds max {spec.max_length}",
        )
    tokens = set(_PLACEHOLDER_RE.findall(text))
    unknown = sorted(tokens - set(spec.allowed_placeholders))
    if unknown:
        allowed = ", ".join(sorted(spec.allowed_placeholders)) or "<none>"
        raise PromptLibraryError(
            spec.file,
            spec.key,
            f"unknown placeholder {', '.join(repr(t) for t in unknown)}; allowed: {allowed}",
        )
    return text


def reset_prompt_library() -> None:
    """Clear the loaded library so the next render auto-loads (used by tests)."""
    global _LIBRARY
    with _LOCK:
        _LIBRARY = None


def prompt_library() -> PromptLibrary | None:
    """Return the currently loaded library, or ``None`` before the first load."""
    return _LIBRARY


def _ensure_library() -> PromptLibrary:
    """Return the loaded library, auto-loading from the default root once.

    The read and the one-time load both happen under the lock so a concurrent
    explicit load can never leave this caller with a stale ``None``.
    """
    global _LIBRARY
    with _LOCK:
        if _LIBRARY is None:
            _LIBRARY = _load(_prompt_root())
        return _LIBRARY


def render_prompt(key: str, **values: str) -> str:
    """Render key's loaded text with only its allowlisted placeholders replaced.

    Substitutes exactly each ``{token}`` form not adjacent to another brace
    (``{{name}}`` and JSON example braces stay literal), every present
    allowlisted token exactly once. Supplied values whose names are outside the
    key's allowlist raise ``UnexpectedPromptValueError`` so a consumer typo such
    as ``namme=`` fails loudly; an unavailable key raises
    ``PromptUnavailableError`` for the consuming layer's degrade path; an
    unknown key raises ``UnknownPromptKeyError``. Auto-loads once on first use.
    """
    library = _ensure_library()
    spec = PROMPT_SPECS.get(key)
    if spec is None:
        raise UnknownPromptKeyError(None, key, "unknown prompt key")
    error = library.errors.get(key)
    if error is not None:
        raise PromptUnavailableError(error.file, key, error.problem)

    unexpected = sorted(set(values) - set(spec.allowed_placeholders))
    if unexpected:
        raise UnexpectedPromptValueError(
            None,
            key,
            f"unexpected value name {', '.join(repr(name) for name in unexpected)}"
            f"; allowed: {', '.join(sorted(spec.allowed_placeholders)) or '<none>'}",
        )

    def _sub(match: re.Match[str]) -> str:
        return values[match.group(1)]

    return _PLACEHOLDER_RE.sub(_sub, library.text(key))