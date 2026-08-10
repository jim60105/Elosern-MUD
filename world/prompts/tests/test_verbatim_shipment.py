"""Byte-for-byte shipment pinning for the prompt library (prompt-library).

The initial ``prompts/*.yaml`` files ship the current prompt text verbatim, so
behavior is byte-identical until an admin edits a file. These tests pin every
rendered system message and deterministic description against the exact text
that previously lived as Python constants, and pin the source-of-truth
scenarios: each generative layer renders its prompt from the library.
"""

from __future__ import annotations

import unittest

from world.prompts.loader import load_prompt_library, render_prompt, reset_prompt_library
from world.prompts.registry import PROMPT_SPECS
from world.prompts.tests.fixtures import REPO_PROMPTS

from tools.spec_traceability import covers_requirement


# The exact text of the removed Python constants (verbatim from git history).
_NARRATOR_SYSTEM = (
    "你是《伊洛瑟恩大陸》的旁白敘述者。請以正體中文，將底下的事件紀錄改寫成流暢的散文敘事。"
    "必須嚴格忠於紀錄：只能描述實際發生的事件，不得虛構任何事件、結果、數字或狀態。"
    "只輸出敘事散文本身，不要加上任何標題、前言、註解或元資訊。"
)
_SCENARIO_DIRECTOR_SYSTEM = (
    "你是《伊洛瑟恩大陸》的任務企劃（ScenarioDirector）。請以正體中文，"
    "根據請求設計一個冒險者公會任務的提案。你只能引用世界上真實存在的內容："
    "不得編造任何公會階級、場景類型、NPC 階級、怪物階級、物品、地點或獎勵。"
    "只輸出一個 JSON 物件，其結構必須符合 QuestBlueprint："
    '{"name": "…", "quest_type": "採集/討伐/護衛/探索/緊急", "rank": "F", '
    '"issuer": "guild_branch_…", "stages": [{"index": 0, "objective": '
    '{"kind": "defeat/reach_location/escort/acquire", "quantity": 1, '
    '"monster_tier": null, "item_key": null}, "location_req": {"layer": '
    '"anchor/grid/instance", "archetype": "…", "anchor_key": null, '
    '"anchor_near": null, "xyz": null, "scene_sentence": null}, "npc_req": '
    '[{"role": "…", "tier": "…", "disposition": null}]}], "reward": '
    '{"copper": 100, "items": [{"item_key": "healing_potion", "quantity": 1}], '
    '"merit": 25}, "failure": {"deadline_hours": 72, "conditions": []}}。'
    "stage 的 index 必須從 0 開始連續遞增。"
)
_NPC_DIALOGUE_TEMPLATE = (
    "{persona}"
    "你是《伊洛瑟恩大陸》中的 {name}。{desc}。目前位於{location}。"
    "你只能根據自己確實能觀察到的情況回應；"
    "玩家在你面前展現出的樣貌，就是你所見到的真實。"
    "請以正體中文和對方說話，並只輸出一個 JSON 物件："
    '{"speech": "你要說的話", "intent": {"kind": "..."}}。'
    "若玩家資料裡提供你對她的好感度，"
    "你可以依此決定是否送出 intent 為 adjust_relation、"
    "delta 為 0 到 10 之間整數的好感度調整；"
    "但好感度的數值與上限是你心中的祕密，絕不可在 speech 中說出。"
    "不得虛構任何結果、數字、對話或世界狀態；"
    "你沒有把握能確實執行的行為，不要寫進 intent。"
)
_NPC_THINKING = "（{name} 沉思片刻……）"
_ART_CHARACTER_TEMPLATE = "A {race} adult named {name} ({age}) in the {style}."
_SCENE_BUILDER_SYSTEM = (
    "你是《伊洛瑟恩大陸》的場景氛圍描述者。場景句子：{scene_sentence}。"
    "任務脈絡：{quest_context}。房間名稱：{room_name}。地區：{region}。"
    "請以正體中文，為這個任務場景寫一段 50 到 200 字的氛圍散文，"
    "只描寫環境與感官氛圍（光線、聲音、氣味、溫度、空間感）。"
    "你只能依據上面提供的四項資訊寫作：不得虛構任何人物、怪物、物品、數字或世界狀態，"
    "不得描述正在發生的事件，也不得預言後續發展。"
    "只輸出氛圍散文本身，不要加上任何標題、前言、註解或元資訊。"
)


