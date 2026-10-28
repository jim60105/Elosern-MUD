// The one priority banner (frontend design §5.2): the highest-priority active
// condition with a single action. Derived from the displayed snapshot, the
// connection, the follow hold and the command client's failure; nothing is
// pre-checked locally.
//
// 1. disconnected, or a restarted service (action: reconnect and read)
// 2. a failed or uncertain save (action: explicit reread)
// 3. an external change held behind open drafts (action: load new version)
// 4. a rejected command (action: explicit reread; ends with a newer snapshot)
// 5. a stale or unavailable preview (no action; recovery is automatic)

import { changedDocuments, HOLD_DRAFT, HOLD_RESTART } from "./following.js";
import { persistenceBanner } from "./persistence.js";
import { clock, priorityBanner } from "./status.js";
import { DISCONNECTED } from "./workspace_client.js";

const PERSISTENT = new Set(["save_failed", "save_uncertain", "reread_failed"]);

function draftsClause(drafts) {
  return drafts > 0 ? `${drafts} 個未確認草稿` : "";
}

export function workspaceBanner({ workspace, connection, hold = null, pending = null, drafts = 0, failure = null }) {
  const status = priorityBanner(workspace, connection);
  if (connection === DISCONNECTED) return status;
  if (hold === HOLD_RESTART) {
    const lost = draftsClause(drafts);
    return {
      key: "restarted",
      tone: "seal",
      title: "服務已重啟",
      text: `畫面停留在 ${clock(workspace?.checked_at)} 的快照，現在無法寫入。重新連線並讀取後才能寫入${
        lost ? `；${lost}與復原紀錄會被捨棄` : ""
      }。尚未送出的操作不會重送。`,
      action: "reconnect",
    };
  }
  if (workspace?.pending_intent || (failure && PERSISTENT.has(failure.code))) {
    return persistenceBanner(workspace, failure);
  }
  if (hold === HOLD_DRAFT) {
    const documents = changedDocuments(workspace, pending);
    return {
      key: "external-draft",
      tone: "warn",
      title: "檔案已被外部修改（有草稿）",
      text: `${documents.join("、") || "工作區"} 已被外部修改。載入新版會捨棄${draftsClause(drafts) || "草稿"}與目前的復原/重做紀錄。`,
      action: "adopt",
      documents,
    };
  }
  if (failure) return persistenceBanner(workspace, failure);
  return status;
}
