// Static chrome and the committed closed catalog; never equipment or match rules.
export const GALLERY_FIELDS = [
  { id: "appearance", label: "角色外貌描述", note: "使用角色的外貌設定（髮型、瞳色、種族等）", glyph: "◇" },
  { id: "weapon_main", label: "主手武器", note: "使用目前裝備的主手武器", glyph: "⚔" },
  { id: "weapon_off", label: "副手武器", note: "使用目前裝備的副手武器", glyph: "⚔" },
  { id: "armor", label: "防具", note: "使用目前裝備的防具外觀", glyph: "♜" },
  { id: "accessories", label: "飾品", note: "使用目前裝備的飾品", glyph: "◇" },
];
export const GALLERY_SLOTS = GALLERY_FIELDS.slice(1);
export const GALLERY_FILTERS = [
  { id: "all", label: "全部" },
  { id: "defaults", label: "預設" },
  { id: "bound", label: "已綁定" },
  { id: "pending", label: "生成中" },
  { id: "failed", label: "失敗" },
];

export function galleryTimestamp(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "";
  const date = new Date(value * 1000);
  return Number.isNaN(date.getTime()) ? String(value) : date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}
