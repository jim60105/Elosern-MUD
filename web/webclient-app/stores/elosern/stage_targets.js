// The stage target step (webclient-combat-stage-target-picking, design D1):
// one pure model of the target frame of an enabled SINGLE, SELF or AREA skill
// while its targets are picked on the stage figures instead of in the card's
// rows. It derives everything from the current frame's items (their keys and
// payloads, never reordered), the opened skill's client-local selection, the
// committed participants and the formation's stage order; it mutates
// nothing, so the store, the components and Vitest all read the same answer.
//
// A position is `{ key, kind, identities, side, digit, offStage, label }`:
// - `member` — one SINGLE `target-<id>` or AREA `area-<id>` item, on one figure;
// - `self` — the SELF `self-confirm` item, on the controlled figure;
// - `group` — one AREA `shorthand-<key>` item, lighting a whole side;
// - `confirm` — the AREA `area-confirm` item, lighting the current choice.

// The frames that open one skill's target items (frame-resolvers.js).
export const STAGE_TARGET_SOURCES = Object.freeze(["combat.skill", "combat.target"]);

// The client display labels of the three approved AREA shorthands
// (world/rules/targeting.py AREA_SHORTHANDS); the payload keeps the key.
export const GROUP_LABELS = Object.freeze({
  "all-enemies": "全體敵人",
  "all-allies": "全體我方",
  all: "全體",
});

export const SIDE_LABELS = Object.freeze({ foes: "敵方", party: "我方" });

const FORMS = new Set(["single", "self", "area"]);

function idKey(identity) {
  return String(identity);
}

// The position an item of the current frame stands for, or null when the
// item is no target item of the stage step (a scale chip, a NONE confirm, a
// disabled skill's explanation row, a back row).
function itemPosition(item, form) {
  const key = item && typeof item.key === "string" ? item.key : null;
  if (!key) {
    return null;
  }
  if (form === "single" && key.startsWith("target-")) {
    const ids = item.payload && Array.isArray(item.payload.target_ids) ? item.payload.target_ids : [];
    return ids.length === 1 ? { key, kind: "member", identity: ids[0] } : null;
  }
  if (form === "self" && key === "self-confirm") {
    return { key, kind: "self" };
  }
  if (form === "area") {
    if (key.startsWith("area-") && key !== "area-confirm" && item.actionId === "toggle-target") {
      const identity = item.payload ? item.payload.identity : undefined;
      return identity === undefined || identity === null ? null : { key, kind: "member", identity };
    }
    if (key.startsWith("shorthand-") && item.actionId === "choose-shorthand") {
      const shorthand = item.payload ? item.payload.shorthand : null;
      return typeof shorthand === "string" ? { key, kind: "group", shorthand } : null;
    }
    if (key === "area-confirm") {
      return { key, kind: "confirm" };
    }
  }
  return null;
}

// The default stage order when no measured formation is published (layout-free
// tests and stories): every participant that has not fled, the party before
// the foes, each side in presenter order — the formation's own left-to-right
// reading of the two sides.
export function fallbackFormationOrder(participants) {
  const rows = Array.isArray(participants) ? participants.filter((p) => p && p.state !== "fled") : [];
  return [...rows.filter((p) => p.team !== "foes"), ...rows.filter((p) => p.team === "foes")].map((p) =>
    idKey(p.identity),
  );
}

// The candidates a group position lights: the skill's server candidates of
// that side (`all` every candidate), in the server's order.
function groupIdentities(shorthand, candidates, byId) {
  return candidates.filter((identity) => {
    const row = byId.get(idKey(identity));
    if (shorthand === "all") return true;
    if (shorthand === "all-enemies") return !!row && row.team === "foes";
    if (shorthand === "all-allies") return !!row && row.team === "party";
    return false;
  });
}

