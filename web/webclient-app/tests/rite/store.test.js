// landmark-rite-store (design D2): the rite group of the real composed store
// behind a fake sender, fed synthetic committed `rite` panels through the
// real wire validators. No rite component is mounted; the one mounted suite
// asserts the centred-card predicate through the travel store's walk refusal.
import { afterEach, describe, expect, it } from "vitest";
import { DIALOGUE_PANEL_SAMPLE } from "../../stories/fixtures/dialogue_panels.js";
import { RITE_PARTY, ritePanel } from "../../stories/fixtures/rite.js";
import { fx, liveTravel, panelsAt, tick, walkArea, walkCapacity, walkPanels, WILD_SUBJECT } from "../travel/support.js";

const wrappers = [];
afterEach(() => {
  while (wrappers.length) wrappers.pop().unmount();
  document.body.innerHTML = "";
});

const OTHER = ritePanel({
  district: { key: "synthetic_lowlands", name: "合成低地", landmark: "合成石碑", lit: false },
});

const DELIVERY = {
  kind: "formal",
  delivery_id: "rite:synthetic_highlands:drink:1",
  scene_id: "rite.synthetic.drink.self",
  scene_revision: "r1",
  actor_name: "你",
  guardian_name: "合成泉聲",
  lines: [
    { kind: "narration", text: "合成敘述之一。" },
    { kind: "speech", speaker: "host", text: "合成台詞之二。" },
  ],
};

/** A store whose session began at a wilderness node, with or without the panel. */
function harness({ rite = null } = {}) {
  const h = liveTravel({ mounted: false, panels: panelsAt(WILD_SUBJECT, rite ? { rite } : {}) });
  const rites = () => h.sender.sent.actions.filter((a) => a.action_id === "explore.landmark_rite");
  const view = () => h.store.view.rite;
  /** Publish the panel (or remove it with null) at the next revision. */
  const commitRite = (panel) => {
    if (panel === null) {
      const revision = h.next();
      h.accept("ui_update", fx.update({ revision, panels: {}, removed_panels: ["rite"] }));
      return revision;
    }
    return h.publish({ rite: panel });
  };
  /** The result of the last rite request at the committed revision. */
  const answer = (overrides = {}) => {
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
    // A refusal carries no data slot at all.
    if (body.data === undefined) delete body.data;
    h.accept("ui_action_result", body);
  };
  /** Arrive (card opens) and approach the stage. */
  const onStage = (panel = ritePanel()) => {
    commitRite(panel);
    expect(view().phase).toBe("card");
    expect(h.store.approachRite()).toBe(true);
    expect(view().phase).toBe("stage");
  };
  return { ...h, rites, view, commitRite, answer, onStage };
}

