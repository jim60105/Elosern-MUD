// party-status-model (webclient-party-status-tab, design §6.3): the pure
// projections the party window's 狀態 tab reads from the committed
// `character` v9 panel. Nothing here computes a rule: the trait totals, the
// breakdown layers, the condition rows and the disguise are the server's;
// this module only orders, labels and formats them for display.
import { conditionModifiers } from "../lib/condition_label.js";

// The 屬性 rows are the four static traits (a fail-closed allowlist: a new
// server trait key renders nowhere until reviewed in). The gauges (hp/mp/sp)
// render as gauges from the `party` row and the guild merit beside the gem.
export const STATUS_TRAIT_KEYS = Object.freeze(["atk_phys", "agility", "defense", "magic_power"]);

export function statusTraits(character) {
  const rows = Array.isArray(character?.traits) ? character.traits : [];
  const byKey = new Map(rows.map((row) => [row.key, row]));
  return STATUS_TRAIT_KEYS.map((key) => byKey.get(key)).filter(Boolean);
}

export function statusConditions(character) {
  return Array.isArray(character?.conditions) ? character.conditions : [];
}

function layersOf(row) {
  return Array.isArray(row?.layers) ? row.layers : [];
}

// The trait selected when the tab opens: the requested key when present,
// else the first trait with layers, else the first trait, else the first
// condition, else nothing.
export function defaultSelection(traits, conditions, wanted = null) {
  if (wanted && traits.some((row) => row.key === wanted)) return { type: "trait", key: wanted };
  const layered = traits.find((row) => layersOf(row).length > 0);
  if (layered) return { type: "trait", key: layered.key };
  if (traits.length) return { type: "trait", key: traits[0].key };
  if (conditions.length) return { type: "condition", key: conditions[0].code };
  return null;
}

// Whether a selection still names a committed row (conditions by their
// local key, see conditionKeys).
export function selectionExists(selection, traits, conditions) {
  if (!selection) return false;
  if (selection.type === "trait") return traits.some((row) => row.key === selection.key);
  return conditions.some((row) => row.code === selection.key);
}

// The condition rows with a local key each: the code, suffixed `#n` from
// the second occurrence of the same code, so two rows never share a key.
export function conditionKeys(conditions) {
  const seen = new Map();
  return (Array.isArray(conditions) ? conditions : []).map((condition) => {
    const count = seen.get(condition.code) ?? 0;
    seen.set(condition.code, count + 1);
    return { code: count ? `${condition.code}#${count + 1}` : condition.code, condition };
  });
}

const MINUS = "−";

// Strips binary float noise from a displayed difference of two payload
// numbers (a fractional grant such as 2.5 stays exact).
function tidy(value) {
  return Math.round(value * 100) / 100;
}

// up | down | flat: the effective total against the stored base.
export function traitTrend(row) {
  const base = Number(row?.base);
  const effective = Number(row?.effective);
  if (!Number.isFinite(base) || !Number.isFinite(effective)) return "flat";
  if (effective > base) return "up";
  if (effective < base) return "down";
  return "flat";
}

// The signed difference the row shows beside the effective total (empty when
// the totals agree): `+9`, `−2`.
export function signedDelta(row) {
  const trend = traitTrend(row);
  if (trend === "flat") return "";
  const diff = tidy(Math.abs(Number(row.effective) - Number(row.base)));
  return `${trend === "up" ? "+" : MINUS}${diff}`;
}

export const TREND_GLYPHS = Object.freeze({ up: "▲", down: "▼", flat: "" });

// One layer's amount formatted only by its `kind` (the raw amount is
// re-signed for display, never recomputed): flat `+4` / `−2`, pct `+15%`,
// mult `×1.5` (a negative factor keeps its sign); U+2212 minus throughout.
export function formatLayerAmount(kind, amount) {
  const n = Number(amount);
  const magnitude = String(Math.abs(n));
  if (kind === "mult") return `×${n < 0 ? MINUS : ""}${magnitude}`;
  const sign = n < 0 ? MINUS : "+";
  return kind === "pct" ? `${sign}${magnitude}%` : `${sign}${magnitude}`;
}

