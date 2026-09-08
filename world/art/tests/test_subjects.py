"""Tests for the art subject model (pure, no database)."""

from unittest.mock import Mock, patch
import unittest

from evennia.utils.test_resources import EvenniaTestCase

from world.prompts.tests.fixtures import PromptFixture

from world.art import subjects
from world.art.subjects import (
    DIGITS_ONLY_KEY_PATTERN,
    FORBIDDEN_SUBJECT_KEY_CHARACTERS,
    MAX_SUBJECT_KEY_BYTES,
    MAX_SUBJECT_KEY_LENGTH,
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    character_description,
    character_subject_for,
    description_for,
    is_reserved_player_stable_key,
    monster_description,
    monster_subject_for,
    parse_subject,
    scene_description,
    scene_subject_for,
)
from world.prompts.loader import PromptUnavailableError

from tools.spec_traceability import covers_requirement


class SubjectParsingTests(unittest.TestCase):
    @covers_requirement("art-subject-model::art-subject-keys-are-typed-namespaced-and-validated-before-queue-access")
    def test_known_kinds_parse_into_typed_subjects(self):
        cases = (
            ("scene:forest_path", ArtSubjectKind.SCENE, "forest_path"),
            ("portrait:character:42", ArtSubjectKind.CHARACTER, "42"),
            ("portrait:monster:gray_wolf", ArtSubjectKind.MONSTER, "gray_wolf"),
        )
        for full, kind, key in cases:
            subject = parse_subject(full)
            self.assertIs(subject.kind, kind)
            self.assertEqual(subject.key, key)
            self.assertEqual(subject.full(), full)

    @covers_requirement("art-subject-model::art-subject-keys-are-typed-namespaced-and-validated-before-queue-access")
    def test_malformed_keys_are_rejected(self):
        for bad in (
            "scene:",
            "scene:a:b",
            "scene:a/b",
            "scene:a|b",
            "scene:a{b",
            "scene:a}b",
            "scene:bad\x00key",
            "scene:" + "x" * (MAX_SUBJECT_KEY_LENGTH + 1),
            "portrait:character:",
            "portrait:character:a:b",
            "unknown:key",
            "scene",
            "",
        ):
            with self.subTest(full_key=bad):
                with self.assertRaises(ArtSubjectError):
                    parse_subject(bad)

    @covers_requirement("art-subject-model::art-subject-keys-are-typed-namespaced-and-validated-before-queue-access")
    def test_kind_cannot_change_while_keeping_the_same_full_key(self):
        scene = ArtSubject(ArtSubjectKind.SCENE, "k")
        character = ArtSubject(ArtSubjectKind.CHARACTER, "k")
        monster = ArtSubject(ArtSubjectKind.MONSTER, "k")
        self.assertNotEqual(scene.full(), character.full())
        self.assertNotEqual(scene.full(), monster.full())
        self.assertNotEqual(character.full(), monster.full())


