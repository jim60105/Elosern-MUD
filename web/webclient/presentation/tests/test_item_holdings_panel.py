"""Tests for the version-1 ``item_holdings`` presentation panel.

The panel answers, for one selected item, every party member's held count and
(for equipment) each member's server-computed stat delta against that
member's current slot occupant, plus the transfer verdict. This module covers
the pure validator's drift rejections, the dual-direction JS parity contract,
the maximal envelope, and the presenter's selection, possession, combat and
unavailable behaviour.

The canonical requirement IDs this module carries:

- ``webclient-item-holdings-panel::the-item-holdings-panel-is-an-exact-read-only-version-1-panel``
- ``webclient-item-holdings-panel::holdings-rows-report-counts-and-transfer-availability``
- ``webclient-item-holdings-panel::equipment-deltas-are-server-computed-against-each-member-s-slot-occupant``
- ``webclient-item-holdings-panel::the-selected-item-rides-the-viewed-member-selection``
"""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.items import EquipmentModifierKey, EquipmentSlot
from world.rules.combat_session import engage
from world.rules.equipment_effects import EquipmentEffectRule
from world.rules.party import join_party
from world.rules.party_inventory import (
    MAX_EQUIPMENT_DELTA_CHANGES,
    MAX_ITEM_HOLDINGS_ROWS,
    TRANSFER_MESSAGES,
)
from world.rules.party_scope import PARTY_SCOPE_MESSAGES
from world.tests.synthetic_data import make_item
from world.rules.tests._combat_session_helpers import (
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.item_holdings import (
    ITEM_HOLDINGS_SCHEMA_VERSION,
    MAX_CHANGES,
    MAX_KEY_CODE_POINTS,
    MAX_LABEL_CODE_POINTS,
    MAX_REASON_CODE_POINTS,
    MAX_ROWS,
    item_holdings_presenter,
    validate_item_holdings,
)
from web.webclient.presentation.party_view_selection import PartyViewSelection
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    check_envelope,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry

ROOT = Path(__file__).resolve().parents[4]

_SWORD = make_item(
    "t_hold_panel_sword",
    display_name_zh="測試鋼劍",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.PLAIN_SWORD,
)
_STAFF = make_item(
    "t_hold_panel_staff",
    display_name_zh="測試法杖",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.APPRENTICE_FOCUS_STAFF,
)
_CHARM = make_item(
    "t_hold_panel_charm",
    display_name_zh="測試飾品",
    sellable=False,
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=EquipmentModifierKey.SILVER_HAIRPIN,
)
_TONIC_KEY = "t_hold_panel_tonic"
_TONIC = make_item(_TONIC_KEY, display_name_zh="測試藥水", sellable=False)

_SCOPE_EXTRA = {
    "items": {row.key: row for row in (_SWORD, _STAFF, _CHARM, _TONIC)}
}

_EFFECT_RULES = {
    EquipmentModifierKey.PLAIN_SWORD: EquipmentEffectRule(
        adjustments={"atk_phys": 6},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
    EquipmentModifierKey.APPRENTICE_FOCUS_STAFF: EquipmentEffectRule(
        adjustments={},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
    EquipmentModifierKey.SILVER_HAIRPIN: EquipmentEffectRule(
        adjustments={"defense": 2},
        gauge_caps={},
        immune=(),
        attached_buffs=(),
        exposure_bias=0,
    ),
}

_EMPTY = {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []}


def _change(overrides=None):
    change = {"key": "atk_phys", "label": "攻擊", "amount": 6}
    change.update(overrides or {})
    return change


def _delta(overrides=None):
    delta = {"equippable": True, "changes": [_change()]}
    delta.update(overrides or {})
    return delta


def _receive(overrides=None):
    receive = {"enabled": True, "reason": None}
    receive.update(overrides or {})
    return receive


def _row(overrides=None):
    row = {
        "member_id": 41,
        "held": 0,
        "equipped": False,
        "delta": None,
        "receive": _receive(),
    }
    row.update(overrides or {})
    return row


def _payload(overrides=None):
    payload = {
        "schema_version": ITEM_HOLDINGS_SCHEMA_VERSION,
        "available": True,
        "kind": "item_holdings",
        "item_key": _TONIC_KEY,
        "giver_id": 7,
        "rows": [
            _row(
                {
                    "member_id": 7,
                    "held": 2,
                    "receive": _receive({"enabled": False, "reason": None}),
                }
            ),
            _row(),
        ],
    }
    payload.update(overrides or {})
    return payload


def _maximal_rows():
    # The breakdown publishes eight canonical traits, so the eight-change row
    # is the largest reachable row even though the wire ceiling is sixteen.
    traits = (
        "hp",
        "mp",
        "sp",
        "atk_phys",
        "agility",
        "defense",
        "magic_power",
        "guild_merit",
    )
    rows = []
    for index in range(MAX_ROWS):
        changes = [
            _change(
                {
                    "key": key,
                    "label": "名" * MAX_LABEL_CODE_POINTS,
                    "amount": 999,
                }
            )
            for key in traits
        ]
        rows.append(
            _row(
                {
                    "member_id": index + 1,
                    "held": 99,
                    "delta": _delta({"changes": changes}),
                    "receive": (
                        _receive({"enabled": False, "reason": None})
                        if index == 0
                        else _receive()
                    ),
                }
            )
        )
    return rows


class ItemHoldingsWireTests(unittest.TestCase):
    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    @covers_requirement(
        "webclient-item-holdings-panel::the-item-holdings-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_bidirectional_boundary_parity(self):
        cases = [
            ("valid", _payload(), True),
            ("valid refused delta", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "delta": {"equippable": False, "reason": "accessory_slots_full"},
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({
                        "delta": {"equippable": False, "reason": "accessory_slots_full"},
                    }),
                ],
            }), True),
            ("no selection", _payload({"item_key": None, "rows": []}), True),
            ("maximal bounded", _payload({
                "item_key": "t".ljust(MAX_KEY_CODE_POINTS, "x"),
                "giver_id": 1,
                "rows": _maximal_rows(),
            }), True),
            ("unknown top key", _payload({"extra": 1}), False),
            ("wrong schema", _payload({"schema_version": 2}), False),
            ("schema boolean", _payload({"schema_version": True}), False),
            ("unavailable", _payload({"available": False}), False),
            ("wrong kind", _payload({"kind": "party_inventory"}), False),
            ("blank item key", _payload({"item_key": "  "}), False),
            ("null item with rows", _payload({"item_key": None}), False),
            ("rows missing giver", _payload({"rows": [_row()]}), False),
            ("duplicate member", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"member_id": 7}),
                ],
            }), False),
            ("delta boolean discriminator", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"delta": {"equippable": 1, "changes": []}}),
                ],
            }), False),
            ("equippable with reason", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({
                        "delta": {
                            "equippable": True,
                            "changes": [],
                            "reason": "accessory_slots_full",
                        },
                    }),
                ],
            }), False),
            ("change zero amount", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"delta": _delta({"changes": [_change({"amount": 0})]})}),
                ],
            }), False),
            ("change boolean amount", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"delta": _delta({"changes": [_change({"amount": True})]})}),
                ],
            }), False),
            ("too many changes", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"delta": _delta({
                        "changes": [_change() for _ in range(MAX_CHANGES + 1)],
                    })}),
                ],
            }), False),
            ("enabled own row", _payload({
                "rows": [
                    _row({"member_id": 7, "receive": _receive()}),
                    _row(),
                ],
            }), False),
            ("disabled receive without reason", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"receive": _receive({"enabled": False, "reason": None})}),
                ],
            }), False),
            ("negative held", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "held": -1,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row(),
                ],
            }), False),
            ("mixed delta nullability", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"delta": _delta()}),
                ],
            }), False),
            ("equipped with changes", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"equipped": True, "delta": _delta()}),
                ],
            }), False),
            ("duplicate change keys", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"delta": _delta({"changes": [_change(), _change()]})}),
                ],
            }), False),
            ("unordered change keys", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"delta": _delta({"changes": [
                        _change({"key": "defense", "label": "防禦"}),
                        _change({"key": "atk_phys", "label": "攻擊"}),
                    ]})}),
                ],
            }), False),
            ("non-canonical change key", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({"enabled": False, "reason": None}),
                    }),
                    _row({"delta": _delta({"changes": [_change({"key": "luck"})]})}),
                ],
            }), False),
            ("astral key at the bound", _payload({
                "item_key": "😀" * MAX_KEY_CODE_POINTS,
            }), True),
            ("astral key over the bound", _payload({
                "item_key": "😀" * (MAX_KEY_CODE_POINTS + 1),
            }), False),
            ("unicode whitespace key", _payload({"item_key": "\u0085"}), True),
            ("byte-order-mark key", _payload({"item_key": "\ufeff"}), True),
            ("reason at the bound", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({
                            "enabled": False,
                            "reason": "理" * MAX_REASON_CODE_POINTS,
                        }),
                    }),
                    _row(),
                ],
            }), True),
            ("reason over the bound", _payload({
                "rows": [
                    _row({
                        "member_id": 7,
                        "receive": _receive({
                            "enabled": False,
                            "reason": "理" * (MAX_REASON_CODE_POINTS + 1),
                        }),
                    }),
                    _row(),
                ],
            }), False),
        ]

        script = """
const fs = require('node:fs');
const protocol = require('./web/static/webclient/js/elosern/protocol.js');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = cases.map(([name, value]) => {
  try { return [name, true, protocol.validateItemHoldingsPanel(value)]; }
  catch (_) { return [name, false, null]; }
});
process.stdout.write(JSON.stringify(results));
"""
        output = subprocess.run(
            ["node", "-e", script],
            input=json.dumps(cases),
            text=True,
            capture_output=True,
            cwd=ROOT,
            check=True,
        )
        js_results = json.loads(output.stdout)
        for (name, value, expected), (_, js_accepts, echoed) in zip(
            cases, js_results, strict=True
        ):
            with self.subTest(case=name):
                try:
                    validate_item_holdings(value)
                    python_accepts = True
                except ProtocolValidationError:
                    python_accepts = False
                self.assertEqual(python_accepts, expected)
                self.assertEqual(js_accepts, expected)
                if js_accepts:
                    self.assertEqual(validate_item_holdings(echoed), value)

    @covers_requirement(
        "webclient-item-holdings-panel::the-item-holdings-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_the_maximal_panel_fits_a_whole_envelope(self):
        payload = validate_item_holdings(
            _payload(
                {
                    "item_key": "t".ljust(MAX_KEY_CODE_POINTS, "x"),
                    "giver_id": 1,
                    "rows": _maximal_rows(),
                }
            )
        )
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        envelope = {
            "protocol_version": 1,
            "message": "ui_update",
            "presentation_epoch": "a" * 22,
            "revision": 1,
            "mode": "exploration",
            "panels": {"item_holdings": payload},
        }
        check_envelope(envelope)
        self.assertLessEqual(json_byte_size(envelope), MAX_CANONICAL_JSON_BYTES)

    def test_non_finite_amounts_reject(self):
        for amount in (float("nan"), float("inf")):
            with self.subTest(amount=amount):
                with self.assertRaises(ProtocolValidationError):
                    validate_item_holdings(
                        _payload(
                            {
                                "rows": [
                                    _row(
                                        {
                                            "member_id": 7,
                                            "receive": _receive(
                                                {"enabled": False, "reason": None}
                                            ),
                                        }
                                    ),
                                    _row(
                                        {
                                            "delta": _delta(
                                                {"changes": [_change({"amount": amount})]}
                                            )
                                        }
                                    ),
                                ]
                            }
                        )
                    )

    @covers_requirement(
        "webclient-item-holdings-panel::the-item-holdings-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_the_panel_caps_mirror_the_rules_ceilings(self):
        self.assertEqual(MAX_ROWS, MAX_ITEM_HOLDINGS_ROWS)
        self.assertEqual(MAX_CHANGES, MAX_EQUIPMENT_DELTA_CHANGES)


class ItemHoldingsPresenterTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        from unittest.mock import patch

        open_synthetic_scope(self, "items", extra=_SCOPE_EXTRA)
        effects = patch.dict(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", _EFFECT_RULES
        )
        effects.start()
        self.addCleanup(effects.stop)
        super().setUp()
        self.player = _player("item holdings presenter")
        self.player.location = self.room1
        self.companion = self._companion("艾拉")
        self.kahn = self._companion("卡恩")
        self.registry = build_production_registry()

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room1, home=self.room1)
        npc.race = _race_key()
        npc.apply_race_baseline()
        join_party(npc, self.player)
        return npc

    def _hold(self, entity, *keys):
        entity.db.inventory = list(keys)

    def _wear(self, entity, **slots):
        entity.db.equipment = {**_EMPTY, **slots}

    def _render(self, *, actor=None, member=None, item_key=None):
        selection = (
            None
            if member is None
            else PartyViewSelection(
                int(self.player.pk), int(member.pk), "bag", None, item_key
            )
        )
        return item_holdings_presenter(
            PresentationContext(
                actor=actor or self.player,
                protocol_version=1,
                party_view=selection,
            )
        )

    def _row(self, payload, member):
        return next(
            row for row in payload["rows"] if row["member_id"] == int(member.pk)
        )

    @covers_requirement(
        "webclient-party-panel::party-view-member-selects-the-viewed-member-for-the-session"
    )
    @covers_requirement(
        "webclient-item-holdings-panel::the-item-holdings-panel-is-an-exact-read-only-version-1-panel"
    )
    @covers_requirement(
        "webclient-item-holdings-panel::the-selected-item-rides-the-viewed-member-selection"
    )
    def test_no_selection_yields_no_rows(self):
        payload = self._render(member=self.companion)

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["kind"], "item_holdings")
        self.assertIsNone(payload["item_key"])
        self.assertEqual(payload["rows"], [])
        self.assertEqual(payload["giver_id"], int(self.companion.pk))

    @covers_requirement(
        "webclient-item-holdings-panel::holdings-rows-report-counts-and-transfer-availability"
    )
    def test_rows_are_commander_first_with_counts(self):
        self._hold(self.player, _TONIC_KEY)
        self._hold(self.companion, _TONIC_KEY, _TONIC_KEY)

        payload = self._render(member=self.companion, item_key=_TONIC_KEY)

        self.assertEqual(payload["item_key"], _TONIC_KEY)
        self.assertEqual(
            [row["member_id"] for row in payload["rows"]],
            [int(self.player.pk), int(self.companion.pk), int(self.kahn.pk)],
        )
        self.assertEqual([row["held"] for row in payload["rows"]], [1, 2, 0])

    @covers_requirement(
        "webclient-item-holdings-panel::equipment-deltas-are-server-computed-against-each-member-s-slot-occupant"
    )
    def test_equipment_delta_is_server_computed_for_each_member(self):
        self._hold(self.companion, _STAFF.key)
        self._wear(self.companion, weapon_main=_STAFF.key)

        payload = self._render(member=self.companion, item_key=_SWORD.key)

        row = self._row(payload, self.companion)
        self.assertEqual(
            row["delta"],
            {
                "equippable": True,
                "changes": [{"key": "atk_phys", "label": "攻擊", "amount": 6}],
            },
        )
        self.assertEqual(row["held"], 0)

    @covers_requirement(
        "webclient-item-holdings-panel::equipment-deltas-are-server-computed-against-each-member-s-slot-occupant"
    )
    def test_an_already_equipped_item_reports_no_change(self):
        self._hold(self.companion, _SWORD.key)
        self._wear(self.companion, weapon_main=_SWORD.key)

        payload = self._render(member=self.companion, item_key=_SWORD.key)

        row = self._row(payload, self.companion)
        self.assertTrue(row["equipped"])
        self.assertEqual(row["delta"], {"equippable": True, "changes": []})

    @covers_requirement(
        "webclient-item-holdings-panel::the-selected-item-rides-the-viewed-member-selection"
    )
    def test_possession_publishes_an_identical_payload(self):
        self._hold(self.companion, _SWORD.key)
        self._wear(self.companion, weapon_main=_STAFF.key)
        before = self._render(member=self.companion, item_key=_SWORD.key)

        self.player.db.possession = {
            "npc_dbid": int(self.companion.pk),
            "since_tick": 0,
        }
        self.companion.db.possessed_by = int(self.player.pk)
        after = self._render(
            actor=self.companion, member=self.companion, item_key=_SWORD.key
        )

        self.assertEqual(after, before)

    @covers_requirement(
        "webclient-item-holdings-panel::the-selected-item-rides-the-viewed-member-selection"
    )
    def test_an_unknown_item_key_clears_the_holdings(self):
        payload = self._render(
            member=self.companion, item_key="t_hold_unregistered"
        )

        self.assertIsNone(payload["item_key"])
        self.assertEqual(payload["rows"], [])

    @covers_requirement(
        "webclient-item-holdings-panel::holdings-rows-report-counts-and-transfer-availability"
    )
    def test_an_absent_receiver_is_disabled_with_the_presence_message(self):
        self._hold(self.player, _TONIC_KEY)
        self.kahn.location = create_object(
            Room, key="item holdings presenter far room"
        )

        payload = self._render(member=self.companion, item_key=_TONIC_KEY)

        row = self._row(payload, self.kahn)
        self.assertFalse(row["receive"]["enabled"])
        self.assertEqual(
            row["receive"]["reason"], PARTY_SCOPE_MESSAGES["member_not_present"]
        )

    @covers_requirement(
        "webclient-item-holdings-panel::holdings-rows-report-counts-and-transfer-availability"
    )
    def test_combat_disables_transfer_on_every_row(self):
        self._hold(self.player, _TONIC_KEY)
        monster = _monster("item holdings presenter goblin", hp=500)
        monster.location = self.room1
        engage(self.player, monster)

        payload = self._render(member=self.companion, item_key=_TONIC_KEY)

        for row in payload["rows"]:
            with self.subTest(member=row["member_id"]):
                self.assertFalse(row["receive"]["enabled"])
                self.assertEqual(
                    row["receive"]["reason"],
                    TRANSFER_MESSAGES["transfer_in_combat"],
                )

    @covers_requirement(
        "webclient-item-holdings-panel::the-selected-item-rides-the-viewed-member-selection"
    )
    def test_rendering_leaves_an_unchanged_snapshot(self):
        self._hold(self.companion, _SWORD.key, _STAFF.key)
        self._wear(self.companion, weapon_main=_STAFF.key)
        before = {
            "inventory": list(self.companion.db.inventory),
            "equipment": deepcopy(self.companion.db.equipment),
            "traits": deepcopy(
                self.companion.attributes.get("traits", category="traits")
            ),
            "party": deepcopy(self.player.db.party),
        }

        first = self._render(member=self.companion, item_key=_SWORD.key)
        second = self._render(member=self.companion, item_key=_SWORD.key)

        self.assertEqual(first, second)
        self.assertEqual(list(self.companion.db.inventory), before["inventory"])
        self.assertEqual(self.companion.db.equipment, before["equipment"])
        self.assertEqual(
            self.companion.attributes.get("traits", category="traits"),
            before["traits"],
        )
        self.assertEqual(self.player.db.party, before["party"])

    @covers_requirement(
        "webclient-item-holdings-panel::the-item-holdings-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_registry_registers_the_panel(self):
        spec = self.registry.spec("item_holdings")
        self.assertEqual(spec.schema_version, ITEM_HOLDINGS_SCHEMA_VERSION)
        self.assertIs(spec.presenter, item_holdings_presenter)
        self.assertIn("item_holdings", self.registry.panel_names)

    @covers_requirement(
        "webclient-item-holdings-panel::the-item-holdings-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_unavailable_forms_use_the_registry_reason(self):
        creation_pending = _player("待建立者")
        creation_pending.location = self.room1
        creation_pending.creation_pending = True
        no_location = _player("無處者")
        for name, actor in (
            ("creation pending", creation_pending),
            ("no location", no_location),
        ):
            with self.subTest(name=name):
                payload = self.registry.render(
                    "item_holdings",
                    PresentationContext(actor=actor, protocol_version=1),
                )
                self.assertEqual(
                    payload,
                    {
                        "schema_version": ITEM_HOLDINGS_SCHEMA_VERSION,
                        "available": False,
                        "reason": {
                            "code": "presentation_unavailable",
                            "message": "目前無法顯示此介面",
                        },
                    },
                )
