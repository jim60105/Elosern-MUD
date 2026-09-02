"""Frozen action-options card vocabulary and the validation ladder (proposals only).

This module owns the immutable ``OptionSet``/``SuggestionCard`` vocabulary
exchanged between the generative layer, the trigger service, and the
``context_actions`` presentation. It is a pure, proposal-only module: it
imports no Evennia typeclasses and no state writer at module time, holds no
module-level logger binding, and never mutates game state. The single-writer
boundary is untouched — this vocabulary is proposal-only by construction.

The vocabulary-lock contract (overview D-1): a validated card's payload is a
copy of one *currently executable* affordance. The ladder's stage 9 resolves
``action_code`` against the caller-supplied affordance list and unconditionally
replaces the card's ``params`` with that affordance's canonical payload, so a
card shipped to the client is byte-for-byte the payload the dispatcher accepts.
The single exception is the ``freeform`` card, whose ``{"npc_id": int}`` params
are binding-only: no registered validator produces that shape without
``speech``, so the full dispatcher validator runs only on the client-composed
dispatch payload (webclient change).

The 12-stage ladder order (stages 0-11) is public contract: the pipeline reuses
the stage numbers for retry messages, and the first failing stage wins and maps
to degrade. ``validate_optionset`` returns an ``OptionSet`` on success and
raises ``OptionsValidationError`` carrying one named rejection code on the
first failure.

The generative layer (pipeline design doc) extends this module with the
bounded-context serializer, the prompt assembly, and the guarded generation
pipeline: ``build_options_context`` truncates the deterministic view in fixed
order, ``build_action_options_prompt`` renders the two ``action_options``
prompt-library keys, and ``generate_action_options`` runs the guardrail's
validation-retry-degrade loop (with the degrade fallback and the raw-wire
output schema installed by ``register_action_options``). The same import
discipline holds: no Evennia import, no state writer, no live transport, and
no module-level logger binding at module time; the only outputs are the frozen
``OptionSet`` proposal and ``None``.

The bounds constants below are the single source mirrored later by
``protocol.js`` under the dual-direction parity test.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from twisted.internet import defer

from web.webclient.presentation.protocol import MAX_SAFE_INTEGER
from world.ai import guardrail
from world.ai.guardrail import (
    GuardrailRegistrationError,
    guarded_call,
    register_degrade_fallback,
)
from world.ai.profiles import get_profile
from world.ai.schemas import ChatRequestDescriptor
from world.ai.schemas.registry import (
    DuplicateSchemaError,
    _OUTPUT_SCHEMAS,
    register_output_schema,
)
from world.prompts.loader import PromptUnavailableError, render_prompt

if TYPE_CHECKING:
    from web.webclient.presentation.affordances import AffordanceView

# Bounds table (schema design doc §2) — the single source for the card
# vocabulary; the client mirror in protocol.js repeats these under the
# dual-direction parity test.
MIN_CARDS = 3
MAX_CARDS = 5
MAX_LABEL_LENGTH = 24
MAX_HINT_LENGTH = 60
MAX_PARAMS = 4
MAX_PARAM_STRING_LENGTH = 32
MAX_OPTIONSET_CACHE_ENTRIES = 16
NEGATIVE_MEMO_TTL = 30

FREEFORM_ACTION_CODE = "explore.talk_freeform"
CONTEXT_KIND = "exploration"
READY_STATUS = "ready"
CARD_KINDS = ("known_action", "freeform")

# Named rejection codes of the ladder (spec requirement 3).
SCHEMA_VIOLATION = "schema_violation"
CARD_COUNT_OUT_OF_RANGE = "card_count_out_of_range"
EMPTY_LABEL = "empty_label"
LABEL_TOO_LONG = "label_too_long"
NON_CJK_LABEL = "non_cjk_label"
PLACEHOLDER_LABEL = "placeholder_label"
DIGIT_IN_LABEL = "digit_in_label"
UNKNOWN_ACTION_CODE = "unknown_action_code"
NO_SUCH_AFFORDANCE = "no_such_affordance"
UNKNOWN_TARGET = "unknown_target"
HINT_TOO_LONG = "hint_too_long"
LEAK_DETECTED = "leak_detected"

LADDER_CODES = (
    SCHEMA_VIOLATION,
    CARD_COUNT_OUT_OF_RANGE,
    EMPTY_LABEL,
    LABEL_TOO_LONG,
    NON_CJK_LABEL,
    PLACEHOLDER_LABEL,
    DIGIT_IN_LABEL,
    UNKNOWN_ACTION_CODE,
    NO_SUCH_AFFORDANCE,
    UNKNOWN_TARGET,
    HINT_TOO_LONG,
    LEAK_DETECTED,
)

# Stage 7: a generic brace token, unlike narrator's token-specific regex.
_PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
# Stage 8: a mechanical ASCII-digit gate (narrator alignment).
_DIGIT_RE = re.compile(r"[0-9]")
# Stage 2: an opaque fingerprint of 8..64 characters without whitespace.
_FINGERPRINT_RE = re.compile(r"^[^\s]{8,64}$")


class OptionsValidationError(ValueError):
    """One named ladder rejection; carries the rejection code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _reject_mutable_containers(value: Any, path: str) -> None:
    """Reject any ``dict``/``list`` nested under ``value`` so immutability is
    enforced by construction, not only by the frozen dataclass."""
    if isinstance(value, (dict, list)):
        raise TypeError(f"{path} holds a mutable dict/list container")
    if isinstance(value, tuple):
        for index, item in enumerate(value):
            _reject_mutable_containers(item, f"{path}[{index}]")
    elif is_dataclass(value):
        for dataclass_field in fields(value):
            _reject_mutable_containers(
                getattr(value, dataclass_field.name),
                f"{path}.{dataclass_field.name}",
            )


def _validate_params_shape(params: Mapping[str, Any], path: str) -> None:
    """Validate the wire value shapes of one params mapping.

    Values are ints within ``MAX_SAFE_INTEGER``, strings up to
    ``MAX_PARAM_STRING_LENGTH``, or — as the single boolean exception — the
    exact room-survey marker ``{"room": true}`` of the canonical look payload
    (schema design doc §1.1). Any other boolean or any boolean mixed with other
    fields is rejected, so a proposal never carries a wire value no dispatcher
    validator produces. Anything else (including any nested container) is
    rejected so a proposal never holds a mutable value.
    """
    if len(params) > MAX_PARAMS:
        raise ValueError(f"{path} exceeds the maximum of {MAX_PARAMS} params")
    for key, value in params.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{path} params keys must be non-empty strings")
        if isinstance(value, bool):
            if params != {"room": True}:
                raise ValueError(
                    f"{path} boolean values are allowed only as the exact "
                    "room-survey marker {\"room\": true}"
                )
            continue
        if isinstance(value, int):
            if not 0 <= value <= MAX_SAFE_INTEGER:
                raise ValueError(
                    f"{path}[{key!r}] is outside the JavaScript-safe integer range"
                )
            continue
        if isinstance(value, str):
            if len(value) > MAX_PARAM_STRING_LENGTH:
                raise ValueError(
                    f"{path}[{key!r}] exceeds the maximum of "
                    f"{MAX_PARAM_STRING_LENGTH} chars"
                )
            continue
        raise TypeError(
            f"{path}[{key!r}] holds a value of unsupported type "
            f"{type(value).__name__}"
        )


