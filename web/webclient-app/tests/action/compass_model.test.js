// exploration-exit-compass (task 1.1): the pure exit-compass model — angle
// sources, snap, pointer zones, portal slots, cycle order, key aim, and the
// continuous-movement step rules.
import { describe, expect, it } from "vitest";
import ExplorationMenu from "../../lib/exploration_menu.js";
import LocalMap from "../../lib/local_map.js";
import {
  DEAD_ZONE,
  HOLD_MS,
  MAP_UNSYNCED_REASON,
  SNAP_TOLERANCE,
  STEP_DWELL_MS,
  aimForTarget,
  aimFromKeys,
  aimFromPointer,
  cycleTarget,
  nextStep,
  resnapAim,
  resolveTargets,
  snapAngled,
  snapPortal,
} from "../../components/compass-model.js";

const CURRENT = "node:here";

function node(id, x, y, visibility = "visible_unvisited") {
  return { id, label: `地點${id}`, x, y, visibility, current: visibility === "current", anchor: false, landmark: false, action: null };
}

// A committed local-map model exactly as the store builds it.
function mapModel(layer, nodes, currentNode = CURRENT) {
  return LocalMap.reducePanel({ schema_version: 1, available: true, layer, current_node: currentNode, title: "", nodes, edges: [], legend: [] });
}

function exitRow(ref, label, destination, extra = {}) {
  return { exit_ref: ref, label, destination, enabled: true, disabled_reason: null, ...extra };
}

// Build the rows through the real `moveItems`, so payloads are the real ones.
function rowsFor(move, currentNode = CURRENT) {
  return ExplorationMenu.moveItems({ move }, currentNode);
}

function targetsFor(move, model, currentNode = CURRENT) {
  return resolveTargets(rowsFor(move, currentNode), model, { currentNode });
}

const angledT = (angle, extra = {}) => ({ key: `exit-${angle}`, kind: "angled", angle, enabled: true, ...extra });

describe("compass-model constants", () => {
  it("fixes the spec values", () => {
    expect(SNAP_TOLERANCE).toBe(30);
    expect(DEAD_ZONE).toBe(0.2);
    expect(HOLD_MS).toBe(400);
    expect(STEP_DWELL_MS).toBe(350);
  });
});

