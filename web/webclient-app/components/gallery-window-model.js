// Pure view-model functions of the gallery window (gallery window design
// D4/D9; change gallery-wall-component design D2). No Vue, no DOM, no side
// effects: the wall reads the committed v4 panel through these helpers.

// The tray item id of the 生成新圖 tile; `selectedImage` names it to mark
// that tile selected.
export const GENERATE_TILE = "generate";

// A scene subject is drawn as a 16:9 landscape tile; every other kind as a
// 9:16 portrait tile.
export function tileShape(kind) {
  return kind === "scene" ? "landscape" : "portrait";
}

// Whether the selected subject's committed capabilities let it hold more
// than one card (and therefore open a tray). Null capabilities open none.
export function trayOpen(capabilities) {
  return capabilities !== null && capabilities !== undefined && capabilities.max_cards !== 1;
}

// The wall's tiles in reading order: every subject of every expanded group.
// A collapsed group lists no subject, so it contributes no tile.
export function wallTiles(groups) {
  return (groups ?? [])
    .filter((group) => group.expanded)
    .flatMap((group) => group.subjects.map((subject) => ({ groupKey: group.key, subject })));
}

// The tray's items in order: the committed card rows in payload order, then
// the 生成新圖 tile, then the official entries.
export function trayItems(cards, officialEntries) {
  return [
    ...(cards ?? []).map((row) => ({ id: row.image_id, kind: "card", row })),
    { id: GENERATE_TILE, kind: "generate", row: null },
    ...(officialEntries ?? []).map((row) => ({ id: row.identity, kind: "official", row })),
  ];
}

// The index (within its group) of the last tile on the owner's row: the tray
// is placed directly after it. A short last row ends at the group's last tile.
export function trayInsertIndex(ownerIndex, columns, groupLength) {
  const perRow = Math.max(1, columns);
  return Math.min(groupLength - 1, Math.ceil((ownerIndex + 1) / perRow) * perRow - 1);
}