class StableKeyContractTests(unittest.TestCase):
    @covers_requirement("art-stable-key-contract::stable-keys-share-one-producer-contract")
    def test_boundary_length_key_round_trips_for_every_kind(self):
        key = "x" * MAX_SUBJECT_KEY_LENGTH
        for kind in ArtSubjectKind:
            with self.subTest(kind=kind):
                subject = ArtSubject(kind, key)
                self.assertEqual(subject.full(), f"{kind.value}:{key}")
                self.assertEqual(parse_subject(subject.full()), subject)

    @covers_requirement("art-stable-key-contract::stable-keys-share-one-producer-contract")
    def test_utf8_byte_bound_keeps_worker_identities_within_name_max(self):
        # 64 four-byte characters are legal code points but 256 UTF-8 bytes;
        # the byte bound must reject them and keep the worst accepted key
        # inside the 255-byte filesystem name limit for every kind.
        key = "😀" * MAX_SUBJECT_KEY_LENGTH
        with self.assertRaises(ArtSubjectError):
            parse_subject(f"scene:{key}")
        boundary = "😀" * (MAX_SUBJECT_KEY_BYTES // 4)
        self.assertEqual(len(boundary.encode("utf-8")), MAX_SUBJECT_KEY_BYTES)
        from world.art.worker import expected_output_identity

        for kind in ArtSubjectKind:
            with self.subTest(kind=kind):
                subject = ArtSubject(kind, boundary)
                identity = expected_output_identity(subject)
                self.assertLessEqual(
                    len(identity.encode("utf-8")), 255, identity
                )
                self.assertEqual(parse_subject(subject.full()), subject)

    @covers_requirement("art-stable-key-contract::stable-keys-share-one-producer-contract")
    def test_full_wire_subject_key_always_fits_the_wire_bound(self):
        from web.webclient.presentation.art import MAX_SUBJECT_KEY

        key = "x" * MAX_SUBJECT_KEY_LENGTH
        for kind in ArtSubjectKind:
            with self.subTest(kind=kind):
                full = f"{kind.value}:{key}"
                self.assertLessEqual(len(full), MAX_SUBJECT_KEY)
        # The wire bound stays at 128; a 64-character producer key plus the
        # longest kind prefix (portrait:character:) still fits with headroom.
        self.assertEqual(MAX_SUBJECT_KEY, 128)

    @covers_requirement("art-subject-model::subject-producer-validation-rejects-unrepresentable-keys")
    def test_unrepresentable_keys_reject_with_a_named_error(self):
        for bad in (
            "a/b",
            "a|b",
            "a{b",
            "a}b",
            "x" * (MAX_SUBJECT_KEY_LENGTH + 1),
            "😀" * (MAX_SUBJECT_KEY_BYTES // 4 + 1),
        ):
            with self.subTest(key=bad[:8]):
                with self.assertRaises(ArtSubjectError):
                    character_subject_for(
                        self._character({"mode": "named", "stable_key": bad})
                    )

    @covers_requirement("art-subject-model::art-subject-keys-are-typed-namespaced-and-validated-before-queue-access")
    def test_unvalidated_construction_is_rejected_at_the_dataclass(self):
        with self.assertRaises(ArtSubjectError):
            ArtSubject(ArtSubjectKind.SCENE, "a/b")
        with self.assertRaises(ArtSubjectError):
            ArtSubject(ArtSubjectKind.CHARACTER, "x" * (MAX_SUBJECT_KEY_LENGTH + 1))

    def _character(self, policy):
        character = Mock()
        character.db.portrait_policy = policy
        return character


class RegistryResolutionTests(unittest.TestCase):
    @covers_requirement("art-subject-model::scene-and-generic-monster-subjects-resolve-from-immutable-registries")
    def test_registered_archetypes_resolve(self):
        subject = scene_subject_for("tavern_interior")
        self.assertEqual(subject.full(), "scene:tavern_interior")
        monster = monster_subject_for("low")
        self.assertEqual(monster.full(), "portrait:monster:low")

    @covers_requirement("art-subject-model::scene-and-generic-monster-subjects-resolve-from-immutable-registries")
    def test_unknown_archetypes_are_rejected(self):
        for bad in ("not_a_scene", "", "unknown_monster"):
            with self.subTest(bad=bad):
                with self.assertRaises(ArtSubjectError):
                    scene_subject_for(bad)
                with self.assertRaises(ArtSubjectError):
                    monster_subject_for(bad)


class ReservedPlayerStableKeyTests(unittest.TestCase):
    @covers_requirement("art-stable-key-contract::the-character-portrait-keyspace-reserves-the-digit-only-region-for-player-characters")
    def test_digit_only_keys_are_reserved(self):
        for key in ("42", "7", "0", "042", "12345678901234567890"):
            with self.subTest(key=key):
                self.assertTrue(is_reserved_player_stable_key(key), key)

    @covers_requirement("art-stable-key-contract::the-character-portrait-keyspace-reserves-the-digit-only-region-for-player-characters")
    def test_non_digit_keys_are_not_reserved(self):
        for key in (
            "forest_bandit_chief",
            "library_keeper",
            "bandit_02",
            "a1b2c3",
            "_42",
            "42_",
        ):
            with self.subTest(key=key):
                self.assertFalse(is_reserved_player_stable_key(key), key)

    @covers_requirement("art-stable-key-contract::the-character-portrait-keyspace-reserves-the-digit-only-region-for-player-characters")
    def test_empty_and_whitespace_keys_are_not_reserved(self):
        for key in ("", "   ", "\t42\n"):
            with self.subTest(key=key):
                self.assertFalse(is_reserved_player_stable_key(key), key)

    @covers_requirement("art-stable-key-contract::the-character-portrait-keyspace-reserves-the-digit-only-region-for-player-characters")
    def test_unicode_digits_are_not_reserved(self):
        # Full-width digits cannot equal an ASCII pk string, so they stay
        # legal for non-player producers (design D1).
        for key in ("０４２", "١٢٣", "42٠"):
            with self.subTest(key=key):
                self.assertFalse(is_reserved_player_stable_key(key), key)

    @covers_requirement("art-stable-key-contract::the-character-portrait-keyspace-reserves-the-digit-only-region-for-player-characters")
    def test_pattern_constant_is_the_ascii_digits_class(self):
        self.assertEqual(DIGITS_ONLY_KEY_PATTERN, r"[0-9]+")


class PortraitPolicyTests(EvenniaTestCase):
    def _character(self, policy):
        character = Mock()
        character.db.portrait_policy = policy
        return character

    @covers_requirement("art-subject-model::named-character-portrait-eligibility-is-explicit-policy-never-inferred")
    def test_explicit_named_policy_yields_a_unique_subject(self):
        subject = character_subject_for(self._character(
            {"mode": "named", "stable_key": "42"}
        ))
        self.assertEqual(subject.full(), "portrait:character:42")

    @covers_requirement("art-subject-model::named-character-portrait-eligibility-is-explicit-policy-never-inferred")
    def test_no_named_policy_produces_no_unique_portrait(self):
        self.assertIsNone(character_subject_for(self._character(None)))
        self.assertIsNone(character_subject_for(self._character({"mode": "generic"})))

    @covers_requirement("art-subject-model::named-character-portrait-eligibility-is-explicit-policy-never-inferred")
    def test_eligibility_is_not_inferred_from_display_name_uniqueness(self):
        named = self._character({"mode": "named", "stable_key": "42"})
        unnamed = self._character(None)
        named.key = "共同名字"
        unnamed.key = "共同名字"
        self.assertIsNotNone(character_subject_for(named))
        self.assertIsNone(character_subject_for(unnamed))

    def test_malformed_policy_raises(self):
        for bad in (
            {"mode": "named"},
            {"mode": "named", "stable_key": "a:b"},
            {"mode": "weird"},
            {"mode": "named", "stable_key": ""},
        ):
            with self.subTest(policy=bad):
                with self.assertRaises(ArtSubjectError):
                    character_subject_for(self._character(bad))


class DescriptionTests(EvenniaTestCase):
    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_character_description_contains_only_allowed_stable_data(self):
        character = Mock()
        character.db.display_name = "艾琳"
        character.db.race = "beastfolk"
        character.db.subrace = "catkin"
        character.db.persona = "secret tragic past"
        character.db.disguised_stats = {"atk_phys": 99}
        character.key = "艾琳"
        text = character_description(character, 24)
        self.assertIn("艾琳", text)
        self.assertIn("貓人族", text)
        self.assertIn("24", text)
        self.assertNotIn("secret tragic past", text)
        self.assertNotIn("99", text)

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_scene_and_monster_descriptions_are_registry_text(self):
        scene = scene_subject_for("forest_path")
        monster = monster_subject_for("low")
        first = description_for(scene)
        second = description_for(scene)
        self.assertEqual(first, second)
        self.assertIn("林間小徑", first)
        monster_text = description_for(monster)
        self.assertIn("Threats a beginning adventurer", monster_text)
        self.assertEqual(monster_text, monster_description(monster))


def _persona_entity(persona):
    """A DB-free stand-in character with a fixed identity and the given persona."""
    entity = Mock()
    entity.db.display_name = "艾琳"
    entity.db.race = "beastfolk"
    entity.db.subrace = "catkin"
    entity.db.persona = persona
    entity.key = "艾琳"
    return entity


_APPEARANCE = {
    "height": "tall",
    "weight": "slender",
    "measurement": "narrow-shouldered",
    "style": "travel-worn leather",
    "overview": "a sharp-eyed scout",
    "attire": "a hooded cloak",
    "feature": "a silver ear piercing",
}


class AppearanceDescriptionTests(PromptFixture):
    """The admitted persona ``appearance`` block in character descriptions
    (portrait-prompt-appearance): ordering, exclusion, determinism, emptiness."""

    def _full_persona(self):
        # Insertion order deliberately shuffled away from _SUBKEY_ORDER so the
        # declared rendering order is what the ordering assertions observe.
        return {
            "appearance": {
                "attire": "a hooded cloak",
                "overview": "a sharp-eyed scout",
                "height": "tall",
                "style": "travel-worn leather",
                "measurement": "narrow-shouldered",
                "feature": "a silver ear piercing",
                "weight": "slender",
            },
            "personality": "guarded beneath a warm smile",
            "habit": "hums old road songs",
            "background": "raised in the border caravans",
            "life_story": "lost her patrol at the Ashford crossing",
            "identity": {
                "public": "village scout",
                "hidden": "exiled crown courier",
            },
            "social_connection": {"貝莎": "apprenticed smith"},
        }

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_full_persona_contributes_every_appearance_subkey_and_nothing_else(self):
        self.load()
        text = character_description(_persona_entity(self._full_persona()), 31)
        self.assertIn("艾琳", text)
        self.assertIn("貓人族", text)
        self.assertIn("31", text)
        for value in _APPEARANCE.values():
            self.assertIn(value, text)
        for excluded in (
            "guarded beneath a warm smile",
            "hums old road songs",
            "raised in the border caravans",
            "lost her patrol at the Ashford crossing",
            "village scout",
            "exiled crown courier",
            "貝莎",
            "apprenticed smith",
        ):
            self.assertNotIn(excluded, text)

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_hidden_identity_layer_never_reaches_the_prompt(self):
        self.load()
        persona = self._full_persona()
        persona["identity"] = {"public": "村落的偵察員", "hidden": "流放的王室信使"}
        text = character_description(_persona_entity(persona), 31)
        self.assertNotIn("流放的王室信使", text)
        self.assertNotIn("村落的偵察員", text)
        self.assertIn("a silver ear piercing", text)

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_description_is_byte_identical_with_declared_subkey_order(self):
        self.load()
        entity = _persona_entity(self._full_persona())
        first = character_description(entity, 31)
        second = character_description(entity, 31)
        self.assertEqual(first, second)
        # The contracted shape: base sentence, then the labeled appearance
        # block in _SUBKEY_ORDER order (unknown sub-keys would follow in
        # insertion order).
        self.assertEqual(
            first,
            "A 貓人族 character named 艾琳 (31) in the approved visual style.\n"
            "外觀：\n"
            "height：tall\n"
            "weight：slender\n"
            "measurement：narrow-shouldered\n"
            "style：travel-worn leather\n"
            "overview：a sharp-eyed scout\n"
            "attire：a hooded cloak\n"
            "feature：a silver ear piercing",
        )
        positions = [first.index(_APPEARANCE[key]) for key in (
            "height", "weight", "measurement", "style", "overview", "attire", "feature"
        )]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(set(positions)), len(positions))

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_empty_appearance_renders_the_pre_change_description(self):
        self.load()
        expected = "A 貓人族 character named 艾琳 (24) in the approved visual style."
        for persona in (
            {},
            {"appearance": {}, "personality": "guarded"},
            {"appearance": {"height": "", "attire": ""}},
            None,
            "secret tragic past",
        ):
            with self.subTest(persona=persona):
                self.assertEqual(character_description(_persona_entity(persona), 24), expected)

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_disguised_stats_never_appear_as_physical_truth(self):
        self.load()
        entity = _persona_entity(self._full_persona())
        entity.db.disguised_stats = {
            "str": 87,
            "physique": 154,
            "grace": 43,
            "vigour": 106,
        }
        entity.db.age = 61
        text = character_description(entity, 31)
        for value in (87, 154, 43, 106):
            self.assertNotIn(str(value), text)
        self.assertIn("a silver ear piercing", text)

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_overlong_appearance_is_capped_to_the_persona_field_bound(self):
        # The section inherits PersonaStore's per-field cap, so a pathological
        # authored block can never smuggle an unbounded prompt to the pipeline.
        self.load()
        persona = {"appearance": {"overview": "長" * 900}}
        text = character_description(_persona_entity(persona), 31)
        section = text.removeprefix(
            "A 貓人族 character named 艾琳 (31) in the approved visual style.\n"
        )
        self.assertEqual(len(section), 600)
        self.assertTrue(section.endswith("…"))

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_degraded_fallback_reads_no_persona(self):
        # Only art.character_description is broken, so the PromptUnavailableError
        # fallback branch is what runs. Any persona read raises through the trap.
        self.write_file(
            "art.yaml",
            "schema_version: 1\nprompts:\n"
            "  art.style: approved visual style\n"
            "  art.character_description: A {race} character named {name} ({age}) in the {style} {oops}.\n"
            '  art.monster_description: "{description} ({display_name}；例如：{examples})"\n',
        )
        self.load()

        class _DbTrap:
            """Identity fields resolve; touching persona fails the test."""

            display_name = "艾琳"
            race = "beastfolk"
            subrace = "catkin"

            @property
            def persona(self):
                raise AssertionError("the degraded fallback must read no persona")

        entity = Mock()
        entity.db = _DbTrap()
        entity.key = "艾琳"
        self.assertEqual(character_description(entity, 24), "艾琳（貓人族，24 歲）")

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_library_turning_unavailable_mid_render_keeps_the_base(self):
        # A reload that breaks the key between the base render and the
        # appearance render must degrade to the appearance-free base, never
        # raise and never lose the portrait.
        self.load()
        entity = _persona_entity({"appearance": {"feature": "a silver ear piercing"}})
        real = subjects.render_prompt
        calls = []

        def stub(key, **values):
            if key == "art.character_description":
                calls.append(values["appearance"])
                if len(calls) == 2:
                    raise PromptUnavailableError("art.yaml", key, "swapped mid-call")
            return real(key, **values)

        with patch.object(subjects, "render_prompt", stub):
            text = character_description(entity, 31)
        self.assertEqual(calls, ["", "\n外觀：\nfeature：a silver ear piercing"])
        self.assertEqual(
            text, "A 貓人族 character named 艾琳 (31) in the approved visual style."
        )


if __name__ == "__main__":
    unittest.main()
