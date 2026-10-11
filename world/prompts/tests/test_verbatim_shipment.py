"""Program-logic contract for the shipped prompt library (prompt-library).

The shipped ``prompts/*.yaml`` wording is deployment-authored and retuned
freely, so this module asserts no literal shipped sentence: every key must load
from the shipped root, its template token set must stay inside its declared
allowlist, each supplied value must substitute exactly as often as the template
spells its token leaving no ``{token}`` behind, and two identical renders must
be byte-identical. ``LibrarySourceTests`` keeps the source-of-truth checks —
each consumer's prompt equals the library render from the same inputs — which
compare against the seam and never against a literal.
"""

from __future__ import annotations

from collections import Counter
import unittest

from world.prompts.loader import (
    _PLACEHOLDER_RE,
    load_prompt_library,
    render_prompt,
    reset_prompt_library,
)
from world.prompts.registry import PROMPT_SPECS
from world.prompts.tests.fixtures import REPO_PROMPTS

from tools.spec_traceability import covers_requirement

from world.tests.synthetic_data import (
    SYNTH_ARCHETYPES,
    SYNTH_SUBRACES,
    synthetic_registries,
)

# The one shipped key whose template deliberately selects a subset of its
# allowlist: ``art.monster_description`` declares both public identity tokens
# while the shipped text uses only ``{description}``. A key renders with the
# tokens it declares and an unused declared value is inert (change design D1),
# so the template side of parity is a subset there and exact everywhere else.
_SUBSET_PARITY_KEY = "art.monster_description"


class VerbatimShipmentTests(unittest.TestCase):
    """The code-level contract every shipped prompt key must satisfy."""

    def setUp(self) -> None:
        load_prompt_library(str(REPO_PROMPTS))

    def tearDown(self) -> None:
        reset_prompt_library()

    @covers_requirement(
        "prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt",
        "prompt-library::prompt-library-tests-verify-program-logic-not-shipped-wording",
    )
    def test_every_shipped_key_loads_with_placeholder_parity(self):
        library = load_prompt_library(str(REPO_PROMPTS))
        self.assertEqual(library.unavailable, frozenset())
        self.assertEqual(set(library.texts), set(PROMPT_SPECS))
        for key, spec in PROMPT_SPECS.items():
            with self.subTest(key=key):
                tokens = set(_PLACEHOLDER_RE.findall(library.text(key)))
                allowed = set(spec.allowed_placeholders)
                # A shipped token outside the allowlist is already a load-time
                # unknown-placeholder error, so the template is always a
                # subset; the allowlist itself is the declared contract.
                self.assertLessEqual(tokens, allowed)
                if key != _SUBSET_PARITY_KEY:
                    self.assertEqual(tokens, allowed)

    @covers_requirement(
        "prompt-library::prompt-rendering-substitutes-only-allowlisted-placeholders-deterministically",
        "prompt-library::prompt-library-tests-verify-program-logic-not-shipped-wording",
    )
    def test_every_shipped_key_substitutes_its_supplied_values_once(self):
        library = load_prompt_library(str(REPO_PROMPTS))
        # Assert the shipped root is whole first so a token-set regression
        # there reports its own named failure instead of a KeyError here.
        self.assertEqual(library.unavailable, frozenset())
        for key, spec in PROMPT_SPECS.items():
            with self.subTest(key=key):
                text = library.text(key)
                # One distinct, test-owned marker per allowlisted token: every
                # token the template selects lands exactly as many times as the
                # template spells it and leaves nothing unsubstituted, while an
                # allowlisted token the template does not select stays inert.
                occurrences = Counter(_PLACEHOLDER_RE.findall(text))
                values = {token: f"<{token}>" for token in spec.allowed_placeholders}
                rendered = render_prompt(key, **values)
                for token, count in occurrences.items():
                    self.assertEqual(rendered.count(f"<{token}>"), count)
                    self.assertNotIn(f"{{{token}}}", rendered)
                for token in set(spec.allowed_placeholders) - set(occurrences):
                    self.assertNotIn(f"<{token}>", rendered)
                self.assertEqual(render_prompt(key, **values), rendered)


