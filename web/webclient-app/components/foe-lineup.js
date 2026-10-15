// The foe line-up's selection (OpenSpec changes webclient-combat-foes-on-stage
// and webclient-combat-formation). Every active foe stands on the stage, in
// presenter order, at the box the combat formation engine
// (combat-formation.js) gives it; the depth table and the three-foe cap of the
// first line-up are retired. Pure: no Vue import.

// The most foes the stage stands: a session holds at most 16 participants and
// at least the player, so 15 — and with a party of `n` figures, `16 - n`.
export const FOE_STAGE_MAX = 15;
export const SESSION_PARTICIPANT_MAX = 16;

// How many foes stand beside a drawn party of `partyCount` figures.
export function foeStageLimit(partyCount) {
  const party = Math.max(1, Math.floor(Number(partyCount) || 0));
  return Math.max(0, Math.min(FOE_STAGE_MAX, SESSION_PARTICIPANT_MAX - party));
}

// The committed combat participants that stand on the stage: the opposing
// side's active members, in presenter order.
export function activeFoes(participants) {
  if (!Array.isArray(participants)) {
    return [];
  }
  return participants.filter((p) => p && p.team === "foes" && p.state === "active");
}
