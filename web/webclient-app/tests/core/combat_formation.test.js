// webclient-combat-formation-engine (design D1-D5): the combat formation is
// one pure function of the stage geometry and the two counts. Every check
// below is re-derived from the spec's rules (zones, gap, headroom, plate
// spacing, the vitals dock), never by calling the engine's internals; the
// reference viewports' inputs are written out from tokens.css by hand.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  COMPACT_SLOT,
  FULL_SLOT,
  SCALE_FLOOR,
  SCALE_LADDER,
  combatFormation,
  formationInputFromStage,
} from "../../components/combat-formation.js";

const APP_ROOT = join(process.cwd(), "web/webclient-app");

// The chrome factor per supported viewport: clamp(1, min(H/790, W/1451), 1.4)
// rounded to 4 dp (lib/ui_scale.js), written out so the test does not share
// the code it checks.
const VIEWPORTS = Object.freeze({
  "1451x790": { width: 1451, height: 790, S: 1 },
  "1600x900": { width: 1600, height: 900, S: 1.1027 },
  "1920x1080": { width: 1920, height: 1080, S: 1.3232 },
  "2560x1440": { width: 2560, height: 1440, S: 1.4 },
});

// The reference input for one viewport (tokens.css): the top band is the 48px·S
// header; the bottom band is clamp(190px·S, 27.85vh, 400px·S); the portrait
// height is min(62vh, 680px·S, the stage between the bands); the reference
// vitals dock is 25vw × 92px·S standing on the band's top edge (its top is
// bandTop − 92px·S), 16px·S from the left.
function reference(name, partyCount, foeCount) {
  const { width, height, S } = VIEWPORTS[name];
  const header = 48 * S;
  const band = Math.min(Math.max(190 * S, 0.2785 * height), 400 * S);
  const bandTop = height - band;
  return {
    stageWidth: width,
    stageHeight: height,
    uiScale: S,
    bandTop,
    actorHeight: Math.min(0.62 * height, 680 * S, height - header - band),
    topBandBottom: header,
    cardWidth: 264 * S,
    vitalsDock: { left: 16 * S, top: bandTop - 92 * S, width: 0.25 * width, height: 92 * S },
    partyCount,
    foeCount,
  };
}

function cases(name) {
  const out = [];
  for (let party = 1; party <= 5; party += 1) {
    for (let foes = 1; foes <= 16 - party; foes += 1) out.push([party, foes]);
  }
  return out.map(([party, foes]) => ({ name, party, foes, input: reference(name, party, foes) }));
}

const right = (box) => box.left + box.width;
const bottom = (box) => box.top + box.height;
const allFigures = (result) => [...result.party.figures, ...result.foes.figures];
const slotsOf = (figure) => [figure.box, figure.plate, figure.marker];

// Rectangle distance: 0 when they overlap or touch.
function distance(a, b) {
  const dx = Math.max(a.left - right(b), b.left - right(a), 0);
  const dy = Math.max(a.top - bottom(b), b.top - bottom(a), 0);
  return Math.max(dx, dy);
}

function overlaps(a, b) {
  return a.left < right(b) && b.left < right(a) && a.top < bottom(b) && b.top < bottom(a);
}

const TOL = 1e-6;

