// authored-dialogue-reading-client: the memory-only formal-completion queue.
//
// Drives the REAL composed store (`useElosernStore`) over committed dialogue
// panels and exact `ui_action_result` envelopes, exactly like the transport
// seam would. The queue is memory-only: no localStorage, IndexedDB or
// beforeunload exists here or in the module, and a fresh store instance has no
// pending state (the AppClient/browser reload scenario covers the user
// journey).
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useElosernStore } from "../../stores/elosern.js";
import { DIALOGUE_ACK_TIMEOUT_MS } from "../../stores/elosern/dialogue_reading.js";
import { dialogueViewModel } from "../../stores/dialogue-view.js";
import * as fx from "../store/protocol_fixtures.js";
import {
  choiceRow,
  dialoguePanel as v3Panel,
  narration,
  sceneDelivery,
  speech,
} from "../support/dialogue_panel.js";

const HOST = 7;
const CTX = "ctx-1";
const LONG_TOPIC = `g.${"r".repeat(40)}.${"k".repeat(2048 - 43)}`;

function panel(overrides = {}) {
  return v3Panel({
    hostId: HOST,
    hostName: "店長",
    actorId: 1,
    actorName: "旅人",
    contextId: CTX,
    line: "歡迎來到西風酒館。",
    keywords: ["news", "town"],
    labels: ["最近有什麼消息？", "關於這座城鎮"],
    ...overrides,
  });
}

const LINES = [speech("actor", "最近有什麼消息？"), speech("host", "北岸大道最近不太平。")];

function formal(lines = LINES, overrides = {}) {
  return sceneDelivery(lines, {
    deliveryId: "dlv-1",
    contextId: CTX,
    topicId: "host.news",
    sceneId: "host.news_scene",
    revision: "r1",
    kind: "formal",
    ...overrides,
  });
}

function detail(delivery, npcId = HOST) {
  return {
    npc_id: npcId,
    delivery_id: delivery.delivery_id,
    context_id: delivery.context_id,
    topic_id: delivery.topic_id,
    scene_id: delivery.scene_id,
    scene_revision: delivery.scene_revision,
    kind: delivery.kind,
  };
}

function harness() {
  setActivePinia(createPinia());
  const store = useElosernStore();
  const sender = fx.createFakeSender();
  store.setSender(sender);
  store.setTextSpeed?.("instant");
  let revision = 1;
  let generation = 1;
  let epoch = fx.EPOCH_A;
  store.beginTransport(generation);
  store.setConnected(true);
  store.setLoggedIn(true);

  function commit(mode, dialogue = null, extraPanels = {}) {
    const panels = {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      context_actions: fx.explorationActions(),
      local_map: fx.localMapPanel(),
      ...extraPanels,
    };
    if (dialogue) {
      panels.dialogue = dialogue;
    }
    const response = store.receive(
      generation,
      "ui_snapshot",
      [fx.snapshot({ revision, mode, panels, presentation_epoch: epoch })],
      {},
    );
    expect(response.accepted, JSON.stringify(response)).toBe(true);
    revision += 1;
  }

  function reconnect(nextEpoch = fx.EPOCH_B) {
    generation += 1;
    epoch = nextEpoch;
    store.beginTransport(generation);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
  }

  function respondTo(requestId, overrides = {}) {
    const response = store.receive(
      generation,
      "ui_action_result",
      [
        fx.actionResult({
          request_id: requestId,
          presentation_epoch: epoch,
          presentation_revision: store.view.revision,
          ...overrides,
        }),
      ],
      {},
    );
    expect(response.accepted, JSON.stringify(response)).toBe(true);
  }

  function respond(overrides = {}) {
    const envelope = sender.sent.actions[sender.sent.actions.length - 1];
    expect(envelope, "an acknowledgement must be on the wire").toBeTruthy();
    respondTo(envelope.request_id, overrides);
    return envelope;
  }

  return {
    store,
    sender,
    commit,
    reconnect,
    respond,
    respondTo,
    get generation() {
      return generation;
    },
  };
}

