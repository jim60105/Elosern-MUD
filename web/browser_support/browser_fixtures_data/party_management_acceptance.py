"""Dedicated party-management acceptance fixture identity and composition rules.

The managed browser harness offers an opt-in pre-session seed that supplies
the exact co-located companions 艾拉 and 卡恩 plus the physical prerequisites
the party-management acceptance journey needs. This module owns the fixture's
stable identity (object tags, authored names, starting-state constants) and
the composition guard, so the seed process, the server-side consumers and the
tests read one declaration.

The fixture is accepted ONLY in the isolated synthetic managed runtime. It
rejects incompatible overlapping party/service composition flags with a
setup diagnostic before any database mutation, instead of relying on
order-dependent fixture overwrites.
"""

from __future__ import annotations

from collections.abc import Mapping

from web.browser_support.browser_fixtures_data.fixture_values import (
    SYNTH_SHOP_KEY,
    SYNTH_STORE_OPEN_SECONDS,
)

#: The opt-in flag the managed runtime sets on the seed process environment.
FIXTURE_FLAG = "ELOSERN_BROWSER_PARTY_MANAGEMENT_ACCEPTANCE"

#: Tag category of every object this fixture authors. Tags are the stable
#: identity tests use; authored keys are presentation only.
FIXTURE_TAG_CATEGORY = "browser_fixture"

#: Exact authored display identities (never a positional companion pick).
AIRA_NAME = "艾拉"
KAHN_NAME = "卡恩"

AIRA_TAG = "t_party_acceptance_aira"
KAHN_TAG = "t_party_acceptance_kahn"
STORE_ROOM_TAG = "t_party_acceptance_store"
SAFE_ROOM_TAG = "t_party_acceptance_safe_room"
STORE_EXIT_TAG = "t_party_acceptance_store_exit"
RETURN_EXIT_TAG = "t_party_acceptance_return_exit"
MERCHANT_TAG = "t_party_acceptance_merchant"
MONSTER_TAG = "t_party_acceptance_monster"

#: Every tag that proves fixture state already exists (fresh-runtime guard).
FIXTURE_TAGS = (
    AIRA_TAG,
    KAHN_TAG,
    STORE_ROOM_TAG,
    SAFE_ROOM_TAG,
    STORE_EXIT_TAG,
    RETURN_EXIT_TAG,
    MERCHANT_TAG,
    MONSTER_TAG,
)

#: Authored presentation identity (free-form prose, never a catalog key).
STORE_ROOM_NAME = "苔徑驗收商鋪"
STORE_ROOM_DESC = "一間為隊伍驗收準備的合成商鋪，後門通往安靜的院子。"
SAFE_ROOM_NAME = "商鋪後院"
SAFE_ROOM_DESC = "商鋪後方的安靜院落，遠離街道與野獸。"
MERCHANT_NAME = "驗收商人"
STORE_EXIT_KEY = "後門"
RETURN_EXIT_KEY = "回到商鋪"
MONSTER_NAME = "驗收燼蟲"

#: Starting-state table. These are the fixture's declared deterministic
#: resources; the acceptance journey must be executable from exactly these.
COMMANDER_HP_DEFICIT = 60
AIRA_HP_DEFICIT = 25
KAHN_HP_DEFICIT = 30
COMMANDER_WALLET = 1000
PURCHASE_QUANTITY = 3
TRANSFER_QUANTITY = 2
MINIMUM_PURCHASABLE_POTIONS = 3

POTION_KEY = "t_ember_spray"
SPARE_WEAPON_KEY = "t_cinder_dirk"
STARTING_WEAPON_KEY = "t_thorn_knife"
SALE_ITEM_KEY = POTION_KEY
HEAL_SKILL_KEY = "t_hush_mend"
OPENER_SKILL_KEY = "t_ember_burst"

#: 艾拉: the heal and the hostile opener are her OWN lineage grants; her bag
#: holds the equipped knife, the spare alternative and four potions.
AIRA_INVENTORY = (
    (STARTING_WEAPON_KEY, 1),
    (SPARE_WEAPON_KEY, 1),
    (POTION_KEY, 4),
)
AIRA_EQUIPPED_KEY = STARTING_WEAPON_KEY
#: 卡恩: one real usable consumable of his own and nothing else.
KAHN_INVENTORY = ((POTION_KEY, 1),)
#: One nearby living hostile the pair can finish deterministically.
MONSTER_HP = 40
MONSTER_ATTACK = 3