// Every invariant of design D3 for one case; returns the list of violations so
// a failing matrix names each broken case.
function violations({ input }, result) {
  const S = input.uiScale;
  const C = input.stageWidth / 2;
  const gapLeft = C - 132 * S - 16 * S;
  const gapRight = C + 132 * S + 16 * S;
  const problems = [];
  const fail = (message) => problems.push(message);
  if (!result.fits) fail("fits is false");
  if (!SCALE_LADDER.includes(result.scale) || result.scale < 0.5) fail(`scale ${result.scale} off the ladder`);
  if (result.party.figures.length !== input.partyCount) fail("party count");
  if (result.foes.figures.length !== input.foeCount) fail("foe count");
  const h = result.scale * input.actorHeight;
  for (const figure of allFigures(result)) {
    if (Math.abs(figure.box.height - h) > 0.5) fail(`box height ${figure.box.height} != ${h}`);
    if (Math.abs(figure.box.width - (h * 2) / 3) > 0.5) fail(`box width ${figure.box.width}`);
  }
  for (const figure of result.party.figures) {
    for (const box of slotsOf(figure)) {
      if (right(box) > gapLeft + TOL) fail(`party slot enters the gap at ${right(box)}`);
      if (box.left < 16 * S - TOL) fail(`party slot outside the left gutter at ${box.left}`);
    }
  }
  for (const figure of result.foes.figures) {
    for (const box of slotsOf(figure)) {
      if (box.left < gapRight - TOL) fail(`foe slot enters the gap at ${box.left}`);
      if (right(box) > input.stageWidth - 16 * S + TOL) fail(`foe slot outside the right gutter at ${right(box)}`);
    }
  }
  for (const figure of allFigures(result)) {
    for (const box of slotsOf(figure)) {
      if (box.top < 0 - TOL || bottom(box) > input.stageHeight + TOL) fail("slot outside the stage");
    }
    if (figure.marker.top < input.topBandBottom + 8 * S - TOL) fail(`marker at ${figure.marker.top} under the top band`);
    if (figure.plate.top < input.topBandBottom + 8 * S - TOL) fail("plate under the top band");
    if (figure.marker.height !== 24 * S || bottom(figure.marker) > figure.plate.top + TOL) fail("marker not above plate");
    const dims = figure.plate.form === "compact" ? COMPACT_SLOT : FULL_SLOT;
    if (figure.plate.width !== dims.width * S || figure.plate.height !== dims.height * S) fail("plate size");
    if (bottom(figure.plate) > figure.box.top - 4 * S + TOL) fail("plate not above its figure");
    if (distance(figure.plate, input.vitalsDock) === 0) fail("plate touches the vitals dock");
  }
  for (const side of [result.party, result.foes]) {
    const plates = side.figures.map((figure) => figure.plate);
    for (let a = 0; a < plates.length; a += 1) {
      for (let b = a + 1; b < plates.length; b += 1) {
        if (distance(plates[a], plates[b]) < 2 * S - TOL) fail(`plates ${a} and ${b} closer than 2px·S`);
      }
    }
  }
  const dock = input.vitalsDock;
  for (const figure of result.party.figures) {
    const box = figure.box;
    if (!overlaps(box, dock)) continue;
    const coveredTop = Math.max(box.top, dock.top);
    if (coveredTop < bottom(box) - 0.4 * box.height - TOL) fail("dock covers more than the lowest 40%");
  }
  return problems;
}

// The spec's one-rank test for a side, re-derived for the policy checks: the
// step rule, the plate-line rule, and the marker headroom.
function oneRankFits(input, n, scale, slot) {
  const S = input.uiScale;
  const zone = input.stageWidth / 2 - 132 * S - 16 * S - 16 * S;
  const h = scale * input.actorHeight;
  const w = (h * 2) / 3;
  const step = n > 1 ? Math.min(0.62 * w, (zone - w) / (n - 1)) : 0;
  if (step < 0 || w > zone) return false;
  let lines;
  if (n <= 1 || step >= slot.width * S + 4 * S) lines = 1;
  else if (2 * step >= slot.width * S + 4 * S) lines = 2;
  else return false;
  const markerTop = input.bandTop - h - 4 * S - slot.height * S - (lines - 1) * (slot.height * S + 4 * S) - 24 * S;
  return markerTop >= input.topBandBottom + 8 * S;
}

const code = (result) =>
  `${result.scale.toFixed(2)}${result.foes.form === "compact" ? "C" : "F"}${result.foes.ranks}`;

