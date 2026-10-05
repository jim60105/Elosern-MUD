// webclient-avg-stage-shell (design D4) and webclient-dialogue-stage-actors
// (design D1/D2/D3/D5): the stage actors live in the portrait anchors. The
// player's StageActor stands in `actor-left` outside creation; the dialogue
// host's StageActor stands in `actor-right` only while the mode is dialogue
// and the committed panel is available, fed by the raw `art` catalog entry
// named by `host.portrait_ref`. The listener is dimmed from the in-flight
// speech action. The dock stays one mounted element across the mode flips,
// and focus moves to the dialogue's focus home on entering (the choice list,
// shown at once here because the log holds no unread line) and back to the
// dock on leaving.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import { ART_PANEL_SAMPLE } from "../stories/fixtures.js";
import * as fx from "./store/protocol_fixtures.js";

const HOST_ENTRY = {
  subject_key: "npc_7",
  status: "done",
  url: "/art/portraits/npc_7.webp",
  aspect_ratio: "3:4",
  alt: "店長的肖像",
  placeholder: null,
  face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
  stage: { scale: 1, x: 0, y: 0 },
  // builtin-silhouette-stage-fallback: the stage-eligible entry carries the
  // server-resolved built-in silhouette beside its own fields.
  origin: "runtime",
  fallback: {
    key: "elder",
    url: "/art/defaults/elder.webp",
    face_rect: { x: 0.35, y: 0.03, w: 0.29, h: 0.16 },
  },
  context: { name: "店長", role: "對話對象" },
};

function basePanels() {
  return {
    status: fx.statusPanel(),
    exploration: fx.explorationPanel(),
    context_actions: fx.explorationActions(),
    local_map: fx.localMapPanel(),
    art: { ...ART_PANEL_SAMPLE, portrait_catalog: { ...ART_PANEL_SAMPLE.portrait_catalog, 7: HOST_ENTRY } },
  };
}

function dialoguePanel(portraitRef = "7") {
  return {
    schema_version: 2,
    available: true,
    kind: "dialogue",
    host: { identity: 7, display_name: "店長", portrait_ref: portraitRef },
    bond_stage: "熟識",
    line: "歡迎來到西風酒館。",
    choices: [
      { keyword_id: "news", label: "最近有什麼消息？" },
      { keyword_id: "town", label: "關於這座城鎮" },
    ],
  };
}

