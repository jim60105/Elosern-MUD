"""Tests for the version-1 ``party_inventory`` presentation panel.

The panel is the viewed member's equipment doll, aggregated bag rows with
server-authored use/toggle/give descriptors, and the commander purse. This
module covers the presenter (companion subject, possession-identical payloads,
the party purse, absent-member readability, malformed storage unavailable, the
maximal envelope), the pure validator's drift rejections, the dual-direction
JS parity contract, and the registry wiring.

The canonical requirement IDs this module carries:

- ``webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel``
- ``webclient-party-inventory-panel::equipment-reflects-the-viewed-members-worn-slots``
- ``webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors``
- ``webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows``
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
from world.lore.items import EquipmentModifierKey, EquipmentSlot, ItemUseMechanics
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
    ItemTargetScope,
)
from world.rules.combat_session import engage
from world.rules.party import join_party, leave_party
from world.rules.party_inventory import (
    MAX_MEMBER_INVENTORY_ROWS,
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
from web.webclient.presentation.party_inventory import (
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_KEY_CODE_POINTS,
    MAX_PRESENTATION_KEY_CODE_POINTS,
    MAX_PRESENTATION_SUMMARY_CODE_POINTS,
    MAX_REASON_CODE_POINTS,
    MAX_ROWS,
    PARTY_INVENTORY_ACCESSORY_LIMIT,
    PARTY_INVENTORY_SCHEMA_VERSION,
    party_inventory_presenter,
    validate_party_inventory,
)
from web.webclient.presentation.party_view_selection import PartyViewSelection
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    check_envelope,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry

ROOT = Path(__file__).resolve().parents[4]

_BLADE = make_item(
    "t_panel_blade",
    display_name_zh="測試長劍",
    sellable=False,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.PLAIN_SWORD,
)
_TONIC_KEY = "t_panel_tonic"
_TONIC = make_item(
    _TONIC_KEY,
    display_name_zh="測試藥水",
    price_table_key="t_mossmeals",
    use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=True),
)
_HEAL_PROFILE = ItemEffectProfile(
    effects=(
        GaugeAdjustEffect(stat=ItemStat.HP, amount=40, scope=ItemTargetScope.SELF),
    )
)
_MAXIMAL_ITEMS = tuple(
    make_item(
        f"t_panel_max_{index:02d}",
        display_name_zh="名" * MAX_DISPLAY_NAME_CODE_POINTS,
    )
    for index in range(MAX_ROWS)
)
_SCOPE_EXTRA = {
    "items": {
        row.key: row for row in (_BLADE, _TONIC, *_MAXIMAL_ITEMS)
    },
    "item_effect_profiles": {_TONIC_KEY: _HEAL_PROFILE},
}


def _row(overrides=None):
    row = {
        "item_key": _TONIC_KEY,
        "display_name": "測試藥水",
        "held": 2,
        "equipped_count": 0,
        "slot": None,
        "presentation": {
            "kind": "potion",
            "icon_key": "potion",
            "rarity": "common",
            "summary": "測試用藥水。",
        },
        "use": {"route": "field_use", "enabled": True, "reason": None},
        "toggle": None,
        "give": {"enabled": True, "reason": None, "max_quantity": 2},
    }
    row.update(overrides or {})
    return row


def _equipment(overrides=None):
    equipment = {
        "weapon_main": None,
        "weapon_off": None,
        "armor": None,
        "accessories": [],
        "accessory_limit": PARTY_INVENTORY_ACCESSORY_LIMIT,
    }
    equipment.update(overrides or {})
    return equipment


def _payload(overrides=None):
    payload = {
        "schema_version": PARTY_INVENTORY_SCHEMA_VERSION,
        "available": True,
        "kind": "party_inventory",
        "member_id": 41,
        "purse": 1240,
        "equipment": _equipment(),
        "rows": [_row()],
    }
    payload.update(overrides or {})
    return payload


def _maximal_rows(reason_length=0):
    reason = (
        "理" * reason_length
        if reason_length
        else "戰鬥中無法交換物品。"
    )
    return [
        _row(
            {
                "item_key": f"t_{index}".ljust(MAX_KEY_CODE_POINTS, "x"),
                "display_name": "名" * MAX_DISPLAY_NAME_CODE_POINTS,
                "presentation": {
                    "kind": "k" * MAX_PRESENTATION_KEY_CODE_POINTS,
                    "icon_key": "i" * MAX_PRESENTATION_KEY_CODE_POINTS,
                    "rarity": "r" * MAX_PRESENTATION_KEY_CODE_POINTS,
                    "summary": "獎" * MAX_PRESENTATION_SUMMARY_CODE_POINTS,
                },
                "use": {
                    "route": "field_use",
                    "enabled": False,
                    "reason": reason,
                },
                "give": {
                    "enabled": False,
                    "reason": reason,
                    "max_quantity": 999,
                },
            }
        )
        for index in range(MAX_ROWS)
    ]


class PartyInventoryWireTests(unittest.TestCase):
    @covers_requirement(
        "webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel"
    )
    @covers_requirement(
        "webclient-party-inventory-panel::equipment-reflects-the-viewed-member-s-worn-slots"
    )
    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_bidirectional_boundary_parity(self):
        cases = [("valid", _payload(), True)]

        def add(name, modify, accepted=False):
            value = deepcopy(_payload())
            modify(value)
            cases.append((name, value, accepted))

        add("unknown top key", lambda p: p.update(extra=1))
        add("wrong schema", lambda p: p.update(schema_version=2))
        add("schema boolean", lambda p: p.update(schema_version=True))
        add("unavailable form", lambda p: p.update(available=False))
        add("wrong kind", lambda p: p.update(kind="party"))
        add("negative purse", lambda p: p.update(purse=-1))
        add("boolean member", lambda p: p.update(member_id=True))
        add(
            "purse at the safe-integer ceiling",
            lambda p: p.update(purse=MAX_SAFE_INTEGER),
            True,
        )
        add(
            "purse over the safe-integer ceiling",
            lambda p: p.update(purse=MAX_SAFE_INTEGER + 1),
        )
        add("unknown row key", lambda p: p["rows"][0].update(extra=1))
        add("missing use", lambda p: p["rows"][0].pop("use"))
        add(
            "enabled use with reason",
            lambda p: p["rows"][0].update(
                use={"route": "field_use", "enabled": True, "reason": "不行。"}
            ),
        )
        add(
            "disabled use without reason",
            lambda p: p["rows"][0].update(
                use={"route": "field_use", "enabled": False, "reason": None}
            ),
        )
        add(
            "unknown use route",
            lambda p: p["rows"][0].update(
                use={"route": "toggle", "enabled": True, "reason": None}
            ),
        )
        add(
            "unknown toggle route",
            lambda p: (
                p["equipment"].update(weapon_main="t_blade"),
                p["rows"][0].update(
                    item_key="t_blade",
                    equipped_count=1,
                    slot="weapon_main",
                    toggle={"route": "field_use", "enabled": True, "reason": None},
                ),
            ),
        )
        add(
            "give enabled with reason",
            lambda p: p["rows"][0].update(
                give={"enabled": True, "reason": "不行。", "max_quantity": 1}
            ),
        )
        add(
            "give disabled without reason",
            lambda p: p["rows"][0].update(
                give={"enabled": False, "reason": None, "max_quantity": 1}
            ),
        )
        add(
            "negative max quantity",
            lambda p: p["rows"][0].update(
                give={"enabled": False, "reason": "不行。", "max_quantity": -1}
            ),
        )
        add(
            "boolean max quantity",
            lambda p: p["rows"][0].update(
                give={"enabled": True, "reason": None, "max_quantity": True}
            ),
        )
        add("duplicate item key", lambda p: p["rows"].append(deepcopy(p["rows"][0])))
        add(
            "row over the ceiling",
            lambda p: p.update(
                rows=[_row({"item_key": f"t_{index}"}) for index in range(MAX_ROWS + 1)]
            ),
        )
        add(
            "accessory overflow",
            lambda p: p["equipment"].update(
                accessories=["a1", "a2", "a3", "a4", "a5", "a6"]
            ),
        )
        add(
            "accessory limit drift",
            lambda p: p["equipment"].update(
                accessory_limit=PARTY_INVENTORY_ACCESSORY_LIMIT - 1
            ),
        )
        add(
            "duplicate equipment key",
            lambda p: p["equipment"].update(
                weapon_main="t_blade", armor="t_blade"
            ),
        )
        add(
            "two equipped copies",
            lambda p: (
                p["equipment"].update(weapon_main="t_blade"),
                p["rows"][0].update(
                    item_key="t_blade",
                    held=2,
                    equipped_count=2,
                    slot="weapon_main",
                    toggle={"route": "toggle", "enabled": True, "reason": None},
                ),
            ),
        )
        add(
            "worn row reports no equipment",
            lambda p: (
                p["equipment"].update(weapon_main="t_blade"),
                p["rows"][0].update(item_key="t_blade"),
            ),
        )
        add(
            "unworn row reports equipment",
            lambda p: p["rows"][0].update(
                item_key="t_blade",
                equipped_count=1,
                slot="weapon_main",
                toggle={"route": "toggle", "enabled": True, "reason": None},
            ),
        )
        add(
            "slot without toggle",
            lambda p: (
                p["equipment"].update(weapon_main="t_blade"),
                p["rows"][0].update(
                    item_key="t_blade",
                    equipped_count=1,
                    slot="weapon_main",
                ),
            ),
        )
        add(
            "unknown row slot",
            lambda p: p["rows"][0].update(slot="bag"),
        )
        add(
            "presentation key drift",
            lambda p: p["rows"][0]["presentation"].update(kind="Food"),
        )
        add(
            "presentation summary over cap",
            lambda p: p["rows"][0]["presentation"].update(
                summary="獎" * (MAX_PRESENTATION_SUMMARY_CODE_POINTS + 1)
            ),
        )
        add(
            "item key over cap",
            lambda p: p["rows"][0].update(item_key="k" * (MAX_KEY_CODE_POINTS + 1)),
        )
        add(
            "display name at cap",
            lambda p: p["rows"][0].update(
                display_name="𠮷" * MAX_DISPLAY_NAME_CODE_POINTS
            ),
            True,
        )
        add(
            "display name over cap",
            lambda p: p["rows"][0].update(
                display_name="𠮷" * (MAX_DISPLAY_NAME_CODE_POINTS + 1)
            ),
        )
        add(
            "empty display name",
            lambda p: p["rows"][0].update(display_name="  "),
        )
        add(
            "lone surrogate display name",
            lambda p: p["rows"][0].update(display_name="\ud800"),
        )
        # The closed ASCII blank vocabulary is identical on both sides: these
        # Unicode-whitespace-only values are non-blank in both validators.
        add(
            "display name unicode whitespace",
            lambda p: p["rows"][0].update(display_name="\u0085"),
            True,
        )
        add(
            "display name byte-order mark",
            lambda p: p["rows"][0].update(display_name="\ufeff"),
            True,
        )
        add(
            "reason unicode whitespace",
            lambda p: p["rows"][0].update(
                use={
                    "route": "field_use",
                    "enabled": False,
                    "reason": "\u0085",
                }
            ),
            True,
        )
        add(
            "item key unicode whitespace",
            lambda p: p["rows"][0].update(item_key="\u0085"),
            True,
        )
        add(
            "maximal bounded rows",
            lambda p: p.update(rows=_maximal_rows()),
            True,
        )
        add(
            "envelope byte overflow",
            lambda p: p.update(rows=_maximal_rows(MAX_REASON_CODE_POINTS)),
        )

        script = """
