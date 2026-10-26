// webclient-immutable-adoption: the live client reads one immutable committed
// record, and a complete same-mode alignment preserves valid local UI state.
//
// The store-level contract (reference retention, adoption isolation, one
// notification per publication) is proven by the dependency-free Node suite
// (web/static/webclient/js/tests/protocol_immutable.test.js). This suite covers
// what only the composed Vue client can show: the view projects the committed
// record instead of a private copy, a hostile consumer cannot write through
// resolved menus or the published view, an equal alignment keeps the open
// drawer/focus/unsaved text without remounting, the existing semantic teardown
// still runs, and playback is never replayed by an equal checkpoint.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";

import AppClient from "../AppClient.vue";
import CombatMenu from "../lib/combat_menu.js";
import { resetPartyWindowMemory } from "../components/party-window-memory.js";
import { useElosernStore } from "../stores/elosern.js";
import { CHARACTER_PANEL_SAMPLE } from "../stories/fixtures.js";
import {
  PARTY_MEMBER_PANEL_SAMPLE,
  PARTY_PANEL_EMPTY_SAMPLE,
} from "../stories/fixtures/party_panels.js";
import * as fx from "./store/protocol_fixtures.js";
import {
  dialoguePanel as v3Panel,
  sceneDelivery,
  speech,
} from "./support/dialogue_panel.js";

const ATTACK_KEY = CombatMenu.BASIC_ATTACK_KEY;
const HOST = 7;
const CTX = "ctx-1";
const FOE = "7";
const PLAYER = "42";
const ROUND = "s-1/1";

function dialoguePanel() {
  return v3Panel({
    hostId: HOST,
    hostName: "店長",
    actorId: 1,
    actorName: "旅人",
    contextId: CTX,
    line: "歡迎來到西風酒館。",
    keywords: ["news"],
    labels: ["最近有什麼消息？"],
  });
}

// The four panels one exploration-form client always commits, plus whatever a
// case adds.
function explorationPanels(extra = {}) {
  return {
    status: fx.statusPanel(),
    exploration: fx.explorationPanel(),
    context_actions: fx.explorationActions(),
    local_map: fx.localMapPanel(),
    ...extra,
  };
}

function combatParticipants() {
  return [
    {
      identity: 7,
      token: "e1",
      display_name: "灰袍盜賊",
      team: "foes",
      state: "active",
      hp_current: 80,
      hp_maximum: 80,
      portrait_ref: FOE,
      conditions: [],
    },
    {
      identity: 42,
      token: "a1",
      display_name: "影行者",
      team: "party",
      state: "active",
      hp_current: 80,
      hp_maximum: 100,
      portrait_ref: PLAYER,
      conditions: [],
    },
  ];
}

function beatPanel() {
  return {
    schema_version: 1,
    available: true,
    round: ROUND,
    beats: [
      {
        seq: 0,
        action: 0,
        kind: "roll",
        actor: PLAYER,
        target: FOE,
        amount: null,
        hp_after: null,
        text: "你擲出了骰子。",
      },
      {
        seq: 1,
        action: 1,
        kind: "damage",
        actor: PLAYER,
        target: FOE,
        amount: 12,
        hp_after: 68,
        text: "你擊中了灰袍盜賊，造成 12 點傷害。",
      },
    ],
  };
}

function formalDelivery() {
  return sceneDelivery(
    [speech("actor", "最近有什麼消息？"), speech("host", "北岸大道最近不太平。")],
    {
      deliveryId: "dlv-1",
      contextId: CTX,
      topicId: "host.news",
      sceneId: "host.news_scene",
      revision: "r1",
      kind: "formal",
    },
  );
}

function deliveryDetail(delivery) {
  return {
    npc_id: HOST,
    delivery_id: delivery.delivery_id,
    context_id: delivery.context_id,
    topic_id: delivery.topic_id,
    scene_id: delivery.scene_id,
    scene_revision: delivery.scene_revision,
    kind: delivery.kind,
  };
}

