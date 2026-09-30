// Display names for the two finite skill enums the combat panel and the
// skill book ship as raw identifiers: `target_spec` (the validated closed set
// none / self / single / area, web/webclient/presentation/combat_panel.py
// TARGET_SPECS) and `element` (the element registry keys,
// world/lore/elements.py, named here with the registry's own 火 / 水 / …).
// The identifiers stay untouched for routing and payloads; an unrecognised
// value gets a neutral label, never a guessed mechanic or the raw key.
export const TARGET_SPEC_LABELS = Object.freeze({
  none: "無目標",
  self: "自身",
  single: "單一目標",
  area: "範圍",
});

export const ELEMENT_LABELS = Object.freeze({
  fire: "火",
  water: "水",
  wind: "風",
  earth: "土",
  lightning: "雷",
  ice: "冰",
  light: "光",
  dark: "暗",
});

export function targetSpecLabel(spec) {
  return Object.hasOwn(TARGET_SPEC_LABELS, spec) ? TARGET_SPEC_LABELS[spec] : "未知目標類型";
}

export function elementLabel(element) {
  return Object.hasOwn(ELEMENT_LABELS, element) ? `${ELEMENT_LABELS[element]}屬性` : "未知屬性";
}