#: The world-clock tick the merchant is open at (catalog hours 08:00-20:00).
STORE_OPEN_SECONDS = SYNTH_STORE_OPEN_SECONDS
#: The kit shop whose catalog offers stock the merchant host.
SHOP_KEY = SYNTH_SHOP_KEY

#: Fixture flags that compose overlapping party/service state and therefore
#: cannot run beside the dedicated fixture. The value check treats an empty
#: string and "0" as absent; any other value is a composition.
INCOMPATIBLE_FLAGS: Mapping[str, str] = {
    "ELOSERN_BROWSER_PARTY_ACCEPTANCE": "seeds its own bound companion grants",
    "ELOSERN_BROWSER_COMPANION_LINEUP": "seeds a full positional companion party",
    "ELOSERN_BROWSER_COMPANION_FIELD_CAST": "grants skills to the first companion",
    "ELOSERN_BROWSER_EXPLORATION": "places the character at the South Gate",
    "ELOSERN_BROWSER_SERVICES": "composes shop/companion/inventory modes",
    "ELOSERN_BROWSER_CREATION": "returns before the gameplay seed",
    "ELOSERN_BROWSER_COMBAT_SEAL": "locks equipment toggles through an exam seal",
}


def _is_set(value: str | None) -> bool:
    return value is not None and value not in ("", "0")


def composition_error(environ: Mapping[str, str]) -> str | None:
    """Return the setup diagnostic for one invalid composition, else ``None``.

    The dedicated fixture is an isolated synthetic-runtime fixture: it is
    meaningless (and would silently substitute shipped catalog rows) outside
    ``ELOSERN_BROWSER_SYNTH_CATALOGS=1``. Overlapping party/service fixture
    flags are rejected here rather than letting flag order decide which seed
    state wins.
    """
    if not _is_set(environ.get(FIXTURE_FLAG)):
        return None
    if environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") != "1":
        return (
            f"{FIXTURE_FLAG}=1 requires ELOSERN_BROWSER_SYNTH_CATALOGS=1 "
            "(the isolated synthetic managed runtime)"
        )
    for flag, reason in INCOMPATIBLE_FLAGS.items():
        if _is_set(environ.get(flag)):
            return (
                f"{FIXTURE_FLAG}=1 is incompatible with {flag}="
                f"{environ.get(flag)!r} ({reason})"
            )
    return None


__all__ = [
    "AIRA_EQUIPPED_KEY",
    "AIRA_HP_DEFICIT",
    "AIRA_INVENTORY",
    "AIRA_NAME",
    "AIRA_TAG",
    "COMMANDER_HP_DEFICIT",
    "COMMANDER_WALLET",
    "FIXTURE_FLAG",
    "FIXTURE_TAGS",
    "FIXTURE_TAG_CATEGORY",
    "HEAL_SKILL_KEY",
    "INCOMPATIBLE_FLAGS",
    "KAHN_HP_DEFICIT",
    "KAHN_INVENTORY",
    "KAHN_NAME",
    "KAHN_TAG",
    "MERCHANT_NAME",
    "MERCHANT_TAG",
    "MINIMUM_PURCHASABLE_POTIONS",
    "MONSTER_ATTACK",
    "MONSTER_HP",
    "MONSTER_NAME",
    "MONSTER_TAG",
    "OPENER_SKILL_KEY",
    "POTION_KEY",
    "PURCHASE_QUANTITY",
    "RETURN_EXIT_KEY",
    "RETURN_EXIT_TAG",
    "SAFE_ROOM_DESC",
    "SAFE_ROOM_NAME",
    "SAFE_ROOM_TAG",
    "SALE_ITEM_KEY",
    "SHOP_KEY",
    "SPARE_WEAPON_KEY",
    "STARTING_WEAPON_KEY",
    "STORE_EXIT_KEY",
    "STORE_EXIT_TAG",
    "STORE_OPEN_SECONDS",
    "STORE_ROOM_DESC",
    "STORE_ROOM_NAME",
    "STORE_ROOM_TAG",
    "TRANSFER_QUANTITY",
    "composition_error",
]