describe("the live client reads the committed record", () => {
  let store;
  let revision;
  // The record the reducer published last, captured through the app's public
  // subscription seam (the store does not expose its reducer).
  let committed;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    store.subscribe((record) => {
      committed = record;
    });
    revision = 1;
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
  });

  function commit(panels, extra = {}) {
    const response = store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ revision, panels, ...extra })],
      {},
    );
    expect(response.accepted, JSON.stringify(response)).toBe(true);
    revision += 1;
    return response;
  }

  it("projects the committed panel values by reference instead of copying them", () => {
    commit(explorationPanels());
    expect(Object.isFrozen(committed)).toBe(true);
    expect(Object.isFrozen(committed.panels)).toBe(true);
    expect(Object.isFrozen(committed.panels.status.resources)).toBe(true);
    // The view is a projection of that record, not a private deep copy.
    expect(store.view.panels.status).toBe(committed.panels.status);
    expect(store.view.panels.exploration).toBe(committed.panels.exploration);
  });

  it("keeps the unchanged panels and the published view by identity across a delta", () => {
    commit(explorationPanels());
    const before = store.view;
    const exploration = before.panels.exploration;

    // An exact-base delta replacing only `status`.
    const delta = store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision,
          panels: { status: fx.statusPanel({ disguise_active: true }) },
        }),
      ],
      {},
    );
    expect(delta.accepted, JSON.stringify(delta)).toBe(true);
    revision += 1;
    expect(store.view).not.toBe(before);
    expect(store.view.panels.exploration).toBe(exploration);
    expect(store.view.panels.status).not.toBe(before.panels.status);
    expect(store.view.panels.status.disguise_active).toBe(true);
  });

  it("publishes one frozen record that subscribers and the getter both see", () => {
    commit(explorationPanels());
    const seen = [];
    const stop = store.subscribe((record) => seen.push(record));
    commit(explorationPanels());
    stop();
    expect(seen).toHaveLength(1);
    expect(seen[0]).toBe(committed);
    expect(Object.isFrozen(seen[0])).toBe(true);
  });

  it("a hostile consumer cannot write through the published view or a resolved menu", () => {
    commit(explorationPanels());
    const authoritative = committed.panels.status.resources.hp.current;

    // The view carries committed values, and this module is strict-mode ESM.
    expect(() => {
      store.view.panels.status.resources.hp.current = 0;
    }).toThrow(TypeError);
    expect(committed.panels.status.resources.hp.current).toBe(authoritative);

    // Resolved menus are the consumer's own copy (`isolate`), so editing one is
    // allowed and still cannot reach committed state; the next resolution is
    // the committed truth again.
    const descriptor = { source: "exploration.navigation", params: {} };
    const menu = store.resolveFrame(descriptor);
    expect(menu.items.map((item) => item.key)).toEqual(["character", "quests", "inventory"]);
    const label = menu.items[0].label;
    menu.items[0].label = "改寫";
    menu.items.push({ key: "t_injected", label: "注入" });
    menu.items.length = 1;
    expect(store.resolveFrame(descriptor).items[0].label).toBe(label);
    expect(store.resolveFrame(descriptor).items.map((item) => item.key)).toEqual([
      "character",
      "quests",
      "inventory",
    ]);
    expect(() => {
      committed.panels.exploration.move.push({});
    }).toThrow(TypeError);
  });
});

describe("a complete same-mode alignment preserves local interaction state", () => {
  let store;
  let wrapper;
  let revision;

  beforeEach(async () => {
    resetPartyWindowMemory();
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    wrapper = mount(AppClient, { attachTo: document.body });
    revision = 1;
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    commit(explorationPanels(partyPanels()));
    await nextTick();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.replaceChildren();
  });

  function partyPanels() {
    return {
      character: CHARACTER_PANEL_SAMPLE,
      party: PARTY_PANEL_EMPTY_SAMPLE,
      party_member: PARTY_MEMBER_PANEL_SAMPLE,
    };
  }

  function commit(panels, extra = {}) {
    const response = store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ revision, panels, ...extra })],
      {},
    );
    expect(response.accepted, JSON.stringify(response)).toBe(true);
    revision += 1;
  }

  // Open the 成員 tab's persona editor and leave unsaved text in its field.
  async function openPersonaDraft(text) {
    store.openHudDrawer("status");
    await nextTick();
    await wrapper.get('[data-testid="icon-tabs__tab--member"]').trigger("click");
    await nextTick();
    await wrapper.get('[data-testid="action-bar__btn--persona-edit"]').trigger("click");
    await wrapper.get('[data-testid="party-member-tab__persona-edit--life_story"]').trigger("click");
    const input = wrapper.get('[data-testid="party-member-tab__persona-input--life_story"]');
    await input.setValue(text);
    input.element.focus();
    return input;
  }

  it("keeps the open drawer, the focused field and its unsaved text without remounting", async () => {
    const input = await openPersonaDraft("還沒送出的草稿");
    const drawer = wrapper.get('[data-testid="hud-drawer"]');
    const drawerElement = drawer.element;
    const windowElement = wrapper.get('[data-testid="party-window"]').element;
    const rootElement = wrapper.get('[data-testid="elosern-client-root"]').element;

    // A checkpoint commits the same identity with a newer revision and a fresh
    // object graph for the same panels.
    commit(explorationPanels(partyPanels()));
    await nextTick();

    expect(store.view.hudDrawer).toBe("party");
    expect(wrapper.get('[data-testid="hud-drawer"]').element).toBe(drawerElement);
    expect(wrapper.get('[data-testid="party-window"]').element).toBe(windowElement);
    expect(wrapper.get('[data-testid="elosern-client-root"]').element).toBe(rootElement);
    const kept = wrapper.get('[data-testid="party-member-tab__persona-input--life_story"]');
    expect(kept.element).toBe(input.element);
    expect(kept.element.value).toBe("還沒送出的草稿");
    expect(document.activeElement).toBe(input.element);
  });

  it("still tears the drawer down on a mode change into creation", async () => {
    await openPersonaDraft("跨模式的草稿");
    commit(explorationPanels(partyPanels()), { mode: "creation" });
    await nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(false);
  });

  it("still closes the drawer when its backing panel becomes unavailable", async () => {
    await openPersonaDraft("面板消失的草稿");
    commit(
      explorationPanels({
        ...partyPanels(),
        party: {
          schema_version: 3,
          available: false,
          reason: { code: "presentation_unavailable", message: "隊伍暫時無法顯示" },
        },
      }),
    );
    await nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(false);
  });
});

