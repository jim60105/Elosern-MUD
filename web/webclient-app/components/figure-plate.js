// The glance plates' pure helpers (OpenSpec change webclient-combat-formation,
// design D4): the hit-point fraction a plate's stroke fills, the plate's
// accessible name, and which drawn names repeat (so only those plates show
// their session token). Pure: no Vue import, no DOM.

const SIDE_LABEL = Object.freeze({ party: "我方", foes: "敵方" });

// The stroke's fill, in percent of the track (0..100), or null when the
// participant carries no usable numbers. A non-positive maximum is empty.
export function plateHpPercent(current, maximum) {
  if (typeof current !== "number" || typeof maximum !== "number" || !Number.isFinite(current) || !Number.isFinite(maximum)) {
    return null;
  }
  if (maximum <= 0) {
    return 0;
  }
  return Math.min(100, Math.max(0, (current / maximum) * 100));
}

// The value a plate shows: the displayed playback value while a round plays
// (keyed by the participant's portrait reference, as the beats name it),
// else the committed value. A null reference or an unmapped one keeps the
// committed value.
export function plateHpCurrent(participant, displayHp) {
  const ref = participant?.portrait_ref;
  const displayed = ref === null || ref === undefined ? undefined : displayHp?.[ref];
  return typeof displayed === "number" ? displayed : participant?.hp_current;
}

// "<name> <token>，<我方|敵方>，生命 <cur>/<max>": the session token is always
// part of the accessible name, even where the plate does not show it.
export function plateLabel({ name, token, side, current, maximum }) {
  const who = [name, token].filter((part) => typeof part === "string" && part.length > 0).join(" ");
  const hp = typeof current === "number" && typeof maximum === "number" ? `${current}/${maximum}` : "--";
  return `${who}，${SIDE_LABEL[side] ?? SIDE_LABEL.foes}，生命 ${hp}`;
}

// The names that two or more drawn participants share: a plate shows its
// session token only while its name is one of these.
export function repeatedNames(names) {
  const seen = new Map();
  for (const name of names) {
    if (typeof name !== "string" || name.length === 0) continue;
    seen.set(name, (seen.get(name) || 0) + 1);
  }
  return new Set([...seen].filter(([, count]) => count > 1).map(([name]) => name));
}
