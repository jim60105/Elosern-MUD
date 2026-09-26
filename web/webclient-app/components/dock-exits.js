import { disabledReasonText } from "./dock-items.js";

// Exit presentation helpers for the scene overview's exit chips
// (SceneOverview.vue) and the dialogue choice list's exit rows
// (DialogueChoices.vue, webclient-dialogue-choices-overlay D8), moved out of DockMenu.vue when the dock's exit outlet
// was retired (webclient-scene-overview-component design D6,
// webclient-retire-exploration-submenus).
//
// The fixed client-side direction-glyph table (H3 design D9): a move row's
// canonical direction resolves to a glyph; a direction string outside the
// table (named doors, dynamic wilderness gates) resolves to no glyph, and
// the row keeps its own label as primary text. The table is built on a
// null prototype so an out-of-table direction can never collide with an
// inherited `Object.prototype` property name.
const DIRECTION_GLYPHS = Object.assign(Object.create(null), {
  north: "↑",
  south: "↓",
  east: "→",
  west: "←",
  northeast: "↗",
  northwest: "↖",
  southeast: "↘",
  southwest: "↙",
  up: "↑",
  down: "↓",
});

export function directionGlyph(direction) {
  if (direction === null || direction === undefined) {
    return null;
  }
  return DIRECTION_GLYPHS[direction] ?? null;
}

// The destination label for an exit row (task 5.4): joined from the
// committed `local_map.nodes[].label`. Null when the destination is not in
// the committed lattice.
export function destinationLabel(item, localMapModel) {
  if (!item || !item.destination || !localMapModel || !Array.isArray(localMapModel.nodes)) {
    return null;
  }
  const node = localMapModel.nodes.find((n) => n.id === item.destination);
  return node ? node.label : null;
}

// An exit row's headline (the exit outlet's rule): while enabled with a
// canonical direction and a known destination, the destination's name;
// otherwise the row's own label.
export function exitLabel(item, localMapModel) {
  if (item && item.enabled !== false && directionGlyph(item.direction)) {
    return destinationLabel(item, localMapModel) || item.label;
  }
  return item ? item.label : "";
}

// The server-authored reason of a disabled exploration row: the dock's
// shared reader first, then the exploration menu's own fields. Null for an
// enabled row.
export function disabledRowReason(item) {
  if (!item || item.enabled !== false) {
    return null;
  }
  return (
    disabledReasonText(item) ||
    (item.disabledReason && item.disabledReason.message) ||
    item.description ||
    null
  );
}
