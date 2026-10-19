// party-window-model (webclient-party-window-member-tab, design §6/§6.1): the
// pure projections the party window and its 成員 tab read. Nothing here
// computes a rule: every enablement and reason is a committed server
// descriptor or affordance, and every label is client display copy.

// The first-level tabs in their fixed order. `key` is the wire tab value
// `party.view_member` accepts (`web/webclient/presentation/
// party_view_selection.py` TABS), so a selection names the open tab exactly.
export const PARTY_WINDOW_TABS = Object.freeze([
  Object.freeze({ key: "member", label: "成員", glyph: "member" }),
  Object.freeze({ key: "bag", label: "背包", glyph: "inventory" }),
  Object.freeze({ key: "status", label: "狀態", glyph: "status" }),
  Object.freeze({ key: "skills", label: "技能", glyph: "skills" }),
  Object.freeze({ key: "lineage", label: "系譜", glyph: "lineage" }),
]);

export const PARTY_WINDOW_TAB_KEYS = new Set(PARTY_WINDOW_TABS.map((tab) => tab.key));

// The panel each not-yet-built tab reads (the next changes fill them; the
// 背包 tab is PartyBagTab, which states its own panel's reason).
export const TAB_BACKING_PANEL = Object.freeze({
  status: "character",
  skills: "character",
  lineage: "lineage",
});

export const PERSONA_SECTIONS = Object.freeze([
  Object.freeze({ key: "personality", label: "個性" }),
  Object.freeze({ key: "life_story", label: "生平" }),
  Object.freeze({ key: "habit", label: "習慣" }),
  Object.freeze({ key: "background", label: "背景" }),
]);

export const INTIMATE_ROWS = Object.freeze([
  Object.freeze({ key: "arousal", label: "興奮" }),
  Object.freeze({ key: "wetness", label: "濕潤" }),
  Object.freeze({ key: "shame", label: "羞恥" }),
  Object.freeze({ key: "exposure", label: "露出" }),
  Object.freeze({ key: "climax_phase", label: "高潮" }),
  Object.freeze({ key: "climax_today", label: "今日" }),
]);

// The client's own state line for a 空位 with no invite affordance in the
// committed room (a state, not a rule explanation).
export const NO_INVITE_TARGET_TEXT = "這裡沒有可邀請的對象。";

const isAvailable = (panel) => !!panel && panel.available === true;

export function partyRows(party) {
  return isAvailable(party) && Array.isArray(party.slots) ? party.slots : [];
}

// The MemberRail entries: every committed row in panel order (the commander
// first). The rail carries no possession or "you" marker; the portrait column
// stays the initial because only the shared attempt lifecycle may resolve an
// artwork descriptor into an image (the 成員 nameplate carries the artwork).
export function railMembers(party) {
  return partyRows(party).map((row) => ({
    id: row.identity,
    name: row.display_name,
    portrait: null,
    knockedOut: row.knocked_out === true,
    unread: row.unread === true,
  }));
}

export function viewedMemberId(party) {
  if (!isAvailable(party)) return null;
  const id = party.viewed_member_id;
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

export function hasFreeSlot(party) {
  const quota = isAvailable(party) ? party.general_quota : null;
  return !!quota && Number.isInteger(quota.used) && Number.isInteger(quota.limit) && quota.used < quota.limit;
}

export function rowById(party, id) {
  return partyRows(party).find((row) => row.identity === id) ?? null;
}

// The committed reason of an unavailable panel ({code, message}) or null.
export function panelReason(panel) {
  if (!panel || panel.available !== false) return null;
  const reason = panel.reason;
  if (reason && typeof reason.message === "string") return reason;
  return null;
}

// The 空位's invite target: the first committed interact target whose
// `explore.party_invite` affordance is enabled, else the first one carrying a
// disabled invite affordance (with its committed reason), else none.
export function inviteResolution(interactTargets) {
  let disabled = null;
  for (const target of Array.isArray(interactTargets) ? interactTargets : []) {
    const affordance = (target?.affordances || []).find((a) => a?.action_id === "explore.party_invite");
    if (!affordance) continue;
    if (affordance.enabled !== false) {
      return { target, enabled: true, reason: null };
    }
    if (!disabled) {
      const message = affordance.disabled_reason?.message;
      disabled = { target, enabled: false, reason: typeof message === "string" && message ? message : null };
    }
  }
  return disabled ?? { target: null, enabled: false, reason: NO_INVITE_TARGET_TEXT };
}

// One `party_member` descriptor as an ActionBar action: the committed
// enablement and reason, verbatim.
export function descriptorAction(descriptor, { key, label, tone = null, glyph = null }) {
  return {
    key,
    label,
    tone,
    glyph,
    enabled: descriptor?.enabled === true,
    reason: descriptor?.enabled === true ? null : (descriptor?.reason ?? null),
  };
}

export function findDescriptor(actions, actionIds) {
  const ids = Array.isArray(actionIds) ? actionIds : [actionIds];
  return (Array.isArray(actions) ? actions : []).find((a) => ids.includes(a?.action_id)) ?? null;
}

export function gaugePercent(current, maximum) {
  const max = Number(maximum);
  const cur = Number(current);
  if (!Number.isFinite(max) || max <= 0 || !Number.isFinite(cur)) return 0;
  return Math.max(0, Math.min(100, Math.round((cur / max) * 100)));
}

const numberFormat = new Intl.NumberFormat("en-US");
export function formatPurse(value) {
  return numberFormat.format(value);
}
