// Prototype of the pure exit-compass model (spec §3.1). Reference only: the
// shipped module will read the committed exploration/local-map payloads, but
// the rules here are the ones the spec fixes.

export const SNAP_TOLERANCE = 30; // degrees either side of the aim
export const DEAD_ZONE = 0.2; // fraction of the pad radius
export const HOLD_MS = 400; // press length that starts continuous movement
export const STEP_DWELL_MS = 350; // minimum dwell in each room while continuing

const WORD_ANGLES = Object.assign(Object.create(null), {
  north: 0, n: 0, 北: 0,
  northeast: 45, ne: 45, 東北: 45,
  east: 90, e: 90, 東: 90,
  southeast: 135, se: 135, 東南: 135,
  south: 180, s: 180, 南: 180,
  southwest: 225, sw: 225, 西南: 225,
  west: 270, w: 270, 西: 270,
  northwest: 315, nw: 315, 西北: 315,
});
const VERTICAL = Object.assign(Object.create(null), { up: "up", 上: "up", down: "down", 下: "down" });
const GEO_LAYERS = new Set(["grid", "wilderness"]);
const OCTANT_NAMES = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"];

export function normalizeAngle(deg) {
  return ((deg % 360) + 360) % 360;
}

export function angleDelta(a, b) {
  const d = Math.abs(normalizeAngle(a) - normalizeAngle(b));
  return d > 180 ? 360 - d : d;
}

export function bearing(from, to) {
  return normalizeAngle((Math.atan2(to.x - from.x, to.y - from.y) * 180) / Math.PI);
}

export function octantName(angle) {
  return OCTANT_NAMES[Math.floor(normalizeAngle(angle) / 45 + 0.5) % 8];
}

export function octantGlyph(angle) {
  return ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"][Math.floor(normalizeAngle(angle) / 45 + 0.5) % 8];
}

// Angle source, in order (spec §3.1):
//  1. same geographic layer, destination on the map → atan2 bearing;
//  2. a canonical direction word → its fixed angle;
//  3. otherwise a portal (up/down are portals with fixed slots).
export function resolveTargets(scene, sceneById) {
  const angled = [];
  const portals = [];
  for (const exit of scene.exits) {
    const dest = sceneById(exit.dest);
    const key = String(exit.label).trim().toLowerCase();
    const base = {
      key: exit.ref,
      label: exit.label,
      dest: exit.dest,
      destName: dest ? dest.name : exit.label,
      enabled: exit.enabled !== false,
      reason: exit.reason || null,
    };
    if (
      GEO_LAYERS.has(scene.layer) &&
      dest &&
      dest.layer === scene.layer &&
      Number.isInteger(dest.x) &&
      !(dest.x === scene.x && dest.y === scene.y)
    ) {
      angled.push({ ...base, kind: "angled", angle: bearing(scene, dest), source: "map" });
    } else if (key in WORD_ANGLES) {
      angled.push({ ...base, kind: "angled", angle: WORD_ANGLES[key], source: "word" });
    } else {
      portals.push({ ...base, kind: "portal", vertical: VERTICAL[key] || null });
    }
  }
  angled.sort((a, b) => a.angle - b.angle);
  assignPortalSlots(portals);
  return { angled, portals, cycle: [...angled, ...portals] };
}

// Up is pinned to 0°, down to 180°; the rest spread evenly over a 12-slot
// (30°) ring, skipping the pinned slots. More than ten portals fall to a
// 24-slot ring.
export function assignPortalSlots(portals) {
  const others = portals.filter((p) => !p.vertical);
  const step = others.length > 10 ? 15 : 30;
  const taken = new Set();
  for (const p of portals) {
    if (p.vertical === "up") {
      p.slot = 0;
      taken.add(0);
    } else if (p.vertical === "down") {
      p.slot = 180;
      taken.add(180);
    }
  }
  // Spread the rest evenly round the ring, each taking the free slot
  // nearest its ideal position (clockwise first on a tie).
  const count = 360 / step;
  others.forEach((p, i) => {
    const ideal = Math.round(((i + 0.5) * count) / others.length) % count;
    for (let off = 0; off < count; off += 1) {
      const cw = ((ideal + off) % count) * step;
      const ccw = ((ideal - off + count) % count) * step;
      const free = !taken.has(cw) ? cw : !taken.has(ccw) ? ccw : null;
      if (free !== null) {
        p.slot = free;
        taken.add(free);
        break;
      }
    }
  });
  portals.sort((a, b) => a.slot - b.slot);
}

// Snap an aim angle to the nearest angled exit within the tolerance. Ties
// go to the lower clockwise angle so the result is deterministic.
export function snapAngled(angled, aim, tolerance = SNAP_TOLERANCE) {
  let best = null;
  let bestDelta = Infinity;
  for (const t of angled) {
    const d = angleDelta(t.angle, aim);
    if (d <= tolerance && d < bestDelta) {
      best = t;
      bestDelta = d;
    }
  }
  return best;
}

export function snapPortal(portals, aim) {
  let best = null;
  let bestDelta = Infinity;
  for (const p of portals) {
    const d = angleDelta(p.slot, aim);
    if (d < bestDelta) {
      best = p;
      bestDelta = d;
    }
  }
  return best;
}

// The pointer → aim resolution. `r` is the distance from the centre as a
// fraction of the inner pad radius; `ringStart` is where the portal track
// begins (same unit).
export function aimFromPointer(targets, r, angle, ringStart) {
  if (r < DEAD_ZONE) {
    return { angle: null, target: null, zone: "dead" };
  }
  if (r >= ringStart && targets.portals.length > 0) {
    return { angle, target: snapPortal(targets.portals, angle), zone: "ring" };
  }
  return { angle, target: snapAngled(targets.angled, angle), zone: "pad" };
}

// Arrow keys held → an eight-way aim angle, or null when they cancel out.
export function aimFromKeys(keys) {
  const dx = (keys.has("ArrowRight") ? 1 : 0) - (keys.has("ArrowLeft") ? 1 : 0);
  const dy = (keys.has("ArrowUp") ? 1 : 0) - (keys.has("ArrowDown") ? 1 : 0);
  if (dx === 0 && dy === 0) {
    return null;
  }
  return normalizeAngle((Math.atan2(dx, dy) * 180) / Math.PI);
}

// The continuous-movement step decision on arrival (spec §3.1): re-snap the
// held aim in the new room; stop when nothing is in tolerance or the exit
// is disabled. Portals never chain.
export function nextStep(targets, aim) {
  if (aim === null) {
    return { stop: "no-aim" };
  }
  const t = snapAngled(targets.angled, aim);
  if (!t) {
    return { stop: "no-exit" };
  }
  if (!t.enabled) {
    return { stop: "disabled", target: t };
  }
  return { target: t };
}
