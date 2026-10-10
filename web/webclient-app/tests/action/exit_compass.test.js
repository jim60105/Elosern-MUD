// exploration-exit-compass (task 2.1): ExitCompass pointer and keyboard
// operation, the one-move-in-flight queue, commit-driven continuous movement,
// and every stop reason. The compass sends nothing: it emits `move(item)`.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import ExitCompass from "../../components/ExitCompass.vue";
import ExplorationMenu from "../../lib/exploration_menu.js";
import { HOLD_MS, STEP_DWELL_MS, resolveTargets } from "../../components/compass-model.js";

const CURRENT = "room:here";

function room(move) {
  const rows = ExplorationMenu.moveItems({ move }, CURRENT);
  return resolveTargets(rows, null, { currentNode: CURRENT });
}

function exit(ref, label, extra = {}) {
  return { exit_ref: ref, label, destination: `dest:${ref}`, enabled: true, disabled_reason: null, ...extra };
}

const NORTH_ROOM = room([exit("n1", "north"), exit("e1", "east"), exit("door", "酒館門")]);
const NORTH_ROOM_2 = room([exit("n2", "north"), exit("s2", "south")]);
const DEAD_END = room([exit("s3", "south")]);
const LOCKED_NORTH = room([
  exit("n4", "north", { enabled: false, disabled_reason: { code: "locked", message: "前方的吊橋已經收起。" } }),
]);

let wrapper;
let documentKeys;

function onDocumentKey(event) {
  documentKeys.push(event.key);
}

beforeEach(() => {
  vi.useFakeTimers();
  documentKeys = [];
  document.addEventListener("keydown", onDocumentKey);
  document.addEventListener("keyup", onDocumentKey);
});

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  document.removeEventListener("keydown", onDocumentKey);
  document.removeEventListener("keyup", onDocumentKey);
  document.body.innerHTML = "";
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function mountCompass(props = {}) {
  wrapper = mount(ExitCompass, {
    attachTo: document.body,
    props: { targets: NORTH_ROOM, arrivalKey: 1, busy: false, active: true, motionLevel: "full", ...props },
  });
  const svg = wrapper.get('[data-testid="exit-compass-pad"]').element;
  svg.getBoundingClientRect = () => ({ left: 0, top: 0, width: 200, height: 200, right: 200, bottom: 200, x: 0, y: 0 });
  return wrapper;
}

// A pointer position at `angle` degrees clockwise from north, `r` user units
// from the centre (the pad radius is 72, the portal track 88).
function at(angle, r = 50) {
  const rad = (angle * Math.PI) / 180;
  return { clientX: 100 + r * Math.sin(rad), clientY: 100 - r * Math.cos(rad), button: 0 };
}

const moves = () => (wrapper.emitted("move") || []).map(([item]) => item.payload.exit_ref);
const blockedKinds = () => (wrapper.emitted("blocked") || []).map(([b]) => b.kind);
const lastAim = () => {
  const aims = wrapper.emitted("aim") || [];
  return aims.length ? aims[aims.length - 1][0] : null;
};
const pad = () => wrapper.get('[data-testid="exit-compass-pad"]');
const root = () => wrapper.get('[data-testid="exit-compass"]');

async function click(angle, r = 50) {
  await pad().trigger("pointermove", at(angle, r));
  await pad().trigger("pointerdown", at(angle, r));
  await pad().trigger("pointerup", at(angle, r));
}

async function key(type, k, extra = {}) {
  await root().trigger(type, { key: k, ...extra });
}

async function arrive(targets, arrivalKey, props = {}) {
  await wrapper.setProps({ targets, arrivalKey, ...props });
}

