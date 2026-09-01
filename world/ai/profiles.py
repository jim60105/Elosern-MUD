"""Per-layer LLM endpoint profiles with strict construction-time validation.

The generative layer is governed by one ``LLMProfile`` per layer, read from the
``LLM_PROFILES`` Django setting. Profiles are frozen, validated at
construction, and never clamped: a failing bound raises a named error naming
the layer and field so misconfiguration surfaces at startup rather than at a
live call.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
import math
from types import MappingProxyType
from typing import Any

from django.conf import settings

# The inert knob table owns the layer set so generated environment names and
# the profile registry can never disagree (design D-A4); re-exported here for
# every existing consumer of ``profiles.LAYER_NAMES``.
from server.conf.llm_knobs import LAYER_NAMES

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_CHAT_PATH = "/v1/chat/completions"
DEFAULT_MODEL = "llama3.2"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 250
ACTION_OPTIONS_MAX_TOKENS = 320
# 5-candidate ``{display, basis}`` JSON payload (change G); sized like the
# action-options payload with headroom for 80-character Traditional-Chinese
# basis quotes.
TITLE_NOMINATION_MAX_TOKENS = 640
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 2
DEFAULT_HEADERS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {"Content-Type": ("application/json",)}
)

# Closed sets for the optional reasoning fields (endpoint design §4.1).
REASONING_EFFORTS: tuple[str, ...] = ("minimal", "low", "medium", "high")
REASONING_STYLES: tuple[str, ...] = ("openrouter", "vllm", "off")

# The dataclass repr includes the headers mapping, so a bearer value smuggled
# into headers would defeat api_key's repr=False exclusion; fail closed so
# api_key stays the single credential route (design D-A5).
CREDENTIAL_HEADER_NAMES = frozenset(
    {"authorization", "proxy-authorization", "x-api-key", "api-key"}
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
        if key.lower() in CREDENTIAL_HEADER_NAMES:
            raise ProfileValidationError(
                layer,
                "headers",
                f"{key!r} is a credential-bearing header; use the api_key"
                " profile field as the sanctioned credential route",
            )
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
    # Optional endpoint-configuration fields (endpoint design §4.1). The api
    # key is excluded from the repr: profile debug output never carries a
    # credential. Unset optionals serialize as nothing in the request body.
    api_key: str = field(default="", repr=False)
    app_title: str = ""
    app_url: str = ""
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    top_k: int | None = None
    top_p: float | None = None
    repetition_penalty: float | None = None
    min_p: float | None = None
    top_a: float | None = None
    reasoning_enabled: bool | None = None
    reasoning_effort: str | None = None
    reasoning_style: str = "openrouter"
    max_completion_tokens: int | None = None

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
            "api_key": self.api_key,
            "app_title": self.app_title,
            "app_url": self.app_url,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty,
            "min_p": self.min_p,
            "top_a": self.top_a,
            "reasoning_enabled": self.reasoning_enabled,
            "reasoning_effort": self.reasoning_effort,
            "reasoning_style": self.reasoning_style,
            "max_completion_tokens": self.max_completion_tokens,
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
    # Raw maps may omit these keys entirely (the dataclass default applies);
    # direct construction always passes them, so an explicit None is rejected.
    for field in ("api_key", "app_title", "app_url"):
        if field in values and not isinstance(values[field], str):
            raise ProfileValidationError(layer, field, "must be a string")
    for field, rule, in_range in (
        (
            "frequency_penalty",
            "must be None or a finite float in -2..2",
            lambda v: -2 <= v <= 2,
        ),
        (
            "presence_penalty",
            "must be None or a finite float in -2..2",
            lambda v: -2 <= v <= 2,
        ),
        (
            "top_p",
            "must be None or a finite float in 0 < x <= 1",
            lambda v: 0 < v <= 1,
        ),
        (
            "repetition_penalty",
            "must be None or a finite float greater than 0",
            lambda v: 0 < v,
        ),
        (
            "min_p",
            "must be None or a finite float in 0..1",
            lambda v: 0 <= v <= 1,
        ),
        (
            "top_a",
            "must be None or a non-negative finite float",
            lambda v: 0 <= v,
        ),
    ):
        value = values.get(field)
        if value is None:
            continue
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not in_range(float(value))
        ):
            raise ProfileValidationError(layer, field, rule)
    for field in ("top_k", "max_completion_tokens"):
        value = values.get(field)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ProfileValidationError(
                layer, field, "must be None or a positive integer"
            )
    reasoning_enabled = values.get("reasoning_enabled")
    if reasoning_enabled is not None and not isinstance(reasoning_enabled, bool):
        raise ProfileValidationError(layer, "reasoning_enabled", "must be None or a boolean")
    reasoning_effort = values.get("reasoning_effort")
    if reasoning_effort is not None and reasoning_effort not in REASONING_EFFORTS:
        raise ProfileValidationError(
            layer,
            "reasoning_effort",
            "must be None or one of " + "/".join(REASONING_EFFORTS),
        )
    # A raw map may omit the key entirely (the dataclass default applies);
    # direct construction always passes it, so an explicit None is rejected.
    if "reasoning_style" in values and values["reasoning_style"] not in REASONING_STYLES:
        raise ProfileValidationError(
            layer,
            "reasoning_style",
            "must be one of " + "/".join(REASONING_STYLES),
        )
    _normalize_headers(values.get("headers"), layer)


def default_profiles(
    defaults: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return the local-first default ``LLM_PROFILES`` dict for every layer.

    The module performs no environment reads (design D-A3): the base URL is
    the bare-metal localhost code default, and ``server/conf/settings.py``
    injects its environment-resolved per-layer field overrides through
    ``defaults``. ``supports_response_format`` defaults false because design §7.5 only
    requests structured output when the endpoint declares support; the
    ``action_options`` layer is the single exception and always defaults to
    the capability on, with ``max_tokens`` sized for a 5-card JSON payload
    (pipeline design doc §5).
    """
    profiles = {
        layer: {
            "base_url": DEFAULT_BASE_URL,
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
    profiles["title_nomination"] = {
        **profiles["title_nomination"],
        "max_tokens": TITLE_NOMINATION_MAX_TOKENS,
    }
    if defaults is not None:
        for layer, overrides in defaults.items():
            if layer not in LAYER_NAMES:
                raise UnknownLayerError(layer)
            profiles[layer] = {**profiles[layer], **dict(overrides)}
            # Injected values pass the same construction-time bounds here, so
            # an invalid environment value fails even before build_profiles.
            validate_profile_values(layer, profiles[layer])
    return profiles


def build_profiles(
    raw_profiles: Mapping[str, Mapping[str, Any]] | Iterable[tuple[str, Mapping[str, Any]]],
) -> Mapping[str, LLMProfile]:
    """Validate a raw ``LLM_PROFILES`` source and build frozen profiles.

    Accepts either a mapping or an iterable of ``(layer, values)`` pairs so
    duplicate layer keys can be detected. Unknown layers are rejected, every
    profile is validated against every bound, and any of the seven layers missing
    from the source falls back to the local-first default so the registry maps
    exactly the seven layer names. Per-layer required flags (``action_options``
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