@dataclass(frozen=True)
class SuggestionCard:
    """One suggestion card: exactly one of two wire shapes.

    A ``known_action`` card carries a real dispatcher action id and params that
    are a canonical copy of one current affordance (after stage 9). A
    ``freeform`` card carries ``action_code == "explore.talk_freeform"`` and the
    binding-only params ``{"npc_id": int}``; the full dispatcher validator runs
    only on the client-composed dispatch payload.
    """

    kind: str
    action_code: str
    label: str
    params: Mapping[str, str | int | bool]
    hint: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in CARD_KINDS:
            raise ValueError(f"kind {self.kind!r} is outside {CARD_KINDS}")
        if not isinstance(self.action_code, str) or not self.action_code:
            raise ValueError("action_code must be a non-empty string")
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("label must be a non-empty string")
        if self.hint is not None and not isinstance(self.hint, str):
            raise ValueError("hint must be a string or None")
        if not isinstance(self.params, Mapping):
            raise ValueError("params must be a mapping")
        _validate_params_shape(self.params, type(self).__name__)
        object.__setattr__(
            self, "params", MappingProxyType(dict(self.params))
        )
        _reject_mutable_containers(self, type(self).__name__)


@dataclass(frozen=True)
class OptionSet:
    """The frozen proposal: fingerprint, exploration kind, ready status, cards.

    Construction rejects any status other than ``"ready"`` (transport states
    like ``generating``/``degraded`` are never cached) and any context kind
    other than ``"exploration"`` (the v1 closed enum), mirroring the
    ``QuestBlueprint`` construction discipline.
    """

    fingerprint: str
    context_kind: str = CONTEXT_KIND
    status: str = READY_STATUS
    cards: tuple[SuggestionCard, ...] = ()

    def __post_init__(self) -> None:
        if self.status != READY_STATUS:
            raise ValueError(f"status must be exactly {READY_STATUS!r}")
        if self.context_kind != CONTEXT_KIND:
            raise ValueError(f"context_kind must be exactly {CONTEXT_KIND!r}")
        if not isinstance(self.fingerprint, str) or not self.fingerprint:
            raise ValueError("fingerprint must be a non-empty string")
        if not isinstance(self.cards, tuple):
            raise TypeError("cards must be a tuple of SuggestionCard")
        for card in self.cards:
            if not isinstance(card, SuggestionCard):
                raise TypeError("cards must be a tuple of SuggestionCard")
        _reject_mutable_containers(self, type(self).__name__)


def _has_cjk(text: str) -> bool:
    """True when ``text`` contains no CJK codepoint (narrator's exact rule).

    Delegates to ``world/ai/narrator.py::_validate_has_cjk`` — the single
    reused validator of this module (schema design doc stage 6–8 amendment).
    Imported lazily so this module keeps no Evennia import at module time
    (narrator transitively imports ``evennia.logger`` through the guardrail);
    the import happens at call time, inside the Evennia runtime.
    """
    from world.ai.narrator import _validate_has_cjk

    return bool(_validate_has_cjk(text))


def _leaked(text: str, blocklist: frozenset[str]) -> bool:
    """True when any blocklist token appears in the NFKC-normalized text.

    Mirrors the npc_dialogue no-leak validator shape: NFKC normalization folds
    fullwidth digits into ASCII so a decimal secret cannot be disguised, and
    tokens are matched as substrings of the player-facing text.
    """
    if not blocklist:
        return False
    normalized = unicodedata.normalize("NFKC", text)
    return any(token and token in normalized for token in blocklist)


def enrich_options_payload(raw: Any, *, fingerprint: str) -> dict[str, Any]:
    """Inject caller-side fields into the raw LLM payload (ladder stage 0).

    Given the model payload (``context_kind`` plus ``cards``, without the
    caller-side ``fingerprint``/``status``), inject the caller-supplied
    ``fingerprint``, set ``status`` to ``"ready"``, derive each card's
    ``kind``, and default every freeform card's ``action_code`` to
    ``"explore.talk_freeform"``. The ``{npc_index}`` -> ``{"npc_id": int}``
    binding resolution is owned by the generative layer; fixtures here feed
    already-resolved params. Any structural violation raises
    ``OptionsValidationError`` with ``schema_violation``.
    """
    if not isinstance(raw, Mapping):
        raise OptionsValidationError(
            SCHEMA_VIOLATION, "raw payload must be an object"
        )
    cards = raw.get("cards")
    if not isinstance(cards, list):
        raise OptionsValidationError(
            SCHEMA_VIOLATION, "cards must be a list of card objects"
        )
    enriched_cards: list[dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, Mapping):
            raise OptionsValidationError(
                SCHEMA_VIOLATION, "each card must be an object"
            )
        enriched_card = dict(card)
        if "kind" not in enriched_card:
            if "action_code" in enriched_card:
                enriched_card["kind"] = "known_action"
            else:
                enriched_card["kind"] = "freeform"
                enriched_card["action_code"] = FREEFORM_ACTION_CODE
        enriched_card.setdefault("params", {})
        enriched_cards.append(enriched_card)
    enriched = dict(raw)
    enriched["fingerprint"] = fingerprint
    enriched["status"] = READY_STATUS
    enriched["cards"] = enriched_cards
    return enriched


