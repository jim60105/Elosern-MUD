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
  const external = workspace.external_change;
  if (external?.sequence && external.at === workspace.snapshot_read_at) {
    return { tone: "ok", glyph: "◉", text: `已載入外部變更 ${clock(external.at)}` };
  }
  return { tone: "ok", glyph: "◉", text: `已同步 ${clock(workspace.snapshot_read_at)}` };
}

// `state` names the condition for the page (and its tests); text is copy.
export function indexChip(workspace) {
  const status = workspace?.external_context_status;
  if (!status) return { tone: "neutral", glyph: "⟳", text: "索引", state: "loading" };
  const invalid = (workspace?.diagnostics ?? []).filter((item) => item.category === "external").length;
  if (!status.current) return { tone: "warn", glyph: "▲", text: "索引不可用 · 無法刪除", state: "unavailable" };
  if (invalid) return { tone: "seal", glyph: "✕", text: `外部引用無效 ${invalid}`, state: "invalid" };
  return { tone: "ok", glyph: "✓", text: "索引 現行", state: "current" };
}

// The 分區 chip (frontend design §5.1) combines the artifact's freshness with
// the explicit partition job. `action` is what activating it does: regenerate
// when the output is not current, cancel while generating, nothing otherwise
// (the chip then only expands the partition diagnostics).
export function partitionChip(workspace) {
  const status = workspace?.partition_status;
  const job = workspace?.partition_job;
  if (!status) return { tone: "neutral", glyph: "⟳", text: "分區", state: "loading", action: null };
  if (job?.state === "generating" || job?.state === "publishing") {
    return { tone: "busy", glyph: "⟳", text: "分區產生中 · 取消", state: "generating", action: "cancel" };
  }
  if (status.game_ready) return { tone: "ok", glyph: "✓", text: "分區 現行", state: "current", action: null };
  if (job?.state === "cancelled") {
    return { tone: "neutral", glyph: "⦸", text: "分區已取消 · 保留舊版", state: "cancelled", action: "regenerate" };
  }
  if (job?.state === "failed") {
    return { tone: "seal", glyph: "✕", text: "分區產生失敗 · 保留舊版", state: "failed", action: "regenerate" };
  }
  if (status.status === "stale") {
    return { tone: "warn", glyph: "▲", text: "分區過期 · 重新產生", state: "stale", action: "regenerate" };
  }
  return { tone: "seal", glyph: "⦸", text: "分區不可用 · 重新產生", state: "unavailable", action: "regenerate" };
}

// The partition output's input revision: the artifact's input signature
// against the current one, shortened for display, and whether the displayed
// output belongs to older inputs.
export function partitionRevision(workspace) {
  const status = workspace?.partition_status;
  if (!status || status.status === "unavailable") return null;
  const short = (value) => (value ? String(value).slice(0, 8) : "—");
  return {
    output: short(status.input_signature),
    current: short(status.expected_signature),
    older: status.status === "stale",
  };
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
      action: "reconnect",
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
