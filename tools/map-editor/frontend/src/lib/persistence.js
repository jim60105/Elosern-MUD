// Save-state presentation (frontend design §5.1-§5.3). The service is
// authoritative: an operation counts as saved only after its acknowledgement,
// an uncertain result is whatever the service's write pause says, and nothing
// here retries or restores state from browser storage.

import { clock } from "./status.js";

export const SAVED = "saved";
export const SAVING = "saving";
export const DRAFT = "draft";
export const FAILED = "failed";
export const UNCERTAIN = "uncertain";

// A field draft is complete only as a plain decimal integer.
export function parseIntegerDraft(text) {
  const trimmed = String(text ?? "").trim();
  if (!/^-?\d+$/.test(trimmed)) return { ok: false };
  const value = Number(trimmed);
  return Number.isSafeInteger(value) ? { ok: true, value } : { ok: false };
}

export function saveState({ workspace, inFlight = 0, failure = null, drafts = 0 }) {
  if (workspace?.write_pause?.reason === "uncertain_durability" || failure?.code === "save_uncertain") {
    return UNCERTAIN;
  }
  if (failure) return FAILED;
  if (inFlight > 0) return SAVING;
  if (drafts > 0) return DRAFT;
  return SAVED;
}

export function saveChip(state, savedAt) {
  switch (state) {
    case UNCERTAIN:
      return { tone: "seal", glyph: "?", text: "存檔結果不確定" };
    case FAILED:
      return { tone: "seal", glyph: "✕", text: "存檔失敗" };
    case SAVING:
      return { tone: "busy", glyph: "⟳", text: "存檔中" };
    case DRAFT:
      return { tone: "draft", glyph: "✎", text: "有未確認草稿" };
    default:
      return { tone: "ok", glyph: "✓", text: savedAt ? `已存檔 ${clock(savedAt)}` : "已存檔" };
  }
}

const COMMAND_LABELS = {
  move_interior_layout: "移動房間版面",
  remove_interior_layout: "移除版面文件",
  undo: "復原",
  redo: "重做",
};

export function commandLabel(name) {
  return COMMAND_LABELS[name] ?? name;
}

// Banner priority 2: a failed, uncertain or rejected save. Its only action is
// an explicit reread; there is never an automatic retry.
export function persistenceBanner(workspace, failure) {
  const intent = workspace?.pending_intent;
  if (intent || failure?.code === "save_uncertain") {
    const document = intent?.document_id ?? failure?.documentId ?? "";
    return {
      key: "save-uncertain",
      tone: "seal",
      title: `?「${commandLabel(intent?.command ?? failure?.command)}」存檔結果不確定`,
      text: `${document} 可能已寫入也可能未寫入。重新讀取前不會再寫入，也不會自動重試。`,
      action: "reload",
    };
  }
  if (!failure) return null;
  const document = failure.documentId ? `${failure.documentId}：` : "";
  return {
    key: failure.code === "save_failed" ? "save-failed" : "save-rejected",
    tone: "seal",
    title: `✕「${commandLabel(failure.command)}」未存檔`,
    text: `${document}${failure.message}（${failure.code}）。磁碟上仍是上次讀取的版本。`,
    action: "reload",
  };
}
