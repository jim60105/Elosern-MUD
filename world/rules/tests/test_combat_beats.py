"""Pure builder tests for the structured combat beats (design D1/D5-D9).

Hand-built ``EventLog``s with synthetic keys and no database: the builder reads
only the frozen :class:`~world.rules.combat_beats.RoundRecord`, so every case
is deterministic and free of the round transaction.
"""

from dataclasses import asdict
import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.ansi import strip_ansi

from world.rules.combat_beats import (
    BEAT_KINDS,
    MAX_BEATS,
    MAX_BEAT_TEXT,
    MAX_ROUND_ID,
    CombatBeatsError,
    RoundRecord,
    build_combat_beats,
)
from world.rules.event_log import EventEntry, EventLog, render_plain_text


_HERO = "hero"
_GOBLIN = "goblin"
_COMPANION = "companion"
_GHOST = "ghost"
_HERO_DBREF = 101
_GOBLIN_DBREF = 202
_COMPANION_DBREF = 303

_IDENTITIES = {
    _HERO: _HERO_DBREF,
    _GOBLIN: _GOBLIN_DBREF,
    _COMPANION: _COMPANION_DBREF,
}


def _entry(kind, *, actor=_HERO, target=None, data=None, template="{actor} 行動。"):
    return EventEntry(kind, actor, target, {} if data is None else data, template)


def _log(entries, *, actor=_HERO, key="t_strike"):
    return EventLog(actor, key, (), tuple(entries), 6)


def _record(
    logs,
    *,
    hp_before=None,
    hp_after=None,
    identities=None,
    session_id="hostile:42:1200",
    number=1,
):
    return RoundRecord(
        session_id=session_id,
        number=number,
        logs=tuple(logs),
        identities=_IDENTITIES if identities is None else identities,
        hp_before={_GOBLIN_DBREF: 30} if hp_before is None else hp_before,
        hp_after={_GOBLIN_DBREF: 30} if hp_after is None else hp_after,
    )


