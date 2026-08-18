"""Exact ``exploration`` schema, presenter, and affordance tests.

Covers the D10 shared bounds, the version-1 payload validation, the bounded
move/look/interact serialization, the action-vs-navigate affordance shape,
locked-exit disclosure, the unavailable forms, and presenter isolation.
"""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from world.rules.tests.combat_fixtures import BattlefieldIsolation

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from typeclasses.exits import WildernessGateExit
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import GridRoom, Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.exploration import (
    ACTION_IDS,
    EXPLORATION_SCHEMA_VERSION,
    MAX_AFFORDANCES,
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_EXIT_REF_CHARS,
    MAX_INTERACT_TARGETS,
    MAX_KEYWORD_ID_CHARS,
    MAX_KEYWORD_LABEL_CODE_POINTS,
    MAX_LABEL_CODE_POINTS,
    MAX_LOOK_ENTITIES,
    MAX_LOOK_OBJECTS,
    MAX_MOVE_EXITS,
    MAX_NODE_ID_CHARS,
    MAX_SCRIPTED_KEYWORDS,
    ExplorationPanelError,
    validate_exploration,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry
from world.maps.bootstrap import NORTH_GATE_XYZ, SOUTH_GATE_XYZ, sync_grid, sync_wilderness
from world.rules.clock import get_world_clock
from world.rules.guild_economy import sync_guild_economy
from world.rules.map_knowledge import record_arrival


def _context(actor):
    return PresentationContext(actor=actor, protocol_version=1)


def _keyword(**overrides):
    value = {"keyword_id": "公會", "label": "公會"}
    value.update(overrides)
    return value


def _affordance(**overrides):
    value = {
        "kind": "action",
        "action_id": "explore.talk_scripted",
        "label": "交談",
        "enabled": True,
        "disabled_reason": None,
    }
    value.update(overrides)
    return value


def _move_row(**overrides):
    value = {
        "exit_ref": "42",
        "label": "東",
        "destination": "room:7",
        "enabled": True,
        "disabled_reason": None,
    }
    value.update(overrides)
    return value


def _entity(**overrides):
    value = {
        "identity": 5,
        "display_name": "南門守衛",
        "kind": "npc",
        "portrait_ref": None,
    }
    value.update(overrides)
    return value


def _object(**overrides):
    value = {"identity": 6, "display_name": "木箱"}
    value.update(overrides)
    return value


def _target(**overrides):
    value = {
        "identity": 5,
        "display_name": "南門守衛",
        "portrait_ref": None,
        "affordances": [_affordance()],
        "keywords": [_keyword()],
    }
    value.update(overrides)
    return value


def _valid_panel(**overrides):
    value = {
        "schema_version": 1,
        "available": True,
        "kind": "exploration",
        "move": [_move_row()],
        "look": {
            "room": {"identity": 3, "display_name": "南門", "room": True},
            "entities": [_entity()],
            "objects": [_object()],
        },
        "interact": [_target()],
        "character": {"available": True},
        "quests": {"available": True},
        "inventory": {"available": True},
    }
    value.update(overrides)
    return value


class ExplorationSchemaTests(unittest.TestCase):
    def test_valid_panel_passes(self):
        normalized = validate_exploration(_valid_panel())
        self.assertEqual(normalized["schema_version"], EXPLORATION_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["kind"], "exploration")
        self.assertEqual(normalized["look"]["room"]["room"], True)
        self.assertEqual(len(normalized["interact"][0]["affordances"]), 1)

    def test_rejects_unknown_and_missing_fields(self):
        payload = _valid_panel(bogus=1)
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)
        payload = _valid_panel()
        del payload["interact"]
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_rejects_wrong_kind_and_version(self):
        with self.assertRaises(ExplorationPanelError):
            validate_exploration(_valid_panel(kind="services"))
        with self.assertRaises(ExplorationPanelError):
            validate_exploration(_valid_panel(schema_version=2))

    def test_rejects_duplicate_interact_identities(self):
        payload = _valid_panel(
            interact=[_target(), _target(identity=5)]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_exit_ref_bound_enforced(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(move=[_move_row(exit_ref="x" * (MAX_EXIT_REF_CHARS + 1))])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(move=[_move_row(exit_ref="非ascii")]))

    def test_destination_must_be_canonical_node(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(move=[_move_row(destination="not:a:node")]))

    def test_locked_move_row_requires_reason(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(move=[_move_row(enabled=False, disabled_reason=None)])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    move=[
                        _move_row(
                            enabled=True,
                            disabled_reason={"code": "locked", "message": "此出口目前無法通行。"},
                        )
                    ]
                )
            )

    def test_affordance_kind_shapes_are_exact(self):
        # navigate must not carry action_id.
        payload = _valid_panel(
            interact=[
                _target(
                    affordances=[
                        {
                            "kind": "navigate",
                            "action_id": "explore.talk_scripted",
                            "surface": "guild",
                            "label": "公會服務",
                            "enabled": True,
                            "disabled_reason": None,
                        }
                    ]
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)
        # navigate is never a registered adapter: only action kind carries action_id.
        payload = _valid_panel(
            interact=[
                _target(
                    affordances=[
                        {
                            "kind": "action",
                            "surface": "guild",
                            "label": "公會服務",
                            "enabled": True,
                            "disabled_reason": None,
                        }
                    ]
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_keywords_require_a_talk_scripted_affordance(self):
        # Scripted keyword buttons live on the target descriptor; a target that
        # carries keywords but no talk_scripted affordance is rejected.
        payload = _valid_panel(
            interact=[
                _target(
                    affordances=[
                        {
                            "kind": "action",
                            "action_id": "explore.engage",
                            "label": "戰鬥",
                            "enabled": True,
                            "disabled_reason": None,
                        }
                    ],
                    keywords=[_keyword()],
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_action_id_closed_set(self):
        payload = _valid_panel(
            interact=[
                _target(
                    affordances=[
                        {
                            "kind": "action",
                            "action_id": "explore.take",
                            "label": "拾取",
                            "enabled": True,
                            "disabled_reason": None,
                        }
                    ]
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_keyword_count_bound(self):
        payload = _valid_panel(
            interact=[
                _target(
                    keywords=[
                        _keyword(keyword_id=f"k{i}", label=f"話題{i}")
                        for i in range(MAX_SCRIPTED_KEYWORDS + 1)
                    ]
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_affordance_count_bound(self):
        payload = _valid_panel(
            interact=[
                _target(
                    affordances=[
                        {
                            "kind": "action",
                            "action_id": "explore.engage",
                            "label": "戰鬥",
                            "enabled": True,
                            "disabled_reason": None,
                        }
                    ]
                    * (MAX_AFFORDANCES + 1)
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_list_count_bounds(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    move=[_move_row(exit_ref=str(i), destination=f"room:{i}") for i in range(MAX_MOVE_EXITS + 1)]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        **_valid_panel()["look"],
                        "entities": [
                            _entity(identity=i) for i in range(MAX_LOOK_ENTITIES + 1)
                        ],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        **_valid_panel()["look"],
                        "objects": [
                            _object(identity=i) for i in range(MAX_LOOK_OBJECTS + 1)
                        ],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[_target(identity=i) for i in range(MAX_INTERACT_TARGETS + 1)]
                )
            )

    @covers_requirement("webclient-exploration-menu::portrait-focus-stays-client-local-against-the-art-catalog-seam")
    def test_portrait_ref_must_be_null(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[_target(portrait_ref="catalog:goblin")]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(look={
                **_valid_panel()["look"],
                "entities": [_entity(portrait_ref="catalog:goblin")],
            }))

    def test_disguise_like_availability_entries_are_exact(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(character={"available": True, "extra": 1}))
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(quests={"available": "yes"}))

    def test_worst_case_legal_payload_fits_the_envelope(self):
        # The structural maxima the schema allows -- 12 exits, 32 entities,
        # 32 objects, 32 targets with 8 affordances each -- with realistic
        # bounded content. Only the scripted affordance carries keyword rows,
        # exactly as a real dialogue host would.
        move = [
            _move_row(
                exit_ref=f"e{i}",
                label="東邊出口" * 2,
                destination=f"room:{i + 1000}",
            )
            for i in range(MAX_MOVE_EXITS)
        ]
        entities = [
            _entity(identity=i + 1, display_name="南門守衛" * 2)
            for i in range(MAX_LOOK_ENTITIES)
        ]
        objects = [
            _object(identity=1000 + i, display_name="木箱") for i in range(MAX_LOOK_OBJECTS)
        ]
        interact = []
        for i in range(MAX_INTERACT_TARGETS):
            affordances = [_affordance()]
            for _ in range(MAX_AFFORDANCES - 1):
                affordances.append(
                    {
                        "kind": "action",
                        "action_id": "explore.engage",
                        "label": "戰鬥",
                        "enabled": True,
                        "disabled_reason": None,
                    }
                )
            interact.append(
                _target(
                    identity=i + 1,
                    display_name="守衛",
                    affordances=affordances,
                    keywords=[
                        _keyword(keyword_id=f"k{j}", label="話題")
                        for j in range(MAX_SCRIPTED_KEYWORDS)
                    ],
                )
            )
        payload = _valid_panel(
            move=move,
            look={
                "room": {"identity": 3, "display_name": "南門", "room": True},
                "entities": entities,
                "objects": objects,
            },
            interact=interact,
        )
        normalized = validate_exploration(payload)
        size = json_byte_size(normalized)
        self.assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)

    def test_byte_budget_fails_closed_on_the_theoretical_worst_case(self):
        # Per-field ceilings are bounds, not a guarantee any combination fits.
        # A payload with 8 scripted-with-16-keyword affordances on every one of
        # 32 targets serializes far beyond the envelope, so the validator MUST
        # reject it -- conformance is enforced on serialized size (D10).
        interact = []
        for i in range(MAX_INTERACT_TARGETS):
            affordances = []
            for _ in range(MAX_AFFORDANCES):
                affordances.append(
                    {
                        "kind": "action",
                        "action_id": "explore.talk_scripted",
                        "label": "交談" * 60,
                        "enabled": True,
                        "disabled_reason": None,
                        "keywords": [
                            {
                                "keyword_id": f"keyword-{j}-{i}",
                                "label": "很長的話題標籤" * 40,
                            }
                            for j in range(MAX_SCRIPTED_KEYWORDS)
                        ],
                    }
                )
            interact.append(
                _target(
                    identity=i + 1,
                    display_name="非常長的名稱" * 40,
                    affordances=affordances,
                )
            )
        payload = _valid_panel(interact=interact)
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_rejects_blank_labels_and_bad_branch_shapes(self):
        wide_node = "x" * (MAX_NODE_ID_CHARS + 1)
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(move=[_move_row(exit_ref="e1", destination=wide_node)])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(keywords=[_keyword(keyword_id="  ", label="話題")])
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            keywords=[
                                _keyword(
                                    keyword_id="x" * (MAX_KEYWORD_ID_CHARS + 1),
                                    label="話題",
                                )
                            ]
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(keywords=[_keyword(keyword_id="k", label="  ")])
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            keywords=None,
                            affordances=[
                                {
                                    "kind": "action",
                                    "action_id": "explore.engage",
                                    "label": "戰鬥",
                                    "enabled": False,
                                    "disabled_reason": {"code": "locked", "message": " "},
                                }
                            ],
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(interact=[_target(keywords=None, affordances=[42])])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            keywords=None,
                            affordances=[
                                {
                                    "kind": "cast",
                                    "action_id": "explore.engage",
                                    "label": "戰鬥",
                                    "enabled": True,
                                    "disabled_reason": None,
                                }
                            ]
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            keywords=None,
                            affordances=[
                                {
                                    "kind": "action",
                                    "action_id": "explore.engage",
                                    "label": " ",
                                    "enabled": True,
                                    "disabled_reason": None,
                                }
                            ]
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            keywords=None,
                            affordances=[
                                {
                                    "kind": "action",
                                    "action_id": "explore.engage",
                                    "label": "戰鬥",
                                    "enabled": False,
                                    "disabled_reason": None,
                                }
                            ],
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            keywords=None,
                            affordances=[
                                {
                                    "kind": "action",
                                    "action_id": "explore.engage",
                                    "label": "戰鬥",
                                    "enabled": True,
                                    "disabled_reason": {
                                        "code": "locked",
                                        "message": "此出口目前無法通行。",
                                    },
                                }
                            ],
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            keywords=None,
                            affordances=[
                                {
                                    "kind": "navigate",
                                    "surface": "bank",
                                    "label": "公會",
                                    "enabled": True,
                                    "disabled_reason": None,
                                }
                            ]
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": "南門", "room": True},
                        "entities": [_entity(display_name=" ")],
                        "objects": [],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": "南門", "room": True},
                        "entities": [_entity(kind="goblin")],
                        "objects": [],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": "南門", "room": True},
                        "entities": [],
                        "objects": [_object(display_name=" ")],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": " ", "room": True},
                        "entities": [],
                        "objects": [],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": "南門", "room": False},
                        "entities": [],
                        "objects": [],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[_target(identity=1, display_name=" ")]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(move=[_move_row(label=" ")]))
        with self.assertRaises(ExplorationPanelError):
            validate_exploration(_valid_panel(available=False))

    def test_over_envelope_fails_closed(self):
        wide = "😀" * MAX_LABEL_CODE_POINTS
        wide_keyword = "😀" * MAX_KEYWORD_LABEL_CODE_POINTS
        interact = []
        for i in range(MAX_INTERACT_TARGETS):
            interact.append(
                _target(
                    identity=i + 1,
                    display_name=wide,
                    affordances=[
                        _affordance(label=wide)
                        for _ in range(MAX_AFFORDANCES)
                    ],
                    keywords=[
                        _keyword(keyword_id=f"k{i}_{j}", label=wide_keyword)
                        for j in range(MAX_SCRIPTED_KEYWORDS)
                    ],
                )
            )
        payload = _valid_panel(
            move=[_move_row(exit_ref=f"e{i}", label=wide) for i in range(MAX_MOVE_EXITS)],
            interact=interact,
        )
        with self.assertRaises(ExplorationPanelError):
            validate_exploration(payload)


class ExplorationPresenterTests(BattlefieldIsolation, EvenniaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        get_world_clock()
        sync_grid()

    def setUp(self):
        from world.quests.catalog import register_catalog
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_config import (
            CATALOG,
            load_catalog_into_cache,
            register_catalog_offers,
        )
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._catalog = CATALOG
        self._offers = list(GUILD_OFFER_REGISTRY.items())
        register_catalog()
        catalog = load_catalog_into_cache()
        register_catalog_offers(catalog)
        self.room1 = create_object(Room, key="南門")
        self.south_gate = self.room1
        self.player = create_object(PlayerCharacter, key="探索測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.south_gate
        record_arrival(self.player)

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        if hasattr(self, "_registry_items"):
            import world.rules.guild_config as guild_config

            QUEST_DEFINITION_REGISTRY.clear()
            QUEST_DEFINITION_REGISTRY.update(self._registry_items)
            GUILD_OFFER_REGISTRY.clear()
            GUILD_OFFER_REGISTRY.update(self._offers)
            guild_config.CATALOG = self._catalog
        super().tearDown()

    def _registry(self):
        return build_production_registry()

    def _render(self):
        return self._registry().render("exploration", _context(self.player))

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-1-presentation-panel")
    def test_room_renders_exploration_payload_without_mutation(self):
        before = {
            "location": self.player.location,
            "wallet": self.player.db.wallet,
            "map_knowledge": self.player.attributes.get("map_knowledge"),
        }
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "exploration")
        self.assertEqual(payload["look"]["room"]["room"], True)
        self.assertEqual(payload["look"]["room"]["identity"], int(self.south_gate.pk))
        self.assertEqual(payload["character"], {"available": True})
        self.assertIs(self.player.location, before["location"])
        self.assertEqual(self.player.db.wallet, before["wallet"])
        self.assertEqual(
            self.player.attributes.get("map_knowledge"), before["map_knowledge"]
        )

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-1-presentation-panel")
    def test_move_lists_exits_with_canonical_destinations(self):
        destination = create_object(Room, key="南大道", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="北",
            location=self.south_gate,
            destination=destination,
        )
        payload = self._render()
        move = payload["move"]
        self.assertTrue(any(row["exit_ref"] == str(int(exit_obj.id)) for row in move))
        row = next(row for row in move if row["exit_ref"] == str(int(exit_obj.id)))
        self.assertTrue(row["enabled"])
        self.assertEqual(row["destination"], f"room:{int(destination.pk)}")
        self.assertIsNone(row["disabled_reason"])

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-1-presentation-panel")
    def test_locked_exit_is_disclosed_but_disabled(self):
        destination = create_object(Room, key="密室", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="下",
            location=self.south_gate,
            destination=destination,
        )
        exit_obj.locks.add("traverse:false()")
        payload = self._render()
        row = next(
            row for row in payload["move"] if row["exit_ref"] == str(int(exit_obj.id))
        )
        self.assertFalse(row["enabled"])
        self.assertEqual(row["disabled_reason"]["code"], "locked")
        self.assertTrue(row["disabled_reason"]["message"].strip())

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-1-presentation-panel")
    def test_no_location_is_unavailable_without_fabrication(self):
        self.player.location = None
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("move", payload)
        self.assertNotIn("interact", payload)

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_scripted_host_exposes_its_authored_keywords(self):
        host = create_object(NPC, key="公會職員", location=self.south_gate)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key="guild_staff")
        )
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(host.pk))
        scripted = next(
            a for a in target["affordances"] if a["kind"] == "action"
            and a["action_id"] == "explore.talk_scripted"
        )
        self.assertTrue(scripted["enabled"])
        self.assertIsNotNone(target.get("keywords"))
        keyword_ids = [keyword["keyword_id"] for keyword in target["keywords"]]
        self.assertIn("註冊", keyword_ids)
        self.assertIn("任務", keyword_ids)
        self.assertIn("回報", keyword_ids)
        # A scripted-only host offers no free-form affordance.
        self.assertFalse(
            any(
                a["kind"] == "action" and a["action_id"] == "explore.talk_freeform"
                for a in target["affordances"]
            )
        )

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_generative_npc_offers_free_form_talk(self):
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.south_gate)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(npc.pk))
        freeform = next(
            a for a in target["affordances"] if a["kind"] == "action"
            and a["action_id"] == "explore.talk_freeform"
        )
        self.assertTrue(freeform["enabled"])

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_living_hostile_monster_offers_engage(self):
        monster = create_object(Monster, key="哥布林", location=self.south_gate)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(monster.pk))
        engage = next(
            a for a in target["affordances"] if a["kind"] == "action"
            and a["action_id"] == "explore.engage"
        )
        self.assertTrue(engage["enabled"])
        # The actor has no active session, so no engage disablement is offered.
        self.assertIsNone(engage["disabled_reason"])

    def test_no_affordance_is_fabricated_for_a_plain_npc(self):
        plain = create_object(NPC, key="路人", location=self.south_gate)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(plain.pk))
        self.assertEqual(target["affordances"], [])
        action_ids = {
            a.get("action_id") for a in target["affordances"] if a.get("action_id")
        }
        self.assertNotIn("explore.party_invite", action_ids)
        self.assertNotIn("explore.party_leave", action_ids)

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_unbound_generative_npc_offers_an_enabled_invite(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.south_gate)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(npc.pk))
        invite = next(
            a for a in target["affordances"]
            if a["action_id"] == "explore.party_invite"
        )
        self.assertTrue(invite["enabled"])
        self.assertIsNone(invite["disabled_reason"])
        self.assertNotIn(
            "explore.party_leave",
            {a["action_id"] for a in target["affordances"] if a.get("action_id")},
        )

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_full_party_disables_the_invite_with_the_reason(self):
        from world.rules.party import PARTY_MAX_COMPANIONS, join_party

        for index in range(PARTY_MAX_COMPANIONS):
            join_party(
                create_object(LLMNPC, key=f"同伴{index}", location=self.south_gate),
                self.player,
            )
        npc = create_object(LLMNPC, key="對話精靈", location=self.south_gate)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(npc.pk))
        invite = next(
            a for a in target["affordances"]
            if a["action_id"] == "explore.party_invite"
        )
        self.assertFalse(invite["enabled"])
        self.assertEqual(invite["disabled_reason"]["code"], "party_full")
        self.assertIn("滿", invite["disabled_reason"]["message"])

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_bound_companion_offers_leave_and_never_invite(self):
        from world.rules.party import join_party

        npc = create_object(LLMNPC, key="對話精靈", location=self.south_gate)
        join_party(npc, self.player)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(npc.pk))
        action_ids = {
            a["action_id"] for a in target["affordances"] if a.get("action_id")
        }
        self.assertIn("explore.party_leave", action_ids)
        self.assertNotIn("explore.party_invite", action_ids)
        leave = next(
            a for a in target["affordances"] if a["action_id"] == "explore.party_leave"
        )
        self.assertTrue(leave["enabled"])

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_bound_plain_npc_offers_leave_too(self):
        from world.rules.party import join_party

        plain = create_object(NPC, key="路人", location=self.south_gate)
        join_party(plain, self.player)
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(plain.pk))
        action_ids = {
            a["action_id"] for a in target["affordances"] if a.get("action_id")
        }
        self.assertIn("explore.party_leave", action_ids)
        self.assertNotIn("explore.party_invite", action_ids)

    @covers_requirement("webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose")
    def test_service_affordance_is_navigate_kind_and_host_bound(self):
        staff = create_object(NPC, key="公會職員", location=self.south_gate)
        staff.components.add(
            GuildStaff.create(staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        monster = create_object(Monster, key="哥布林", location=self.south_gate)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        payload = self._render()
        staff_target = next(
            t for t in payload["interact"] if t["identity"] == int(staff.pk)
        )
        monster_target = next(
            t for t in payload["interact"] if t["identity"] == int(monster.pk)
        )
        service = next(
            a for a in staff_target["affordances"] if a["kind"] == "navigate"
        )
        self.assertEqual(service["surface"], "guild")
        self.assertEqual(service["action_id"] if "action_id" in service else None, None)
        # The navigate affordance is dock-navigation only: never an action_id,
        # never submitted as an action, and never on an unrelated target.
        self.assertNotIn("action_id", service)
        self.assertFalse(
            any(a["kind"] == "navigate" for a in monster_target["affordances"])
        )
        # No explore.take / explore.drop descriptor anywhere.
        all_action_ids = {
            a.get("action_id")
            for t in payload["interact"]
            for a in t["affordances"]
            if a.get("action_id") is not None
        }
        self.assertEqual(
            all_action_ids & {"explore.take", "explore.drop"}, set()
        )

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-1-presentation-panel")
    def test_quests_and_inventory_respect_the_services_capability(self):
        payload = self._render()
        self.assertTrue(payload["quests"]["available"])
        self.assertTrue(payload["inventory"]["available"])
        # A malformed wallet makes the services view unbuildable; both entries
        # turn unavailable while the exploration panel itself stays available.
        self.player.db.wallet = -1
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertFalse(payload["quests"]["available"])
        self.assertFalse(payload["inventory"]["available"])

    @covers_requirement("webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-1-presentation-panel")
    def test_combat_mode_renders_unavailable_form(self):
        monster = create_object(Monster, key="哥布林", location=self.south_gate)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        from world.rules.combat_session import engage

        engage(self.player, monster)
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("move", payload)
        self.assertNotIn("interact", payload)

    def test_creation_pending_renders_unavailable_form(self):
        self.player.db.creation_pending = True
        payload = self._render()
        self.assertFalse(payload["available"])

    def test_corrupt_dialogue_table_degrades_only_the_affordance(self):
        host = create_object(NPC, key="壞掉的NPC", location=self.south_gate)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="unknown_table"))
        payload = self._render()
        self.assertTrue(payload["available"])
        target = next(t for t in payload["interact"] if t["identity"] == int(host.pk))
        scripted = next(
            a for a in target["affordances"] if a["kind"] == "action"
            and a["action_id"] == "explore.talk_scripted"
        )
        self.assertFalse(scripted["enabled"])
        self.assertEqual(scripted["disabled_reason"]["code"], "dialogue_unavailable")
        self.assertNotIn("keywords", target)

    def test_missing_host_and_broken_presenter_keep_status_healthy(self):
        # A room with no host yields an empty interact list and the panel stays
        # available; a corrupt dialogue host degrades only that affordance.
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["interact"], [])
        host = create_object(NPC, key="壞掉的NPC", location=self.south_gate)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="unknown_table"))
        exploration = self._registry().render("exploration", _context(self.player))
        self.assertTrue(exploration["available"])
        # The status and narrative surfaces stay healthy alongside a degraded
        # exploration affordance.
        status = self._registry().render("status", _context(self.player))
        self.assertTrue(status["available"])

    def test_move_rows_cover_grid_and_terrain_destinations(self):
        from unittest.mock import PropertyMock

        from typeclasses.rooms import GridRoom, TerrainRoom
        from web.webclient.actions.node_ids import node_id_for_location
        from world.maps.bootstrap import NORTH_GATE_XYZ

        north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        grid_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="北門",
            location=self.south_gate,
            destination=north_gate,
        )
        terrain = create_object(TerrainRoom, key="霧區", location=None)
        terrain.ndb.active_coordinates = (5, 5)
        wild_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="荒野",
            location=self.south_gate,
            destination=terrain,
        )
        bare = create_object(TerrainRoom, key="無座標", location=None)
        bare_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="霧",
            location=self.south_gate,
            destination=bare,
        )
        plain = create_object(Room, key="普通目的地", location=None)
        plain_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="門",
            location=self.south_gate,
            destination=plain,
        )
        none_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="虛",
            location=self.south_gate,
            destination=self.south_gate,
        )
        payload = self._render()
        rows = {row["exit_ref"]: row for row in payload["move"]}
        # Every destination node is byte-identical to the shared encoder's
        # derivation (ordinary room, GridRoom, and TerrainRoom alike).
        self.assertEqual(
            rows[str(int(grid_exit.id))]["destination"],
            node_id_for_location(north_gate),
        )
        self.assertEqual(
            rows[str(int(wild_exit.id))]["destination"],
            node_id_for_location(terrain),
        )
        self.assertEqual(
            rows[str(int(plain_exit.id))]["destination"],
            node_id_for_location(plain),
        )
        self.assertNotIn(str(int(bare_exit.id)), rows)
        with patch.object(
            type(none_exit), "destination", new_callable=PropertyMock, return_value=None
        ):
            payload = self._render()
        self.assertNotIn(str(int(none_exit.id)), [r["exit_ref"] for r in payload["move"]])

    def test_exit_access_failure_discloses_a_disabled_row(self):
        from unittest.mock import patch

        destination = create_object(Room, key="密室", location=None)
        exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="下",
            location=self.south_gate,
            destination=destination,
        )
        with patch.object(exit_obj, "access", side_effect=RuntimeError("boom")):
            payload = self._render()
        row = next(
            r for r in payload["move"] if r["exit_ref"] == str(int(exit_obj.id))
        )
        self.assertFalse(row["enabled"])
        self.assertEqual(row["disabled_reason"]["code"], "locked")

    def test_dead_monster_offers_a_disabled_engage_affordance(self):
        monster = create_object(Monster, key="屍體", location=self.south_gate)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.current = 0
        monster.save()
        payload = self._render()
        target = next(t for t in payload["interact"] if t["identity"] == int(monster.pk))
        engage = next(
            a for a in target["affordances"] if a["action_id"] == "explore.engage"
        )
        self.assertFalse(engage["enabled"])
        self.assertEqual(engage["disabled_reason"]["code"], "target_dead")

    def test_locationless_serializers_return_empty_lists(self):
        from web.webclient.actions.node_ids import node_id_for_location
        from web.webclient.presentation import exploration as module

        self.player.location = None
        self.assertEqual(module._move_rows(self.player), [])
        self.assertEqual(module._look_entities(self.player), [])
        self.assertEqual(module._look_objects(self.player), [])
        self.assertEqual(module._interact_targets(self.player), [])
        self.assertIsNone(node_id_for_location(None))
        self.assertFalse(hasattr(module, "_destination_node"))


