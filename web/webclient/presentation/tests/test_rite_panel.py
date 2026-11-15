"""The ``rite`` panel and its committed delivery (landmark-rite-panel).

The pure validator tests pin the exact version-1 available form and one
mutation per bound. The presenter tests drive the shared synthetic landmark
fixture (``world.rules.tests.rite_fixtures``) and the real
``explore.landmark_rite`` action; every string here is synthetic.
"""

import copy
import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement
from world.lore.rites.shape import art_subject_key
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from web.webclient.presentation.rite import (
    DELIVERY_NDB,
    RITE_MAX_BYTES,
    RITE_SCHEMA_VERSION,
    RITE_UNAVAILABLE_REASON,
    rite_presenter,
    validate_rite,
)
from web.webclient.actions.rite_actions import landmark_rite_adapter
from world.rules.fatigue import SleepPosture, write_fatigue_state
from world.rules.landmark_rite_record import RECORD_ATTR
from world.rules.map_knowledge import node_id_for, record_arrival
from world.rules.possession import enter_possession
from world.rules.tests.rite_fixtures import (
    ARCHETYPE_KEY,
    DISTRICT_KEY,
    DISTRICT_NAME,
    GUARDIAN_FORM,
    GUARDIAN_NAME,
    LANDMARK_NAME,
    RiteSettlementFixture,
    complete_rite_record,
)

VALID = {
    "schema_version": RITE_SCHEMA_VERSION,
    "available": True,
    "kind": "rite",
    "district": {
        "key": DISTRICT_KEY,
        "name": DISTRICT_NAME,
        "landmark": LANDMARK_NAME,
        "lit": False,
    },
    "guardian": {"name": GUARDIAN_NAME, "form": GUARDIAN_FORM},
    "art": None,
    "options": [
        {"key": "solo", "label": "獨自", "companion": False},
        {"key": "shared", "label": "共行", "companion": True},
    ],
    "performers": [
        {"member_id": None, "name": "測試主角", "owner": True},
        {"member_id": 7, "name": "測試同伴", "owner": False},
    ],
    "delivery": None,
    "seen": [],
}

DELIVERY = {
    "kind": "formal",
    "delivery_id": "rite:t_district:shared:150",
    "scene_id": "t_rite.shared.watch",
    "scene_revision": "r1",
    "actor_name": "測試同伴",
    "guardian_name": GUARDIAN_NAME,
    "lines": [
        {"kind": "narration", "text": "測試旁觀敘述。"},
        {"kind": "speech", "speaker": "actor", "text": "測試同伴之語。"},
        {"kind": "speech", "speaker": "host", "text": "測試守護對測試同伴說話。"},
    ],
}

#: A descriptor ``validate_artwork`` accepts: no attempts, no terminal.
MINIMAL_ARTWORK = {
    "subject_id": "t_subject",
    "revision": "0" * 64,
    "generation_subject": None,
    "generation_state": None,
    "attempts": [],
    "terminal": None,
    "retention_sources": [],
}


def _panel(**overrides):
    payload = copy.deepcopy(VALID)
    payload.update(overrides)
    return payload


def _section(section, **overrides):
    payload = copy.deepcopy(VALID)
    payload[section].update(overrides)
    return payload


def _with_delivery():
    payload = copy.deepcopy(VALID)
    payload["delivery"] = copy.deepcopy(DELIVERY)
    return payload


def _option_case(field, value):
    payload = copy.deepcopy(VALID)
    payload["options"][0][field] = value
    return payload


def _performer_case(field, value):
    payload = copy.deepcopy(VALID)
    payload["performers"][0][field] = value
    return payload