describe("resolveTargets angle sources", () => {
  it("a wilderness exit takes its map bearing, equal to the minimap's", () => {
    const model = mapModel("wilderness", [node(CURRENT, 0, 0, "current"), node("ne", 1, 1)]);
    const targets = targetsFor([exitRow("a", "林間小徑", "ne")], model);
    expect(targets.angled).toHaveLength(1);
    const [target] = targets.angled;
    expect(target.source).toBe("map");
    expect(target.angle).toBeCloseTo(45, 9);
    expect(target.angle).toBe(LocalMap.remoteDirection({ x: 0, y: 0 }, { x: 1, y: 1 }).theta);
    expect(target.glyph).toBe("↗");
  });

  it("keeps an irregular city bearing unrounded", () => {
    const model = mapModel("grid", [node(CURRENT, 0, 0, "current"), node("d", 3, 4)]);
    const [target] = targetsFor([exitRow("a", "east", "d")], model).angled;
    expect(target.source).toBe("map");
    expect(target.angle).toBeCloseTo(36.87, 2);
  });

  it("uses a remembered destination node too", () => {
    const model = mapModel("grid", [node(CURRENT, 0, 0, "current"), node("far", -2, 0, "remembered")]);
    const [target] = targetsFor([exitRow("a", "小路", "far")], model).angled;
    expect(target.angle).toBe(270);
  });

  it("falls back to the direction word when the destination is off the map", () => {
    const model = mapModel("wilderness", [node(CURRENT, 0, 0, "current")]);
    const [target] = targetsFor([exitRow("a", "northeast", "elsewhere")], model).angled;
    expect(target.source).toBe("word");
    expect(target.angle).toBe(45);
  });

  it("falls back to the word when coordinates are equal or missing", () => {
    const model = mapModel("grid", [node(CURRENT, 0, 0, "current"), node("same", 0, 0)]);
    const [target] = targetsFor([exitRow("a", "南", "same")], model).angled;
    expect(target.source).toBe("word");
    expect(target.angle).toBe(180);
  });

  it("a cross-layer gate whose label is not a direction word is a portal", () => {
    const model = mapModel("grid", [node(CURRENT, 0, 0, "current")]);
    const targets = targetsFor([exitRow("gate", "荒野入口", "wild:1:1")], model);
    expect(targets.angled).toHaveLength(0);
    expect(targets.portals[0]).toMatchObject({ kind: "portal", vertical: null, glyph: "✦" });
  });

  it("never uses interior coordinates for a bearing", () => {
    const model = mapModel("interior", [node(CURRENT, 0, 0, "current"), node("hall", 3, 0)]);
    const targets = targetsFor([exitRow("door", "公會大廳", "hall")], model);
    expect(targets.angled).toHaveLength(0);
    expect(targets.portals).toHaveLength(1);
  });

  it("an interior direction word is still angled (rule 2), but never by its coordinates", () => {
    const model = mapModel("interior", [node(CURRENT, 0, 0, "current"), node("n", 5, 1)]);
    const [target] = targetsFor([exitRow("n", "north", "n")], model).angled;
    expect(target.source).toBe("word");
    expect(target.angle).toBe(0);
  });

  it("same-coordinate stairs are portals pinned up and down", () => {
    const model = mapModel("grid", [node(CURRENT, 2, 2, "current"), node("upper", 2, 2), node("lower", 2, 2)]);
    const targets = targetsFor([exitRow("u", "up", "upper"), exitRow("d", "下", "lower")], model);
    expect(targets.angled).toHaveLength(0);
    expect(targets.portals.map((p) => [p.vertical, p.slot, p.glyph])).toEqual([
      ["up", 0, "⇧"],
      ["down", 180, "⇩"],
    ]);
  });

  it("carries the row, its payload, its destination name, and payload order", () => {
    const model = mapModel("grid", [node(CURRENT, 0, 0, "current"), node("n", 0, 1)]);
    const rows = rowsFor([exitRow("x", "north", "n")]);
    const [target] = resolveTargets(rows, model, { currentNode: CURRENT }).angled;
    expect(target.item).toBe(rows[0]);
    expect(target.item.payload).toEqual({ exit_ref: "x", current_node: CURRENT });
    expect(target.exitRef).toBe("x");
    expect(target.label).toBe("地點n");
  });

  it("resolves every row exactly once", () => {
    const model = mapModel("grid", [node(CURRENT, 0, 0, "current"), node("e", 1, 0)]);
    const move = [exitRow("a", "east", "e"), exitRow("b", "西", "w"), exitRow("c", "門", "z"), exitRow("d", "up", "u")];
    const targets = targetsFor(move, model);
    expect(targets.cycle.map((t) => t.exitRef).sort()).toEqual(["a", "b", "c", "d"]);
  });
});

describe("resolveTargets disabled exits and absence", () => {
  it("keeps a disabled exit with its server-authored reason", () => {
    const model = mapModel("grid", [node(CURRENT, 0, 0, "current"), node("n", 0, 1)]);
    const move = [exitRow("n", "north", "n", { enabled: false, disabled_reason: { code: "locked", message: "門鎖著。" } })];
    const [target] = targetsFor(move, model).angled;
    expect(target.enabled).toBe(false);
    expect(target.reason).toBe("門鎖著。");
    expect(target.label).toBe("north");
  });

  it("with no local map, words still angle, the rest are portals, all disabled as unsynced", () => {
    const move = [exitRow("n", "north", "n"), exitRow("door", "酒館門", "t")];
    const targets = resolveTargets(rowsFor(move, null), null, { currentNode: null });
    expect(targets.angled.map((t) => [t.angle, t.enabled, t.reason])).toEqual([[0, false, MAP_UNSYNCED_REASON]]);
    expect(targets.portals.map((t) => [t.enabled, t.reason])).toEqual([[false, MAP_UNSYNCED_REASON]]);
  });

  it("a room with no exits has no targets", () => {
    expect(resolveTargets([], null)).toEqual({ angled: [], portals: [], cycle: [] });
  });
});