describe("the stage actors in the portrait anchors", () => {
  let store, wrapper, revision;

  beforeEach(async () => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    commit("exploration");
    await nextTick();
  });
  afterEach(() => {
    wrapper.unmount();
    document.body.replaceChildren();
  });

  function commit(mode, dialogue = null) {
    const panels = basePanels();
    if (dialogue) {
      panels.dialogue = dialogue;
    }
    const response = store.receive(1, "ui_snapshot", [fx.snapshot({ revision, mode, panels })], {});
    expect(response.accepted).toBe(true);
    revision += 1;
  }

  const actorIn = (anchor) => wrapper.find(`[data-testid="anchor-${anchor}"] [data-testid="stage-actor"]`);

  it("stands the player in actor-left, lit, with actor-right empty outside dialogue", () => {
    const player = actorIn("actor-left");
    expect(player.exists()).toBe(true);
    expect(player.attributes("data-side")).toBe("left");
    expect(player.attributes("data-speaking")).toBe("true");
    const actorLeft = wrapper.get('[data-testid="anchor-actor-left"]');
    expect(actorLeft.findAll("button, a, input, textarea, select, [tabindex]")).toHaveLength(0);
    // Exactly one stage portrait, and none left behind in the backdrop.
    expect(wrapper.findAll('[data-testid="elosern-stage"] [data-testid="reference-artwork"]')).toHaveLength(1);
    // The host Transition (webclient-mode-transitions D3) holds no actor.
    expect(wrapper.get('[data-testid="anchor-actor-right"]').findAll('[data-testid="stage-actor"]')).toHaveLength(0);
  });

  it("stands the host in actor-right from the catalog entry the committed key names, only in dialogue", async () => {
    commit("dialogue", dialoguePanel("7"));
    await nextTick();
    const host = actorIn("actor-right");
    expect(host.exists()).toBe(true);
    expect(host.attributes("data-side")).toBe("right");
    expect(host.get("img").attributes("src")).toBe("/art/portraits/npc_7.webp");
    expect(host.findAll("button, a, input, textarea, select, [tabindex]")).toHaveLength(0);

    commit("exploration");
    await nextTick();
    // The host Transition (webclient-mode-transitions D3) holds no actor.
    expect(wrapper.get('[data-testid="anchor-actor-right"]').findAll('[data-testid="stage-actor"]')).toHaveLength(0);
  });

  it("stands only the active foes in actor-right in combat, from the committed catalog", async () => {
    // webclient-combat-foes-on-stage D1: the active foes in presenter order;
    // party members and non-active foes stay in the participant frame.
    const participants = [
      { identity: 1, token: "a1", display_name: "艾莉亞", team: "party", state: "active", hp_current: 80, hp_maximum: 100, portrait_ref: null },
      { identity: 7, token: "e1", display_name: "灰袍盜賊", team: "foes", state: "active", hp_current: 40, hp_maximum: 60, portrait_ref: "7" },
      { identity: 9, token: "e2", display_name: "逃兵", team: "foes", state: "fled", hp_current: 10, hp_maximum: 60, portrait_ref: null },
      { identity: 10, token: "e3", display_name: "哥布林", team: "foes", state: "active", hp_current: 30, hp_maximum: 30, portrait_ref: null },
    ];
    const response = store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ revision, mode: "combat", panels: { ...basePanels(), context_actions: fx.combatActions({ participants }) } })],
      {},
    );
    expect(response.accepted).toBe(true);
    revision += 1;
    await nextTick();
    const right = wrapper.get('[data-testid="anchor-actor-right"]');
    const slots = right.findAll('[data-testid="foe-slot"]');
    expect(slots.map((s) => s.attributes("data-portrait-ref"))).toEqual(["7", ""]);
    expect(slots[0].get("img").attributes("src")).toBe("/art/portraits/npc_7.webp");
    expect(slots[1].get("figcaption").text()).toBe("哥布林，無肖像");
    for (const actor of right.findAll('[data-testid="stage-actor"]')) {
      expect(actor.attributes("data-speaking")).toBe("true");
    }
    expect(right.findAll("button, a, input, textarea, select, [tabindex]")).toHaveLength(0);
    // The player still stands, lit, in actor-left.
    expect(actorIn("actor-left").attributes("data-speaking")).toBe("true");

    commit("exploration");
    await nextTick();
    expect(right.findAll('[data-testid="foe-lineup"]')).toHaveLength(0);
  });

  it("stands no foe line-up in dialogue, where the host stands", async () => {
    commit("dialogue", dialoguePanel("7"));
    await nextTick();
    const right = wrapper.get('[data-testid="anchor-actor-right"]');
    expect(right.findAll('[data-testid="foe-lineup"]')).toHaveLength(0);
    expect(right.findAll('[data-testid="stage-actor"]')).toHaveLength(1);
  });

  it("falls back to the host's name placeholder when the key is null or names no entry", async () => {
    commit("dialogue", dialoguePanel(null));
    await nextTick();
    let host = actorIn("actor-right");
    expect(host.find("img").exists()).toBe(false);
    expect(host.get(".reference-artwork__placeholder-glyph").text()).toBe("店");
    expect(host.get("figcaption").text()).toBe("店長，無肖像");

    commit("dialogue", dialoguePanel("999"));
    await nextTick();
    host = actorIn("actor-right");
    expect(host.find("img").exists()).toBe(false);
    expect(host.get("figcaption").text()).toBe("店長，無肖像");
  });

  it("renders no host actor while the dialogue panel is unavailable", async () => {
    commit("dialogue", { schema_version: 2, available: false, reason: { code: "dialogue_unavailable", message: "對話目前無法顯示" } });
    await nextTick();
    expect(actorIn("actor-right").exists()).toBe(false);
    expect(actorIn("actor-left").attributes("data-speaking")).toBe("true");
  });

  it("dims the listener: the player while the host speaks, the host while a pick is in flight", async () => {
    commit("dialogue", dialoguePanel("7"));
    await nextTick();
    expect(actorIn("actor-left").attributes("data-speaking")).toBe("false");
    expect(actorIn("actor-right").attributes("data-speaking")).toBe("true");

    // The choice list's pick: the single dispatch entry.
    expect(store.dispatchAction("explore.talk_scripted", { npc_id: 7, keyword_id: "news" }, null)).not.toBe(null);
    await nextTick();
    expect(store.view.dialogueSpeaker).toBe("player");
    expect(actorIn("actor-left").attributes("data-speaking")).toBe("true");
    expect(actorIn("actor-right").attributes("data-speaking")).toBe("false");

    // The reply's revision commits: the host speaks again.
    store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: revision })], {});
    commit("dialogue", { ...dialoguePanel("7"), line: "北岸大道最近不太平。" });
    await nextTick();
    expect(actorIn("actor-left").attributes("data-speaking")).toBe("false");
    expect(actorIn("actor-right").attributes("data-speaking")).toBe("true");
  });

  const choiceList = () => wrapper.get('[data-anchor="choices"] [data-testid="dialogue-choices"]').element;

  it("keeps one #action-dock element and moves focus to the choice list and back across the mode flips", async () => {
    const dock = document.getElementById("action-dock");
    dock.focus();
    commit("dialogue", dialoguePanel("7"));
    await nextTick();
    await nextTick();
    await nextTick();
    expect(document.getElementById("action-dock")).toBe(dock);
    expect(document.activeElement).toBe(choiceList());

    commit("exploration");
    await nextTick();
    await nextTick();
    expect(document.getElementById("action-dock")).toBe(dock);
    expect(document.activeElement).toBe(dock);
  });

  it("re-homes focus once when the conversation opens from a verb popover and again on leaving", async () => {
    document.getElementById("action-dock").focus();
    // The overview's person chip opens its verb popover (the dockSource
    // watcher's case), then the commit that opens the conversation closes it.
    expect(store.focusItemByKey("target-7")).toBe(true);
    expect(store.focusConfirm("keyboard")).toBe(true);
    await nextTick();
    expect(store.view.dockSource).toBe("exploration.target");
    commit("dialogue", dialoguePanel("7"));
    await nextTick();
    await nextTick();
    await nextTick();
    expect(store.view.dockDepth).toBe(1);
    await nextTick();
    expect(document.activeElement).toBe(choiceList());

    commit("exploration");
    await nextTick();
    await nextTick();
    expect(document.activeElement).toBe(document.getElementById("action-dock"));
  });
});
