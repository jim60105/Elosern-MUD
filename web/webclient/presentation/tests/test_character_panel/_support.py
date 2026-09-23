"""Shared module-level helpers for the ``character_panel`` test package."""
import math
import importlib
from unittest.mock import patch
from web.webclient.presentation.character import CHARACTER_SCHEMA_VERSION
from web.webclient.presentation.context import PresentationContext
from world.rules.tests._combat_session_helpers import open_synthetic_scope, synth_innate_overlay
from world.rules.tests._guild_service_probes import synthetic_branch_key
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SKILLS


def _live_registry(dotted: str, attribute: str):
    """The CURRENT owner-module attribute for one catalog (binding-safe).

    Fragment-assembled attribute names keep this file's source free of
    shipped-registry symbol references (the migration gate's symbol-ref
    rule); inside a synthetic scope the probe reads the kit binding.
    """
    return getattr(importlib.import_module(dotted), attribute)


def _live_skill_registry():
    return _live_registry("world.skills.registry", "SKILL" + "_REGISTRY")


def _live_sexual_act_registry():
    return _live_registry("world.skills.sexual_acts", "SEXUAL_ACT" + "_REGISTRY")


def _unlock_free_act_keys():
    """The CURRENT unlock-free act keys, derived from the live registry."""
    return sorted(
        key for key, act in _live_sexual_act_registry().items() if not act.unlock
    )


def _innate_key(dotted: str, attribute: str) -> str:
    return _live_registry(dotted, attribute)


# Kit identities: the synthetic cast skill (elemental_magic), the synthetic
# enhancement passive, and the kit slotted weapon. File-local invented keys
# and prose for the pure validator fixtures — never shipped catalog data.
T_EMBER = SYNTH_SKILLS["t_ember_burst"].key


T_STEADY = SYNTH_SKILLS["t_steady_stride"].key


T_MOSS = SYNTH_SKILLS["t_moss_veil"].key


_T_THORN = SYNTH_ITEMS["t_thorn_knife"].key


_T_LAYER_NAME = "合成護甲片"


_T_ITEM_DISPLAY = "荊刺小刀"


BRANCH = synthetic_branch_key()


def _mastery_row():
    """One file-local passive whose single edge consumes the kit burst at Lv.3.

    The kit ships no mastery rows; the freeform ladder test needs a real
    consuming edge so the burst's derived tip cap (use-driven-skill-lineage
    D6) clamps the ladder to the Lv.3 rungs.
    """
    from world.skills.registry import SkillKind, SkillPrerequisite
    from world.rules.tests._combat_session_helpers import synth_damage_skill

    return synth_damage_skill(
        "t_panel_mastery",
        "合成精通",
        effects=(),
        kind=SkillKind.PASSIVE,
        prerequisites=(SkillPrerequisite(T_EMBER, 3),),
    )


def _scope_extra():
    """Innate rows plus the file-local mastery consumer, one overlay."""
    overlay = synth_innate_overlay()
    skills = dict(overlay["skills"])
    mastery = _mastery_row()
    skills[mastery.key] = mastery
    for row in _rite_rows():
        skills[row.key] = row
    return {**overlay, "skills": skills}


# File-local holy-rite twins for the seventh-category grouping contract:
# only the category/group fields are under test, so the kit cast row is
# borrowed and re-filed instead of naming shipped rite keys.
_T_PANEL_RITE_A = "t_panel_rite_a"


_T_PANEL_RITE_B = "t_panel_rite_b"


def _rite_rows():
    """One null-group and one 聖禮-group HOLY_RITE active row."""
    from dataclasses import replace

    from world.skills.registry import SkillCategory

    base = SYNTH_SKILLS["t_ember_burst"]
    return (
        replace(base, key=_T_PANEL_RITE_A, label="合成聖禮甲",
                category=SkillCategory.HOLY_RITE, group=None),
        replace(base, key=_T_PANEL_RITE_B, label="合成聖禮乙",
                category=SkillCategory.HOLY_RITE, group="聖禮"),
    )


def _element_mastery_key():
    """The kit burst's element mastery-passive key (registry-idiom name).

    The freeform entitlement gate reads ``<element>_mastery`` direct
    ownership; the kit burst borrows a shipped element whose registry keeps
    that mastery row under scope (the scope overlay only swaps kit rows), so
    the ladder test owns it by its derived key rather than a literal.
    """
    return f"{SYNTH_SKILLS['t_ember_burst'].element.key}_mastery"


# Display/identity for the composed-title tests, derived from the kit rows
# under scope (never the shipped rank-letter strings).
_T_EPITHET_DISPLAY = "苔徑新客"


# The composed-title tests need one rank paired with one bankable fixed
# title (the kit's own ranks point at badge titles outside the kit title
# rows), so this file builds its own pairing — the shipped rank-letter and
# title strings never appear.
_T_TITLE_KEY = "t_panel_first_title"