describe("rite arrival", () => {
  it("a session's first snapshot on a landmark stays closed", () => {
    const h = harness({ rite: ritePanel() });
    expect(h.view().phase).toBe("closed");
    expect(h.view().panel.district.key).toBe("synthetic_highlands");
    // A later commit of the same district still opens nothing.
    h.commitRite(ritePanel());
    expect(h.view().phase).toBe("closed");
  });

  it("opens on arrival, stays dismissed for the same district and reopens after a return", () => {
    const h = harness();
    expect(h.view()).toMatchObject({ panel: null, phase: "closed" });
    h.commitRite(ritePanel());
    expect(h.view()).toMatchObject({ phase: "card", revisit: false });
    expect(h.store.leaveRite()).toBe(true);
    h.commitRite(ritePanel());
    expect(h.view().phase).toBe("closed");
    h.commitRite(null);
    expect(h.view().panel).toBe(null);
    h.commitRite(ritePanel());
    expect(h.view().phase).toBe("card");
  });

  it("another district opens the card again", () => {
    const h = harness({ rite: ritePanel() });
    h.commitRite(OTHER);
    expect(h.view().phase).toBe("card");
    expect(h.view().panel.district.key).toBe("synthetic_lowlands");
  });

  it("a new session on a landmark starts closed", () => {
    const h = harness();
    h.commitRite(ritePanel());
    expect(h.view().phase).toBe("card");
    h.store.setConnected(false);
    h.store.beginTransport(2);
    h.store.setConnected(true);
    const outcome = h.store.receive(2, "ui_snapshot", [fx.snapshot({ presentation_epoch: fx.EPOCH_B, panels: panelsAt(WILD_SUBJECT, { rite: ritePanel() }) })], {});
    expect(outcome.accepted).toBe(true);
    expect(h.view()).toMatchObject({ phase: "closed", revisit: false, pending: false, delivery: null });
    expect(h.view().panel).not.toBe(null);
  });

  it("a session that begins outside exploration on a landmark opens nothing on return", () => {
    const h = harness();
    h.store.setConnected(false);
    h.store.beginTransport(2);
    h.store.setConnected(true);
    const first = fx.snapshot({
      presentation_epoch: fx.EPOCH_B,
      mode: "dialogue",
      panels: panelsAt(WILD_SUBJECT, { rite: ritePanel(), dialogue: DIALOGUE_PANEL_SAMPLE }),
    });
    expect(h.store.receive(2, "ui_snapshot", [first], {}).accepted).toBe(true);
    expect(h.view().phase).toBe("closed");
    const back = fx.update({
      presentation_epoch: fx.EPOCH_B,
      revision: 2,
      panels: { rite: ritePanel() },
      removed_panels: ["dialogue"],
    });
    expect(h.store.receive(2, "ui_update", [back], {}).accepted).toBe(true);
    expect(h.store.view.mode).toBe("exploration");
    expect(h.view().phase).toBe("closed");
  });
});

describe("rite transitions", () => {
  it("approach, leave and reopen are local and send nothing", () => {
    const h = harness();
    const before = h.sender.sent.actions.length;
    h.onStage();
    expect(h.store.leaveRite()).toBe(true);
    expect(h.view()).toMatchObject({ phase: "closed", revisit: false });
    expect(h.store.openRiteCard()).toBe(true);
    expect(h.view()).toMatchObject({ phase: "card", revisit: true });
    expect(h.store.approachRite()).toBe(true);
    expect(h.view()).toMatchObject({ phase: "stage", revisit: true });
    expect(h.sender.sent.actions.length).toBe(before);
  });

  it("each transition is refused in the wrong phase", () => {
    const h = harness();
    // No panel: nothing opens.
    expect(h.store.openRiteCard()).toBe(false);
    expect(h.store.approachRite()).toBe(false);
    expect(h.store.leaveRite()).toBe(false);
    h.commitRite(ritePanel());
    expect(h.store.openRiteCard()).toBe(false);
    expect(h.store.approachRite()).toBe(true);
    expect(h.store.approachRite()).toBe(false);
    expect(h.store.openRiteCard()).toBe(false);
    expect(h.store.finishRiteScene()).toBe(false);
    expect(h.view().phase).toBe("stage");
  });
});

describe("performing a rite", () => {
  it("sends exactly one action with the option and a null member", () => {
    const h = harness();
    expect(h.store.performRite("drink")).toBe(false); // not on the stage
    h.onStage();
    expect(h.store.performRite("drink")).toBe(true);
    expect(h.view().pending).toBe(true);
    expect(h.store.performRite("drink")).toBe(false);
    expect(h.store.performRite("bathe")).toBe(false);
    expect(h.store.leaveRite()).toBe(false);
    expect(h.rites()).toHaveLength(1);
    expect(h.rites()[0].payload).toEqual({ option: "drink", member_id: null });
  });

  it("an unknown option sends nothing", () => {
    const h = harness();
    h.onStage();
    expect(h.store.performRite("swim")).toBe(false);
    expect(h.rites()).toHaveLength(0);
    expect(h.view().pending).toBe(false);
  });

  it("a disconnected state sends nothing", () => {
    const h = harness();
    h.onStage();
    h.store.setConnected(false);
    expect(h.view().phase).toBe("stage");
    expect(h.store.performRite("drink")).toBe(false);
    expect(h.rites()).toHaveLength(0);
  });

  it("a locked state sends nothing", () => {
    const h = harness();
    h.onStage();
    // A revision gap requests recovery: mutations lock, the panel stays.
    const gap = h.store.receive(h.store.view.generation, "ui_update", [fx.update({ revision: h.next() + 1, base_revision: h.next(), panels: {} })], {});
    expect(gap.accepted).toBe(false);
    expect(h.store.view.mutationsLocked).toBe(true);
    expect(h.view().phase).toBe("stage");
    expect(h.store.performRite("drink")).toBe(false);
    expect(h.rites()).toHaveLength(0);
  });
});

