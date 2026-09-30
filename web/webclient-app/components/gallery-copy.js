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

// Card dates (webclient-zh-tw-copy-and-labels): a card's structured
// `created_at` (epoch seconds) is shown as a local relative time with the
// exact local instant beside it — never parsed from the label, which the
// server no longer stamps. `nowMs` is the gallery's minute clock; `timeZone`
// is injectable for deterministic tests and otherwise the runtime's own.
// A non-numeric, non-finite, or out-of-calendar value reads 日期不詳 and the
// row keeps its label and status.
export const GALLERY_DATE_UNAVAILABLE = "日期不詳";

// Smallest unit first: a span reads in the first unit whose ceiling it is
// under (years have none).
const RELATIVE_UNITS = [
  { unit: "minute", seconds: 60, below: 3600 },
  { unit: "hour", seconds: 3600, below: 86400 },
  { unit: "day", seconds: 86400, below: 30 * 86400 },
  { unit: "month", seconds: 30 * 86400, below: 360 * 86400 },
  { unit: "year", seconds: 365 * 86400, below: Infinity },
];

const formatters = new Map();
function formatter(kind, timeZone) {
  const key = `${kind}:${timeZone ?? ""}`;
  if (!formatters.has(key)) {
    formatters.set(
      key,
      kind === "relative"
        ? new Intl.RelativeTimeFormat("zh-TW", { numeric: "auto" })
        : new Intl.DateTimeFormat("zh-TW", { dateStyle: "long", timeStyle: "short", ...(timeZone ? { timeZone } : {}) }),
    );
  }
  return formatters.get(key);
}

export function galleryDate(value, nowMs = Date.now(), { timeZone } = {}) {
  const unavailable = { relative: GALLERY_DATE_UNAVAILABLE, exact: null, iso: null };
  if (typeof value !== "number" || !Number.isFinite(value)) return unavailable;
  const date = new Date(value * 1000);
  if (Number.isNaN(date.getTime())) return unavailable;
  const exact = formatter("exact", timeZone).format(date);
  const delta = (value * 1000 - nowMs) / 1000;
  const magnitude = Math.abs(delta);
  let relative = "剛剛";
  if (magnitude >= 60) {
    const step = RELATIVE_UNITS.find((entry) => magnitude < entry.below);
    // At least one whole unit: 360–364 days read 1 年前, not 12 個月前.
    const count = Math.max(1, Math.trunc(magnitude / step.seconds));
    relative = formatter("relative").format(delta < 0 ? -count : count, step.unit);
  }
  return { relative, exact, iso: date.toISOString() };
}

// The accessible name of a card image or row: the server label plus the
// exact local instant, so identical 肖像 labels stay distinguishable and the
// name does not change every minute.
export function galleryCardName(card, { timeZone } = {}) {
  const { exact } = galleryDate(card?.created_at, 0, { timeZone });
  return exact ? `${card.label}，${exact}` : card?.label ?? "";
}