describe("portal slots", () => {
  function portalsFor(labels) {
    const move = labels.map((label, i) => exitRow(`p${i}`, label, `dest${i}`));
    return targetsFor(move, mapModel("interior", [node(CURRENT, 0, 0, "current")])).portals;
  }

  it("spreads three portals evenly at 60°, 180°, 300°", () => {
    expect(portalsFor(["甲", "乙", "丙"]).map((p) => [p.label, p.slot])).toEqual([
      ["甲", 60],
      ["乙", 180],
      ["丙", 300],
    ]);
  });

  it("pins up and down and keeps the other portal off both slots", () => {
    const portals = portalsFor(["up", "down", "門"]);
    const bySlot = Object.fromEntries(portals.map((p) => [p.slot, p.label]));
    expect(bySlot[0]).toBe("up");
    expect(bySlot[180]).toBe("down");
    const other = portals.find((p) => p.label === "門");
    expect([0, 180]).not.toContain(other.slot);
  });

  it("takes the nearest free slot with the clockwise slot winning a tie", () => {
    // One other portal: ideal round(0.5 · 12) = 6 (180°), taken by down, so
    // the clockwise neighbour 7 (210°) wins over 5 (150°).
    const portals = portalsFor(["down", "門"]);
    expect(portals.find((p) => p.label === "門").slot).toBe(210);
  });

  it("switches to 24 slots above ten portals and never shares a slot", () => {
    const labels = Array.from({ length: 11 }, (_, i) => `門${i}`);
    const portals = portalsFor(labels);
    const slots = portals.map((p) => p.slot);
    expect(new Set(slots).size).toBe(11);
    expect(slots.some((slot) => slot % 30 !== 0)).toBe(true);
    slots.forEach((slot) => expect(slot % 15).toBe(0));
  });

  it("ten portals stay on the 12-slot ring", () => {
    const portals = portalsFor(Array.from({ length: 10 }, (_, i) => `門${i}`));
    portals.forEach((p) => expect(p.slot % 30).toBe(0));
    expect(new Set(portals.map((p) => p.slot)).size).toBe(10);
  });
});

describe("snap", () => {
  it("captures the nearest exit within thirty degrees", () => {
    expect(snapAngled([angledT(0), angledT(90)], 20).angle).toBe(0);
  });

  it("has no target outside tolerance", () => {
    expect(snapAngled([angledT(0)], 100)).toBeNull();
  });

  it("gives a tie to the smaller clockwise angle", () => {
    expect(snapAngled([angledT(0), angledT(60)], 30).angle).toBe(0);
  });

  it("wraps across north", () => {
    expect(snapAngled([angledT(350), angledT(90)], 10).angle).toBe(350);
  });

  it("the outer track snaps to the nearest portal at any angle", () => {
    const portals = [{ key: "a", slot: 0 }, { key: "b", slot: 180 }];
    expect(snapPortal(portals, 100).key).toBe("b");
    expect(snapPortal([], 100)).toBeNull();
  });
});

describe("aimFromPointer zones", () => {
  const targets = { angled: [angledT(0)], portals: [{ key: "p", slot: 90 }], cycle: [] };

  it("the dead zone has no angle and no target", () => {
    expect(aimFromPointer(targets, 0.19, 10, 1.1)).toEqual({ angle: null, target: null, zone: "dead" });
  });

  it("the pad snaps angled exits", () => {
    const aim = aimFromPointer(targets, 0.5, 10, 1.1);
    expect(aim.zone).toBe("pad");
    expect(aim.target.angle).toBe(0);
  });

  it("the ring snaps portals", () => {
    const aim = aimFromPointer(targets, 1.15, 10, 1.1);
    expect(aim.zone).toBe("ring");
    expect(aim.target.key).toBe("p");
  });

  it("without portals the ring is just more pad", () => {
    const aim = aimFromPointer({ ...targets, portals: [] }, 1.15, 10, 1.1);
    expect(aim.zone).toBe("pad");
  });
});

