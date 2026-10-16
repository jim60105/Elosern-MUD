// The foe line-up's selection (OpenSpec changes webclient-combat-foes-on-stage,
// webclient-combat-formation and webclient-combat-defeated-foes). Every foe
// that has not fled stands on the stage, in
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

// The committed combat participants that stand on the stage
// (webclient-combat-defeated-foes design D5): the opposing side's members that
// have not fled, in presenter order. A knocked-out or defeated foe keeps its
// slot in its defeated look, so a defeat never re-forms the line; a fled foe
// leaves it.
export function drawnFoes(participants) {
  if (!Array.isArray(participants)) {
    return [];
  }
  return participants.filter((p) => p && p.team === "foes" && p.state !== "fled");
}

// The fallen look a participant's state takes on the stage (design D1): a
// knocked-out or defeated foe is "defeated", a knocked-out (or defeated)
// party member is "down", and every other state stands (null).
export const FALLEN_STATES = Object.freeze(["knocked_out", "defeated"]);
export function fallenLook(team, state) {
  if (!FALLEN_STATES.includes(state)) {
    return null;
  }
  return team === "foes" ? "defeated" : "down";
}
