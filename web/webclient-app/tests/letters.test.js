// Personal-letter folio lifecycle: one initial page load per opening, lock-aware
// deferred dispatch, lifecycle isolation, authoritative response reuse, and
// explicit close/reopen recovery.
//
// The harness drives the REAL Pinia store and the REAL reducer, so every
// dispatch and every committed presentation replaces `store.view` wholesale —
// exactly the production publication that used to discard a successful
// `letters.ok` (correspondence-panel-open-once D5). No stable-object mock.
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";

import AppClient from "../AppClient.vue";
import LettersPanel from "../components/LettersPanel.vue";
import { NAV_TOOLS } from "../components/nav-tools.js";
import { useElosernStore } from "../stores/elosern.js";
import CommandEcho from "../../static/webclient/js/elosern/command_echo.js";
import * as fx from "./store/protocol_fixtures.js";

const wrappers = [];
const hosts = [];
afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount());
  hosts.splice(0).forEach((host) => host.remove());
});

let store;
let sender;

function openSession({ epoch = fx.EPOCH_A, revision = 1, generation = 1 } = {}) {
  store.beginTransport(generation);
  store.setConnected(true);
  const received = store.receive(
    generation,
    "ui_snapshot",
    [fx.snapshot({ presentation_epoch: epoch, revision })],
    {},
  );
  expect(received.accepted).toBe(true);
}

function mountPanel() {
  const wrapper = mount(LettersPanel, { props: { store } });
  wrappers.push(wrapper);
  return wrapper;
}

function mountAppClient() {
  const host = document.createElement("div");
  host.id = "elosern-app";
  document.body.appendChild(host);
  hosts.push(host);
  const wrapper = mount(AppClient, { attachTo: host });
  wrappers.push(wrapper);
  return wrapper;
}

const letterRow = (sourceId, senderId = "12", readTick = null) => ({
  source_id: sourceId,
  sender_id: senderId,
  sent_tick: 17,
  read_tick: readTick,
});
const collectedPage = (letters = [], { branch = false, next = null } = {}) => ({
  branch,
  letters,
  next,
});

const actionIds = () => sender.sent.actions.map((envelope) => envelope.action_id);
const listPayloads = () =>
  sender.sent.actions
    .filter((envelope) => envelope.action_id === "letters.list")
    .map((envelope) => envelope.payload);

// Deliver one correlated action result through the real reducer. A
// presentation revision of 0 releases the in-flight gate on receipt.
function deliverResult({
  requestId,
  outcome = "success",
  data,
  message = "完成",
  presentationRevision = 0,
}) {
  const payload = fx.actionResult({
    presentation_epoch: store.view.epoch,
    request_id: requestId,
    outcome,
    message,
    presentation_revision: presentationRevision,
  });
  if (data !== undefined) {
    payload.data = data;
  }
  const received = store.receive(store.view.generation, "ui_action_result", [payload], {});
  expect(received.accepted).toBe(true);
}

const panelText = (wrapper) => wrapper.find('[data-testid="letters-panel"]').text();

