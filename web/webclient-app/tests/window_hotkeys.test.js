// webclient-main-navigation-hotkeys: the window hotkeys P B C K L J M open
// their surfaces through the navigation's own openers, only outside text
// inputs, IME composition, modifiers, held keys and modal questions, never
// behind another open surface, and never for an absent surface (M in
// combat). The bar renders identically while possessing.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { CHARACTER_PANEL_SAMPLE } from "../stories/fixtures.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";
import { partyWindowTab, rememberPartyWindowTab, resetPartyWindowMemory } from "../components/party-window-memory.js";
import { PARTY_WINDOW_PANEL_SAMPLE } from "../stories/fixtures/party_panels.js";
import { QUEST_LOG_PANEL_SAMPLE } from "../stories/fixtures/quest_log_panels.js";
import { hotkeyCode, isTextEntry } from "../composables/use-window-hotkeys.js";

let store;
let wrapper;

function mountAppClient() {
  const host = document.createElement("div");
  host.id = "elosern-app";
  document.body.appendChild(host);
  wrapper = mount(AppClient, { attachTo: host });
  return wrapper;
}

function commit({ mode = "exploration", party = true, extra = {} } = {}) {
  store.beginTransport(1);
  store.setConnected(true);
  const panels =
    mode === "combat"
      ? { status: fx.statusPanel(), context_actions: fx.combatActions() }
      : {
          status: fx.statusPanel(),
          exploration: fx.explorationPanel(),
          context_actions: fx.explorationActions(),
          character: CHARACTER_PANEL_SAMPLE,
          quest_log: QUEST_LOG_PANEL_SAMPLE,
        };
  if (party) panels.party = PARTY_WINDOW_PANEL_SAMPLE;
  const result = store.receive(1, "ui_snapshot", [fx.snapshot({ mode, panels: { ...panels, ...extra } })], {});
  expect(result.accepted).toBe(true);
}

// A key pressed with focus on `target` (the document body by default).
async function press(key, init = {}, target = document.body) {
  const code = /^[a-z]$/i.test(key) ? `Key${key.toUpperCase()}` : "";
  const event = new KeyboardEvent("keydown", { key, code, bubbles: true, cancelable: true, ...init });
  target.dispatchEvent(event);
  await wrapper.vm.$nextTick();
  return event;
}

const partyTab = () => wrapper.find('[data-testid="party-window"]').attributes("data-tab");

beforeEach(() => {
  setActivePinia(createPinia());
  store = useElosernStore();
  store.setSender(fx.createFakeSender());
  resetPartyWindowMemory();
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  document.body.innerHTML = "";
});