def _mutations():
    """One mutation per bound of the design's panel table."""
    crowded = copy.deepcopy(VALID)
    crowded["performers"] = [
        {"member_id": None, "name": "測試主角", "owner": True}
    ] + [
        {"member_id": index, "name": "測試同伴", "owner": False}
        for index in range(1, 17)
    ]

    four_options = copy.deepcopy(VALID)
    four_options["options"] += [
        {"key": "third", "label": "第三", "companion": False},
        {"key": "fourth", "label": "第四", "companion": False},
    ]

    duplicate_key = copy.deepcopy(VALID)
    duplicate_key["options"][1]["key"] = "solo"

    duplicate_member = copy.deepcopy(VALID)
    duplicate_member["performers"].append(
        {"member_id": 7, "name": "測試路人", "owner": False}
    )

    two_owners = copy.deepcopy(VALID)
    two_owners["performers"][1]["owner"] = True

    zero_lines = _with_delivery()
    zero_lines["delivery"]["lines"] = []

    wrong_delivery_kind = _with_delivery()
    wrong_delivery_kind["delivery"]["kind"] = "informal"

    unknown_speaker = _with_delivery()
    unknown_speaker["delivery"]["lines"][1]["speaker"] = "narrator"

    narration_speaker = _with_delivery()
    narration_speaker["delivery"]["lines"][0]["speaker"] = "actor"

    empty_text = _with_delivery()
    empty_text["delivery"]["lines"][0]["text"] = ""

    long_text = _with_delivery()
    long_text["delivery"]["lines"][0]["text"] = "字" * 2001

    long_scene_id = _with_delivery()
    long_scene_id["delivery"]["scene_id"] = "a" * 97

    long_delivery_id = _with_delivery()
    long_delivery_id["delivery"]["delivery_id"] = "a" * 129

    non_ascii_delivery_id = _with_delivery()
    non_ascii_delivery_id["delivery"]["delivery_id"] = "儀式"

    long_actor_name = _with_delivery()
    long_actor_name["delivery"]["actor_name"] = "名" * 129

    long_guardian_name = _with_delivery()
    long_guardian_name["delivery"]["guardian_name"] = "名" * 129

    reserved_revision = _with_delivery()
    reserved_revision["delivery"]["revision"] = "r1"

    oversize = _with_delivery()
    oversize["delivery"]["lines"] = [
        {"kind": "narration", "text": "字" * 2000} for _ in range(32)
    ]

    missing_seen = copy.deepcopy(VALID)
    missing_seen.pop("seen")

    return [
        ("extra top-level key", _panel(extra=1)),
        ("missing top-level key", missing_seen),
        ("wrong schema version", _panel(schema_version=2)),
        ("not available", _panel(available=False)),
        ("non-boolean available", _panel(available=1)),
        ("wrong kind", _panel(kind="camp")),
        ("extra district key", _section("district", extra=1)),
        ("non-ascii district key", _section("district", key="測試")),
        ("empty district key", _section("district", key="")),
        ("blank district name", _section("district", name="  ")),
        ("ecmascript-blank district name", _section("district", name="\ufeff")),
        ("too long district name", _section("district", name="丘" * 257)),
        ("too long district landmark", _section("district", landmark="碑" * 257)),
        ("non-boolean district lit", _section("district", lit=None)),
        ("extra guardian key", _section("guardian", extra=1)),
        ("blank guardian name", _section("guardian", name=" ")),
        ("too long guardian form", _section("guardian", form="形" * 201)),
        ("invalid art", _panel(art={"subject_id": "t_subject"})),
        ("no options", _panel(options=[])),
        ("four options", four_options),
        ("duplicate option key", duplicate_key),
        ("invalid option key", _option_case("key", "Solo")),
        ("blank option label", _option_case("label", "  ")),
        ("non-boolean companion", _option_case("companion", 1)),
        ("no performers", _panel(performers=[])),
        ("first performer with an id", _performer_case("member_id", 7)),
        ("too long performer name", _performer_case("name", "名" * 129)),
        ("seventeen performers", crowded),
        ("duplicate member_id", duplicate_member),
        (
            "member_id above MAX_SAFE_INTEGER",
            _performer_case("member_id", MAX_SAFE_INTEGER + 1),
        ),
        ("two owners", two_owners),
        ("seen key not an option", _panel(seen=["other"])),
        ("duplicate seen key", _panel(seen=["solo", "solo"])),
        ("too many seen keys", _panel(seen=["solo", "shared", "solo", "shared"])),
        ("delivery kind", wrong_delivery_kind),
        ("zero delivery lines", zero_lines),
        ("unknown speech speaker", unknown_speaker),
        ("narration with a speaker", narration_speaker),
        ("empty line text", empty_text),
        ("too long line text", long_text),
        ("too long scene id", long_scene_id),
        ("too long delivery id", long_delivery_id),
        ("non-ascii delivery id", non_ascii_delivery_id),
        ("too long actor name", long_actor_name),
        ("too long delivery guardian name", long_guardian_name),
        ("extra delivery key", reserved_revision),
        ("oversize panel", oversize),
    ]


