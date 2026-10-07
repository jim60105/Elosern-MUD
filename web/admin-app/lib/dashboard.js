// Pure mappings from the /gm/api/dashboard snapshot to display states
// (gm-portal-s2b-dashboard). Status is always a (tone, text) pair so the UI
// never relies on colour alone. Thresholds are deliberate view constants.
import { formatAge, formatClock } from "./format.js";

export const DEGRADE_WARN_RATE = 0.1;
export const DEGRADE_CRIT_RATE = 0.3;

// A slot either holds data or `{error: {code, message}}`.
export function slotError(slot) {
  if (slot && typeof slot === "object" && !Array.isArray(slot) && slot.error && typeof slot.error === "object") {
    return slot.error;
  }
  return null;
}

export const RESULT_BADGES = Object.freeze({
  ok: { status: "ok", label: "成功" },
  degraded: { status: "warn", label: "降級" },
  rejected: { status: "crit", label: "拒絕" },
});

export function resultBadge(result) {
  return RESULT_BADGES[result] ?? { status: "neutral", label: String(result ?? "—") };
}

export function degradeRate(layer) {
  if (!layer?.calls) return null;
  return ((layer.degraded ?? 0) + (layer.rejected ?? 0)) / layer.calls;
}

export function layerStatus(layer) {
  if (!layer.enabled) return { status: "neutral", label: "已停用", rank: 4 };
  if (!layer.calls) return { status: "neutral", label: "尚無資料", rank: 3 };
  const rate = degradeRate(layer);
  if (rate >= DEGRADE_CRIT_RATE) return { status: "crit", label: "異常", rank: 0 };
  if (rate >= DEGRADE_WARN_RATE || layer.rejected > 0) return { status: "warn", label: "降級", rank: 1 };
  return { status: "ok", label: "正常", rank: 2 };
}

// crit -> warn -> ok -> no data -> disabled; registry order within a rank.
export function sortLayers(layers) {
  return layers
    .map((layer, index) => ({ layer, index, state: layerStatus(layer) }))
    .sort((a, b) => a.state.rank - b.state.rank || a.index - b.index);
}

export function sdCard(slot, now) {
  const error = slotError(slot);
  if (error) return { name: "SD 繪圖", error };
  const meta = [{ label: "主機", value: slot.host ?? "—", mono: true }];
  if (slot.checked_at != null) {
    meta.push({
      label: "檢查於",
      value: `${formatClock(slot.checked_at)}${slot.from_cache ? "（快取）" : ""}`,
      mono: true,
    });
  }
  if (!slot.ok && slot.code) meta.push({ label: "錯誤代碼", value: slot.code, mono: true });
  return {
    name: "SD 繪圖",
    status: slot.ok ? "ok" : "crit",
    statusLabel: slot.ok ? "正常" : "離線",
    detail: slot.ok ? "sd-webui 可連線" : "無法連線至 sd-webui；生成會在服務恢復後繼續",
    meta,
    error: null,
  };
}

export function backendCard(name, slot, now) {
  const error = slotError(slot);
  if (error) return { name, error };
  const failure = slot.latest_failure;
  let status = "neutral";
  let statusLabel = "已停用";
  let detail = "設定為停用，相關步驟會略過";
  if (slot.backend === "real") {
    status = failure ? "warn" : "ok";
    statusLabel = failure ? "最近失敗" : "真實後端";
    detail = failure ? "後端已啟用，但緩衝區內有失敗紀錄" : "後端已啟用";
  } else if (slot.backend === "fake") {
    status = "warn";
    statusLabel = "假後端";
    detail = "使用測試用假後端，輸出不是真實結果";
  }
  const meta = [];
  if (slot.class_name) meta.push({ label: "實作類別", value: slot.class_name, mono: true });
  meta.push(
    failure
      ? {
          label: "最近失敗",
          value: `${failure.event} · ${formatAge(failure.ts, now)}`,
          mono: true,
          title: failure.exc ?? "",
        }
      : { label: "最近失敗", value: "無失敗紀錄" },
  );
  return { name, status, statusLabel, detail, meta, error: null };
}

export function llmCard(slot) {
  const error = slotError(slot);
  if (error) return { name: "LLM", error };
  const any = slot.enabled > 0;
  return {
    name: "LLM",
    status: any ? "ok" : "warn",
    statusLabel: any ? `${slot.enabled} / ${slot.total} 層啟用` : "全部停用",
    detail: any ? "健康狀態由最近的呼叫被動推算，不主動探測" : "所有生成層都會直接降級",
    meta: [],
    error: null,
  };
}

export function drainBadge(drain) {
  if (!drain?.exists) return { status: "crit", label: "排程不存在" };
  if (drain.running) return { status: "ok", label: "排程執行中" };
  return { status: "warn", label: "排程已暫停" };
}

export const ART_SEGMENTS = Object.freeze([
  { key: "failed", label: "失敗", tone: "crit", pattern: "cross" },
  { key: "in_progress", label: "進行中", tone: "gold", pattern: "hatch" },
  { key: "pending", label: "等待", tone: "neutral", pattern: "solid" },
  { key: "missing", label: "缺圖", tone: "neutral", pattern: "outline" },
  { key: "done", label: "完成", tone: "ok", pattern: "solid" },
]);

export function issueBadge(level) {
  if (level === "error") return { status: "crit", label: "錯誤" };
  if (level === "warn") return { status: "warn", label: "警告" };
  return { status: "neutral", label: String(level ?? "—") };
}

export function messageGroups(messages = []) {
  const groups = [
    { role: "system", label: "系統", items: [] },
    { role: "user", label: "使用者", items: [] },
    { role: "assistant", label: "助理", items: [] },
  ];
  const other = { role: "other", label: "其他", items: [] };
  messages.forEach((message, index) => {
    const group = groups.find((item) => item.role === message?.role) ?? other;
    group.items.push({ index: index + 1, role: message?.role ?? "", content: message?.content ?? "" });
  });
  return [...groups, other].filter((group) => group.items.length > 0);
}

export function attemptFailed(exchange, outcome) {
  if (exchange?.error) return true;
  const attempt = outcome?.attempts?.find((item) => item.attempt === exchange?.attempt);
  return Boolean(attempt?.validation_errors?.length);
}

export function attemptErrors(exchange, outcome) {
  return outcome?.attempts?.find((item) => item.attempt === exchange?.attempt)?.validation_errors ?? [];
}

export const NUMBER = new Intl.NumberFormat("zh-TW");
export function formatCount(value) {
  return typeof value === "number" && Number.isFinite(value) ? NUMBER.format(value) : "—";
}
