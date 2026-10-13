// The exploration screen's shared readout (exploration-exit-compass design
// D4; scene overview redesign §3.6 and §5.3): one explanation line whose
// content is chosen by priority — a transient flash for a blocked move, then
// whatever is aimed or hovered, then the idle summary. Pure: the pane owns
// the state and the flash timer; the presence rail, the place card's
// buttons, and the 建議 pill feed the same priority function
// (exploration-presence-rail, exploration-room-actions).
import { octantGlyph } from "./compass-model.js";

// How long a blocked-move flash holds the readout.
export const FLASH_MS = 1600;

export const NO_EXIT_TEXT = "這個方向沒有出口";
export const DEAD_END_TEXT = "這個方向沒有路了，停下腳步。";
export const SUPPRESSED_TEXT = "上一步還沒走完，先停下腳步。";
export const NO_CHANGE_TEXT = "沒有走出這裡，停下腳步。";
const NOWHERE_LEAD = "·";

// The compass aim (§3.6): an angled target names its destination after the
// octant glyph, a portal after its bead glyph, a disabled target shows its
// server-authored reason unaltered, and an aim at nothing says so. No aim
// (the compass at rest) contributes nothing.
export function aimReadout(aim) {
  if (!aim) {
    return null;
  }
  const target = aim.target || null;
  if (target) {
    if (!target.enabled) {
      return { lead: "無法通行", text: target.reason || target.label, tone: "warn" };
    }
    const lead = target.kind === "portal" ? `通道 ${target.glyph}` : `前往 ${target.glyph}`;
    return { lead, text: target.label, tone: "normal" };
  }
  if (aim.zone === "dead") {
    return { lead: NOWHERE_LEAD, text: NO_EXIT_TEXT, tone: "quiet" };
  }
  if (aim.angle === null || aim.angle === undefined) {
    return null;
  }
  return { lead: octantGlyph(aim.angle), text: NO_EXIT_TEXT, tone: "quiet" };
}

// A blocked move's flash, in the warn tone. `resultMessage` is the server's
// message for the compass's own last request, when there is one.
export function blockedReadout(blocked, { resultMessage = null } = {}) {
  if (!blocked) {
    return null;
  }
  const lead =
    blocked.angle === null || blocked.angle === undefined ? NOWHERE_LEAD : octantGlyph(blocked.angle);
  switch (blocked.kind) {
    case "disabled":
      return {
        lead: "無法通行",
        text: (blocked.target && (blocked.target.reason || blocked.target.label)) || NO_EXIT_TEXT,
        tone: "warn",
      };
    case "dead-end":
      return { lead, text: DEAD_END_TEXT, tone: "warn" };
    case "rejected":
      return { lead: "無法前進", text: blocked.message || resultMessage || NO_CHANGE_TEXT, tone: "warn" };
    case "no-change":
      return { lead: "停下腳步", text: resultMessage || NO_CHANGE_TEXT, tone: "warn" };
    case "suppressed":
      return { lead: "停下腳步", text: SUPPRESSED_TEXT, tone: "warn" };
    case "no-exit":
    default:
      return { lead, text: `${NO_EXIT_TEXT}。`, tone: "warn" };
  }
}

// The idle summary: the room's exit count and the people present.
export function idleReadout(exitCount, presentCount) {
  return { lead: "", text: `出口 ${exitCount} · 在場 ${presentCount}`, tone: "quiet" };
}

// The people present in the committed exploration panel: every interact
// target plus every present entity without an interact descriptor (the
// overview's 人物 row).
export function presentCount(panel) {
  if (!panel || panel.available === false) {
    return 0;
  }
  const ids = new Set();
  for (const target of panel.interact || []) {
    ids.add(String(target.identity));
  }
  for (const entity of (panel.look && panel.look.entities) || []) {
    ids.add(String(entity.identity));
  }
  return ids.size;
}

// A departed person's flash (exploration-presence-rail; redesign §7): the
// verb card closed because its person left in the committed panel.
export function departedReadout(name) {
  return { lead: "", text: `${name} 已經離開了。`, tone: "warn" };
}

// The place card's buttons (exploration-room-actions; redesign §5.3).
export const PLACE_LOOK_READOUT = Object.freeze({ lead: "查看房間", text: "重新觀察四周", tone: "normal" });
export const PLACE_WAIT_READOUT = Object.freeze({ lead: "等待", text: "讓時間流逝、休息或睡眠", tone: "normal" });

// The 建議 pill: how many next steps the card lists, or what it is doing.
export function pillReadout(status, count) {
  if (status === "generating") {
    return { lead: "建議", text: "AI 正在構思建議…", tone: "normal" };
  }
  if (count > 0) {
    return { lead: "建議", text: `${count} 個可行的下一步`, tone: "normal" };
  }
  return { lead: "建議", text: "查看可行的下一步", tone: "normal" };
}

// Priority (§5.3; exploration-room-actions design D6): a blocked-move flash,
// then whatever is aimed or hovered, then idle. Inside the aimed-or-hovered
// tier the pointed-at controls outrank the compass aim, which stays set while
// the compass rests: a hovered or focused place-card button, then the 建議
// pill, then a presence-rail entry, then the compass aim. Hovering or
// focusing any of them is the player's latest act of attention (focusing one
// blurs the compass), and leaving one falls back to the next live slot.
export function readoutContent({ flash = null, aim = null, rail = null, place = null, pill = null, idle = null } = {}) {
  if (flash) {
    return { ...flash, flash: true };
  }
  for (const source of [place, pill, rail, aim]) {
    if (source) {
      return { ...source, flash: false };
    }
  }
  return idle ? { ...idle, flash: false } : { lead: "", text: "", tone: "quiet", flash: false };
}
