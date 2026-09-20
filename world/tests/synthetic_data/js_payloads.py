"""JS-mirror canonical payload table (design D4).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# JS-mirror canonical payload (design D4): the single source of truth the
# Python kit, both JS mirrors, and the Node self-test all agree on.
# ---------------------------------------------------------------------------

SYNTH_JS_PAYLOADS: dict[str, dict[str, object]] = {
    "SYNTH_ITEM": {
        "id": "t_ember_spray",
        "display": "熾焰噴射劑",
        "kind": "potion",
        "rarity": "common",
        "price_table": "t_mossmeals",
    },
    "SYNTH_SKILL": {
        "id": "t_ember_burst",
        "label": "燼火爆發",
        "category": "elemental_magic",
        "target": "single",
        "cost": {"mp": 12},
    },
    "SYNTH_PRESET": {
        "id": "t_pale_wren",
        "display": "蒼雀",
        "race": "t_duskmari",
        "subrace": "t_duskmari_evensong",
        "emphasis": "wanderer",
    },
    "SYNTH_QUEST": {
        "id": "t_ember_cull",
        "display": "燼殼蟲清剿",
        "rank": "t_bronze",
        "type": "defeat",
    },
    "SYNTH_TITLE": {
        "id": "t_synth_first_hunt",
        "display": "初獵合成者",
        "category": "combat",
    },
}

