// CharacterStatusDrawer character-panel read-model group: the `character` v5/v7
// payload projections extracted verbatim from `CharacterStatusDrawer.vue` so
// the SFC stays a thin, passive renderer. Owns availability/reason gating, the
// true-trait rows and the 屬性 allowlist filter, the disguise comparison, the
// guild counters, the persona section table, the intimate disclosure rows, and
// the composed full title. Consumes the component props explicitly; the status
// group consumes this group's `traits` for its gauge-layer guard.
import { computed } from "vue";

export function useStatusDrawerCharacter(props) {
  // The `character` body (task 5.3): render the trait table (true values only),
  // equipment, disguise, guild and persona. When the panel is unavailable,
  // show the registry-owned reason and invent no rows.
  const characterAvailable = computed(() => props.character?.available !== false);
  const characterReason = computed(() => (characterAvailable.value ? null : (props.character?.reason ?? null)));

  const traits = computed(() => (characterAvailable.value && Array.isArray(props.character?.traits) ? props.character.traits : []));

  // The 設計稿's #dr-status 屬性 section shows only the four true-attribute
  // rows. The gauge (hp/mp/sp) and counter (guild_merit) values are already
  // owned by the 生命量 and 計數・公會 sections, so the 屬性 section filters
  // to an allowlist (fails closed: a new server trait key renders nowhere
  // until reviewed in) rather than rendering every trait row.
  const ATTRIBUTE_KEYS = ["atk_phys", "agility", "defense", "magic_power"];

  const attributeRows = computed(() => {
    const byKey = new Map(traits.value.map((row) => [row.key, row]));
    return ATTRIBUTE_KEYS.map((key) => byKey.get(key)).filter(Boolean);
  });


  function traitValue(row) {
    return row.max === null ? String(row.current) : `${row.current} / ${row.max}`;
  }

  // The equipment section is now the EquipmentDoll component (task 6.3); the
  // doll reads `character.equipment` itself, so the flat list's computed is
  // retired.

  // The disguise section (task 5.4): the `displayed[]` values paired with the
  // true trait they describe, shown as a 真值 / 顯示 side-by-side comparison,
  // with the standing statement that combat always resolves on true traits.
  const disguise = computed(() => (characterAvailable.value ? (props.character?.disguise ?? null) : null));
  const disguiseActive = computed(() => disguise.value?.active === true);
  const displayedRows = computed(() => {
    const rows = disguise.value?.displayed;
    if (!Array.isArray(rows)) return [];
    return rows.map((row) => {
      const trueRow = traits.value.find((t) => t.key === row.key);
      return {
        key: row.key,
        label: row.label,
        value: row.value,
        trueValue: trueRow ? trueRow.current : null,
      };
    });
  });

  const guild = computed(() => (characterAvailable.value ? (props.character?.guild ?? null) : null));

  // The persona area (add-persona-edit-surface D4): the four editable prose
  // sections in 個性／生平／習慣／背景 order. Each value is the committed
  // panel's verbatim text or null; a null renders the localized 未設定
  // placeholder (display copy only — the payload never carries placeholder
  // text). The structural persona keys (identity, appearance,
  // social_connection) are not part of the wire payload and are never
  // rendered here.
  const PERSONA_SECTIONS = [
    { key: "personality", label: "個性" },
    { key: "life_story", label: "生平" },
    { key: "habit", label: "習慣" },
    { key: "background", label: "背景" },
  ];

  const personaSections = computed(() =>
    PERSONA_SECTIONS.map((section) => ({
      ...section,
      value: characterAvailable.value
        ? (props.character?.persona?.[section.key] ?? null)
        : null,
    }))
  );

  const intimate = computed(() => (characterAvailable.value ? (props.character?.intimate ?? null) : null));

  // The composed live full title (character panel v6 optional field); rendered
  // as a header line only when present — a pre-onboarding character shows no
  // title line (title-system D6 name fallback applies at the HUD head).
  const fullTitle = computed(() =>
    characterAvailable.value ? (props.character?.full_title ?? "") : ""
  );

  // The 親密狀態 (intimate status) section rows: the 設計稿's #dr-status stat
  // grid. The first five rows are level words from the fixed vocabulary, and
  // the last row is the daily climax count.
  const INTIMATE_ROWS = [
    { key: "arousal", label: "興奮" },
    { key: "wetness", label: "濕潤" },
    { key: "shame", label: "羞恥" },
    { key: "exposure", label: "露出" },
    { key: "climax_phase", label: "高潮" },
    { key: "climax_today", label: "今日" },
  ];

  return {
    characterAvailable,
    characterReason,
    traits,
    attributeRows,
    traitValue,
    disguise,
    disguiseActive,
    displayedRows,
    guild,
    personaSections,
    intimate,
    fullTitle,
    INTIMATE_ROWS,
  };
}