const fs = require('node:fs');
const protocol = require('./web/static/webclient/js/elosern/protocol.js');
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = cases.map(([name, value]) => {
  try { return [name, true, protocol.validatePartyInventoryPanel(value)]; }
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
                    validate_party_inventory(value)
                    python_accepts = True
                except ProtocolValidationError:
                    python_accepts = False
                self.assertEqual(python_accepts, expected)
                self.assertEqual(js_accepts, expected)
                if js_accepts:
                    self.assertEqual(validate_party_inventory(echoed), value)

    @covers_requirement(
        "webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_the_maximal_panel_fits_a_whole_envelope(self):
        payload = validate_party_inventory(
            _payload({"rows": _maximal_rows()})
        )
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)
        envelope = {
            "protocol_version": 1,
            "message": "ui_update",
            "presentation_epoch": "a" * 22,
            "revision": 1,
            "mode": "exploration",
            "panels": {"party_inventory": payload},
        }
        check_envelope(envelope)
        self.assertLessEqual(
            json_byte_size(envelope), MAX_CANONICAL_JSON_BYTES
        )

    def test_the_validator_rejects_an_unknown_top_level_field(self):
        with self.assertRaises(ProtocolValidationError):
            validate_party_inventory(_payload({"extra": 1}))

    def test_the_panel_cap_mirrors_the_rules_row_ceiling(self):
        self.assertEqual(MAX_ROWS, MAX_MEMBER_INVENTORY_ROWS)


class PartyInventoryPublicationTests(unittest.TestCase):
    """The bag tab's panel rides every update that flips or spends a bag.

    webclient-party-bag-retire made the party window's 背包 tab the only bag:
    a dock engagement must republish its combat descriptors and a combat
    round that consumes a member's item must republish its counts, in the
    same partial update as the holdings strip.
    """

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_engagement_and_rounds_republish_the_bag(self):
        from web.webclient.actions.exploration_actions import AFFECTED_ENGAGE
        from world.rules.combat_result import AFFECTED_PANELS

        for name, panels in (("engage", AFFECTED_ENGAGE), ("round", AFFECTED_PANELS)):
            self.assertIn("party_inventory", panels, name)
            self.assertIn("item_holdings", panels, name)


class PartyInventoryPresenterTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        open_synthetic_scope(self, "items", extra=_SCOPE_EXTRA)
        super().setUp()
        self.player = _player("party inventory presenter")
        self.player.location = self.room1
        self.companion = self._companion("艾拉")
        join_party(self.companion, self.player)
        self.registry = build_production_registry()

    def _companion(self, key, *, hp=100):
        npc = create_object(NPC, key=key, location=self.room1, home=self.room1)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.hp.base = hp
        npc.traits.hp.current = hp
        return npc

    def _hold(self, entity, *keys):
        entity.db.inventory = list(keys)

    def _render(self, *, actor=None, member=None):
        selection = (
            None
            if member is None
            else PartyViewSelection(
                int(self.player.pk), int(member.pk), "bag"
            )
        )
        return party_inventory_presenter(
            PresentationContext(
                actor=actor or self.player,
                protocol_version=1,
                party_view=selection,
            )
        )

    @covers_requirement(
        "webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel"
    )
    @covers_requirement(
        "webclient-party-inventory-panel::equipment-reflects-the-viewed-member-s-worn-slots"
    )
    def test_companion_subject_reports_her_own_bag_and_the_party_purse(self):
        self.player.db.wallet = 1240
        self.companion.db.wallet = 999
        self._hold(self.companion, _BLADE.key, _TONIC_KEY)
        self.companion.db.equipment = {
            "weapon_main": _BLADE.key,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }

        payload = self._render(member=self.companion)

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["kind"], "party_inventory")
        self.assertEqual(payload["member_id"], int(self.companion.pk))
        self.assertEqual(payload["purse"], 1240)
        self.assertEqual(payload["equipment"]["weapon_main"], _BLADE.key)
        self.assertEqual(payload["equipment"]["accessory_limit"], 5)
        blade = next(
            row for row in payload["rows"] if row["item_key"] == _BLADE.key
        )
        self.assertEqual(blade["equipped_count"], 1)
        self.assertEqual(blade["slot"], "weapon_main")
        self.assertIsNone(blade["use"])
        self.assertEqual(blade["give"]["max_quantity"], 0)
        self.assertEqual(
            blade["give"]["reason"], TRANSFER_MESSAGES["item_equipped"]
        )

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_possession_publishes_an_identical_payload(self):
        self._hold(self.companion, _BLADE.key, _TONIC_KEY)
        self.companion.db.equipment = {
            "weapon_main": _BLADE.key,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        before = self._render(member=self.companion)

        self.player.db.possession = {
            "npc_dbid": int(self.companion.pk),
            "since_tick": 0,
        }
        self.companion.db.possessed_by = int(self.player.pk)
        after = self._render(actor=self.companion, member=self.companion)

        self.assertEqual(after, before)

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_malformed_storage_takes_the_common_unavailable_form(self):
        cases = {
            "malformed inventory": lambda: setattr(
                self.companion.db, "inventory", "not a list"
            ),
            "malformed equipment": lambda: setattr(
                self.companion.db,
                "equipment",
                {"weapon_main": _BLADE.key},
            ),
            "malformed wallet": lambda: setattr(self.player.db, "wallet", -1),
        }
        for name, break_state in cases.items():
            with self.subTest(name=name):
                self.companion.db.inventory = []
                self.companion.db.equipment = None
                self.player.db.wallet = 0
                break_state()
                payload = self.registry.render(
                    "party_inventory",
                    PresentationContext(
                        actor=self.player,
                        protocol_version=1,
                        party_view=PartyViewSelection(
                            int(self.player.pk), int(self.companion.pk), "bag"
                        ),
                    ),
                )
                self.assertEqual(
                    payload,
                    {
                        "schema_version": PARTY_INVENTORY_SCHEMA_VERSION,
                        "available": False,
                        "reason": {
                            "code": "presentation_unavailable",
                            "message": "目前無法顯示此介面",
                        },
                    },
                )

    @covers_requirement(
        "webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_the_maximal_presenter_payload_stays_inside_the_envelope(self):
        self._hold(
            self.companion, *[item.key for item in _MAXIMAL_ITEMS]
        )

        payload = self._render(member=self.companion)

        self.assertEqual(len(payload["rows"]), MAX_ROWS)
        self.assertLessEqual(
            json_byte_size(payload), MAX_CANONICAL_JSON_BYTES
        )
        self.assertEqual(
            payload["rows"][0]["display_name"],
            "名" * MAX_DISPLAY_NAME_CODE_POINTS,
        )

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_the_panel_falls_back_to_the_commander_after_leave(self):
        selection = PartyViewSelection(
            int(self.player.pk), int(self.companion.pk), "bag"
        )
        context = PresentationContext(
            actor=self.player, protocol_version=1, party_view=selection
        )
        self.assertEqual(
            party_inventory_presenter(context)["member_id"],
            int(self.companion.pk),
        )

        leave_party(self.companion, self.player, "dismissed")

        payload = party_inventory_presenter(context)
        self.assertEqual(payload["member_id"], int(self.player.pk))
        self.assertEqual(payload["rows"], [])

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_an_absent_companion_stays_readable_with_refused_descriptors(self):
        self._hold(self.companion, _BLADE.key)
        self.companion.location = create_object(
            Room, key="party inventory panel far room"
        )
        presence = PARTY_SCOPE_MESSAGES["member_not_present"]

        payload = self._render(member=self.companion)

        self.assertEqual(len(payload["rows"]), 1)
        row = payload["rows"][0]
        self.assertFalse(row["toggle"]["enabled"])
        self.assertEqual(row["toggle"]["reason"], presence)
        self.assertFalse(row["give"]["enabled"])
        self.assertEqual(row["give"]["reason"], presence)

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_a_combat_session_reports_the_transfer_bar(self):
        self._hold(self.companion, _BLADE.key)
        monster = _monster("party inventory panel goblin", hp=500)
        monster.location = self.room1
        engage(self.player, monster)

        payload = self._render(member=self.companion)

        row = payload["rows"][0]
        self.assertFalse(row["give"]["enabled"])
        self.assertEqual(
            row["give"]["reason"], TRANSFER_MESSAGES["transfer_in_combat"]
        )
        self.assertTrue(row["toggle"]["enabled"])

    @covers_requirement(
        "webclient-party-inventory-panel::bag-rows-carry-presentation-and-server-authored-descriptors"
    )
    def test_a_malformed_combat_record_disables_field_use(self):
        from world.rules.player_messages import session_reason_message

        self.companion.traits.hp.current = 50
        self._hold(self.companion, _TONIC_KEY)
        # ``party_in_combat`` reads an unreadable record as "no session"; the
        # panel must still route the use descriptor to the combat draft and
        # publish the session's own refusal instead of field eligibility.
        self.player.db.active_combat = {"not": "a session"}

        payload = self._render(member=self.companion)

        use = payload["rows"][0]["use"]
        self.assertEqual(use["route"], "combat_draft")
        self.assertFalse(use["enabled"])
        self.assertEqual(
            use["reason"], session_reason_message("malformed_session")
        )

    @covers_requirement(
        "webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel"
    )
    def test_rendering_leaves_an_unchanged_snapshot(self):
        self.player.db.wallet = 321
        self._hold(self.companion, _BLADE.key, _TONIC_KEY)
        self.companion.db.equipment = {
            "weapon_main": _BLADE.key,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        before = {
            "inventory": list(self.companion.db.inventory),
            "equipment": deepcopy(self.companion.db.equipment),
            "wallet": self.player.db.wallet,
            "party": deepcopy(self.player.db.party),
        }

        first = self._render(member=self.companion)
        second = self._render(member=self.companion)

        self.assertEqual(first, second)
        self.assertEqual(list(self.companion.db.inventory), before["inventory"])
        self.assertEqual(self.companion.db.equipment, before["equipment"])
        self.assertEqual(self.player.db.wallet, before["wallet"])
        self.assertEqual(self.player.db.party, before["party"])

    @covers_requirement(
        "webclient-party-inventory-panel::the-panel-follows-the-viewed-member-and-never-invents-rows"
    )
    def test_registry_registers_the_panel(self):
        spec = self.registry.spec("party_inventory")
        self.assertEqual(spec.schema_version, PARTY_INVENTORY_SCHEMA_VERSION)
        self.assertIs(spec.presenter, party_inventory_presenter)
        self.assertIn("party_inventory", self.registry.panel_names)

    @covers_requirement(
        "webclient-party-inventory-panel::the-party-inventory-panel-is-an-exact-read-only-version-1-panel"
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
                    "party_inventory",
                    PresentationContext(actor=actor, protocol_version=1),
                )
                self.assertEqual(
                    payload,
                    {
                        "schema_version": PARTY_INVENTORY_SCHEMA_VERSION,
                        "available": False,
                        "reason": {
                            "code": "presentation_unavailable",
                            "message": "目前無法顯示此介面",
                        },
                    },
                )
