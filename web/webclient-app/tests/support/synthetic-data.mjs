// Synthetic catalog payloads shared by web-client behavior tests
// (add-test-synthetic-data-kit). SYNTH_CANONICAL_JSON below is the single
// source of truth. This file exists in two byte-identical copies
// (web/webclient-app/tests/support/ and web/static/webclient/js/tests/support/)
// for the vitest and node --test runners; the Node self-test
// (synthetic_data.test.js) asserts each copy's exports deep-equal its
// canonical block and that the two copies are byte-identical; the Python
// kit (world/tests/synthetic_data.py, SYNTH_JS_PAYLOADS) is checked
// against the same text by world/tests/test_synthetic_data.py. Every value
// is invented t_-keyed synthetic content — never shipped lore strings.

export const SYNTH_CANONICAL_JSON = `{
  "SYNTH_ITEM": {
    "id": "t_ember_spray",
    "display": "熾焰噴射劑",
    "kind": "potion",
    "rarity": "common",
    "price_table": "t_mossmeals"
  },
  "SYNTH_SKILL": {
    "id": "t_ember_burst",
    "label": "燼火爆發",
    "category": "elemental_magic",
    "target": "single",
    "cost": {
      "mp": 12
    }
  },
  "SYNTH_PRESET": {
    "id": "t_pale_wren",
    "display": "蒼雀",
    "race": "t_duskmari",
    "subrace": "t_duskmari_evensong",
    "emphasis": "wanderer"
  },
  "SYNTH_QUEST": {
    "id": "t_ember_cull",
    "display": "燼殼蟲清剿",
    "rank": "t_bronze",
    "type": "defeat"
  },
  "SYNTH_TITLE": {
    "id": "t_synth_first_hunt",
    "display": "初獵合成者",
    "category": "combat"
  }
}`;

const CANONICAL = JSON.parse(SYNTH_CANONICAL_JSON);

export const SYNTH_ITEM = CANONICAL.SYNTH_ITEM;
export const SYNTH_SKILL = CANONICAL.SYNTH_SKILL;
export const SYNTH_PRESET = CANONICAL.SYNTH_PRESET;
export const SYNTH_QUEST = CANONICAL.SYNTH_QUEST;
export const SYNTH_TITLE = CANONICAL.SYNTH_TITLE;
export const SYNTH_CANONICAL = CANONICAL;