describe("combat formation: the full matrix", () => {
  for (const name of Object.keys(VIEWPORTS)) {
    it(`fits every party 1-5 × foes 1-(16 − party) case at ${name} with every invariant`, () => {
      const failures = [];
      for (const entry of cases(name)) {
        const result = combatFormation(entry.input);
        const problems = violations(entry, result);
        if (problems.length) failures.push(`p${entry.party} f${entry.foes}: ${problems.join("; ")}`);
      }
      expect(failures).toEqual([]);
    });
  }

  it("keeps the party in one full-slot rank at every supported viewport", () => {
    for (const name of Object.keys(VIEWPORTS)) {
      for (const entry of cases(name)) {
        const result = combatFormation(entry.input);
        expect(result.party.ranks).toBe(1);
        expect(result.party.form).toBe("full");
      }
    }
  });
});

describe("combat formation: the policy", () => {
  it("uses a second rank only where one rank cannot fit at the chosen scale", () => {
    for (const name of Object.keys(VIEWPORTS)) {
      for (const entry of cases(name)) {
        const result = combatFormation(entry.input);
        if (result.foes.ranks !== 2) continue;
        const slot = result.foes.form === "compact" ? COMPACT_SLOT : FULL_SLOT;
        expect(oneRankFits(entry.input, entry.foes, result.scale, slot), `${name} p${entry.party} f${entry.foes}`).toBe(
          false,
        );
      }
    }
  });

  it("prefers all-full slots at a smaller scale over compact slots at a larger one", () => {
    // 15 foes fit with compact slots at 0.55, so 14 foes would too; the
    // full pass still wins at the floor.
    const fourteen = combatFormation(reference("1451x790", 1, 14));
    expect(code(fourteen)).toBe("0.50F2");
    const fifteen = combatFormation(reference("1451x790", 1, 15));
    expect(code(fifteen)).toBe("0.55C2");
    expect(fifteen.foes.figures.every((figure) => figure.plate.form === "compact")).toBe(true);
    expect(fourteen.foes.figures.every((figure) => figure.plate.form === "full")).toBe(true);
  });

  it("uses compact slots only for fifteen foes", () => {
    for (const name of Object.keys(VIEWPORTS)) {
      for (const entry of cases(name)) {
        const result = combatFormation(entry.input);
        const compact = allFigures(result).some((figure) => figure.plate.form === "compact");
        expect(compact, `${name} p${entry.party} f${entry.foes}`).toBe(name !== "2560x1440" && entry.foes === 15);
      }
    }
  });
});

describe("combat formation: the shared scale", () => {
  it("gives every box on both sides the same height and the 2/3 width", () => {
    const result = combatFormation(reference("1451x790", 5, 11));
    const heights = new Set(allFigures(result).map((figure) => figure.box.height));
    expect(heights.size).toBe(1);
    expect([...heights][0]).toBeCloseTo(0.5 * 0.62 * 790, 6);
    for (const figure of allFigures(result)) expect(figure.box.width).toBeCloseTo((figure.box.height * 2) / 3, 6);
  });
});

describe("combat formation: the spec's anchors at 1451x790", () => {
  it("0.84, full, one rank per side for one party figure against one to three foes", () => {
    for (let foes = 1; foes <= 3; foes += 1) {
      const result = combatFormation(reference("1451x790", 1, foes));
      expect(code(result)).toBe("0.84F1");
      expect(result.party.ranks).toBe(1);
      expect(result.party.form).toBe("full");
    }
  });

  it("0.72 with full slots for five party figures against one to six foes", () => {
    for (let foes = 1; foes <= 6; foes += 1) {
      const result = combatFormation(reference("1451x790", 5, foes));
      expect(result.scale).toBe(0.72);
      expect(result.party.form).toBe("full");
      expect(result.foes.form).toBe("full");
    }
  });

  it("0.60 with one foe rank for one to five party figures against seven foes", () => {
    for (let party = 1; party <= 5; party += 1) {
      const result = combatFormation(reference("1451x790", party, 7));
      expect(result.scale).toBe(0.6);
      expect(result.foes.ranks).toBe(1);
    }
  });

  it("0.50 with two foe ranks and full slots for one party figure against eight to fourteen foes", () => {
    for (let foes = 8; foes <= 14; foes += 1) {
      expect(code(combatFormation(reference("1451x790", 1, foes)))).toBe("0.50F2");
    }
  });

  // Amended from the planning prototype's 0.50 (design D4 note): the spec's
  // explicit fit rule admits compact slots at 0.55 here.
  it("0.55 with two foe ranks and compact slots for one party figure against fifteen foes", () => {
    expect(code(combatFormation(reference("1451x790", 1, 15)))).toBe("0.55C2");
  });
});

