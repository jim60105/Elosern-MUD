"""Runtime immutability acceptance (tasks 1.3 / 6.1).

Establishes the delta requirement "Two-layer immutable inspection acceptance"
at runtime: reading every entity kind through the list/detail/raw/search
routes, the narrative tabs and the recall preview must leave every inspected
object's stored Attribute rows and every narrative table row byte-identical —
row counts *and* stored values, not just counts — with missing-Attribute
fixtures exercising the indirect autocreation risk. The baseline is taken after
the fixtures are built and asserted before any teardown, so no transaction
rollback can mask a write. Facade events and in-process recall caches are
permitted; domain writes are not. The ``gm-runtime-state::*`` requirement IDs
this module covers enter the traceability index when the change's delta spec is
synced at archive.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps
from evennia.objects.models import ObjectDB
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.art.store import ArtAssetRecord
from world.narrative.models import (
    DialogueEpoch,
    DialogueFrame,
    MemoryRecord,
    MemoryRevision,
    NarrativeContextSnapshot,
    NarrativeEvent,
)
from world.quests.runtime import QuestRecord, QuestState, read_records
from world.quests.transitions import apply_quest_log_replacement
from world.rules.monster_individual import construct_species_individual
from world.rules.traits import restore_gauges_to_full
from world.tests.synthetic_data import SYNTH_GUILD_ISSUER_KEY

from web.gm.readers import registry
from web.gm.tests._state_support import open_synthetic_scope

SYNTH_RACE = "t_duskmari"
SPECIES = "t_whisper_quail"
VARIANT = "t_whisper_quail_ordinary"
QUEST_KEY = "t_tarn_messenger"
CALL_ID = "cd" * 16

#: The kinds whose list route needs an owner filter to be answerable.
OWNER_SCOPED = {"quests", "memories", "snapshots", "dialogue"}


def _through_rows(entity: Any) -> list[tuple]:
    """The raw Attribute rows of an object/account, read via the join table."""
    through = entity.db_attributes.through.objects
    field = "objectdb_id" if isinstance(entity, ObjectDB) else "accountdb_id"
    return sorted(
        tuple(row)
        for row in through.filter(**{field: entity.pk}).values_list(
            "attribute__db_key", "attribute__db_category", "attribute__db_value"
        )
    )


def _handler_rows(entity: Any) -> list[tuple]:
    """The handler view of a script's stored Attributes (Scripts have no join)."""
    return sorted(
        (str(attribute.key), str(attribute.category or ""), repr(attribute.value))
        for attribute in entity.attributes.all()
    )


def _narrative_snapshot() -> dict[str, list]:
    """Every narrative table's stored rows, values included."""
    snapshot: dict[str, list] = {}
    for model in apps.get_app_config("narrative").get_models():
        rows = list(model.objects.order_by("pk").values())
        snapshot[model.__name__] = rows
    return snapshot


