// The NPC service-menu prototype's pure row rules (reference only, mock data;
// not imported by the app). One person-focus card, three groups in a fixed
// order: the common interactions (row 1 交談 and row 2 查看人物 for every
// NPC, kept with their reason even when disabled), the conditional
// interactions (invite / possess / persona, in one fixed order whatever order
// the fixture supplies them in), then the services, in the order the supplied
// service descriptors list them. Every row but a status line takes a number
// by position, a disabled row keeps its number, digits stop at 9 (later rows
// stay reachable by the arrows and the scroller with a `·` badge), and the
// trailing `✕ 返回` is the production back row (unnumbered, Escape).
//
// Services exist only when the NPC's fixture supplies service descriptors:
// none (or an empty list) renders no services group at all, and an
// unreadable service read renders one non-actionable status line instead of
// any service row, so no stale service can be activated.
import { BACK_ROW } from "../../../web/webclient-app/composables/use-person-focus.js";

export const SERVICES_UNREADABLE_TEXT = "服務資訊暫時無法讀取。";
export const PAUSED_PREFIX = "暫停";

// The conditional interactions' fixed order (prototype assumption).
export const CONDITIONAL_ORDER = Object.freeze(["invite", "possess", "persona"]);

const MAX_DIGIT = 9;

// The production verb card's badge rule: digits 1–9, then `·`.
function digitBadge(index) {
  return index < MAX_DIGIT ? String(index + 1) : "·";
}

function conditionalRank(key) {
  const rank = CONDITIONAL_ORDER.indexOf(key);
  return rank < 0 ? CONDITIONAL_ORDER.length : rank;
}

// The effective services state of a fixture NPC: "ready" with at least one
// descriptor, "unreadable", or "none" (no capability, or an empty list).
export function servicesState(npc) {
  const services = npc?.services;
  if (services?.state === "unreadable") {
    return "unreadable";
  }
  if (services?.state === "ready" && Array.isArray(services.entries) && services.entries.length > 0) {
    return "ready";
  }
  return "none";
}

// The card's rows and the per-row facts the prototype's pick handler reads.
// Returns `{rows, digitRows, trailingIndex, meta}`; `meta[key]` is
// `{type: "talk"|"look"|"conditional"|"service", flow?, label}`.
export function serviceMenuRows(npc) {
  const numbered = [];
  const meta = {};

  const talk = npc.talk || { enabled: true, reason: null };
  numbered.push({
    key: "talk",
    label: "交談",
    kind: "verb",
    enabled: talk.enabled !== false,
    reason: talk.enabled === false ? talk.reason || null : null,
    testId: "service-card-row",
  });
  meta.talk = { type: "talk", label: "交談" };

  numbered.push({ key: "look", label: "查看人物", kind: "verb", enabled: true, reason: null, testId: "service-card-row" });
  meta.look = { type: "look", label: "查看人物" };

  const conditional = [...(npc.conditional || [])].sort(
    (a, b) => conditionalRank(a.key) - conditionalRank(b.key),
  );
  for (const item of conditional) {
    const key = `cond:${item.key}`;
    numbered.push({
      key,
      label: item.label,
      kind: "conditional",
      enabled: item.enabled !== false,
      reason: item.enabled === false ? item.reason || null : null,
      testId: "service-card-row",
    });
    meta[key] = { type: "conditional", label: item.label };
  }

  const state = servicesState(npc);
  if (state === "ready") {
    for (const entry of npc.services.entries) {
      const key = `service:${entry.key}`;
      const paused = entry.available === false;
      numbered.push({
        key,
        label: entry.label,
        kind: "service",
        enabled: !paused,
        // The paused state is stated in text, never by colour alone.
        reason: paused ? `${PAUSED_PREFIX}：${entry.reason || "目前無法使用。"}` : null,
        testId: "service-card-row",
      });
      meta[key] = { type: "service", flow: entry.flow, label: entry.label };
    }
  }

  const rows = numbered.map((row, index) => ({ ...row, badge: digitBadge(index) }));
  if (state === "unreadable") {
    // A status line in the services position: unnumbered, never actionable.
    rows.push({
      key: "services-unreadable",
      label: SERVICES_UNREADABLE_TEXT,
      badge: "—",
      kind: "service-status",
      enabled: false,
      reason: null,
      testId: "service-card-status",
    });
  }
  const trailingIndex = rows.length;
  rows.push(BACK_ROW);
  return { rows, digitRows: Math.min(MAX_DIGIT, numbered.length), trailingIndex, meta };
}

// The rail readout's second line: the card's actionable labels, joined like
// the production presence summary.
export function railSummary(npc) {
  return serviceMenuRows(npc)
    .rows.filter((row) => !row.back && row.kind !== "service-status")
    .map((row) => row.label)
    .join("／");
}