// The pinned reference table (design D4): any later change that moves a cell
// updates this literal deliberately. Rows are party sizes; each row lists
// foes 1..(16 - party) as scale, foe slot form, foe rank count.
const TABLE = Object.freeze({
  "1451x790": [
    "0.84F1 0.84F1 0.84F1 0.72F1 0.72F1 0.72F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.55C2",
    "0.84F1 0.84F1 0.84F1 0.72F1 0.72F1 0.72F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2",
    "0.84F1 0.84F1 0.84F1 0.72F1 0.72F1 0.72F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2",
    "0.72F1 0.72F1 0.72F1 0.72F1 0.72F1 0.72F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2",
    "0.72F1 0.72F1 0.72F1 0.72F1 0.72F1 0.72F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2",
  ],
  "1600x900": [
    "0.84F1 0.84F1 0.84F1 0.78F1 0.78F1 0.78F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.55C2",
    "0.84F1 0.84F1 0.84F1 0.78F1 0.78F1 0.78F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2",
    "0.84F1 0.84F1 0.84F1 0.78F1 0.78F1 0.78F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2",
    "0.78F1 0.78F1 0.78F1 0.78F1 0.78F1 0.78F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2 0.50F2",
    "0.78F1 0.78F1 0.78F1 0.78F1 0.78F1 0.78F1 0.60F1 0.50F2 0.50F2 0.50F2 0.50F2",
  ],
  "2560x1440": [
    "0.90F1 0.90F1 0.90F1 0.90F1 0.84F1 0.84F1 0.84F1 0.78F1 0.66F1 0.55F2 0.55F2 0.55F2 0.55F2 0.55F2 0.55F2",
    "0.90F1 0.90F1 0.90F1 0.90F1 0.84F1 0.84F1 0.84F1 0.78F1 0.66F1 0.55F2 0.55F2 0.55F2 0.55F2 0.55F2",
    "0.90F1 0.90F1 0.90F1 0.90F1 0.84F1 0.84F1 0.84F1 0.78F1 0.66F1 0.55F2 0.55F2 0.55F2 0.55F2",
    "0.90F1 0.90F1 0.90F1 0.90F1 0.84F1 0.84F1 0.84F1 0.78F1 0.66F1 0.55F2 0.55F2 0.55F2",
    "0.84F1 0.84F1 0.84F1 0.84F1 0.84F1 0.84F1 0.84F1 0.78F1 0.66F1 0.55F2 0.55F2",
  ],
});

describe("combat formation: the pinned table", () => {
  // 1920x1080 shares the 1600x900 table (design D4).
  for (const [name, rows] of [...Object.entries(TABLE), ["1920x1080", TABLE["1600x900"]]]) {
    it(`matches the reference table at ${name}`, () => {
      const actual = rows.map((_, index) => {
        const party = index + 1;
        const cells = [];
        for (let foes = 1; foes <= 16 - party; foes += 1) cells.push(code(combatFormation(reference(name, party, foes))));
        return cells.join(" ");
      });
      expect(actual).toEqual(rows);
    });
  }
});

