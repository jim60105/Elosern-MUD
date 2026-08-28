// Local item-icon map (redesign-inventory-item-grid, task 1.1): a closed
// table keyed by the services-v2 `presentation.icon_key` vocabulary
// (mirrors the server's `world/lore/items.py` ItemIconKey: food, potion,
// weapon, armor, accessory, ammunition, tool, material, misc). Each entry
// is an inline SVG path (24x24 viewBox, stroke-based, same idiom as
// `dock-icons.js`) plus a Traditional Chinese accessible label. No URL, no
// HTML, no emoji, no raw SVG strings — the view layer owns its own icon
// markup and never imports server data. A neutral unknown-item fallback
// covers `presentation: null` and any future icon key not yet mapped.
export const ITEM_ICONS = {
  food: { label: "食物", d: "M4 13h16a8 8 0 0 1-16 0Z" },
  potion: { label: "藥水", d: "M10 3h4v4l3 9a3 3 0 0 1-3 4h-4a3 3 0 0 1-3-4l3-9V3z" },
  weapon: { label: "武器", d: "M5 19 17 7M17 7l-3 1M5 19l2-3" },
  armor: { label: "裝甲", d: "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z" },
  accessory: { label: "飾品", d: "M12 4a5 5 0 1 1 0 10 5 5 0 0 1 0-10zM12 14v6" },
  ammunition: { label: "彈藥", d: "M4 20 20 4M20 4h-6M20 4v6" },
  tool: { label: "工具", d: "M13 3l8 8-4 4-8-8zM3 21l9-9" },
  material: { label: "素材", d: "M4 14l2-5h12l2 5v4H4v-4z" },
  misc: { label: "雜項", d: "M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2" },
};

// The neutral unknown-item fallback: used when `presentation` is null OR when
// a non-null `presentation.icon_key` is not in the closed map (a future server
// enum value arriving before the local map grows). It is labelled, never
// inferred from the item key or display name.
export const UNKNOWN_ITEM_ICON = { label: "未知", d: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM9 9a3 3 0 1 1 3 3v1M12 17v.01" };

// The closed kind vocabulary mirrors the icon-key vocabulary (the server's
// ItemKind and ItemIconKey share the same nine values), so kind words reuse
// the icon labels.
export const KIND_LABELS = Object.fromEntries(
  Object.entries(ITEM_ICONS).map(([key, entry]) => [key, entry.label]),
);

// The closed rarity vocabulary (the server's ItemRarity): the inspector
// spells the rarity word so colour is never the only representation.
export const RARITY_LABELS = {
  common: "普通",
  uncommon: "罕見",
  rare: "稀有",
  epic: "史詩",
  legendary: "傳說",
};

// Return the icon entry {label, d} for a committed `presentation.icon_key`,
// or null when the key is not a string or not in the closed map.
export function itemIcon(iconKey) {
  if (typeof iconKey !== "string") {
    return null;
  }
  return ITEM_ICONS[iconKey] || null;
}

// Return the SVG path `d` string for a committed icon key, or null when
// unmapped (the caller renders the neutral unknown-item fallback).
export function itemIconPath(iconKey) {
  const entry = itemIcon(iconKey);
  return entry ? entry.d : null;
}

// Return the Traditional Chinese accessible label for a committed icon key.
export function itemIconLabel(iconKey) {
  const entry = itemIcon(iconKey);
  return entry ? entry.label : null;
}

// The neutral unknown-item icon path and label (the `presentation: null`
// case and any unmapped key).
export function unknownItemPath() {
  return UNKNOWN_ITEM_ICON.d;
}

export function unknownItemLabel() {
  return UNKNOWN_ITEM_ICON.label;
}

// The Traditional Chinese word for a committed `presentation.rarity`, or
// null when the rarity value is outside the closed vocabulary (never
// invented).
export function rarityLabel(rarity) {
  if (typeof rarity !== "string") {
    return null;
  }
  return RARITY_LABELS[rarity] || null;
}

// The Traditional Chinese word for a committed `presentation.kind`, or null
// when the kind value is outside the closed vocabulary.
export function kindLabel(kind) {
  if (typeof kind !== "string") {
    return null;
  }
  return KIND_LABELS[kind] || null;
}