def parse_action_options_payload(payload: Any) -> dict[str, Any]:
    """Exact-field parse of the decoded model output (schema doc §5).

    Validates the inline ``response_format`` JSON shape: the top level carries
    exactly ``context_kind`` and ``cards`` (``fingerprint``/``status`` are
    caller-side and absent), and each card is exactly one of two forms — a
    known_action card carrying ``action_code``, ``label``, optional ``params``
    and ``hint``, or a freeform card carrying ``npc_index``, ``label`` and
    optional ``hint``. Unknown keys and wrong shapes are rejected with a named
    rejection instead of being silently coerced (the
    ``web/webclient/presentation/protocol.py`` parser pattern). The freeform
    ``npc_index`` fixture path is layer-owned: the generative layer resolves it
    to ``{"npc_id": int}`` params before enrichment.
    """
    if not isinstance(payload, dict):
        raise OptionsValidationError(
            SCHEMA_VIOLATION, "model output must be an object"
        )
    if set(payload) != {"context_kind", "cards"}:
        raise OptionsValidationError(
            SCHEMA_VIOLATION,
            "model output must carry exactly context_kind and cards",
        )
    context_kind = payload["context_kind"]
    if not isinstance(context_kind, str):
        raise OptionsValidationError(
            SCHEMA_VIOLATION, "context_kind must be a string"
        )
    cards = payload["cards"]
    if not isinstance(cards, list):
        raise OptionsValidationError(
            SCHEMA_VIOLATION, "cards must be a list of card objects"
        )
    parsed_cards: list[dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, dict):
            raise OptionsValidationError(
                SCHEMA_VIOLATION, "each card must be an object"
            )
        has_action_code = "action_code" in card
        has_npc_index = "npc_index" in card
        if has_action_code == has_npc_index:
            raise OptionsValidationError(
                SCHEMA_VIOLATION,
                "a card must be exactly one of the known_action or freeform forms",
            )
        if has_action_code:
            allowed = {"action_code", "label", "params", "hint"}
            if set(card) - allowed or "label" not in card:
                raise OptionsValidationError(
                    SCHEMA_VIOLATION,
                    "known_action cards carry action_code, label, and "
                    "optional params/hint",
                )
            if not isinstance(card["action_code"], str) or not card["action_code"]:
                raise OptionsValidationError(
                    SCHEMA_VIOLATION, "action_code must be a non-empty string"
                )
            if not isinstance(card["label"], str):
                raise OptionsValidationError(
                    SCHEMA_VIOLATION, "label must be a string"
                )
            if "params" in card and not isinstance(card["params"], dict):
                raise OptionsValidationError(
                    SCHEMA_VIOLATION, "params must be an object"
                )
            if "hint" in card and not isinstance(card["hint"], str):
                raise OptionsValidationError(
                    SCHEMA_VIOLATION, "hint must be a string"
                )
        else:
            allowed = {"npc_index", "label", "hint"}
            if set(card) - allowed or "label" not in card:
                raise OptionsValidationError(
                    SCHEMA_VIOLATION,
                    "freeform cards carry npc_index, label, and optional hint",
                )
            if (
                isinstance(card["npc_index"], bool)
                or not isinstance(card["npc_index"], int)
            ):
                raise OptionsValidationError(
                    SCHEMA_VIOLATION, "npc_index must be an integer"
                )
            if not isinstance(card["label"], str):
                raise OptionsValidationError(
                    SCHEMA_VIOLATION, "label must be a string"
                )
            if "hint" in card and not isinstance(card["hint"], str):
                raise OptionsValidationError(
                    SCHEMA_VIOLATION, "hint must be a string"
                )
        parsed_cards.append(card)
    return {"context_kind": context_kind, "cards": parsed_cards}


def _registered_action_codes() -> frozenset[str]:
    """The globally registered exploration action codes (change 1 vocabulary).

    Imported lazily so this module keeps no Evennia/state-writer import at
    module time; the affordance vocabulary lives in the web presentation layer.
    """
    from web.webclient.presentation.affordances import ACTION_CODE_ALLOWLIST

    return frozenset(ACTION_CODE_ALLOWLIST)


def _resolve_known_action(
    card: dict[str, Any], affordances: tuple[AffordanceView, ...]
) -> None:
    """Stage-9 canonical match for a known_action card.

    Resolves ``action_code`` to the unique current executable affordance and
    replaces the card's params with its canonical payload (model params are
    curation hints, never equality-checked for a unique code). When several
    affordances share the code, the model's typed params select the entry whose
    canonical payload they match; an ambiguous or absent selector rejects with
    ``no_such_affordance``.
    """
    code = card["action_code"]
    candidates = [
        entry
        for entry in affordances
        if not entry.navigation
        and not entry.freeform
        and getattr(entry, "enabled", True)
        and entry.action_id == code
    ]
    if not candidates:
        if code in _registered_action_codes():
            raise OptionsValidationError(
                NO_SUCH_AFFORDANCE,
                f"action {code!r} is registered but not a current affordance",
            )
        raise OptionsValidationError(
            UNKNOWN_ACTION_CODE, f"action code {code!r} is not registered"
        )
    if len(candidates) == 1:
        entry = candidates[0]
    else:
        typed = card.get("params") or {}
        matches = [entry for entry in candidates if entry.params == typed]
        if len(matches) != 1:
            raise OptionsValidationError(
                NO_SUCH_AFFORDANCE,
                f"action {code!r} does not resolve to a unique current "
                "affordance from the card params",
            )
        entry = matches[0]
    card["params"] = dict(entry.params)


def _resolve_freeform(
    card: dict[str, Any], affordances: tuple[AffordanceView, ...]
) -> None:
    """Stage-9 freeform binding check.

    Requires ``action_code == "explore.talk_freeform"`` and params exactly
    ``{"npc_id": int}`` where the ``npc_id`` equals a freeform affordance's
    bound target (the binding-only exception; the full dispatcher validator
    runs only on the client-composed payload). The matched freeform affordance
    itself must carry exactly the binding shape, and the validated card's
    params stay exactly ``{"npc_id": int}`` — never a copy of the affordance's
    params, which could smuggle extra fields past the binding contract.
    """
    if card["action_code"] != FREEFORM_ACTION_CODE:
        raise OptionsValidationError(
            UNKNOWN_ACTION_CODE,
            f"a freeform card must carry action_code {FREEFORM_ACTION_CODE!r}",
        )
    params = card.get("params") or {}
    if (
        not isinstance(params, Mapping)
        or set(params) != {"npc_id"}
        or isinstance(params.get("npc_id"), bool)
        or not isinstance(params.get("npc_id"), int)
    ):
        raise OptionsValidationError(
            UNKNOWN_TARGET,
            "freeform params must be exactly {\"npc_id\": int}",
        )
    npc_id = params["npc_id"]
    bound = [
        entry
        for entry in affordances
        if entry.freeform
        and getattr(entry, "enabled", True)
        and isinstance(entry.params, Mapping)
        and set(entry.params) == {"npc_id"}
        and entry.params.get("npc_id") == npc_id
    ]
    if not bound:
        raise OptionsValidationError(
            UNKNOWN_TARGET,
            f"no freeform affordance binds target {npc_id}",
        )
    card["params"] = {"npc_id": npc_id}


