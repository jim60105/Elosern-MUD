// CharacterStatusDrawer read-model group: the `character` v8 payload
// projections plus the `party_member` persona/intimate sections, extracted so
// the SFC stays a thin, passive renderer. Owns availability/reason gating, the
// true-trait rows and the 屬性 allowlist filter, the disguise comparison, the
// guild counters, the persona section table and the intimate disclosure rows
// (the hero's full title reads the `status` panel instead). Persona prose and
// intimate state come from `party_member`: the commander section owns the
// prose, and the viewed member's section owns the intimate rows. Consumes the
// component props explicitly; the status group consumes this group's `traits`
// and subject guard for its gauge-layer check.
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
  // owned by the 生命量 and 計數‧公會 sections, so the 屬性 section filters
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

  // Equipment is presented by the party window's 背包 tab
  // (webclient-party-bag-retire), so the flat list's computed is retired.

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

  // The `party_member` panel is the source of the persona and intimate
  // sections (character v8 dropped both). When it is unavailable the drawer
  // marks the persona area with its registry-owned reason and invents nothing.
  const partyMemberAvailable = computed(
    () => props.partyMember?.available !== false
  );
  const partyMemberReason = computed(() =>
    partyMemberAvailable.value ? null : (props.partyMember?.reason ?? null)
  );
  const commanderSection = computed(() =>
    partyMemberAvailable.value ? (props.partyMember?.commander ?? null) : null
  );
  const memberSection = computed(() => {
    if (!partyMemberAvailable.value) return null;
    return commanderSection.value ?? props.partyMember?.companion ?? null;
  });

  // The persona area (add-persona-edit-surface D4): the four editable prose
  // sections in 個性／生平／習慣／背景 order, from the commander section of
  // `party_member`. Each value is the committed section's verbatim text or
  // null; a null renders the localized 未設定 placeholder (display copy only —
  // the payload never carries placeholder text). The structural persona keys
  // (identity, appearance, social_connection) are not part of the wire payload
  // and are never rendered here. The array stays an array (empty while the
  // commander section is absent) so the inline editor's watcher never
  // dereferences null; the template gates the whole area separately.
  const PERSONA_SECTIONS = [
    { key: "personality", label: "個性" },
    { key: "life_story", label: "生平" },
    { key: "habit", label: "習慣" },
    { key: "background", label: "背景" },
  ];

  const personaSections = computed(() => {
    const persona = commanderSection.value?.persona ?? null;
    if (persona === null) return [];
    return PERSONA_SECTIONS.map((section) => ({
      ...section,
      value: persona[section.key] ?? null,
    }));
  });
  // The area renders while the commander section exists, and also while
  // `party_member` is unavailable (so its registry-owned reason stays
  // visible); it is absent while a companion is the viewed member.
  const personaVisible = computed(
    () => !partyMemberAvailable.value || commanderSection.value !== null
  );

  const intimate = computed(() => memberSection.value?.intimate ?? null);

  // The character panel follows the viewed member while `status` describes
  // the controlled figure — and under possession that panel's resources
  // belong to the owner while its identity names the puppet. The two panels'
  // trait/gauge facts may therefore only be combined when no possession is
  // active and both name the same member.
  const characterSubjectMatches = computed(() => {
    if (props.possessing) return false;
    const memberId = props.character?.member_id;
    const identity = props.status?.actor?.identity;
    if (!Number.isSafeInteger(memberId) || memberId <= 0) return false;
    const subject = Number(identity);
    return Number.isSafeInteger(subject) && subject === memberId;
  });

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
    personaVisible,
    partyMemberAvailable,
    partyMemberReason,
    intimate,
    characterSubjectMatches,
    INTIMATE_ROWS,
  };
}
