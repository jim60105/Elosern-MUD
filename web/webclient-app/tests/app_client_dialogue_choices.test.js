// webclient-dialogue-choices-overlay D3/D4/D7/D8 and authored-dialogue-
// playback: the live wiring of the dialogue choice list and the shared
// manual scene player. The list renders in the stage's `choices` anchor only
// in dialogue with the panel available, once the native line is fully read
// or an authored scene received its explicit finish activation, and never
// while an action is in flight. Its four intents reach the store's single
// entry (a pick's `explore.talk_scripted`, the free row's borrow, an exit's
// overview payload, and the leave); focus moves onto it when it appears over
// the message window and parks on the message page before an activation
// dispatches. A scene line updates the page text, the name plate and the
// stage emphasis in one render; a reconnect replays the delivery from line
// one without selecting again; a mode change retires it without finishing.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";
import {
  dialoguePanel as v3Panel,
  narration,
  sceneDelivery,
  speech,
  unavailableDialoguePanel,
} from "./support/dialogue_panel.js";

function dialoguePanel(overrides = {}) {
  return v3Panel({
    hostId: 7,
    hostName: "店長",
    actorName: "旅人",
    bondStage: "熟識",
    line: "歡迎來到西風酒館。",
    keywords: ["news", "town"],
    labels: ["最近有什麼消息？", "關於這座城鎮"],
    ...overrides,
  });
}

// The deterministic multi-line scene: actor speech, two consecutive host
// lines, narration.
const SCENE_LINES = [
  speech("actor", "最近有什麼消息？"),
  speech("host", "北岸大道最近不太平。"),
  speech("host", "夜裡別走那條路。"),
  narration("店長壓低了聲音。"),
];

function scenePanel(lines = SCENE_LINES, deliveryOverrides = {}, panelOverrides = {}) {
  return dialoguePanel({
    delivery: sceneDelivery(lines, { topicId: "host.news", sceneId: "host.news_scene", ...deliveryOverrides }),
    ...panelOverrides,
  });
}

