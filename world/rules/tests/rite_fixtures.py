"""One synthetic landmark rite world shared by the rules, action and command suites.

Every identifier and prose value is invented with the reserved ``t_`` prefix
(test-data gate), so no test importing this fixture names shipped content. The
fixture installs one frozen rite snapshot over the synthetic grid map, places
the player on the district's landmark node, and joins one present companion, so
a settlement, an action delivery and a text command all observe the same world.

The scenes are shared authored values: the solo option's self scene carries the
literal ``{name}`` placeholder on purpose, and the shared option's watch scene
carries it as the companion-name substitution the watch perspective performs.
"""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace as NS
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.dbserialize import deserialize
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from world.lore.rites import installed
from world.lore.rites.shape import RiteArchetype, RiteOption, RiteSnapshot
from world.lore.scenes import Narration, Scene, Speech
from world.rules.clock import get_world_clock
from world.rules.landmark_rite_record import RECORD_ATTR
from world.rules.landmark_rites import REFUSAL_MESSAGES, RiteRefused, perform_rite
from world.rules.map_knowledge import node_id_for
from world.rules.party import join_party
from world.tests.geography_fixture import publish_shipped_geography
from world.tests.synthetic_grid_map import load_synthetic_grid, synthetic_rooms

publish_shipped_geography()

DISTRICT_KEY = "t_district"
ARCHETYPE_KEY = "t_archetype"
GUARDIAN_NAME = "測試守護"
GUARDIAN_FORM = "測試形體"
DISTRICT_NAME = "測試丘陵"
LANDMARK_NAME = "測試碑"
SOLO_SECONDS = 120
SHARED_SECONDS = 300
SOLO_SHAME = 1
SOLO_EXPOSURE = 2
SHARED_SHAME = 2
SHARED_EXPOSURE = 1


def _scene(scene_id: str, *lines: Any) -> Scene:
    """One synthetic authored scene; a lone narration when no lines are given."""
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=lines or (Narration(text="測試敘述。"),),
    )


SOLO = RiteOption(
    key="solo",
    label_zh="獨自",
    seconds=SOLO_SECONDS,
    shame=SOLO_SHAME,
    exposure=SOLO_EXPOSURE,
    # The self perspective never substitutes ``{name}``: it stays literal.
    self_scene=_scene(
        "t_rite.solo.self",
        Narration(text="測試敘述。"),
        Speech(speaker="actor", text="測試自語。"),
        Speech(speaker="host", text="測試守護對{name}說話。"),
    ),
    watch_scene=None,
)
SHARED = RiteOption(
    key="shared",
    label_zh="共行",
    seconds=SHARED_SECONDS,
    shame=SHARED_SHAME,
    exposure=SHARED_EXPOSURE,
    self_scene=_scene("t_rite.shared.self"),
    # The watch perspective substitutes ``{name}`` with the performing body.
    watch_scene=_scene(
        "t_rite.shared.watch",
        Narration(text="測試旁觀敘述。"),
        Speech(speaker="actor", text="測試同伴之語。"),
        Speech(speaker="host", text="測試守護對{name}說話。"),
    ),
)
SNAPSHOT = RiteSnapshot(
    archetypes={
        ARCHETYPE_KEY: RiteArchetype(
            key=ARCHETYPE_KEY,
            guardian_name_zh=GUARDIAN_NAME,
            guardian_form_zh=GUARDIAN_FORM,
            options=(SOLO, SHARED),
        )
    },
    districts={DISTRICT_KEY: ARCHETYPE_KEY},
)


class RiteSettlementFixture(EvenniaTest):
    """One synthetic landmark, one synthetic rite world, one present companion."""

    #: The rite snapshot this fixture installs; a subclass may install its own.
    snapshot = SNAPSHOT

    def setUp(self):
        super().setUp()
        load_synthetic_grid()
        self.source, self.landmark, self.end = synthetic_rooms()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.landmark
        self.district = NS(
            district_id=DISTRICT_KEY,
            district_name_zh=DISTRICT_NAME,
            landmark_name_zh=LANDMARK_NAME,
        )
        self.district_snapshot = NS(districts={DISTRICT_KEY: self.district})
        self.landmark_node = node_id_for(self.landmark)
        self.enterContext(
            patch(
                "world.lore.map_districts.current",
                new=lambda: self.district_snapshot,
            )
        )
        self.enterContext(
            patch(
                "world.lore.map_districts.landmark_node_ids",
                side_effect=lambda *args, **kwargs: {
                    DISTRICT_KEY: self.landmark_node
                },
            )
        )
        self.enterContext(installed(self.snapshot))
        self.companion = self._companion("測試同伴")
        self.assertNotEqual(self.player.pk, self.companion.pk)

    def _companion(self, key: str, location: Any = None):
        npc = create_object(NPC, key=key, location=self.player.location)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        if location is not None:
            npc.location = location
        return npc

    def perform(self, *args: Any, **kwargs: Any):
        """Perform one rite, delivering its commit callbacks first."""
        with self.captureOnCommitCallbacks(execute=True):
            return perform_rite(*args, **kwargs)

    def record(self) -> Any:
        raw = self.player.attributes.get(RECORD_ATTR)
        return None if raw is None else deserialize(raw)

    def sexual_state(self, entity: Any) -> tuple[Any, ...]:
        return (
            entity.sexual.pleasure.value,
            entity.sexual.climax_phase.level,
            entity.sexual.climax_today,
            entity.sexual.climax_turns,
            entity.sexual.shame.value,
            entity.sexual.exposure.value,
        )

    def world_state(self, actor: Any = None) -> tuple[Any, ...]:
        """The refused-request snapshot: world tick, record and sexual state."""
        actor = self.player if actor is None else actor
        return (
            get_world_clock().tick,
            deepcopy(self.record()),
            self.sexual_state(actor),
        )

    def assert_unchanged(self, before: tuple[Any, ...], actor: Any = None) -> None:
        """Assert one request left the shared world exactly as it found it."""
        self.assertEqual(self.world_state(actor), before)

    def refused(
        self,
        code: str,
        call: Any,
        *,
        actor: Any = None,
        char: Any = None,
        district: Any = None,
    ) -> RiteRefused:
        """Assert one refusal wrote nothing and logged exactly one refused event."""
        actor = self.player if actor is None else actor
        before = self.world_state(actor)
        with patch("world.rules.landmark_rites.log_info") as info:
            with self.assertRaises(RiteRefused) as caught:
                call()
        refusal = caught.exception
        self.assertEqual(refusal.code, code)
        self.assertEqual(refusal.message, REFUSAL_MESSAGES[code])
        self.assert_unchanged(before, actor)
        self.assertEqual(info.call_count, 1)
        self.assertEqual(info.call_args.args[0], "landmark_rite_refused")
        context = info.call_args.kwargs["context"]
        self.assertEqual(context["reason"], code)
        if char is not None:
            self.assertEqual(context["char"], char)
        if district is not None:
            self.assertEqual(context["district"], district)
        return refusal