class ExplorationByteStabilityTests(BattlefieldIsolation, EvenniaTestCase):
    """The v1 payload is byte-stable while the panel delegates to the shared vocabulary.

    Pins the pre-refactor expected descriptor shapes for one rule-table fixture
    room (scripted host, generative NPC, plain NPC, monster, objects, enabled
    and locked exits) — same dicts, same order — and asserts the idle-baseline
    entries never appear in the v1 payload.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from world.quests.catalog import register_catalog
        from world.rules.guild_config import (
            CATALOG,
            load_catalog_into_cache,
            register_catalog_offers,
        )

        cls._registry_items = None
        get_world_clock()
        sync_grid()
        register_catalog()
        catalog = load_catalog_into_cache()
        register_catalog_offers(catalog)

    def setUp(self):
        from evennia.objects.objects import DefaultObject

        self.room1 = create_object(Room, key="南門")
        self.player = create_object(PlayerCharacter, key="穩定測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        record_arrival(self.player)
        self.destination = create_object(Room, key="北大道", location=None)
        self.exit_obj = create_object(
            "evennia.objects.objects.DefaultExit",
            key="東",
            location=self.room1,
            destination=self.destination,
        )
        self.secret = create_object(Room, key="密室", location=None)
        self.locked_exit = create_object(
            "evennia.objects.objects.DefaultExit",
            key="西",
            location=self.room1,
            destination=self.secret,
        )
        self.locked_exit.locks.add("traverse:false()")
        self.host = create_object(NPC, key="公會職員", location=self.room1)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key="guild_staff")
        )
        self.bard = create_object(LLMNPC, key="吟遊詩人", location=self.room1)
        self.passerby = create_object(NPC, key="路人", location=self.room1)
        self.goblin = create_object(Monster, key="哥布林", location=self.room1)
        self.goblin.threat_tier = "low"
        self.goblin.apply_monster_tier("floor")
        self.box = create_object(DefaultObject, key="木箱", location=self.room1)

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        if self._registry_items is not None:
            import world.rules.guild_config as guild_config

            QUEST_DEFINITION_REGISTRY.clear()
            QUEST_DEFINITION_REGISTRY.update(self._registry_items)
            GUILD_OFFER_REGISTRY.clear()
            GUILD_OFFER_REGISTRY.update(self._offers)
            guild_config.CATALOG = self._catalog
        super().tearDown()

    def _render(self):
        return build_production_registry().render("exploration", _context(self.player))

    def test_rule_table_fixture_payload_is_byte_identical_to_v1(self):
        payload = self._render()
        self.assertEqual(
            payload,
            {
                "schema_version": 1,
                "available": True,
                "kind": "exploration",
                "move": [
                    {
                        "exit_ref": str(int(self.exit_obj.id)),
                        "label": "東",
                        "destination": f"room:{int(self.destination.pk)}",
                        "enabled": True,
                        "disabled_reason": None,
                    },
                    {
                        "exit_ref": str(int(self.locked_exit.id)),
                        "label": "西",
                        "destination": f"room:{int(self.secret.pk)}",
                        "enabled": False,
                        "disabled_reason": {
                            "code": "locked",
                            "message": "此出口目前無法通行。",
                        },
                    },
                ],
                "look": {
                    "room": {
                        "identity": int(self.room1.pk),
                        "display_name": "南門",
                        "room": True,
                    },
                    "entities": [
                        {
                            "identity": int(self.host.pk),
                            "display_name": "公會職員",
                            "kind": "npc",
                            "portrait_ref": None,
                        },
                        {
                            "identity": int(self.bard.pk),
                            "display_name": "吟遊詩人",
                            "kind": "npc",
                            "portrait_ref": None,
                        },
                        {
                            "identity": int(self.passerby.pk),
                            "display_name": "路人",
                            "kind": "npc",
                            "portrait_ref": None,
                        },
                        {
                            "identity": int(self.goblin.pk),
                            "display_name": "哥布林",
                            "kind": "monster",
                            "portrait_ref": None,
                        },
                    ],
                    "objects": [
                        {"identity": int(self.box.pk), "display_name": "木箱"}
                    ],
                },
                "interact": [
                    {
                        "identity": int(self.host.pk),
                        "display_name": "公會職員",
                        "portrait_ref": None,
                        "affordances": [
                            {
                                "kind": "action",
                                "action_id": "explore.talk_scripted",
                                "label": "交談",
                                "enabled": True,
                                "disabled_reason": None,
                            }
                        ],
                        "keywords": [
                            {"keyword_id": "註冊", "label": "註冊"},
                            {"keyword_id": "任務", "label": "任務"},
                            {"keyword_id": "公會", "label": "公會"},
                            {"keyword_id": "工會", "label": "工會"},
                            {"keyword_id": "回報", "label": "回報"},
                            {"keyword_id": "再見", "label": "再見"},
                        ],
                    },
                    {
                        "identity": int(self.bard.pk),
                        "display_name": "吟遊詩人",
                        "portrait_ref": None,
                        "affordances": [
                            {
                                "kind": "action",
                                "action_id": "explore.talk_freeform",
                                "label": "自由交談",
                                "enabled": True,
                                "disabled_reason": None,
                            },
                            {
                                "kind": "action",
                                "action_id": "explore.party_invite",
                                "label": "邀請",
                                "enabled": True,
                                "disabled_reason": None,
                            },
                        ],
                    },
                    {
                        "identity": int(self.passerby.pk),
                        "display_name": "路人",
                        "portrait_ref": None,
                        "affordances": [],
                    },
                    {
                        "identity": int(self.goblin.pk),
                        "display_name": "哥布林",
                        "portrait_ref": None,
                        "affordances": [
                            {
                                "kind": "action",
                                "action_id": "explore.engage",
                                "label": "戰鬥",
                                "enabled": True,
                                "disabled_reason": None,
                            }
                        ],
                    },
                ],
                "character": {"available": True},
                "quests": {"available": True},
                "inventory": {"available": True},
            },
        )

    def test_idle_baseline_entries_never_appear_in_the_v1_payload(self):
        payload = self._render()
        action_ids = {
            affordance.get("action_id")
            for target in payload["interact"]
            for affordance in target["affordances"]
            if affordance.get("action_id") is not None
        }
        self.assertNotIn("explore.wait", action_ids)
        self.assertNotIn("explore.look", action_ids)
        self.assertEqual(
            action_ids,
            {"explore.talk_scripted", "explore.talk_freeform", "explore.party_invite", "explore.engage"},
        )
        # The same room's vocabulary does carry the baseline room-look entry,
        # so the exclusion is a v1 serialization property, not an empty room.
        from web.webclient.presentation.affordances import exploration_affordances

        vocabulary = exploration_affordances(self.player)
        self.assertTrue(
            any(
                not entry.navigation
                and entry.action_id == "explore.look"
                and entry.params == {"room": True}
                for entry in vocabulary
            )
        )


class WildernessExplorationPresenterTests(EvenniaTestCase):
    """Wilderness move rows advertise canonical arrival nodes (fix-wilderness-web-navigation)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        cls._north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()

    def setUp(self):
        self.room1 = create_object(Room, key="Room1")
        self.char1 = create_object(PlayerCharacter, key="Char", location=self.room1)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.north_gate = GridRoom.objects.get(id=self._north_gate.id)
        self.gate = [
            exit_obj
            for exit_obj in self.north_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]

    def _render(self):
        return build_production_registry().render("exploration", _context(self.char1))

    @covers_requirement("webclient-exploration-menu::exploration-move-rows-advertise-canonical-destinations")
    def test_wilderness_move_rows_advertise_canonical_destinations(self):
        from typeclasses.rooms import TerrainRoom
        from world.maps.wilderness_destination import resolve_wilderness_destination

        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        room = self.char1.location
        payload = self._render()
        self.assertTrue(payload["available"])
        rows = {row["label"]: row for row in payload["move"]}
        # The eight cardinal exits all route through the resolver.
        self.assertEqual(
            set(rows),
            {"north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"},
        )
        for direction, row in rows.items():
            expected = resolve_wilderness_destination(room, direction)
            self.assertIsNotNone(expected)
            self.assertEqual(row["destination"], expected, direction)
            self.assertTrue(row["enabled"])
            self.assertIsNone(row["disabled_reason"])
        # The gateway south row advertises the grid arrival node, not a wild cell.
        self.assertEqual(rows["south"]["destination"], "grid:capital_altoria:2:4")


if __name__ == "__main__":
    unittest.main()
