// title-codex-model (handbook-titles-tab, design D5): the pure view model of
// the handbook's titles tab over the committed `title_codex` v1 panel. Every
// function takes the committed panel (or null) and derives presentation only:
// the client evaluates no gate rule. Equip availability follows the row's
// `unlocked` and the panel's `equipped` slot, and removal follows the
// server-computed `can_remove` flag verbatim.
//
// The guild grade gem (`guildGrade`) is the only client-side reading of a
// title key; a row that does not match draws its category emblem instead.

// The closed fixed-title category order (the server enum), with the authored
// rail labels; 風流韻事 is shortened on the rail only.
export const TITLE_CATEGORIES = Object.freeze([
  { key: "combat", label: "戰鬥" },
  { key: "spell", label: "法術" },
  { key: "explore", label: "探索" },
  { key: "guild", label: "公會" },
  { key: "clergy", label: "聖職" },
  { key: "romance", label: "風流韻事", short: "韻事" },
]);

const CATEGORY_KEYS = TITLE_CATEGORIES.map((category) => category.key);
const isFixedRail = (rail) => CATEGORY_KEYS.includes(rail);

// "absent" before the first commit, "unavailable" for the common unavailable
// form, else "available".
export function titleCodexStatus(panel) {
  if (!panel) return "absent";
  return panel.available === true ? "available" : "unavailable";
}

const available = (panel) => titleCodexStatus(panel) === "available";
const fixedRows = (panel) => (available(panel) && Array.isArray(panel.fixed_rows) ? panel.fixed_rows : []);
const epithetRows = (panel) => (available(panel) && Array.isArray(panel.epithet_rows) ? panel.epithet_rows : []);
const ballotRows = (panel) => (available(panel) && Array.isArray(panel.pending_ballot) ? panel.pending_ballot : []);
const rowsOf = (panel, category) => fixedRows(panel).filter((row) => row.category === category);
const equippedFixed = (panel) => (available(panel) ? (panel.equipped?.fixed ?? null) : null);

// The rail: the six categories with their unlocked counts, the epithet entry,
// then the ballot entry only while a ballot is pending (a hot count).
export function titleRail(panel) {
  if (!available(panel)) return [];
  const rail = TITLE_CATEGORIES.map((category) => ({
    key: category.key,
    label: category.short ?? category.label,
    count: rowsOf(panel, category.key).filter((row) => row.unlocked).length,
  }));
  rail.push({ key: "epithet", label: "異名", count: epithetRows(panel).length });
  const ballot = ballotRows(panel);
  if (ballot.length > 0) rail.push({ key: "ballot", label: "提名", count: ballot.length, hot: true });
  return rail;
}

// The first category in closed order holding an unlocked row, else the first.
export function defaultTitleRail(panel) {
  return TITLE_CATEGORIES.find((category) => rowsOf(panel, category.key).some((row) => row.unlocked))?.key
    ?? TITLE_CATEGORIES[0].key;
}

// The full label of a rail entry (the list heading and the detail ribbon).
export function titleRailLabel(rail) {
  if (rail === "epithet") return "異名";
  if (rail === "ballot") return "提名中";
  return TITLE_CATEGORIES.find((category) => category.key === rail)?.label ?? "";
}

export function guildGrade(row) {
  if (row?.category !== "guild" || typeof row.key !== "string") return null;
  const match = row.key.match(/^g_([a-z])_rank$/);
  return match ? match[1].toUpperCase() : null;
}

// The medal wall's items for a fixed rail, in payload order.
export function medalItems(panel, rail) {
  if (!isFixedRail(rail)) return [];
  const equipped = equippedFixed(panel);
  return rowsOf(panel, rail).map((row) => {
    const isEquipped = equipped === row.key;
    const state = !row.unlocked ? "未取得" : isEquipped ? "裝備中" : "已取得";
    return {
      id: row.key,
      selectable: true,
      label: `${row.display}，${state}`,
      locked: !row.unlocked,
      equipped: isEquipped,
      grade: guildGrade(row),
      row,
    };
  });
}

// QuestList rows for the epithet and ballot rails.
export function titleListRows(panel, rail) {
  const rows = rail === "epithet" ? epithetRows(panel) : rail === "ballot" ? ballotRows(panel) : [];
  return rows.map((row) => ({
    id: row.display,
    name: row.display,
    glyph: "codex",
    sub: rail === "epithet" && row.equipped ? `★ 裝備中・${row.basis}` : row.basis,
    grade: null,
    progress: null,
    tracked: false,
  }));
}

export function defaultTitleSelection(panel, rail) {
  if (isFixedRail(rail)) {
    const rows = rowsOf(panel, rail);
    return (rows.find((row) => row.unlocked) ?? rows[0])?.key ?? null;
  }
  return titleListRows(panel, rail)[0]?.id ?? null;
}

