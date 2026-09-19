"""The 12-stage validation ladder and the exact-field wire parser.

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
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import TYPE_CHECKING

from world.ai.action_options.cards import (
    CARD_KINDS,
    CONTEXT_KIND,
    FREEFORM_ACTION_CODE,
    MAX_CARDS,
    MAX_HINT_LENGTH,
    MAX_LABEL_LENGTH,
    OptionSet,
    OptionsValidationError,
    READY_STATUS,
    SuggestionCard,
)

if TYPE_CHECKING:
    from typing import Any

    from web.webclient.presentation.affordances import AffordanceView

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