class CombatBeatsBuilderTests(unittest.TestCase):
    @covers_requirement("webclient-combat-beats::combat-beats-derive-only-from-the-settled-round-s-event-records")
    def test_entry_kinds_map_to_the_closed_set_in_order(self):
        # The spec scenario: a resource_spend, a roll, a damage, a
        # target_defeated, and a target_knocked_out entry, with each beat
        # carrying its source log's 0-based ordinal as ``action``.
        logs = (
            _log(
                [
                    _entry("resource_spend", template="{actor} 消耗了資源。"),
                    _entry(
                        "roll",
                        target=_GOBLIN,
                        data={"raw_roll": 42, "hit": True},
                        template="{actor} 對 {target} 的攻擊擲出了 {data[raw_roll]}。",
                    ),
                    _entry(
                        "damage",
                        target=_GOBLIN,
                        data={"amount": 12},
                        template="{actor} 對 {target} 造成了 {data[amount]} 點傷害。",
                    ),
                ]
            ),
            _log(
                [
                    _entry(
                        "target_defeated",
                        target=_GOBLIN,
                        template="{actor} 擊敗了 {target}。",
                    ),
                    _entry(
                        "target_knocked_out",
                        target=_COMPANION,
                        template="{actor} 擊倒了 {target}。",
                    ),
                ]
            ),
        )
        view = build_combat_beats(
            _record(
                logs,
                hp_before={_GOBLIN_DBREF: 30, _COMPANION_DBREF: 10},
                hp_after={_GOBLIN_DBREF: 18, _COMPANION_DBREF: 10},
            )
        )
        self.assertEqual(view.round, "hostile:42:1200/1")
        self.assertEqual(
            [beat.kind for beat in view.beats],
            ["other", "roll", "damage", "target_defeated", "other"],
        )
        self.assertEqual([beat.seq for beat in view.beats], [0, 1, 2, 3, 4])
        self.assertEqual([beat.action for beat in view.beats], [0, 0, 0, 1, 1])

    @covers_requirement("webclient-combat-beats::combat-beats-derive-only-from-the-settled-round-s-event-records")
    def test_an_unknown_kind_maps_to_other_and_keeps_its_actor(self):
        view = build_combat_beats(
            _record([_log([_entry("action_skipped", template="{actor} 無法行動。")])])
        )
        self.assertEqual(view.beats[0].kind, "other")
        self.assertEqual(view.beats[0].actor, str(_HERO_DBREF))
        self.assertEqual(view.beats[0].text, "hero 無法行動。")

    @covers_requirement("webclient-combat-beats::combat-beats-derive-only-from-the-settled-round-s-event-records")
    def test_beat_identities_match_the_portrait_catalog(self):
        view = build_combat_beats(
            _record(
                [
                    _log(
                        [
                            _entry(
                                "trait_delta",
                                actor=_HERO,
                                target=_GHOST,
                                template="{target} 的能力值發生了變化。",
                            )
                        ]
                    )
                ]
            )
        )
        self.assertEqual(view.beats[0].actor, str(_HERO_DBREF))
        # A name outside the roster is not a participant: null, never a guess.
        self.assertIsNone(view.beats[0].target)

    @covers_requirement("webclient-combat-beats::combat-beats-derive-only-from-the-settled-round-s-event-records")
    def test_amount_and_hp_after_are_set_on_damage_beats_only(self):
        view = build_combat_beats(
            _record(
                [
                    _log(
                        [
                            _entry("roll", target=_GOBLIN, data={"raw_roll": 9, "hit": True}),
                            _entry(
                                "damage",
                                target=_GOBLIN,
                                data={"amount": 5},
                                template="{target} 受到了 {data[amount]} 點傷害。",
                            ),
                        ]
                    )
                ],
                hp_after={_GOBLIN_DBREF: 25},
            )
        )
        roll, damage = view.beats
        self.assertIsNone(roll.amount)
        self.assertIsNone(roll.hp_after)
        self.assertEqual(damage.amount, 5)
        self.assertEqual(damage.hp_after, 25)
        self.assertEqual(damage.target, str(_GOBLIN_DBREF))

    @covers_requirement("webclient-combat-beats::beat-hp-is-projected-on-the-server-and-checked-against-the-round-s-recorded-hp")
    def test_ordered_damage_projects_hp_after(self):
        view = build_combat_beats(
            _record(
                [
                    _log(
                        [
                            _entry(
                                "damage",
                                target=_GOBLIN,
                                data={"amount": 12},
                                template="{target} 受到了 {data[amount]} 點傷害。",
                            )
                        ]
                    ),
                    _log(
                        [
                            _entry(
                                "damage",
                                target=_GOBLIN,
                                data={"amount": 25},
                                template="{target} 受到了 {data[amount]} 點傷害。",
                            )
                        ]
                    ),
                ],
                hp_after={_GOBLIN_DBREF: 0},
            )
        )
        self.assertEqual([beat.hp_after for beat in view.beats], [18, 0])

    @covers_requirement("webclient-combat-beats::beat-hp-is-projected-on-the-server-and-checked-against-the-round-s-recorded-hp")
    def test_a_knockout_floors_the_projection_at_one(self):
        view = build_combat_beats(
            _record(
                [
                    _log(
                        [
                            _entry(
                                "damage",
                                target=_COMPANION,
                                data={"amount": 15},
                                template="{target} 受到了 {data[amount]} 點傷害。",
                            ),
                            _entry(
                                "target_knocked_out",
                                target=_COMPANION,
                                template="{actor} 擊倒了 {target}。",
                            ),
                        ]
                    )
                ],
                hp_before={_COMPANION_DBREF: 10},
                hp_after={_COMPANION_DBREF: 1},
            )
        )
        self.assertEqual(view.beats[0].hp_after, 1)
        self.assertEqual(view.beats[1].kind, "other")

    @covers_requirement("webclient-combat-beats::beat-hp-is-projected-on-the-server-and-checked-against-the-round-s-recorded-hp")
    def test_an_hp_change_without_a_damage_entry_raises(self):
        # A damaged target that is also healed (or regenerated, drained,
        # diverted, or ticked silently) has no damage entry for the extra HP
        # move: the projection disagrees with the recorded end-of-round HP.
        with self.assertRaises(CombatBeatsError) as raised:
            build_combat_beats(
                _record(
                    [
                        _log(
                            [
                                _entry(
                                    "damage",
                                    target=_GOBLIN,
                                    data={"amount": 5},
                                    template="{target} 受到了 {data[amount]} 點傷害。",
                                ),
                                _entry(
                                    "heal",
                                    target=_GOBLIN,
                                    data={"amount": 5},
                                    template="{target} 恢復了 {data[amount]} 點生命。",
                                ),
                            ]
                        )
                    ],
                    hp_after={_GOBLIN_DBREF: 30},
                )
            )
        self.assertEqual(raised.exception.args[0], "hp_mismatch")

    @covers_requirement("webclient-combat-beats::beat-hp-is-projected-on-the-server-and-checked-against-the-round-s-recorded-hp")
    def test_an_unknown_damage_target_raises(self):
        with self.assertRaises(CombatBeatsError) as raised:
            build_combat_beats(
                _record(
                    [
                        _log(
                            [
                                _entry(
                                    "damage",
                                    target=_GHOST,
                                    data={"amount": 5},
                                    template="{target} 受到了 {data[amount]} 點傷害。",
                                )
                            ]
                        )
                    ]
                )
            )
        self.assertEqual(raised.exception.args[0], "unknown_damage_target")

    @covers_requirement("webclient-combat-beats::combat-beats-derive-only-from-the-settled-round-s-event-records")
    def test_a_damage_entry_without_an_integer_amount_raises(self):
        with self.assertRaises(CombatBeatsError) as raised:
            build_combat_beats(
                _record(
                    [
                        _log(
                            [
                                _entry(
                                    "damage",
                                    target=_GOBLIN,
                                    template="{target} 受到了傷害。",
                                )
                            ]
                        )
                    ]
                )
            )
        self.assertEqual(raised.exception.args[0], "damage_amount_invalid")

    @covers_requirement("webclient-combat-beats::the-combat-beats-panel-is-an-exact-read-only-panel")
    def test_over_bound_input_raises(self):
        with self.subTest("too many beats"):
            with self.assertRaises(CombatBeatsError) as raised:
                build_combat_beats(
                    _record(
                        [
                            _log(
                                [_entry("resource_spend", template="")]
                                * (MAX_BEATS + 1)
                            )
                        ]
                    )
                )
            self.assertEqual(raised.exception.args[0], "too_many_beats")
        with self.subTest("text too long"):
            with self.assertRaises(CombatBeatsError) as raised:
                build_combat_beats(
                    _record([_log([_entry("resource_spend", template="字" * (MAX_BEAT_TEXT + 1))])])
                )
            self.assertEqual(raised.exception.args[0], "beat_text_too_long")
        with self.subTest("round id too long"):
            with self.assertRaises(CombatBeatsError) as raised:
                build_combat_beats(
                    _record(
                        [_log([_entry("resource_spend", template="")])],
                        session_id="s" * (MAX_ROUND_ID + 1),
                    )
                )
            self.assertEqual(raised.exception.args[0], "round_id_too_long")

    @covers_requirement("webclient-combat-beats::combat-beats-derive-only-from-the-settled-round-s-event-records")
    @covers_requirement("webclient-combat-beats::combat-beats-disclose-nothing-the-combat-panel-does-not")
    def test_a_beat_text_is_the_delivered_line_with_ansi_stripped(self):
        entries = (
            _entry(
                "roll",
                target=_GOBLIN,
                data={"raw_roll": 42, "hit": True},
                template="|r{actor}|n 對 |y{target}|n 的攻擊擲出了 {data[raw_roll]}。",
            ),
            _entry("combat_kill_xp", template=""),
            _entry(
                "damage",
                target=_GOBLIN,
                data={"amount": 12},
                template="{actor} 對 {target} 造成了 {data[amount]} 點傷害。",
            ),
        )
        log = _log(entries)
        view = build_combat_beats(
            _record([log], hp_after={_GOBLIN_DBREF: 18})
        )
        rendered = render_plain_text(log).split("\n")
        self.assertEqual(
            [beat.text for beat in view.beats],
            ["hero 對 goblin 的攻擊擲出了 42。", "", "hero 對 goblin 造成了 12 點傷害。"],
        )
        # One-to-one with the text channel's own lines, ANSI markup stripped.
        self.assertEqual(
            [beat.text for beat in view.beats],
            [strip_ansi(line) for line in rendered],
        )
        self.assertNotIn("|r", view.beats[0].text)

    @covers_requirement("webclient-combat-beats::the-combat-beats-panel-is-an-exact-read-only-panel")
    @covers_requirement("webclient-combat-beats::combat-beats-disclose-nothing-the-combat-panel-does-not")
    def test_no_beat_exposes_raw_roll_hit_or_other_entry_data(self):
        view = build_combat_beats(
            _record(
                [
                    _log(
                        [
                            _entry(
                                "roll",
                                target=_GOBLIN,
                                data={"raw_roll": 42, "hit": True},
                            ),
                            _entry(
                                "damage",
                                target=_GOBLIN,
                                data={"amount": 12},
                                template="{target} 受到了 {data[amount]} 點傷害。",
                            ),
                        ]
                    )
                ],
                hp_after={_GOBLIN_DBREF: 18},
            )
        )
        for beat in view.beats:
            fields = asdict(beat)
            self.assertEqual(
                set(fields),
                {"seq", "action", "kind", "actor", "target", "amount", "hp_after", "text"},
            )
            self.assertNotIn("raw_roll", repr(fields))
            self.assertNotIn("hit", repr(fields))
        self.assertIn("damage", BEAT_KINDS)
        self.assertIn("other", BEAT_KINDS)


if __name__ == "__main__":
    unittest.main()