describe("ExitCompass rendering", () => {
  it("is one application tab stop with pips, beads, ticks, the dead zone, and the track", () => {
    mountCompass();
    const el = root();
    expect(el.attributes("role")).toBe("application");
    expect(el.attributes("aria-label")).toBe("出口羅盤");
    expect(el.attributes("tabindex")).toBe("0");
    expect(wrapper.findAll('[data-testid="exit-compass-pip"]').map((p) => p.attributes("data-exit-ref"))).toEqual(["n1", "e1"]);
    expect(wrapper.findAll('[data-testid="exit-compass-portal"]').map((p) => p.attributes("data-exit-ref"))).toEqual(["door"]);
    expect(wrapper.findAll(".exit-compass__tick")).toHaveLength(4);
    expect(wrapper.find(".exit-compass__dead").attributes("r")).toBe(String(0.2 * 72));
    expect(wrapper.find('[data-testid="exit-compass-track"]').exists()).toBe(true);
  });

  it("draws a disabled exit as a hollow dashed pip", () => {
    mountCompass({ targets: LOCKED_NORTH });
    const pip = wrapper.get('[data-testid="exit-compass-pip"]');
    expect(pip.attributes("data-enabled")).toBe("false");
    expect(pip.classes()).toContain("exit-compass__pip--off");
  });

  it("renders an empty pad with no track for a room without exits", () => {
    mountCompass({ targets: room([]) });
    expect(wrapper.find('[data-testid="exit-compass-pip"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="exit-compass-track"]').exists()).toBe(false);
  });
});

describe("ExitCompass pointer", () => {
  it("hover aims, highlights the pip, leans the knob, and sends nothing", async () => {
    mountCompass();
    await pad().trigger("pointermove", at(10));
    expect(lastAim()).toMatchObject({ zone: "pad", target: { exitRef: "n1" } });
    expect(wrapper.get('[data-exit-ref="n1"]').attributes("data-aimed")).toBe("true");
    expect(wrapper.find('[data-testid="exit-compass-wedge"]').exists()).toBe(true);
    const knob = wrapper.get('[data-testid="exit-compass-knob"]');
    expect(Number(knob.attributes("cy"))).toBeCloseTo(-72 * 0.48, 5);
    expect(wrapper.emitted("move")).toBeUndefined();
  });

  it("the dead zone has no target and the knob stays centred", async () => {
    mountCompass();
    await pad().trigger("pointermove", at(10, 10));
    expect(lastAim()).toEqual({ angle: null, target: null, zone: "dead" });
  });

  it("an aim with no exit in tolerance leans weakly and unlit", async () => {
    mountCompass();
    await pad().trigger("pointermove", at(200));
    expect(lastAim().target).toBeNull();
    const knob = wrapper.get('[data-testid="exit-compass-knob"]');
    expect(knob.classes()).not.toContain("exit-compass__knob--lit");
    expect(Math.hypot(Number(knob.attributes("cx")), Number(knob.attributes("cy")))).toBeCloseTo(72 * 0.3, 5);
  });

  it("the outer track aims the nearest portal", async () => {
    mountCompass();
    await pad().trigger("pointermove", at(170, 86));
    expect(lastAim()).toMatchObject({ zone: "ring", target: { exitRef: "door" } });
  });

  it("a click moves once with the committed row", async () => {
    mountCompass();
    await click(5);
    expect(moves()).toEqual(["n1"]);
    expect(wrapper.emitted("move")[0][0]).toStrictEqual(NORTH_ROOM.angled[0].item);
  });

  it("a click with no target shakes and sends nothing", async () => {
    mountCompass();
    await click(200);
    expect(moves()).toEqual([]);
    expect(blockedKinds()).toEqual(["no-exit"]);
    await nextTick();
    expect(pad().classes()).toContain("exit-compass__svg--shake");
  });

  it("a click on a disabled target shakes and carries the target", async () => {
    mountCompass({ targets: LOCKED_NORTH });
    await click(0);
    expect(moves()).toEqual([]);
    expect(wrapper.emitted("blocked")[0][0]).toMatchObject({ kind: "disabled", target: { reason: "前方的吊橋已經收起。" } });
  });

  it("the off motion level never shakes", async () => {
    mountCompass({ motionLevel: "off" });
    await click(200);
    await nextTick();
    expect(blockedKinds()).toEqual(["no-exit"]);
    expect(pad().classes()).not.toContain("exit-compass__svg--shake");
  });

  it("rapid clicks queue exactly one step, sent after the arrival and re-snapped", async () => {
    mountCompass();
    await click(5);
    await wrapper.setProps({ busy: true });
    await click(5);
    await click(5);
    await click(5);
    expect(moves()).toEqual(["n1"]);
    await arrive(NORTH_ROOM_2, 2, { busy: false });
    vi.advanceTimersByTime(STEP_DWELL_MS);
    expect(moves()).toEqual(["n1", "n2"]);
    await arrive(NORTH_ROOM, 3);
    vi.advanceTimersByTime(STEP_DWELL_MS * 3);
    expect(moves()).toEqual(["n1", "n2"]);
  });

  it("a hold starts a walk, steering follows the cursor, and release sends nothing more", async () => {
    mountCompass();
    await pad().trigger("pointermove", at(0));
    await pad().trigger("pointerdown", at(0));
    vi.advanceTimersByTime(HOLD_MS);
    await nextTick();
    expect(moves()).toEqual(["n1"]);
    expect(root().attributes("data-walking")).toBe("true");
    expect(root().classes()).toContain("exit-compass--walking");
    // Steer east before the next arrival.
    await pad().trigger("pointermove", at(90));
    await arrive(room([exit("n5", "north"), exit("e5", "east")]), 2);
    vi.advanceTimersByTime(STEP_DWELL_MS);
    expect(moves()).toEqual(["n1", "e5"]);
    await pad().trigger("pointerup", at(90));
    await arrive(room([exit("e6", "east")]), 3);
    vi.advanceTimersByTime(STEP_DWELL_MS * 3);
    expect(moves()).toEqual(["n1", "e5"]);
    expect(root().attributes("data-walking")).toBe("false");
  });

  it("a hold on a portal never starts a walk and its release sends nothing", async () => {
    mountCompass();
    await pad().trigger("pointermove", at(170, 86));
    await pad().trigger("pointerdown", at(170, 86));
    vi.advanceTimersByTime(HOLD_MS + 10);
    await pad().trigger("pointerup", at(170, 86));
    expect(moves()).toEqual([]);
    expect(root().attributes("data-walking")).toBe("false");
  });

  it("leaving the pad stops a walk and clears the aim", async () => {
    mountCompass();
    await pad().trigger("pointermove", at(0));
    await pad().trigger("pointerdown", at(0));
    vi.advanceTimersByTime(HOLD_MS);
    await pad().trigger("pointerleave");
    expect(lastAim()).toMatchObject({ target: null, zone: "none" });
    await arrive(NORTH_ROOM_2, 2);
    vi.advanceTimersByTime(STEP_DWELL_MS * 3);
    expect(moves()).toEqual(["n1"]);
  });
});

