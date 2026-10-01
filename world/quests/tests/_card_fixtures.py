"""Synthetic compact NPC card fixtures for generated-quest occupant tests.

Every ``npc_req`` occupant carries a complete compact card
(npc-persona-generated-quest-cards D1), so payload and requirement builders
across the quest, scenario-director, and scene-builder tests share these
file-local synthetic cards. The prose is generic synthetic text and names no
shipped content.
"""

from world.lore.npc_card import NpcCard, normalize_card


def occupant_card_record(tag: str = "") -> dict:
    """Return one valid synthetic card record; ``tag`` varies the prose."""
    return {
        "identity": {
            "public": f"在試煉場景中現身的測試住民{tag}。",
            "hidden": "",
        },
        "appearance": f"身形普通的測試住民{tag}，披著灰色斗篷。",
        "personality": "謹慎而寡言，遇事先觀察再行動。",
        "speech_style": "說話簡短低沉，習慣在句尾停頓片刻。",
        "life_story": "自幼在邊境長大，靠替旅人帶路維生。",
        "habit": "每到黃昏便擦拭隨身短刀。",
        "social_connection": "",
    }


def occupant_card(tag: str = "") -> NpcCard:
    """Return the normalized ``NpcCard`` of :func:`occupant_card_record`."""
    return normalize_card(occupant_card_record(tag))
