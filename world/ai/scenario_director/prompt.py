"""Deterministic bounded prompt construction for quest generation.

The bounded-context serializer, the deterministic name-inspiration bank, and
``build_scenario_prompt`` (design D2, namegen-npc-flow D1). The prompt-library
``scenario_director.system`` key is the sole source of the system-message text;
nothing here embeds it as a Python constant.

The boundary contract (``tests/test_ai_transport_contract.py``): this module
imports no state writer, no typeclass, no live transport, and no socket. It
reads only the side-effect-free ``world.rules.namegen`` pure rollers
(documented read-only-rule exemption, namegen-npc-flow design D6).
"""

from __future__ import annotations

import json
import zlib
from random import Random
from typing import Any

from world.prompts.loader import render_prompt
from world.rules.namegen import roll_name_for_race

from world.ai.scenario_director.blueprints import (
    MAX_CONTEXT_FIELD_LENGTH,
    MAX_TOTAL_SIZE,
)

_CONTEXT_KEYS = ("requested_type", "allowed_rank", "issuer_branch", "anchor", "note")
# Optional keys dropped (in this order) if the serialized context still
# exceeds the total-size bound, so the user message is always valid bounded JSON.
_CONTEXT_DROP_ORDER = ("note", "anchor", "requested_type", "allowed_rank")


def _cap_string(value: str) -> str:
    if len(value) <= MAX_CONTEXT_FIELD_LENGTH:
        return value
    return value[:MAX_CONTEXT_FIELD_LENGTH]


def _bounded_context(context: Any) -> str:
    """Serialize the request context within the hard prompt bounds.

    Only the fixed context keys are accepted; every string value is capped to
    ``MAX_CONTEXT_FIELD_LENGTH``. If the stable sorted JSON serialization still
    exceeds ``MAX_TOTAL_SIZE``, optional keys are dropped in a fixed order until
    it fits, so the returned text is always valid JSON within the bound.
    """
    if not isinstance(context, dict):
        raise TypeError("scenario-director context must be a mapping")
    payload: dict[str, Any] = {}
    for key in _CONTEXT_KEYS:
        if key not in context or context[key] is None:
            continue
        value = context[key]
        if not isinstance(value, (str, int, float, bool)):
            raise TypeError(f"scenario-director context field {key!r} must be plain data")
        payload[key] = _cap_string(str(value)) if isinstance(value, str) else value
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    for drop_key in _CONTEXT_DROP_ORDER:
        if len(text) <= MAX_TOTAL_SIZE or drop_key not in payload:
            continue
        del payload[drop_key]
        text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return text


# Name-inspiration bank (namegen-npc-flow design D1): a fixed count so the
# same bounded context always renders a byte-identical system message. The
# separator matches the catalogue's 正體中文 listing idiom.
_INSPIRATION_COUNT = 6
_INSPIRATION_SEPARATOR = "、"


def _name_inspirations(bounded_context_text: str) -> str:
    """Roll the deterministic name-inspiration bank for one bounded context.

    The seed is the crc32 of the FINAL serialized (capped and key-dropped)
    user-message text, not the raw context dict, so contexts that normalize
    to the same bounded text share the same bank (spec: context-seeded bank).
    Every roll goes through the read-only ``world.rules.namegen`` layer with
    one ``Random`` instance drawn in order, which keeps the bank sequence
    stable; an empty sex string routes the rule layer to its random pool,
    which is exactly the inspiration-only intent (no declared sex exists at
    prompt time). The names are style anchors, never commitments.
    """
    rng = Random(zlib.crc32(bounded_context_text.encode("utf-8")))
    return _INSPIRATION_SEPARATOR.join(
        roll_name_for_race(None, "", rng) for _ in range(_INSPIRATION_COUNT)
    )


def build_scenario_prompt(
    context: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    """Build a deterministic (system, user) message pair for quest generation.

    The system message fixes the director role in 伊洛瑟恩大陸, the 正體中文
    language, the no-invention fidelity rule, and the ``QuestBlueprint`` JSON
    output contract with contiguous stage indices, and carries a deterministic
    name-inspiration bank rendered into the library text's ``{name_inspiration}``
    placeholder. The user message serializes the request context (requested
    type, allowed rank, issuer branch, anchor, and an optional note) with
    stable sorted JSON and ``ensure_ascii=False``. Identical input always
    produces byte-identical prompts with no live entity references; the bank
    is seeded from the serialized user text, so the inspiration names exist
    only inside the returned strings and mutate no state.
    """
    user_text = _bounded_context(context)
    system = {
        "role": "system",
        "content": render_prompt(
            "scenario_director.system",
            name_inspiration=_name_inspirations(user_text),
        ),
    }
    user = {"role": "user", "content": user_text}
    return system, user