class VerbatimShipmentTests(unittest.TestCase):
    def setUp(self) -> None:
        load_prompt_library(str(REPO_PROMPTS))

    def tearDown(self) -> None:
        reset_prompt_library()

    @covers_requirement("narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_narrator_system_message_is_shipped_verbatim(self):
        system = render_prompt("narrator.system")
        self.assertEqual(system, _NARRATOR_SYSTEM)
        self.assertIn("正體中文", system)
        self.assertIn("不得虛構", system)

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_scenario_director_system_message_is_shipped_verbatim(self):
        system = render_prompt("scenario_director.system")
        self.assertEqual(system, _SCENARIO_DIRECTOR_SYSTEM)
        self.assertIn("QuestBlueprint", system)
        self.assertIn("不得編造", system)

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_npc_dialogue_system_template_is_shipped_verbatim(self):
        rendered = render_prompt(
            "npc_dialogue.system",
            name="甲",
            desc="乙",
            location="丙",
            persona="",
        )
        self.assertEqual(
            rendered,
            _NPC_DIALOGUE_TEMPLATE.replace("{persona}", "")
            .replace("{name}", "甲")
            .replace("{desc}", "乙")
            .replace("{location}", "丙"),
        )

    @covers_requirement("prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt")
    def test_npc_thinking_template_is_shipped_verbatim(self):
        self.assertEqual(
            render_prompt("npc.thinking", name="甲"),
            _NPC_THINKING.format(name="甲"),
        )

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-adult-safe-and-exclude-non-physical-truth")
    def test_art_character_description_is_shipped_verbatim(self):
        style = render_prompt("art.style")
        self.assertEqual(
            render_prompt(
                "art.character_description",
                race="貓人族",
                name="艾琳",
                age="24",
                style=style,
            ),
            _ART_CHARACTER_TEMPLATE.format(
                race="貓人族", name="艾琳", age="24", style=style
            ),
        )
        self.assertEqual(
            render_prompt(
                "art.character_description",
                race="貓人族",
                name="艾琳",
                age="24",
                style=style,
            ),
            "A 貓人族 adult named 艾琳 (24) in the approved visual style.",
        )

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_npc_dialogue_render_equals_the_original_rendered_constant(self):
        rendered = render_prompt(
            "npc_dialogue.system",
            name="甲",
            desc="乙",
            location="丙",
            persona="",
        )
        self.assertEqual(
            rendered,
            "你是《伊洛瑟恩大陸》中的 甲。乙。目前位於丙。"
            "你只能根據自己確實能觀察到的情況回應；"
            "玩家在你面前展現出的樣貌，就是你所見到的真實。"
            "請以正體中文和對方說話，並只輸出一個 JSON 物件："
            '{"speech": "你要說的話", "intent": {"kind": "..."}}。'
            "若玩家資料裡提供你對她的好感度，"
            "你可以依此決定是否送出 intent 為 adjust_relation、"
            "delta 為 0 到 10 之間整數的好感度調整；"
            "但好感度的數值與上限是你心中的祕密，絕不可在 speech 中說出。"
            "不得虛構任何結果、數字、對話或世界狀態；"
            "你沒有把握能確實執行的行為，不要寫進 intent。",
        )

    @covers_requirement("prompt-library::the-prompt-library-is-the-single-source-of-truth-for-every-llm-prompt")
    def test_scene_builder_system_is_shipped_verbatim(self):
        rendered = render_prompt(
            "scene_builder.system",
            scene_sentence="古老森林深處的祭壇",
            quest_context="採集任務",
            room_name="林間祭壇",
            region="遺忘森林",
        )
        self.assertEqual(
            rendered,
            _SCENE_BUILDER_SYSTEM.replace("{scene_sentence}", "古老森林深處的祭壇")
            .replace("{quest_context}", "採集任務")
            .replace("{room_name}", "林間祭壇")
            .replace("{region}", "遺忘森林"),
        )
        self.assertIn("正體中文", rendered)
        self.assertIn("不得虛構", rendered)


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
            skill_key="basic_attack",
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

        system, _ = build_scenario_prompt(
            {
                "requested_type": "討伐",
                "allowed_rank": "F",
                "issuer_branch": "guild_branch_altoria",
                "anchor": "capital_altoria",
            }
        )
        self.assertEqual(system["content"], render_prompt("scenario_director.system"))

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
            render_prompt(
                "npc_dialogue.system",
                name="甲",
                desc="乙",
                location="丙",
                persona="",
            ),
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

    @covers_requirement("art-subject-model::subject-descriptions-are-deterministic-adult-safe-and-exclude-non-physical-truth")
    def test_art_descriptions_render_from_the_library_solely(self):
        from unittest.mock import Mock

        from world.art.subjects import (
            character_description,
            description_for,
            monster_description,
            monster_subject_for,
            scene_subject_for,
        )

        scene = scene_subject_for("forest_path")
        self.assertEqual(
            description_for(scene),
            "陽光穿過層疊的枝葉，灑在一條蜿蜒的林間小徑上，四周寂靜得只剩下風聲。",
        )

        character = Mock()
        character.db.display_name = "艾琳"
        character.db.race = "beastfolk"
        character.db.subrace = "catkin"
        character.key = "艾琳"
        self.assertEqual(
            character_description(character, 24),
            "A 貓人族 adult named 艾琳 (24) in the approved visual style.",
        )

        monster = monster_subject_for("low")
        self.assertEqual(
            monster_description(monster),
            render_prompt(
                "art.monster_description",
                description="Threats a beginning adventurer can handle alone.",
                display_name="低階",
                examples="史萊姆、哥布林、巨鼠",
            ),
        )


if __name__ == "__main__":
    unittest.main()
