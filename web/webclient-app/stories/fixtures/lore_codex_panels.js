// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The committed `lore_codex` panel v1 (webclient-lore-codex-panel): the
// eight codex categories in CODE_CATEGORIES mapping order, each with its
// discovered count and rendered card fields. Deterministic offline
// literals only — discovered entries only, no registry-size leak.
const LORE_CODEX_CATEGORY = (key, label, entries) =>
  Object.freeze({ key, label, count: entries.length, entries: Object.freeze(entries) });

export const LORE_CODEX_PANEL_SAMPLE = Object.freeze({
  schema_version: 1,
  available: true,
  categories: Object.freeze([
    LORE_CODEX_CATEGORY("race", "種族", [
      Object.freeze({
        key: "human",
        title: "人類",
        card: Object.freeze([
          Object.freeze({ name: "代號", value: "human" }),
          Object.freeze({ name: "描述", value: "適應力最強的短命種，遍布灰河沿岸。" }),
        ]),
      }),
    ]),
    LORE_CODEX_CATEGORY("nation", "國家", []),
    LORE_CODEX_CATEGORY("region", "地域", [
      Object.freeze({
        key: "grey_river",
        title: "灰河",
        card: Object.freeze([
          Object.freeze({ name: "名稱", value: "灰河" }),
          Object.freeze({ name: "地貌", value: "終年起霧的寬緩河流，渡口夜燈明滅。" }),
        ]),
      }),
    ]),
    LORE_CODEX_CATEGORY("monster", "魔物", [
      Object.freeze({
        key: "mist_wolf",
        title: "霧骨狼",
        card: Object.freeze([
          Object.freeze({ name: "名稱", value: "霧骨狼" }),
          Object.freeze({ name: "描述", value: "群棲於霧中的中型獸，骨白如霧。" }),
          Object.freeze({ name: "例證", value: "霧骨狼·頭狼" }),
        ]),
      }),
    ]),
    LORE_CODEX_CATEGORY("element", "元素", []),
    LORE_CODEX_CATEGORY("magic", "魔法", []),
    LORE_CODEX_CATEGORY("anchor", "地點", [
      Object.freeze({
        key: "misty_ford",
        title: "霧骨渡口",
        card: Object.freeze([
          Object.freeze({ name: "名稱", value: "霧骨渡口" }),
          Object.freeze({ name: "描述", value: "灰河上的主要渡口，旅人與貨物的集散地。" }),
        ]),
      }),
    ]),
    LORE_CODEX_CATEGORY("guild", "公會", []),
  ]),
  discovered_total: 4,
});

export const LORE_CODEX_PANEL_EMPTY_SAMPLE = Object.freeze({
  schema_version: 1,
  available: true,
  categories: Object.freeze([
    LORE_CODEX_CATEGORY("race", "種族", []),
    LORE_CODEX_CATEGORY("nation", "國家", []),
    LORE_CODEX_CATEGORY("region", "地域", []),
    LORE_CODEX_CATEGORY("monster", "魔物", []),
    LORE_CODEX_CATEGORY("element", "元素", []),
    LORE_CODEX_CATEGORY("magic", "魔法", []),
    LORE_CODEX_CATEGORY("anchor", "地點", []),
    LORE_CODEX_CATEGORY("guild", "公會", []),
  ]),
  discovered_total: 0,
});

export const LORE_CODEX_PANEL_UNAVAILABLE_SAMPLE = Object.freeze({
  schema_version: 1,
  available: false,
  reason: Object.freeze({
    code: "lore_codex_unavailable",
    message: "知識圖鑑目前無法顯示",
  }),
});