def validate_optionset(
    raw: Any,
    *,
    fingerprint: str,
    affordances: tuple[AffordanceView, ...],
    leak_blocklist: frozenset[str] = frozenset(),
) -> OptionSet:
    """Run the fixed 12-stage validation ladder on one proposal.

    The first failing stage wins and raises ``OptionsValidationError`` with one
    named rejection code; the caller (the generative layer) maps any rejection
    to degrade. On success an immutable ``OptionSet`` is returned with the
    cards in the model's original order (stage 11 keeps LLM order).
    """
    # Stage 0: enrichment (caller-side field injection and card defaults).
    enriched = enrich_options_payload(raw, fingerprint=fingerprint)
    # Stage 1: structure — exactly the OptionSet keys; cards a sequence of
    # dicts.
    if set(enriched) != {"fingerprint", "context_kind", "status", "cards"}:
        raise OptionsValidationError(
            SCHEMA_VIOLATION,
            "the enriched payload must carry exactly fingerprint, "
            "context_kind, status, and cards",
        )
    cards = enriched["cards"]
    if not isinstance(cards, list) or not all(
        isinstance(card, dict) for card in cards
    ):
        raise OptionsValidationError(
            SCHEMA_VIOLATION, "cards must be a list of card objects"
        )
    # Stage 2: fingerprint — opaque string of 8..64 chars, no whitespace.
    if (
        not isinstance(fingerprint, str)
        or not _FINGERPRINT_RE.fullmatch(fingerprint)
    ):
        raise OptionsValidationError(
            SCHEMA_VIOLATION,
            "fingerprint must be an opaque string of 8..64 chars "
            "without whitespace",
        )
    # Stage 3: kind — the v1 closed enum.
    if enriched["context_kind"] != CONTEXT_KIND:
        raise OptionsValidationError(
            SCHEMA_VIOLATION,
            f"context_kind must be exactly {CONTEXT_KIND!r} in v1",
        )
    # Stage 4: card count — the ladder accepts 0..5 (the 3..5 minimum is a
    # generation rule owned by the layer, not a ladder rejection).
    if not 0 <= len(cards) <= MAX_CARDS:
        raise OptionsValidationError(
            CARD_COUNT_OUT_OF_RANGE,
            f"card count must be within 0..{MAX_CARDS}",
        )
    # Stage 5: card kind and exact keys.
    for card in cards:
        keys = set(card)
        if not {"kind", "action_code", "label", "params"} <= keys <= {
            "kind",
            "action_code",
            "label",
            "params",
            "hint",
        }:
            raise OptionsValidationError(
                SCHEMA_VIOLATION,
                "a card must carry exactly kind, action_code, label, params, "
                "and optional hint",
            )
        if card["kind"] not in CARD_KINDS:
            raise OptionsValidationError(
                SCHEMA_VIOLATION, f"card kind {card['kind']!r} is outside {CARD_KINDS}"
            )
        if not isinstance(card["action_code"], str) or not card["action_code"]:
            raise OptionsValidationError(
                SCHEMA_VIOLATION, "action_code must be a non-empty string"
            )
        if not isinstance(card["label"], str):
            raise OptionsValidationError(
                SCHEMA_VIOLATION, "label must be a string"
            )
        if not isinstance(card["params"], Mapping):
            raise OptionsValidationError(
                SCHEMA_VIOLATION, "params must be an object"
            )
        hint = card.get("hint")
        if hint is not None and not isinstance(hint, str):
            raise OptionsValidationError(
                SCHEMA_VIOLATION, "hint must be a string or absent"
            )
    # Stage 6: label — non-empty, bounded, contains at least one CJK codepoint
    # (reuses the narrator's exact CJK validator).
    for card in cards:
        label = card["label"]
        if not label.strip():
            raise OptionsValidationError(
                EMPTY_LABEL, "label must be non-empty"
            )
        if len(label) > MAX_LABEL_LENGTH:
            raise OptionsValidationError(
                LABEL_TOO_LONG,
                f"label exceeds the maximum of {MAX_LABEL_LENGTH} chars",
            )
        if _has_cjk(label):
            raise OptionsValidationError(
                NON_CJK_LABEL,
                "label must contain at least one CJK codepoint",
            )
    # Stage 7: placeholder gate — no generic {...} token in any label/hint.
    for card in cards:
        if _PLACEHOLDER_RE.search(card["label"]):
            raise OptionsValidationError(
                PLACEHOLDER_LABEL, "label must not contain a template placeholder"
            )
        hint = card.get("hint")
        if hint is not None and _PLACEHOLDER_RE.search(hint):
            raise OptionsValidationError(
                PLACEHOLDER_LABEL, "hint must not contain a template placeholder"
            )
    # Stage 8: digit gate — no ASCII digit in any label.
    for card in cards:
        if _DIGIT_RE.search(card["label"]):
            raise OptionsValidationError(
                DIGIT_IN_LABEL, "label must not contain ASCII digits"
            )
    # Stage 9: canonical match (vocabulary lock).
    for card in cards:
        if card["kind"] == "freeform":
            _resolve_freeform(card, affordances)
        else:
            _resolve_known_action(card, affordances)
    # Stage 10: hint gate — bounded length, the leak (numeric) gate applies to
    # labels and hints only (never to params), and the digit gate closes hint
    # numerals (design.md label-digit-gate risk). The leak predicate runs
    # before the digit gate so a blocklisted numeric literal is reported as a
    # leak, matching the spec's leak scenario.
    for card in cards:
        hint = card.get("hint")
        if hint is not None and len(hint) > MAX_HINT_LENGTH:
            raise OptionsValidationError(
                HINT_TOO_LONG,
                f"hint exceeds the maximum of {MAX_HINT_LENGTH} chars",
            )
        if _leaked(card["label"], leak_blocklist):
            raise OptionsValidationError(
                LEAK_DETECTED, "label echoes a hidden value"
            )
        if hint is not None and _leaked(hint, leak_blocklist):
            raise OptionsValidationError(
                LEAK_DETECTED, "hint echoes a hidden value"
            )
        if hint is not None and _DIGIT_RE.search(hint):
            raise OptionsValidationError(
                DIGIT_IN_LABEL, "hint must not contain ASCII digits"
            )
    # Stage 11: normalization — keep the model's order (it is the curatorial
    # intent); build the frozen OptionSet.
    return OptionSet(
        fingerprint=fingerprint,
        context_kind=CONTEXT_KIND,
        status=READY_STATUS,
        cards=tuple(
            SuggestionCard(
                kind=card["kind"],
                action_code=card["action_code"],
                label=card["label"],
                params=card["params"],
                hint=card.get("hint"),
            )
            for card in cards
        ),
    )


# ==== Bounded-context serializer (pipeline design doc §2) ====

