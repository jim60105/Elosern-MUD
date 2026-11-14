// The landmark rite in the client shell (landmark-rite-stage design D5): the
// real composed store behind a fake sender, synthetic committed `rite`
// panels through the real validators and the mounted AppClient. The arrival
// card, the rite stage over the exploration mode, the one perform, the
// delivered scene through the shared player, the return entry and the
// withdrawal.
import { afterEach, describe, expect, it, vi } from "vitest";
import { ritePanel } from "../stories/fixtures/rite.js";
import { fx, liveTravel, panelsAt, tick, TOWN_SUBJECT, walkArea, walkNode, walkPanels } from "./travel/support.js";

vi.setConfig({ testTimeout: 60000 });

const CX = 60;
const CY = 80;

const DELIVERY = {
  kind: "formal",
  delivery_id: "rite:synthetic_highlands:drink:1",
  scene_id: "rite.synthetic.drink.self",
  scene_revision: "r1",
  actor_name: "你",
  guardian_name: "合成泉聲",
  lines: [
    { kind: "narration", text: "合成敘述之一。" },
    { kind: "speech", speaker: "actor", text: "合成台詞之二。" },
    { kind: "speech", speaker: "host", text: "合成台詞之三。" },
  ],
};

function sleepHandoffPanel() {
  return {
    schema_version: 1,
    available: true,
    owner_id: 42,
    controlled_body_id: 42,
    transition_id: "42:v:1",
    selection: {
      available: true,
      rows: [{ kind: "possess", identity: 2, name: "同伴", reserve_percent: 100, stage: "normal", label: "接手 同伴（精力 100%）", enabled: true, reason: null }],
    },
    party: { label: "全員一起睡眠", enabled: true, reason: null },
    controlled_sleep: { sleep_id: "sleep-1", revision: 0 },
    owner_sleep: {
      sleep_id: "sleep-1", revision: 0, generation: 1, dream_pending: false, continuation: "none",
      continuation_available: false, continuation_reason: null,
    },
  };
}

/** One typed `landmark_reached` notice reached at `node`. */
function arrivalLog(node) {
  return {
    travel_log: {
      schema_version: 1,
      available: true,
      entries: [{
        id: `${"b".repeat(32)}:t0001.0`,
        kind: "landmark_reached",
        tick: 1001,
        day: 3,
        time: "09:40",
        text: "抵達合成石龕。",
        params: { arrival_node: node, name: "合成石龕", lit_district: null, prose: "水聲。", artwork: null },
      }],
    },
  };
}

const wrappers = [];
afterEach(() => {
  while (wrappers.length) wrappers.pop().unmount();
  document.body.innerHTML = "";
  localStorage.clear();
}, 60000);

function helpers(h) {
  const find = (id) => h.w.find(`[data-testid="${id}"]`);
  const rites = () => h.sender.sent.actions.filter((a) => a.action_id === "explore.landmark_rite");
  const key = async (target, k, init = {}) => {
    target.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true, ...init }));
    await tick();
    await tick();
  };
  const pressR = () => key(document.activeElement ?? document.body, "r", { code: "KeyR" });
  const frameMode = () => h.w.get('[data-testid="elosern-vue-root"]').attributes("data-elosern-mode");
  const page = () => h.w.get('[data-testid="message-page"]');
  const plate = () => {
    const el = h.w.find('[data-testid="message-name-plate"] .message-window__plate-name');
    return el.exists() ? el.text() : null;
  };
  const commitRite = (panel) => {
    if (panel === null) {
      h.accept("ui_update", fx.update({ revision: h.next(), panels: {}, removed_panels: ["rite"] }));
    } else {
      h.publish({ rite: panel });
    }
    return tick();
  };
  const answer = async (overrides = {}) => {
    const request = rites().at(-1);
    const body = {
      protocol_version: 1,
      presentation_epoch: request.presentation_epoch,
      request_id: request.request_id,
      outcome: "success",
      code: "explore.landmark_rite",
      message: "完成",
      presentation_revision: h.store.view.revision,
      data: { delivery: DELIVERY, first_completion: true },
      ...overrides,
    };
    if (body.data === undefined) delete body.data;
    h.accept("ui_action_result", body);
    await tick();
    await tick();
  };
  return { ...h, find, rites, key, pressR, frameMode, page, plate, commitRite, answer };
}

/** The travel layout at a wilderness cell with its map adopted. */
async function travelStage() {
  const h = liveTravel({ wrappers, panels: walkPanels(CX, CY) });
  h.store.setMotionLevel("off");
  h.store.setTextSpeed("instant");
  await tick();
  await h.answerMap(walkArea(CX, CY));
  await tick();
  return helpers(h);
}

/** A settlement room (no travel layout). */
async function roomStage() {
  const h = liveTravel({ wrappers, subject: TOWN_SUBJECT, panels: panelsAt(TOWN_SUBJECT) });
  h.store.setMotionLevel("off");
  h.store.setTextSpeed("instant");
  await tick();
  return helpers(h);
}

