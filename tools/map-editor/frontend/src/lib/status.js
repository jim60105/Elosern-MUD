// Coarse workspace status presentation (frontend design D4 §5): the header
// chips and one priority banner are derived from the authoritative state the
// service returned; nothing is pre-checked or inferred locally.

import { DISCONNECTED } from "./workspace_client.js";

export function clock(iso) {
  if (!iso) return "--:--";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--:--";
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

export function syncChip(workspace, connection) {
  if (connection === DISCONNECTED) return { tone: "seal", glyph: "⦸", text: "服務未連線" };
  if (!workspace) return { tone: "neutral", glyph: "⟳", text: "讀取中" };
  if (workspace.preview_state === "unavailable") return { tone: "seal", glyph: "⦸", text: "無可用預覽" };
  if (workspace.preview_state === "stale") return { tone: "warn", glyph: "▲", text: "預覽過期 · YAML 錯誤" };
  return { tone: "ok", glyph: "◉", text: `已同步 ${clock(workspace.snapshot_read_at)}` };
}

export function indexChip(workspace) {
  const status = workspace?.external_context_status;
  if (!status) return { tone: "neutral", glyph: "⟳", text: "索引" };
  if (status.current) return { tone: "ok", glyph: "✓", text: "索引 現行" };
  return { tone: "warn", glyph: "▲", text: "索引不可用 · 無法刪除" };
}

export function partitionChip(workspace) {
  const status = workspace?.partition_status;
  if (!status) return { tone: "neutral", glyph: "⟳", text: "分區" };
  if (status.status === "current") return { tone: "ok", glyph: "✓", text: "分區 現行" };
  if (status.status === "stale") return { tone: "warn", glyph: "▲", text: "分區過期" };
  return { tone: "seal", glyph: "⦸", text: "分區不可用" };
}

export function firstFailure(workspace) {
  const [first] = workspace?.candidate_diagnostics ?? [];
  if (!first) return null;
  const where = first.relative_path ? `${first.relative_path}${first.line ? `:${first.line}` : ""}` : "（工作區）";
  return `${where} — ${first.message}`;
}

// Highest-priority active condition only; null when none is active.
export function priorityBanner(workspace, connection) {
  if (connection === DISCONNECTED) {
    return {
      key: "disconnected",
      tone: "seal",
      title: "服務未連線",
      text: workspace
        ? `畫面停留在 ${clock(workspace.checked_at)} 的快照，現在無法寫入。重新連線後會自動重新讀取。`
        : "無法連線到地圖編纂服務。",
    };
  }
  if (!workspace) return null;
  if (workspace.preview_state === "stale") {
    return {
      key: "stale",
      tone: "warn",
      title: "預覽過期",
      text: `顯示的是 ${clock(workspace.snapshot_read_at)} 的最後可用版本。${firstFailure(workspace) ?? ""}`,
    };
  }
  if (workspace.preview_state === "unavailable") {
    return {
      key: "unavailable",
      tone: "seal",
      title: "無可用預覽",
      text: firstFailure(workspace) ?? "工作區無法載入。",
    };
  }
  return null;
}

export function diagnosticCounts(diagnostics) {
  let errors = 0;
  let warnings = 0;
  for (const item of diagnostics ?? []) {
    if (item.category === "structure" || item.category === "external") errors += 1;
    else warnings += 1;
  }
  return { errors, warnings };
}