# Hard context budgets; the single source the trigger service's deterministic
# view mirrors. ``affordances``, ``room_name``, and ``room_summary`` are never
# truncated (a summary of what you *can't* do is useless); every other field is
# truncated by ``build_options_context`` in the fixed order: narrative tail
# first (oldest characters), then persona-digest characters, then the oldest
# NPC (and monster) entries.
MAX_ROOM_NAME_LENGTH = 40
MAX_ROOM_SUMMARY_LENGTH = 300
MAX_NARRATIVE_TAIL_LENGTH = 600
MAX_NPC_ENTRIES = 8
MAX_NPC_DIGEST_LENGTH = 160
MAX_MONSTER_ENTRIES = 4
MAX_MONSTER_ENTRY_LENGTH = 80
MAX_OBJECTIVE_LENGTH = 120
MAX_AFFORDANCES = 16


class ActionOptionsInputError(ValueError):
    """A context input outside its hard budget or of the wrong shape.

    Raised by ``build_options_context`` and ``ActionOptionsContext``
    construction; the generation entry point catches it, logs a bounded
    diagnostic, and resolves ``None`` — out-of-bounds data is never emitted.
    """


class ActionOptionsBindingError(ValueError):
    """A freeform ``{npc_index}`` binding failure (unknown index or duplicate)."""


class ActionOptionsClientRequiredError(TypeError):
    """Raised when a generation call is made with an explicit ``None`` client."""


class ActionOptionsNotRegisteredError(RuntimeError):
    """Raised when the action_options layer's hooks are not installed."""


@dataclass(frozen=True)
class ActionOptionsNPCEntry:
    """One present NPC in the bounded context (stable positional identity).

    ``npc_id`` is the deterministic entity id the freeform binding resolves to;
    ``persona_digest`` is the public persona digest (never true traits);
    ``public_tier`` is the relationship tier label (e.g. 好感層級), never the
    numeric affinity — the same boundary npc_dialogue observes. Construction
    validates every field type so a later digest-length check can never hit a
    non-string.
    """

    npc_id: int
    display_name: str
    dialogue_key: str | None = None
    persona_digest: str = ""
    public_tier: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.npc_id, bool) or not isinstance(self.npc_id, int):
            raise ActionOptionsInputError("npc_id must be an integer")
        if not isinstance(self.display_name, str) or not self.display_name:
            raise ActionOptionsInputError("display_name must be a non-empty string")
        if not isinstance(self.persona_digest, str):
            raise ActionOptionsInputError("persona_digest must be a string")
        for field in ("dialogue_key", "public_tier"):
            value = getattr(self, field)
            if value is not None and not isinstance(value, str):
                raise ActionOptionsInputError(f"{field} must be a string or None")


@dataclass(frozen=True)
class ActionOptionsMonsterEntry:
    """One present monster in the bounded context."""

    monster_id: int
    display_name: str
    threat_tier: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.monster_id, bool) or not isinstance(self.monster_id, int):
            raise ActionOptionsInputError("monster_id must be an integer")
        if not isinstance(self.display_name, str) or not self.display_name:
            raise ActionOptionsInputError("display_name must be a non-empty string")
        if self.threat_tier is not None and not isinstance(self.threat_tier, str):
            raise ActionOptionsInputError("threat_tier must be a string or None")


@dataclass(frozen=True)
class ActionOptionsContext:
    """The frozen bounded context for one action-options generation.

    Construction is strict: every field is type-checked and every cap is
    enforced, raising ``ActionOptionsInputError`` for out-of-bounds values.
    ``build_options_context`` is the sanctioned constructor that applies the
    fixed truncation policy first. ``affordances`` holds the canonical tuple
    the ladder validates against (never truncated); ``leak_blocklist`` is
    consumed by validation only and never rendered into a prompt.
    """

    room_name: str
    room_summary: str
    npc_entries: tuple[ActionOptionsNPCEntry, ...]
    monster_entries: tuple[ActionOptionsMonsterEntry, ...]
    objective: str | None
    narrative_tail: str
    affordances: tuple[AffordanceView, ...]
    leak_blocklist: frozenset[str]

    def __post_init__(self) -> None:
        self._check_budget("room_name", self.room_name, MAX_ROOM_NAME_LENGTH)
        self._check_budget("room_summary", self.room_summary, MAX_ROOM_SUMMARY_LENGTH)
        self._check_budget("narrative_tail", self.narrative_tail, MAX_NARRATIVE_TAIL_LENGTH)
        if self.objective is not None and not isinstance(self.objective, str):
            raise ActionOptionsInputError("objective must be a string or None")
        if self.objective is not None and len(self.objective) > MAX_OBJECTIVE_LENGTH:
            raise ActionOptionsInputError(
                f"objective exceeds the maximum of {MAX_OBJECTIVE_LENGTH} chars"
            )
        if not isinstance(self.npc_entries, tuple) or not all(
            isinstance(entry, ActionOptionsNPCEntry) for entry in self.npc_entries
        ):
            raise ActionOptionsInputError("npc_entries must be a tuple of NPCEntry")
        if len(self.npc_entries) > MAX_NPC_ENTRIES:
            raise ActionOptionsInputError(
                f"npc_entries exceed the maximum of {MAX_NPC_ENTRIES} entries"
            )
        for entry in self.npc_entries:
            if len(entry.persona_digest) > MAX_NPC_DIGEST_LENGTH:
                raise ActionOptionsInputError(
                    f"persona digest exceeds the maximum of {MAX_NPC_DIGEST_LENGTH} chars"
                )
        if not isinstance(self.monster_entries, tuple) or not all(
            isinstance(entry, ActionOptionsMonsterEntry) for entry in self.monster_entries
        ):
            raise ActionOptionsInputError("monster_entries must be a tuple of MonsterEntry")
        if len(self.monster_entries) > MAX_MONSTER_ENTRIES:
            raise ActionOptionsInputError(
                f"monster_entries exceed the maximum of {MAX_MONSTER_ENTRIES} entries"
            )
        for entry in self.monster_entries:
            if len(entry.display_name) > MAX_MONSTER_ENTRY_LENGTH:
                raise ActionOptionsInputError(
                    f"monster display name exceeds the maximum of "
                    f"{MAX_MONSTER_ENTRY_LENGTH} chars"
                )
        if not isinstance(self.affordances, tuple) or not all(
            isinstance(getattr(entry, "navigation", None), bool)
            and isinstance(getattr(entry, "action_id", None), (str, type(None)))
            and hasattr(entry, "label")
            for entry in self.affordances
        ):
            raise ActionOptionsInputError(
                "affordances must be a tuple of AffordanceView entries"
            )
        if len(self.affordances) > MAX_AFFORDANCES:
            raise ActionOptionsInputError(
                f"affordances exceed the maximum of {MAX_AFFORDANCES} entries"
            )
        if not isinstance(self.leak_blocklist, frozenset) or any(
            not isinstance(token, str) or not token for token in self.leak_blocklist
        ):
            raise ActionOptionsInputError(
                "leak_blocklist must be a frozenset of non-empty strings"
            )

    def _check_budget(self, field: str, value: Any, cap: int) -> None:
        if not isinstance(value, str):
            raise ActionOptionsInputError(f"{field} must be a string")
        if len(value) > cap:
            raise ActionOptionsInputError(f"{field} exceeds the maximum of {cap} chars")


