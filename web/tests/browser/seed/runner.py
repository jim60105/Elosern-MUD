"""Seed-process entry point.

Slice of the former ``web/tests/browser/seed.py`` module;
every body ships verbatim."""

import os

from web.tests.browser.seed.identity import (
    BROWSER_ACCOUNT_EMAIL,
    BROWSER_ACCOUNT_PASSWORD,
    BROWSER_ACCOUNT_USERNAME,
    BROWSER_CHARACTER_NAME,
    BROWSER_ROOM_NAME,
    CREATION_ACCOUNT_EMAIL,
    CREATION_ACCOUNT_PASSWORD,
    CREATION_ACCOUNT_USERNAME,
)
from web.tests.browser.seed.art_fixture import _art_fixture
from web.tests.browser.seed.exploration_fixture import _exploration_fixture
from web.tests.browser.seed.minimap_fixture import _minimap_fixture
from web.tests.browser.seed.options_surface_fixture import _options_surface_fixture
from web.tests.browser.seed.services_fixture import _services_fixture
from web.tests.browser.seed.titles_fixture import _titles_fixture


def main() -> None:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "web.tests.browser.browser_settings"
    )

    import django

    django.setup()

    import evennia

    evennia._init()

    # Synthetic-catalog process install (kit design D2b): the kit imports
    # Evennia contrib code that needs evennia._init() first, so the flag
    # check lives here rather than in settings load. The harness shares ONE
    # install path with the server process (``browser_startstop``): import the
    # shipped-rulebook cross-validators BEFORE the swap, install the kit,
    # redirect the boot quest catalog, graft the entry rank, and assign the
    # shared synthetic guild-economy catalog.
    from web.tests.browser.browser_startstop import _install_synthetic_catalogs_if_flagged

    _install_synthetic_catalogs_if_flagged()

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

    account = create_account(
        BROWSER_ACCOUNT_USERNAME,
        BROWSER_ACCOUNT_EMAIL,
        BROWSER_ACCOUNT_PASSWORD,
        typeclass=Account,
        is_superuser=True,
    )

    if os.environ.get("ELOSERN_BROWSER_CREATION") == "1":
        # A pending-creation account (webclient-character-creation-ui): the
        # auto-created shell is creation-pending with an empty trait set and no
        # activation, exactly as a freshly registered account sees it.
        # Optionally a validated custom draft is saved so browser journeys can
        # resume at the custom_filled stage. The South Gate and world clock are
        # created by the managed server's own at_server_start bootstrap.
        # Evennia's initial setup assumes ObjectDB #1 is the superuser
        # character and #2 is 虛境 (the renamed starting room): it locks #1 with
        # ``puppet:false()`` and
        # wipes the superuser account's attributes. So #1 is a dedicated dummy
        # superuser character and the pending shell is #3, owned by a
        # non-superuser account the initial setup never touches.
        superuser_character = create_object(
            PlayerCharacter, key=BROWSER_CHARACTER_NAME, nohome=True
        )
        account.at_post_create_character(superuser_character)
        superuser_character.db_account = account
        room = create_object(Room, key=BROWSER_ROOM_NAME, nohome=True)
        superuser_character.location = room
        superuser_character.home = room
        superuser_character.save()
        account.db._last_puppet = superuser_character

        pending = create_object(PlayerCharacter, key="creation-shell", nohome=True)
        creator = create_account(
            CREATION_ACCOUNT_USERNAME,
            CREATION_ACCOUNT_EMAIL,
            CREATION_ACCOUNT_PASSWORD,
            typeclass=Account,
        )
        creator.at_post_create_character(pending)
        pending.db_account = creator
        pending.location = room
        pending.home = room
        pending.save()
        creator.db._last_puppet = pending
        if os.environ.get("ELOSERN_BROWSER_CREATION_PRESET_DRAFT") == "1":
            from world.rules.creation_wizard import save_preset_draft

            from web.browser_support.browser_fixtures_data import SHIPPED_PRESET_KEY

            save_preset_draft(
                creator,
                pending,
                "t_pale_wren"
                if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
                else SHIPPED_PRESET_KEY,
            )
            pending.save()
        elif os.environ.get("ELOSERN_BROWSER_CREATION_DRAFT") == "1":
            from world.rules.creation_wizard import save_custom_draft

            _synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
            from web.browser_support.browser_fixtures_data import (
                SHIPPED_DRAFT_RACE,
                SHIPPED_DRAFT_SUBRACE,
            )

            save_custom_draft(
                creator,
                pending,
                CharacterCreationRequest(
                    mode="custom",
                    display_name="草稿角色",
                    age=21,
                    apparent_age=21,
                    race="t_duskmari" if _synth else SHIPPED_DRAFT_RACE,
                    subrace="t_duskmari_evensong" if _synth else SHIPPED_DRAFT_SUBRACE,
                    allocations=balanced_allocations(
                        "t_duskmari" if _synth else SHIPPED_DRAFT_RACE,
                        "t_duskmari_evensong" if _synth else SHIPPED_DRAFT_SUBRACE,
                    ),
                ),
            )
            pending.save()
        print(
            f"seeded pending creation account={creator.key} "
            f"character={pending.key} pending=True"
        )
        return

    character = create_object(PlayerCharacter, key=BROWSER_CHARACTER_NAME, nohome=True)
    account.at_post_create_character(character)
    account.db._last_puppet = character

    room = create_object(Room, key=BROWSER_ROOM_NAME, nohome=True)
    character.location = room
    character.home = room
    character.save()

    if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1":
        # Under the synthetic install every shipped catalog is t_-only, so the
        # base character activates from the kit's own preset card (its race,
        # subrace, skills, and starting items are all t_-keyed). The
        # shipped-prose fixtures below are not synthetic-aware; the flag is
        # documented as combinable with no other fixture flag.
        request = CharacterCreationRequest(
            mode="preset",
            preset_key="t_pale_wren",
            skip_portrait=True,
        )
    else:
        from web.browser_support.browser_fixtures_data import (
            SHIPPED_BASE_RACE,
            SHIPPED_BASE_SUBRACE,
        )

        request = CharacterCreationRequest(
            mode="custom",
            display_name=BROWSER_CHARACTER_NAME,
            age=20,
            apparent_age=20,
            race=SHIPPED_BASE_RACE,
            subrace=SHIPPED_BASE_SUBRACE,
            allocations=balanced_allocations(SHIPPED_BASE_RACE, SHIPPED_BASE_SUBRACE),
            # The art fixture below settles classic records deterministically;
            # the automatic gallery request (gallery-autogen-retrofit) must never
            # race it, so the seeded activation carries the explicit skip flag.
            skip_portrait=True,
        )
    result = activate_player_character(account, character, request)

    # Deterministic MP for the exact-cost cast journeys: gauge regen accrues
    # only inside player-driven clock advances (world/rules.clock settles it
    # on every advance source, combat included), so any advance between the
    # test's before-sample and the deduction commit shifts the pool and
    # breaks the exact-delta pins. Zero the seeded character's mp rate so the
    # pool moves only through casts (world.rules.tests.test_combat_party's
    # `hp.rate = 0` precedent, applied at the shared seed). Fill the pool to
    # the cap so every advertised scale stays castable from a settled start.
    character.traits.mp.rate = 0
    character.traits.mp.current = int(character.traits.mp.max)
    character.save()

    if os.environ.get("ELOSERN_BROWSER_MINIMAP") == "1":
        _minimap_fixture(character)

    _services_fixture(character)

    _art_fixture(character, room)
    _exploration_fixture(character)
    _options_surface_fixture(character)
    _titles_fixture(character)

    # Deterministic combat fixtures (webclient-combat-menu): grant active
    # skills covering every TargetSpec and spawn two living monsters in the
    # start room so browser tests can ``engage`` one through the real server.
    # The mastery passive additionally activates the freeform scale step for
    # the ladder skill (element-mastery-freeform-casting), exercised by the
    # scaled cast acceptance test.  ``grant_lineage`` closes the skill lineage
    # and seeds prerequisite proficiency so every requested ACTIVE skill is
    # actually castable under the lineage gate.  ``rungs`` raises the ladder
    # skill's OWN proficiency to the ladder's top level
    # (use-driven-skill-lineage DC5).  The grant set is mode-derived: the kit
    # rows under the synthetic install, the shipped rows otherwise.
    from world.rules.tests.combat_fixtures import grant_lineage
    from web.browser_support.browser_fixtures_data import (
        SHIPPED_COMBAT_ACTIVE_SKILLS,
        SHIPPED_COMBAT_DEBUFF_KEY,
        SHIPPED_COMBAT_LADDER_LEVEL,
        SHIPPED_COMBAT_LADDER_SKILL,
        SHIPPED_COMBAT_MONSTERS,
        SHIPPED_COMBAT_PASSIVE_SKILLS,
        SHIPPED_MONSTER_TIER_ATTR,
        SHIPPED_MONSTER_TIER_KEY,
        SYNTH_COMBAT_ACTIVE_SKILLS,
        SYNTH_COMBAT_DEBUFF_KEY,
        SYNTH_COMBAT_LADDER_LEVEL,
        SYNTH_COMBAT_LADDER_SKILL,
        SYNTH_COMBAT_MONSTERS,
        SYNTH_COMBAT_PASSIVE_SKILLS,
        SYNTH_INNATE_ATTACK_KEY,
        SYNTH_INNATE_FLEE_KEY,
        first_live_monster_tier_key,
    )

    synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
    # The universal attack/flee seam: shipped ownership arrives through the
    # human race baseline's innates; the kit race grants nothing, so the
    # grafted seam rows are owned explicitly under the synthetic install.
    active_skills = list(SYNTH_COMBAT_ACTIVE_SKILLS if synth else SHIPPED_COMBAT_ACTIVE_SKILLS)
    if synth:
        active_skills += [SYNTH_INNATE_ATTACK_KEY, SYNTH_INNATE_FLEE_KEY]
    # ``seed_lineage_proficiency`` honours an already-stored proficiency even
    # when it leaves an edge unmet, and the kit preset's activation writes a
    # low explicit value for t_ember_burst — so under the synthetic install
    # the prerequisite edges of the grant set are raised explicitly through
    # ``rungs`` (the ladder's own rung wins: rungs is applied after the seed).
    combat_rungs: dict[str, int] = {}
    if synth:
        from web.browser_support.browser_fixtures_data import lineage_rungs_for

        combat_rungs.update(
            lineage_rungs_for([*active_skills, *SYNTH_COMBAT_PASSIVE_SKILLS])
        )
    combat_rungs[SYNTH_COMBAT_LADDER_SKILL] = SYNTH_COMBAT_LADDER_LEVEL
    grant_lineage(
        character,
        active_skills,
        list(SYNTH_COMBAT_PASSIVE_SKILLS if synth else SHIPPED_COMBAT_PASSIVE_SKILLS),
        rungs=(
            combat_rungs
            if synth
            else {SHIPPED_COMBAT_LADDER_SKILL: SHIPPED_COMBAT_LADDER_LEVEL}
        ),
    )
    # A persistent buff gives the status panel a deterministic
    # applied-modifier condition for viewport assertions.
    from world.rules.buffs import apply_buff

    if synth:
        # The kit debuff stacks unique_per_source; a fixture source key names
        # the seed itself (free-form data, never a catalog key).
        apply_buff(character, SYNTH_COMBAT_DEBUFF_KEY, source_key="browser-seed")
    else:
        apply_buff(character, SHIPPED_COMBAT_DEBUFF_KEY)
    for monster_key, hp in (SYNTH_COMBAT_MONSTERS if synth else SHIPPED_COMBAT_MONSTERS):
        monster = create_object(Monster, key=monster_key, nohome=True)
        monster.threat_tier = first_live_monster_tier_key() if synth else SHIPPED_MONSTER_TIER_ATTR
        monster.apply_monster_tier(SHIPPED_MONSTER_TIER_KEY)
        monster.traits.hp.base = hp
        monster.traits.hp.current = hp
        monster.location = room
        monster.save()
    print(
        f"seeded account={account.key} character={result.display_name} "
        f"race={result.race} magic_power={result.magic_power}"
    )

