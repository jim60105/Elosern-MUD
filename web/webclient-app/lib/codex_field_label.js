// Readable names for the lore codex card fields. The panel ships each card
// field as `{name, value}` where `name` is the registry attribute the
// category declares (world/rules/lore_knowledge.py CODE_CATEGORIES); the
// drawer keeps that identifier as a hook and shows this name instead. The
// value is never touched. An undeclared field is named 資料 rather than
// showing its identifier.
export const CODEX_FIELD_LABELS = Object.freeze({
  display_name_zh: "名稱",
  description: "描述",
  capital_name_zh: "首都",
  terrain_flavor_zh: "地貌",
  example_monsters_zh: "例證",
});

export function codexFieldLabel(name) {
  return Object.hasOwn(CODEX_FIELD_LABELS, name) ? CODEX_FIELD_LABELS[name] : "資料";
}
