"""Fixed-title rows the codex fixture banks, per boot mode.

Slice of the former ``web/browser_support/browser_fixtures_data``
module; every payload ships verbatim."""

from __future__ import annotations

from web.browser_support.browser_fixtures_data.mode import synth_mode_enabled
from web.browser_support.browser_fixtures_data.shipped_seed import (
    SHIPPED_TITLE_RANK_E_KEY,
    SHIPPED_TITLE_RANK_F_KEY,
)

#: Fixed-title rows the synth titles fixture banks; registration already
#: banked the entry-rank title through the grafted F row, so the fixture
#: banks it idempotently alongside the second kit row.
SYNTH_TITLE_BANKED_KEYS = ("t_synth_first_hunt", "t_synth_lodging_friend")
#: A third kit title kept UNbanked so the codex renders a locked row.
SYNTH_TITLE_LOCKED_KEY = "t_synth_deep_walker"


def title_codex_values() -> dict:
    """The codex fixture's fixed-title rows for the current boot mode.

    (banked keys, banked displays in bank order, the display the freshly
    registered character previews — the FIRST banked row auto-equips the
    empty fixed slot — and the deliberately-locked row's key/display/hint).
    The kit displays mirror the kit rows' authored text: the Playwright-side
    process has no Django settings, so they are mirrored here exactly like
    the art scene label.
    """
    if synth_mode_enabled():
        return {
            "banked_keys": tuple(SYNTH_TITLE_BANKED_KEYS),
            "banked_displays": ("初獵合成者", "驛站常客"),
            "banked_categories": ("combat", "romance"),
            "locked_key": SYNTH_TITLE_LOCKED_KEY,
            "locked_display": "深霧行者",
            "locked_hint": "在合成荒野深處留下足夠多的到訪紀錄即可獲得。",
            "locked_category": "explore",
        }
    return {
        "banked_keys": (SHIPPED_TITLE_RANK_F_KEY, SHIPPED_TITLE_RANK_E_KEY),
        "banked_displays": ("F級冒險者", "E級斥候"),
        "banked_categories": ("guild", "guild"),
        "locked_key": "g_s_rank",
        "locked_display": "S級傳說",
        "locked_hint": "通過 S 級公會考核即可獲得。",
        "locked_category": "guild",
    }
