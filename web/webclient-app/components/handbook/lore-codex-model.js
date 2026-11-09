// lore-codex-model (handbook-codex-tab, design D3): the pure view model of the
// handbook's codex (圖鑑) tab over the committed `lore_codex` v2 panel. Every
// function takes the committed panel (or null) and derives presentation only.
// The client hard-codes no field list: the detail renders the slot's card in
// panel order and one locked box per `locked_fields` name, both under the
// readable names below. The research stage, stamp and track follow the slot's
// own `stage`; only the legend asks which category is the monster wall.

// The one category whose wall carries the stage legend (the server's
// MONSTER_CATEGORY wire key).
export const MONSTER_CATEGORY = "monster";

// The card field that is the entry's title; it heads the detail and is not
// repeated as a field.
const TITLE_FIELD = "display_name_zh";

// Readable names for the codex card fields. The panel ships each card field
// as `{name, value}`, where `name` is the registry attribute; the tab keeps
// that identifier as a hook (`data-field`) and shows this name instead. The
// value is never touched. An undeclared field is named 資料.
export const CODEX_FIELD_LABELS = Object.freeze({
  display_name_zh: "名稱",
  description: "描述",
  capital_name_zh: "首都",
  terrain_flavor_zh: "地貌",
  example_monsters_zh: "例證",
  published_appearance_zh: "外觀",
  threat_tier: "威脅",
  published_description_zh: "描述",
  published_ecology_zh: "生態",
  habitat_tags: "棲地",
  variants: "變種",
});

export function codexFieldLabel(name) {
  return Object.hasOwn(CODEX_FIELD_LABELS, name) ? CODEX_FIELD_LABELS[name] : "資料";
}

const STAGE_SUFFIX = Object.freeze({ defeated: "，已擊敗", sighted: "，已目擊" });

// "absent" before the first commit, "unavailable" for the common unavailable
// form, else "available".
export function loreCodexStatus(panel) {
  if (!panel) return "absent";
  return panel.available === true ? "available" : "unavailable";
}

const categoriesOf = (panel) =>
  loreCodexStatus(panel) === "available" && Array.isArray(panel.categories) ? panel.categories : [];
const categoryOf = (panel, key) => categoriesOf(panel).find((category) => category.key === key) ?? null;
const groupsOf = (category) => (Array.isArray(category?.groups) ? category.groups : []);
const slotsOf = (group) => (Array.isArray(group?.slots) ? group.slots : []);
const isEntry = (slot) => !!slot && slot.placeholder !== true && typeof slot.key === "string";
const entriesOf = (category) => groupsOf(category).flatMap((group) => slotsOf(group).filter(isEntry));

// The rail: one entry per shipped category, in panel order, with its
// discovered count.
export function codexRail(panel) {
  return categoriesOf(panel).map((category) => ({ key: category.key, label: category.label, count: category.discovered }));
}

// The first category holding a discovery, else the first category, else null.
export function defaultCodexCategory(panel) {
  const categories = categoriesOf(panel);
  return (categories.find((category) => category.discovered > 0) ?? categories[0])?.key ?? null;
}

// The wall's groups for one category, in panel order. A placeholder names no
// entry: its id is its ordinal position and its label is identity-free.
export function codexGroups(panel, categoryKey) {
  return groupsOf(categoryOf(panel, categoryKey)).map((group) => ({
    key: group.key,
    label: group.label ?? null,
    items: slotsOf(group).map((slot, index) =>
      isEntry(slot)
        ? {
            id: slot.key,
            selectable: true,
            label: `${slot.title}${STAGE_SUFFIX[slot.stage] ?? ""}`,
            placeholder: false,
            stage: slot.stage ?? null,
            art: slot.art ?? null,
            title: slot.title,
          }
        : { id: `p:${group.key}:${index}`, selectable: false, label: "未記錄", placeholder: true },
    ),
  }));
}

// The category's first entry slot key, or null when it has none.
export function firstEntryKey(panel, categoryKey) {
  return entriesOf(categoryOf(panel, categoryKey))[0]?.key ?? null;
}

// The detail view model of one entry, or null for an unknown key.
export function codexDetail(panel, categoryKey, key) {
  const category = categoryOf(panel, categoryKey);
  const slot = entriesOf(category).find((entry) => entry.key === key);
  if (!slot) return null;
  const stage = slot.stage ?? null;
  const lockedNames = Array.isArray(slot.locked_fields) ? slot.locked_fields : [];
  const locked = lockedNames.map((name) => ({ name, label: codexFieldLabel(name) }));
  const card = Array.isArray(slot.card) ? slot.card : [];
  return {
    kind: "codex",
    id: slot.key,
    category: category.key,
    name: slot.title,
    ribbon: category.label,
    emblem: category.key,
    stage,
    art: slot.art ?? null,
    stamp: stage ? { kind: stage, label: stage === "defeated" ? "已擊敗" : "目擊" } : null,
    fields: card
      .filter((field) => field.name !== TITLE_FIELD)
      .map((field) => ({ name: field.name, label: codexFieldLabel(field.name), value: field.value })),
    locked,
    track: stage
      ? [
          { key: "sighted", label: "目擊", unlocks: null, reached: true },
          {
            key: "defeated",
            label: "擊敗",
            unlocks: stage === "sighted" && locked.length ? locked.map((item) => item.label).join("・") : null,
            reached: stage === "defeated",
          },
        ]
      : null,
  };
}