describe("the dialogue choice list over the stage", () => {
  let store, sender, wrapper, revision, generation, epoch;

  beforeEach(async () => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    // `normal` speed: with no animation frame in jsdom, a new page stays
    // typing until the reader completes it.
    store.setTextSpeed?.("normal");
    wrapper = mount(AppClient, { attachTo: document.body });
    generation = 1;
    epoch = fx.EPOCH_A;
    store.beginTransport(generation);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    commit("exploration");
    // A line already read, so later lines open as new responses.
    store.appendText("out", "渡口的霧。");
    await settle();
  });
  afterEach(() => {
    wrapper.unmount();
    document.body.replaceChildren();
  });

  async function settle() {
    for (let i = 0; i < 4; i += 1) {
      await nextTick();
    }
  }

  function commit(mode, dialogue = null) {
    const panels = {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      context_actions: fx.explorationActions(),
      local_map: fx.localMapPanel(),
    };
    if (dialogue) {
      panels.dialogue = dialogue;
    }
    const response = store.receive(generation, "ui_snapshot", [fx.snapshot({ revision, mode, panels, presentation_epoch: epoch })], {});
    expect(response.accepted, JSON.stringify(response)).toBe(true);
    revision += 1;
  }

  const list = () => wrapper.find('[data-anchor="choices"] [data-testid="dialogue-choices"]');
  const page = () => wrapper.get('[data-testid="message-page"]').element;
  const win = () => wrapper.get('[data-testid="message-window"]');
  const typing = () => win().attributes("data-typing");
  const pageText = () => wrapper.get('[data-testid="message-page"]').text();
  const plate = () => wrapper.find('[data-testid="message-name-plate"]');
  const actorSpeaking = () => wrapper.get('[data-anchor="actor-left"] [data-testid="stage-actor"]').attributes("data-speaking");
  const hostSpeaking = () => wrapper.get('[data-anchor="actor-right"] [data-testid="stage-actor"]').attributes("data-speaking");

  async function press(key = "Enter", init = {}) {
    page().dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...init }));
    await settle();
  }

  async function openDialogue(panel = dialoguePanel()) {
    commit("dialogue", panel);
    await settle();
  }

  // The scene's attribution as rendered in one frame.
  function frame() {
    return {
      text: pageText(),
      plate: plate().exists() ? plate().get(".message-window__plate-name").text() : null,
      actor: actorSpeaking(),
      host: hostSpeaking(),
    };
  }

  it("renders nowhere outside dialogue and inside the choices anchor in dialogue", async () => {
    expect(list().exists()).toBe(false);
    await openDialogue();
    expect(list().exists()).toBe(true);
    expect(wrapper.findAll('[data-testid="dialogue-choices"]')).toHaveLength(1);
    expect(wrapper.find('[data-anchor="band-message"] [data-testid="dialogue-pick"]').exists()).toBe(false);
    expect(list().findAll('[data-testid="dialogue-pick"]').map((row) => row.attributes("data-keyword-id"))).toEqual(["news", "town"]);
  });

  it("renders nothing while the dialogue panel is unavailable", async () => {
    await openDialogue(unavailableDialoguePanel());
    expect(store.view.mode).toBe("dialogue");
    expect(list().exists()).toBe(false);
  });

  it("waits for the line to be fully read, then takes focus from the message page", async () => {
    await openDialogue();
    page().focus();
    // The session line arrives as a new response and types.
    store.appendText("in", "talk 店長");
    store.appendText("out", "店長說：歡迎來到西風酒館。");
    await settle();
    expect(typing()).toBe("true");
    expect(list().exists()).toBe(false);
    // Enter on the page completes the (last) page: the list appears and
    // takes focus with its first row active.
    await press();
    expect(typing()).toBe("false");
    expect(list().exists()).toBe(true);
    expect(document.activeElement).toBe(list().element);
    expect(list().attributes("aria-activedescendant")).toBe(list().findAll('[role="menuitem"]')[0].attributes("id"));
  });

  it("never steals focus from the command field when it appears", async () => {
    await openDialogue();
    store.appendText("in", "talk 店長");
    store.appendText("out", "店長說：歡迎。");
    await settle();
    expect(list().exists()).toBe(false);
    await wrapper.findComponent({ name: "AppShell" }).vm.focusCommandField();
    const field = document.getElementById("inputfield");
    expect(document.activeElement).toBe(field);
    await press();
    expect(list().exists()).toBe(true);
    expect(document.activeElement).toBe(field);
  });

  it("a pick dispatches the scripted topic, parks focus on the page, and hides the list while in flight", async () => {
    await openDialogue();
    list().element.focus();
    list().element.dispatchEvent(new KeyboardEvent("keydown", { key: "2", bubbles: true, cancelable: true }));
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.talk_scripted",
      payload: { npc_id: 7, topic_id: "host.town", context_id: "ctx-1" },
    });
    await settle();
    expect(list().exists()).toBe(false);
    expect(document.activeElement).toBe(page());
    // The reply commits its complete scene: the list stays away until the
    // scene's final page receives a further activation.
    store.receive(generation, "ui_action_result", [fx.actionResult({ presentation_revision: revision })], {});
    store.appendText("out", "你說：關於這座城鎮");
    store.appendText("out", "店長說：北岸大道最近不太平。");
    commit("dialogue", scenePanel([speech("actor", "關於這座城鎮"), speech("host", "北岸大道最近不太平。")]));
    await settle();
    expect(store.view.dispatch.inFlight).toBe(null);
    expect(list().exists()).toBe(false);
    await press(); // complete line 1
    await press(); // line 2
    await press(); // complete line 2 (the final page, fully shown)
    expect(typing()).toBe("false");
    expect(list().exists()).toBe(false);
    await press(); // the explicit finish
    expect(list().exists()).toBe(true);
    expect(document.activeElement).toBe(list().element);
  });

  it("the free row borrows the command line and dispatches nothing", async () => {
    await openDialogue();
    const before = store.view.drawerRequest;
    await list().get('[data-testid="dialogue-freeform"]').trigger("click");
    await settle();
    expect(store.view.drawerRequest).toBe(before + 1);
    expect(store.view.freeformBound).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
    expect(document.activeElement?.id).toBe("inputfield");
    expect(wrapper.get('[data-testid="anchor-command-line"]').attributes("data-expanded")).toBe("true");
  });

  it("`↦ 移動…` then an exit dispatches the committed exit row's payload", async () => {
    await openDialogue();
    await list().get('[data-testid="dialogue-move"]').trigger("click");
    const exitRows = list().findAll('[data-testid="dialogue-exit-row"]');
    // exploration-exit-compass D9: the list reads the committed exit rows
    // (the compass's), not the router root, which carries no exit item.
    expect(store.view.rootMenu.items.some((item) => item.actionId === "explore.move")).toBe(false);
    const overviewExit = store.view.explorationExits.find((item) => item.actionId === "explore.move" && item.enabled !== false);
    expect(exitRows.length).toBe(store.view.explorationExits.length);
    const enabledRow = exitRows.find((row) => row.attributes("aria-disabled") !== "true");
    await enabledRow.trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.move", payload: overviewExit.payload });
    expect(document.activeElement).toBe(page());
  });

  it("a locked exit keeps its reason and dispatches nothing", async () => {
    await openDialogue();
    await list().get('[data-testid="dialogue-move"]').trigger("click");
    const locked = list().findAll('[data-testid="dialogue-exit-row"]').find((row) => row.attributes("aria-disabled") === "true");
    expect(locked.get('[data-testid="dialogue-exit-reason"]').text()).toBe("門被鎖住了");
    await locked.trigger("click");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("the leave row dispatches explore.dialogue_leave for the host and nothing else", async () => {
    await openDialogue();
    await list().get('[data-testid="dialogue-exit"]').trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.dialogue_leave", payload: { npc_id: 7 } });
  });

  describe("the shared manual scene player", () => {
    it("changes text, plate and emphasis together at every line start, one reading step per line", async () => {
      await openDialogue(scenePanel());
      page().focus();
      const frames = [frame()];
      // Each line: complete its typing, then advance to the next line.
      for (let line = 1; line < SCENE_LINES.length; line += 1) {
        await press();
        await press();
        frames.push(frame());
      }
      expect(frames).toEqual([
        { text: "最近有什麼消息？", plate: "旅人", actor: "true", host: "false" },
        { text: "北岸大道最近不太平。", plate: "店長", actor: "false", host: "true" },
        // The same host again: a separate reading step, still the host's.
        { text: "夜裡別走那條路。", plate: "店長", actor: "false", host: "true" },
        // Narration: no plate (an invisible spacer keeps its row), and
        // neither participant emphasized.
        { text: "店長壓低了聲音。", plate: null, actor: "false", host: "false" },
      ]);
      expect(wrapper.find('[data-testid="message-plate-spacer"]').exists()).toBe(true);
      // The bond suffix belongs to host speech only.
      expect(wrapper.find('[data-testid="dialogue-bond"]').exists()).toBe(false);
      expect(list().exists()).toBe(false);
    });

    it("finishes only on a further activation after the final page and reports completion once", async () => {
      await openDialogue(scenePanel([speech("actor", "嗯？"), speech("host", "好。")]));
      const shell = wrapper.findComponent({ name: "MessageWindow" });
      page().focus();
      await press(); // complete line 1
      await press(); // line 2 typing
      await press(); // line 2 complete: the ■ final page
      expect(shell.get('[data-testid="message-page-marker"]').attributes("data-state")).toBe("end");
      expect(shell.get('[data-testid="message-page-marker"]').attributes("data-await-finish")).toBe("true");
      expect(win().attributes("data-reading-complete")).toBe("false");
      expect(list().exists()).toBe(false);
      await press();
      expect(win().attributes("data-reading-complete")).toBe("true");
      expect(list().exists()).toBe(true);
      expect(shell.get('[data-testid="message-page-marker"]').attributes("data-await-finish")).toBeUndefined();
      // Further activations on the finished scene change nothing.
      page().focus();
      await press();
      expect(pageText()).toBe("好。");
      expect(sender.sent.actions).toHaveLength(0);
    });

    it("plays without appending transcript and keeps auto-advance off for scenes", async () => {
      store.setAutoAdvance?.(true);
      store.setTextSpeed?.("instant");
      await openDialogue(scenePanel());
      const logLength = store.narrative.length;
      page().focus();
      // Instant speed: each line is fully shown at once, and nothing moves
      // without an activation.
      expect(typing()).toBe("false");
      await new Promise((resolve) => setTimeout(resolve, 50));
      await settle();
      expect(pageText()).toBe("最近有什麼消息？");
      for (let line = 1; line < SCENE_LINES.length; line += 1) {
        await press();
      }
      expect(pageText()).toBe("店長壓低了聲音。");
      expect(list().exists()).toBe(false);
      await press();
      expect(list().exists()).toBe(true);
      expect(store.narrative.length).toBe(logLength);
    });

    it("ignores a held key's repeat and modified keys", async () => {
      store.setTextSpeed?.("instant");
      await openDialogue(scenePanel());
      page().focus();
      await press("Enter", { repeat: true });
      await press(" ", { shiftKey: true });
      await press("Enter", { ctrlKey: true });
      expect(pageText()).toBe("最近有什麼消息？");
      await press(" ");
      expect(pageText()).toBe("北岸大道最近不太平。");
    });

    it("keeps the local line on a same-delivery availability refresh", async () => {
      store.setTextSpeed?.("instant");
      await openDialogue(scenePanel());
      page().focus();
      await press();
      expect(pageText()).toBe("北岸大道最近不太平。");
      // The same delivery with refreshed choices.
      commit("dialogue", scenePanel(SCENE_LINES, {}, { keywords: ["news"], labels: ["最近有什麼消息？"] }));
      await settle();
      expect(pageText()).toBe("北岸大道最近不太平。");
      expect(plate().text()).toContain("店長");
    });

    it("replays from line one after a reconnect without selecting again", async () => {
      store.setTextSpeed?.("instant");
      await openDialogue(scenePanel());
      page().focus();
      await press();
      await press();
      expect(pageText()).toBe("夜裡別走那條路。");
      const logLength = store.narrative.length;
      // The transport resets; the resync snapshot carries the same delivery.
      generation = 2;
      store.beginTransport(generation);
      store.setConnected(true);
      store.setLoggedIn(true);
      await settle();
      revision = 1;
      epoch = fx.EPOCH_B;
      commit("dialogue", scenePanel());
      await settle();
      expect(pageText()).toBe("最近有什麼消息？");
      expect(frame()).toMatchObject({ plate: "旅人", actor: "true", host: "false" });
      expect(list().exists()).toBe(false);
      expect(sender.sent.actions).toHaveLength(0);
      expect(store.narrative.length).toBe(logLength);
    });

    it("retires without finishing when combat begins midway, keeping the transcript", async () => {
      store.setTextSpeed?.("instant");
      store.appendText("out", "你說：最近有什麼消息？");
      store.appendText("out", "店長說：北岸大道最近不太平。");
      await openDialogue(scenePanel());
      await press();
      const transcript = store.narrative.map((line) => line.text);
      commit("combat");
      await settle();
      expect(win().attributes("data-scene")).toBeUndefined();
      expect(list().exists()).toBe(false);
      expect(plate().exists()).toBe(false);
      expect(store.narrative.map((line) => line.text)).toEqual(transcript);
      // The covered transcript settles: it is shown, already read.
      expect(typing()).toBe("false");
    });

    it("holds the window while a pick awaits its scene, and types a rejection once it is handled", async () => {
      store.setTextSpeed?.("instant");
      await openDialogue();
      await press();
      list().element.focus();
      list().element.dispatchEvent(new KeyboardEvent("keydown", { key: "1", bubbles: true, cancelable: true }));
      const requestId = sender.sent.actions[0].request_id;
      await settle();
      const held = pageText();
      // An echo reaches the log while the pick is out: the window holds.
      store.appendText("in", "talk 店長 最近有什麼消息？");
      await settle();
      expect(pageText()).toBe(held);
      // The pick is refused (no scene, no transcript): the lock releases and
      // the refusal reads as new text.
      store.receive(
        generation,
        "ui_action_result",
        [fx.actionResult({ request_id: requestId, outcome: "rejected", code: "stale_context", message: "對話情境已過期。", presentation_revision: revision - 1 })],
        {},
      );
      store.appendText("err", "對話情境已過期。");
      await settle();
      expect(store.view.dispatch.inFlight).toBe(null);
      expect(pageText()).toBe("對話情境已過期。");
    });

    it("types a freeform reply whose lines arrive before the commit that retires the scene", async () => {
      store.setTextSpeed?.("normal");
      await openDialogue(scenePanel([speech("actor", "嗯？")]));
      page().focus();
      await press(); // complete
      await press(); // finish
      expect(list().exists()).toBe(true);
      const requestId = store.dispatchAction("explore.talk_freeform", { npc_id: 7, speech: "你好。" }, null);
      expect(requestId).not.toBe(null);
      await settle();
      store.appendText("in", "say 你好。");
      store.appendText("out", "店長說：你好啊，旅人。");
      await settle();
      expect(pageText()).toBe("嗯？");
      store.receive(generation, "ui_action_result", [fx.actionResult({ request_id: requestId, presentation_revision: revision })], {});
      commit("dialogue", dialoguePanel({ line: "你好啊，旅人。" }));
      await settle();
      expect(win().attributes("data-scene")).toBeUndefined();
      expect(pageText()).toBe("店長說：你好啊，旅人。");
      expect(typing()).toBe("true");
    });

    it("does not take focus from an open drawer when the finished scene returns the choices", async () => {
      store.setTextSpeed?.("instant");
      await openDialogue(scenePanel([speech("actor", "嗯？")]));
      page().focus();
      await press(); // the final page is shown at once; this is the finish
      expect(list().exists()).toBe(true);
      // A new scene, finished while focus sits elsewhere (a drawer control).
      const elsewhere = document.createElement("button");
      document.body.appendChild(elsewhere);
      commit("dialogue", scenePanel([speech("actor", "再一次？")], { deliveryId: "dlv-2" }));
      await settle();
      expect(list().exists()).toBe(false);
      page().focus();
      page().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
      elsewhere.focus();
      await settle();
      expect(list().exists()).toBe(true);
      expect(document.activeElement).toBe(elsewhere);
    });
  });
});