// `stageTargetModel` — null outside a stage target step, else the step.
//
// Inputs: `source` (the current frame descriptor's source), `menu` (the
// current frame's resolved menu), `skill` (the CombatMenu skill model the
// frame opened, with its `selected` / `shorthand`), `participants` (the
// committed combat participants), `formationOrder` (the drawn identities in
// stage order, left to right, or null), `controlledIdentity` (the controlled
// figure's identity), `focusKey` (the frame's focused item key) and `locked`
// (a combat round plays by itself).
export function stageTargetModel({
  source,
  menu,
  skill,
  participants,
  formationOrder,
  controlledIdentity,
  focusKey,
  locked,
} = {}) {
  if (locked || !STAGE_TARGET_SOURCES.includes(source)) {
    return null;
  }
  if (!skill || !skill.enabled || !FORMS.has(skill.targetSpec)) {
    return null;
  }
  const items = menu && Array.isArray(menu.items) ? menu.items : [];
  const form = skill.targetSpec;
  // Every item of the frame must be a target item of this form: a scale step
  // (`scale-*`), a NONE confirm or a disabled skill's row is no step.
  const raw = items.map((item, index) => ({ item, index, position: itemPosition(item, form) }));
  if (raw.length === 0 || raw.some((entry) => entry.position === null)) {
    return null;
  }
  if (form === "self" && (controlledIdentity === null || controlledIdentity === undefined)) {
    return null;
  }

  const rows = Array.isArray(participants) ? participants : [];
  const byId = new Map(rows.filter(Boolean).map((p) => [idKey(p.identity), p]));
  // Stage order: the formation's published order, then every other drawn
  // participant in the fallback order (a roster change can commit a frame
  // before the new formation is published). Whether a candidate stands on the
  // stage is its committed state (only a fled participant has no figure),
  // never the published order, so the commit's own frame is already right.
  const order = Array.isArray(formationOrder) ? formationOrder.map(idKey) : [];
  for (const identity of fallbackFormationOrder(rows)) {
    if (!order.includes(identity)) order.push(identity);
  }
  const stageIndex = new Map(order.map((identity, index) => [identity, index]));
  const drawn = (identity) => {
    const row = byId.get(idKey(identity));
    return !!row && row.state !== "fled";
  };
  const candidates = Array.isArray(skill.targets) ? skill.targets : [];
  const selected = form === "area" && Array.isArray(skill.selected) ? skill.selected.map(idKey) : [];
  const shorthand = form === "area" && typeof skill.shorthand === "string" ? skill.shorthand : null;

  // Display names shared by two or more candidates take the session token.
  const nameCounts = new Map();
  for (const identity of candidates) {
    const name = byId.get(idKey(identity))?.display_name;
    if (typeof name === "string" && name) nameCounts.set(name, (nameCounts.get(name) || 0) + 1);
  }
  const nameOf = (identity) => {
    const row = byId.get(idKey(identity));
    const name = (row && row.display_name) || "";
    const token = row && typeof row.token === "string" && row.token ? row.token : "";
    return nameCounts.get(name) > 1 && token ? `${name}（${token}）` : name;
  };
  const sideOf = (identity) => (byId.get(idKey(identity))?.team === "foes" ? "foes" : "party");
  const digitOf = (index) => (index < 9 ? index + 1 : null);

  const members = [];
  const tail = [];
  for (const { item, index, position } of raw) {
    if (position.kind === "member") {
      const id = idKey(position.identity);
      members.push({
        key: position.key,
        kind: "member",
        identities: [id],
        side: sideOf(position.identity),
        digit: digitOf(index),
        offStage: !drawn(position.identity),
        label: nameOf(position.identity),
        serverIndex: index,
      });
    } else if (position.kind === "self") {
      const id = idKey(controlledIdentity);
      members.push({
        key: position.key,
        kind: "self",
        identities: [id],
        side: "party",
        digit: digitOf(index),
        offStage: false,
        label: "自己",
        serverIndex: index,
      });
    } else if (position.kind === "group") {
      tail.push({
        key: position.key,
        kind: "group",
        shorthand: position.shorthand,
        // A group's size and lit set are the candidates standing on the
        // stage: a listed fled participant has no figure to light or count.
        identities: groupIdentities(position.shorthand, candidates, byId).filter(drawn).map(idKey),
        side: position.shorthand === "all-enemies" ? "foes" : position.shorthand === "all-allies" ? "party" : null,
        digit: digitOf(index),
        offStage: false,
        label: GROUP_LABELS[position.shorthand] || item.label || position.shorthand,
      });
    } else {
      tail.push({
        key: position.key,
        kind: "confirm",
        identities: [],
        side: null,
        digit: digitOf(index),
        offStage: false,
        label: "施展",
      });
    }
  }
  // Members in stage order: drawn figures left to right, then the candidates
  // no figure draws (only a fled participant) in the server's order.
  members.sort((a, b) => {
    if (a.offStage !== b.offStage) return a.offStage ? 1 : -1;
    if (a.offStage) return a.serverIndex - b.serverIndex;
    const delta = stageIndex.get(a.identities[0]) - stageIndex.get(b.identities[0]);
    return delta || a.serverIndex - b.serverIndex;
  });
  // The confirm position lights the current choice: the explicit selection,
  // else the chosen shorthand's group, else nothing.
  const groupOf = (key) => tail.find((p) => p.kind === "group" && p.shorthand === key) || null;
  const chosenGroup = shorthand ? groupOf(shorthand) : null;
  const choice = selected.length > 0 ? selected : chosenGroup ? chosenGroup.identities : [];
  for (const position of tail) {
    if (position.kind === "confirm") position.identities = choice.slice();
  }
  const positions = [...members, ...tail].map(({ serverIndex, ...rest }) => Object.freeze(rest));
  if (positions.length === 0) {
    return null;
  }

  const focused = positions.find((p) => p.key === focusKey) || null;
  // A focused candidate no figure draws (a fled participant) lights nothing.
  const lit = focused && !focused.offStage ? focused.identities.filter((id) => drawn(id) || focused.kind === "self") : [];
  const selectable = members.map((p) => p.identities[0]);
  const digits = {};
  for (const p of members) {
    if (p.digit !== null) digits[p.identities[0]] = p.digit;
  }

  return Object.freeze({
    form,
    skillKey: skill.key,
    label: skill.label || "",
    scaleLabel: scaleLabelOf(skill),
    positions,
    focusKey: focused ? focused.key : null,
    focused,
    lit,
    selectable,
    selectedIds: selected,
    shorthand,
    choiceCount: choice.length,
    digits,
    announce: announceFor(focused, { selected, shorthand, chosenGroup, choice }),
  });
}