describe("ExitCompass keyboard", () => {
  it("an arrow tap only aims", async () => {
    mountCompass();
    await key("keydown", "ArrowUp");
    await key("keyup", "ArrowUp");
    expect(lastAim()).toMatchObject({ angle: 0, target: { exitRef: "n1" } });
    vi.advanceTimersByTime(HOLD_MS * 2);
    expect(moves()).toEqual([]);
  });

  it("two arrows give a diagonal and an opposing arrow cancels its axis", async () => {
    mountCompass();
    await key("keydown", "ArrowUp");
    await key("keydown", "ArrowRight");
    expect(lastAim().angle).toBeCloseTo(45, 9);
    await key("keydown", "ArrowDown");
    expect(lastAim().angle).toBe(90);
  });

  it("brackets cycle angled exits by angle, then portals, then wrap", async () => {
    mountCompass();
    const seen = [];
    for (let i = 0; i < 4; i += 1) {
      await key("keydown", "]");
      seen.push(root().attributes("data-aim-ref"));
    }
    expect(seen).toEqual(["n1", "e1", "door", "n1"]);
    await key("keydown", "[");
    expect(root().attributes("data-aim-ref")).toBe("door");
  });

  it("Enter released before the hold moves once and key repeat is ignored", async () => {
    mountCompass();
    await key("keydown", "ArrowUp");
    await key("keyup", "ArrowUp");
    await key("keydown", "Enter");
    await key("keydown", "Enter", { repeat: true });
    await key("keydown", "Enter", { repeat: true });
    vi.advanceTimersByTime(HOLD_MS - 50);
    await key("keyup", "Enter");
    expect(moves()).toEqual(["n1"]);
  });

  it("Space moves like Enter", async () => {
    mountCompass();
    await key("keydown", "]");
    await key("keydown", " ");
    await key("keyup", " ");
    expect(moves()).toEqual(["n1"]);
  });

  it("Enter on a disabled exit sends nothing and says why", async () => {
    mountCompass({ targets: LOCKED_NORTH });
    await key("keydown", "]");
    await key("keydown", "Enter");
    await key("keyup", "Enter");
    expect(moves()).toEqual([]);
    expect(blockedKinds()).toEqual(["disabled"]);
  });

  it("holding Enter walks without an extra discrete move, and release stops", async () => {
    mountCompass();
    await key("keydown", "]");
    await key("keydown", "Enter");
    vi.advanceTimersByTime(HOLD_MS);
    expect(moves()).toEqual(["n1"]);
    await arrive(NORTH_ROOM_2, 2);
    vi.advanceTimersByTime(STEP_DWELL_MS);
    expect(moves()).toEqual(["n1", "n2"]);
    await key("keyup", "Enter");
    expect(moves()).toEqual(["n1", "n2"]);
    await arrive(NORTH_ROOM, 3);
    vi.advanceTimersByTime(STEP_DWELL_MS * 3);
    expect(moves()).toEqual(["n1", "n2"]);
  });

  it("holding an arrow walks one move per arrival, never two in flight", async () => {
    mountCompass();
    await key("keydown", "ArrowUp");
    vi.advanceTimersByTime(HOLD_MS);
    expect(moves()).toEqual(["n1"]);
    // The arrival commit lands while the gate still waits for its revision.
    await arrive(NORTH_ROOM_2, 2, { busy: true });
    vi.advanceTimersByTime(STEP_DWELL_MS);
    expect(moves()).toEqual(["n1"]);
    await wrapper.setProps({ busy: false });
    expect(moves()).toEqual(["n1", "n2"]);
    await key("keyup", "ArrowUp");
  });

  it("each step waits the dwell after the previous send", async () => {
    mountCompass();
    await key("keydown", "ArrowUp");
    vi.advanceTimersByTime(HOLD_MS);
    await arrive(NORTH_ROOM_2, 2);
    vi.advanceTimersByTime(STEP_DWELL_MS - 1);
    expect(moves()).toEqual(["n1"]);
    vi.advanceTimersByTime(1);
    expect(moves()).toEqual(["n1", "n2"]);
  });

  it("blur stops a keyboard walk", async () => {
    mountCompass();
    root().element.focus();
    await key("keydown", "ArrowUp");
    vi.advanceTimersByTime(HOLD_MS);
    root().element.blur();
    await root().trigger("blur");
    await arrive(NORTH_ROOM_2, 2);
    vi.advanceTimersByTime(STEP_DWELL_MS * 3);
    expect(moves()).toEqual(["n1"]);
    expect(lastAim()).toMatchObject({ target: null });
  });

  it("Escape clears the aim and stops a walk; a bare Escape bubbles", async () => {
    mountCompass();
    await key("keydown", "ArrowUp");
    vi.advanceTimersByTime(HOLD_MS);
    await key("keydown", "Escape");
    expect(lastAim()).toMatchObject({ angle: null, target: null });
    expect(root().attributes("data-walking")).toBe("false");
    expect(documentKeys).not.toContain("Escape");
    await key("keydown", "Escape");
    expect(documentKeys).toContain("Escape");
  });

  it("consumes its keys so the document bridge never sees them, while digits and / bubble", async () => {
    mountCompass();
    for (const k of ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "[", "]", "Enter", " "]) {
      await key("keydown", k);
      await key("keyup", k);
    }
    expect(documentKeys).toEqual([]);
    await key("keydown", "1");
    await key("keydown", "/");
    expect(documentKeys).toEqual(["1", "/"]);
  });

  it("leaves modified keys to the browser", async () => {
    mountCompass();
    await key("keydown", "ArrowLeft", { altKey: true });
    expect(documentKeys).toEqual(["ArrowLeft"]);
    expect(lastAim()).toBeNull();
  });
});

