"""Declarative LLM knob table — the single inert source for LLM env names.

Import-safe by contract (design D-A4): this module is stdlib-only, performs
zero environment reads, and imports nothing that touches Django settings. That
lets ``server/conf/test_settings.py`` sanitize the generated names before the
production settings import, and lets the inventory contract tests consume the
exact name set that ``server/conf/settings.py`` resolves through a loop (an
AST extractor cannot see loop-constructed names).

``LAYER_NAMES`` lives here so the knob table and the profile registry can
never disagree on the layer set; ``world/ai/profiles.py`` imports it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

LAYER_NAMES: tuple[str, ...] = (
    "narrator",
    "npc_dialogue",
    "scenario_director",
    "scene_builder",
    "character_creation",
    "action_options",
    "title_nomination",
)

# Resolution kinds consumed by the dispatcher in server/conf/settings.py.
KIND_STR = "str"
KIND_FLOAT = "float"
KIND_INT = "int"
KIND_BOOL = "bool"
KIND_CHOICE = "choice"


@dataclass(frozen=True)
class LlmKnob:
    """One profile field reachable through ``LLM_<SUFFIX>`` and per-layer names.

    ``default`` is the code default shared by all layers, except the knobs
    listed in ``layer_defaults``; bounds mirror ``validate_profile_values`` in
    ``world/ai/profiles.py`` — ``minimum`` is an EXCLUSIVE lower bound,
    ``at_least``/``maximum`` inclusive, identical to ``_env_typed``.
    """

    field: str
    suffix: str
    kind: str
    default: object = None
    choices: tuple[str, ...] = ()
    minimum: float | None = None
    at_least: float | None = None
    maximum: float | None = None
    rule: str = ""
    layer_defaults: Mapping[str, object] | None = None

    def layer_default(self, layer: str) -> object:
        """Return the code default for one layer (honouring per-layer defaults)."""
        if self.layer_defaults is not None and layer in self.layer_defaults:
            return self.layer_defaults[layer]
        return self.default


# The 23 knobs of the endpoint-configuration design §3.1, in documented order.
# A None-resolved optional value means "no environment intent"; the field then
# keeps its code default and the follow-up wire change omits it from the body.
LLM_KNOBS: tuple[LlmKnob, ...] = (
    LlmKnob("base_url", "BASE_URL", KIND_STR, "http://127.0.0.1:11434"),
    LlmKnob("path", "PATH", KIND_STR, "/v1/chat/completions"),
    LlmKnob("api_key", "API_KEY", KIND_STR, ""),
    LlmKnob("app_title", "APP_TITLE", KIND_STR, ""),
    LlmKnob("app_url", "APP_URL", KIND_STR, ""),
    LlmKnob("model", "MODEL", KIND_STR, "llama3.2"),
    LlmKnob(
        "temperature",
        "TEMPERATURE",
        KIND_FLOAT,
        0.7,
        at_least=0.0,
        maximum=2.0,
        rule="expected a finite float in 0..2",
    ),
    LlmKnob(
        "frequency_penalty",
        "FREQUENCY_PENALTY",
        KIND_FLOAT,
        None,
        at_least=-2.0,
        maximum=2.0,
        rule="expected a finite float in -2..2",
    ),
    LlmKnob(
        "presence_penalty",
        "PRESENCE_PENALTY",
        KIND_FLOAT,
        None,
        at_least=-2.0,
        maximum=2.0,
        rule="expected a finite float in -2..2",
    ),
    LlmKnob(
        "top_k",
        "TOP_K",
        KIND_INT,
        None,
        minimum=0,
        rule="expected a positive integer",
    ),
    LlmKnob(
        "top_p",
        "TOP_P",
        KIND_FLOAT,
        None,
        minimum=0.0,
        maximum=1.0,
        rule="expected a float in 0 < x <= 1",
    ),
    LlmKnob(
        "repetition_penalty",
        "REPETITION_PENALTY",
        KIND_FLOAT,
        None,
        minimum=0.0,
        rule="expected a float greater than 0",
    ),
    LlmKnob(
        "min_p",
        "MIN_P",
        KIND_FLOAT,
        None,
        at_least=0.0,
        maximum=1.0,
        rule="expected a float in 0..1",
    ),
    LlmKnob(
        "top_a",
        "TOP_A",
        KIND_FLOAT,
        None,
        at_least=0.0,
        rule="expected a non-negative float",
    ),
    LlmKnob("reasoning_enabled", "REASONING_ENABLED", KIND_BOOL, None),
    LlmKnob(
        "reasoning_effort",
        "REASONING_EFFORT",
        KIND_CHOICE,
        None,
        choices=("minimal", "low", "medium", "high"),
    ),
    LlmKnob(
        "reasoning_style",
        "REASONING_STYLE",
        KIND_CHOICE,
        "openrouter",
        choices=("openrouter", "vllm", "off"),
    ),
    LlmKnob(
        "max_completion_tokens",
        "MAX_COMPLETION_TOKENS",
        KIND_INT,
        None,
        minimum=0,
        rule="expected a positive integer",
    ),
    LlmKnob(
        "max_tokens",
        "MAX_TOKENS",
        KIND_INT,
        250,
        minimum=0,
        rule="expected a positive integer",
        layer_defaults={"action_options": 320, "title_nomination": 640},
    ),
    LlmKnob(
        "timeout_seconds",
        "TIMEOUT_SECONDS",
        KIND_INT,
        60,
        minimum=0,
        rule="expected a positive integer",
    ),
    LlmKnob(
        "max_retries",
        "MAX_RETRIES",
        KIND_INT,
        2,
        at_least=0,
        rule="expected a non-negative integer",
    ),
    LlmKnob("supports_response_format", "SUPPORTS_RESPONSE_FORMAT", KIND_BOOL, False),
    LlmKnob("enabled", "ENABLED", KIND_BOOL, True),
)


def llm_global_env_names() -> frozenset[str]:
    """The 23 global ``LLM_<SUFFIX>`` names."""
    return frozenset(f"LLM_{knob.suffix}" for knob in LLM_KNOBS)


def llm_layer_env_names(layer: str) -> frozenset[str]:
    """The 23 per-layer ``LLM_<LAYER>_<SUFFIX>`` names for one layer."""
    prefix = f"LLM_{layer.upper()}_"
    return frozenset(f"{prefix}{knob.suffix}" for knob in LLM_KNOBS)


def llm_env_names() -> frozenset[str]:
    """Every generated name: 23 globals plus 23 per layer for all seven layers."""
    names: set[str] = set(llm_global_env_names())
    for layer in LAYER_NAMES:
        names |= llm_layer_env_names(layer)
    return frozenset(names)
