// party-skill-model (webclient-party-skill-tab, design §6.4): the pure
// projections the party window's 技能 tab reads. Nothing here evaluates a
// rule: costs, growth, lineage and the ladder are the committed `character`
// v9 payload's own facts, availability is the server preview's answer once
// 施放 is pressed, and every string is client display copy or a committed
// reason.

// The committed reasons the action bar states in combat (design §6.4): the
// casting card owns combat casting, and the server refuses a booking in
// combat with the same line (world/rules/time_skip.py BOOKING_IN_COMBAT_MESSAGE).
export const CAST_IN_COMBAT_REASON = "戰鬥中請使用指令卡";
export const PRACTICE_IN_COMBAT_REASON = "戰鬥中無法排入修煉。";
export const CAST_IN_DIALOGUE_REASON = "對話中無法施放。";
export const CAST_UNAVAILABLE_REASON = "目前無法施放。";
export const CAST_COMBAT_ONLY_REASON = "此技能僅能在戰鬥中使用。";

// The field capability, worded as a capability (never a `combat` badge and
// never a claim about present availability).
export const FIELD_CAPABLE_TEXT = "可於戰鬥外使用";
export const COMBAT_ONLY_TEXT = "僅能在戰鬥中使用";

// The colour dot the binding visual reference (docs/design/elosern-redesign/
// index.html) samples: fire, water and wind elemental groups and the
// sexual-act category. Any other group has no dot.
const ELEMENT_DOT = Object.freeze({
  fire: "var(--seal-500)",
  water: "var(--vit-mp)",
  wind: "var(--warn)",
});

export function groupDot(category, group) {
  if (category === "sexual_act") return "var(--seal-500)";
  if (category === "elemental_magic" && ELEMENT_DOT[group]) return ELEMENT_DOT[group];
  return null;
}

function skillsOf(group) {
  return Array.isArray(group?.skills) ? group.skills : [];
}

function groupsOf(category) {
  return Array.isArray(category?.groups) ? category.groups : [];
}

export function skillCount(rows) {
  let count = 0;
  for (const category of rows ?? []) {
    for (const group of groupsOf(category)) count += skillsOf(group).length;
  }
  return count;
}

// The search: a case-insensitive substring of the skill, group or category
// label. The payload's category → group → skill order is never re-sorted.
export function filterCategories(rows, query) {
  const q = typeof query === "string" ? query.trim().toLowerCase() : "";
  const matches = (row, group, category) =>
    !q || [row.label, group?.label, category?.label].some((label) => typeof label === "string" && label.toLowerCase().includes(q));
  const filtered = [];
  for (const category of rows ?? []) {
    const groups = [];
    for (const group of groupsOf(category)) {
      const skills = skillsOf(group).filter((row) => matches(row, group, category));
      if (skills.length) groups.push({ ...group, skills });
    }
    if (groups.length) filtered.push({ ...category, groups });
  }
  return filtered;
}

// Every skill of the given categories with its context, in rendered order.
export function flattenSkills(categories) {
  const list = [];
  for (const category of categories ?? []) {
    for (const group of groupsOf(category)) {
      for (const row of skillsOf(group)) list.push({ row, group, category });
    }
  }
  return list;
}

// A registry-backed active row carries the descriptor fields; an
// unregistered key carries only its identity and growth facts.
export const hasDescriptor = (row) => !!row && Object.prototype.hasOwnProperty.call(row, "cost");
export const hasGrowth = (row) => !!row && Number.isFinite(row.level);

// Display-only normalization: practice XP is a float; only the stored pair
// is formatted, never a progression rule.
export function formatXp(value) {
  if (!Number.isFinite(value)) return "0";
  return Number.isInteger(value) ? String(value) : String(Math.round(value * 10) / 10);
}