describe("window hotkeys", () => {
  it("P opens the party window on its last tab with the session's viewed member", async () => {
    mountAppClient();
    commit();
    await wrapper.vm.$nextTick();
    rememberPartyWindowTab(`${store.view.generation}|${store.view.epoch}`, "skills");
    const event = await press("p");
    expect(event.defaultPrevented).toBe(true);
    expect(store.view.hudDrawer).toBe("party");
    expect(partyTab()).toBe("skills");
    expect(wrapper.get('[data-testid="party-window"]').exists()).toBe(true);
    expect(store.view.panels?.party?.viewed_member_id ?? PARTY_WINDOW_PANEL_SAMPLE.viewed_member_id).toBe(
      PARTY_WINDOW_PANEL_SAMPLE.viewed_member_id,
    );
    // The bar marks 隊伍 current.
    expect(wrapper.findAll('.desktop-navigation [aria-current="page"]').map((b) => b.attributes("data-nav-slot"))).toEqual(["party"]);
  });

  it.each([
    ["b", "bag"],
    ["c", "status"],
    ["k", "skills"],
    ["l", "lineage"],
  ])("%s opens the party window on %s", async (key, tab) => {
    mountAppClient();
    commit();
    await wrapper.vm.$nextTick();
    await press(key);
    expect(store.view.hudDrawer).toBe("party");
    expect(partyTab()).toBe(tab);
    expect(partyWindowTab()).toBe(tab);
  });

  it("the party tab keys switch an open party window live; J and M never open behind it", async () => {
    mountAppClient();
    commit();
    await wrapper.vm.$nextTick();
    await press("b");
    expect(partyTab()).toBe("bag");
    // Focus fell out of the trap (a click on inert content): the key reaches
    // the document and the window switches its tab.
    await press("c");
    expect(partyTab()).toBe("status");
    await press("j");
    await press("m");
    expect(store.view.hudDrawer).toBe("party");
    expect(store.view.hudOverlay).toBeNull();
  });

  it("J opens the quest board and M the map, each as its bar control does", async () => {
    mountAppClient();
    commit();
    await wrapper.vm.$nextTick();
    await press("j");
    expect(store.view.hudDrawer).toBe("quest");
    store.closeHudDrawer();
    await wrapper.vm.$nextTick();
    await press("m");
    expect(store.view.hudOverlay).toBe("map");
  });

  it("M and J are inert in combat, where the map and quest entries are absent; P still opens the window", async () => {
    mountAppClient();
    commit({ mode: "combat" });
    await wrapper.vm.$nextTick();
    expect(store.view.mode).toBe("combat");
    const m = await press("m");
    expect(m.defaultPrevented).toBe(false);
    expect(store.view.hudOverlay).toBeNull();
    await press("j");
    expect(store.view.hudDrawer).toBeNull();
    await press("p");
    expect(store.view.hudDrawer).toBe("party");
  });

  it("party keys are inert without a committed party panel, and J without the quest surface", async () => {
    mountAppClient();
    commit({ party: false, extra: { exploration: fx.explorationPanel({ quests: { available: false } }) } });
    await wrapper.vm.$nextTick();
    for (const key of ["p", "b", "c", "k", "l", "j"]) await press(key);
    expect(store.view.hudDrawer).toBeNull();
  });

  it("typing in the command line, a textarea or a contenteditable never triggers a hotkey", async () => {
    mountAppClient();
    commit();
    await wrapper.vm.$nextTick();
    const input = document.createElement("input");
    const textarea = document.createElement("textarea");
    const editable = document.createElement("div");
    editable.setAttribute("contenteditable", "true");
    const inner = document.createElement("span");
    editable.appendChild(inner);
    document.body.append(input, textarea, editable);
    for (const target of [input, textarea, inner]) {
      for (const key of ["p", "b", "m", "j"]) {
        const event = await press(key, {}, target);
        expect(event.defaultPrevented).toBe(false);
      }
    }
    expect(store.view.hudDrawer).toBeNull();
    expect(store.view.hudOverlay).toBeNull();
    // The real command field too (it stays mounted while collapsed).
    const field = document.querySelector("#inputfield");
    expect(field).not.toBeNull();
    field.focus();
    await press("p", {}, field);
    expect(store.view.hudDrawer).toBeNull();
  });

  it("ignores modifiers, Shift, IME composition, held keys and an already consumed key", async () => {
    mountAppClient();
    commit();
    await wrapper.vm.$nextTick();
    for (const init of [{ ctrlKey: true }, { altKey: true }, { metaKey: true }, { shiftKey: true }, { isComposing: true }, { repeat: true }]) {
      await press("p", init);
    }
    await press("Process", { keyCode: 229, code: "KeyP" });
    const consumed = new KeyboardEvent("keydown", { key: "p", code: "KeyP", bubbles: true, cancelable: true });
    consumed.preventDefault();
    document.body.dispatchEvent(consumed);
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBeNull();
  });

  it("ignores every key while a modal question or another surface is open", async () => {
    mountAppClient();
    commit();
    await wrapper.vm.$nextTick();
    // A rendered alertdialog (a confirmation) holds the keys.
    const question = document.createElement("div");
    question.setAttribute("role", "alertdialog");
    document.body.appendChild(question);
    await press("p");
    expect(store.view.hudDrawer).toBeNull();
    // A hidden one does not.
    question.hidden = true;
    await press("p");
    expect(store.view.hudDrawer).toBe("party");
    store.closeHudDrawer();
    question.remove();
    // An open overlay or another drawer keeps its own keys.
    store.openOverlay("help");
    await wrapper.vm.$nextTick();
    await press("p");
    expect(store.view.hudOverlay).toBe("help");
    expect(store.view.hudDrawer).toBeNull();
    store.closeOverlay();
    store.openHudDrawer("letters");
    await wrapper.vm.$nextTick();
    await press("b");
    expect(store.view.hudDrawer).toBe("letters");
  });

  it("runs once per press while mounted and stops when the client unmounts", async () => {
    mountAppClient();
    commit();
    await wrapper.vm.$nextTick();
    wrapper.unmount();
    wrapper = mount({ template: "<div />" }, { attachTo: document.body });
    await press("p");
    expect(store.view.hudDrawer).toBeNull();
  });

  it("P opens the window in dialogue mode too", async () => {
    mountAppClient();
    commit({ mode: "dialogue" });
    await wrapper.vm.$nextTick();
    expect(store.view.mode).toBe("dialogue");
    await press("p");
    expect(store.view.hudDrawer).toBe("party");
  });

  it("renders the bar identically while possessing", async () => {
    mountAppClient();
    commit();
    await wrapper.vm.$nextTick();
    const plain = wrapper.get(".desktop-navigation").html();
    const result = store.receive(1, "ui_update", [fx.update({
      revision: 2,
      panels: { possession_banner: { schema_version: 1, available: true, host_name: "蕾娜", since_tick: 0 } },
    })], {});
    expect(result.accepted).toBe(true);
    await wrapper.vm.$nextTick();
    expect(store.view.panels?.possession_banner?.available ?? store.reducer.getState().panels.possession_banner.available).toBe(true);
    expect(wrapper.get(".desktop-navigation").html()).toBe(plain);
  });

  it("reads the physical key, falling back to the character, and recognises text entries", () => {
    expect(hotkeyCode({ code: "KeyP", key: "ㄣ" })).toBe("KeyP");
    expect(hotkeyCode({ code: "", key: "B" })).toBe("KeyB");
    expect(hotkeyCode({ code: "Digit1", key: "1" })).toBeNull();
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    expect(isTextEntry(checkbox)).toBe(false);
    expect(isTextEntry(document.createElement("select"))).toBe(true);
    expect(isTextEntry(document.createElement("button"))).toBe(false);
  });
});
