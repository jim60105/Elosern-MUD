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

// ---- the image page (change gallery-image-page) -----------------------------

function footerButton(key, label, tone = "plain", extra = {}) {
  return { key, label, tone, enabled: true, testid: `gallery-page__${key}`, ...extra };
}

// The image page's footer descriptor (gallery-image-page design D2): the
// buttons a selection offers, in order, and an optional note for the footer's
// reason line. It reads the selection and the subject's committed
// capabilities only — never a subject category — so the button table of the
// window design follows from the declared facts. Null capabilities declare
// nothing.
export function galleryFooter(selection, capabilities) {
  const caps = capabilities ?? {};
  if (!selection || selection.type === "empty") {
    return { buttons: [footerButton("generate", "生成新圖", "primary")], note: null };
  }
  if (selection.type === "official") {
    if (!caps.supports_personal_official_preferences) return { buttons: [], note: null };
    return {
      buttons: [
        footerButton("official-geometry-clear", "清除個人調整"),
        ...(caps.supports_face_rect ? [footerButton("official-face", "臉框")] : []),
        ...(caps.supports_stage ? [footerButton("official-stage", "舞台位置")] : []),
        selection.row.is_current
          ? footerButton("official-clear-selection", "清除選取")
          : footerButton("official-select", "設為預設", "primary"),
      ],
      note: null,
    };
  }
  const row = selection.row;
  if (row.status === "pending") return { buttons: [], note: "生成中" };
  if (row.status === "failed") return { buttons: [footerButton("regenerate", "重新生成", "primary")], note: null };
  const buttons = [];
  let note = null;
  if (caps.supports_card_delete) buttons.push(footerButton("delete", "刪除", "danger"));
  if (caps.supports_face_rect) buttons.push(footerButton("face", "臉框"));
  if (caps.supports_stage) buttons.push(footerButton("stage", "舞台位置"));
  if (caps.supports_bindings) buttons.push(footerButton("binding", "綁定裝備"));
  if (caps.max_cards === null) {
    buttons.push(footerButton("default", "設為預設", "primary", { enabled: !row.is_default, describedByReason: true }));
    if (row.is_default) note = "目前預設";
  } else if (caps.max_cards === 1) {
    buttons.push(footerButton("regenerate", "重新生成", "primary"));
  }
  // The destructive button stands apart from the rest of the row.
  if (buttons[0]?.key === "delete" && buttons[1]) buttons[1] = { ...buttons[1], spacerBefore: true };
  return { buttons, note };
}

// ---- the landscape page (change gallery-landscape-page) ---------------------

// The image page takes the selected subject's tile shape: a scene subject's
// page is landscape (the 16:9 art above the facts), every other kind's
// portrait (the 9:16 art beside them).
export function pageShape(kind) {
  return tileShape(kind);
}

// The image an empty selection shows: for a landscape subject, its committed
// tile artwork — the bundled image in effect while no card is stored; for
// every other kind (or a scene without tile artwork) none, so the page says
// 尚無圖片.
export function bundledArtwork(subject) {
  return subject && pageShape(subject.kind) === "landscape" ? subject.artwork ?? null : null;
}

// The page ribbon: the category label, then `・` and the group label when the
// subject's group has one.
export function galleryRibbon(categoryLabel, groupLabel) {
  return groupLabel ? `${categoryLabel}・${groupLabel}` : categoryLabel;
}

// ---- the window (change gallery-window-component) ---------------------------

// The image a newly committed subject opens on (gallery window design D4):
// its default card, else its first card row, else its current official
// entry, else its first official entry, else none (the empty page). Card ids
// and official identities never collide, so one id names the selection.
export function initialImage(cards, officialEntries) {
  const rows = cards ?? [];
  const entries = officialEntries ?? [];
  const card = rows.find((row) => row.is_default) ?? rows[0];
  if (card) return card.image_id;
  const entry = entries.find((row) => row.is_current) ?? entries[0];
  return entry ? entry.identity : null;
}
