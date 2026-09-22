"""Data-contract test: saintess vessel registry and enrollment grant contract

Row-shape and grant-surface contract for the 聖女容器 (``saintess_vessel``)
clergy qualifier passive (saintess-vessel §9.1): same qualifier-row shape as
its three siblings, practice-unearnable through the pre-existing PASSIVE
guards, non-conferrable, absent from every lineage/unlock table, granted only
through church enrollment by a female ``human_royal`` character (no office
uniqueness), and never a redemption-catalogue row at any price. The shipped
royal preset 薇歐蕾特 carries neither the vessel nor the robe and her persona
carries no religious narrative.

Shipped registry/preset keys appear literally because this module IS the
shipped-content contract for those rows (the test-data-independence gate
exempts tagged data-contract tests).
"""

import re
from pathlib import Path

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase, EvenniaTest

from typeclasses.characters import PlayerCharacter

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.rules import cross_lineage_unlock
from world.rules.character_creation import (
    CharacterCreationRequest,
    activate_player_character,
)
from world.rules.progression import grant_skill_practice_xp, grant_study_practice_xp
from world.rules.skill_effects import validate_conferrable_skill
from world.rules.skill_ownership import owns_stored_skill
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillKind, TargetSpec

VESSEL_KEY = "saintess_vessel"
PRESET_KEY = "violet_altoria"
CLERGY_SIBLINGS = ("pain_to_pleasure", "rapture_renewal", "priestly_grace")

REPO_ROOT = Path(__file__).resolve().parents[3]

_CJK_RE = re.compile(r"[\u3400-\u9fff]")

# The retired religious narrative, deleted not reframed (design §9.1/D4):
# once-per-generation donated-princess claims and consecration wording must
# appear nowhere in authored content.
_RETIRED_CLAIMS = (
    "聖女繼承人",
    "每代獻任",
    "每代由王國王室獻任的公主",
    "每代獻一女",
    "祝聖接任",
)

# Persona prose surfaces of the shipped card searched for the narrative.
_PERSONA_SURFACES = (
    "identity",
    "personality",
    "life_story",
    "habit",
    "appearance",
    "social_connection",
    "background",
)


def _persona_prose(preset) -> str:
    """Concatenate every authored persona surface of one preset card."""
    persona = preset.persona
    parts: list[str] = [
        persona.identity.public,
        persona.identity.hidden,
        persona.personality,
        persona.life_story,
        persona.habit,
        persona.background,
    ]
    for key in ("height", "weight", "measurement", "style", "overview", "attire", "feature"):
        parts.append(getattr(persona.appearance, key))
    parts.extend(
        f"{name}：{relation}" for name, relation in persona.social_connection
    )
    return "\n".join(parts)


class SaintessVesselRegistryContractTests(EvenniaTestCase):
    """The vessel row exists with the clergy qualifier shape."""

    def test_row_shape_matches_the_clergy_qualifier_contract(self):
        skill = SKILL_REGISTRY[VESSEL_KEY]
        self.assertIs(skill.kind, SkillKind.PASSIVE)
        self.assertIs(skill.target_spec, TargetSpec.NONE)
        self.assertTrue(skill.usable_out_of_combat)
        self.assertIs(skill.element, ELEMENT_REGISTRY["light"])
        self.assertIs(skill.category, SkillCategory.ENHANCEMENT)
        self.assertFalse(skill.effects, "the qualifier row carries no effects")
        self.assertFalse(skill.prerequisites, "no lineage prerequisites")
        self.assertTrue(skill.label)
        self.assertTrue(skill.description)
        self.assertTrue(_CJK_RE.search(skill.label))
        self.assertTrue(_CJK_RE.search(skill.description))

    def test_row_is_registered_immediately_after_priestly_grace(self):
        keys = list(SKILL_REGISTRY)
        self.assertEqual(
            keys.index(VESSEL_KEY), keys.index("priestly_grace") + 1
        )

    def test_vessel_is_not_a_node_in_any_genealogy_or_unlock_rule(self):
        # No shipped skill lists the vessel as a prerequisite edge...
        self.assertTrue(
            all(
                VESSEL_KEY
                not in {edge.skill_key for edge in skill.prerequisites}
                for skill in SKILL_REGISTRY.values()
            )
        )
        # ...no cross-lineage rule samples or grants it.
        rulebook = cross_lineage_unlock.RULEBOOK
        self.assertNotIn(VESSEL_KEY, rulebook.reverse_index)
        self.assertTrue(
            all(VESSEL_KEY not in rule.grants for rule in rulebook.rules)
        )

    @covers_requirement("saintess-vessel::saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive")
    def test_practice_awards_reject_the_passive_key(self):
        entity = create_object(PlayerCharacter, key="vessel practice probe")
        entity.race = "human"
        entity.apply_race_baseline()
        self.assertFalse(
            grant_skill_practice_xp(entity, VESSEL_KEY, target=entity),
            "use-driven practice must refuse a PASSIVE skill",
        )
        self.assertFalse(
            grant_study_practice_xp(entity, VESSEL_KEY, 2),
            "booked study must refuse a PASSIVE skill",
        )

    @covers_requirement("saintess-vessel::saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive")
    def test_cross_lineage_engine_rejects_the_passive_as_a_scope_node(self):
        # A rule scoping the vessel as a practice-proficiency node must fail
        # closed at load: only ACTIVE nodes hold practice proficiency.
        from world.rules.cross_lineage_unlock import load_rules

        with self.assertRaisesRegex(ValueError, "ACTIVE"):
            load_rules(
                [
                    {
                        "id": "t_vessel_scope",
                        "requires": [
                            {
                                "scope": {"keys": [VESSEL_KEY]},
                                "min_level": 1,
                            }
                        ],
                        "grants": ["pain_to_pleasure"],
                    }
                ]
            )

    @covers_requirement("saintess-vessel::saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive")
    def test_vessel_is_not_conferrable_like_its_siblings(self):
        from world.rules.action import RejectedAction

        for key in (*CLERGY_SIBLINGS, VESSEL_KEY):
            with self.subTest(key=key):
                with self.assertRaises(RejectedAction):
                    validate_conferrable_skill(key)