function actions(sender) {
  return sender.sent.actions;
}

describe("the memory-only dialogue completion queue", () => {
  let h;
  beforeEach(() => {
    h = harness();
    h.commit("dialogue", panel());
  });

  it("admits exactly one exact acknowledgement for a formal finish and dedups repeats", () => {
    const delivery = formal();
    const key = h.store.finishDialogueDelivery(detail(delivery));
    expect(key).toBe(JSON.stringify([CTX, "dlv-1"]));
    expect(actions(h.sender)).toHaveLength(1);
    expect(actions(h.sender)[0]).toMatchObject({
      protocol_version: 1,
      action_id: "explore.dialogue_complete",
      payload: {
        npc_id: HOST,
        delivery_id: "dlv-1",
        context_id: CTX,
        topic_id: "host.news",
        scene_revision: "r1",
      },
    });
    expect(Object.keys(actions(h.sender)[0].payload).sort()).toEqual([
      "context_id",
      "delivery_id",
      "npc_id",
      "scene_revision",
      "topic_id",
    ]);
    expect(h.store.view.dialogueReading.pendingCount).toBe(1);
    expect(h.store.view.dialogueReading.pending[0]).toMatchObject({ status: "sending" });

    // A repeated finish (the same final activation delivered twice) never
    // admits or sends a second acknowledgement.
    expect(h.store.finishDialogueDelivery(detail(delivery))).toBe(key);
    expect(actions(h.sender)).toHaveLength(1);
    expect(h.store.view.dialogueReading.pendingCount).toBe(1);
  });

  it("preserves an opaque generated topic id untruncated through the payload", () => {
    const delivery = formal(LINES, { topicId: LONG_TOPIC, sceneId: LONG_TOPIC + "_scene" });
    h.store.finishDialogueDelivery(detail(delivery));
    expect(actions(h.sender)[0].payload.topic_id).toBe(LONG_TOPIC);
    expect(actions(h.sender)[0].payload.topic_id).toHaveLength(2048);
    expect(h.store.view.dialogueReading.pending[0].topicId).toBe(LONG_TOPIC);
  });

  it("never queues a refusal, opening, service or freeform finish", () => {
    for (const kind of ["refusal", "opening", "service"]) {
      expect(
        h.store.finishDialogueDelivery(detail(formal(LINES, { deliveryId: `dlv-${kind}`, kind }))),
      ).toBeNull();
    }
    expect(h.store.finishDialogueDelivery(detail({ ...formal(), topic_id: null }))).toBeNull();
    expect(actions(h.sender)).toHaveLength(0);
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
  });

  it("clears pending only for the exact saved response identity", () => {
    h.store.finishDialogueDelivery(detail(formal()));
    const envelope = actions(h.sender)[0];

    // A foreign result (a different request) never clears this entry.
    h.store.receive(
      h.generation,
      "ui_action_result",
      [fx.actionResult({ request_id: "session:99", presentation_revision: h.store.view.revision })],
      {},
    );
    expect(h.store.view.dialogueReading.pendingCount).toBe(1);

    h.respond({ code: "dialogue_completed", outcome: "success" });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
    expect(h.store.view.dialogueReading.savedTopicIds).toEqual(["host.news"]);
    expect(envelope.payload.topic_id).toBe("host.news");

    // A duplicate delivery of the same result is inert (no second save).
    h.store.receive(
      h.generation,
      "ui_action_result",
      [
        fx.actionResult({
          request_id: envelope.request_id,
          presentation_revision: h.store.view.revision,
        }),
      ],
      {},
    );
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
  });

  it("discards a logically stale entry and refreshes canonical state", () => {
    h.store.finishDialogueDelivery(detail(formal()));
    h.respond({
      outcome: "rejected",
      code: "dialogue_receipt_stale",
      message: "對話情境已過期。",
    });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
    expect(h.store.view.dialogueReading.retryable).toBe(false);
    expect(h.sender.sent.syncs).toBe(1);
  });

  it("keeps an operational failure and retries the identical payload explicitly", () => {
    h.store.finishDialogueDelivery(detail(formal()));
    h.respond({ outcome: "rejected", code: "busy", message: "另一項操作正在進行中" });
    expect(h.store.view.dialogueReading.pendingCount).toBe(1);
    expect(h.store.view.dialogueReading.retryable).toBe(true);
    expect(h.store.view.dialogueReading.sending).toBe(false);
    expect(actions(h.sender)).toHaveLength(1);

    expect(h.store.retryDialogueReading()).toBe(true);
    expect(actions(h.sender)).toHaveLength(2);
    // The retry is a fresh attempt with a fresh request id and the same
    // exact payload.
    expect(actions(h.sender)[1].request_id).not.toBe(actions(h.sender)[0].request_id);
    expect(actions(h.sender)[1].payload).toEqual(actions(h.sender)[0].payload);
    h.respond({ code: "dialogue_completed" });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
  });

  it("leaves a synchronous transport error pending and retryable", () => {
    let failNext = true;
    const original = h.sender.sendAction;
    h.sender.sendAction = (envelope) => {
      if (failNext) {
        failNext = false;
        throw new Error("socket closed");
      }
      original(envelope);
    };
    h.store.finishDialogueDelivery(detail(formal()));
    expect(actions(h.sender)).toHaveLength(0);
    expect(h.store.view.dialogueReading.pendingCount).toBe(1);
    expect(h.store.view.dialogueReading.retryable).toBe(true);
    expect(h.store.view.dialogueReading.sending).toBe(false);

    h.store.retryDialogueReading();
    expect(actions(h.sender)).toHaveLength(1);
    h.respond({ code: "dialogue_completed" });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
  });

  it("reveals the pre-delivered public successor and serializes its acknowledgement after the predecessor", () => {
    const root = formal();
    const child = formal([speech("host", "接續的話。")], {
      deliveryId: "dlv-child",
      topicId: "host.news_child",
      sceneId: "host.news_child_scene",
      revision: "r2",
    });
    h.commit(
      "dialogue",
      panel({
        delivery: root,
        pureChain: [{ delivery: child, predecessors: ["host.news"] }],
      }),
    );

    h.store.finishDialogueDelivery(detail(root));
    expect(actions(h.sender)).toHaveLength(1);
    expect(actions(h.sender)[0].payload.delivery_id).toBe("dlv-1");
    const revealed = h.store.view.dialogueReading.revealed;
    expect(revealed).toMatchObject({
      deliveryId: "dlv-child",
      topicId: "host.news_child",
      predecessors: ["host.news"],
    });
    // The revealed delivery is what the player now reads.
    const vm = dialogueViewModel(h.store.view.panels.dialogue, h.store.view.dialogueReading);
    expect(vm.delivery.delivery_id).toBe("dlv-child");

    h.store.finishDialogueDelivery(detail(child));
    expect(h.store.view.dialogueReading.pendingCount).toBe(2);
    // The successor waits for the saved predecessor: still one envelope.
    expect(actions(h.sender)).toHaveLength(1);

    h.respond({ code: "dialogue_completed" }); // root saved
    expect(actions(h.sender)).toHaveLength(2);
    expect(actions(h.sender)[1].payload).toMatchObject({
      delivery_id: "dlv-child",
      topic_id: "host.news_child",
      scene_revision: "r2",
    });
    h.respond({ code: "dialogue_completed" }); // child saved
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
    expect(h.store.view.dialogueReading.savedTopicIds).toEqual(
      expect.arrayContaining(["host.news", "host.news_child"]),
    );
  });

  it("advances a three-node chain predecessor-first while the root acknowledgement is still failed", () => {
    const a = formal([speech("host", "一。")], { deliveryId: "dlv-a", topicId: "t.a", revision: "r1" });
    const b = formal([speech("host", "二。")], { deliveryId: "dlv-b", topicId: "t.b", revision: "r1" });
    const c = formal([speech("host", "三。")], { deliveryId: "dlv-c", topicId: "t.c", revision: "r1" });
    h.commit(
      "dialogue",
      panel({
        delivery: a,
        pureChain: [
          { delivery: b, predecessors: ["t.a"] },
          { delivery: c, predecessors: ["t.b"] },
        ],
      }),
    );
    h.store.finishDialogueDelivery(detail(a));
    expect(h.store.view.dialogueReading.revealed.topicId).toBe("t.b");

    // The root acknowledgement fails operationally: the chain still advances
    // locally, but nothing after the root is sent.
    h.respond({ outcome: "rejected", code: "busy", message: "另一項操作正在進行中" });
    h.store.finishDialogueDelivery(detail(b));
    expect(h.store.view.dialogueReading.revealed.topicId).toBe("t.c");
    h.store.finishDialogueDelivery(detail(c));
    expect(h.store.view.dialogueReading.pendingCount).toBe(3);
    expect(actions(h.sender)).toHaveLength(1);

    h.store.retryDialogueReading();
    expect(actions(h.sender)).toHaveLength(2);
    expect(actions(h.sender)[1].payload.topic_id).toBe("t.a");
    h.respond({ code: "dialogue_completed" }); // a saved
    expect(actions(h.sender)).toHaveLength(3);
    expect(actions(h.sender)[2].payload.topic_id).toBe("t.b");
    h.respond({ code: "dialogue_completed" }); // b saved
    expect(actions(h.sender)).toHaveLength(4);
    expect(actions(h.sender)[3].payload.topic_id).toBe("t.c");
    h.respond({ code: "dialogue_completed" });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
    // Every acknowledgement was sent in predecessor order, exactly once.
    expect(actions(h.sender).map((envelope) => envelope.payload.topic_id)).toEqual([
      "t.a",
      "t.a",
      "t.b",
      "t.c",
    ]);
  });

  it("keeps a predecessor_unread successor queued until the predecessor saves", () => {
    const a = formal(LINES, { deliveryId: "dlv-a", topicId: "t.a" });
    const b = formal(LINES, { deliveryId: "dlv-b", topicId: "t.b" });
    h.commit("dialogue", panel({ delivery: a, pureChain: [{ delivery: b, predecessors: ["t.a"] }] }));
    h.store.finishDialogueDelivery(detail(a));
    h.store.finishDialogueDelivery(detail(b));
    expect(actions(h.sender)).toHaveLength(1);

    // Root saved -> the successor is sent; a defensive server answer keeps it
    // queued instead of spinning, and the canonical save later releases it.
    h.respond({ code: "dialogue_completed" });
    expect(actions(h.sender)).toHaveLength(2);
    h.respond({
      outcome: "rejected",
      code: "dialogue_predecessor_unread",
      message: "前面的話還沒讀完。",
    });
    expect(h.store.view.dialogueReading.pendingCount).toBe(1);
    expect(actions(h.sender)).toHaveLength(2);
    h.commit(
      "dialogue",
      panel({
        delivery: a,
        pureChain: [{ delivery: b, predecessors: ["t.a"] }],
        readingRevision: 2,
        completedTopicIds: ["t.a"],
      }),
    );
    expect(actions(h.sender)).toHaveLength(3);
    expect(actions(h.sender)[2].payload.topic_id).toBe("t.b");
    h.respond({ code: "dialogue_completed" });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
  });

  it("keeps the reveal and the playing delivery on a reading-revision-only refresh", () => {
    const root = formal();
    const child = formal([speech("host", "接續。")], {
      deliveryId: "dlv-child",
      topicId: "t.child",
    });
    h.commit("dialogue", panel({ delivery: root, pureChain: [{ delivery: child, predecessors: ["host.news"] }] }));
    h.store.finishDialogueDelivery(detail(root));
    h.respond({ code: "dialogue_completed" });
    // The same session delivery with a newer reading revision and saved root.
    h.commit(
      "dialogue",
      panel({
        delivery: root,
        pureChain: [{ delivery: child, predecessors: ["host.news"] }],
        readingRevision: 1,
        completedTopicIds: ["host.news"],
      }),
    );
    const reading = h.store.view.dialogueReading;
    expect(reading.revealed.deliveryId).toBe("dlv-child");
    expect(reading.readingRevision).toBe(1);
    expect(reading.completedTopicIds).toEqual(["host.news"]);
    const vm = dialogueViewModel(h.store.view.panels.dialogue, reading);
    expect(vm.delivery.delivery_id).toBe("dlv-child");
    expect(vm.readingRevision).toBe(1);
    expect(actions(h.sender)).toHaveLength(1);
  });

  it("does not let another connection's saved update steal the current line or restart it", () => {
    const root = formal();
    const child = formal([speech("host", "接續。")], {
      deliveryId: "dlv-child",
      topicId: "t.child",
    });
    h.commit("dialogue", panel({ delivery: root, pureChain: [{ delivery: child, predecessors: ["host.news"] }] }));
    h.store.finishDialogueDelivery(detail(root));
    h.store.finishDialogueDelivery(detail(child));
    // Another connection saved the root while this one reads the successor.
    h.commit(
      "dialogue",
      panel({
        delivery: root,
        pureChain: [{ delivery: child, predecessors: ["host.news"] }],
        readingRevision: 4,
        completedTopicIds: ["host.news"],
      }),
    );
    expect(h.store.view.dialogueReading.revealed.deliveryId).toBe("dlv-child");
    // The playing successor keeps its line; the root acknowledgement is still
    // on the wire, so nothing new is sent in this commit.
    expect(actions(h.sender)).toHaveLength(1);
    h.respond({ code: "dialogue_completed" });
    // Root saved (by our own retry here) satisfies the successor's gate; the
    // client sends it exactly once, using the current committed revision.
    expect(actions(h.sender)).toHaveLength(2);
    expect(actions(h.sender)[1].payload.topic_id).toBe("t.child");
  });

  it("discards pending memory and the reveal when the context changes", () => {
    const root = formal();
    const child = formal([speech("host", "接續。")], { deliveryId: "dlv-child", topicId: "t.child" });
    h.commit("dialogue", panel({ delivery: root, pureChain: [{ delivery: child, predecessors: ["host.news"] }] }));
    h.store.finishDialogueDelivery(detail(root));
    h.respond({ outcome: "rejected", code: "busy", message: "busy" });
    h.store.finishDialogueDelivery(detail(child));
    expect(h.store.view.dialogueReading.pendingCount).toBe(2);

    // A new conversation context (leave + reopen, or a new host) retires it.
    h.commit("dialogue", panel({ contextId: "ctx-2", delivery: undefined }));
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
    expect(h.store.view.dialogueReading.revealed).toBeNull();
    expect(actions(h.sender)).toHaveLength(1);
  });

  it("discards on leaving dialogue but survives a bare transport reset for same-context retry", () => {
    h.store.finishDialogueDelivery(detail(formal()));
    // A reset alone keeps the entry: it can still be retried in the same
    // context once the restoring snapshot arrives.
    h.reconnect();
    expect(h.store.view.dialogueReading.pendingCount).toBe(1);
    h.store.setConnected(true);
    h.commit("dialogue", panel());
    expect(actions(h.sender)).toHaveLength(2);
    expect(actions(h.sender)[1].payload).toEqual(actions(h.sender)[0].payload);
    expect(actions(h.sender)[1].request_id).not.toBe(actions(h.sender)[0].request_id);

    // Leaving the conversation discards the pending memory.
    h.commit("exploration");
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
  });

  it("discards on a changed acting character", () => {
    h.store.finishDialogueDelivery(detail(formal()));
    h.commit("dialogue", panel(), {
      status: fx.statusPanel({ actor: { identity: "43", location: { label: "測試起點", identity: "17" } } }),
    });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
  });

  it("bounds the queue to 32 entries and never evicts the attempt on the wire", () => {
    // Force a failed first entry so it stays queued while 32 more are admitted.
    let failFirst = true;
    const original = h.sender.sendAction;
    h.sender.sendAction = (envelope) => {
      if (failFirst) {
        failFirst = false;
        throw new Error("socket closed");
      }
      original(envelope);
    };
    const first = formal(LINES, { deliveryId: "dlv-0", topicId: "t.0" });
    h.store.finishDialogueDelivery(detail(first));
    for (let index = 1; index <= 40; index += 1) {
      const delivery = formal(LINES, {
        deliveryId: `dlv-${index}`,
        topicId: `t.${index}`,
      });
      h.store.finishDialogueDelivery(detail(delivery));
    }
    expect(h.store.view.dialogueReading.pendingCount).toBeLessThanOrEqual(32);
    // The failed root entry is retained: overflow never silently drops the
    // unsaved progress the player can still retry.
    expect(
      h.store.view.dialogueReading.pending.some((entry) => entry.deliveryId === "dlv-0"),
    ).toBe(true);
  });

  it("keeps unrelated topic selections and qualified rows untouched", () => {
    const lockedRow = {
      ...choiceRow("dream", { hostId: HOST, contextId: CTX, topicId: "host.dream", label: "夢想" }),
      availability: "locked",
      requirement_hint: "需要好感階段至少為熟識",
    };
    h.commit("dialogue", panel({ choices: [choiceRow("news", { hostId: HOST }), lockedRow] }));
    const before = dialogueViewModel(h.store.view.panels.dialogue, h.store.view.dialogueReading);
    h.store.finishDialogueDelivery(detail(formal()));
    const after = dialogueViewModel(h.store.view.panels.dialogue, h.store.view.dialogueReading);
    expect(after.picks).toEqual(before.picks);
    expect(after.picks[1]).toMatchObject({ locked: true, hint: "需要好感階段至少為熟識" });
  });

  it("sends the queued acknowledgement when one publication settles a result and releases the player lock", () => {
    // A player action owns the single-mutation lock when the scene finishes.
    const dispatchId = h.store.dispatchAction("explore.look", { target: "room" });
    expect(dispatchId).not.toBeNull();
    const dispatchEnvelope = h.sender.sent.actions[0];
    h.store.finishDialogueDelivery(detail(formal()));
    expect(actions(h.sender)).toHaveLength(1);
    expect(h.store.view.dialogueReading.pendingCount).toBe(1);

    // The result names the already-committed revision, so the very same
    // publication releases the lock (view.js flushes after `releaseIfReady`);
    // the queued acknowledgement must still go out in that publish.
    h.respondTo(dispatchEnvelope.request_id);
    expect(h.store.view.dispatch.inFlight).toBe(null);
    expect(h.store.view.dialogueReading.sending).toBe(true);
    expect(actions(h.sender)).toHaveLength(2);
    expect(actions(h.sender)[1].action_id).toBe("explore.dialogue_complete");
    expect(actions(h.sender)[1].payload.topic_id).toBe("host.news");
    h.respond({ code: "dialogue_completed" });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
  });

  it("retries a transport-failed acknowledgement on same-context restoration, never an operational rejection", () => {
    let failNext = true;
    const original = h.sender.sendAction;
    h.sender.sendAction = (envelope) => {
      if (failNext) {
        failNext = false;
        throw new Error("socket closed");
      }
      original(envelope);
    };
    h.store.finishDialogueDelivery(detail(formal()));
    expect(h.store.view.dialogueReading.retryable).toBe(true);
    expect(actions(h.sender)).toHaveLength(0);

    // Same-context restoration retries the transport failure by itself.
    h.reconnect();
    h.commit("dialogue", panel());
    expect(actions(h.sender)).toHaveLength(1);

    // An operational server rejection is NOT retried by a plain reconnect.
    h.respond({ outcome: "rejected", code: "busy", message: "另一項操作正在進行中" });
    expect(h.store.view.dialogueReading.retryable).toBe(true);
    h.reconnect(fx.EPOCH_C);
    h.commit("dialogue", panel());
    expect(actions(h.sender)).toHaveLength(1);
    // The explicit retry still works.
    h.store.retryDialogueReading();
    expect(actions(h.sender)).toHaveLength(2);
  });

  it("discards pending memory and reveal on authoritative detachment and ignores a late saved answer", () => {
    const root = formal();
    const child = formal([speech("host", "接續。")], { deliveryId: "dlv-child", topicId: "t.child" });
    h.commit("dialogue", panel({ delivery: root, pureChain: [{ delivery: child, predecessors: ["host.news"] }] }));
    h.store.finishDialogueDelivery(detail(root));
    const envelope = actions(h.sender)[0];
    expect(h.store.view.dialogueReading.revealed).not.toBeNull();

    // `ui_protocol_error: no_puppet` is the authoritative character exit.
    h.store.receive(h.generation, "ui_protocol_error", [fx.protocolError()], {});
    expect(h.store.view.phase).toBe("detached");
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
    expect(h.store.view.dialogueReading.revealed).toBeNull();
    expect(h.store.view.dialogueReading.savedTopicIds).toEqual([]);

    // A late success (the server accepted it before the reap) must not settle
    // into the next character's state.
    h.respondTo(envelope.request_id, { code: "dialogue_completed" });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
    expect(h.store.view.dialogueReading.savedTopicIds).toEqual([]);
  });

  it("settles a saved answer that arrives after the acknowledgement timeout", () => {
    vi.useFakeTimers();
    try {
      h.store.finishDialogueDelivery(detail(formal()));
      const envelope = actions(h.sender)[0];
      vi.advanceTimersByTime(DIALOGUE_ACK_TIMEOUT_MS + 10);
      expect(h.store.view.dialogueReading.retryable).toBe(true);
      expect(h.store.view.dialogueReading.sending).toBe(false);
      // The retained correlation lets the late saved answer settle the entry.
      h.respondTo(envelope.request_id, { code: "dialogue_completed" });
      expect(h.store.view.dialogueReading.pendingCount).toBe(0);
      expect(h.store.view.dialogueReading.savedTopicIds).toEqual(["host.news"]);
    } finally {
      vi.useRealTimers();
    }
  });

  it("never lets a superseded attempt's late failure clear the newer attempt", () => {
    h.store.finishDialogueDelivery(detail(formal()));
    const first = actions(h.sender)[0];
    h.respond({ outcome: "rejected", code: "busy", message: "另一項操作正在進行中" });
    h.store.retryDialogueReading();
    const second = actions(h.sender)[1];
    expect(second.request_id).not.toBe(first.request_id);
    expect(h.store.view.dialogueReading.pending[0].status).toBe("sending");

    // The superseded attempt's late rejection must not fail or drop the new
    // attempt.
    h.respondTo(first.request_id, {
      outcome: "rejected",
      code: "dialogue_receipt_stale",
      message: "對話情境已過期。",
    });
    expect(h.store.view.dialogueReading.pendingCount).toBe(1);
    expect(h.store.view.dialogueReading.pending[0].status).toBe("sending");

    h.respondTo(second.request_id, { code: "dialogue_completed" });
    expect(h.store.view.dialogueReading.pendingCount).toBe(0);
    expect(h.store.view.dialogueReading.savedTopicIds).toEqual(["host.news"]);
  });
});