describe("ExitCompass stop reasons", () => {
  async function startWalkingNorth() {
    mountCompass();
    await key("keydown", "ArrowUp");
    vi.advanceTimersByTime(HOLD_MS);
    expect(moves()).toEqual(["n1"]);
  }

  it("a dead end stops with a shake", async () => {
    await startWalkingNorth();
    await arrive(DEAD_END, 2);
    vi.advanceTimersByTime(STEP_DWELL_MS);
    expect(moves()).toEqual(["n1"]);
    expect(blockedKinds()).toEqual(["dead-end"]);
    await nextTick();
    expect(root().attributes("data-walking")).toBe("false");
  });

  it("a disabled exit stops with its server reason", async () => {
    await startWalkingNorth();
    await arrive(LOCKED_NORTH, 2);
    vi.advanceTimersByTime(STEP_DWELL_MS);
    expect(wrapper.emitted("blocked")[0][0]).toMatchObject({ kind: "disabled", target: { reason: "前方的吊橋已經收起。" } });
  });

  it("a server rejection halts the walk with its message", async () => {
    await startWalkingNorth();
    wrapper.vm.halt("你被荊棘纏住了。");
    await nextTick();
    expect(wrapper.emitted("blocked")[0][0]).toMatchObject({ kind: "rejected", message: "你被荊棘纏住了。" });
    await arrive(NORTH_ROOM_2, 2);
    vi.advanceTimersByTime(STEP_DWELL_MS * 3);
    expect(moves()).toEqual(["n1"]);
  });

  it("leaving exploration stops the walk without another move", async () => {
    await startWalkingNorth();
    await arrive(NORTH_ROOM_2, 2, { active: false });
    vi.advanceTimersByTime(STEP_DWELL_MS * 3);
    expect(moves()).toEqual(["n1"]);
    expect(root().attributes("data-walking")).toBe("false");
  });

  it("a gate that never releases suppresses the step after a bounded wait", async () => {
    await startWalkingNorth();
    await arrive(NORTH_ROOM_2, 2, { busy: true });
    vi.advanceTimersByTime(STEP_DWELL_MS + 2000);
    expect(blockedKinds()).toEqual(["suppressed"]);
    await wrapper.setProps({ busy: false });
    expect(moves()).toEqual(["n1"]);
  });

  it("an accepted step with no new panel stops after a bounded wait", async () => {
    await startWalkingNorth();
    await wrapper.setProps({ busy: true });
    await wrapper.setProps({ busy: false });
    vi.advanceTimersByTime(1199);
    expect(blockedKinds()).toEqual([]);
    vi.advanceTimersByTime(1);
    expect(blockedKinds()).toEqual(["no-change"]);
    await nextTick();
    expect(root().attributes("data-walking")).toBe("false");
  });

  it("a panel that lags the gate release by less than the grace still steps", async () => {
    await startWalkingNorth();
    await wrapper.setProps({ busy: true });
    await wrapper.setProps({ busy: false });
    vi.advanceTimersByTime(1000);
    await arrive(NORTH_ROOM_2, 2);
    vi.advanceTimersByTime(STEP_DWELL_MS);
    expect(moves()).toEqual(["n1", "n2"]);
    expect(blockedKinds()).toEqual([]);
  });

  it("a stopped and restarted walk never fires the stale step", async () => {
    await startWalkingNorth();
    await arrive(NORTH_ROOM_2, 2);
    await key("keyup", "ArrowUp");
    await key("keydown", "ArrowUp");
    vi.advanceTimersByTime(HOLD_MS);
    // The restart sent n2 itself; the cancelled step must not send again.
    expect(moves()).toEqual(["n1", "n2"]);
    vi.advanceTimersByTime(STEP_DWELL_MS * 3);
    expect(moves()).toEqual(["n1", "n2"]);
  });
});