describe("personal letter folio", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  it("loads the first page once per opening, renders no reload control, and needs no reload (task 2.3)", async () => {
    openSession();
    const wrapper = mountPanel();
    await nextTick();

    // Exactly one first-page request for this opening, and no reload control.
    expect(listPayloads()).toEqual([{ after: 0 }]);
    expect(wrapper.text()).not.toContain("重新載入");
    expect(wrapper.find('[data-testid="letters-panel"]').exists()).toBe(true);

    deliverResult({ requestId: "session:1", data: collectedPage([letterRow("synthetic-letter")]) });
    await nextTick();
    expect(wrapper.find(".letters-folio__letter").exists()).toBe(true);
    expect(panelText(wrapper)).toContain("未讀");

    // An ordinary committed presentation with the same identity and generation
    // submits no additional initial request and preserves the loaded page.
    expect(store.receive(1, "ui_update", [fx.update({ revision: 2 })], {}).accepted).toBe(true);
    await nextTick();
    expect(listPayloads()).toEqual([{ after: 0 }]);
    expect(wrapper.find(".letters-folio__letter").exists()).toBe(true);
    expect(listPayloads()).toHaveLength(1);
  });

  it("waits for a preceding request to release the dispatch lock, then submits exactly one load (task 2.2)", async () => {
    openSession();
    const preceding = store.dispatchAction("explore.wait", {});
    expect(preceding).toBe("session:1");

    const wrapper = mountPanel();
    await nextTick();
    // The earlier request owns the global lock: the opening submits nothing.
    expect(listPayloads()).toHaveLength(0);
    expect(panelText(wrapper)).toContain("正在載入信件");
    expect(panelText(wrapper)).not.toContain("請關閉信件面板後重新開啟");

    deliverResult({ requestId: preceding });
    await nextTick();
    // The lock now belongs to the folio's own single load, not the closed-out
    // preceding request.
    expect(store.view.dispatch.inFlight.requestId).not.toBe(preceding);
    expect(listPayloads()).toEqual([{ after: 0 }]);
    expect(listPayloads()).toHaveLength(1);
  });

  it("waits for a declared presentation revision to commit before loading (task 2.2)", async () => {
    openSession();
    const preceding = store.dispatchAction("explore.wait", {});
    const wrapper = mountPanel();
    await nextTick();
    expect(listPayloads()).toHaveLength(0);

    // The preceding result declares a revision the presentation has not reached
    // yet, so the lock holds and the folio keeps waiting.
    deliverResult({ requestId: preceding, presentationRevision: 2 });
    await nextTick();
    expect(store.view.dispatch.inFlight).toEqual({ requestId: preceding, presentationRevision: 2 });
    expect(listPayloads()).toHaveLength(0);

    expect(store.receive(1, "ui_update", [fx.update({ revision: 2 })], {}).accepted).toBe(true);
    await nextTick();
    expect(store.view.dispatch.inFlight.requestId).not.toBe(preceding);
    expect(listPayloads()).toEqual([{ after: 0 }]);
    expect(panelText(wrapper)).not.toContain("請關閉信件面板後重新開啟");
  });

  it("submits no refused request behind a mutation lock and discards the blocked opening (task 2.2)", async () => {
    openSession();
    const locked = store.receive(
      1,
      "ui_protocol_error",
      [fx.protocolError({ code: "unsupported_version", message: "需要重新載入", reload_required: true })],
      {},
    );
    expect(locked.accepted).toBe(true);
    expect(store.view.mutationsLocked).toBe(true);
    expect(store.view.dispatch.inFlight).toBe(null);

    const wrapper = mountPanel();
    await nextTick();
    expect(listPayloads()).toHaveLength(0);
    expect(panelText(wrapper)).toContain("正在載入信件");
    expect(panelText(wrapper)).not.toContain("請關閉信件面板後重新開啟");

    // The only supported recovery is a fresh transport generation: that
    // boundary discards the blocked opening instead of loading under a new
    // identity, and a subsequent opening owns its own single initial load.
    store.beginTransport(2);
    store.setConnected(true);
    expect(
      store.receive(2, "ui_snapshot", [fx.snapshot({ presentation_epoch: fx.EPOCH_B })], {}).accepted,
    ).toBe(true);
    await nextTick();
    expect(listPayloads()).toHaveLength(0);

    wrapper.unmount();
    const reopened = mountPanel();
    await nextTick();
    expect(listPayloads()).toEqual([{ after: 0 }]);
    expect(panelText(reopened)).not.toContain("請關閉信件面板後重新開啟");
  });

  it("cancels an unsent load on close and loads once on a reopening that waits on the previous request (tasks 1.2, 2.2)", async () => {
    openSession();
    store.dispatchAction("explore.wait", {});
    const first = mountPanel();
    await nextTick();
    expect(listPayloads()).toHaveLength(0);

    first.unmount();
    // The lock releases only after the opening is gone: a closed opening must
    // submit nothing even then.
    deliverResult({ requestId: "session:1" });
    await nextTick();
    expect(listPayloads()).toHaveLength(0);

    // Reopen while the previous submitted request still owns the lock.
    const held = store.dispatchAction("explore.wait", {});
    const second = mountPanel();
    await nextTick();
    expect(listPayloads()).toHaveLength(0);

    deliverResult({ requestId: held });
    await nextTick();
    expect(listPayloads()).toEqual([{ after: 0 }]);
    expect(listPayloads()).toHaveLength(1);
    expect(second.find('[data-testid="letters-panel"]').exists()).toBe(true);
  });

  it("ignores a late result from a closed opening and accepts only the current one (tasks 1.1, 2.1)", async () => {
    openSession();
    const first = mountPanel();
    await nextTick();
    expect(listPayloads()).toEqual([{ after: 0 }]);
    first.unmount();

    const second = mountPanel();
    await nextTick();
    // The second opening waits for the first opening's unconfirmed request, so
    // nothing is submitted yet.
    expect(listPayloads()).toHaveLength(1);

    // The first opening's response arrives late: it releases the lock but must
    // not populate the new panel or change its status.
    deliverResult({ requestId: "session:1", data: collectedPage([letterRow("synthetic-late")], { branch: true }) });
    await nextTick();
    expect(second.find(".letters-folio__index").exists()).toBe(false);
    expect(panelText(second)).not.toContain("synthetic-late");
    expect(panelText(second)).not.toContain("已領取");
    expect(listPayloads()).toEqual([{ after: 0 }, { after: 0 }]);
    const messageBefore = panelText(second);

    // A re-delivered prior result for a foreign request must not be applied.
    deliverResult({ requestId: "session:1", data: collectedPage([letterRow("synthetic-late")], { branch: true }) });
    await nextTick();
    expect(panelText(second)).toBe(messageBefore);
    expect(second.find(".letters-folio__index").exists()).toBe(false);

    // Only the new opening's correlated result populates it.
    deliverResult({ requestId: "session:2", data: collectedPage([letterRow("synthetic-current")]) });
    await nextTick();
    expect(second.find(".letters-folio__index").exists()).toBe(true);
    expect(second.text()).toContain("synthetic-current");
    expect(second.text()).not.toContain("synthetic-late");
  });

  it("preserves page, opened prose, and an unsent draft across an ordinary publication (tasks 1.1, 2.1, 2.5)", async () => {
    openSession();
    const wrapper = mountPanel();
    await nextTick();
    deliverResult({
      requestId: "session:1",
      data: collectedPage([letterRow("synthetic-letter")], { branch: true }),
    });
    await nextTick();
    await wrapper.find(".letters-folio__letter").trigger("click");
    expect(actionIds()).toEqual(["letters.list", "letters.read"]);
    deliverResult({
      requestId: "session:2",
      data: { source_id: "synthetic-letter", sender_id: "12", read_tick: 20, body_parts: ["合成私密內容"] },
    });
    await nextTick();
    await wrapper.find("input").setValue("synthetic-recipient");
    await wrapper.find("textarea").setValue("synthetic unsent draft");

    // The ordinary presentation that used to discard all of it.
    expect(store.receive(1, "ui_update", [fx.update({ revision: 2 })], {}).accepted).toBe(true);
    await nextTick();

    expect(listPayloads()).toHaveLength(1);
    expect(wrapper.find(".letters-folio__letter").exists()).toBe(true);
    expect(wrapper.find(".letters-folio__reading").text()).toContain("合成私密內容");
    expect(wrapper.find("input").element.value).toBe("synthetic-recipient");
    expect(wrapper.find("textarea").element.value).toBe("synthetic unsent draft");
    expect(wrapper.text()).not.toContain("連線或角色已變更");
  });

  it("paginates with the server cursor without collecting or reading (task 2.3)", async () => {
    openSession();
    const wrapper = mountPanel();
    await nextTick();
    deliverResult({
      requestId: "session:1",
      data: collectedPage([letterRow("synthetic-first")], { next: 42 }),
    });
    await nextTick();

    const nextControl = wrapper.findAll("button").find((button) => button.text() === "下一頁");
    expect(nextControl).toBeDefined();
    await nextControl.trigger("click");
    expect(listPayloads()).toEqual([{ after: 0 }, { after: 42 }]);
    expect(actionIds()).toEqual(["letters.list", "letters.list"]);

    deliverResult({ requestId: "session:2", data: collectedPage([letterRow("synthetic-second")]) });
    await nextTick();
    expect(wrapper.text()).toContain("synthetic-second");
    expect(wrapper.text()).not.toContain("synthetic-first");
    expect(actionIds()).not.toContain("letters.read");
    expect(actionIds()).not.toContain("letters.collect");
  });

  it("reuses authoritative collect and send pages without an extra list or read (task 2.5)", async () => {
    openSession();
    const wrapper = mountPanel();
    await nextTick();
    deliverResult({
      requestId: "session:1",
      data: collectedPage([letterRow("synthetic-first")], { branch: true }),
    });
    await nextTick();

    // Explicit collection: one collect, and its response IS the new page.
    await wrapper.find(".letters-folio__tools button").trigger("click");
    expect(actionIds()).toEqual(["letters.list", "letters.collect"]);
    deliverResult({
      requestId: "session:2",
      data: { ...collectedPage([letterRow("synthetic-collected")], { branch: true }), count: 1 },
    });
    await nextTick();
    expect(wrapper.text()).toContain("synthetic-collected");
    expect(wrapper.text()).toContain("已領取 1 封信件。");

    // Explicit send: one send, its response updates the page, and the body clears.
    await wrapper.find("input").setValue("synthetic-recipient");
    await wrapper.find("textarea").setValue("synthetic body");
    await wrapper.find("form").trigger("submit");
    expect(actionIds()).toEqual(["letters.list", "letters.collect", "letters.send"]);
    deliverResult({
      requestId: "session:3",
      data: { ...collectedPage([letterRow("synthetic-sent")], { branch: true }), sent_id: "synthetic-sent" },
    });
    await nextTick();
    expect(wrapper.text()).toContain("synthetic-sent");
    expect(wrapper.find("textarea").element.value).toBe("");
    // No follow-up list request, and no read was ever dispatched.
    expect(listPayloads()).toEqual([{ after: 0 }]);
    expect(actionIds()).not.toContain("letters.read");
  });

  it("shows close-and-reopen guidance for a failed load with no automatic retry (task 2.4)", async () => {
    openSession();
    const wrapper = mountPanel();
    await nextTick();
    deliverResult({
      requestId: "session:1",
      outcome: "rejected",
      message: "信件服務暫時無法使用。",
    });
    await nextTick();
    expect(panelText(wrapper)).toContain("信件服務暫時無法使用。");
    expect(panelText(wrapper)).toContain("請關閉信件面板後重新開啟，以重新載入信件。");

    // Later publications and a released lock never retry the consumed attempt.
    expect(store.receive(1, "ui_update", [fx.update({ revision: 2 })], {}).accepted).toBe(true);
    await nextTick();
    expect(listPayloads()).toHaveLength(1);
    expect(panelText(wrapper)).toContain("請關閉信件面板後重新開啟，以重新載入信件。");
  });

  it("treats a synchronous send failure as terminal guidance, never a retry, and never mistakes uncertainty or a synchronous result (task 2.4)", async () => {
    openSession();
    const attempts = [];
    store.setSender({
      sent: [],
      sendAction(envelope) {
        attempts.push(envelope);
        throw new Error("transport closed");
      },
      sendText() {},
    });
    const wrapper = mountPanel();
    await nextTick();
    // The attempt was submitted and failed synchronously: one request id, no
    // in-flight record, no server result, global uncertainty preserved.
    expect(attempts).toHaveLength(1);
    expect(store.view.dispatch.inFlight).toBe(null);
    expect(store.view.dispatch.uncertain).toBe(true);
    expect(store.view.lastActionResult).toBe(null);
    expect(panelText(wrapper)).toContain("請關閉信件面板後重新開啟。");

    // Ordinary publications and lock releases neither retry nor overwrite it.
    expect(store.receive(1, "ui_update", [fx.update({ revision: 2 })], {}).accepted).toBe(true);
    await nextTick();
    expect(attempts).toHaveLength(1);
    expect(panelText(wrapper)).toContain("請關閉信件面板後重新開啟。");

    // Recovery needs a new opening; the retained global uncertainty is not
    // mistaken for this opening's failure.
    wrapper.unmount();
    store.setSender(sender);
    const reopened = mountPanel();
    await nextTick();
    expect(listPayloads()).toEqual([{ after: 0 }]);
    expect(store.view.dispatch.uncertain).toBe(true);
    expect(panelText(reopened)).not.toContain("請關閉信件面板後重新開啟。");
    // The new opening loads normally despite the retained global uncertainty.
    deliverResult({ requestId: "session:2", data: collectedPage([letterRow("synthetic-recovered")]) });
    await nextTick();
    expect(reopened.text()).toContain("synthetic-recovered");

    // A transport that completes synchronously is not a send failure.
    const current = store.view.epoch;
    store.setSender({
      sent: [],
      sendAction(envelope) {
        store.receive(1, "ui_action_result", [
          fx.actionResult({
            presentation_epoch: current,
            request_id: envelope.request_id,
            data: collectedPage([letterRow("synthetic-sync")]),
          }),
        ]);
      },
      sendText() {},
    });
    reopened.unmount();
    const syncWrapper = mountPanel();
    await nextTick();
    await nextTick();
    expect(panelText(syncWrapper)).not.toContain("請關閉信件面板後重新開啟。");
    expect(syncWrapper.text()).toContain("synthetic-sync");
    expect(store.view.dispatch.inFlight).toBe(null);
  });

  it("closes the folio and discards its private state on every genuine lifecycle boundary (tasks 1.2, 2.1)", async () => {
    openSession();
    const app = mountAppClient();
    await nextTick();
    const panel = () => app.find('[data-testid="letters-panel"]');

    store.openHudDrawer("letters");
    await nextTick();
    expect(store.view.hudDrawer).toBe("letters");
    expect(panel().exists()).toBe(true);
    expect(listPayloads()).toEqual([{ after: 0 }]);

    // Private prose and an unsent draft in the open folio.
    deliverResult({
      requestId: "session:1",
      data: collectedPage([letterRow("synthetic-letter")], { branch: true }),
    });
    await nextTick();
    await panel().find("input").setValue("synthetic-recipient");
    await panel().find("textarea").setValue("synthetic draft");

    // 1. Transport loss closes the folio and unmounts it.
    store.setConnected(false);
    await nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(panel().exists()).toBe(false);

    // 2. A reconnect on a fresh transport generation and a replaced identity:
    //    the old page and draft must not survive; the new opening loads once.
    store.beginTransport(2);
    store.setConnected(true);
    expect(
      store.receive(2, "ui_snapshot", [fx.snapshot({ presentation_epoch: fx.EPOCH_B })], {}).accepted,
    ).toBe(true);
    await nextTick();
    store.openHudDrawer("letters");
    await nextTick();
    expect(panel().exists()).toBe(true);
    expect(panel().find("textarea").exists()).toBe(false);
    expect(panel().find(".letters-folio__letter").exists()).toBe(false);
    expect(listPayloads()).toHaveLength(2);

    // 3. A generation reset with an active epoch closes the folio.
    store.beginTransport(3);
    await nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(panel().exists()).toBe(false);

    // 4. A generation reset while the epoch is still null — the folio can be
    //    opened before the first snapshot commits, so the epoch-change teardown
    //    never fires and the generation boundary itself must close it.
    store.setConnected(true);
    store.openHudDrawer("letters");
    await nextTick();
    expect(store.view.epoch).toBe(null);
    expect(store.view.phase).toBe("awaiting_initial_snapshot");
    expect(panel().exists()).toBe(true);
    store.beginTransport(4);
    await nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(panel().exists()).toBe(false);

    // 5. A no-puppet detach closes the folio; a fresh-epoch snapshot
    //    re-establishes the session and the next opening loads its own page.
    store.setConnected(true);
    expect(
      store.receive(4, "ui_snapshot", [fx.snapshot({ presentation_epoch: fx.EPOCH_C })], {}).accepted,
    ).toBe(true);
    await nextTick();
    store.openHudDrawer("letters");
    await nextTick();
    expect(panel().exists()).toBe(true);
    deliverResult({
      requestId: "session:1",
      data: collectedPage([letterRow("synthetic-letter")], { branch: true }),
    });
    await nextTick();
    await panel().find("textarea").setValue("synthetic draft");
    expect(store.receive(4, "ui_protocol_error", [fx.protocolError()], {}).accepted).toBe(true);
    await nextTick();
    expect(store.view.phase).toBe("detached");
    expect(store.view.hudDrawer).toBe(null);
    expect(panel().exists()).toBe(false);
  });

  it("keeps the private state isolated from an unrelated draft identity (tasks 1.2, 2.5)", async () => {
    openSession();
    const wrapper = mountPanel();
    await nextTick();
    deliverResult({
      requestId: "session:1",
      data: collectedPage([letterRow("synthetic-letter")], { branch: true }),
    });
    await nextTick();
    await wrapper.find("textarea").setValue("first draft");
    // The same opening, an unrelated presentation: the draft is not cleared and
    // no list request is issued.
    expect(store.receive(1, "ui_update", [fx.update({ revision: 2 })], {}).accepted).toBe(true);
    await nextTick();
    expect(wrapper.find("textarea").element.value).toBe("first draft");
    expect(listPayloads()).toHaveLength(1);

    // Closing discards the draft: a reopened folio starts empty.
    wrapper.unmount();
    const reopened = mountPanel();
    await nextTick();
    expect(reopened.find("textarea").exists()).toBe(false);
  });

  it("provides a keyboard tool and actual text-equivalent echoes", () => {
    expect(NAV_TOOLS.find((tool) => tool.key === "letters").drawer).toBe("letters");
    expect(CommandEcho.commandLine("letters.collect", {})).toBe("信件 領取");
    expect(CommandEcho.commandLine("letters.list", { after: 41 })).toBe("信件 更多 41");
    expect(CommandEcho.commandLine("letters.read", { source_id: "synthetic-letter" })).toBe("信件 讀 synthetic-letter");
    expect(CommandEcho.commandLine("letters.send", { recipient: "#12", body_parts: ["a=", "b"] })).toBe("信件 寄 #12=a=b");
  });
});