def _build_npc_entry(raw: Mapping[str, Any]) -> ActionOptionsNPCEntry:
    """Validate one plain-data NPC mapping and bound its persona digest."""
    if not isinstance(raw, Mapping):
        raise ActionOptionsInputError("each npc entry must be a mapping")
    npc_id = raw.get("npc_id")
    display_name = raw.get("display_name")
    if isinstance(npc_id, bool) or not isinstance(npc_id, int):
        raise ActionOptionsInputError("npc_id must be an integer")
    if not isinstance(display_name, str) or not display_name:
        raise ActionOptionsInputError("display_name must be a non-empty string")
    for field in ("dialogue_key", "public_tier"):
        value = raw.get(field)
        if value is not None and not isinstance(value, str):
            raise ActionOptionsInputError(f"{field} must be a string or absent")
    digest = raw.get("persona_digest", "")
    if not isinstance(digest, str):
        raise ActionOptionsInputError("persona_digest must be a string")
    return ActionOptionsNPCEntry(
        npc_id=npc_id,
        display_name=display_name,
        dialogue_key=raw.get("dialogue_key"),
        persona_digest=digest[:MAX_NPC_DIGEST_LENGTH],
        public_tier=raw.get("public_tier"),
    )


def _build_monster_entry(raw: Mapping[str, Any]) -> ActionOptionsMonsterEntry:
    """Validate one plain-data monster mapping and bound its display name."""
    if not isinstance(raw, Mapping):
        raise ActionOptionsInputError("each monster entry must be a mapping")
    monster_id = raw.get("monster_id")
    display_name = raw.get("display_name")
    if isinstance(monster_id, bool) or not isinstance(monster_id, int):
        raise ActionOptionsInputError("monster_id must be an integer")
    if not isinstance(display_name, str) or not display_name:
        raise ActionOptionsInputError("display_name must be a non-empty string")
    threat_tier = raw.get("threat_tier")
    if threat_tier is not None and not isinstance(threat_tier, str):
        raise ActionOptionsInputError("threat_tier must be a string or absent")
    return ActionOptionsMonsterEntry(
        monster_id=monster_id,
        display_name=display_name[:MAX_MONSTER_ENTRY_LENGTH],
        threat_tier=threat_tier,
    )


def build_options_context(
    *,
    room_name: str,
    room_summary: str,
    narrative_tail: str,
    npc_entries: Sequence[Mapping[str, Any]],
    monster_entries: Sequence[Mapping[str, Any]] = (),
    objective: str | None = None,
    affordances: Sequence[AffordanceView],
    secret_tokens: Iterable[str] = (),
) -> ActionOptionsContext:
    """Assemble the frozen bounded context from caller-supplied plain data.

    The fixed truncation policy applies to the truncatable fields only:
    narrative tail keeps the most recent ``MAX_NARRATIVE_TAIL_LENGTH``
    characters (oldest dropped first), persona digests keep their first
    ``MAX_NPC_DIGEST_LENGTH`` characters, and NPC/monster entries beyond the
    caps drop the oldest. ``affordances``, ``room_name``, and ``room_summary``
    are never truncated: an over-cap value raises ``ActionOptionsInputError``.
    ``secret_tokens`` (numeric literals + hidden trait keys of the
    deterministic view) compose the context's ``LEAK_BLOCKLIST``, consumed by
    validation only. Identical input produces a byte-identical frozen context
    with no live entity references; NPC order is the caller's stable order.
    """
    if not isinstance(narrative_tail, str):
        raise ActionOptionsInputError("narrative_tail must be a string")
    if objective is not None and not isinstance(objective, str):
        raise ActionOptionsInputError("objective must be a string or None")
    if isinstance(secret_tokens, str):
        raise ActionOptionsInputError(
            "secret_tokens must be an iterable of strings, not a string"
        )
    if len(affordances) > MAX_AFFORDANCES:
        raise ActionOptionsInputError(
            f"affordances exceed the maximum of {MAX_AFFORDANCES} entries"
        )
    npc = tuple(npc_entries)[-MAX_NPC_ENTRIES:]
    monsters = tuple(monster_entries)[-MAX_MONSTER_ENTRIES:]
    return ActionOptionsContext(
        room_name=room_name,
        room_summary=room_summary,
        npc_entries=tuple(_build_npc_entry(entry) for entry in npc),
        monster_entries=tuple(_build_monster_entry(entry) for entry in monsters),
        objective=objective[:MAX_OBJECTIVE_LENGTH] if objective is not None else None,
        narrative_tail=narrative_tail[-MAX_NARRATIVE_TAIL_LENGTH:],
        affordances=tuple(affordances),
        leak_blocklist=frozenset(token for token in secret_tokens if token),
    )


# ==== Prompt assembly (pipeline design doc §3) ====


def _serialize_structured(value: Any) -> str:
    """Deterministic stable-key JSON with non-ASCII kept literal."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def build_action_options_prompt(
    context: ActionOptionsContext,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build the deterministic (system, user) message pair for one proposal.

    Both messages render through the prompt library's two ``action_options``
    keys: the system key with no substitution values (empty allowlist), the
    user key with exactly the seven serialized ``ActionOptionsContext`` fields
    (``leak_blocklist`` is never rendered). Structured fields are
    pre-serialized: NPC entries carry their stable positional ``npc_index`` so
    freeform cards reference a present person without the model typing an id,
    and the affordance list carries each entry's canonical ``action_id`` +
    typed params (navigation entries have no dispatcher code and are excluded).
    Identical input always produces byte-identical messages with no live entity
    references.
    """
    system = {"role": "system", "content": render_prompt("action_options.system")}
    npc_entries = [
        {
            "npc_index": index,
            "npc_id": entry.npc_id,
            "display_name": entry.display_name,
            "dialogue_key": entry.dialogue_key,
            "persona_digest": entry.persona_digest,
            "public_tier": entry.public_tier,
        }
        for index, entry in enumerate(context.npc_entries)
    ]
    monster_entries = [
        {
            "monster_id": entry.monster_id,
            "display_name": entry.display_name,
            "threat_tier": entry.threat_tier,
        }
        for entry in context.monster_entries
    ]
    affordances = [
        {
            "action_id": entry.action_id,
            "label": entry.label,
            "params": dict(entry.params or {}),
        }
        for entry in context.affordances
        if not entry.navigation
    ]
    user = {
        "role": "user",
        "content": render_prompt(
            "action_options.user",
            room_name=context.room_name,
            room_summary=context.room_summary,
            npc_entries=_serialize_structured(npc_entries),
            monster_entries=_serialize_structured(monster_entries),
            objective=context.objective or "",
            narrative_tail=context.narrative_tail,
            affordances=_serialize_structured(affordances),
        ),
    }
    return system, user


