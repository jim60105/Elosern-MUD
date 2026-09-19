// CharacterStatusDrawer status-panel read-model group: the committed `status`
// v1 projections extracted verbatim from `CharacterStatusDrawer.vue` — the
// three gauges, the FULL condition roster (no 6-chip cap, unlike H2's
// ConditionChips island), and the breakdown layer-chip math
// (render-equipment-breakdown-webclient D1). Consumes the component props and
// the character group's `traits` computed explicitly (the gauge chips decompose
// the maximum the trait payload also carries).
import { computed } from "vue";
import { gaugeRatio } from "../components/vitals.js";

export function useStatusDrawerStatus(props, traits) {
  // Per-severity glyph shapes: the same non-colour-separated set H2's
  // ConditionChips uses, so no two severities differ by colour alone.
  const SEVERITY_GLYPHS = {
    beneficial: "▲",
    informational: "◆",
    warning: "▽",
    harmful: "▼",
    critical: "✕",
  };

  const SEVERITY_LABELS = {
    beneficial: "增益",
    informational: "資訊",
    warning: "警示",
    harmful: "減益",
    critical: "致命",
  };

  const resources = computed(() => props.status?.resources ?? null);

  // --- Breakdown layer chips (render-equipment-breakdown-webclient D1) -----
  // A chip is a pure projection of one payload layer: the verbatim registry
  // `name` plus an amount formatted ONLY by `kind` (the raw amount is
  // re-signed for display, never recomputed): mult → a SIGNED factor `×1.2`
  // / `×−1.2` (the wire accepts negative non-zero factors) with trailing
  // zeros stripped, flat → `+4`/`−2`, pct → `−10%`/`+15%`; U+2212 minus
  // throughout. An unknown kind renders the signed verbatim number on a
  // neutral chip (direct-render defense; the wire validators reject unknown
  // enums).
  function formatLayerAmount(kind, amount) {
    const n = Number(amount);
    const magnitude = Math.abs(n);
    const sign = n < 0 ? "−" : "+";
    if (kind === "mult") {
      // A negative factor stays visible: the wire validator accepts signed
      // non-zero mult amounts and the server prose keeps the factor sign.
      return `×${n < 0 ? "−" : ""}${String(magnitude)}`;
    }
    const digits = String(magnitude);
    if (kind === "pct") {
      return `${sign}${digits}%`;
    }
    if (kind === "flat") {
      return `${sign}${digits}`;
    }
    return `${sign}${digits}`;
  }

  // Source tints reuse the existing design tokens (skill = buff-green,
  // condition = warn-amber, equipment = gold). An unknown `source` OR an
  // unknown `kind` gets the neutral 其他 class AND label suffix — an
  // unrecognised formatting rule is not a trusted skill/condition/equipment
  // chip (text-bearing, never colour-alone, WCAG baseline). The wire never
  // carries unknown enums; this fallback only guards a direct component
  // render with hand-built props.
  const LAYER_TINTS = { skill: "skill", condition: "condition", equipment: "equipment" };
  const LAYER_KINDS = new Set(["mult", "flat", "pct"]);

  function layerTint(layer) {
    return Object.hasOwn(LAYER_TINTS, layer?.source ?? "") && LAYER_KINDS.has(layer?.kind)
      ? LAYER_TINTS[layer.source]
      : "other";
  }

  function layerLabel(layer) {
    return layerTint(layer) === "other"
      ? `${layer.name}（其他）`
      : layer.name;
  }

  // The committed traits keyed by trait key (empty when unavailable).
  const traitsByKey = computed(
    () => new Map(traits.value.map((row) => [row.key, row]))
  );

  // A gauge row's chips decompose its maximum, whose decomposed value IS the
  // trait payload's `max` — so the layers attach ONLY while both panels agree
  // on that maximum (and the row is a gauge at all: a null trait max has
  // nothing to decompose). Cross-payload disagreement (a stale pair) renders
  // the existing status text with no breakdown element.
  function gaugeLayers(key) {
    const trait = traitsByKey.value.get(key);
    const maximum = resources.value?.[key]?.maximum;
    if (!trait || trait.max === null || maximum === null || maximum === undefined) {
      return [];
    }
    if (trait.max !== maximum || !Array.isArray(trait.layers)) {
      return [];
    }
    return trait.layers;
  }

  // The three gauge rows (hp/mp/sp). A missing gauge or non-numeric fields
  // yield a null ratio (no value is invented); a non-positive maximum yields 0.
  const VITALS = [
    { key: "hp", label: "生命" },
    { key: "mp", label: "魔力" },
    { key: "sp", label: "耐力" },
  ];

  function gaugeRatioPct(gauge) {
    return gaugeRatio(gauge);
  }

  // The full condition roster: every committed condition, each with its
  // severity glyph + severity label, its label, its remaining duration (only
  // when the payload supplies remaining_seconds, verbatim — never decremented
  // between revisions) and every derived modifier value.
  const conditions = computed(() => (Array.isArray(props.status?.conditions) ? props.status.conditions : []));

  return {
    SEVERITY_GLYPHS,
    SEVERITY_LABELS,
    resources,
    formatLayerAmount,
    layerTint,
    layerLabel,
    gaugeLayers,
    VITALS,
    gaugeRatioPct,
    conditions,
  };
}
