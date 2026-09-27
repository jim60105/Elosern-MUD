// The foe line-up's pure geometry and selection (OpenSpec change
// webclient-combat-foes-on-stage, design D1/D2; the AVG stage design §10.2).
//
// The line-up stands at most three foes in `actor-right`, as a depth-staged
// row that grows leftward from the anchor's right edge: the first foe in
// presenter order stands in front, nearest the edge; each later foe stands
// behind the one before it, further toward the stage centre, and smaller.
// Every measure here is a fraction of the portrait anchor (its height for a
// slot's height, its width for a slot's horizontal offset), so the row keeps
// its proportions at every viewport. Pure: no Vue import.

export const FOE_LINEUP_MAX = 3;

// The height of each shown foe, front to back, as a fraction of the portrait
// anchor's height, per shown count. The front foe gives up a little height as
// the group grows so the row still ends right of the stage centre, and each
// foe behind is smaller than the one before it (depth).
export const FOE_SCALES = Object.freeze({
  1: Object.freeze([1]),
  2: Object.freeze([0.9, 0.78]),
  3: Object.freeze([0.8, 0.7, 0.61]),
});

// The part of a back foe's width that shows left of the foe in front of it.
export const FOE_EXPOSED = 0.46;

// How much higher each foe further back stands, as a fraction of the anchor's
// height: the stage floor recedes, so a foe behind another stands a little
// up-stage instead of merely looking smaller.
export const FOE_LIFT = 0.035;

// The committed combat participants that stand on the stage: the opposing
// side's active members, in presenter order (the participant frame lists
// everyone else).
export function activeFoes(participants) {
  if (!Array.isArray(participants)) {
    return [];
  }
  return participants.filter((p) => p && p.team === "foes" && p.state === "active");
}

function scalesFor(count) {
  return FOE_SCALES[Math.min(Math.max(count, 0), FOE_LINEUP_MAX)] || [];
}

// One entry per shown slot, front to back: `scale` (height fraction), `right`
// (the slot's right edge measured from the line-up's right edge, as a
// fraction of the anchor's width; a slot is `scale` anchor-widths wide),
// `lift` (how far its feet stand above the band's edge, as a fraction of the
// anchor's height), and `z` (the front foe paints above the ones behind it).
export function foeSlots(count) {
  const scales = scalesFor(count);
  const slots = [];
  let right = 0;
  scales.forEach((scale, index) => {
    if (index > 0) {
      right += scales[index - 1] - (1 - FOE_EXPOSED) * scale;
    }
    slots.push({ index, scale, right, lift: index * FOE_LIFT, z: scales.length - index });
  });
  return slots;
}

// How far the row reaches left of the line-up's right edge, in anchor widths
// (0 when nobody stands on the stage).
export function foeLineupSpan(count) {
  const slots = foeSlots(count);
  const last = slots[slots.length - 1];
  return last ? last.right + last.scale : 0;
}

// The decorative gauge's fill, in percent of the track (0..100), from the
// committed hit points; null when the participant carries no usable numbers.
export function foeHpPercent(participant) {
  const current = participant?.hp_current;
  const maximum = participant?.hp_maximum;
  if (typeof current !== "number" || typeof maximum !== "number") {
    return null;
  }
  if (maximum <= 0) {
    return 0;
  }
  return Math.min(100, Math.max(0, (current / maximum) * 100));
}