describe("ExitCompass stories bind the derived shapes", async () => {
  const stories = await import("../../stories/Action/ExitCompass.stories.js");

  it("each static story resolves the documented targets", () => {
    const angles = (args) => args.targets.angled.map((t) => Math.round(t.angle));
    expect(angles(stories.Wilderness8Way.args)).toEqual([0, 45, 90, 135, 180, 225, 270, 315]);
    expect(angles(stories.GridIrregular.args)).toEqual([37, 143, 323]);
    expect(stories.InteriorPortals.args.targets.angled).toHaveLength(0);
    expect(stories.InteriorPortals.args.targets.portals.map((p) => p.slot)).toEqual([60, 180, 300]);
    const stairs = stories.Stairs.args.targets.portals;
    expect(stairs.find((p) => p.vertical === "up").slot).toBe(0);
    expect(stairs.find((p) => p.vertical === "down").slot).toBe(180);
    expect(stories.DisabledExit.args.targets.angled.find((t) => !t.enabled).reason).toBe("前方的吊橋已經收起。");
    expect(new Set(stories.TenPortals.args.targets.portals.map((p) => p.slot)).size).toBe(10);
  });

  it("every story mounts", () => {
    for (const name of ["Wilderness8Way", "GridIrregular", "InteriorPortals", "Stairs", "DisabledExit", "TenPortals", "Walking"]) {
      const story = stories[name];
      const w = mount(story.render(story.args), { attachTo: document.body });
      expect(w.find('[data-testid="exit-compass"]').exists(), name).toBe(true);
      w.unmount();
    }
  });
});