// The chosen 威力 label of a master's freeform skill (the scale step's own
// chip label), or null for a skill that carries no scales.
function scaleLabelOf(skill) {
  const scales = Array.isArray(skill.freeformScales) ? skill.freeformScales : [];
  const chosen = scales.find((entry) => entry && entry.scale === skill.scale);
  return chosen && chosen.label != null ? `威力 ×${chosen.label}` : null;
}

// The polite announcement (spec "The focused target is announced"): it names
// the focused position, its side, a group's size or the current choice.
function announceFor(position, { selected, shorthand, chosenGroup, choice }) {
  if (!position) {
    return "";
  }
  if (position.kind === "self") {
    return "目標：自己";
  }
  if (position.kind === "member") {
    const id = position.identities[0];
    let text = `目標：${position.label}，${SIDE_LABELS[position.side]}`;
    if (position.offStage) text += "，場外";
    if (selected.includes(id)) text += "，已選";
    return text;
  }
  if (position.kind === "group") {
    return `目標：${position.label}，共 ${position.identities.length} 名`;
  }
  if (selected.length > 0) {
    return `施展：已選 ${selected.length} 名`;
  }
  if (shorthand) {
    const label = chosenGroup ? chosenGroup.label : GROUP_LABELS[shorthand] || shorthand;
    return `施展：${label}，共 ${choice.length} 名`;
  }
  return "施展：尚未選擇目標";
}

// The position the arrow keys move to (design D2): Right/Down the next one
// in stage order and Left/Up the previous one, each wrapping; from a focus
// that is no position, Right/Down the first and Left/Up the last. A single
// position keeps the focus where it is (null).
export function arrowTarget(model, key) {
  if (!model || model.positions.length === 0) {
    return null;
  }
  const forward = key === "ArrowRight" || key === "ArrowDown";
  const keys = model.positions.map((p) => p.key);
  const index = model.focusKey === null ? -1 : keys.indexOf(model.focusKey);
  if (index === -1) {
    return forward ? keys[0] : keys[keys.length - 1];
  }
  if (keys.length === 1) {
    return null;
  }
  return keys[(index + (forward ? 1 : -1) + keys.length) % keys.length];
}

export const ARROW_KEYS = Object.freeze(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"]);
