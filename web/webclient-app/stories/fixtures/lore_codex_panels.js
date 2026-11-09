// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The committed `lore_codex` panel v2 (webclient-lore-codex-panel): the
// eight codex categories in CODE_CATEGORIES mapping order, each with its
// discovered count, its registry total and its groups of slots (an entry
// slot with its rendered card fields, or an identity-free placeholder).
// Deterministic offline literals only.
const LORE_CODEX_PLACEHOLDER = Object.freeze({ placeholder: true });
const LORE_CODEX_ENTRY = (key, title, card, stage = null) =>
  Object.freeze({
    key,
    title,
    stage,
    art: null,
    card: Object.freeze(card.map((field) => Object.freeze(field))),
    locked_fields: Object.freeze([]),
  });
const LORE_CODEX_CATEGORY = (key, label, slots, group = { key, label: null }) =>
  Object.freeze({
    key,
    label,
    discovered: slots.filter((slot) => !slot.placeholder).length,
    total: slots.length,
    groups: Object.freeze([Object.freeze({ ...group, slots: Object.freeze(slots) })]),
  });

export const LORE_CODEX_PANEL_SAMPLE = Object.freeze({
  schema_version: 2,
  available: true,
  discovered_total: 4,
  total: 8,
  categories: Object.freeze([
    LORE_CODEX_CATEGORY("race", "種族", [
      LORE_CODEX_ENTRY("human", "平原族", [
        { name: "display_name_zh", value: "平原族" },
        { name: "description", value: "適應力最強的短命種，遍布灰河沿岸。" },
      ]),
      LORE_CODEX_PLACEHOLDER,
    ]),
    LORE_CODEX_CATEGORY("nation", "國家", []),
    LORE_CODEX_CATEGORY("region", "地域", [
      LORE_CODEX_ENTRY("grey_river", "灰河", [
        { name: "display_name_zh", value: "灰河" },
        { name: "terrain_flavor_zh", value: "終年起霧的寬緩河流，渡口夜燈明滅。" },
      ]),
    ]),
    LORE_CODEX_CATEGORY(
      "monster",
      "魔物",
      [
        LORE_CODEX_ENTRY(
          "mist_wolf",
          "霧骨狼",
          [
            { name: "display_name_zh", value: "霧骨狼" },
            { name: "description", value: "群棲於霧中的中型獸，骨白如霧。" },
            { name: "example_monsters_zh", value: "霧骨狼‧頭狼" },
          ],
          "defeated",
        ),
        LORE_CODEX_PLACEHOLDER,
      ],
      { key: "moderate", label: "中階" },
    ),
    LORE_CODEX_CATEGORY("element", "元素", []),
    LORE_CODEX_CATEGORY("magic", "魔法", []),
    LORE_CODEX_CATEGORY("anchor", "地點", [
      LORE_CODEX_ENTRY("misty_ford", "霧骨渡口", [
        { name: "display_name_zh", value: "霧骨渡口" },
        { name: "description", value: "灰河上的主要渡口，旅人與貨物的集散地。" },
      ]),
    ]),
    LORE_CODEX_CATEGORY("guild", "公會", [LORE_CODEX_PLACEHOLDER, LORE_CODEX_PLACEHOLDER]),
  ]),
});

export const LORE_CODEX_PANEL_EMPTY_SAMPLE = Object.freeze({
  schema_version: 2,
  available: true,
  discovered_total: 0,
  total: 3,
  categories: Object.freeze([
    LORE_CODEX_CATEGORY("race", "種族", [LORE_CODEX_PLACEHOLDER]),
    LORE_CODEX_CATEGORY("nation", "國家", [LORE_CODEX_PLACEHOLDER]),
    LORE_CODEX_CATEGORY("region", "地域", []),
    LORE_CODEX_CATEGORY("monster", "魔物", [LORE_CODEX_PLACEHOLDER], { key: "moderate", label: "中階" }),
    LORE_CODEX_CATEGORY("element", "元素", []),
    LORE_CODEX_CATEGORY("magic", "魔法", []),
    LORE_CODEX_CATEGORY("anchor", "地點", []),
    LORE_CODEX_CATEGORY("guild", "公會", []),
  ]),
});

export const LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE = Object.freeze({
  schema_version: 2,
  available: false,
  reason: Object.freeze({
    code: "lore_codex_unavailable",
    message: "知識圖鑑目前無法顯示",
  }),
});