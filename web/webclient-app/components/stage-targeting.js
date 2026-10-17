// The stage target step's stage-side joins (webclient-combat-stage-target-
// picking D1/D4): the formation's stage order the store reads, the line-ups'
// `targeting` sets, and the plates layer's arrow markers. Pure functions over
// the formation the stage draws and the store's `view.stageTarget`.

// The drawn identities in stage order: every figure by the horizontal centre
// of its formation box, left to right, the front rank first on a tie (then
// the identity, so the order is total). `party` and `foes` are the drawn
// identities in the formation's own figure order. Null without a formation.
export function formationOrderFor(formation, party, foes) {
  if (!formation) {
    return null;
  }
  const entries = [];
  const add = (figures, identities) => {
    (figures || []).forEach((figure, index) => {
      const identity = identities[index];
      if (identity === null || identity === undefined) return;
      entries.push({ id: String(identity), centre: figure.box.left + figure.box.width / 2, rank: figure.rank ?? 0 });
    });
  };
  add(formation.party?.figures, party);
  add(formation.foes?.figures, foes);
  entries.sort((a, b) => a.centre - b.centre || a.rank - b.rank || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  return entries.map((entry) => entry.id);
}

// The step as the stage draws it: a SELF position stands on the commanded
// actor's figure, which the store's model already names
// (webclient-party-command-selection: a companion SELF stands on the
// companion, never the controlled portrait). The line-up's controlled slot is
// only a fallback for a model that carries no identity.
export function onStage(step, fallbackSelfId) {
  if (!step || step.form !== "self") {
    return step;
  }
  const selfPosition = step.positions.find((p) => p.kind === "self");
  if (!selfPosition) {
    return step;
  }
  const current = selfPosition.identities[0];
  if (current !== null && current !== undefined) {
    return step;
  }
  if (fallbackSelfId === null || fallbackSelfId === undefined) {
    return step;
  }
  const id = String(fallbackSelfId);
  const positions = step.positions.map((p) => (p.kind === "self" ? { ...p, identities: [id] } : p));
  const focused = positions.find((p) => p.key === step.focusKey) || null;
  return {
    ...step,
    positions,
    focused,
    lit: focused ? [id] : [],
    selectable: [id],
    digits: Object.fromEntries(positions.filter((p) => p.digit !== null).map((p) => [id, p.digit])),
  };
}

// The line-ups' `targeting` prop: null outside the step, else Sets of
// String(identity).
export function targetingFor(step) {
  if (!step) {
    return null;
  }
  return Object.freeze({
    lit: new Set(step.lit.map(String)),
    selectable: new Set(step.selectable.map(String)),
    selected: new Set(step.selectedIds.map(String)),
  });
}

// The position key a figure's identity stands for: its member item, or the
// SELF confirm on the commanded actor's figure.
export function positionKeyFor(step, identity) {
  if (!step || identity === null || identity === undefined) {
    return null;
  }
  const id = String(identity);
  const position = step.positions.find(
    (p) => (p.kind === "member" || p.kind === "self") && p.identities[0] === id,
  );
  return position ? position.key : null;
}

// One arrow marker per selectable drawn figure, at its formation marker slot
// (directly above its plate): `{ key, identity, positionKey, box, state,
// digit, selected }`, where `state` is "focus" for a lit figure and
// "selectable" otherwise.
export function markersFor(step, formation, party, foes) {
  if (!step || !formation) {
    return [];
  }
  const lit = new Set(step.lit.map(String));
  const selected = new Set(step.selectedIds.map(String));
  const out = [];
  const add = (figures, identities, side) => {
    (figures || []).forEach((figure, index) => {
      const identity = identities[index];
      if (identity === null || identity === undefined) return;
      const id = String(identity);
      const positionKey = positionKeyFor(step, id);
      if (!positionKey || !figure.marker) return;
      out.push({
        key: `${side}:${id}`,
        identity: id,
        positionKey,
        box: figure.marker,
        state: lit.has(id) ? "focus" : "selectable",
        digit: step.digits[id] ?? null,
        selected: selected.has(id),
      });
    });
  };
  add(formation.party?.figures, party, "party");
  add(formation.foes?.figures, foes, "foes");
  return out;
}