describe("combat formation: order and ranks", () => {
  it("stands the controlled figure and the first foe at their side's outer edge", () => {
    const result = combatFormation(reference("1451x790", 2, 2));
    const party = result.party.figures;
    expect(party.map((figure) => figure.index)).toEqual([0, 1]);
    expect(party[1].box.left).toBeGreaterThan(party[0].box.left);
    const foes = result.foes.figures;
    expect(foes.map((figure) => figure.index)).toEqual([0, 1]);
    expect(foes[1].box.left).toBeLessThan(foes[0].box.left);
    // The group's outer edge sits at the 6vw home inset when it fits there.
    expect(party[0].box.left).toBeCloseTo(0.06 * 1451, 6);
    expect(right(foes[0].box)).toBeCloseTo(1451 - 0.06 * 1451, 6);
  });

  it("pushes a group that does not fit at the home inset toward the outer gutter, never into the gap", () => {
    // Four foes at 0.72 fill the whole zone: the row runs from the gap's
    // edge to the right gutter.
    const result = combatFormation(reference("1451x790", 1, 4));
    const foes = result.foes.figures;
    expect(result.scale).toBe(0.72);
    expect(right(foes[0].box)).toBeCloseTo(1451 - 16, 6);
    expect(foes.at(-1).box.left).toBeCloseTo(1451 / 2 + 148, 6);
  });

  it("puts the first ceil(n/2) foes in the front rank and lifts the back rank 0.27 × actor-h", () => {
    const input = reference("1451x790", 1, 9);
    const result = combatFormation(input);
    expect(result.foes.ranks).toBe(2);
    expect(result.foes.figures.map((figure) => figure.rank)).toEqual([0, 0, 0, 0, 0, 1, 1, 1, 1]);
    const front = result.foes.figures.filter((figure) => figure.rank === 0);
    const back = result.foes.figures.filter((figure) => figure.rank === 1);
    for (const figure of front) expect(bottom(figure.box)).toBeCloseTo(input.bandTop, 6);
    for (const figure of back) expect(bottom(figure.box)).toBeCloseTo(input.bandTop - 0.27 * input.actorHeight, 6);
    // Half a step toward the centre: each back figure stands between two
    // front ones.
    for (let i = 0; i < back.length; i += 1) {
      expect(back[i].box.left).toBeLessThan(front[i].box.left);
      expect(back[i].box.left).toBeGreaterThan(front[i + 1].box.left);
    }
    // The front rank paints above the back rank.
    expect(Math.min(...front.map((figure) => figure.z))).toBeGreaterThan(Math.max(...back.map((figure) => figure.z)));
  });
});

describe("combat formation: inputs outside the supported range", () => {
  it("returns the floor, two-rank, compact formation with fits false on a small stage", () => {
    const S = 1;
    const width = 1024;
    const height = 560;
    const band = 190;
    const input = {
      stageWidth: width,
      stageHeight: height,
      uiScale: S,
      bandTop: height - band,
      actorHeight: Math.min(0.62 * height, 680, height - 48 - band),
      topBandBottom: 48,
      vitalsDock: { left: 16, top: height - band - 92, width: 0.25 * width, height: 92 },
      partyCount: 4,
      foeCount: 9,
    };
    const result = combatFormation(input);
    expect(result.fits).toBe(false);
    expect(result.scale).toBe(SCALE_FLOOR);
    expect(result.party.ranks).toBe(2);
    expect(result.foes.ranks).toBe(2);
    expect(allFigures(result).every((figure) => figure.plate.form === "compact")).toBe(true);
    const heights = new Set(allFigures(result).map((figure) => figure.box.height));
    expect(heights.size).toBe(1);
    expect(result.party.figures).toHaveLength(4);
    expect(result.foes.figures).toHaveLength(9);
  });
});

