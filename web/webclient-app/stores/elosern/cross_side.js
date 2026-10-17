// The cross-side cast predicate (webclient-combat-cross-side-confirm, design
// D1): pure and DOM-free. A submission is cross-side when the skill's static
// `hostile` fact meets a `party` participant (the actor included) or its
// `beneficial` fact meets a `foes` participant. No amount, formula or
// prediction takes part; the server still validates every sent cast.

// The question's side wording (the user confirmed these four).
export const SIDE_WORDS = Object.freeze({
  ally: "友方",
  self: "自己",
  foe: "敵方",
  both: "友方與敵方",
});

const SHORTHAND_TEAMS = Object.freeze({
  "all-enemies": "foes",
  "all-allies": "party",
});

function idKey(identity) {
  return identity === null || identity === undefined ? null : String(identity);
}

// The exact question for one outcome and one skill label.
export function crossSideQuestion(sides, label) {
  return `確定要對${SIDE_WORDS[sides]}使用〈${label || ""}〉？`;
}

// The static facts of one skill, read from the committed combat panel's raw
// descriptor (category → groups → skills). A missing descriptor or field
// counts as false.
export function skillFacts(panel, skillKey) {
  const skill = committedSkill(panel, skillKey);
  return skill
    ? { hostile: skill.hostile === true, beneficial: skill.beneficial === true, label: skill.label || "" }
    : { hostile: false, beneficial: false, label: "" };
}

// The committed combat panel's raw descriptor for one skill key (the first
// match, category → groups → skills), or null.
export function committedSkill(panel, skillKey) {
  for (const category of (panel && panel.skills) || []) {
    for (const group of (category && category.groups) || []) {
      for (const skill of (group && group.skills) || []) {
        if (skill && skill.key === skillKey) {
          return skill;
        }
      }
    }
  }
  return null;
}

// The identities a submission reaches (spec "The target set of each form"):
// - `single` → the payload's one target;
// - `self` → the actor (unknown actor → one unresolvable identity);
// - `area` explicit → the payload's selection;
// - `area` shorthand → every candidate of that side (`all` → every candidate);
// - `none` → nothing.
// `candidates` are the skill's server candidates and `participants` the
// committed participant rows.
export function targetSetFor({ form, payload, candidates, participants, actorIdentity } = {}) {
  const body = payload || {};
  if (form === "self") {
    return [idKey(actorIdentity)];
  }
  if (form === "single") {
    return Array.isArray(body.target_ids) ? body.target_ids.map(idKey) : [];
  }
  if (form === "area") {
    if (typeof body.target_shorthand === "string") {
      const list = Array.isArray(candidates) ? candidates : [];
      if (body.target_shorthand === "all") {
        return list.map(idKey);
      }
      const team = SHORTHAND_TEAMS[body.target_shorthand];
      const byId = new Map((participants || []).filter(Boolean).map((p) => [idKey(p.identity), p]));
      return list.map(idKey).filter((id) => {
        const row = byId.get(id);
        return !!team && !!row && row.team === team;
      });
    }
    return Array.isArray(body.target_ids) ? body.target_ids.map(idKey) : [];
  }
  return [];
}

// The predicate: null (send at once) or `{ sides }`, where `sides` is
// "ally" | "self" | "foe" | "both". An identity no committed row carries
// fails closed: with either fact true the question names both sides.
export function crossSide({ hostile, beneficial } = {}, targets, participants, actorIdentity) {
  if (!hostile && !beneficial) {
    return null;
  }
  const ids = Array.isArray(targets) ? targets : [];
  if (ids.length === 0) {
    return null;
  }
  const byId = new Map((participants || []).filter(Boolean).map((p) => [idKey(p.identity), p]));
  const actor = idKey(actorIdentity);
  let unresolved = false;
  const party = [];
  let foes = 0;
  for (const id of ids) {
    const row = id === null ? null : byId.get(id);
    if (!row || (row.team !== "party" && row.team !== "foes")) {
      unresolved = true;
    } else if (row.team === "party") {
      party.push(id);
    } else {
      foes += 1;
    }
  }
  if (unresolved) {
    return { sides: "both" };
  }
  const allyHit = !!hostile && party.length > 0;
  const foeHit = !!beneficial && foes > 0;
  if (allyHit && foeHit) {
    return { sides: "both" };
  }
  if (allyHit) {
    return { sides: actor !== null && party.every((id) => id === actor) ? "self" : "ally" };
  }
  if (foeHit) {
    return { sides: "foe" };
  }
  return null;
}
