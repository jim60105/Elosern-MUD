"""Synthetic initialized NPC for the real persona-editor browser journeys."""

import os

NPC_NAME = "人物設定測試員"
NPC_SECOND_NAME = "二號人物設定測試員"
SECONDARY_CHARACTER_NAME = "BrowserTestAlt"
HOLDING_ROOM_NAME = "人物設定暫存室"


def _npc_persona_fixture(character, account=None) -> None:
    """Initialize an independent card through the sole persona writer."""
    if os.environ.get("ELOSERN_BROWSER_NPC_PERSONA") != "1":
        return

    from evennia.utils.create import create_object
    from typeclasses.components import ScriptedDialogue
    from typeclasses.npcs import NPC
    from typeclasses.rooms import Room
    from typeclasses.characters import PlayerCharacter
    from web.browser_support.browser_fixtures_data import SYNTH_DIALOGUE_TABLE_KEY
    from world.rules.npc_persona import initialize_npc_persona
    from world.rules.character_creation import (
        CharacterCreationRequest,
        activate_player_character,
        resolve_starting_profile,
    )

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

    npc2 = create_object(NPC, key=NPC_SECOND_NAME, location=character.location)
    npc2.components.add(ScriptedDialogue.create(npc2, dialogue_key=SYNTH_DIALOGUE_TABLE_KEY))
    initialize_npc_persona(
        npc2,
        {
            "identity": {"public": "市集的檢驗員", "hidden": "工會秘探"},
            "appearance": "戴著銅框眼鏡",
            "personality": "一絲不苟",
            "speech_style": "說話嚴肅而準確",
            "life_story": "長年在市集查驗貨物",
            "habit": "隨身攜帶記事簿",
            "social_connection": "",
        },
        {"kind": "import", "record": "browser-npc-persona-2"},
    )

    holding_room = create_object(Room, key=HOLDING_ROOM_NAME, nohome=True)
    holding_room.save()

    # Create second activated character on the browser account
    if account is None:
        account = getattr(character, "account", None) or getattr(character, "db_account", None)
    if account:
        if hasattr(account, "characters") and character not in account.characters:
            account.characters.add(character)
        char2, errs = account.create_character(key=SECONDARY_CHARACTER_NAME)
        if not char2:
            raise AssertionError(f"create_character failed: {errs}")
        char2.location = character.location
        char2.home = character.location
        char2.save()
        if hasattr(account, "characters"):
            account.characters.add(char2)
            account.characters.add(character)
        account.db._playable_characters = [character, char2]

        synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
        if synth:
            req = CharacterCreationRequest(
                mode="preset",
                preset_key="t_ash_finch",
                skip_portrait=True,
            )
        else:
            from web.browser_support.browser_fixtures_data import (
                SHIPPED_BASE_RACE,
                SHIPPED_BASE_SUBRACE,
            )
            profile = resolve_starting_profile(SHIPPED_BASE_RACE, SHIPPED_BASE_SUBRACE)
            rem = profile.budget
            allocs = {}
            for k, (l, u) in profile.bounds:
                val = min(u - l, rem)
                allocs[k] = val
                rem -= val
            req = CharacterCreationRequest(
                mode="custom",
                display_name=SECONDARY_CHARACTER_NAME,
                age=22,
                apparent_age=22,
                race=SHIPPED_BASE_RACE,
                subrace=SHIPPED_BASE_SUBRACE,
                allocations=allocs,
                skip_portrait=True,
            )
        activate_player_character(account, char2, req)
        char2.traits.mp.rate = 0
        char2.traits.mp.current = int(char2.traits.mp.max)
        char2.save()
        # Preserve _last_puppet as the primary character
        account.db._last_puppet = character

    print("seeded NPC persona editor fixture")