describe("combat formation: edge rules", () => {
  it("gives a one-figure rank a single plate line", () => {
    // Three foes in the floor fallback: two in front, one behind.
    const result = combatFormation({ ...reference("1451x790", 1, 3), stageWidth: 700 });
    expect(result.fits).toBe(false);
    const back = result.foes.figures.filter((figure) => figure.rank === 1);
    expect(back).toHaveLength(1);
    expect(back[0].plate.line).toBe(0);
  });

  it("treats a plate that only touches the vitals dock as touching it", () => {
    const base = reference("1451x790", 1, 1);
    const plate = combatFormation(base).party.figures[0].plate;
    expect(combatFormation(base).scale).toBe(0.84);
    // A dock whose bottom edge lies exactly on the 0.84 plate's top edge.
    const touching = combatFormation({ ...base, vitalsDock: { left: plate.left, top: plate.top - 10, width: 10, height: 10 } });
    expect(touching.scale).toBeLessThan(0.84);
    const touched = touching.party.figures[0].plate;
    expect(distance(touched, { left: plate.left, top: plate.top - 10, width: 10, height: 10 })).toBeGreaterThan(0);
  });

  it("keeps plates 2px·S apart across ranks where a short back-rank lift brings them together", () => {
    // Short figures (actor-h 300px) lift the back rank only 81px, so a
    // two-rank full layout would stack its plates onto the front rank's.
    for (const foeCount of [8, 10, 12, 14]) {
      const input = {
        ...reference("1451x790", 1, foeCount),
        actorHeight: 300,
        vitalsDock: { left: 16, top: 560, width: 10, height: 10 },
      };
      const result = combatFormation(input);
      expect(violations({ input }, result), `f${foeCount}`).toEqual([]);
    }
  });

  it("shrinks or compacts until the vitals dock covers at most the lowest 40% of the party box", () => {
    // A 170px dock covers 41% of the 0.84 box (411.4px) but 38.5% of the
    // 0.90 box, which fits only with compact plates.
    const base = reference("1451x790", 1, 1);
    const input = { ...base, vitalsDock: { ...base.vitalsDock, top: base.bandTop - 170, height: 170 } };
    const result = combatFormation(input);
    expect(result.scale).toBe(0.9);
    expect(result.party.form).toBe("compact");
    expect(violations({ input }, result)).toEqual([]);
  });

  it("rejects missing or non-finite required inputs", () => {
    const base = reference("1451x790", 1, 1);
    for (const name of ["stageWidth", "stageHeight", "bandTop", "actorHeight", "topBandBottom"]) {
      expect(() => combatFormation({ ...base, [name]: undefined }), name).toThrow(TypeError);
      expect(() => combatFormation({ ...base, [name]: Number.NaN }), name).toThrow(TypeError);
    }
    // A missing or unusable chrome factor would size every slot for S = 1.
    for (const uiScale of [undefined, 0, -1, "abc"]) {
      expect(() => combatFormation({ ...base, uiScale }), String(uiScale)).toThrow(TypeError);
    }
    for (const bad of [undefined, -1, 1.5, "two", null]) {
      expect(() => combatFormation({ ...base, partyCount: bad }), `party ${bad}`).toThrow(TypeError);
      expect(() => combatFormation({ ...base, foeCount: bad }), `foes ${bad}`).toThrow(TypeError);
    }
  });
});

