"""Data-contract test: import schema, validation, loader, and profile social identity producers."""

import json
import tempfile
from pathlib import Path

from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.npcs import NPC
from world.imports.loader import load_batch
from world.imports.validate import validate_character
from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.lore.npc_profiles.shape import NpcProfile
from world.lore.player_presets.vocab import PlayerPreset
from world.rules.social_identity import read_social_identities


class ImportSocialIdentitiesTests(EvenniaTestCase):
    """Test import schema, validation, loader persistence and producer assignments."""

    def _sample_valid_record(self, **kwargs) -> dict:
        base = {
            "record_type": "character",
            "schema_version": 1,
            "key": "test_social_npc",
            "display_name": "測試身分者",
            "title": "測試職稱",
            "age": 30,
            "apparent_age": 30,
            "race": "human",
            "subrace": "human_noble",
            "sex": "other",
            "stats": {"hp": 100},
            "disguised_stats": {},
            "skills": [],
            "passives": [],
            "equipment": {},
            "inventory": [],
            "sexual_baseline": {
                "arousal": "平靜",
                "virgin": True,
                "sensitivity": {"general": "普通"},
            },
            "persona": {
                "identity": {"public": "測試用NPC身分", "hidden": ""},
                "appearance": "普通外貌",
                "personality": "隨和",
                "speech_style": "平淡",
                "life_story": "生於王都",
                "habit": "散步",
                "social_connection": "",
            },
        }
        base.update(kwargs)
        return base

    def test_import_validation_accepts_valid_social_identities(self):
        """Optional social_identities passes validation when containing valid keys."""
        record = self._sample_valid_record(social_identities=["clergy", "official"])
        report = validate_character(record, typeclass=NPC)
        self.assertTrue(report.is_valid, report.rejections)

    def test_import_validation_rejects_unknown_keys(self):
        """Unknown social identity key causes validation rejection."""
        record = self._sample_valid_record(social_identities=["clergy", "invented_king"])
        report = validate_character(record, typeclass=NPC)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(iss.field == "social_identities" for iss in report.rejections))

    def test_import_validation_rejects_duplicates_or_exceeding_max(self):
        """Duplicate keys or >8 keys fail validation."""
        record_dup = self._sample_valid_record(social_identities=["noble", "noble"])
        report_dup = validate_character(record_dup, typeclass=NPC)
        self.assertFalse(report_dup.is_valid)

        record_excess = self._sample_valid_record(
            social_identities=["noble", "clergy", "official", "adventurer", "noble", "k6", "k7", "k8", "k9"]
        )
        report_excess = validate_character(record_excess, typeclass=NPC)
        self.assertFalse(report_excess.is_valid)

    def test_import_validation_rejects_boolean_or_non_strings(self):
        """Non-string or boolean items in social_identities fail validation."""
        record_bool = self._sample_valid_record(social_identities=[True])
        report_bool = validate_character(record_bool, typeclass=NPC)
        self.assertFalse(report_bool.is_valid)

    def test_loader_instantiates_and_persists_social_identities(self):
        """Imported social_identities are persisted into entity.db.social_identities and readable."""
        record = self._sample_valid_record(
            key="test_imported_clergy",
            social_identities=["clergy"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_char.json"
            file_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            created_entities = load_batch([file_path], typeclass=NPC)
            self.assertEqual(len(created_entities), 1)
            created = created_entities[0]
            self.assertEqual(read_social_identities(created), frozenset({"clergy"}))

    def test_profile_shape_validation_and_producer_mapping(self):
        """NpcProfile validates social_identities and shipped producers have typed identities."""
        from world.lore.npc_profiles import NPC_PROFILE_REGISTRY

        guild_master = NPC_PROFILE_REGISTRY["altoria_guild_master"]
        self.assertEqual(guild_master.social_identities, ("official",))

        guard_captain = NPC_PROFILE_REGISTRY["altoria_guard_captain"]
        self.assertEqual(guard_captain.social_identities, ("official",))

        high_priestess = NPC_PROFILE_REGISTRY["altoria_high_priestess"]
        self.assertEqual(high_priestess.social_identities, ("clergy",))

        sanctum_deacon = NPC_PROFILE_REGISTRY["altoria_sanctum_deacon"]
        self.assertEqual(sanctum_deacon.social_identities, ("clergy",))

        watch_captain = NPC_PROFILE_REGISTRY["altoria_noble_watch_captain"]
        self.assertEqual(watch_captain.social_identities, ("official",))

        # Other profiles remain empty by default
        eatery_owner = NPC_PROFILE_REGISTRY["altoria_eatery_owner"]
        self.assertEqual(eatery_owner.social_identities, ())