// The detail view model of one entry (CodexDetail's `detail`), or null for an
// unknown id.
export function titleDetail(panel, rail, id) {
  if (id == null) return null;
  if (isFixedRail(rail)) {
    const row = rowsOf(panel, rail).find((candidate) => candidate.key === id);
    if (!row) return null;
    const equipped = equippedFixed(panel) === row.key;
    const locked = !row.unlocked;
    return {
      kind: "fixed",
      id: row.key,
      name: row.display,
      ribbon: `${titleRailLabel(rail)}稱號`,
      emblem: row.category,
      grade: guildGrade(row),
      locked,
      equipped,
      removable: false,
      stamp: locked ? { kind: "locked", label: "未取得" } : equipped ? { kind: "equipped", label: "裝備中" } : null,
      subtitle: locked ? "" : (row.flavor ?? ""),
      sections: locked ? [{ label: "取得條件", text: row.hint || "—" }] : [],
      index: null,
      row,
    };
  }
  if (rail === "epithet") {
    const row = epithetRows(panel).find((candidate) => candidate.display === id);
    if (!row) return null;
    return {
      kind: "epithet",
      id: row.display,
      name: row.display,
      ribbon: "異名",
      emblem: "epithet",
      grade: null,
      locked: false,
      equipped: row.equipped === true,
      removable: row.can_remove === true,
      stamp: row.equipped ? { kind: "equipped", label: "裝備中" } : null,
      subtitle: row.basis ?? "",
      sections: [],
      index: null,
      row,
    };
  }
  if (rail === "ballot") {
    const ballot = ballotRows(panel);
    const index = ballot.findIndex((candidate) => candidate.display === id);
    if (index < 0) return null;
    const row = ballot[index];
    return {
      kind: "ballot",
      id: row.display,
      name: row.display,
      ribbon: "異名提名",
      emblem: "ballot",
      grade: null,
      locked: false,
      equipped: false,
      removable: false,
      stamp: { kind: "pending", label: "提名中" },
      subtitle: row.basis ?? "",
      sections: [],
      index,
      row,
    };
  }
  return null;
}

function equipButton(detail, reason) {
  return {
    key: "equip",
    label: detail.equipped ? "已裝備" : "裝備",
    tone: "primary",
    enabled: !detail.locked && !detail.equipped,
    describedByReason: true,
    spacerBefore: !reason,
    testid: "handbook__equip",
  };
}

// The DetailFooter props of one detail (null for no detail). `armed` shows the
// removal confirmation; it applies only to a removable epithet.
export function titleFooter(detail, { armed = false } = {}) {
  if (!detail) return null;
  const base = { testid: "handbook__actions", reasonTestid: "handbook__action-reason", reasonTone: "plain", reasonRole: null };
  if (detail.kind === "fixed") {
    const reason = detail.locked ? "尚未取得，無法裝備" : detail.equipped ? "★ 目前裝備中" : null;
    return { ...base, reason, buttons: [equipButton(detail, reason)] };
  }
  if (detail.kind === "epithet") {
    if (armed && detail.removable) {
      return {
        ...base,
        reason: "移除後無法恢復，確定要移除這個異名嗎？",
        reasonTone: "danger",
        reasonRole: "alert",
        buttons: [
          { key: "cancel", label: "取消", tone: "ghost", testid: "handbook__remove-cancel" },
          { key: "confirm-remove", label: "確認移除", tone: "primary", testid: "handbook__remove-confirm" },
        ],
      };
    }
    const reason = detail.equipped ? "★ 目前裝備中" : null;
    return {
      ...base,
      reason,
      buttons: [
        ...(detail.removable ? [{ key: "remove", label: "移除…", tone: "ghost", testid: "handbook__remove" }] : []),
        equipButton(detail, reason),
      ],
    };
  }
  return {
    ...base,
    reason: null,
    buttons: [
      { key: "decline", label: "放棄提名", tone: "ghost", testid: "handbook__ballot-decline" },
      { key: "accept", label: "接受此異名", tone: "primary", spacerBefore: true, testid: "handbook__ballot-accept" },
    ],
  };
}

// The `{action_id, payload}` intent of a footer key, or null for a disabled
// or unknown key.
export function titleIntent(detail, key) {
  if (!detail) return null;
  if (key === "equip") {
    if (detail.locked || detail.equipped) return null;
    if (detail.kind === "fixed") return { action_id: "title.equip", payload: { kind: "fixed", identifier: detail.row.key } };
    if (detail.kind === "epithet") return { action_id: "title.equip", payload: { kind: "epithet", identifier: detail.row.display } };
    return null;
  }
  if (key === "confirm-remove") {
    return detail.kind === "epithet" && detail.removable
      ? { action_id: "title.remove", payload: { display: detail.row.display } }
      : null;
  }
  if (key === "accept") {
    return detail.kind === "ballot" ? { action_id: "title.accept", payload: { index: detail.index + 1 } } : null;
  }
  if (key === "decline") {
    return detail.kind === "ballot" ? { action_id: "title.decline", payload: {} } : null;
  }
  return null;
}