/** Arrive, then approach the stage with Enter on the card. */
async function enterStage(s) {
  await s.commitRite(ritePanel());
  await s.key(s.find("rite-arrival-card").element, "Enter");
  expect(s.find("rite-panel").exists()).toBe(true);
}

describe("the rite arrival card", () => {
  it("opens instead of the generic landmark card and never lets it open for that arrival", async () => {
    const s = await travelStage();
    s.publish({ rite: ritePanel(), ...arrivalLog(walkNode(CX, CY)) });
    await tick();
    await tick();
    expect(s.find("rite-arrival-card").exists()).toBe(true);
    expect(s.find("landmark-card").exists()).toBe(false);
    expect(document.activeElement?.textContent).toContain("走近");
    // The rite card claimed the arrival: the generic card never opens later.
    expect(s.store.view.travel.arrival).toBeNull();
    await s.key(s.find("rite-arrival-card").element, "Escape");
    await s.commitRite(null);
    expect(s.find("landmark-card").exists()).toBe(false);
    expect(s.rites()).toHaveLength(0);
  });

  it("Escape closes it to the map with the return entry, and R reopens it as a revisit", async () => {
    const s = await travelStage();
    await s.commitRite(ritePanel());
    expect(s.find("rite-arrival-kicker").attributes("data-revisit")).toBe("false");
    expect(s.find("rite-entry").exists()).toBe(false);
    await s.key(s.find("rite-arrival-card").element, "Escape");
    expect(s.find("rite-arrival-card").exists()).toBe(false);
    expect(s.find("rite-entry").exists()).toBe(true);
    expect(s.find("rite-entry").text()).toContain("合成泉聲");
    expect(document.activeElement).toBe(s.find("travel-map").element);
    await s.pressR();
    expect(s.find("rite-arrival-card").exists()).toBe(true);
    expect(s.find("rite-arrival-kicker").attributes("data-revisit")).toBe("true");
    expect(s.find("rite-entry").exists()).toBe(false);
    expect(s.sender.sent.actions.filter((a) => a.action_id !== "map.view")).toHaveLength(0);
  });

  it("the entry reopens the card on click", async () => {
    const s = await travelStage();
    await s.commitRite(ritePanel());
    await s.key(s.find("rite-arrival-card").element, "Escape");
    await s.find("rite-entry").trigger("click");
    await tick();
    expect(s.find("rite-arrival-card").exists()).toBe(true);
    expect(s.find("rite-arrival-kicker").attributes("data-revisit")).toBe("true");
  });

  it("R does nothing while the card or the stage is open, or without the panel", async () => {
    const s = await travelStage();
    await s.pressR();
    expect(s.find("rite-arrival-card").exists()).toBe(false);
    await s.commitRite(ritePanel());
    await s.pressR();
    expect(s.find("rite-arrival-kicker").attributes("data-revisit")).toBe("false");
    await s.key(s.find("rite-arrival-card").element, "Enter");
    expect(s.find("rite-entry").exists()).toBe(false);
    await s.pressR();
    expect(s.find("rite-arrival-card").exists()).toBe(false);
    expect(s.find("rite-panel").exists()).toBe(true);
  });

  it("waits behind a sleep-handoff card and opens once it closes", async () => {
    const s = await travelStage();
    s.publish({ sleep_handoff: sleepHandoffPanel() });
    await tick();
    s.publish({ rite: ritePanel(), sleep_handoff: sleepHandoffPanel() });
    await tick();
    expect(s.find("sleep-handoff-card").exists()).toBe(true);
    expect(s.find("rite-arrival-card").exists()).toBe(false);
    expect(s.find("rite-entry").exists()).toBe(false);
    s.accept("ui_update", fx.update({ revision: s.next(), panels: {}, removed_panels: ["sleep_handoff"] }));
    await tick();
    await tick();
    expect(s.find("rite-arrival-card").exists()).toBe(true);
  });

  it("opens in a settlement room and leaving focuses the return entry", async () => {
    const s = await roomStage();
    expect(s.store.view.travel?.layout ?? false).toBe(false);
    await s.commitRite(ritePanel());
    expect(s.find("rite-arrival-card").exists()).toBe(true);
    await s.key(s.find("rite-arrival-card").element, "Escape");
    expect(s.find("rite-entry").exists()).toBe(true);
    expect(document.activeElement).toBe(s.find("rite-entry").element);
  });
});

