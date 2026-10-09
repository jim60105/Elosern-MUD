// Grade gem material ladder (quest-drawer-ui-primitives, design Decision 5):
// iron (F) → bronze (E) → dark bronze (D) → silver (C) → gold (B) → bright
// gold (A) → seal-red with a gold rim (S). Each material is the set of CSS
// custom properties GradeGem.vue reads; the values are copied from the
// approved prototype's `.qd-gem--<grade>` rules
// (docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue). The letter
// always carries the meaning; the material only reinforces it.

// The inner rim every grade below A shares (the prototype's default).
const DEFAULT_INNER = "rgba(185, 154, 96, 0.35)";

export const GRADE_MATERIALS = Object.freeze({
  F: Object.freeze({ "--gem-hi": "#3b3d42", "--gem-lo": "#1a1b1f", "--gem-rim": "#6d6a62", "--gem-ink": "#c9c4b9", "--gem-inner": DEFAULT_INNER }),
  E: Object.freeze({ "--gem-hi": "#4a3b2b", "--gem-lo": "#1d1712", "--gem-rim": "#8a6a45", "--gem-ink": "#e1c29b", "--gem-inner": DEFAULT_INNER }),
  D: Object.freeze({ "--gem-hi": "#5a4527", "--gem-lo": "#221a10", "--gem-rim": "#a27d45", "--gem-ink": "#ecd3a6", "--gem-inner": DEFAULT_INNER }),
  C: Object.freeze({ "--gem-hi": "#55585e", "--gem-lo": "#1d1f23", "--gem-rim": "#a9adb3", "--gem-ink": "#eef0f2", "--gem-inner": DEFAULT_INNER }),
  B: Object.freeze({ "--gem-hi": "#6a5730", "--gem-lo": "#261e0f", "--gem-rim": "var(--gold-500)", "--gem-ink": "var(--gold-300)", "--gem-inner": DEFAULT_INNER }),
  A: Object.freeze({ "--gem-hi": "#7a6230", "--gem-lo": "#2c210c", "--gem-rim": "var(--gold-400)", "--gem-ink": "#fff3d4", "--gem-inner": "var(--gold-500)" }),
  S: Object.freeze({ "--gem-hi": "var(--seal-600)", "--gem-lo": "var(--seal-700)", "--gem-rim": "var(--gold-400)", "--gem-ink": "var(--gold-300)", "--gem-inner": "var(--gold-500)" }),
});

// The material for a grade key; any unknown or missing key gets iron (F).
export function gradeMaterial(grade) {
  return Object.hasOwn(GRADE_MATERIALS, grade) ? GRADE_MATERIALS[grade] : GRADE_MATERIALS.F;
}
