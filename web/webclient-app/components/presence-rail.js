// The presence rail's pure slot rules (exploration-presence-rail design D7;
// scene overview redesign §4.1), shared by the rail, the store's digit path,
// and the overflow card so all three agree on what is visible.

// At most six slots show.
export const RAIL_MAX = 6;

// The `＋N` slot's key. Real entry keys are `target-`, `entity-`, or
// `object-` prefixed, so it can never collide with one.
export const RAIL_MORE_KEY = "presence-more";

// The visible slots: every entry up to six; beyond six, the first five
// entries and a `＋N` slot counting the rest.
export function railSlots(entries) {
  const list = Array.isArray(entries) ? entries : [];
  if (list.length <= RAIL_MAX) {
    return list;
  }
  const shown = list.slice(0, RAIL_MAX - 1);
  const rest = list.length - shown.length;
  shown.push({
    key: RAIL_MORE_KEY,
    presence: "more",
    label: "其餘",
    count: rest,
    summary: "列出其餘在場者與物件",
    enabled: true,
    actionId: null,
    payload: null,
  });
  return shown;
}

// The entries the overflow card lists: everything the rail folded into `＋N`.
export function railOverflow(entries) {
  const list = Array.isArray(entries) ? entries : [];
  return list.length > RAIL_MAX ? list.slice(RAIL_MAX - 1) : [];
}

// The readout content for a hovered or focused slot (§4.1, §5.3): the name
// over the affordance summary, or 查看.
export function railReadout(entry) {
  if (!entry) {
    return null;
  }
  if (entry.presence === "more") {
    return { lead: `＋${entry.count}`, text: entry.summary, tone: "normal" };
  }
  return { lead: entry.label, text: entry.summary || "查看", tone: "normal" };
}
