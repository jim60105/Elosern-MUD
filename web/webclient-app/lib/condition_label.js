// The ONE condition label rule (webclient-frontend-utils): the accessible
// chip name (ConditionChips) and the drawer roster prose (CharacterStatusDrawer)
// MUST agree — label (or code fallback), the verbatim remaining duration when
// the payload supplies numeric `remaining_seconds`, and every derived modifier
// pair, joined with `，`. Both components delegate to this single copy.
//
// Modifier keys are the combat-modifier rulebook's adjustment fields
// (world/rules/rulebook/combat_modifiers.yaml). They are named with the
// game's stat vocabulary (攻擊 / 敏捷 / 防禦 as the character panel names the
// traits; 準度 as the condition labels name accuracy); an unrecognised key is
// named by the neutral 其他修正 so its value is never dropped. Values are
// printed verbatim: no sign, unit or rounding is added or removed.
export const MODIFIER_LABELS = Object.freeze({
  atk_phys: "攻擊",
  agility: "敏捷",
  agility_flat: "敏捷",
  defense: "防禦",
  accuracy: "準度",
  actions_per_turn: "每回合行動",
  chance: "觸發機率",
  mp_regen_scale: "魔力回復倍率",
  recovery_share_bonus: "回復分享加成",
  sp_cost: "耐力消耗",
  mp_cost: "魔力消耗",
  heal_gain: "治療量",
  recovery_arousal_scale: "回復興奮倍率",
  blessing_arousal_scale: "祝福興奮倍率",
});

export const UNKNOWN_MODIFIER_LABEL = "其他修正";

export function modifierLabel(key) {
  return Object.hasOwn(MODIFIER_LABELS, key) ? MODIFIER_LABELS[key] : UNKNOWN_MODIFIER_LABEL;
}

// Each derived modifier as `{key, text}` in payload order; `key` stays the
// raw identifier (hooks and keys), `text` is the readable pair.
export function conditionModifiers(condition) {
  const mods = condition?.modifiers;
  if (!mods || typeof mods !== "object") return [];
  return Object.entries(mods).map(([key, value]) => ({
    key,
    text: `${modifierLabel(key)} ${String(value)}`,
  }));
}

export function conditionLabel(condition) {
  const parts = [condition.label ?? condition.code];
  if (typeof condition.remaining_seconds === "number") {
    parts.push(`剩 ${condition.remaining_seconds} 秒`);
  }
  for (const modifier of conditionModifiers(condition)) {
    parts.push(modifier.text);
  }
  const source = conditionSource(condition);
  if (source) parts.push(source);
  return parts.join("，");
}

export function conditionSource(condition) {
  const provenance = condition.provenance;
  if (provenance.kind === "unknown") return "來源暫無資料";
  if (provenance.kind === "non_equipment") return "";
  const labels = provenance.equipment_sources.map((source) => source.label).join("、");
  return `裝備來源：${labels}${provenance.kind === "mixed" ? "，另有獨立來源" : ""}`;
}