# ==== Generation pipeline (pipeline design doc §4-§5) ====


# The raw model wire shape (schema design doc §5): ``context_kind`` plus
# ``cards`` where a known_action card carries action_code/label and optional
# params/hint, and a freeform card carries npc_index/label and optional hint.
# The caller-injected ``fingerprint``/``status`` (and the enriched
# ``kind``/``action_code``/``params``) never appear here (design D-7); the
# exact-field parser enforces the same contract with named rejections.
ACTION_OPTIONS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["context_kind", "cards"],
    "additionalProperties": False,
    "properties": {
        "context_kind": {"type": "string", "enum": [CONTEXT_KIND]},
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label"],
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "hint": {"type": "string"},
                    "action_code": {"type": "string"},
                    "params": {"type": "object"},
                    "npc_index": {"type": "integer", "minimum": 0},
                },
                "oneOf": [
                    {"required": ["action_code"]},
                    {"required": ["npc_index"]},
                ],
            },
        },
    },
}

_ACTION_OPTIONS_DEGRADED = object()


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the public ``None``."""
    return _ACTION_OPTIONS_DEGRADED


def _resolve_freeform_bindings(
    payload: Mapping[str, Any], npc_bindings: tuple[int, ...]
) -> dict[str, Any]:
    """Resolve every freeform card's ``{npc_index}`` against the bound NPC list.

    The prompt's bound NPC list fixes the positional order; an out-of-range
    index, or a target already bound by an earlier freeform card in the same
    proposal, rejects the card with a binding error (design D-4). Resolved
    cards carry the enriched freeform shape (``kind``, ``action_code``,
    ``params``) so the ladder's stage-0 enrichment keeps them freeform and
    stage 9 validates the binding-only params.
    """
    resolved_cards: list[dict[str, Any]] = []
    bound_targets: set[int] = set()
    for card in payload["cards"]:
        if "npc_index" not in card:
            resolved_cards.append(dict(card))
            continue
        index = card["npc_index"]
        if index < 0 or index >= len(npc_bindings):
            raise ActionOptionsBindingError(
                f"freeform npc_index {index} is outside the bound NPC list"
            )
        target = npc_bindings[index]
        if target in bound_targets:
            raise ActionOptionsBindingError(
                f"freeform npc_index {index} binds target {target} twice"
            )
        bound_targets.add(target)
        resolved = {key: value for key, value in card.items() if key != "npc_index"}
        resolved["kind"] = "freeform"
        resolved["action_code"] = FREEFORM_ACTION_CODE
        resolved["params"] = {"npc_id": target}
        resolved_cards.append(resolved)
    return {"context_kind": payload["context_kind"], "cards": resolved_cards}


# The stage each ladder code is reported with in retry messages — the first
# ladder stage able to raise the code (schema design doc §3). Parse failures
# share the structure stage (1): the exact-field parser enforces the raw JSON
# contract before the ladder, so enrichment-stage violations are unreachable
# after a successful parse.
_STAGE_BY_CODE: Mapping[str, int] = {
    SCHEMA_VIOLATION: 1,
    CARD_COUNT_OUT_OF_RANGE: 4,
    EMPTY_LABEL: 6,
    LABEL_TOO_LONG: 6,
    NON_CJK_LABEL: 6,
    PLACEHOLDER_LABEL: 7,
    DIGIT_IN_LABEL: 8,
    UNKNOWN_ACTION_CODE: 9,
    NO_SUCH_AFFORDANCE: 9,
    UNKNOWN_TARGET: 9,
    HINT_TOO_LONG: 10,
    LEAK_DETECTED: 10,
}


def _stage_message(code: str) -> str:
    return f"stage {_STAGE_BY_CODE.get(code, 0)}: {code}"


def _evaluate_enriched(
    parsed: Any,
    *,
    fingerprint: str,
    affordances: tuple[AffordanceView, ...],
    npc_bindings: tuple[int, ...],
    leak_blocklist: frozenset[str],
) -> tuple[OptionSet | None, list[str]]:
    """Total enrichment + binding + ladder evaluation; never raises (design D-3).

    Returns ``(OptionSet, [])`` on success, or ``(None, [message])`` where the
    message is a named error for the guardrail's retry loop: ``"stage N: <code>"``
    for ladder/parse rejections, the binding error text for freeform resolution,
    and a generation-rule message for sets the ladder accepts below ``MIN_CARDS``.
    Every parsing, enrichment, binding, and ladder exception is converted here —
    nothing escapes into ``guarded_call``, which would errback the Deferred
    instead of retrying.
    """
    try:
        payload = parse_action_options_payload(parsed)
    except OptionsValidationError as exc:  # observability: ignore R2: error becomes the retry-feedback message, not a log
        return None, [_stage_message(exc.code)]
    try:
        resolved = _resolve_freeform_bindings(payload, npc_bindings)
    except ActionOptionsBindingError as exc:  # observability: ignore R2: error becomes the retry-feedback message, not a log
        return None, [str(exc)]
    try:
        optionset = validate_optionset(
            resolved,
            fingerprint=fingerprint,
            affordances=affordances,
            leak_blocklist=leak_blocklist,
        )
    except OptionsValidationError as exc:  # observability: ignore R2: error becomes the retry-feedback message, not a log
        return None, [_stage_message(exc.code)]
    except (TypeError, ValueError) as exc:  # observability: ignore R2: error becomes the bounded internal-error feedback message
        return None, [f"internal error: {type(exc).__name__}: {exc}"]
    if len(optionset.cards) < MIN_CARDS:
        return None, [f"generation rule: fewer than {MIN_CARDS} cards proposed"]
    return optionset, []


def _make_enriched_validator(
    *,
    fingerprint: str,
    affordances: tuple[AffordanceView, ...],
    npc_bindings: tuple[int, ...],
    leak_blocklist: frozenset[str],
) -> Callable[[Any], list[str]]:
    """Return the per-call semantic validator bound to this call's data (D-2).

    The closure is carried by the request descriptor, never registered: it
    captures only this call's immutable copies of the fingerprint, affordance
    tuple, NPC bindings, and leak blocklist, so an interleaved second call can
    never observe another call's data.
    """

    def validate(parsed: Any) -> list[str]:
        _, errors = _evaluate_enriched(
            parsed,
            fingerprint=fingerprint,
            affordances=affordances,
            npc_bindings=npc_bindings,
            leak_blocklist=leak_blocklist,
        )
        return errors

    return validate


def _is_registered() -> bool:
    """True when the guardrail registries hold every action_options hook."""
    if guardrail._degrade_fallbacks.get("action_options") is not _degrade_fallback:
        return False
    return _OUTPUT_SCHEMAS.get("action_options") is ACTION_OPTIONS_OUTPUT_SCHEMA


def _require_registered() -> None:
    if not _is_registered():
        raise ActionOptionsNotRegisteredError(
            "the action_options layer is not registered; call register_action_options() first"
        )


def _uninstall_fallback() -> None:
    if guardrail._degrade_fallbacks.get("action_options") is _degrade_fallback:
        del guardrail._degrade_fallbacks["action_options"]


def _uninstall_schema() -> None:
    if _OUTPUT_SCHEMAS.get("action_options") is ACTION_OPTIONS_OUTPUT_SCHEMA:
        del _OUTPUT_SCHEMAS["action_options"]


def _uninstall_all_own_hooks() -> None:
    """Remove every action_options hook this module installed (by identity)."""
    _uninstall_fallback()
    _uninstall_schema()


def register_action_options() -> None:
    """Install the action_options layer's guardrail hooks atomically and idempotently.

    Registers the sentinel degrade fallback and the raw-wire output schema
    (design D-7). No semantic validators are registered — the ladder owns every
    text gate, and the per-call closure rides the request descriptor (D-2). On
    a partial failure every hook belonging to this module (by identity) is
    removed before the error propagates, so the layer is never left
    half-registered. A second call is a no-op that keeps the first
    registration.
    """
    if _is_registered():
        return
    try:
        if guardrail._degrade_fallbacks.get("action_options") is not _degrade_fallback:
            register_degrade_fallback("action_options", _degrade_fallback)
        if _OUTPUT_SCHEMAS.get("action_options") is not ACTION_OPTIONS_OUTPUT_SCHEMA:
            register_output_schema("action_options", ACTION_OPTIONS_OUTPUT_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _uninstall_all_own_hooks()
        raise


def _log_bounded_diagnostic(problem: str) -> None:
    """Log one bounded degrade diagnostic through the observability facade."""
    from world.observability import log_warn

    log_warn("action_options_diagnostic", context={"problem": problem})


@defer.inlineCallbacks
def generate_action_options(
    context: ActionOptionsContext,
    client: Any,
    *,
    fingerprint: str,
):
    """Run the action_options layer's guarded pipeline for one proposal.

    Args:
        context: The frozen bounded context (``build_options_context`` output)
            whose affordance tuple is the vocabulary-lock source and whose
            ``leak_blocklist`` feeds the ladder's leak gates.
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); an explicit ``None`` is rejected with
            ``ActionOptionsClientRequiredError`` before any prompt construction
            or transport interaction.
        fingerprint: The caller-supplied opaque situation fingerprint; carried
            through into the enriched ``OptionSet`` and into the ladder entry
            point, never rendered into the prompt.

    Returns:
        A Deferred resolving to a frozen ``OptionSet`` (``status: "ready"``,
        3-5 cards in the model's order) on success, or to ``None`` — the single
        public degraded marker — when the profile is disabled (before any
        prompt construction or transport work), the prompt key is unavailable,
        the transport fails (no retry loop; the trigger service memoizes), the
        retry budget is exhausted, or an over-budget context input raises
        ``ActionOptionsInputError``. No state change is ever made.
    """
    if client is None:
        raise ActionOptionsClientRequiredError(
            "generate_action_options requires an injected client; got None"
        )
    if not get_profile("action_options").enabled:
        return None
    _require_registered()
    try:
        system, user = build_action_options_prompt(context)
    except (PromptUnavailableError, ActionOptionsInputError) as exc:  # observability: ignore R2: logged via _log_bounded_diagnostic below
        _log_bounded_diagnostic(str(exc))
        return None
    npc_bindings = tuple(entry.npc_id for entry in context.npc_entries)
    descriptor = ChatRequestDescriptor(
        messages=(system, user),
        schema_id="action_options",
        semantic_validators={
            "enriched_optionset": _make_enriched_validator(
                fingerprint=fingerprint,
                affordances=context.affordances,
                npc_bindings=npc_bindings,
                leak_blocklist=context.leak_blocklist,
            ),
        },
    )
    text = yield guarded_call("action_options", client, descriptor)
    if text is _ACTION_OPTIONS_DEGRADED:
        return None
    parsed = json.loads(text)
    optionset, errors = _evaluate_enriched(
        parsed,
        fingerprint=fingerprint,
        affordances=context.affordances,
        npc_bindings=npc_bindings,
        leak_blocklist=context.leak_blocklist,
    )
    if optionset is None:
        _log_bounded_diagnostic(
            "accepted text failed strict re-validation: " + " | ".join(errors)
        )
        return None
    return optionset


__all__ = [
    "ACTION_OPTIONS_OUTPUT_SCHEMA",
    "ActionOptionsBindingError",
    "ActionOptionsClientRequiredError",
    "ActionOptionsContext",
    "ActionOptionsInputError",
    "ActionOptionsMonsterEntry",
    "ActionOptionsNPCEntry",
    "ActionOptionsNotRegisteredError",
    "CARD_KINDS",
    "CARD_COUNT_OUT_OF_RANGE",
    "CONTEXT_KIND",
    "DIGIT_IN_LABEL",
    "EMPTY_LABEL",
    "FREEFORM_ACTION_CODE",
    "HINT_TOO_LONG",
    "LABEL_TOO_LONG",
    "LADDER_CODES",
    "LEAK_DETECTED",
    "MAX_AFFORDANCES",
    "MAX_CARDS",
    "MAX_HINT_LENGTH",
    "MAX_LABEL_LENGTH",
    "MAX_MONSTER_ENTRIES",
    "MAX_MONSTER_ENTRY_LENGTH",
    "MAX_NARRATIVE_TAIL_LENGTH",
    "MAX_NPC_DIGEST_LENGTH",
    "MAX_NPC_ENTRIES",
    "MAX_OBJECTIVE_LENGTH",
    "MAX_OPTIONSET_CACHE_ENTRIES",
    "MAX_PARAMS",
    "MAX_ROOM_NAME_LENGTH",
    "MAX_ROOM_SUMMARY_LENGTH",
    "MAX_SAFE_INTEGER",
    "MIN_CARDS",
    "NEGATIVE_MEMO_TTL",
    "NO_SUCH_AFFORDANCE",
    "NON_CJK_LABEL",
    "OptionsValidationError",
    "OptionSet",
    "PLACEHOLDER_LABEL",
    "READY_STATUS",
    "SCHEMA_VIOLATION",
    "SuggestionCard",
    "UNKNOWN_ACTION_CODE",
    "UNKNOWN_TARGET",
    "build_action_options_prompt",
    "build_options_context",
    "enrich_options_payload",
    "generate_action_options",
    "parse_action_options_payload",
    "register_action_options",
    "validate_optionset",
]