describe("rite result adoption", () => {
  it("plays the pending request's delivery, ignores a foreign result and plays nothing on a refusal", () => {
    const h = harness();
    h.onStage();
    expect(h.store.performRite("drink")).toBe(true);
    // A result for another request changes nothing.
    h.accept("ui_action_result", fx.actionResult({ request_id: "session:999", presentation_revision: h.store.view.revision }));
    expect(h.view()).toMatchObject({ pending: true, delivery: null, playing: false });
    h.answer();
    expect(h.view()).toMatchObject({ phase: "stage", pending: false, playing: true });
    expect(h.view().delivery).toEqual(DELIVERY);
    expect(h.store.leaveRite()).toBe(false);
    expect(h.store.performRite("bathe")).toBe(false);
    expect(h.store.finishRiteScene()).toBe(true);
    expect(h.view()).toMatchObject({ phase: "stage", playing: false, delivery: null });

    // A second request is refused by the server.
    expect(h.store.performRite("bathe")).toBe(true);
    h.answer({ outcome: "rejected", code: "rite_unknown_option", message: "沒有這個儀式。", data: undefined });
    expect(h.view()).toMatchObject({ phase: "stage", pending: false, delivery: null, playing: false });
    expect(h.store.leaveRite()).toBe(true);
    expect(h.rites()).toHaveLength(2);
  });

  it("a success without a delivery object clears the request and plays nothing", () => {
    const h = harness();
    h.onStage();
    expect(h.store.performRite("drink")).toBe(true);
    h.answer({ data: { first_completion: false } });
    expect(h.view()).toMatchObject({ pending: false, delivery: null, playing: false });
  });
});

describe("the newly lit mark", () => {
  /** Perform on the stage and answer with `first_completion`. */
  const performed = (h, firstCompletion, key = "drink") => {
    expect(h.store.performRite(key)).toBe(true);
    h.answer({ data: { delivery: DELIVERY, first_completion: firstCompletion } });
  };

  it("follows the adopted success result's first completion", () => {
    const h = harness();
    h.onStage();
    expect(h.view().newlyLit).toBe(false);
    performed(h, true);
    expect(h.view()).toMatchObject({ newlyLit: true, playing: true });
    // The scene finishing keeps it: the stage names the district now.
    expect(h.store.finishRiteScene()).toBe(true);
    expect(h.view().newlyLit).toBe(true);
    // A new perform clears it at dispatch; a repeat's result leaves it clear.
    expect(h.store.performRite("drink")).toBe(true);
    expect(h.view().newlyLit).toBe(false);
    h.answer({ data: { delivery: DELIVERY, first_completion: false } });
    expect(h.view().newlyLit).toBe(false);
  });

  it("a refused result and a foreign result set nothing", () => {
    const h = harness();
    h.onStage();
    expect(h.store.performRite("drink")).toBe(true);
    h.accept("ui_action_result", fx.actionResult({ request_id: "session:999", presentation_revision: h.store.view.revision }));
    expect(h.view().newlyLit).toBe(false);
    h.answer({ outcome: "rejected", code: "rite_unknown_option", message: "沒有這個儀式。", data: undefined });
    expect(h.view().newlyLit).toBe(false);
  });

  it("a perform refused locally keeps it", () => {
    const h = harness();
    h.onStage();
    performed(h, true);
    h.store.finishRiteScene();
    expect(h.store.performRite("swim")).toBe(false);
    h.store.setConnected(false);
    expect(h.store.performRite("drink")).toBe(false);
    expect(h.view().newlyLit).toBe(true);
  });

  it("leaving and re-entering the stage clears it", () => {
    const h = harness();
    h.onStage();
    performed(h, true);
    h.store.finishRiteScene();
    expect(h.store.leaveRite()).toBe(true);
    expect(h.view().newlyLit).toBe(false);
    expect(h.store.openRiteCard()).toBe(true);
    expect(h.store.approachRite()).toBe(true);
    expect(h.view().newlyLit).toBe(false);
  });

  it("the panel becoming unavailable clears it", () => {
    const h = harness();
    h.onStage();
    performed(h, true);
    h.store.finishRiteScene();
    h.commitRite(null);
    expect(h.view().newlyLit).toBe(false);
  });
});

