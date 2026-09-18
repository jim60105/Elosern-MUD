// The ONE condition label rule (webclient-frontend-utils): the accessible
// chip name (ConditionChips) and the drawer roster prose (CharacterStatusDrawer)
// MUST agree — label (or code fallback), the verbatim remaining duration when
// the payload supplies numeric `remaining_seconds`, and every derived modifier
// pair, joined with `，`. Both components delegate to this single copy.
export function conditionLabel(condition) {
  const parts = [condition.label ?? condition.code];
  if (typeof condition.remaining_seconds === "number") {
    parts.push(`剩 ${condition.remaining_seconds} 秒`);
  }
  const mods = condition.modifiers;
  if (mods && typeof mods === "object") {
    for (const [key, value] of Object.entries(mods)) {
      parts.push(`${key} ${value}`);
    }
  }
  return parts.join("，");
}
