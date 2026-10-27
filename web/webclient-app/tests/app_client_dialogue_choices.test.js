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
  choiceRow,
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

  it("retires an absent service topic after opening and never focuses a later conversation", async () => {
    const host = {
      ...fx.explorationPanel().interact[0],
      services: { state: "ready", entries: [{
        key: "dialogue.offer", label: "委託", enabled: true, disabled_reason: null,
        route: { kind: "dialogue", npc_id: 7, topic_id: "not-disclosed" },
      }] },
    };
    const response = store.receive(generation, "ui_update", [fx.update({
      revision, panels: { exploration: fx.explorationPanel({ interact: [host] }) },
    })], {});
    expect(response.accepted).toBe(true);
    revision += 1;
    store.activatePresence("target-7");
    store.activatePresenceVerb("service-dialogue.offer");
    const request = sender.sent.actions.at(-1);
    expect(request.action_id).toBe("explore.talk_open");
    commit("dialogue", dialoguePanel());
    store.receive(generation, "ui_action_result", [fx.actionResult({
      request_id: request.request_id, presentation_revision: revision - 1,
    })], {});
    await settle();
    expect(store.view.dialogueFocusTopic).toBeNull();
    expect(sender.sent.actions).toHaveLength(1);
    commit("exploration");
    await settle();
    await openDialogue(dialoguePanel({ keywords: ["news", "not-disclosed"] }));
    expect(store.view.dialogueFocusTopic).toBeNull();
    expect(sender.sent.actions).toHaveLength(1);
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
      // The one formal finish submitted exactly one completion
      // acknowledgement (authored-dialogue-reading-client) and no selection.
      expect(sender.sent.actions.filter((action) => action.action_id === "explore.talk_scripted")).toHaveLength(0);
      expect(
        sender.sent.actions.filter((action) => action.action_id === "explore.dialogue_complete"),
      ).toHaveLength(1);
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

  // authored-dialogue-locked-ui: a visibly locked topic is a selectable
  // refusal through the same single dispatch entry and the same scene
  // player, for static and generated (opaque, up to 2048-character) topics.
  describe("locked topics", () => {
    const GENERATED_ID = `g.${"r".repeat(40)}.${"k".repeat(2048 - 43)}`;
    const openRow = (keyword, label) => choiceRow(keyword, { hostId: 7, topicId: `host.${keyword}`, label });
    const lockedRow = (keyword, label, hint, topicId = `host.${keyword}`) => ({
      ...choiceRow(keyword, { hostId: 7, topicId, label }),
      availability: "locked",
      requirement_hint: hint,
    });
    const CHOICES = [
      openRow("news", "最近有什麼消息？"),
      lockedRow("dream", "夢裡的約定", "需要好感階段至少為熟識", GENERATED_ID),
      openRow("town", "關於這座城鎮"),
    ];
    const pickRows = () => list().findAll('[data-testid="dialogue-pick"]');
    const activeRow = () => document.getElementById(list().attributes("aria-activedescendant"));
    const listKey = async (key) => {
      list().element.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
      await settle();
    };

    it("plays a generated locked topic's refusal through the ordinary player and returns to the choices", async () => {
      store.setTextSpeed?.("instant");
      await openDialogue(dialoguePanel({ choices: CHOICES }));
      await press();
      expect(list().exists()).toBe(true);
      list().element.focus();
      await listKey("ArrowDown");
      // Keyboard focus shows the canonical hint; the row stays selectable.
      expect(list().get('[data-testid="choice-card-tip"]').text()).toBe("需要好感階段至少為熟識");
      expect(pickRows()[1].attributes("aria-disabled")).toBeUndefined();
      await listKey("Enter");
      expect(sender.sent.actions).toHaveLength(1);
      expect(sender.sent.actions[0]).toMatchObject({
        action_id: "explore.talk_scripted",
        payload: { npc_id: 7, topic_id: GENERATED_ID, context_id: "ctx-1" },
      });
      expect(sender.sent.actions[0].payload.topic_id).toHaveLength(2048);
      expect(list().exists()).toBe(false);
      // The server answers with the authored refusal: the shared player
      // presents it line by line; no formal body ever arrives.
      store.receive(generation, "ui_action_result", [fx.actionResult({ presentation_revision: revision })], {});
      commit(
        "dialogue",
        scenePanel(
          [speech("actor", "夢裡的約定？"), speech("host", "等我們更熟一點再說吧。")],
          { kind: "refusal", topicId: GENERATED_ID, sceneId: `g.${"r".repeat(40)}.refusal_scene`, deliveryId: "dlv-refusal" },
          { choices: CHOICES },
        ),
      );
      await settle();
      expect(win().attributes("data-scene")).toBe("true");
      expect(frame()).toMatchObject({ text: "夢裡的約定？", plate: "旅人", actor: "true", host: "false" });
      expect(list().exists()).toBe(false);
      page().focus();
      await press();
      expect(frame()).toMatchObject({ text: "等我們更熟一點再說吧。", plate: "店長", actor: "false", host: "true" });
      expect(list().exists()).toBe(false);
      await press(); // the explicit finish
      expect(list().exists()).toBe(true);
      expect(document.activeElement).toBe(list().element);
      // Back at the choices: nothing further was submitted, and the topic is
      // still the server's locked row (the client unlocks nothing).
      expect(sender.sent.actions).toHaveLength(1);
      expect(pickRows()[1].attributes("data-locked")).toBe("true");
    });

    it("moves focus to the nearest remaining choice when a refresh hides the focused topic", async () => {
      store.setTextSpeed?.("instant");
      await openDialogue(dialoguePanel({ choices: CHOICES }));
      await press();
      list().element.focus();
      await listKey("ArrowDown");
      expect(activeRow()).toBe(pickRows()[1].element);
      commit("dialogue", dialoguePanel({ choices: [CHOICES[0], CHOICES[2]] }));
      await settle();
      expect(list().exists()).toBe(true);
      expect(document.activeElement).toBe(list().element);
      expect(pickRows().map((row) => row.get(".dialogue-choices__label").text())).toEqual(["最近有什麼消息？", "關於這座城鎮"]);
      expect(activeRow()).toBe(pickRows()[1].element);
      expect(list().find('[data-testid="choice-card-tip"]').exists()).toBe(false);
      expect(sender.sent.actions).toHaveLength(0);
    });

    it("keeps the playing line, plate and portrait emphasis when choices refresh mid-scene", async () => {
      store.setTextSpeed?.("instant");
      await openDialogue(scenePanel(SCENE_LINES, {}, { choices: CHOICES }));
      page().focus();
      await press();
      const before = frame();
      expect(before).toMatchObject({ text: "北岸大道最近不太平。", host: "true", actor: "false" });
      // A committed availability refresh: the locked topic opens, a fifth
      // topic appears. The playing scene does not change and stays covered.
      const refreshed = [
        CHOICES[0],
        { ...CHOICES[1], availability: "open", requirement_hint: null },
        CHOICES[2],
        openRow("road", "北岸大道"),
        openRow("night", "夜裡的路"),
      ];
      commit("dialogue", scenePanel(SCENE_LINES, {}, { choices: refreshed }));
      await settle();
      expect(frame()).toEqual(before);
      expect(list().exists()).toBe(false);
      await press();
      await press();
      await press(); // the finish
      expect(list().exists()).toBe(true);
      expect(pickRows()).toHaveLength(5);
      expect(pickRows()[1].attributes("data-locked")).toBeUndefined();
      // Only the formal finish's completion acknowledgement was submitted.
      expect(
        sender.sent.actions.filter((action) => action.action_id !== "explore.dialogue_complete"),
      ).toHaveLength(0);
    });
  });

  // authored-dialogue-reading-client: the formal finish is acknowledged once
  // through the memory-only queue, the status is observable at the
  // return-to-choices boundary, and a pre-delivered public successor may play
  // before its predecessor's acknowledgement saved.
  describe("the memory-only reading acknowledgement", () => {
    const TWO_LINES = [speech("actor", "嗯？"), speech("host", "好。")];
    const acks = () => sender.sent.actions.filter((action) => action.action_id === "explore.dialogue_complete");
    const answer = (requestId, overrides = {}) =>
      store.receive(
        generation,
        "ui_action_result",
        [
          fx.actionResult({
            request_id: requestId,
            presentation_revision: store.view.revision,
            ...overrides,
          }),
        ],
        {},
      );

    it("acknowledges one formal finish, reports pending, retries once, and never rereads", async () => {
      store.setTextSpeed?.("instant");
      await openDialogue(
        scenePanel(TWO_LINES, { deliveryId: "dlv-read", topicId: "host.news", sceneId: "host.news_scene" }),
      );
      page().focus();
      await press();
      await press(); // the explicit finish

      expect(acks()).toHaveLength(1);
      expect(acks()[0].payload).toEqual({
        npc_id: 7,
        delivery_id: "dlv-read",
        context_id: "ctx-1",
        topic_id: "host.news",
        scene_revision: "r1",
      });
      // No selection was repeated: the finish is not a reread.
      expect(sender.sent.actions.filter((action) => action.action_id === "explore.talk_scripted")).toHaveLength(0);
      const status = wrapper.get('[data-testid="dialogue-reading-status"]');
      expect(status.attributes("data-state")).toBe("pending");
      expect(wrapper.find('[data-testid="dialogue-reading-retry"]').exists()).toBe(false);
      expect(pageText()).toBe("好。");

      // A reply naming any other attempt never clears this entry.
      answer("session:77", { code: "dialogue_completed" });
      await settle();
      expect(store.view.dialogueReading.pendingCount).toBe(1);

      // An operational rejection leaves the entry unsaved and offers retry.
      answer(acks()[0].request_id, { outcome: "rejected", code: "busy", message: "另一項操作正在進行中" });
      await settle();
      expect(store.view.dialogueReading.retryable).toBe(true);
      expect(wrapper.get('[data-testid="dialogue-reading-status"]').attributes("data-state")).toBe("failed");
      await wrapper.get('[data-testid="dialogue-reading-retry"]').trigger("click");
      expect(acks()).toHaveLength(2);
      expect(acks()[1].payload).toEqual(acks()[0].payload);
      expect(acks()[1].request_id).not.toBe(acks()[0].request_id);

      answer(acks()[1].request_id, { code: "dialogue_completed" });
      await settle();
      expect(store.view.dialogueReading.pendingCount).toBe(0);
      expect(wrapper.find('[data-testid="dialogue-reading-status"]').exists()).toBe(false);
      expect(list().exists()).toBe(true);
      // The one finished line never reappeared: no replay, no reread.
      expect(pageText()).toBe("好。");
      expect(sender.sent.actions.filter((action) => action.action_id === "explore.talk_scripted")).toHaveLength(0);
    });

    it("plays a pre-delivered public successor and queues its acknowledgement behind the predecessor", async () => {
      store.setTextSpeed?.("instant");
      const root = sceneDelivery(TWO_LINES, {
        deliveryId: "dlv-root",
        topicId: "host.news",
        sceneId: "host.news_scene",
        revision: "r1",
      });
      const child = sceneDelivery([speech("actor", "再說？"), speech("host", "接續。")], {
        deliveryId: "dlv-child",
        topicId: "host.news_more",
        sceneId: "host.news_more_scene",
        revision: "r2",
      });
      const chain = [{ delivery: child, predecessors: ["host.news"] }];
      await openDialogue(dialoguePanel({ delivery: root, pureChain: chain }));
      page().focus();
      await press();
      await press(); // finish the root

      expect(acks()).toHaveLength(1);
      expect(acks()[0].payload.topic_id).toBe("host.news");
      // The already-delivered successor plays from its first line.
      expect(pageText()).toBe("再說？");
      expect(list().exists()).toBe(false);

      // A reading-revision-only update of the same delivery must not replace
      // or restart the playing successor.
      commit("dialogue", dialoguePanel({ delivery: root, pureChain: chain, readingRevision: 1 }));
      await settle();
      expect(pageText()).toBe("再說？");

      await press(); // the successor's second line
      await press(); // finish the successor
      // Its acknowledgement waits for the unsaved predecessor.
      expect(acks()).toHaveLength(1);
      expect(store.view.dialogueReading.pendingCount).toBe(2);

      answer(acks()[0].request_id, { code: "dialogue_completed" });
      await settle();
      expect(acks()).toHaveLength(2);
      expect(acks()[1].payload).toMatchObject({
        delivery_id: "dlv-child",
        topic_id: "host.news_more",
        scene_revision: "r2",
      });
    });
  });
  // authored-dialogue-unread-notices: an unlock batch pushed while a scene
  // plays waits for the explicit finish, then shows one status toast without
  // taking focus; the persistent pip marks the row.
  it("defers an unlock notice until the scene returns the choices and keeps focus", async () => {
    const unread = (panel) => ({
      ...panel,
      choices: panel.choices.map((choice) => ({ ...choice, unread: choice.topic_id === "host.town" })),
    });
    await openDialogue(unread(scenePanel([speech("actor", "嗯？"), speech("host", "好。")])));
    page().focus();
    const batched = unread(scenePanel([speech("actor", "嗯？"), speech("host", "好。")]));
    batched.unlock_batch = { batch_id: "u".repeat(32), host_id: 7, context_id: "ctx-1", topic_ids: ["host.town"] };
    commit("dialogue", batched);
    await settle();
    const toasts = () => store.view.toasts.filter((toast) => toast.tone === "unlock");
    await press(); // complete line 1
    await press(); // line 2
    await press(); // line 2 complete
    expect(toasts()).toEqual([]);
    expect(list().exists()).toBe(false);
    await press(); // the explicit finish
    await settle();
    expect(list().exists()).toBe(true);
    expect(toasts()).toHaveLength(1);
    expect(toasts()[0].chips).toEqual(["關於這座城鎮"]);
    const toast = wrapper.get(`[data-testid="feedback-toast-${toasts()[0].id}"]`);
    expect(toast.attributes("role")).toBe("status");
    expect(toast.attributes("data-tone")).toBe("unlock");
    expect(toast.element.contains(document.activeElement)).toBe(false);
    expect(document.activeElement).toBe(list().element);
    const town = list().findAll('[role="menuitem"]')[1];
    expect(town.attributes("data-unread")).toBe("true");
    // A later publication of the same batch never shows a second notice.
    commit("dialogue", batched);
    await settle();
    expect(toasts()).toHaveLength(1);
  });
});