// The row's growth facts: `xp_to_next_level` is what remains of the level
// band, so the band is the stored pair's sum.
export function growthOf(row) {
  if (!hasGrowth(row)) return null;
  const into = Number.isFinite(row.xp_into_level) ? Math.max(0, row.xp_into_level) : 0;
  const toNext = Number.isFinite(row.xp_to_next_level) ? Math.max(0, row.xp_to_next_level) : 0;
  const band = into + toNext;
  const capped = row.capped === true;
  const percent = capped ? 100 : band > 0 ? Math.min(100, Math.round((into / band) * 100)) : 0;
  return {
    level: row.level,
    capped,
    into,
    band,
    percent,
    levelText: capped ? "見頂" : `Lv ${row.level}`,
    xpText: capped ? "已達上限" : `${formatXp(into)} / ${formatXp(band)}`,
  };
}

// The cost as text with its resource prefix (colour only accompanies it).
export function costOf(row) {
  if (!hasDescriptor(row)) return null;
  const cost = row.cost ?? {};
  const parts = [];
  if (cost.mp > 0) parts.push(`MP ${cost.mp}`);
  if (cost.sp > 0) parts.push(`SP ${cost.sp}`);
  if (!parts.length) return { text: "無消耗", tone: "free" };
  return { text: parts.join(" ‧ "), tone: cost.mp > 0 ? "mp" : "sp" };
}

// The committed `selected_skill` section, only while it names the row on
// screen: the lineage position and the optional ladder never attach to
// another row.
export function selectedSectionFor(panel, rowKey) {
  const section = panel?.selected_skill;
  if (!section || typeof rowKey !== "string" || section.key !== rowKey) return null;
  return section;
}

// The five rungs verbatim: an unlocked rung shows its server-computed MP
// cost, a locked one the level that unlocks it. No client arithmetic.
export function ladderOf(section) {
  const ladder = Array.isArray(section?.freeform_ladder) ? section.freeform_ladder : [];
  return ladder.map((entry) => {
    const locked = entry.unlock_level != null;
    return {
      scale: entry.scale,
      label: entry.label,
      locked,
      standard: entry.scale === 1,
      valueText: locked ? `需 Lv ${entry.unlock_level}` : `MP ${entry.mp_cost}`,
    };
  });
}

// The lineage position: prerequisite(s) → the skill → next unlock(s).
export function lineageOf(section) {
  const lineage = section?.lineage;
  if (!lineage) return null;
  const prerequisites = Array.isArray(lineage.prerequisites) ? lineage.prerequisites : [];
  const next = Array.isArray(lineage.next) ? lineage.next : [];
  return {
    prerequisites: prerequisites.map((edge) => ({ key: edge.key, label: edge.label, levelText: `Lv ${edge.level}` })),
    next: next.map((edge) => ({ key: edge.key, label: edge.label, levelText: `Lv ${edge.min_level}` })),
  };
}

// What 施放 offers for the selected row in the current mode — a label and a
// committed reason, never a legality verdict (the server preview decides).
// Null when the row cannot be cast at all (passive or undescribed).
export function castAction({ row, active, mode, combat, locked, pending }) {
  if (!active || !row || typeof row.usable_out_of_combat !== "boolean") return null;
  const base = { key: "cast", label: "施放", tone: "primary", glyph: "skills" };
  if (combat || mode === "combat") return { ...base, enabled: false, reason: CAST_IN_COMBAT_REASON };
  if (mode === "dialogue") return { ...base, enabled: false, reason: CAST_IN_DIALOGUE_REASON };
  if (mode !== "exploration") return { ...base, enabled: false, reason: CAST_UNAVAILABLE_REASON };
  if (!row.usable_out_of_combat) return { ...base, enabled: false, reason: CAST_COMBAT_ONLY_REASON };
  if (pending) return { ...base, label: "準備中…", enabled: false, reason: null, busy: true };
  return { ...base, enabled: !locked, reason: null };
}

// 排入修煉: one standing booking for the viewed member (no sub-screen).
export function practiceAction({ row, active, combat, disabled, memberId }) {
  if (!active || !row) return null;
  const base = { key: "practice", label: "排入修煉", tone: "gold" };
  if (combat) return { ...base, enabled: false, reason: PRACTICE_IN_COMBAT_REASON };
  return { ...base, enabled: !disabled && memberId !== null, reason: null };
}
