// Fractions of the standing-portrait anchor; front first, rear last.
export const COMPANION_LINEUP_MAX = 5;
// Figures share the controlled character's full size and ground line.
// Dialogue compresses only horizontal overlap to leave the choices clear.
const EXPOSURE = [0, 0, 0.42, 0.3, 0.24, 0.22];
export function companionSlots(count, maximumSpan = Infinity) {
  const length = Math.min(Math.max(Math.floor(count), 0), COMPANION_LINEUP_MAX);
  const exposed = length > 1 ? Math.min(EXPOSURE[length], Math.max(0, (maximumSpan - 1) / (length - 1))) : 0;
  return Array.from({ length }, (_, index) => ({
    scale: 1, x: index ? -index * exposed : 0, lift: 0, z: length - index,
  }));
}
export function companionLineupSpan(count, maximumSpan = Infinity) {
  const slots = companionSlots(count, maximumSpan);
  const last = slots.at(-1);
  return last ? last.scale - last.x : 0;
}

// The figures `CompanionLineup` actually displays: the slot list bounded by its
// own maximum. The shell's actor-right membership join reads this same list, so
// a person counts as represented exactly when a figure is drawn for them
// (reuse-lineup-person-focus D1) — never from raw `party.slots`, a display name,
// a portrait key or art availability.
export function displayedLineup(slots) {
  return (Array.isArray(slots) ? slots : []).slice(0, COMPANION_LINEUP_MAX);
}

// The rendered figure for one wire identity, or null. `String(identity)` is the
// existing wire-identity convention — party rows carry safe integers and
// `status.actor.identity` is a bounded string — and it is applied only inside
// this join: the matched slot keeps its own native identity for the companion
// speaking signal. A null/undefined identity joins nothing, and a null portrait
// still matches (membership is identity-only).
export function lineupSlotByIdentity(slots, identity) {
  if (identity === null || identity === undefined) {
    return null;
  }
  const key = String(identity);
  return displayedLineup(slots).find((slot) => String(slot.identity) === key) || null;
}

// One joined figure position: the committed reference's canonical descriptor,
// the committed panel it is judged against, and whether that panel admitted a
// reference at all (so a deliberately unadmitted figure is expected absence,
// never a local failure marker). No client-built art key.
function position(portraitFor, artPanel, portraitRef) {
  return {
    artwork: portraitFor(artPanel, portraitRef),
    panel: artPanel,
    hasReference: portraitRef !== null && portraitRef !== undefined,
  };
}

// Slots retain positions across possession; only the front and possessed
// companion's original slot exchange portraits. No client-built art key.
export function companionFigures({ player, companions, actorIdentity, possessing, controlledName = "", artPanel, portraitFor }) {
  const rows = Array.isArray(companions) ? companions.slice(0, 4) : [];
  // status v2 has a bounded string identity; party v2 has safe integers.
  const controlledIndex = possessing ? rows.findIndex((row) => String(row.identity) === actorIdentity) : -1;
  const figure = (row) => ({
    identity: row.identity, ...position(portraitFor, artPanel, row.portrait_ref),
    displayName: row.display_name, isControlled: false,
  });
  const back = rows.map((row, index) => index === controlledIndex ? { ...player, isControlled: false } : figure(row));
  const front = controlledIndex >= 0 ? figure(rows[controlledIndex])
    : possessing
      ? { identity: actorIdentity, artwork: null, panel: artPanel, hasReference: false, displayName: controlledName }
      : player;
  return [{ ...front, isControlled: true }, ...back];
}