class SaintessVesselPresetContractTests(EvenniaTest):
    """The shipped royal preset carries neither vessel nor robe nor narrative."""

    @covers_requirement(
        "church-ordination::the-shipped-royal-preset-awaits-nothing-the-vessel-and-the-robe-are-enrollment-gifts",
        "saintess-vessel::saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive",
    )
    def test_the_preset_carries_neither_vessel_nor_robe(self):
        preset = PLAYER_PRESET_REGISTRY[PRESET_KEY]
        self.assertNotIn(
            VESSEL_KEY,
            preset.passive_skills,
            "the vessel is an enrollment grant, never preset-initial state",
        )
        self.assertNotIn(
            "saintess_vestments",
            {item_key for item_key, _ in preset.starting_items},
            "the robe is an enrollment gift, never a family heirloom",
        )

    @covers_requirement(
        "church-ordination::the-shipped-royal-preset-awaits-nothing-the-vessel-and-the-robe-are-enrollment-gifts",
        "saintess-vessel::saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive",
    )
    def test_preset_activation_grants_neither_vessel_nor_event(self):
        holder = self.char1
        holder.race = "human"
        holder.apply_race_baseline()
        self.account.at_post_create_character(holder)
        with self.captureOnCommitCallbacks(execute=True):
            activate_player_character(
                self.account,
                holder,
                CharacterCreationRequest(mode="preset", preset_key=PRESET_KEY),
            )
        self.assertNotIn(VESSEL_KEY, holder.db.skills["passive"])
        self.assertFalse(owns_stored_skill(holder, VESSEL_KEY))
        self.assertNotIn(
            "saintess_vestments", list(holder.db.inventory or [])
        )

    @covers_requirement(
        "church-ordination::the-shipped-royal-preset-awaits-nothing-the-vessel-and-the-robe-are-enrollment-gifts"
    )
    def test_the_persona_carries_no_retired_religious_narrative(self):
        preset = PLAYER_PRESET_REGISTRY[PRESET_KEY]
        prose = _persona_prose(preset)
        self.assertTrue(prose, "the preset persona must be authored")
        for claim in ("聖女", "聖女繼承人", "傾湧", "祝聖", "每代獻"):
            with self.subTest(claim=claim):
                self.assertNotIn(claim, prose, f"retired narrative {claim!r} survives")
        # The public identity keeps the royal clause but loses the church
        # clause entirely (deleted, not reframed into a successor title).
        self.assertIn("王女", preset.persona.identity.public)
        self.assertNotIn("教會", preset.persona.identity.public)

    @covers_requirement(
        "church-ordination::the-shipped-royal-preset-awaits-nothing-the-vessel-and-the-robe-are-enrollment-gifts",
    )
    def test_repo_wide_authored_content_search_proves_the_framing_is_gone(self):
        # Repo-wide authored-content search for the deleted framing: the
        # once-per-generation donated-princess claim and the 聖女繼承人
        # successor framing count as failures wherever they reappear.
        corpus = []
        for root in ("docs", "world/lore"):
            base = REPO_ROOT / root
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(REPO_ROOT).as_posix()
                if "/tests/" in relative or relative.startswith(
                    "docs/superpowers/"
                ):
                    continue
                if path.suffix not in (".md", ".py"):
                    continue
                corpus.append(path)
        offenders = []
        for path in corpus:
            text = path.read_text(encoding="utf-8")
            for claim in _RETIRED_CLAIMS:
                if claim in text:
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT).as_posix()}:{claim}"
                    )
        self.assertEqual(offenders, [], "retired church framing reappears")


if __name__ == "__main__":
    import unittest

    unittest.main()