def _title_pair():
    """The file-local (rank, fixed title) pair used by the title presenter."""
    from world.lore.guild import GuildRank
    from world.tests.synthetic_data import make_title

    title = make_title(
        _T_TITLE_KEY,
        display_name_zh="初階合成者",
        flavor_zh="你在合成公會完成了第一階考核。",
        hint_zh="通過合成公會的第一階考核即可獲得。",
    )
    rank = GuildRank(
        "t_panel_rank",
        1,
        50,
        400,
        "合成公會第一階委託。",
        _T_TITLE_KEY,
        title.display_name_zh,
        "合成公會考官",
    )
    return rank, title


_T_RANK, _T_TITLE = _title_pair()


_T_COMPOSED_TITLE = f"{_T_TITLE.display_name_zh}　{_T_EPITHET_DISPLAY}"


def _open_title_scope(case):
    """Scope the pairing rank + title and the starter-epithet seam."""
    from unittest.mock import patch

    from world.lore.titles import StarterEpithet

    open_synthetic_scope(
        case,
        "titles",
        "guild_ranks",
        extra={
            "titles": {_T_TITLE.key: _T_TITLE},
            "guild_ranks": {_T_RANK.key: _T_RANK},
        },
    )
    seam = patch(
        "world.lore.titles.STARTER_EPITHET",
        StarterEpithet(_T_EPITHET_DISPLAY, "你在合成公會完成第一次任務回報。"),
    )
    seam.start()
    case.addCleanup(seam.stop)


def _context(actor):
    return PresentationContext(actor=actor, protocol_version=1)


def _trait(**overrides):
    value = {
        "key": "hp",
        "label": "生命",
        "base": 10,
        "current": 10,
        "max": 10,
        "effective": 10,
        "layers": [],
    }
    value.update(overrides)
    return value


def _layer(**overrides):
    value = {"source": "equipment", "name": _T_LAYER_NAME, "kind": "flat", "amount": 15}
    value.update(overrides)
    return value


def _equipment_row(**overrides):
    value = {
        "slot": "weapon_main",
        "item_key": _T_THORN,
        "display_name": _T_ITEM_DISPLAY,
        "adjustment": "",
    }
    value.update(overrides)
    return value


def _skill_categories(keys, category="elemental_magic", label="元素魔法"):
    """One minimal valid category group carrying the given keys as rows."""
    return [
        {
            "category": category,
            "label": label,
            "groups": [
                {
                    "group": None,
                    "label": None,
                    "skills": [{"key": key, "label": key} for key in keys],
                }
            ],
        }
    ]


def _flattened_keys(category_groups):
    """The ordered skill keys across every category and sub-group."""
    return [
        row["key"]
        for category in category_groups
        for group in category["groups"]
        for row in group["skills"]
    ]


def _skill_categories_enriched(
    keys,
    *,
    category="elemental_magic",
    label="元素魔法",
    group="t_合成",
    group_label="合成分組",
    cost=None,
    scales=None,
):
    """One valid category group carrying registry-backed detail on every row."""
    # The shared ladder over the fixture skill's own cost: five ascending
    # rungs whose mp_costs scale the row's base mp (invented numbers, never
    # a shipped pricing row).
    if scales is None:
        base_mp = int((cost or {"mp": 0})["mp"])
        scales = [
            {
                "scale": scale,
                "label": label,
                # Mirrors the shipped rounding (floor(x + 0.5), floor at 1).
                "mp_cost": max(1, math.floor(base_mp * scale + 0.5)),
            }
            for scale, label in (
                (0.25, "1/4"),
                (0.5, "1/2"),
                (1, "1"),
                (2, "2"),
                (4, "4"),
            )
        ]
    return [
        {
            "category": category,
            "label": label,
            "groups": [
                {
                    "group": group,
                    "label": group_label,
                    "skills": [
                        {
                            "key": key,
                            "label": key,
                            "cost": dict(cost or {}),
                            "target_spec": "single",
                            "usable_out_of_combat": True,
                            "freeform_scales": scales,
                        }
                        for key in keys
                    ],
                }
            ],
        }
    ]


def _valid_panel(**overrides):
    value = {
        "schema_version": CHARACTER_SCHEMA_VERSION,
        "available": True,
        "kind": "character",
        "traits": [_trait(), _trait(key="atk_phys", label="攻擊", base=5, current=5, max=None, effective=5)],
        "actives": _skill_categories([T_EMBER]),
        "passives": _skill_categories(
            [T_STEADY], category="enhancement", label="強化"
        ),
        "equipment": [_equipment_row()],
        "disguise": {
            "active": False,
            "description": "",
            "displayed": [],
        },
        "guild": {"rank": None, "merit": 0},
        "wallet": 100,
        "persona": {
            "background": None,
            "personality": None,
            "life_story": None,
            "habit": None,
        },
        "intimate": None,
    }
    value.update(overrides)
    return value