describe("combat formation: purity", () => {
  it("returns the same output for the same input and leaves the input untouched", () => {
    const input = reference("1600x900", 2, 9);
    const frozen = Object.freeze({ ...input, vitalsDock: Object.freeze({ ...input.vitalsDock }) });
    const first = combatFormation(frozen);
    const second = combatFormation(frozen);
    expect(second).toEqual(first);
    expect(frozen).toEqual(input);
  });

  it("imports nothing from Vue or the DOM", () => {
    const source = readFileSync(join(APP_ROOT, "components/combat-formation.js"), "utf8");
    const executable = source.replace(/\/\/.*$/gm, "");
    expect(executable).not.toMatch(/\bimport\b/);
    expect(executable).not.toMatch(/\brequire\s*\(/);
    expect(executable).not.toMatch(/\b(document|window|getComputedStyle|getBoundingClientRect)\b/);
    expect(executable).not.toMatch(/\bvue\b/i);
  });
});

describe("combat formation: the stage input adapter", () => {
  function styles(values) {
    return { getPropertyValue: (name) => values[name] ?? "" };
  }

  it("converts resolved CSS values and viewport rectangles into the engine input", () => {
    const stageRect = { left: 0, top: 0, width: 1451, height: 790 };
    const css = styles({ "--ui-scale": "1", "--actor-h": "489.8px", "--band-h": "220.015px", "--header-h": "48px" });
    const vitalsRect = { left: 16, top: 790 - 220.015 - 92, width: 362.75, height: 92 };
    const input = formationInputFromStage(stageRect, css, vitalsRect, { party: 2, foes: 5 });
    expect(input).toMatchObject({
      stageWidth: 1451,
      stageHeight: 790,
      uiScale: 1,
      actorHeight: 489.8,
      topBandBottom: 48,
      cardWidth: 264,
      partyCount: 2,
      foeCount: 5,
    });
    expect(input.bandTop).toBeCloseTo(790 - 220.015, 6);
    expect(combatFormation(input)).toEqual(combatFormation(reference("1451x790", 2, 5)));
  });

  it("measures the vitals dock relative to an offset stage and scales the card", () => {
    const stageRect = { left: 10, top: 20, width: 1600, height: 900 };
    const css = styles({ "--ui-scale": " 1.1027 ", "--actor-h": "558px", "--band-h": "250.65px", "--header-h": "52.9296px" });
    const input = formationInputFromStage(stageRect, css, { left: 27.6, top: 600, width: 400, height: 101.4 }, {
      party: 1,
      foes: 1,
    });
    expect(input.vitalsDock.left).toBeCloseTo(17.6, 6);
    expect(input.vitalsDock.top).toBeCloseTo(580, 6);
    expect(input.cardWidth).toBeCloseTo(264 * 1.1027, 6);
    expect(input.bandTop).toBeCloseTo(900 - 250.65, 6);
  });

  it("drops an absent or empty vitals dock", () => {
    const css = styles({ "--ui-scale": "1", "--actor-h": "489.8px", "--band-h": "220px", "--header-h": "48px" });
    const stageRect = { left: 0, top: 0, width: 1451, height: 790 };
    expect(formationInputFromStage(stageRect, css, null, { party: 1, foes: 1 }).vitalsDock).toBeNull();
    expect(
      formationInputFromStage(stageRect, css, { left: 0, top: 0, width: 0, height: 0 }, { party: 1, foes: 1 }).vitalsDock,
    ).toBeNull();
  });

  it("requires the stage rectangle and the counts", () => {
    const css = styles({ "--ui-scale": "1", "--actor-h": "489.8px", "--band-h": "220px", "--header-h": "48px" });
    expect(() => formationInputFromStage({ left: 0, top: 0, width: 1451, height: 790 }, css, null)).toThrow(TypeError);
    expect(() => formationInputFromStage(null, css, null, { party: 1, foes: 1 })).toThrow(TypeError);
  });

  it("accepts a plain record of measured values", () => {
    const record = { "--ui-scale": 1, "--actor-h": 489.8, "--band-h": 220.015, "--header-h": 48 };
    const input = formationInputFromStage({ left: 0, top: 0, width: 1451, height: 790 }, record, null, { party: 1, foes: 3 });
    expect(input.actorHeight).toBe(489.8);
    expect(input.bandTop).toBeCloseTo(790 - 220.015, 6);
  });

  it("rejects an unresolved custom property instead of computing a NaN formation", () => {
    const css = styles({
      "--ui-scale": "1",
      "--actor-h": "min(62vh, 680px * 1, calc(100vh - 48px - 220px))",
      "--band-h": "220px",
      "--header-h": "48px",
    });
    expect(() => formationInputFromStage({ left: 0, top: 0, width: 1451, height: 790 }, css, null, {})).toThrow(
      TypeError,
    );
  });
});
