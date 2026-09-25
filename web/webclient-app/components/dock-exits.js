// Exit presentation helpers shared by the dock's exit outlet (DockMenu.vue)
// and the scene overview's exit chips (SceneOverview.vue), moved out of
// DockMenu.vue (webclient-scene-overview-component design D6).
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
