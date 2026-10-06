// Display formatting for GM data. Identifiers are never formatted; only
// human-facing renderings (dates) are localized, next to the raw value.
export function formatServerTime(iso, { timeZone } = {}) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("zh-TW", {
    dateStyle: "full",
    timeStyle: "medium",
    hour12: false,
    ...(timeZone ? { timeZone } : {}),
  }).format(date);
}
