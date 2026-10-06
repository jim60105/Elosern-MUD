// Deterministic, offline fixtures for the GM stories (synthetic values).
export const SESSION = Object.freeze({
  account_name: "operator_01",
  permission_level: "Developer",
  server_time: "2026-10-07T14:32:05+08:00",
  game_version: "0.1.0",
});

export const HEALTH_COLUMNS = [
  { key: "label", label: "項目" },
  { key: "key", label: "識別碼", mono: true },
  { key: "value", label: "回報值", mono: true },
  { key: "status", label: "狀態" },
];

export const HEALTH_ROWS = [
  { key: "django", label: "Django 回應", value: "ok", status: { status: "ok", label: "正常" } },
  { key: "database", label: "資料庫讀取", value: "readable", status: { status: "ok", label: "可讀取" } },
];

export function stage(children, { padding = "32px", maxWidth = "880px" } = {}) {
  return { style: { padding, maxWidth }, children };
}
