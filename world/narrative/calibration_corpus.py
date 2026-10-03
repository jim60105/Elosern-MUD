"""Synthetic labeled test fixtures for narrative recall calibration.

Contains ground-truth positive cases (aliases, paraphrases), hard salient negatives,
uninformed role checks, and historical/superseded cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Synthetic memory records representing Yohanna and settlement environment
SYNTHETIC_CALIBRATION_CORPUS: list[dict[str, Any]] = [
    # 1. Protection episode (Yohanna witnessed player protection during encounter)
    # Notice: content summary includes structured encounter semantics compatible with projector output
    {
        "source_id": "corpus:encounter:prot:1",
        "owner_id": "npc_yohanna_101",
        "tick": 100,
        "category": "encounter",
        "tier": "working",
        "salience": 85,
        "knowledge_scope": "witnessed",
        "confidence": 1.0,
        "subjects": ["npc_yohanna_101", "char_player_1"],
        "content": {
            "summary": "Witnessed successful protection during encounter 在溪谷遭遇野獸襲擊時獲得玩家及時保護與援護，成功脫離險境",
            "encounter_outcome": "victory",
            "protected_keys": ["npc_yohanna_101"],
            "location": "溪谷小徑",
            "opponent": "兇暴野狼",
        },
    },
    # 2. Daily routine (Yohanna herb gathering - neutral working memory)
    {
        "source_id": "corpus:routine:herb:1",
        "owner_id": "npc_yohanna_101",
        "tick": 120,
        "category": "routine",
        "tier": "working",
        "salience": 30,
        "knowledge_scope": "witnessed",
        "confidence": 1.0,
        "subjects": ["npc_yohanna_101"],
        "content": {
            "summary": "清晨前往林地採集止血草與藍花藥草，曬乾後存放於木架",
            "activity": "herb_gathering",
        },
    },
    # 3. Unrelated high-salience negative episode (Yohanna's intense personal memory of lost family pendant)
    {
        "source_id": "corpus:personal:pendant:1",
        "owner_id": "npc_yohanna_101",
        "tick": 50,
        "category": "personal",
        "tier": "core",
        "salience": 98,  # Extremely high salience!
        "knowledge_scope": "witnessed",
        "confidence": 1.0,
        "subjects": ["npc_yohanna_101"],
        "content": {
            "summary": "深感悔恨失落了母親遺留的金屬墜飾項鍊，無論如何都想找尋回來",
            "emotion": "deep_grief",
        },
    },
    # 4. Another unrelated high-salience negative (Royal tournament gossip)
    {
        "source_id": "corpus:gossip:tournament:1",
        "owner_id": "npc_yohanna_101",
        "tick": 130,
        "category": "rumor",
        "tier": "working",
        "salience": 90,  # High salience negative!
        "knowledge_scope": "told",
        "confidence": 0.8,
        "subjects": ["npc_yohanna_101"],
        "content": {
            "summary": "聽行商提起王都舉辦盛大劍術比武大會，騎士團長一舉奪冠",
            "speaker": "merchant_todd",
        },
    },
    # 5. Historical/superseded memory (Old route gossip superseded by courier arrival)
    {
        "source_id": "corpus:history:courier:old",
        "owner_id": "npc_yohanna_101",
        "tick": 80,
        "category": "courier",
        "tier": "archive",
        "salience": 60,
        "knowledge_scope": "told",
        "confidence": 0.7,
        "superseded": True,  # Will be marked superseded in setup
        "content": {
            "summary": "暴雨山崩封鎖東部隘口道路傳言",
        },
    },
    # 6. Active courier memory (supersedes the old gossip)
    {
        "source_id": "corpus:courier:active:new",
        "owner_id": "npc_yohanna_101",
        "tick": 140,
        "category": "courier",
        "tier": "working",
        "salience": 75,
        "knowledge_scope": "witnessed",
        "confidence": 1.0,
        "subjects": ["npc_yohanna_101"],
        "content": {
            "summary": "親眼見到銀羽驛站信使順利抵達交付信件",
        },
    },
    # 7. Inactive memory (archived historical record marked inactive)
    {
        "source_id": "corpus:inactive:outdated:1",
        "owner_id": "npc_yohanna_101",
        "tick": 30,
        "category": "archive_note",
        "tier": "archive",
        "salience": 20,
        "knowledge_scope": "witnessed",
        "confidence": 0.5,
        "inactive": True,  # Marked inactive
        "content": {
            "summary": "廢棄舊磨坊地下暗室探查筆記",
        },
    },
    # 8. Uninformed role memory (Different NPC who knows nothing about the protection)
    {
        "source_id": "corpus:uninformed:record:1",
        "owner_id": "npc_guard_202",
        "tick": 100,
        "category": "routine",
        "tier": "working",
        "salience": 40,
        "knowledge_scope": "witnessed",
        "subjects": ["npc_guard_202"],
        "content": {
            "summary": "守衛在城門巡邏值勤，檢查過往車輛通行證件",
        },
    },
]


@dataclass(frozen=True)
class LabeledTestCase:
    case_id: str
    query: str
    owner_id: str
    expected_top_source_ids: tuple[str, ...]  # Expected top 1 or 2 relevant matches
    forbidden_source_ids: tuple[str, ...]  # Salient negatives that must NEVER be returned
    should_be_empty: bool
    include_superseded: bool = False
    include_inactive: bool = False
    notes: str = ""


# Synthetic calibration test cases covering:
# - Alias and paraphrase positive protection cases
# - Hard salient negative cases
# - Uninformed owner querying protection
# - Historical vs superseded exclusion
# - Normal inactive exclusion vs explicit historical inclusion
CALIBRATION_TEST_CASES: list[LabeledTestCase] = [
    # 1. Direct protection query
    LabeledTestCase(
        case_id="pos_protection_direct",
        query="那天在溪谷遭遇野獸襲擊，你保護了我",
        owner_id="npc_yohanna_101",
        expected_top_source_ids=("corpus:encounter:prot:1",),
        forbidden_source_ids=("corpus:personal:pendant:1", "corpus:gossip:tournament:1"),
        should_be_empty=False,
        notes="Direct query with exact keywords '溪谷', '野獸', '保護'.",
    ),
    # 2. Paraphrase / alias protection query
    LabeledTestCase(
        case_id="pos_protection_paraphrase",
        query="還記得在山谷被野狼圍攻時的援護戰鬥嗎？",
        owner_id="npc_yohanna_101",
        expected_top_source_ids=("corpus:encounter:prot:1",),
        forbidden_source_ids=("corpus:personal:pendant:1", "corpus:gossip:tournament:1"),
        should_be_empty=False,
        notes="Paraphrase using aliases '援護', '野狼', '戰鬥'.",
    ),
    # 3. Yohanna name alias query
    LabeledTestCase(
        case_id="pos_protection_entity_alias",
        query="庫柏小姐，之前遭遇危險時的守護情誼",
        owner_id="npc_yohanna_101",
        expected_top_source_ids=("corpus:encounter:prot:1",),
        forbidden_source_ids=("corpus:personal:pendant:1", "corpus:gossip:tournament:1"),
        should_be_empty=False,
        notes="Entity alias '庫柏' for Yohanna with '守護'.",
    ),
    # 4. Salient negative: completely unrelated query about cooking/fishing
    LabeledTestCase(
        case_id="neg_unrelated_salient",
        query="湖邊釣魚與烹煮鮮魚料理的秘訣",
        owner_id="npc_yohanna_101",
        expected_top_source_ids=(),
        forbidden_source_ids=("corpus:personal:pendant:1", "corpus:gossip:tournament:1", "corpus:encounter:prot:1"),
        should_be_empty=True,
        notes="Completely unrelated topic; high salience pendant (salience 98) must NOT be returned.",
    ),
    # 5. Salient negative: query about royal palace
    LabeledTestCase(
        case_id="neg_unrelated_royal_palace",
        query="王宮地下藏寶庫的古代魔法機關鑰匙",
        owner_id="npc_yohanna_101",
        expected_top_source_ids=(),
        forbidden_source_ids=("corpus:personal:pendant:1", "corpus:gossip:tournament:1"),
        should_be_empty=True,
        notes="Absent subject; tournament gossip (salience 90) must NOT qualify.",
    ),
    # 6. Uninformed role query: Guard asked about protection
    LabeledTestCase(
        case_id="neg_uninformed_guard",
        query="那天在溪谷遭遇野獸襲擊，你保護了我",
        owner_id="npc_guard_202",
        expected_top_source_ids=(),
        forbidden_source_ids=("corpus:encounter:prot:1",),
        should_be_empty=True,
        notes="Guard does not own or know the protection episode; recall must be empty.",
    ),
    # 7. Normal access excludes superseded courier memory
    LabeledTestCase(
        case_id="hist_normal_excludes_superseded",
        query="暴雨山崩封鎖東部隘口道路傳言",
        owner_id="npc_yohanna_101",
        expected_top_source_ids=(),
        forbidden_source_ids=("corpus:history:courier:old",),
        should_be_empty=True,
        include_superseded=False,
        notes="Normal access excludes superseded record even if lexically matching.",
    ),
    # 8. Historical access includes superseded courier memory
    LabeledTestCase(
        case_id="hist_historical_includes_superseded",
        query="暴雨山崩封鎖東部隘口道路傳言",
        owner_id="npc_yohanna_101",
        expected_top_source_ids=("corpus:history:courier:old",),
        forbidden_source_ids=(),
        should_be_empty=False,
        include_superseded=True,
        notes="Historical access (include_superseded=True) retrieves the historical record.",
    ),
    # 9. Normal access excludes inactive memory
    LabeledTestCase(
        case_id="hist_normal_excludes_inactive",
        query="廢棄舊磨坊地下暗室探查筆記",
        owner_id="npc_yohanna_101",
        expected_top_source_ids=(),
        forbidden_source_ids=("corpus:inactive:outdated:1",),
        should_be_empty=True,
        include_inactive=False,
        notes="Normal access excludes inactive record even if lexically matching.",
    ),
    # 10. Historical access includes inactive memory
    LabeledTestCase(
        case_id="hist_historical_includes_inactive",
        query="廢棄舊磨坊地下暗室探查筆記",
        owner_id="npc_yohanna_101",
        expected_top_source_ids=("corpus:inactive:outdated:1",),
        forbidden_source_ids=(),
        should_be_empty=False,
        include_inactive=True,
        notes="Explicit historical/inactive access retrieves the inactive record.",
    ),
]
