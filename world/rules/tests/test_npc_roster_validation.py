"""Data-contract test: shipped NPC persona roster validation contract

Validates that the complete shipped NPC roster satisfies all completeness,
card-validity, voice-coverage, dialogue-mapping, and inventory invariants, and
verifies through synthetic registries that every violation class is detected
and reported with its source and profile/preset identity.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from tools.spec_traceability import covers_requirement
from world.ai.director_templates import QUEST_TEMPLATE_POOL
from world.lore.dialogue.shape import DialogueDefinition, KeywordResponse
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.lore.npc_profiles.inventory import NpcSource
from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines
from world.lore.player_presets import PLAYER_PRESET_REGISTRY, StartingCompanion
from world.lore.settlements.places import PLACE_REGISTRY
from world.rules.npc_roster_validation import (
    NpcRosterError,
    derive_shipped_sources,
    validate_npc_roster,
)


def _make_valid_synthetic_universe(tmp_dir: Path):
    """Build a minimal, self-consistent synthetic universe that passes validation."""
    valid_card = NpcCard(
        identity=NpcCardIdentity(public="測試公眾身分", hidden=""),
        appearance="灰髮，穿亞麻襯衫與皮背心。",
        personality="務實且冷靜，看重承諾。",
        speech_style="語調平緩簡潔，少用多餘形容詞。",
        life_story="在王都長大，經營雜貨多年。",
        habit="說話時習慣整理案上的帳本。",
        social_connection="無特殊派系關聯。",
    )

    examiner_card = NpcCard(
        identity=NpcCardIdentity(public="公會考核官身分", hidden=""),
        appearance="身材魁梧，身穿重甲。",
        personality="嚴肅專注，不苟言笑。",
        speech_style="冷硬簡短。",
        life_story="退役冒險者，現任公會考核官。",
        habit="戰鬥時目光銳利。",
        social_connection="",
    )

    profile_registry = {
        "t_host_prof": NpcProfile(
            key="t_host_prof",
            card=valid_card,
            age=40,
            apparent_age=40,
            voice=NpcVoiceLines(greeting=None, misunderstood="「我聽不懂你在說什麼。」"),
        ),
        "t_examiner_prof": NpcProfile(
            key="t_examiner_prof",
            card=examiner_card,
            age=35,
            apparent_age=35,
            voice=NpcVoiceLines(greeting=None, misunderstood=None),
        ),
    }

    base_place = PLACE_REGISTRY["altoria_general_store"]
    places = {
        "t_shop": replace(
            base_place,
            key="t_shop",
            service_id="t_shop_service",
            authored_kwargs=(
                ("shop_key", "t_shop"),
                ("dialogue_key", "t_dialogue"),
            ),
            host_profile_key="t_host_prof",
        )
    }

    dialogue_rows = {
        "t_dialogue": DialogueDefinition(
            greeting="「歡迎光臨，客人。」",
            responses=(KeywordResponse("買賣", "「要買什麼請看架上。」"),),
        )
    }

    base_rank = GUILD_RANK_REGISTRY["F"]
    guild_ranks = {
        "F": replace(
            base_rank,
            examiner_title="公會考核官",
            examiner_profile_key="t_examiner_prof",
        )
    }

    base_preset = PLAYER_PRESET_REGISTRY["yuna_darknight"]
    player_presets = {
        "t_player": replace(
            base_preset,
            key="t_player",
            starting_companions=(StartingCompanion("t_companion", 50, "同伴"),),
        ),
        "t_companion": replace(
            base_preset,
            key="t_companion",
            starting_companions=(),
            persona=replace(
                base_preset.persona,
                speech_style="語氣簡明沉穩",
                greeting="「隨時可以出發。」",
            ),
        ),
    }

    base_template = QUEST_TEMPLATE_POOL[0]
    quest_templates = (replace(base_template, name="測試討伐任務"),)

    # Shipped import example in tmp_dir
    import world.imports.examples as _examples_pkg
    real_example = Path(_examples_pkg.__file__).resolve().parent / "example_character.json"
    example_path = tmp_dir / "example_character.json"
    example_path.write_text(real_example.read_text(encoding="utf-8"), encoding="utf-8")

    derived = derive_shipped_sources(
        places=places,
        dialogue_rows=dialogue_rows,
        guild_ranks=guild_ranks,
        player_presets=player_presets,
        quest_templates=quest_templates,
        examples_dir=tmp_dir,
    )
    inventory = tuple(NpcSource(kind=kind, key=key, owner="test_slice") for kind, key in sorted(derived))

    return {
        "places": places,
        "dialogue_rows": dialogue_rows,
        "guild_ranks": guild_ranks,
        "player_presets": player_presets,
        "quest_templates": quest_templates,
        "examples_dir": tmp_dir,
        "profile_registry": profile_registry,
        "inventory": inventory,
    }


class ShippedNpcRosterContractTests(unittest.TestCase):
    """The live, shipped NPC roster validates clean against all authoring contracts."""

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_shipped_roster_validates_clean(self):
        validate_npc_roster(quest_templates=QUEST_TEMPLATE_POOL)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_shipped_sources_match_inventory(self):
        from world.lore.npc_profiles.inventory import NPC_SOURCE_INVENTORY

        derived = derive_shipped_sources(quest_templates=QUEST_TEMPLATE_POOL)
        inv_pairs = {(r.kind, r.key) for r in NPC_SOURCE_INVENTORY}
        self.assertEqual(derived, frozenset(inv_pairs))


class SyntheticNpcRosterValidationTests(unittest.TestCase):
    """Synthetic registries exercise every violation class individually and in combination."""

    def setUp(self):
        self.tmp_dir_obj = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir_obj.name)
        self.synth = _make_valid_synthetic_universe(self.tmp_path)

    def tearDown(self):
        self.tmp_dir_obj.cleanup()

    def test_valid_synthetic_universe_passes(self):
        validate_npc_roster(**self.synth)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_missing_place_profile_is_reported(self):
        broken_place = replace(self.synth["places"]["t_shop"], host_profile_key="unregistered_prof")
        self.synth["places"] = {"t_shop": broken_place}

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("place_host", msg)
        self.assertIn("t_shop_service", msg)
        self.assertIn("unregistered_prof", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_invalid_place_profile_card_is_reported(self):
        invalid_card = replace(self.synth["profile_registry"]["t_host_prof"].card, personality="")
        broken_prof = replace(self.synth["profile_registry"]["t_host_prof"], card=invalid_card)
        self.synth["profile_registry"]["t_host_prof"] = broken_prof

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("place_host", msg)
        self.assertIn("t_shop_service", msg)
        self.assertIn("t_host_prof", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_examiner_missing_profile_is_reported(self):
        broken_rank = replace(self.synth["guild_ranks"]["F"], examiner_profile_key="unregistered_exam")
        self.synth["guild_ranks"] = {"F": broken_rank}

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("guild_examiner", msg)
        self.assertIn("F", msg)
        self.assertIn("unregistered_exam", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_examiner_with_voice_lines_is_reported(self):
        voiced_prof = replace(
            self.synth["profile_registry"]["t_examiner_prof"],
            voice=NpcVoiceLines(greeting="「來領教我的鐵拳吧。」", misunderstood=None),
        )
        self.synth["profile_registry"]["t_examiner_prof"] = voiced_prof

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("guild_examiner", msg)
        self.assertIn("F", msg)
        self.assertIn("examiners do not speak", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_dialogue_table_answered_by_zero_hosts_is_reported(self):
        self.synth["dialogue_rows"]["orphan_table"] = DialogueDefinition(
            greeting="「無人看守。」", responses=()
        )
        self.synth["inventory"] = (
            *self.synth["inventory"],
            NpcSource(kind="dialogue_table", key="orphan_table", owner="test_slice"),
        )

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("dialogue_table", msg)
        self.assertIn("orphan_table", msg)
        self.assertIn("0 hosted places", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_dialogue_table_answered_by_multiple_hosts_is_reported(self):
        second_place = replace(
            self.synth["places"]["t_shop"],
            key="t_shop_2",
            service_id="t_shop_2_service",
            host_profile_key="t_host_prof",
        )
        self.synth["places"]["t_shop_2"] = second_place
        self.synth["inventory"] = (
            *self.synth["inventory"],
            NpcSource(kind="place_host", key="t_shop_2_service", owner="test_slice"),
        )

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("dialogue_table", msg)
        self.assertIn("t_dialogue", msg)
        self.assertIn("hosted places", msg)
        self.assertIn("t_shop_service", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_unknown_dialogue_table_referenced_by_place_is_reported(self):
        broken_place = replace(
            self.synth["places"]["t_shop"],
            authored_kwargs=(("dialogue_key", "nonexistent_table"),),
        )
        self.synth["places"]["t_shop"] = broken_place

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("place_host", msg)
        self.assertIn("t_shop_service", msg)
        self.assertIn("unknown dialogue table", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_scripted_host_missing_misunderstood_is_reported(self):
        mute_prof = replace(
            self.synth["profile_registry"]["t_host_prof"],
            voice=NpcVoiceLines(greeting=None, misunderstood=None),
        )
        self.synth["profile_registry"]["t_host_prof"] = mute_prof

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("place_host", msg)
        self.assertIn("t_shop_service", msg)
        self.assertIn("t_host_prof", msg)
        self.assertIn("missing misunderstood", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_scripted_host_authoring_greeting_is_reported(self):
        drifting_prof = replace(
            self.synth["profile_registry"]["t_host_prof"],
            voice=NpcVoiceLines(greeting="「私自設定問候語。」", misunderstood="「聽不懂。」"),
        )
        self.synth["profile_registry"]["t_host_prof"] = drifting_prof

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("place_host", msg)
        self.assertIn("t_shop_service", msg)
        self.assertIn("t_host_prof", msg)
        self.assertIn("authors a greeting", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_companion_partner_preset_missing_speech_style_is_reported(self):
        comp = self.synth["player_presets"]["t_companion"]
        broken_persona = replace(comp.persona, speech_style="")
        self.synth["player_presets"]["t_companion"] = replace(comp, persona=broken_persona)

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("starting_companion", msg)
        self.assertIn("t_player:t_companion", msg)
        self.assertIn("t_companion", msg)
        self.assertIn("missing speech_style", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_companion_partner_preset_missing_greeting_is_reported(self):
        comp = self.synth["player_presets"]["t_companion"]
        broken_persona = replace(comp.persona, greeting="")
        self.synth["player_presets"]["t_companion"] = replace(comp, persona=broken_persona)

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("starting_companion", msg)
        self.assertIn("t_player:t_companion", msg)
        self.assertIn("t_companion", msg)
        self.assertIn("missing greeting", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_companion_unregistered_partner_preset_is_reported(self):
        player = self.synth["player_presets"]["t_player"]
        broken_player = replace(
            player,
            starting_companions=(StartingCompanion("ghost_partner", 50, "旅伴"),),
        )
        self.synth["player_presets"]["t_player"] = broken_player
        self.synth["inventory"] = tuple(
            NpcSource(kind=r.kind, key=("t_player:ghost_partner" if r.key == "t_player:t_companion" else r.key), owner=r.owner)
            for r in self.synth["inventory"]
        )

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("starting_companion", msg)
        self.assertIn("ghost_partner", msg)
        self.assertIn("is not registered", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_companion_partner_preset_card_budget_overflow_is_reported(self):
        comp = self.synth["player_presets"]["t_companion"]
        overlong_persona = replace(comp.persona, personality="長" * 1950)
        self.synth["player_presets"]["t_companion"] = replace(comp, persona=overlong_persona)

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("starting_companion", msg)
        self.assertIn("t_player:t_companion", msg)
        self.assertIn("derived card violates contract", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_quest_template_occupant_missing_persona_is_reported(self):
        broken_req = replace(self.synth["quest_templates"][0].stages[0].npc_reqs[0], persona=None)
        broken_stage = replace(self.synth["quest_templates"][0].stages[0], npc_reqs=(broken_req,))
        broken_template = replace(self.synth["quest_templates"][0], stages=(broken_stage,))
        self.synth["quest_templates"] = (broken_template,)

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("quest_template_occupant", msg)
        self.assertIn("has no persona", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_quest_template_occupant_invalid_card_is_reported(self):
        invalid_card = replace(
            self.synth["quest_templates"][0].stages[0].npc_reqs[0].persona,
            appearance="",
        )
        broken_req = replace(self.synth["quest_templates"][0].stages[0].npc_reqs[0], persona=invalid_card)
        broken_stage = replace(self.synth["quest_templates"][0].stages[0], npc_reqs=(broken_req,))
        broken_template = replace(self.synth["quest_templates"][0], stages=(broken_stage,))
        self.synth["quest_templates"] = (broken_template,)

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("quest_template_occupant", msg)
        self.assertIn("invalid compact card", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_quest_template_occupant_characterization_error_is_reported(self):
        broken_req = replace(self.synth["quest_templates"][0].stages[0].npc_reqs[0], age=-5)
        broken_stage = replace(self.synth["quest_templates"][0].stages[0], npc_reqs=(broken_req,))
        broken_template = replace(self.synth["quest_templates"][0], stages=(broken_stage,))
        self.synth["quest_templates"] = (broken_template,)

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("quest_template_occupant", msg)
        self.assertIn("characterization error", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_import_example_invalid_json_is_reported(self):
        bad_json = self.tmp_path / "bad_example.json"
        bad_json.write_text("{malformed: json", encoding="utf-8")
        self.synth["inventory"] = (
            *self.synth["inventory"],
            NpcSource(kind="import_example", key="bad_example", owner="test_slice"),
        )

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("import_example", msg)
        self.assertIn("bad_example", msg)
        self.assertIn("failed to load JSON", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_import_example_validation_failure_is_reported(self):
        bad_char = self.tmp_path / "bad_char.json"
        bad_char.write_text(json.dumps({"schema_version": 1, "record_type": "character", "key": "壞卡"}), encoding="utf-8")
        self.synth["inventory"] = (
            *self.synth["inventory"],
            NpcSource(kind="import_example", key="bad_char", owner="test_slice"),
        )

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("import_example", msg)
        self.assertIn("bad_char", msg)
        self.assertIn("validation failed", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_orphan_profile_is_reported(self):
        self.synth["profile_registry"]["t_orphan_prof"] = NpcProfile(
            key="t_orphan_prof",
            card=self.synth["profile_registry"]["t_host_prof"].card,
            age=30,
            apparent_age=30,
            voice=NpcVoiceLines(greeting=None, misunderstood=None),
        )

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("orphan profile", msg)
        self.assertIn("t_orphan_prof", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_inventory_missing_source_is_reported(self):
        dropped = self.synth["inventory"][0]
        self.synth["inventory"] = self.synth["inventory"][1:]

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn(dropped.kind, msg)
        self.assertIn(dropped.key, msg)
        self.assertIn("missing from inventory", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_inventory_stale_source_is_reported(self):
        ghost_source = NpcSource(kind="place_host", key="ghost_service_id", owner="test_slice")
        self.synth["inventory"] = (*self.synth["inventory"], ghost_source)

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("ghost_service_id", msg)
        self.assertIn("missing from registries", msg)

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_multiple_violations_reported_together(self):
        # Cause 1: inventory stale row
        ghost_source = NpcSource(kind="place_host", key="ghost_service", owner="test_slice")
        self.synth["inventory"] = (*self.synth["inventory"], ghost_source)

        # Cause 2: invalid template card
        invalid_card = replace(
            self.synth["quest_templates"][0].stages[0].npc_reqs[0].persona,
            personality="",
        )
        broken_req = replace(self.synth["quest_templates"][0].stages[0].npc_reqs[0], persona=invalid_card)
        broken_stage = replace(self.synth["quest_templates"][0].stages[0], npc_reqs=(broken_req,))
        broken_template = replace(self.synth["quest_templates"][0], stages=(broken_stage,))
        self.synth["quest_templates"] = (broken_template,)

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)

        violations = caught.exception.violations
        self.assertGreaterEqual(len(violations), 2)
        has_inv = any("ghost_service" in v for v in violations)
        has_template = any("quest_template_occupant" in v for v in violations)
        self.assertTrue(has_inv, f"Expected inventory violation in {violations}")
        self.assertTrue(has_template, f"Expected template violation in {violations}")

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts"
    )
    def test_one_shot_quest_template_iterator_validates_occupants(self):
        invalid_card = replace(
            self.synth["quest_templates"][0].stages[0].npc_reqs[0].persona,
            personality="",
        )
        broken_req = replace(self.synth["quest_templates"][0].stages[0].npc_reqs[0], persona=invalid_card)
        broken_stage = replace(self.synth["quest_templates"][0].stages[0], npc_reqs=(broken_req,))
        broken_template = replace(self.synth["quest_templates"][0], stages=(broken_stage,))
        self.synth["quest_templates"] = iter([broken_template])

        with self.assertRaises(NpcRosterError) as caught:
            validate_npc_roster(**self.synth)
        msg = str(caught.exception)
        self.assertIn("quest_template_occupant", msg)
        self.assertIn("invalid compact card", msg)