describe("aimFromKeys", () => {
  const cases = [
    [["ArrowUp"], 0],
    [["ArrowUp", "ArrowRight"], 45],
    [["ArrowRight"], 90],
    [["ArrowDown", "ArrowRight"], 135],
    [["ArrowDown"], 180],
    [["ArrowDown", "ArrowLeft"], 225],
    [["ArrowLeft"], 270],
    [["ArrowUp", "ArrowLeft"], 315],
  ];
  it.each(cases)("%j aims at %d°", (keys, angle) => {
    expect(aimFromKeys(new Set(keys))).toBeCloseTo(angle, 9);
  });

  it("opposing keys cancel", () => {
    expect(aimFromKeys(new Set(["ArrowUp", "ArrowDown"]))).toBeNull();
    expect(aimFromKeys(new Set(["ArrowLeft", "ArrowRight"]))).toBeNull();
    expect(aimFromKeys(new Set())).toBeNull();
    expect(aimFromKeys(new Set(["ArrowUp", "ArrowRight", "ArrowDown"]))).toBe(90);
  });
});

describe("cycle order", () => {
  it("walks angled by ascending angle, then portals by ascending slot, then wraps", () => {
    const model = mapModel("grid", [node(CURRENT, 0, 0, "current")]);
    const move = [exitRow("w", "west", "x"), exitRow("door", "門", "y"), exitRow("n", "north", "z"), exitRow("u", "up", "q"), exitRow("ne", "東北", "r")];
    const targets = targetsFor(move, model);
    const order = [];
    let current = null;
    for (let i = 0; i < 6; i += 1) {
      current = cycleTarget(targets, current, 1);
      order.push(current.exitRef);
    }
    expect(order).toEqual(["n", "ne", "w", "u", "door", "n"]);
    expect(cycleTarget(targets, null, -1).exitRef).toBe("door");
    expect(cycleTarget({ cycle: [] }, null, 1)).toBeNull();
  });

  it("a cycled target implies its own aim", () => {
    expect(aimForTarget(angledT(90))).toMatchObject({ angle: 90, zone: "pad" });
    expect(aimForTarget({ kind: "portal", slot: 180 })).toMatchObject({ angle: 180, zone: "ring" });
  });
});

describe("nextStep and resnap", () => {
  it("steps to the snapped enabled exit", () => {
    const step = nextStep({ angled: [angledT(10)] }, 0);
    expect(step.stop).toBeNull();
    expect(step.target.angle).toBe(10);
  });

  it("stops at a dead end", () => {
    expect(nextStep({ angled: [angledT(90)] }, 0)).toEqual({ stop: "no-exit", target: null });
  });

  it("stops at a disabled exit, carrying it for its reason", () => {
    const disabled = angledT(0, { enabled: false, reason: "崩塌了。" });
    expect(nextStep({ angled: [disabled] }, 0)).toEqual({ stop: "disabled", target: disabled });
  });

  it("stops with no aim", () => {
    expect(nextStep({ angled: [angledT(0)] }, null).stop).toBe("no-aim");
  });

  it("re-snaps a pad aim against a new room and clears a missing one", () => {
    const next = { angled: [angledT(20)], portals: [{ key: "p", slot: 0 }] };
    expect(resnapAim(next, { angle: 0, target: null, zone: "pad" }).target.angle).toBe(20);
    expect(resnapAim(next, { angle: 200, target: null, zone: "ring" }).target.key).toBe("p");
    expect(resnapAim(next, { angle: null, target: null, zone: "none" }).zone).toBe("none");
  });
});

describe("bearing equality with the minimap", () => {
  it("matches LocalMap.remoteDirection over a coordinate grid", () => {
    for (let x = -3; x <= 3; x += 1) {
      for (let y = -3; y <= 3; y += 1) {
        if (x === 0 && y === 0) continue;
        const model = mapModel("wilderness", [node(CURRENT, 0, 0, "current"), node("d", x, y)]);
        const [target] = targetsFor([exitRow("a", "路", "d")], model).angled;
        const minimap = LocalMap.remoteDirection({ x: 0, y: 0 }, { x, y });
        expect(target.angle).toBe(minimap.theta);
        expect(Math.floor(target.angle / 45 + 0.5) % 8).toBe(minimap.octant);
      }
    }
  });
});