class RiteValidatorTests(unittest.TestCase):
    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-is-validated-identically-by-server-and-browser",
    )
    def test_the_valid_panel_is_accepted(self):
        self.assertEqual(validate_rite(copy.deepcopy(VALID)), VALID)
        with_delivery = _with_delivery()
        with_delivery["seen"] = ["shared"]
        self.assertEqual(validate_rite(with_delivery), with_delivery)

    def test_a_canonical_artwork_descriptor_is_delegated(self):
        payload = _panel(art=copy.deepcopy(MINIMAL_ARTWORK))
        self.assertEqual(validate_rite(payload), payload)

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-is-validated-identically-by-server-and-browser",
    )
    def test_one_mutation_per_bound_is_rejected(self):
        for label, payload in _mutations():
            with self.subTest(label):
                with self.assertRaises(ProtocolValidationError):
                    validate_rite(payload)

    def test_a_canonical_panel_stays_within_the_byte_ceiling(self):
        payload = _with_delivery()
        self.assertLessEqual(json_byte_size(payload), RITE_MAX_BYTES)
        self.assertEqual(validate_rite(payload), payload)

    def test_the_oversize_mutation_exceeds_only_the_byte_ceiling(self):
        oversize = _with_delivery()
        oversize["delivery"]["lines"] = [
            {"kind": "narration", "text": "字" * 2000} for _ in range(32)
        ]
        self.assertGreater(json_byte_size(oversize), RITE_MAX_BYTES)
        self.assertEqual(len(oversize["delivery"]["lines"]), 32)

    def test_a_mixed_blank_and_text_value_is_not_blank(self):
        payload = _section("district", name="丘\ufeff")
        self.assertEqual(validate_rite(payload), payload)