describe("rite reset", () => {
  it("the panel becoming unavailable closes the stage with no request and no delivery", () => {
    const h = harness();
    h.onStage();
    expect(h.store.performRite("drink")).toBe(true);
    h.commitRite(null);
    expect(h.view()).toEqual({
      panel: null, phase: "closed", revisit: false, pending: false, delivery: null, playing: false,
      performerId: "self", canSwitch: false, newlyLit: false,
    });
    // The stale result arriving later adopts nothing.
    h.answer();
    expect(h.view()).toMatchObject({ phase: "closed", delivery: null, playing: false });
  });

  it("the mode leaving exploration closes the stage", () => {
    const h = harness();
    h.onStage();
    h.publish({ rite: ritePanel(), dialogue: DIALOGUE_PANEL_SAMPLE }, { mode: "dialogue" });
    expect(h.view()).toMatchObject({ phase: "closed", pending: false, delivery: null, playing: false });
  });
});

describe("rite performer picking", () => {
  const PARTY = ritePanel({ performers: RITE_PARTY });

  it("is offered only with another performer and an option a companion may perform", () => {
    const h = harness();
    h.onStage(ritePanel());
    expect(h.view().canSwitch).toBe(false);
    h.commitRite(ritePanel({ performers: RITE_PARTY, options: [{ key: "bathe", label: "浸入池中", companion: false }] }));
    expect(h.view().canSwitch).toBe(false);
    expect(h.store.pickRitePerformer("7")).toBe(false);
    expect(h.store.stepRitePerformer(1)).toBe(false);
    h.commitRite(PARTY);
    expect(h.view()).toMatchObject({ canSwitch: true, performerId: "self" });
  });

  it("picks a listed performer and refuses an unlisted one", () => {
    const h = harness();
    h.onStage(PARTY);
    expect(h.store.pickRitePerformer("8")).toBe(true);
    expect(h.view().performerId).toBe("8");
    expect(h.store.pickRitePerformer("8")).toBe(true);
    expect(h.store.pickRitePerformer("99")).toBe(false);
    expect(h.store.pickRitePerformer(8)).toBe(false);
    expect(h.view().performerId).toBe("8");
    expect(h.store.pickRitePerformer("self")).toBe(true);
    expect(h.view().performerId).toBe("self");
  });

  it("steps through the performers, wrapping in both directions", () => {
    const h = harness();
    h.onStage(PARTY);
    const forward = [];
    for (let i = 0; i < 3; i += 1) {
      expect(h.store.stepRitePerformer(1)).toBe(true);
      forward.push(h.view().performerId);
    }
    expect(forward).toEqual(["7", "8", "self"]);
    expect(h.store.stepRitePerformer(-1)).toBe(true);
    expect(h.view().performerId).toBe("8");
    expect(h.store.stepRitePerformer(0)).toBe(false);
    expect(h.view().performerId).toBe("8");
  });

  it("refuses picking outside the stage and while a rite is pending or playing", () => {
    const h = harness();
    h.commitRite(PARTY);
    expect(h.view().phase).toBe("card");
    expect(h.store.pickRitePerformer("7")).toBe(false);
    expect(h.store.stepRitePerformer(1)).toBe(false);
    expect(h.store.approachRite()).toBe(true);
    expect(h.store.performRite("drink")).toBe(true);
    expect(h.store.pickRitePerformer("7")).toBe(false);
    expect(h.store.stepRitePerformer(1)).toBe(false);
    h.answer();
    expect(h.view().playing).toBe(true);
    expect(h.store.pickRitePerformer("7")).toBe(false);
    expect(h.store.stepRitePerformer(1)).toBe(false);
    expect(h.view().performerId).toBe("self");
  });

  it("every entry to the stage starts with the controlled character", () => {
    const h = harness();
    h.onStage(PARTY);
    expect(h.store.pickRitePerformer("7")).toBe(true);
    expect(h.store.leaveRite()).toBe(true);
    expect(h.view().performerId).toBe("self");
    expect(h.store.openRiteCard()).toBe(true);
    expect(h.store.approachRite()).toBe(true);
    expect(h.view().performerId).toBe("self");
  });

  it("a committed panel that no longer lists the picked performer returns the pick", () => {
    const h = harness();
    h.onStage(PARTY);
    expect(h.store.pickRitePerformer("8")).toBe(true);
    h.commitRite(ritePanel({ performers: RITE_PARTY.slice(0, 2) }));
    expect(h.view()).toMatchObject({ phase: "stage", performerId: "self" });
    expect(h.store.pickRitePerformer("7")).toBe(true);
    h.commitRite(ritePanel({ performers: RITE_PARTY.slice(0, 2) }));
    expect(h.view().performerId).toBe("7");
    h.commitRite(ritePanel());
    expect(h.view().performerId).toBe("self");
  });

  it("sends the picked performer's member id, and nothing for a companion's solo-only option", () => {
    const h = harness();
    h.onStage(PARTY);
    expect(h.store.pickRitePerformer("7")).toBe(true);
    expect(h.store.performRite("bathe")).toBe(false);
    expect(h.rites()).toHaveLength(0);
    expect(h.view().pending).toBe(false);
    expect(h.store.performRite("drink")).toBe(true);
    expect(h.rites()).toHaveLength(1);
    expect(h.rites()[0].payload).toEqual({ option: "drink", member_id: 7 });
  });

  it("a possessed companion in the first row sends a null member and may not pick a solo-only option", () => {
    const h = harness();
    const possessed = [
      { member_id: null, name: "合成同伴", owner: false },
      { member_id: 5, name: "合成旅人", owner: true },
    ];
    h.onStage(ritePanel({ performers: possessed }));
    expect(h.store.performRite("bathe")).toBe(false);
    expect(h.store.pickRitePerformer("5")).toBe(true);
    expect(h.store.performRite("bathe")).toBe(true);
    expect(h.rites()[0].payload).toEqual({ option: "bathe", member_id: 5 });
  });
});

describe("an open rite is a centred card", () => {
  const CX = 60;
  const CY = 80;

  it("refuses a walk step while the card or the stage is open", async () => {
    const h = liveTravel({ wrappers, panels: walkPanels(CX, CY, { capacity: walkCapacity() }) });
    await tick();
    await h.answerMap(walkArea(CX, CY));
    const moves = () => h.sender.sent.actions.filter((a) => a.action_id === "explore.move");
    h.publish({ rite: ritePanel() });
    await tick();
    expect(h.store.view.rite.phase).toBe("card");
    expect(h.store.stepTravel("east")).toMatchObject({ sent: false, reason: "waiting" });
    expect(h.store.approachRite()).toBe(true);
    expect(h.store.stepTravel("east")).toMatchObject({ sent: false, reason: "waiting" });
    expect(moves()).toHaveLength(0);
    expect(h.store.leaveRite()).toBe(true);
    await tick();
    expect(h.store.stepTravel("east")).toMatchObject({ sent: true });
    expect(moves()).toHaveLength(1);
  });
});