class RuntimeImmutabilityTest(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "items",
            "monster_species",
            "monster_variants",
            "monster_tiers",
            "ambient_placements",
            "monster_sites",
            "quest_definitions",
            "quest_issuances",
        )
        super().setUp()
        self.player = self._character("t_imm_player")
        self.owner = self._character("t_imm_owner")
        # Missing stored defaults: the autocreating descriptors must stay absent.
        self.player.attributes.remove("wallet")
        self.owner.attributes.remove("wallet")
        self.npc = create.create_object(NPC, key="t_imm_npc", location=self.room1)
        self.npc.race = SYNTH_RACE
        self.npc.apply_race_baseline()
        restore_gauges_to_full(self.npc)
        self.npc.attributes.remove("wallet")
        self.monster = construct_species_individual(SPECIES, VARIANT)
        self.monster.traits.mp.base = 10
        self.monster.traits.sp.base = 10
        self.monster.traits.mp.current = 10
        self.monster.traits.sp.current = 10
        self.room = create.create_object(Room, key="t_imm_room")
        self.art = create.create_script(ArtAssetRecord, key="art:t_imm_subject")
        self.art.db.subject_key = "t_imm_subject"
        self.event = NarrativeEvent.objects.create(
            source_id="t_imm_event", event_type="t_imm_kind", content={"note": "合成"}
        )
        self.record = QuestRecord(
            quest_id=f"{QUEST_KEY}:1",
            definition_key=QUEST_KEY,
            issuer_key=SYNTH_GUILD_ISSUER_KEY,
            state=QuestState.IN_PROGRESS,
            stage_index=0,
            stage_progress=0,
            deadline_tick=None,
            accepted_tick=0,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
        )
        apply_quest_log_replacement(self.owner, [self.record])
        self.memory = self._memory()
        self.snapshot = self._snapshot()
        self._dialogue()

    # --- fixtures ---------------------------------------------------------

    def _character(self, key: str) -> PlayerCharacter:
        character = create.create_object(PlayerCharacter, key=key, location=self.room1)
        character.race = SYNTH_RACE
        character.apply_race_baseline()
        restore_gauges_to_full(character)
        return character

    def _memory(self) -> MemoryRecord:
        record = MemoryRecord.objects.create(
            owner_id=str(self.npc.pk),
            tick=1,
            category="observation",
            content={"note": "合成記憶"},
            subjects=["t_imm_subject"],
        )
        MemoryRevision.objects.create(record=record, revision_number=1)
        return record

    def _snapshot(self) -> NarrativeContextSnapshot:
        return NarrativeContextSnapshot.objects.create(
            snapshot_id="t_imm_snapshot",
            capability="t_imm_capability",
            prompt_version="t_imm_v1",
            rendering_version="t_imm_v1",
            owner_id=str(self.npc.pk),
            rendered_payload={"sections": [], "call_id": CALL_ID},
            sources=[{"source_id": "t_imm_event"}],
        )

    def _dialogue(self) -> DialogueEpoch:
        epoch = DialogueEpoch.objects.create(
            npc_id=str(self.npc.pk),
            player_id=str(self.player.pk),
            sequence=1,
            version="t_imm_v1",
            reason="t_imm_reason",
            generation_id="t_imm_generation",
            source_refs=[],
        )
        DialogueFrame.objects.create(
            epoch=epoch,
            identity="t_imm_frame",
            content="合成對話",
            tick=1,
            sources=[{"call_id": CALL_ID}],
        )
        return epoch

    # --- the inspection surface ------------------------------------------

    def _inspect_everything(self) -> None:
        for kind in registry.KIND_ORDER:
            filters: dict[str, Any] = {}
            if kind == "narrative":
                filters["subtype"] = "event"
            if kind in OWNER_SCOPED:
                filters["owner"] = f"#{self.npc.pk}"
            registry.build_list(kind, filters)
            registry.build_list(kind, dict(filters, generated="true"))
        registry.detail("characters", str(self.player.pk), {})
        registry.detail("characters", str(self.owner.pk), {})
        registry.detail("npcs", str(self.npc.pk), {})
        registry.detail("monsters", str(self.monster.pk), {})
        registry.detail("rooms", str(self.room.pk), {})
        registry.detail("art", "art:t_imm_subject", {})
        registry.detail("narrative", "event:t_imm_event", {})
        registry.detail("quests", self.record.quest_id, {"owner": f"#{self.owner.pk}"})
        registry.detail("memories", str(self.memory.pk), {"owner": f"#{self.npc.pk}"})
        registry.detail("snapshots", self.snapshot.snapshot_id, {"owner": f"#{self.npc.pk}"})
        registry.detail("dialogue", str(self.player.pk), {"owner": f"#{self.npc.pk}"})
        registry.raw_object(str(self.room1.pk))
        registry.raw_object(str(self.npc.pk))
        registry.raw_object(str(self.account.pk))
        registry.search_items("#%d" % self.npc.pk)
        registry.search_items("t_imm")
        for body in ({"query": "合成"}, {"query": "合成", "include_superseded": True}):
            registry.recall_preview(f"#{self.npc.pk}", body)

    # --- the assertions ---------------------------------------------------

    def test_the_whole_inspection_surface_is_immutable(self):
        before = {
            "player": _through_rows(self.player),
            "owner": _through_rows(self.owner),
            "npc": _through_rows(self.npc),
            "monster": _through_rows(self.monster),
            "room": _through_rows(self.room),
            "art": _handler_rows(self.art),
            "narrative": _narrative_snapshot(),
        }
        self._inspect_everything()
        self.assertEqual(_through_rows(self.player), before["player"])
        self.assertEqual(_through_rows(self.owner), before["owner"])
        self.assertEqual(_through_rows(self.npc), before["npc"])
        self.assertEqual(_through_rows(self.monster), before["monster"])
        self.assertEqual(_through_rows(self.room), before["room"])
        self.assertEqual(_handler_rows(self.art), before["art"])
        after = _narrative_snapshot()
        self.assertEqual(sorted(after), sorted(before["narrative"]))
        for model_name, rows in before["narrative"].items():
            with self.subTest(model=model_name):
                self.assertEqual(after[model_name], rows)

    def test_missing_stored_defaults_stay_missing(self):
        self._inspect_everything()
        for entity in (self.player, self.owner, self.npc):
            with self.subTest(entity=entity.key):
                self.assertIsNone(entity.attributes.get("wallet", default=None))
        self.assertIn("t_imm_room", self.room.key)
        self.assertIsNone(self.npc.attributes.get("schedule", default=None))
        self.assertIsNone(self.monster.attributes.get("behaviour_tree", default=None))

    def test_a_second_pass_reports_the_same_state(self):
        first = _narrative_snapshot()
        self._inspect_everything()
        self._inspect_everything()
        self.assertEqual(_narrative_snapshot(), first)
        self.assertEqual(read_records(self.owner)[0].quest_id, self.record.quest_id)
