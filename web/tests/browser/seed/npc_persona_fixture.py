"""Synthetic initialized NPC for the real persona-editor browser journeys."""

import os

NPC_NAME = "人物設定測試員"


def _npc_persona_fixture(character) -> None:
    """Initialize an independent card through the sole persona writer."""
    if os.environ.get("ELOSERN_BROWSER_NPC_PERSONA") != "1":
        return

    from evennia.utils.create import create_object
    from typeclasses.components import ScriptedDialogue
    from typeclasses.npcs import NPC
    from web.browser_support.browser_fixtures_data import SYNTH_DIALOGUE_TABLE_KEY
    from world.rules.npc_persona import initialize_npc_persona

    npc = create_object(NPC, key=NPC_NAME, location=character.location)
    npc.components.add(ScriptedDialogue.create(npc, dialogue_key=SYNTH_DIALOGUE_TABLE_KEY))
    initialize_npc_persona(
        npc,
        {
            "identity": {"public": "渡口的記錄員", "hidden": "曾經是信差"},
            "appearance": "穿著灰色短褂",
            "personality": "謹慎而親切",
            "speech_style": "說話簡短",
            "life_story": "在渡口整理往來紀錄",
            "habit": "每天擦拭筆尖",
            "social_connection": "",
        },
        {"kind": "import", "record": "browser-npc-persona"},
    )
    print("seeded NPC persona editor fixture")
