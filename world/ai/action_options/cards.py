"""Frozen card vocabulary (action-options schema design doc §1, §2).

This module owns the immutable ``OptionSet``/``SuggestionCard`` vocabulary
exchanged between the generative layer, the trigger service, and the
``context_actions`` presentation. It is a pure, proposal-only module: it
imports no Evennia typeclasses and no state writer at module time, holds no
module-level logger binding, and never mutates game state. The single-writer
boundary is untouched — this vocabulary is proposal-only by construction.

The bounds constants below are the single source mirrored later by
``protocol.js`` under the dual-direction parity test.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from web.webclient.presentation.protocol import MAX_SAFE_INTEGER
from world.ai.immutable import (
    reject_mutable_containers as _reject_mutable_containers,
)

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


class OptionsValidationError(ValueError):
    """One named ladder rejection; carries the rejection code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


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
