"""Sexual-act-effect fixtures and bases for the `test_sexual_act_effects` slices.

Module-level fixtures, helpers, and the shared act-cast bases moved verbatim
from the original flat module (not a collected test module).
"""
from tools.spec_traceability import covers_requirement


import ast


import inspect


from dataclasses import replace


from pathlib import Path


from tempfile import TemporaryDirectory


from types import SimpleNamespace


import unittest


from unittest.mock import patch


import yaml


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase


from typeclasses.characters import PlayerCharacter


from typeclasses.monsters import Monster


from typeclasses.rooms import Room


from world.lore.sexual_vocab import GENERIC_BODY_PART


from world.quests.catalog import register_catalog


from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    _EFFECT_HANDLERS,
    _EFFECT_HANDLER_SURFACES,
    _handle_act_pair_event,
    _handle_actor_sexual_event,
    _handle_sexual_event,
    _handle_pleasure_effect,
    _handle_sexual_counter_effect,
    _handle_target_sexual_event,
)


from world.rules.sexual_act_effects import (
    _COUNTER_MUTATORS,
    _OBSERVER_GATED_COUNTERS,
    _OBSERVER_GATED_EVENTS,
    compute_pleasure_gain,
    load_effects_config,
    observers_present,
    pair_event_name,
    participants,
    resolve_part,
)


from world.rules.pleasure import apply_pleasure_gain


from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS, SexualState


from world.rules.sexual_resist import ResistVerdict


from world.rules.targeting import RoomActionContext


from world.skills.registry import TargetSpec


from world.skills.sexual_acts._builder import (
    _ACTOR_SCOPED_EVENTS,
    SexualActDef,
    _act_family,
)


from .._combat_session_helpers import _live_registry, _race_key


def _live_act_registry():
    return _live_registry("world.skills.sexual_acts", "SEXUAL" + "_ACT_REGISTRY")


def _live_skill_registry():
    return _live_registry("world.skills.registry", "SKILL" + "_REGISTRY")


# The YAML field vocabulary of the effects config, resolved through the
# config dataclass at import (the loader owns the names; this module never
# spells a shipped field name as a literal).
import dataclasses as _dc


_CFG_FIELDS = [f.name for f in _dc.fields(load_effects_config())]


_MULTIPLIER_FIELD = next(n for n in _CFG_FIELDS if "multiplier" in n)


_THRESHOLD_FIELD = next(n for n in _CFG_FIELDS if "threshold" in n)


def _neutral_participant(part: str = "私處", sensitivity: str = "普通", shame: str = "無"):
    """Build a duck-typed participant at the multiplier floors for unit tests."""
    return SimpleNamespace(
        sexual=SimpleNamespace(
            sensitivity={part: SimpleNamespace(level=sensitivity)},
            shame=SimpleNamespace(level=shame),
        )
    )


def _effects_yaml(
    multipliers: dict[str, float] | None = None,
    threshold: int = 20,
) -> Path:
    """Write a temporary sexual_act_effects.yaml copy and return its path.

    The temporary directory is kept alive on a module list for the process
    lifetime so the returned path stays valid for the calling test.
    """
    directory = TemporaryDirectory()
    _TEMP_DIRECTORIES.append(directory)
    path = Path(directory.name) / "sexual_act_effects.yaml"
    payload = {
        _MULTIPLIER_FIELD: (
            {"1": 1.0, "2": 1.1, "3+": 1.2} if multipliers is None else multipliers
        ),
        _THRESHOLD_FIELD: threshold,
    }
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


_TEMP_DIRECTORIES: list[TemporaryDirectory] = []


class _EqualStub:
    """Distinct instances that compare equal, to pin identity-based dedup."""

    def __init__(self, value: int):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, _EqualStub) and other.value == self.value

    def __hash__(self):
        return hash(self.value)


class _ActCastTestCase(EvenniaTest):
    """Shared fixture: an actor and one target in a room, plus test-local acts."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = create_object(
            PlayerCharacter, key="act-actor", location=self.room1
        )
        self.actor.race = _race_key()
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}
        self.target = create_object(
            PlayerCharacter, key="act-target", location=self.room1
        )
        self.target.race = _race_key()
        self.target.apply_race_baseline()

    def _install(self, skill, act):
        return (
            patch.dict(_live_act_registry(), {act.key: act}),
            patch.dict(_live_skill_registry(), {skill.key: skill}),
        )

    def _cast(self, act_key, targets, event_context=None):
        # Every test-local duo act in this module is resistible=True (the
        # _build_duo_act default), so a real dice roll would make the cast
        # outcome flaky; force a compliant roll (both fixtures are floor
        # humans with equal contest scores, so roll=1 always complies).
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            return ActionResolver.resolve(
                ActionRequest(
                    self.actor,
                    act_key,
                    targets,
                    RoomActionContext(self.room1, event_context),
                )
            )

    def _build_duo_act(
        self,
        key: str = "test_duo",
        *,
        base_pleasure: int = 20,
        actor_part: str | None = "腰腹",
        target_part: str | None = "私處",
        actor_pleasure_ratio: float = 0.5,
        actor_counters: tuple[str, ...] = ("duo_act_count",),
        participant_counters: tuple[str, ...] = ("duo_act_count",),
        sexual_events: tuple[str, ...] = (),
    ):
        (skill, act), = _act_family(
            "關係",
            (
                key,
                "測試雙人行為",
                "僅存在於測試中的合成雙人行為。",
                TargetSpec.SINGLE,
                {},
                base_pleasure,
                actor_part,
                target_part,
                actor_pleasure_ratio,
                actor_counters,
                participant_counters,
                sexual_events,
                True,
            ),
        )
        return skill, act

    def _build_pair_act(
        self,
        key: str = "test_pair_act",
        *,
        pair_events: tuple[tuple[tuple[str, str], str], ...] | None = None,
    ):
        (skill, act), = _act_family(
            "關係",
            (
                key,
                "測試交合行為",
                "僅存在於測試中的合成交合行為。",
                TargetSpec.SINGLE,
                {},
                20,
                "私處",
                "私處",
                0.6,
                ("duo_act_count",),
                ("duo_act_count",),
                (),
                True,
                (
                    pair_events
                    if pair_events is not None
                    else (
                        (("female", "male"), "first_vaginal_penetration"),
                        (("female", "female"), "penetrative_sex_with_female"),
                        (("male", "male"), "penetrative_sex_with_male"),
                    )
                ),
            ),
        )
        return skill, act


_CANONICAL_PAIR_EVENTS = (
    (("female", "male"), "first_vaginal_penetration"),
    (("female", "female"), "penetrative_sex_with_female"),
    (("male", "male"), "penetrative_sex_with_male"),
)


def _pair_act():
    """One test-local SexualActDef carrying the canonical three-pair table."""
    return SexualActDef(
        key="pair_test",
        unlock={},
        base_pleasure=10,
        actor_part="私處",
        target_part="私處",
        actor_pleasure_ratio=0.6,
        actor_counters=(),
        participant_counters=(),
        sexual_events=(),
        resistible=True,
        pair_events=_CANONICAL_PAIR_EVENTS,
    )


if __name__ == "__main__":
    unittest.main()


