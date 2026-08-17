"""Per-layer LLM endpoint profiles with strict construction-time validation.

The generative layer is governed by one ``LLMProfile`` per layer, read from the
``LLM_PROFILES`` Django setting. Profiles are frozen, validated at
construction, and never clamped: a failing bound raises a named error naming
the layer and field so misconfiguration surfaces at startup rather than at a
live call.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import math
import os
from types import MappingProxyType
from typing import Any

from django.conf import settings

LAYER_NAMES = (
    "narrator",
    "npc_dialogue",
    "scenario_director",
    "scene_builder",
    "character_creation",
    "action_options",
)

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_CHAT_PATH = "/v1/chat/completions"
DEFAULT_MODEL = "llama3.2"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 250
ACTION_OPTIONS_MAX_TOKENS = 320
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 2
DEFAULT_HEADERS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {"Content-Type": ("application/json",)}
)

# The only generative layer that consumes JSON-schema structured output; its
# profile must declare the capability at construction time (pipeline design
# doc §5), enforced per layer in ``build_profiles``.
REQUIRED_PROFILE_FLAGS: Mapping[str, Mapping[str, bool]] = MappingProxyType(
    {"action_options": {"supports_response_format": True}}
)


class UnknownLayerError(KeyError):
    """Raised when a layer name is outside the fixed generative layer set."""


class ProfileValidationError(ValueError):
    """Raised when a profile field fails a bound; names the layer and field."""

    def __init__(self, layer: str, field: str, message: str):
        self.layer = layer
        self.field = field
        super().__init__(f"profile {layer!r} field {field!r}: {message}")


def _normalize_headers(
    headers: Any, layer: str = "<direct>"
) -> Mapping[str, tuple[str, ...]]:
    """Validate headers and return a frozen ``{key: (values,)}`` mapping."""
    if not isinstance(headers, Mapping):
        raise ProfileValidationError(layer, "headers", "must be a mapping")
    frozen: dict[str, tuple[str, ...]] = {}
    for key, values in headers.items():
        if not isinstance(key, str) or not key:
            raise ProfileValidationError(layer, "headers", "keys must be non-empty strings")
        if isinstance(values, str):
            values = (values,)
        elif not isinstance(values, (list, tuple)):
            raise ProfileValidationError(layer, "headers", f"values for {key!r} must be strings")
        if not values or any(not isinstance(item, str) or not item for item in values):
            raise ProfileValidationError(layer, "headers", f"values for {key!r} must be strings")
        frozen[key] = tuple(values)
    return MappingProxyType(frozen)


@dataclass(frozen=True)
class LLMProfile:
    """Frozen endpoint configuration for one generative layer."""

    base_url: str
    path: str
    headers: Mapping[str, tuple[str, ...]]
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    max_retries: int
    supports_response_format: bool
    enabled: bool

    def __post_init__(self) -> None:
        values = {
            "base_url": self.base_url,
            "path": self.path,
            "headers": self.headers,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "supports_response_format": self.supports_response_format,
            "enabled": self.enabled,
        }
        validate_profile_values("<direct>", values)
        object.__setattr__(self, "headers", _normalize_headers(self.headers, "<direct>"))


def validate_profile_values(layer: str, values: Mapping[str, Any]) -> None:
    """Validate every profile bound, failing closed with the layer and field."""
    for field in ("base_url", "path", "model"):
        value = values.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ProfileValidationError(layer, field, "must be a non-empty string")
    temperature = values.get("temperature")
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not math.isfinite(float(temperature))
        or not 0 <= float(temperature) <= 2
    ):
        raise ProfileValidationError(layer, "temperature", "must be a finite number in 0..2")
    for field in ("max_tokens", "timeout_seconds"):
        value = values.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ProfileValidationError(layer, field, "must be a positive integer")
    max_retries = values.get("max_retries")
    if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
        raise ProfileValidationError(layer, "max_retries", "must be a non-negative integer")
    for field in ("supports_response_format", "enabled"):
        if not isinstance(values.get(field), bool):
            raise ProfileValidationError(layer, field, "must be a boolean")
    _normalize_headers(values.get("headers"), layer)


def default_profiles() -> dict[str, dict[str, Any]]:
    """Return the local-first default ``LLM_PROFILES`` dict for every layer.

    The base URL comes from ``OLLAMA_BASE_URL`` when present (the compose
    runtime) and falls back to a bare-metal localhost endpoint otherwise.
    ``supports_response_format`` defaults false because design §7.5 only
    requests structured output when the endpoint declares support; the
    ``action_options`` layer is the single exception and always defaults to
    the capability on, with ``max_tokens`` sized for a 5-card JSON payload
    (pipeline design doc §5).
    """
    base_url = os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL
    profiles = {
        layer: {
            "base_url": base_url,
            "path": DEFAULT_CHAT_PATH,
            "headers": DEFAULT_HEADERS,
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
            "max_retries": DEFAULT_MAX_RETRIES,
            "supports_response_format": False,
            "enabled": True,
        }
        for layer in LAYER_NAMES
    }
    profiles["action_options"] = {
        **profiles["action_options"],
        "max_tokens": ACTION_OPTIONS_MAX_TOKENS,
        "supports_response_format": True,
    }
    return profiles


def build_profiles(
    raw_profiles: Mapping[str, Mapping[str, Any]] | Iterable[tuple[str, Mapping[str, Any]]],
) -> Mapping[str, LLMProfile]:
    """Validate a raw ``LLM_PROFILES`` source and build frozen profiles.

    Accepts either a mapping or an iterable of ``(layer, values)`` pairs so
    duplicate layer keys can be detected. Unknown layers are rejected, every
    profile is validated against every bound, and any of the six layers missing
    from the source falls back to the local-first default so the registry maps
    exactly the six layer names. Per-layer required flags (``action_options``
    must declare structured output) are enforced after the generic bounds.
    """
    if isinstance(raw_profiles, Mapping):
        entries = list(raw_profiles.items())
    else:
        entries = list(raw_profiles)
    seen: set[str] = set()
    for layer, _ in entries:
        if layer not in LAYER_NAMES:
            raise UnknownLayerError(layer)
        if layer in seen:
            raise ProfileValidationError(layer, "<profile>", "duplicate layer entry")
        seen.add(layer)
    merged = default_profiles()
    merged.update(dict(entries))
    profiles: dict[str, LLMProfile] = {}
    for layer, values in merged.items():
        validate_profile_values(layer, values)
        for field, required in REQUIRED_PROFILE_FLAGS.get(layer, {}).items():
            if values.get(field) is not required:
                raise ProfileValidationError(
                    layer,
                    field,
                    f"must be {required!r} for the {layer!r} layer",
                )
        profiles[layer] = LLMProfile(**dict(values))
    return MappingProxyType(profiles)


def get_profile(layer: str) -> LLMProfile:
    """Return the frozen profile for one layer from ``settings.LLM_PROFILES``."""
    if layer not in LAYER_NAMES:
        raise UnknownLayerError(layer)
    raw = getattr(settings, "LLM_PROFILES", None)
    if not raw:
        raw = default_profiles()
    profiles = build_profiles(raw)
    return profiles[layer]
