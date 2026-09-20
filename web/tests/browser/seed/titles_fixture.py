"""Title-codex seeding fixture.

Slice of the former ``web/tests/browser/seed.py`` module;
every body ships verbatim."""

def _titles_fixture(character) -> None:
    """Deterministically prepare a title-codex fixture (title-codex-removal).

    Opted-in with ``ELOSERN_BROWSER_TITLES=1``. Banks two unlocked guild fixed
    titles (leaving others locked), two epithets — the first auto-equips, the
    newer one is removable — and persists one nomination ballot, so the codex
    window renders locked/unlocked rows, the ★ mark, the server-computed
    ``can_remove`` flags, and the 提名中 tab without any LLM call.
    """
    import os

    if os.environ.get("ELOSERN_BROWSER_TITLES", "") != "1":
        return

    from world.rules.clock import get_world_clock
    from world.rules.titles import (
        bank_epithet,
        bank_fixed,
        persist_nomination_ballot,
    )
    from web.browser_support.browser_fixtures_data import (
        SHIPPED_TITLE_RANK_E_KEY,
        SHIPPED_TITLE_RANK_F_KEY,
        SYNTH_TITLE_BANKED_KEYS,
    )

    tick = get_world_clock().tick
    synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
    for banked in (SYNTH_TITLE_BANKED_KEYS if synth else (SHIPPED_TITLE_RANK_F_KEY, SHIPPED_TITLE_RANK_E_KEY)):
        bank_fixed(character, banked, tick)
    bank_epithet(character, "南門新客", "初入南門。", tick)
    bank_epithet(character, "破城先鋒", "率先破門。", tick + 1)
    persist_nomination_ballot(
        character,
        [{"display": "夜襲之人", "basis": "夜半三度出入敵陣。"}],
    )
    print("seeded titles fixture: fixed 2 banked, epithets 2, one ballot")

