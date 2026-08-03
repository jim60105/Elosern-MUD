"""Deterministic account/character seeding for browser acceptance tests.

Run as a one-off process against a freshly migrated browser-test database:

    ELOSERN_BROWSER_* uv run --locked python -m web.tests.browser.seed

The harness runs ``evennia migrate`` first. This process then creates Account
#1 (the superuser Evennia's launcher requires), an activated adult
PlayerCharacter owned by that account, a start room, and places the character
in it. The world bootstrap (lore sync, maps, clock, guard NPC) is left to the
managed server's ``at_server_start`` hook. Everything is deterministic: no
network service, no LLM, and no random sampling beyond the validated magic
band seeded to its deterministic lower bound.

Importing this module has no side effects; all setup and database work happens
only when it is executed as ``python -m web.tests.browser.seed``.
"""

import os

# Deterministic fixture identity. Password is fixed so Playwright can log in.
BROWSER_ACCOUNT_USERNAME = os.environ.get("ELOSERN_BROWSER_ACCOUNT", "browserplayer")
BROWSER_ACCOUNT_EMAIL = "browser@example.test"
BROWSER_ACCOUNT_PASSWORD = os.environ.get(
    "ELOSERN_BROWSER_PASSWORD", "ElosernBrowserTest!2026"
)
BROWSER_CHARACTER_NAME = os.environ.get("ELOSERN_BROWSER_CHARACTER", "BrowserTest")
BROWSER_ROOM_NAME = os.environ.get("ELOSERN_BROWSER_ROOM", "測試起點")


def main() -> None:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "web.tests.browser.browser_settings"
    )

    import django

    django.setup()

    import evennia

    evennia._init()

    from evennia.utils.create import create_account, create_object

    from typeclasses.accounts import Account
    from typeclasses.characters import PlayerCharacter
    from typeclasses.monsters import Monster
    from typeclasses.rooms import Room
    from world.rules.character_creation import (
        CharacterCreationRequest,
        activate_player_character,
        resolve_starting_profile,
    )

    def balanced_allocations(race_key: str, subrace_key: str | None = None) -> dict[str, int]:
        """Spend the exact starting budget deterministically from the profile bounds."""
        profile = resolve_starting_profile(race_key, subrace_key)
        remaining = profile.budget
        result: dict[str, int] = {}
        for key, (lower, upper) in profile.bounds:
            value = min(upper - lower, remaining)
            result[key] = value
            remaining -= value
        if remaining != 0:
            raise AssertionError("starting profile budget exceeds allocatable spans")
        return result

    def sampler(_low: int, _high: int) -> int:
        """Fixed magic-band sample: deterministic lower bound."""
        return _low

    account = create_account(
        BROWSER_ACCOUNT_USERNAME,
        BROWSER_ACCOUNT_EMAIL,
        BROWSER_ACCOUNT_PASSWORD,
        typeclass=Account,
        is_superuser=True,
    )

    character = create_object(PlayerCharacter, key=BROWSER_CHARACTER_NAME, nohome=True)
    account.at_post_create_character(character)
    account.db._last_puppet = character

    room = create_object(Room, key=BROWSER_ROOM_NAME, nohome=True)
    character.location = room
    character.home = room
    character.save()

    request = CharacterCreationRequest(
        mode="custom",
        display_name=BROWSER_CHARACTER_NAME,
        age=20,
        apparent_age=20,
        race="human",
        subrace=None,
        allocations=balanced_allocations("human"),
    )
    result = activate_player_character(account, character, request, sampler=sampler)

    # Deterministic combat fixtures (webclient-combat-menu): grant active
    # skills covering every TargetSpec and spawn two living monsters in the
    # start room so browser tests can ``engage`` one through the real server.
    character.db.skills = {
        "active": ["fire_ball", "wind_blade", "status_disguise", "concentration"],
        "passive": ["defense_instinct"],
    }
    # A persistent poisoned buff gives the status panel a deterministic
    # applied-modifier condition (agility -10%) for viewport assertions.
    from world.rules.buffs import _add_buff

    _add_buff(character, "poisoned")
    for index, (monster_key, hp) in enumerate(
        (("goblin", 200), ("wolf", 200)), start=1
    ):
        monster = create_object(Monster, key=monster_key, nohome=True)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = hp
        monster.traits.hp.current = hp
        monster.location = room
        monster.save()
    print(
        f"seeded account={account.key} character={result.display_name} "
        f"race={result.race} magic_level={result.magic_level}"
    )


if __name__ == "__main__":
    main()
