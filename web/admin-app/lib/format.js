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

// Epoch seconds -> local wall clock "HH:MM:SS" (24h); null/invalid -> "—".
export function formatClock(epochSeconds, { timeZone } = {}) {
  if (typeof epochSeconds !== "number" || !Number.isFinite(epochSeconds)) return "—";
  return new Intl.DateTimeFormat("zh-TW", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    ...(timeZone ? { timeZone } : {}),
  }).format(new Date(epochSeconds * 1000));
}

// Epoch seconds -> ISO string for <time datetime>; null when absent.
export function isoFromEpoch(epochSeconds) {
  if (typeof epochSeconds !== "number" || !Number.isFinite(epochSeconds)) return null;
  return new Date(epochSeconds * 1000).toISOString();
}

// Milliseconds -> "820 ms" / "8.1 s"; null -> "—".
export function formatMs(ms) {
  if (typeof ms !== "number" || !Number.isFinite(ms)) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)} s`;
}

// Seconds -> compact zh-TW duration: "45 秒", "12 分", "3 時 05 分", "2 天 4 時".
export function formatDuration(seconds) {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) return "—";
  const s = Math.floor(seconds);
  if (s < 60) return `${s} 秒`;
  const minutes = Math.floor(s / 60);
  if (minutes < 60) return `${minutes} 分`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 時 ${String(minutes % 60).padStart(2, "0")} 分`;
  return `${Math.floor(hours / 24)} 天 ${hours % 24} 時`;
}

// Age relative to `now` (both epoch seconds): "剛剛", "12 秒前", "3 分前" ...
export function formatAge(epochSeconds, now) {
  if (typeof epochSeconds !== "number" || typeof now !== "number") return "—";
  const delta = Math.max(0, now - epochSeconds);
  if (delta < 2) return "剛剛";
  return `${formatDuration(delta)}前`;
}

// Ratio 0..1 -> "12.5%"; denominator 0 -> "—".
export function formatPercent(part, whole) {
  if (!whole) return "—";
  const value = (part / whole) * 100;
  return `${value < 10 && value > 0 ? value.toFixed(1) : Math.round(value)}%`;
}