describe("an equal checkpoint never replays playback", () => {
  let store;
  let sender;
  let revision;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    store.setTextSpeed?.("instant");
    revision = 1;
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
  });

  function commit(mode, panels) {
    const response = store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ revision, mode, panels })],
      {},
    );
    expect(response.accepted, JSON.stringify(response)).toBe(true);
    revision += 1;
  }

  it("keeps a settled dialogue delivery settled across the equal snapshot", () => {
    commit("dialogue", explorationPanels({ dialogue: dialoguePanel() }));
    const delivery = formalDelivery();
    const detail = deliveryDetail(delivery);
    const key = store.finishDialogueDelivery(detail);
    expect(key).toBeTruthy();
    const sendsAfterFinish = sender.sent.actions.length;
    expect(sendsAfterFinish).toBe(1);

    // The server acknowledges the one completion: the acknowledgement is
    // settled, not still pending, before the checkpoint arrives.
    const acknowledgement = sender.sent.actions[sendsAfterFinish - 1];
    expect(
      store.receive(
        1,
        "ui_action_result",
        [
          fx.actionResult({
            request_id: acknowledgement.request_id,
            code: "dialogue_completed",
            presentation_revision: revision,
          }),
        ],
        {},
      ).accepted,
    ).toBe(true);
    const settled = store.view.dialogueReading;
    expect(settled.pending).toEqual([]);

    // The equal checkpoint republishes the identical dialogue panel: the
    // committed value keeps its identity, the settled reading is unchanged, and
    // no further acknowledgement is sent.
    const dialogueBefore = store.view.panels.dialogue;
    commit("dialogue", explorationPanels({ dialogue: dialoguePanel() }));
    expect(store.view.panels.dialogue).toBe(dialogueBefore);
    expect(store.view.dialogueReading).toEqual(settled);
    expect(sender.sent.actions).toHaveLength(sendsAfterFinish);
  });

  it("keeps a committed combat round from being presented a second time", async () => {
    // The playback advances on the motion tokens' own timers; the fake clock
    // makes its finish deterministic without measuring it.
    vi.useFakeTimers();
    try {
    commit("combat", {
      status: fx.statusPanel(),
      context_actions: fx.combatActions({ participants: combatParticipants() }),
    });
    store.setMotionLevel("full");

    // The round's lines, then its publication, then the result that binds it:
    // exactly the wire order the beat queue expects.
    const requestId = store.dispatchAction("combat.command", ATTACK_KEY);
    store.appendText("out", "你擲出了骰子。");
    store.appendText("out", "你擊中了灰袍盜賊，造成 12 點傷害。");
    const published = revision;
    // The concluding round is published by a post-combat mode: that is what
    // makes it a terminal round the client holds until its playback ends.
    const update = store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: published,
          mode: "exploration",
          panels: {
            ...explorationPanels(),
            combat_beats: beatPanel(),
          },
        }),
      ],
      {},
    );
    expect(update.accepted).toBe(true);
    revision = published + 1;
    store.receive(
      1,
      "ui_action_result",
      [fx.actionResult({ request_id: requestId, presentation_revision: published })],
      {},
    );
    const bound = store.view.beatPlayback;
    expect(bound).not.toBeNull();
    expect(bound.round).toBe(ROUND);
    expect(bound.texts).toHaveLength(2);
    expect(bound.terminal).toBe(true);
    expect(store.view.beatHold).toBe(true);

    // Play the round out exactly as the message window reports it (each beat
    // shown, then its own act and pause), so a replay would restart it at
    // index 0 and phase "text".
    for (let step = 0; step < 6; step++) {
      const playback = store.view.beatPlayback;
      if (playback.phase === "done") break;
      if (playback.phase === "text") store.beatShown(playback.index);
      vi.advanceTimersByTime(20000);
    }
    const finished = store.view.beatPlayback;
    expect(finished.phase).toBe("done");
    expect(finished.index).toBe(finished.count - 1);
    const narrativeLines = store.narrative.length;

    // An equal checkpoint of the same terminal round, mode included.
    commit("exploration", { ...explorationPanels(), combat_beats: beatPanel() });
    const afterCheckpoint = store.view.beatPlayback;
    expect(afterCheckpoint.round).toBe(ROUND);
    expect(afterCheckpoint.terminal).toBe(true);
    expect(afterCheckpoint.phase).toBe("done");
    expect(afterCheckpoint.index).toBe(finished.index);
    expect(store.narrative).toHaveLength(narrativeLines);
    } finally {
      vi.useRealTimers();
    }
  });
});