describe("the rite stage", () => {
  it("approaching presents the stage over the exploration mode and sends nothing", async () => {
    const s = await travelStage();
    expect(s.find("travel-map").exists()).toBe(true);
    await enterStage(s);
    expect(s.store.view.mode).toBe("exploration");
    expect(s.frameMode()).toBe("dialogue");
    expect(s.w.find('[data-anchor="actor-left"] .companion-lineup').exists()).toBe(true);
    expect(s.find("rite-backdrop").exists()).toBe(true);
    expect(s.find("travel-map").exists()).toBe(false);
    expect(s.w.find("#action-dock").exists()).toBe(false);
    expect(s.find("travel-log").exists()).toBe(false);
    // The guardian's form under the guardian's name plate.
    expect(s.page().text()).toBe("水面映出的聲音，只在有人俯身時開口。");
    expect(s.plate()).toBe("合成泉聲");
    expect(s.find("rite-panel").element.contains(document.activeElement)).toBe(true);
    expect(s.rites()).toHaveLength(0);
    expect(s.sender.sent.actions.filter((a) => a.action_id !== "map.view")).toHaveLength(0);
  });

  it("one pick sends one rite, plays the delivery line by line and returns the panel", async () => {
    const s = await travelStage();
    await enterStage(s);
    const panelEl = s.find("rite-panel").element;
    await s.key(panelEl, "1");
    await s.key(panelEl, "1");
    expect(s.rites()).toHaveLength(1);
    expect(s.rites()[0].payload).toEqual({ option: "drink", member_id: null });
    expect(s.find("rite-panel").exists()).toBe(false);
    await s.answer();
    expect(s.find("rite-panel").exists()).toBe(false);
    const frames = [{ text: s.page().text(), plate: s.plate() }];
    s.page().element.focus();
    // Escape while the scene plays does not leave the stage.
    await s.key(s.page().element, "Escape");
    expect(s.frameMode()).toBe("dialogue");
    for (let line = 1; line < DELIVERY.lines.length; line += 1) {
      await s.key(s.page().element, "Enter");
      frames.push({ text: s.page().text(), plate: s.plate() });
    }
    expect(frames).toEqual([
      { text: "合成敘述之一。", plate: null },
      { text: "合成台詞之二。", plate: "你" },
      { text: "合成台詞之三。", plate: "合成泉聲" },
    ]);
    expect(s.find("rite-panel").exists()).toBe(false);
    await s.key(s.page().element, "Enter");
    expect(s.find("rite-panel").exists()).toBe(true);
    expect(s.find("rite-panel").element.contains(document.activeElement)).toBe(true);
    expect(s.page().text()).toBe("水面映出的聲音，只在有人俯身時開口。");
    expect(s.rites()).toHaveLength(1);
  });

  it("a refusal plays nothing and shows the panel again", async () => {
    const s = await travelStage();
    await enterStage(s);
    await s.key(s.find("rite-panel").element, "1");
    expect(s.find("rite-panel").exists()).toBe(false);
    await s.answer({ outcome: "rejected", code: "rite_refused", message: "現在無法進行。", data: undefined });
    expect(s.rites()).toHaveLength(1);
    expect(s.find("rite-panel").exists()).toBe(true);
    expect(s.page().text()).toBe("水面映出的聲音，只在有人俯身時開口。");
  });

  it("a delivery the shared player cannot present returns the panel instead of holding the stage", async () => {
    const s = await travelStage();
    await enterStage(s);
    await s.key(s.find("rite-panel").element, "1");
    await s.answer({ data: { delivery: { ...DELIVERY, kind: "opening" }, first_completion: false } });
    expect(s.find("rite-panel").exists()).toBe(true);
    expect(s.store.view.rite.playing).toBe(false);
  });

  it("Escape on the panel returns to the map with the entry and focus on the map", async () => {
    const s = await travelStage();
    await enterStage(s);
    await s.key(s.find("rite-panel").element, "Escape");
    expect(s.find("rite-panel").exists()).toBe(false);
    expect(s.find("rite-backdrop").exists()).toBe(false);
    expect(s.find("travel-map").exists()).toBe(true);
    expect(s.frameMode()).toBe("exploration");
    expect(s.find("rite-entry").exists()).toBe(true);
    expect(document.activeElement).toBe(s.find("travel-map").element);
    expect(s.sender.sent.actions.filter((a) => a.action_id !== "map.view")).toHaveLength(0);
  });

  it("a withdrawn panel drops the stage, the panel, the backdrop and the entry", async () => {
    const s = await travelStage();
    await enterStage(s);
    await s.commitRite(null);
    await tick();
    expect(s.find("rite-panel").exists()).toBe(false);
    expect(s.find("rite-backdrop").exists()).toBe(false);
    expect(s.find("rite-entry").exists()).toBe(false);
    expect(s.find("travel-map").exists()).toBe(true);
    expect(s.frameMode()).toBe("exploration");
  });

  it("a playing scene stops when the panel is withdrawn", async () => {
    const s = await travelStage();
    await enterStage(s);
    await s.key(s.find("rite-panel").element, "1");
    await s.answer();
    expect(s.page().text()).toBe("合成敘述之一。");
    await s.commitRite(null);
    await tick();
    expect(s.frameMode()).toBe("exploration");
    expect(s.find("rite-backdrop").exists()).toBe(false);
    expect(s.find("travel-map").exists()).toBe(true);
  });
});