class LibrarySourceTests(unittest.TestCase):
    def setUp(self) -> None:
        load_prompt_library(str(REPO_PROMPTS))

    def tearDown(self) -> None:
        reset_prompt_library()

    @covers_requirement("narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_narrator_renders_from_the_library_solely(self):
        from world.ai.narrator import build_narrator_prompt
        from world.rules.event_log import EventEntry, EventLog

        log = EventLog(
            actor="elosia",
            skill_key="t_synth_strike",
            targets=("violet",),
            entries=(
                EventEntry(
                    kind="damage",
                    actor="elosia",
                    target="violet",
                    data={"amount": 12},
                    text_template="{actor} 對 {target} 造成 {data[amount]} 點傷害。",
                ),
            ),
            time_cost_seconds=5,
        )
        system, _ = build_narrator_prompt((log,))
        self.assertEqual(system["content"], render_prompt("narrator.system"))

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_scenario_director_renders_from_the_library_solely(self):
        from world.ai.scenario_director import build_scenario_prompt

        system, user = build_scenario_prompt(
            {
                "requested_type": "討伐",
                "allowed_rank": "F",
                "issuer_branch": "t_branch_north",
                "anchor": "t_anchor_cross",
            }
        )
        # The full equality against the library text with the independently
        # recomputed context-seeded bank: nothing may be appended to, rewritten
        # in, or dropped from the system prompt outside the YAML template.
        from random import Random
        import zlib

        from world.rules.namegen import roll_name_for_race

        rng = Random(zlib.crc32(user["content"].encode("utf-8")))
        bank = "、".join(roll_name_for_race(None, "", rng) for _ in range(6))
        self.assertEqual(
            system["content"],
            render_prompt("scenario_director.system", name_inspiration=bank),
        )

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_npc_dialogue_renders_from_the_library_solely(self):
        from world.ai.npc_dialogue import build_npc_dialogue_prompt

        system, _ = build_npc_dialogue_prompt(
            {"name": "甲", "desc": "乙", "location": "丙"},
            {"name": "薇歐蕾", "disguised_stats": {}},
            [],
        )
        self.assertEqual(
            system["content"],
            "\n\n".join((render_prompt("npc_dialogue.global_rules"),
                          render_prompt("npc_dialogue.world_digest"), render_prompt(
                "npc_dialogue.system",
                name="甲",
                desc="乙",
                location="",
                persona="",
            ))),
        )

    @covers_requirement("prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt")
    def test_scene_flavor_renders_from_the_library_solely(self):
        from world.ai.scene_flavor import SceneFlavorContext, build_scene_flavor_prompt

        system, _ = build_scene_flavor_prompt(
            SceneFlavorContext(
                scene_sentence="古老森林深處的祭壇",
                quest_context="採集任務：採集靈藥草",
                room_name="林間祭壇",
                region="遺忘森林",
            )
        )
        self.assertEqual(
            system["content"],
            render_prompt(
                "scene_builder.system",
                scene_sentence="古老森林深處的祭壇",
                quest_context="採集任務：採集靈藥草",
                room_name="林間祭壇",
                region="遺忘森林",
            ),
        )

    @synthetic_registries("archetypes", "subraces")
    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth")
    def test_art_descriptions_render_from_the_library_solely(self):
        from unittest.mock import Mock

        from world.art.subjects import (
            character_description,
            description_for,
            monster_description,
            monster_subject_for,
            scene_subject_for,
        )
        from world.lore.monster_visuals import get_monster_visual_registry

        # The description producers resolve their subjects against the scene
        # archetype / subrace catalogs, so the kit rows stand in: the
        # source-of-truth claim compares each consumer against the library
        # render from the same inputs, never against literal text.
        synth_scene = sorted(SYNTH_ARCHETYPES)[0]
        synth_subrace = sorted(SYNTH_SUBRACES)[0]

        scene = scene_subject_for(synth_scene)
        self.assertEqual(
            description_for(scene),
            SYNTH_ARCHETYPES[synth_scene].scene_sentence,
        )

        character = Mock()
        character.db.display_name = "艾琳"
        character.db.race = "t_duskmari"
        character.db.subrace = synth_subrace
        character.key = "艾琳"
        label = SYNTH_SUBRACES[synth_subrace].display_name_zh
        self.assertEqual(
            character_description(character, 24, fields=("appearance",)),
            render_prompt(
                "art.character_description",
                race=label,
                age="24",
                appearance="",
                equipment="",
                custom="",
            ),
        )

        # A registered visual species: the seam supplies both public identity
        # values of the selected row, so the description IS the library render.
        monster = monster_subject_for("goblin")
        row = get_monster_visual_registry()["goblin"]
        self.assertEqual(
            monster_description(monster),
            render_prompt(
                "art.monster_description",
                description=row.published_appearance_zh,
                display_name=row.display_label,
            ),
        )


if __name__ == "__main__":
    unittest.main()