// Whether a layer raises (up) or lowers (down) the total it decomposes: a
// multiplier above 1 raises, below 1 lowers; every other kind by its sign.
export function layerTrend(layer) {
  const n = Number(layer?.amount);
  if (!Number.isFinite(n)) return "flat";
  if (layer?.kind === "mult") return n > 1 ? "up" : n < 1 ? "down" : "flat";
  return n > 0 ? "up" : n < 0 ? "down" : "flat";
}

const LAYER_SOURCES = Object.freeze({
  equipment: Object.freeze({ tone: "equipment", label: "裝備", glyph: "armor" }),
  skill: Object.freeze({ tone: "skill", label: "技能", glyph: "skills" }),
  condition: Object.freeze({ tone: "condition", label: "狀態", glyph: "buff" }),
});
const OTHER_SOURCE = Object.freeze({ tone: "other", label: "其他", glyph: "status" });

export const LAYER_KIND_LABELS = Object.freeze({ flat: "固定值", pct: "百分比", mult: "倍率" });

// The source presentation of one layer. An unknown source OR an unknown
// kind is the neutral 其他 (a direct-render defense; the wire validators
// reject unknown enums), so an unrecognised rule is never shown as a trusted
// equipment, skill or condition layer.
export function layerSource(layer) {
  if (!Object.hasOwn(LAYER_SOURCES, layer?.source ?? "") || !Object.hasOwn(LAYER_KIND_LABELS, layer?.kind ?? "")) {
    return OTHER_SOURCE;
  }
  return LAYER_SOURCES[layer.source];
}

export function layerKindLabel(layer) {
  return Object.hasOwn(LAYER_KIND_LABELS, layer?.kind ?? "") ? LAYER_KIND_LABELS[layer.kind] : "其他";
}

// The five severities, each with its own glyph shape (the same set as the
// HUD's condition chips) and a word, so no severity differs by colour alone.
export const SEVERITIES = Object.freeze({
  beneficial: Object.freeze({ glyph: "▲", word: "增益" }),
  informational: Object.freeze({ glyph: "◆", word: "資訊" }),
  warning: Object.freeze({ glyph: "▽", word: "警示" }),
  harmful: Object.freeze({ glyph: "▼", word: "減益" }),
  critical: Object.freeze({ glyph: "✕", word: "致命" }),
});
const UNKNOWN_SEVERITY = Object.freeze({ glyph: "◆", word: "狀態" });

export function severityOf(condition) {
  return Object.hasOwn(SEVERITIES, condition?.severity ?? "") ? SEVERITIES[condition.severity] : UNKNOWN_SEVERITY;
}

export const INDEFINITE_TEXT = "無時限";

// A committed `remaining_seconds` as exact hour/minute/second parts
// (`2 小時 5 分`, `40 分`, `30 秒`); nothing is rounded away. Null is an
// indefinite condition; a non-number renders nothing.
export function formatRemaining(seconds) {
  if (seconds === null) return INDEFINITE_TEXT;
  if (!Number.isSafeInteger(seconds) || seconds < 0) return "";
  if (seconds === 0) return "0 秒";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  const parts = [];
  if (hours) parts.push(`${hours} 小時`);
  if (minutes) parts.push(`${minutes} 分`);
  if (rest) parts.push(`${rest} 秒`);
  return parts.join(" ");
}

export const NO_MODIFIER_TEXT = "無";

// Every derived modifier pair in payload order (the shared label rule),
// joined for the row's one-line summary.
export function modifierSummary(condition) {
  return conditionModifiers(condition).map((modifier) => modifier.text).join("、");
}

// The active disguise, or null. Only an active disguise renders; its
// displayed values are labelled as displayed and never replace a true row.
export function activeDisguise(character) {
  const disguise = character?.disguise;
  return disguise && disguise.active === true ? disguise : null;
}

export function guildStanding(character) {
  const guild = character?.guild;
  const rank = typeof guild?.rank === "string" ? guild.rank.trim() : "";
  if (!rank) return null;
  return { rank, merit: Number.isSafeInteger(guild.merit) ? guild.merit : 0 };
}

export function fullTitle(character) {
  const title = character?.full_title;
  return typeof title === "string" ? title.trim() : "";
}
