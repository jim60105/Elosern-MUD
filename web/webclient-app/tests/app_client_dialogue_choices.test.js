// webclient-dialogue-choices-overlay D3/D4/D7/D8: the live wiring of the
// dialogue choice list. It renders in the stage's `choices` anchor only in
// dialogue with the panel available, once the message window reports the
// line fully read, and never while an action is in flight. Its four intents
// reach the store's single entry (a pick's `explore.talk_scripted`, the
// free row's borrow, an exit's overview payload, and the leave), focus
// moves onto it when it appears over the message window and parks on the
// message page before an activation dispatches.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

function dialoguePanel(overrides = {}) {
  return {
    schema_version: 2,
    available: true,
    kind: "dialogue",
    host: { identity: 7, display_name: "店長", portrait_ref: null },
    bond_stage: "熟識",
    line: "歡迎來到西風酒館。",
    choices: [
      { keyword_id: "news", label: "最近有什麼消息？" },
      { keyword_id: "town", label: "關於這座城鎮" },
    ],
    ...overrides,
  };
}

describe("the dialogue choice list over the stage", () => {
  let store, sender, wrapper, revision;

  beforeEach(async () => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    // `normal` speed: with no animation frame in jsdom, a new page stays
    // typing until the reader completes it.
    store.setTextSpeed?.("normal");
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
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
    const response = store.receive(1, "ui_snapshot", [fx.snapshot({ revision, mode, panels })], {});
    expect(response.accepted).toBe(true);
    revision += 1;
  }

  const list = () => wrapper.find('[data-anchor="choices"] [data-testid="dialogue-choices"]');
  const page = () => wrapper.get('[data-testid="message-page"]').element;
  const typing = () => wrapper.get('[data-testid="message-window"]').attributes("data-typing");

  async function openDialogue(panel = dialoguePanel()) {
    commit("dialogue", panel);
    await settle();
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
    await openDialogue({ schema_version: 2, available: false, reason: { code: "dialogue_unavailable", message: "對話目前無法顯示" } });
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
    page().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
    await settle();
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
    page().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
    await settle();
    expect(list().exists()).toBe(true);
    expect(document.activeElement).toBe(field);
  });

  it("a pick dispatches the scripted keyword, parks focus on the page, and hides the list while in flight", async () => {
    await openDialogue();
    list().element.focus();
    list().element.dispatchEvent(new KeyboardEvent("keydown", { key: "2", bubbles: true, cancelable: true }));
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.talk_scripted",
      payload: { npc_id: 7, keyword_id: "town" },
    });
    await settle();
    expect(list().exists()).toBe(false);
    expect(document.activeElement).toBe(page());
    // The reply commits (the in-flight record releases) and its line arrives
    // unread: the list stays away until it is read.
    store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: revision })], {});
    store.appendText("out", "店長說：北岸大道最近不太平。");
    commit("dialogue", dialoguePanel({ line: "北岸大道最近不太平。" }));
    await settle();
    expect(store.view.dispatch.inFlight).toBe(null);
    expect(list().exists()).toBe(false);
    page().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
    await settle();
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

  it("`↦ 移動…` then an exit dispatches the overview exit chip's payload", async () => {
    await openDialogue();
    await list().get('[data-testid="dialogue-move"]').trigger("click");
    const exitRows = list().findAll('[data-testid="dialogue-exit-row"]');
    const overviewExit = store.view.rootMenu.items.find((item) => item.actionId === "explore.move" && item.enabled !== false);
    expect(exitRows.length).toBeGreaterThan(0);
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
});
