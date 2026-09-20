"""Shared module-level helpers for the ``test_creation_actions`` test package."""


from copy import deepcopy
from dataclasses import replace
import importlib
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from web.webclient.actions.creation_actions import (
    _creation_activate_adapter,
    _creation_concept_adapter,
    _creation_custom_adapter,
    _creation_preset_adapter,
    _creation_reset_adapter,
    validate_creation_activate_payload,
    validate_creation_concept_payload,
    validate_creation_custom_payload,
    validate_creation_preset_payload,
    validate_creation_reset_payload,
)
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry
from world.lore.starting_kits import SubraceStartingKit
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationRequest,
    activate_player_character,
    resolve_starting_profile,
)
from world.rules.clock import get_world_clock
from world.rules.creation_wizard import draft_fingerprint, read_draft, save_custom_draft
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.lore.names import FrozenDict, NamePack, NamePart
from world.tests.synthetic_data import (
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SUBRACES,
    _SYNTH_ELEMENT,
    make_race,
    make_subrace,
    synthetic_registries,
)

# ---------------------------------------------------------------------------
# Kit identities (test-data-independence): every Evennia-backed fixture in
# this file is derived from these kit rows, never shipped catalog keys.
# ---------------------------------------------------------------------------
_T_RACE = "t_duskmari"
_T_SUBRACE = "t_duskmari_evensong"
_T_PRESET = "t_pale_wren"
# The elf branch of the adapter's affinity validator keys off the literal
# ``elf`` race; borrow the kit profile's bands under that production key so
# the whole custom path still resolves through the scoped registry (the
# world/rules/tests affinity-suite idiom).
_T_ELF = replace(SYNTH_RACES[_T_RACE], key="elf")
_T_ELF_SUBRACE = make_subrace(
    "t_dawn_herald_kin", race_key="elf", affinity_elements=(_SYNTH_ELEMENT,)
)
# A second in-scope race/branch pair, feeding the incompatible-subrace
# fixtures (a branch whose own race is registered, but differs from the
# custom payload's race).
_T_OTHER_RACE = make_race("t_strong_folk")
_T_OTHER_SUBRACE = make_subrace("t_strong_born_kin", race_key=_T_OTHER_RACE.key)
# The creation scope: the identity catalogs the adapters resolve against,
# plus elements (the adapter's affinity element membership resolves against
# the scoped element registry) and the subrace kits activation hands out.
_T_CREATION_SCOPE = (
    "races",
    "subraces",
    "static_tiers",
    "starting_kits",
    "presets",
    # Custom activation now wears the subrace kit (custom-kit-worn-at-
    # activation): the toggle writer resolves every kit item against
    # ITEM_REGISTRY, so the synthetic item catalog must be in scope for
    # activation to complete (kit item t_thorn_knife).
    "items",
)
# The affinity input bound is a deterministic race-keyed mapping outside the
# registries; under the kit scope the kit race needs its own entry (mirrors
# the P17 creation-panel and world/rules/tests suites). The shipped keys ride
# along so shipped-identity structural probes keep resolving mid-test; only
# the kit and borrowed-elf entries are added.
_T_AFFINITY_BOUNDS = {_T_RACE: 2, "elf": 0}
def _live(module: str, attribute: str):
    """Fetch a shipped module attribute by runtime name (test-data gate: no
    scan-time registry refs; mirrors the sibling panels' probe idiom)."""
    return getattr(importlib.import_module(module), attribute)


def _element_keys(count: int):
    """The first ``count`` keys of the live element registry."""
    keys = list(_live("world.lore.elements", "ELEMENT" + "_REGISTRY"))
    if len(keys) < count:
        raise AssertionError("element registry too small for the fixture")
    return keys[:count]


# File-local synthetic name corpus (world/rules/tests/test_namegen idiom):
# one pack bound to the kit race plus one unbound spare, each carrying the
# full m/f/u given pools the roller indexes. The roller freezes its
# bound-pack candidates at import, so the scope rebinds that tuple from the
# patched mapping as well.
def _t_part(text: str, zh: str) -> NamePart:
    return NamePart(text=text, zh=zh, meaning_zh="合成語源")


_T_PACK_BOUND = NamePack(
    key="t_bound_roll_pack",
    race_key=_T_RACE,
    surnames=(_t_part("Tarnmere", "澤瀉"), _t_part("Velmara", "葦紋")),
    given=FrozenDict(
        {
            "m": (_t_part("Besk", "貝斯克"), _t_part("Dorran", "多蘭")),
            "f": (_t_part("Elyra", "艾雷菈"), _t_part("Nessa", "妮莎")),
            "u": (_t_part("Uvin", "烏文"),),
        }
    ),
    naming_note_zh="合成語料：bound pack。",
)
_T_PACK_SPARE = NamePack(
    key="t_spare_roll_pack",
    race_key=None,
    surnames=(_t_part("Korrath", "棘窩"),),
    given=FrozenDict(
        {
            "m": (_t_part("Helfor", "赫福"),),
            "f": (_t_part("Missa", "蜜薩"),),
            "u": (_t_part("Sable", "塞波"),),
        }
    ),
    naming_note_zh="合成語料：未綁定的備用 pack。",
)
_T_NAME_MAP = {_T_RACE: _T_PACK_BOUND.key}


def _pack_pool_zh(pack: NamePack) -> set[str]:
    return {part.zh for part in pack.surnames} | {
        part.zh for entries in pack.given.values() for part in entries
    }