class RitePanelPresenterTests(RiteSettlementFixture):
    def _render(self, actor=None):
        return rite_presenter(
            PresentationContext(
                actor=self.player if actor is None else actor, protocol_version=1
            )
        )

    def _payload(self, actor=None):
        # The fixture's synthetic archetype derives an unregistered scene art
        # subject, so the one scene chain is stubbed: these tests assert the
        # panel's own facts, and the two dedicated artwork tests drive the
        # resolution outcomes themselves.
        with patch("world.art.presenter.describe_scene", return_value=MINIMAL_ARTWORK):
            return self._render(actor)

    def _settle(self, option="shared", member_id=None):
        with self.captureOnCommitCallbacks(execute=True):
            return landmark_rite_adapter(
                self.player,
                {"option": option, "member_id": member_id},
            )

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-is-available-exactly-on-a-rite-landmark",
        "landmark-rite-panel::the-rite-panel-lists-options-performers-and-experienced-options",
    )
    def test_the_landmark_panel_names_the_site_options_and_performers(self):
        payload = self._payload()

        self.assertEqual(payload["schema_version"], RITE_SCHEMA_VERSION)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "rite")
        self.assertEqual(
            payload["district"],
            {
                "key": DISTRICT_KEY,
                "name": DISTRICT_NAME,
                "landmark": LANDMARK_NAME,
                "lit": False,
            },
        )
        self.assertEqual(
            payload["guardian"], {"name": GUARDIAN_NAME, "form": GUARDIAN_FORM}
        )
        self.assertEqual(payload["art"], MINIMAL_ARTWORK)
        self.assertEqual(
            payload["options"],
            [
                {"key": "solo", "label": "獨自", "companion": False},
                {"key": "shared", "label": "共行", "companion": True},
            ],
        )
        self.assertEqual(
            payload["performers"],
            [
                {"member_id": None, "name": self.player.key, "owner": True},
                {
                    "member_id": int(self.companion.id),
                    "name": self.companion.key,
                    "owner": False,
                },
            ],
        )
        self.assertEqual(payload["seen"], [])
        self.assertIsNone(payload["delivery"])
        self.assertEqual(validate_rite(payload), payload)

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-is-available-exactly-on-a-rite-landmark",
    )
    def test_the_lit_flag_follows_a_completed_rite(self):
        # Standing on (and having visited) the landmark lights nothing.
        record_arrival(self.player)
        self.assertFalse(self._payload()["district"]["lit"])

        complete_rite_record(self.player, DISTRICT_KEY)
        payload = self._payload()
        self.assertTrue(payload["available"])
        self.assertTrue(payload["district"]["lit"])

    def test_a_settled_rite_lights_the_panel(self):
        self.assertFalse(self._payload()["district"]["lit"])
        self._settle(option="solo")
        self.assertTrue(self._payload()["district"]["lit"])

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-is-available-exactly-on-a-rite-landmark",
    )
    def test_off_the_landmark_the_presenter_is_unavailable(self):
        self.player.location = self.source
        with self.assertRaises(PanelUnavailableError):
            self._payload()

        payload = build_production_registry().render(
            "rite", PresentationContext(actor=self.player, protocol_version=1)
        )
        self.assertFalse(payload["available"])
        self.assertEqual(payload["reason"]["code"], RITE_UNAVAILABLE_REASON[0])

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-lists-options-performers-and-experienced-options",
        "landmark-rite-panel::the-rite-panel-carries-the-last-delivery-only-on-its-node",
    )
    def test_a_committed_rite_is_carried_on_the_same_node(self):
        result = self._settle(member_id=int(self.companion.id))

        stored = getattr(self.player.ndb, DELIVERY_NDB)
        self.assertEqual(stored["node"], self.landmark_node)
        self.assertEqual(stored["delivery"], result["data"]["delivery"])

        payload = self._payload()
        self.assertEqual(payload["delivery"], result["data"]["delivery"])
        self.assertEqual(payload["seen"], ["shared"])

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-carries-the-last-delivery-only-on-its-node",
    )
    def test_a_delivery_bound_to_another_node_is_not_carried(self):
        result = self._settle(member_id=int(self.companion.id))
        delivery = result["data"]["delivery"]
        other = node_id_for(self.end)
        self.assertNotEqual(other, self.landmark_node)
        setattr(self.player.ndb, DELIVERY_NDB, {"node": other, "delivery": delivery})

        self.assertIsNone(self._payload()["delivery"])

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-carries-the-last-delivery-only-on-its-node",
    )
    def test_returning_to_the_committed_node_carries_the_delivery_again(self):
        result = self._settle(member_id=int(self.companion.id))
        self.player.location = self.source
        with self.assertRaises(PanelUnavailableError):
            self._payload()

        self.player.location = self.landmark
        self.assertEqual(self._payload()["delivery"], result["data"]["delivery"])

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-lists-options-performers-and-experienced-options",
    )
    def test_a_corrupt_record_degrades_to_no_seen_and_one_warning(self):
        self.player.attributes.add(RECORD_ATTR, {"schema_version": 2, "completed": {}})
        with patch("web.webclient.presentation.rite.log_warn") as warning, patch(
            "world.rules.map_district_lighting.log_warn"
        ) as lighting_warning:
            payload = self._payload()

        self.assertTrue(payload["available"])
        self.assertEqual(payload["seen"], [])
        self.assertFalse(payload["district"]["lit"])
        lighting_warning.assert_not_called()
        self.assertEqual(warning.call_count, 1)
        self.assertEqual(warning.call_args.args[0], "landmark_rite_record_corrupt")
        self.assertEqual(
            warning.call_args.kwargs["context"],
            {"char": self.player.pk, "district": DISTRICT_KEY},
        )

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-lists-options-performers-and-experienced-options",
    )
    def test_a_sleeping_companion_is_not_a_performer(self):
        write_fatigue_state(self.companion, 180000, SleepPosture.VOLUNTARY)

        payload = self._payload()
        self.assertEqual([row["member_id"] for row in payload["performers"]], [None])

    @covers_requirement(
        "landmark-rite-panel::the-rite-panel-lists-options-performers-and-experienced-options",
    )
    def test_a_possessed_companion_leads_and_the_owner_row_is_the_player(self):
        enter_possession(self.player, self.companion)

        payload = self._payload(actor=self.companion)
        self.assertEqual(
            payload["performers"][0],
            {
                "member_id": None,
                "name": self.companion.key,
                "owner": False,
            },
        )
        self.assertEqual(
            payload["performers"][1],
            {
                "member_id": int(self.player.id),
                "name": self.player.key,
                "owner": True,
            },
        )

    def test_the_panel_carries_the_resolved_artwork(self):
        """A produced descriptor rides the panel verbatim and still validates."""
        with patch(
            "world.art.presenter.describe_scene", return_value=MINIMAL_ARTWORK
        ) as resolved:
            payload = self._render()

        self.assertEqual(payload["art"], MINIMAL_ARTWORK)
        self.assertEqual(validate_rite(payload), payload)
        self.assertEqual(resolved.call_count, 1)
        target = resolved.call_args.args[0]
        self.assertEqual(target.identity, f"rite:{ARCHETYPE_KEY}")
        self.assertIs(target.trusted_identity, False)
        self.assertEqual(target.archetype, art_subject_key(ARCHETYPE_KEY))
        self.assertIsNone(target.room_art_key)
        self.assertIs(target.room_binding_invalid, False)

    def test_an_unresolvable_artwork_degrades_to_none_with_one_warning(self):
        """A failed resolution leaves the panel available with no artwork."""
        error = RuntimeError("no descriptor")
        with patch(
            "world.art.presenter.describe_scene", side_effect=error
        ), patch("web.webclient.presentation.rite.log_warn") as warning:
            payload = self._render()

        self.assertTrue(payload["available"])
        self.assertIsNone(payload["art"])
        self.assertEqual(validate_rite(payload), payload)
        self.assertEqual(warning.call_count, 1)
        self.assertEqual(warning.call_args.args[0], "landmark_rite_artwork_failed")
        self.assertIs(warning.call_args.kwargs["exc"], error)
        self.assertEqual(
            warning.call_args.kwargs["context"], {"archetype": ARCHETYPE_KEY}
        )


class RitePanelRegistryTests(unittest.TestCase):
    def test_the_production_registry_registers_and_validates_the_rite_panel(self):
        registry = build_production_registry()
        spec = registry.spec("rite")

        self.assertEqual(spec.schema_version, RITE_SCHEMA_VERSION)
        self.assertEqual(spec.unavailable_reason, RITE_UNAVAILABLE_REASON)
        self.assertIs(spec.validator, validate_rite)
        self.assertFalse(spec.on_demand)
        self.assertIn("rite", registry.eager_panel_names)


if __name__ == "__main__":
    unittest.main()