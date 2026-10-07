// S5 world saves (gm-portal-s5-saves): route name, API paths, kind
// vocabulary, and display formatting for the 存檔 page. Save ids are
// identifiers and always render verbatim; only sizes and dates are formatted.

export const SAVES_ROUTE = Object.freeze({ home: "saves" });

export const SAVE_ID_PATTERN = /^\d{8}T\d{6}-[0-9a-f]{6}$/;
export const LABEL_MAX_LENGTH = 80;

export const SAVE_KINDS = Object.freeze([
  Object.freeze({ key: "manual", label: "手動", long: "手動存檔", status: "ok" }),
  Object.freeze({ key: "auto_restore", label: "讀檔前自動", long: "讀檔前自動存檔", status: "neutral" }),
  Object.freeze({ key: "auto_intervention", label: "介入前自動", long: "介入前自動存檔", status: "neutral" }),
]);

export const KIND_FILTERS = Object.freeze([
  Object.freeze({ key: "all", label: "全部" }),
  ...SAVE_KINDS.map((kind) => Object.freeze({ key: kind.key, label: kind.label })),
]);

export function kindInfo(key) {
  return SAVE_KINDS.find((kind) => kind.key === key) ?? { key, label: key, long: key, status: "neutral" };
}

export const savesPath = () => "/saves/";
export const restorePath = (id) => `/saves/${encodeURIComponent(id)}/restore`;
export const deletePath = (id) => `/saves/${encodeURIComponent(id)}/delete`;
export const downloadPath = (id) => `/saves/${encodeURIComponent(id)}/download`;

// Operator copy for the S5 error codes; the server's zh-TW message is shown
// beside it, and the page branches on the code only.
export const SAVE_ERROR_TITLES = Object.freeze({
  save_in_progress: "另一項存檔作業正在進行",
  save_incompatible: "這份存檔與目前的程式碼不相容",
  save_not_found: "找不到這份存檔",
  invalid_save_id: "存檔識別碼不正確",
  save_delete_forbidden: "自動存檔不能手動刪除",
  save_failed: "存檔作業失敗",
  network_error: "無法連線到伺服器",
  csrf_failed: "安全驗證失敗",
});

export function errorTitle(code, fallback = "操作失敗") {
  return SAVE_ERROR_TITLES[code] ?? fallback;
}

// Bytes -> "512 B", "3.4 KB", "12.0 MB", "1.25 GB" (binary units).
export function formatBytes(bytes) {
  if (typeof bytes !== "number" || !Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value < 10 ? 2 : 1)} ${units[unit]}`;
}

// The manifest's world clock -> "第 3 年 春 第 12 日 09:05"; absent -> null.
export function formatGameDate(clock) {
  if (!clock || typeof clock !== "object") return null;
  const hh = String(clock.hour ?? 0).padStart(2, "0");
  const mm = String(clock.minute ?? 0).padStart(2, "0");
  return `第 ${clock.year} 年 ${clock.season} 第 ${clock.day} 日 ${hh}:${mm}`;
}

// ISO creation time -> local "2026/10/07 15:04:09"; invalid -> the raw text.
export function formatCreated(iso, { timeZone } = {}) {
  const date = new Date(iso);
  if (!iso || Number.isNaN(date.getTime())) return iso || "—";
  return new Intl.DateTimeFormat("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    ...(timeZone ? { timeZone } : {}),
  }).format(date);
}

export function countByKind(saves) {
  const counts = { all: saves.length };
  for (const kind of SAVE_KINDS) counts[kind.key] = 0;
  for (const save of saves) counts[save.kind] = (counts[save.kind] ?? 0) + 1;
  return counts;
}

export function totalBytes(saves) {
  return saves.reduce((sum, save) => sum + (Number(save.size_bytes) || 0), 0);
}
