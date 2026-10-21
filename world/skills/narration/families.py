"""Family-tier narration rows: the fallback every active skill resolves to.

Every ACTIVE family narrates from its own per-skill rows; the family tier
stays as the documented fallback under them, including the element-and-shape
line for an element key that has no authored row yet and the line-of-act
clause for a hand-built act. The family tier never replaces an authored
per-skill row; it only keeps a skill narrating from day one.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from world.skills.effects import (
    DamageEffect,
    HealEffect,
    SelfHealEffect,
)
from world.skills.registry import SkillCategory, SkillDef

from .vocab import NarrationRow

#: Families whose per-skill rows have not landed yet. Every ACTIVE family is
#: authored, so the set is empty; a test pins it empty, so no family can
#: silently re-open an exemption.
PENDING_FAMILIES = frozenset()

#: The two elemental shapes: a damaging spell and a supportive one.
ELEMENTAL_SHAPES = ("assault", "succor")

ELEMENTAL_ACTIONS: Mapping[str, Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "fire": MappingProxyType(
            {
                "assault": (
                    "{actor} 的火焰在掌中凝聚成矢。",
                    "{actor} 揚手，一道赤焰破空而去。",
                    "{actor} 的指尖燃起灼目的火光。",
                ),
                "succor": (
                    "{actor} 的火焰收斂成溫柔的暖意。",
                    "{actor} 讓火光安靜環住身周。",
                    "{actor} 掌心的熱度逐漸滲進身體。",
                ),
            }
        ),
        "water": MappingProxyType(
            {
                "assault": (
                    "{actor} 的水刃貼著地面掃出。",
                    "{actor} 抬手，一道水流驟然收緊。",
                    "{actor} 的指尖泛起冷冽的水光。",
                ),
                "succor": (
                    "{actor} 的水氣悄然覆上傷處。",
                    "{actor} 讓清涼的流水漫過四肢。",
                    "{actor} 的掌心聚起一汪溫潤。",
                ),
            }
        ),
        "earth": MappingProxyType(
            {
                "assault": (
                    "{actor} 腳下的土地猛然隆起。",
                    "{actor} 沉身一踏，岩塊隨之翻起。",
                    "{actor} 的拳上裹著厚重的土色。",
                ),
                "succor": (
                    "{actor} 讓大地的沉穩流進身體。",
                    "{actor} 腳下的土石安靜地托住了他。",
                    "{actor} 的呼吸隨著大地慢了下來。",
                ),
            }
        ),
        "wind": MappingProxyType(
            {
                "assault": (
                    "{actor} 的身形化作一道疾風。",
                    "{actor} 抬手，氣流在指間收束成刃。",
                    "{actor} 的衣角一揚，風勢已至。",
                ),
                "succor": (
                    "{actor} 讓風繞著自己盤旋。",
                    "{actor} 的腳步在氣流裡輕了起來。",
                    "{actor} 迎著風，重新找回節奏。",
                ),
            }
        ),
        "lightning": MappingProxyType(
            {
                "assault": (
                    "{actor} 的指尖迸出一道雷光。",
                    "{actor} 抬手，電弧沿著手臂爬升。",
                    "{actor} 的身影在雷鳴中一閃。",
                ),
                "succor": (
                    "{actor} 讓雷光在體內流轉。",
                    "{actor} 的動作快得只剩殘影。",
                    "{actor} 藉著電光穩住了身形。",
                ),
            }
        ),
        "ice": MappingProxyType(
            {
                "assault": (
                    "{actor} 的掌心凝出一枚冰棱。",
                    "{actor} 抬手，寒氣沿著地面蔓延。",
                    "{actor} 的吐息化作白霧。",
                ),
                "succor": (
                    "{actor} 讓寒氣悄然裹住自己。",
                    "{actor} 的傷處被薄冰封住。",
                    "{actor} 在冷意中重新站穩。",
                ),
            }
        ),
        "light": MappingProxyType(
            {
                "assault": (
                    "{actor} 的掌心亮起一線聖光。",
                    "{actor} 抬手，光矢破空而出。",
                    "{actor} 的身周泛起刺目的白。",
                ),
                "succor": (
                    "{actor} 讓光溫柔地落在身上。",
                    "{actor} 的傷口在光裡逐漸合攏。",
                    "{actor} 的呼吸被聖意托住。",
                ),
            }
        ),
        "dark": MappingProxyType(
            {
                "assault": (
                    "{actor} 的影子忽然拉長。",
                    "{actor} 抬手，暗色在指間凝聚。",
                    "{actor} 的低語引來一片陰影。",
                ),
                "succor": (
                    "{actor} 讓黑暗悄然包住自己。",
                    "{actor} 的影子替他擋下了什麼。",
                    "{actor} 在暗處重新穩住了氣息。",
                ),
            }
        ),
    }
)

CATEGORY_ACTIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "elemental_magic": (
            "{actor} 催動元素，力量在掌心成形。",
            "{actor} 的詠唱在空氣裡散開。",
        ),
        "martial_arts": (
            "{actor} 的劍勢毫不遲疑地遞出。",
            "{actor} 沉肩進步，手中兵刃化作一線。",
            "{actor} 的腳步一錯，招式順勢展開。",
        ),
        "holy_rite": (
            "{actor} 的低語在空氣裡散開。",
            "{actor} 抬手畫下一個古老的記號。",
            "{actor} 讓禱詞落在自己身上。",
        ),
        "divine_mystery": (
            "{actor} 的口中吐出古老的音節。",
            "{actor} 的舉止帶著不屬於凡人的重量。",
            "{actor} 抬手，神域的力量隨之回應。",
        ),
        "enhancement": (
            "{actor} 收斂心神，將力量導入身體。",
            "{actor} 的氣息在體內逐層沉澱。",
            "{actor} 閉上眼，把意識收束成一線。",
        ),
        "utility": (
            "{actor} 依照所學出手。",
            "{actor} 的動作謹慎而準確。",
        ),
    }
)

SEXUAL_ACT_ACTIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "獨處": (
            "{actor} 的指尖沿著自己的曲線滑下。",
            "{actor} 讓呼吸逐步沉進自己的身體裡。",
            "{actor} 在無人的角落裡動了起來。",
        ),
        "羞恥": (
            "{actor} 故意讓自己的模樣落進旁人眼裡。",
            "{actor} 沒有遮掩，反而迎上那些視線。",
            "{actor} 把羞澀壓下去，抬起頭來。",
        ),
        "關係": (
            "{actor} 朝對方靠近，帶著明確的意圖。",
            "{actor} 放低姿態，試探地伸出手。",
            "{actor} 的目光先落在對方身上。",
        ),
        "戰鬥": (
            "{actor} 在廝殺的縫隙裡尋找靠近的機會。",
            "{actor} 藉著交錯的身形縮短距離。",
            "{actor} 趁著空檔朝對方伸手。",
        ),
        "異種": (
            "{actor} 朝那具非人的身軀探出手。",
            "{actor} 試著靠近那副陌生的身體。",
            "{actor} 朝不屬於人的溫度伸手。",
        ),
        "神之秘法": (
            "{actor} 的舉止帶著神域的氣息。",
            "{actor} 抬手，某種更高的意志隨之落下。",
            "{actor} 的低語像是某種不容拒絕的宣告。",
        ),
        "sexual_act": (
            "{actor} 的動作帶著明確的意圖。",
            "{actor} 朝對方靠近了一步。",
            "{actor} 朝對方伸出手。",
        ),
    }
)


def _has_damage(skill: SkillDef) -> bool:
    return any(isinstance(effect, DamageEffect) for effect in skill.parsed_effects)


def elemental_shape(skill: SkillDef) -> str:
    """Return ``assault`` for a damaging spell, else ``succor``."""
    if _has_damage(skill):
        return "assault"
    if any(
        isinstance(effect, (HealEffect, SelfHealEffect))
        for effect in skill.parsed_effects
    ):
        return "succor"
    return "succor"


def family_key(skill: SkillDef) -> str:
    """Return the family-tier key one skill resolves through."""
    category = skill.category
    if category is SkillCategory.SEXUAL_ACT:
        return f"sexual_act:{skill.group}" if skill.group else "sexual_act"
    if category is SkillCategory.ELEMENTAL_MAGIC:
        element = skill.element.key if skill.element is not None else None
        if element is None:
            return "elemental_magic"
        return f"elemental_magic:{element}:{elemental_shape(skill)}"
    return category.value


def base_family_key(family: str) -> str:
    """Return the generic tier below one specific family key."""
    if family.startswith("elemental_magic:"):
        return "elemental_magic"
    if family.startswith("sexual_act:"):
        return "sexual_act"
    return family


def _row(key: str, action: tuple[str, ...]) -> tuple[str, NarrationRow]:
    return key, NarrationRow(key=key, action=action)


def _family_rows() -> dict[str, NarrationRow]:
    rows: dict[str, NarrationRow] = {}
    for element, shapes in ELEMENTAL_ACTIONS.items():
        for shape, action in shapes.items():
            key, row = _row(f"elemental_magic:{element}:{shape}", action)
            rows[key] = row
    for key, action in CATEGORY_ACTIONS.items():
        rows[key] = NarrationRow(key=key, action=action)
    for line, action in SEXUAL_ACT_ACTIONS.items():
        key = f"sexual_act:{line}"
        rows[key] = NarrationRow(key=key, action=action)
    return rows


FAMILY_ROWS: Mapping[str, NarrationRow] = MappingProxyType(_family_rows())


__all__ = [
    "CATEGORY_ACTIONS",
    "ELEMENTAL_ACTIONS",
    "ELEMENTAL_SHAPES",
    "FAMILY_ROWS",
    "PENDING_FAMILIES",
    "SEXUAL_ACT_ACTIONS",
    "base_family_key",
    "elemental_shape",
    "family_key",
]
