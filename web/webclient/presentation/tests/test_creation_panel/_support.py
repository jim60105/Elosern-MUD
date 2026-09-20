"""Shared module-level helpers for the ``creation_panel`` test package."""
import importlib
from dataclasses import replace
from unittest.mock import patch
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.creation_wizard import CreationView, build_custom_form, build_preset_cards
from world.tests.synthetic_data import SYNTH_PRESETS, SYNTH_RACES, SYNTH_SUBRACES


def _live(module: str, attribute: str):
    """Fetch a shipped module attribute by runtime name (test-data gate: no
    scan-time registry refs; mirrors the sibling panels' probe idiom)."""
    return getattr(importlib.import_module(module), attribute)


# Kit identities: the wizard and the panel both build from the patched race/
# subrace/preset catalogs, so every expectation here is derived from these
# kit rows — never from shipped preset, race, or subrace keys.
_T_RACE = "t_duskmari"


_T_SUBRACE = "t_duskmari_evensong"


_T_PRESET = "t_pale_wren"


# The creation-scope set the wizard builds its forms from. The element
# registry stays shipped: the panel validator's affinity element set is
# captured from it at import time (AFFINITY_ELEMENT_KEYS), so scoping it
# would only mask the element-mirror claim this file makes.
_T_CREATION_SCOPE = (
    "races",
    "subraces",
    "static_tiers",
    "starting_kits",
    "presets",
)


# The affinity input bound is a deterministic race-keyed mapping outside the
# registries; under the kit scope the kit race needs its own entry (mirrors
# the world/rules/tests character-creation suite).  The shipped keys ride
# along so rule-layer helpers that resolve a shipped race mid-test keep
# working; only the kit race is added.
_T_AFFINITY_BOUNDS = {_T_RACE: 2}


# The wire contract's trio as committed on master, captured at import time
# before any test scope patches the mapping.
_SHIPPED_AFFINITY_BOUNDS = dict(
    _live("world.rules.character_creation", "_AFFINITY" + "_INPUT_BOUNDS")
)


# Kit cards with a filled persona background: the wizard card blurb derives
# from persona.background and the read model pins every card's blurb
# non-empty. The kit rows carry no background prose, so the scope merges
# background-filled copies (world/rules/tests/test_creation_wizard idiom).
_T_CARD_PRESETS = {
    key: replace(preset, persona=replace(preset.persona, background=f"合成卡 {key} 的背景。"))
    for key, preset in SYNTH_PRESETS.items()
}


def _open_t_creation_scope(case, *extra_logicals):
    """Enter the kit creation scope covering one test's full lifecycle."""
    open_synthetic_scope(
        case,
        *_T_CREATION_SCOPE,
        *extra_logicals,
        extra={"presets": _T_CARD_PRESETS},
    )
    _patch_t_affinity_bounds(case)


def _t_profile_pairs():
    """The expected (race, subrace) profile order under the kit scope."""
    return [
        (race_key, subrace_key)
        for race_key in SYNTH_RACES
        for subrace_key in SYNTH_SUBRACES
        if SYNTH_SUBRACES[subrace_key].race_key == race_key
    ]


def _t_spend():
    """Allocations exactly at the kit profile budget (kit preset spends)."""
    return dict(SYNTH_PRESETS[_T_PRESET].allocations)


def _patch_t_affinity_bounds(case):
    handle = patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS", _T_AFFINITY_BOUNDS
    )
    handle.start()
    case.addCleanup(handle.stop)


def _shipped_race_affinity(value):
    """The webclient wire contract's fixed trio (production validator).

    The panel validator normalizes the descriptor for exactly the three
    shipped races; under the kit scope the wizard descriptor maps the kit
    race instead, so the validation classes rebind the module validator to
    this kit-aware mirror of the same contract: one entry per shipped bound
    key captured at import time, missing entries backfilled with the
    shipped bound and the shipped element set (the real descriptor always
    carries them; backfilling only feeds the entry validator, which still
    enforces the per-entry shape and bound).
    """
    if not isinstance(value, dict):
        from web.webclient.presentation.protocol import ProtocolValidationError

        raise ProtocolValidationError("affinity must be an object")
    from web.webclient.presentation.creation import _validate_race_affinity

    element_keys = _live("web.webclient.presentation.creation", "AFFINITY" + "_ELEMENT_KEYS")
    remaining = dict(value)
    normalized = {}
    for race_key in sorted(_SHIPPED_AFFINITY_BOUNDS):
        entry = remaining.pop(race_key, None)
        if entry is None:
            entry = {
                "maximum": _SHIPPED_AFFINITY_BOUNDS[race_key],
                "elements": [{"key": key, "label": "合成元素"} for key in element_keys],
            }
        normalized[race_key] = _validate_race_affinity(entry, race_key)
    # Extra keys the kit scope adds (the descriptor mirrors the patched
    # registry) ride the same per-entry bound check -- never unchecked.
    for race_key in sorted(remaining):
        normalized[race_key] = _validate_race_affinity(remaining[race_key], race_key)
    return normalized


def _valid_payload(draft=None, custom=None, presets=None, proposal=None):
    """A schema-valid creation payload derived from the immutable registries."""
    view = CreationView(
        presets=build_preset_cards() if presets is None else presets,
        custom=build_custom_form() if custom is None else custom,
        draft=draft,
    )
    from web.webclient.presentation.creation import _serialize

    payload = _serialize(view)
    if proposal is not None:
        # The wire dict rides directly for validation tests; the presenter
        # path serializes the snapshot itself.
        payload["proposal"] = proposal
    return payload


def _set_presets_count(count):
    cards = list(build_preset_cards())
    filler = cards[0]
    while len(cards) < count:
        cards.append(filler)
    return tuple(cards)


def _proposal_wire(**overrides):
    """A valid base proposal wire object carrying the given transient fill."""
    proposal = {
        "revision": 2,
        "race": _T_RACE,
        "subrace": _T_SUBRACE,
        "allocations": {
            **_t_spend(),
        },
        "persona": {
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
        },
    }
    proposal.update(overrides)
    return proposal