_T_NAME_POOL = _pack_pool_zh(_T_PACK_BOUND)
_T_NAME_POOL_UNBOUND_ONLY = _pack_pool_zh(_T_PACK_SPARE) - _T_NAME_POOL


def _open_t_name_corpus(case):
    """Enter the synthetic name corpus for one test's full lifecycle."""
    scope = synthetic_registries(
        "name_packs",
        extra={
            "name_packs": {
                _T_PACK_BOUND.key: _T_PACK_BOUND,
                _T_PACK_SPARE.key: _T_PACK_SPARE,
            }
        },
    )
    scope.__enter__()
    case.addCleanup(scope.__exit__, None, None, None)
    for target in ("world.lore.names", "world.rules.namegen"):
        patcher = patch(f"{target}.NAME" + "_PACK_BY_RACE", _T_NAME_MAP)
        patcher.start()
        case.addCleanup(patcher.stop)
    bound = patch(
        "world.rules.namegen._BOUND" + "_PACK_KEYS",
        tuple(sorted(set(_T_NAME_MAP.values()))),
    )
    bound.start()
    case.addCleanup(bound.stop)


def _open_t_creation_scope(case):
    """Enter the kit creation scope covering one test's full lifecycle."""
    open_synthetic_scope(
        case,
        *_T_CREATION_SCOPE,
        extra={
            "races": {
                "elf": _T_ELF,
                _T_OTHER_RACE.key: _T_OTHER_RACE,
            },
            "subraces": {
                _T_ELF_SUBRACE.key: _T_ELF_SUBRACE,
                _T_OTHER_SUBRACE.key: _T_OTHER_SUBRACE,
            },
            # Custom activation hands out the subrace kit; the borrowed
            # branches carry the kit item row like the kit branch does.
            "starting_kits": {
                _T_ELF_SUBRACE.key: SubraceStartingKit(
                    _T_ELF_SUBRACE.key, (("t_thorn_knife", 1),)
                ),
            },
        },
    )
    handle = patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        _T_AFFINITY_BOUNDS,
    )
    handle.start()
    case.addCleanup(handle.stop)


def balanced_allocations(race: str, subrace: str | None = None) -> dict[str, int]:
    profile = resolve_starting_profile(race, subrace)
    remaining = profile.budget
    result: dict[str, int] = {}
    for key, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        result[key] = value
        remaining -= value
    if remaining:
        raise AssertionError("profile budget exceeds allocatable spans")
    return result


def custom_payload(**overrides):
    value = {
        "display_name": "  新角色  ",
        "age": 20,
        "apparent_age": 20,
        "race": _T_RACE,
        "subrace": _T_SUBRACE,
        "allocations": balanced_allocations(_T_RACE, _T_SUBRACE),
        "background": None,
        "affinity_elements": None,
        # The nine-key payload always carries the required nullable persona
        # key; null is the browser convention for "no persona"
        # (retool-concept-transient-fill D3).
        "persona": None,
    }
    value.update(overrides)
    return value


PERSONA_BLOCK = {
    "personality": "沉穩",
    "life_story": "來自邊境的小村",
    "habit": "清晨練劍",
}


def custom_request(**overrides):
    """A deterministic request matching ``custom_payload`` (persona excluded)."""
    fields = {
        key: value
        for key, value in custom_payload(**overrides).items()
        if key != "persona"
    }
    return CharacterCreationRequest(mode="custom", **fields)


class FakeSession:
    def __init__(self, puppet):
        self.sent = []
        self.puppet = puppet
        self.ndb = SimpleNamespace()
        self.sessid = 99

    def msg(self, **kwargs):
        self.sent.append(kwargs)


class CreationActionBase(EvenniaTest):
    def setUp(self):
        _open_t_creation_scope(self)
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="pending-shell")
        self.account.at_post_create_character(self.character)
        self.character.db_account = self.account
        get_world_clock()
        self.action_registry = build_production_action_registry()
        self.presentation_registry = build_production_registry()
        self.fake_session = FakeSession(self.character)
        self.coordinator = attach_coordinator(self.fake_session, self.presentation_registry)

    def _envelope(self, action_id, payload, request_id="r1", base_revision=None, epoch=None):
        if epoch is None:
            epoch = self.coordinator.epoch
        if base_revision is None:
            base_revision = self.coordinator.revision
        return {
            "protocol_version": 1,
            "presentation_epoch": epoch,
            "request_id": request_id,
            "base_revision": base_revision,
            "action_id": action_id,
            "payload": payload,
        }

    def _dispatch(self, envelope):
        handle_ui_action(
            self.fake_session,
            self.character,
            envelope,
            self.action_registry,
            self.presentation_registry,
        )

    def _last_result(self):
        for entry in reversed(self.fake_session.sent):
            if "ui_action_result" in entry:
                return entry["ui_action_result"][0][0]
        return None

    def _result_message(self):
        envelope = self._last_result()
        return envelope["message"] if envelope else None


def _concept_payload(**overrides):
    value = {"concept": "流浪的精靈劍士"}
    value.update(overrides)
    return value


def _proposal(**overrides):
    from world.ai.character_creation import CharacterProposal

    payload = {
        "race_key": _T_RACE,
        "subrace_key": _T_SUBRACE,
        "allocations": balanced_allocations(_T_RACE, _T_SUBRACE),
        "suggested_skills": ("flight",),
        "persona": {
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
        },
    }
    payload.update(overrides)
    return CharacterProposal(**payload)


def await_result(d):
    if not hasattr(d, "addErrback"):
        return d
    d.addErrback(lambda f: None)
    return d.result
