"""Presenter tests for the exact ``combat_beats`` panel (design D3/D7/D8/D10).

A hand-built :class:`~world.rules.combat_beats.RoundRecord` drives the pure
presenter and validator cases; the disclosure case drives the real combat view
against a disguised foe.
"""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from web.webclient.presentation.combat_beats import (
    COMBAT_BEATS_MAX_BYTES,
    COMBAT_BEATS_SCHEMA_VERSION,
    combat_beats_presenter,
    validate_combat_beats,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import UNAVAILABLE_REASON, build_production_registry
from world.rules.action import stored_gauge_pair
from world.rules.combat_beats import (
    MAX_BEATS,
    MAX_BEAT_TEXT,
    MAX_ROUND_ID,
    RoundRecord,
)
from world.rules.combat_session import engage
from world.rules.combat_view import build_combat_view
from world.rules.event_log import EventEntry, EventLog
from world.rules.tests.combat_fixtures import BattlefieldIsolation

REPO_ROOT = Path(__file__).resolve().parents[4]

_HERO = "hero"
_GOBLIN = "goblin"
_HERO_DBREF = 101
_GOBLIN_DBREF = 202
_IDENTITIES = {_HERO: _HERO_DBREF, _GOBLIN: _GOBLIN_DBREF}
_SESSION_ID = "hostile:7:42"

_ROLL_TEMPLATE = "{actor} 對 {target} 的攻擊擲出了 {data[raw_roll]}。"
_DAMAGE_TEMPLATE = "{actor} 對 {target} 造成了 {data[amount]} 點傷害。"


def _entry(kind, *, actor=_HERO, target=None, data=None, template="{actor} 行動。"):
    return EventEntry(kind, actor, target, {} if data is None else data, template)


def _round_logs(entries=None):
    if entries is None:
        entries = [
            _entry(
                "roll",
                target=_GOBLIN,
                data={"raw_roll": 42, "hit": True},
                template=_ROLL_TEMPLATE,
            ),
            _entry(
                "damage",
                target=_GOBLIN,
                data={"amount": 12},
                template=_DAMAGE_TEMPLATE,
            ),
        ]
    return (EventLog(_HERO, "t_strike", (_GOBLIN,), tuple(entries), 6),)


def _record(
    *,
    logs=None,
    identities=None,
    hp_before=None,
    hp_after=None,
    session_id=_SESSION_ID,
    number=1,
):
    return RoundRecord(
        session_id=session_id,
        number=number,
        logs=_round_logs() if logs is None else tuple(logs),
        identities=_IDENTITIES if identities is None else identities,
        hp_before={_HERO_DBREF: 100, _GOBLIN_DBREF: 30} if hp_before is None else hp_before,
        hp_after={_HERO_DBREF: 100, _GOBLIN_DBREF: 18} if hp_after is None else hp_after,
    )


def _context(record, actor=None):
    return PresentationContext(
        actor=SimpleNamespace(pk=1) if actor is None else actor,
        protocol_version=1,
        combat_round=record,
    )


class CombatBeatsPanelTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="beats arena")
        self.player = create_object(PlayerCharacter, key="beats player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.monster = create_object(Monster, key="beats goblin")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")
        self.monster.traits.hp.base = 100
        self.monster.traits.hp.current = 100
        self.monster.location = self.room
        self.registry = build_production_registry()

    def _render(self, record):
        return self.registry.render("combat_beats", _context(record, actor=self.player))

    def test_a_settled_round_renders_the_exact_available_form(self):
        payload = combat_beats_presenter(_context(_record()))
        self.assertEqual(
            set(payload), {"schema_version", "available", "round", "beats"}
        )
        self.assertEqual(payload["schema_version"], COMBAT_BEATS_SCHEMA_VERSION)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["round"], f"{_SESSION_ID}/1")
        self.assertEqual(len(payload["beats"]), 2)
        for beat in payload["beats"]:
            self.assertEqual(
                set(beat),
                {"seq", "action", "kind", "actor", "target", "amount", "hp_after", "text"},
            )
        self.assertEqual(
            payload["beats"][0],
            {
                "seq": 0,
                "action": 0,
                "kind": "roll",
                "actor": str(_HERO_DBREF),
                "target": str(_GOBLIN_DBREF),
                "amount": None,
                "hp_after": None,
                "text": "hero 對 goblin 的攻擊擲出了 42。",
            },
        )
        self.assertEqual(
            payload["beats"][1],
            {
                "seq": 1,
                "action": 0,
                "kind": "damage",
                "actor": str(_HERO_DBREF),
                "target": str(_GOBLIN_DBREF),
                "amount": 12,
                "hp_after": 18,
                "text": "hero 對 goblin 造成了 12 點傷害。",
            },
        )
        # The validator accepts exactly the form the presenter emits.
        self.assertEqual(validate_combat_beats(payload), payload)
        # And the registered panel returns it unchanged.
        self.assertEqual(self._render(_record()), payload)

    def test_no_record_renders_the_common_unavailable_form(self):
        payload = self.registry.render(
            "combat_beats",
            PresentationContext(actor=self.player, protocol_version=1),
        )
        self.assertEqual(set(payload), {"schema_version", "available", "reason"})
        self.assertEqual(payload["schema_version"], COMBAT_BEATS_SCHEMA_VERSION)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], UNAVAILABLE_REASON[0])
        self.assertEqual(payload["reason"]["message"], UNAVAILABLE_REASON[1])
        self.assertNotIn("correlation_id", payload["reason"])
        self.assertNotIn("beats", payload)

    def test_an_hp_mismatch_renders_unavailable_and_logs_a_bounded_reason(self):
        record = _record(hp_after={_HERO_DBREF: 100, _GOBLIN_DBREF: 30})
        with patch(
            "web.webclient.presentation.combat_beats.log_warn"
        ) as warn:
            payload = self._render(record)
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], UNAVAILABLE_REASON[0])
        warn.assert_called_once()
        self.assertEqual(warn.call_args.args[0], "combat_beats_unavailable")
        context = warn.call_args.kwargs["context"]
        self.assertEqual(context["reason"], "hp_mismatch")
        self.assertEqual(context["char"], str(self.player.pk))

    def test_each_bound_renders_unavailable_never_truncated(self):
        cases = {
            "too many beats": _record(
                logs=_round_logs(
                    [_entry("resource_spend", template="")]
                    * (MAX_BEATS + 1)
                )
            ),
            "text too long": _record(
                logs=_round_logs(
                    [_entry("resource_spend", template="字" * (MAX_BEAT_TEXT + 1))]
                )
            ),
            "round id too long": _record(session_id="s" * (MAX_ROUND_ID + 1)),
            "byte budget": _record(
                logs=_round_logs(
                    [
                        _entry("resource_spend", template="字" * MAX_BEAT_TEXT)
                        for _ in range(MAX_BEATS)
                    ]
                )
            ),
        }
        for name, record in cases.items():
            with self.subTest(name):
                payload = self._render(record)
                self.assertFalse(payload["available"])
                self.assertEqual(payload["reason"]["code"], UNAVAILABLE_REASON[0])
                self.assertNotIn("beats", payload)

    def test_the_byte_budget_rejects_an_over_budget_payload(self):
        payload = {
            "schema_version": COMBAT_BEATS_SCHEMA_VERSION,
            "available": True,
            "round": f"{_SESSION_ID}/1",
            "beats": [
                {
                    "seq": seq,
                    "action": 0,
                    "kind": "other",
                    "actor": None,
                    "target": None,
                    "amount": None,
                    "hp_after": None,
                    "text": "字" * MAX_BEAT_TEXT,
                }
                for seq in range(MAX_BEATS)
            ],
        }
        self.assertGreater(json_byte_size(payload), COMBAT_BEATS_MAX_BYTES)
        with self.assertRaises(ProtocolValidationError):
            validate_combat_beats(payload)
        # One beat fewer still fits: the bound is the only rejection.
        payload["beats"] = payload["beats"][:1]
        self.assertLess(json_byte_size(payload), COMBAT_BEATS_MAX_BYTES)
        self.assertTrue(validate_combat_beats(payload)["available"])

    def test_the_validator_rejects_out_of_schema_beats(self):
        valid = combat_beats_presenter(_context(_record()))
        cases = {}

        def mutate(name, change):
            payload = json.loads(json.dumps(valid))
            change(payload)
            cases[name] = payload

        mutate("unknown kind", lambda p: p["beats"][0].update(kind="skill"))
        mutate("extra beat field", lambda p: p["beats"][0].update(extra=1))
        mutate("missing beat field", lambda p: p["beats"][0].pop("text"))
        mutate("extra panel field", lambda p: p.update(extra=1))
        mutate("non-contiguous seq", lambda p: p["beats"][1].update(seq=5))
        mutate("decreasing action", lambda p: p["beats"][0].update(action=1))
        mutate("damage with null hp_after", lambda p: p["beats"][1].update(hp_after=None))
        mutate("damage with null target", lambda p: p["beats"][1].update(target=None))
        mutate("damage with negative amount", lambda p: p["beats"][1].update(amount=-1))
        mutate("non-damage with amount", lambda p: p["beats"][0].update(amount=3))
        mutate("non-damage with hp_after", lambda p: p["beats"][0].update(hp_after=3))
        mutate("non-decimal identity", lambda p: p["beats"][0].update(actor="hero"))
        mutate("over-long identity", lambda p: p["beats"][0].update(actor="1" * 33))
        mutate("empty round", lambda p: p.update(round=" "))
        mutate("over-long round", lambda p: p.update(round="s" * (MAX_ROUND_ID + 1)))
        mutate("too many beats", lambda p: p.update(beats=[p["beats"][0]] * (MAX_BEATS + 1)))
        mutate("unavailable discriminator", lambda p: p.update(available=False))
        mutate(
            "unsupported schema version",
            lambda p: p.update(schema_version=COMBAT_BEATS_SCHEMA_VERSION + 1),
        )
        for name, payload in cases.items():
            with self.subTest(name):
                with self.assertRaises(ProtocolValidationError):
                    validate_combat_beats(payload)

    def test_rendering_leaves_traits_and_the_combat_record_unchanged(self):
        engage(self.player, self.monster)
        before = {
            "hp": int(self.player.traits.hp.current),
            "mp": int(self.player.traits.mp.current),
            "combat": deepcopy(self.player.db.active_combat),
        }
        player_hp = stored_gauge_pair(self.player, "hp")[0]
        monster_hp = stored_gauge_pair(self.monster, "hp")[0]
        record = _record(
            hp_before={_HERO_DBREF: player_hp, _GOBLIN_DBREF: monster_hp + 12},
            hp_after={_HERO_DBREF: player_hp, _GOBLIN_DBREF: monster_hp},
        )
        payload = combat_beats_presenter(_context(record, actor=self.player))
        self.assertTrue(payload["available"])
        self.assertEqual(int(self.player.traits.hp.current), before["hp"])
        self.assertEqual(int(self.player.traits.mp.current), before["mp"])
        self.assertEqual(self.player.db.active_combat, before["combat"])
        self.assertEqual(
            stored_gauge_pair(self.monster, "hp")[0],
            record.hp_after[_GOBLIN_DBREF],
        )

    def test_the_beats_modules_never_read_the_disguise_layer(self):
        for relative in (
            "world/rules/combat_beats.py",
            "web/webclient/presentation/combat_beats.py",
        ):
            with self.subTest(relative):
                source = (REPO_ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn("get_display_value", source)
                self.assertNotIn("disguised_stats", source)

    def test_a_disguised_foe_ships_true_hp_matching_the_combat_view(self):
        engage(self.player, self.monster)
        true_hp = stored_gauge_pair(self.monster, "hp")[0]
        disguised_hp = true_hp + 1
        self.monster.db.disguised_stats = {"hp": disguised_hp}
        view = build_combat_view(self.player)
        foe = next(
            participant
            for participant in view.participants
            if participant.identity == int(self.monster.pk)
        )
        record = _record(
            hp_before={_GOBLIN_DBREF: foe.hp_current + 12},
            hp_after={_GOBLIN_DBREF: foe.hp_current},
        )
        payload = combat_beats_presenter(_context(record, actor=self.player))
        self.assertTrue(payload["available"])
        damage = payload["beats"][1]
        self.assertEqual(damage["kind"], "damage")
        self.assertEqual(damage["hp_after"], foe.hp_current)
        self.assertEqual(damage["hp_after"], true_hp)
        self.assertNotEqual(damage["hp_after"], disguised_hp)
        self.assertNotIn("disguise", repr(payload))


if __name__ == "__main__":
    unittest.main()
