// exploration-presence-rail (tasks 2.2, 3.2, 3.3): the AppClient wiring of
// the presence rail and the person focus. The rail on the stage floor, the
// verb card in the `choices` anchor (no request, no router frame), the
// cockpit stepping away around it (the command panel inert and dimmed, the
// map anchor away, the rail hidden), the standee and the speaker line, the
// card closing on Escape, on 返回, on 查看, on a departure (with the readout
// flash), and on a move, focus returning to the opener, the one StageActor
// element surviving the 交談 commit, the overflow card, the rail digits, the
// Tab chain compass → rail → footer, and the compass walk stopping when a
// card opens.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import { ART_PANEL_SAMPLE } from "../stories/fixtures.js";
import * as fx from "./store/protocol_fixtures.js";

// The exploration panel's schema v3 publishes `portrait_ref: null` on every
// interact target and entity, so a live medallion shows the initial and the
// focus standee the dialogue silhouette; the face-crop path is pinned at the
// component level (tests/world/presence_rail.test.js).
const CLERK = {
  identity: 7,
  display_name: "店長",
  portrait_ref: null,
  affordances: [
    { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
    { kind: "navigate", surface: "guild", label: "公會服務", enabled: true, disabled_reason: null },
  ],
};

function artPanel() {
  return ART_PANEL_SAMPLE;
}

describe("AppClient presence rail and person focus (exploration-presence-rail)", () => {
  let store;
  let wrapper;
  let sender;
  let revision;

  function exploration(overrides = {}) {
    return fx.explorationPanel({ interact: [CLERK], ...overrides });
  }

  async function mountWith(panel = exploration()) {
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          panels: {
            status: fx.statusPanel(),
            exploration: panel,
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
            art: artPanel(),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    await settle();
  }

  async function settle() {
    for (let i = 0; i < 4; i += 1) {
      await nextTick();
    }
  }

  async function commit(panels, extra = {}) {
    revision += 1;
    const result = store.receive(1, "ui_update", [fx.update({ revision, panels, ...extra })], {});
    expect(result.accepted).toBe(true);
    await settle();
  }

  const rail = () => wrapper.find('[data-anchor="presence"] [data-testid="presence-rail"]');
  const entry = (key) => wrapper.get(`[data-anchor="presence"] [data-entry-key="${key}"]`);
  const card = () => wrapper.find('[data-anchor="choices"] [data-testid="presence-card"]');
  const cardRows = () => card().findAll('[role="menuitem"]');
  const standee = () => wrapper.find('[data-testid="anchor-actor-right"] [data-testid="stage-actor"]');
  const stage = () => wrapper.get('[data-testid="elosern-stage"]');
  const readoutText = () => wrapper.get('[data-testid="exploration-readout-text"]').text();

  function key(element, name, init = {}) {
    element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("stands the rail on the stage floor with the host's medallion and the object's lozenge", async () => {
    await mountWith();
    expect(rail().exists()).toBe(true);
    expect(rail().findAll('[data-testid="presence-entry"]').map((el) => el.attributes("data-entry-key"))).toEqual([
      "target-7",
      "object-3",
    ]);
    expect(entry("target-7").get('[data-testid="presence-entry-initial"]').text()).toBe("店");
    expect(wrapper.find('#action-dock [data-item-key="target-7"]').exists()).toBe(false);
  });

  it("an empty room renders no rail and no placeholder", async () => {
    await mountWith(exploration({ interact: [], look: { entities: [], objects: [] } }));
    expect(wrapper.find('[data-anchor="presence"] [data-testid="presence-rail"]').exists()).toBe(false);
    expect(wrapper.find('[data-anchor="presence"] [data-testid="presence-entry"]').exists()).toBe(false);
    expect(wrapper.get('[data-anchor="presence"]').text()).toBe("");
  });

  it("hover explains: the readout shows the clerk's name over the affordance summary", async () => {
    await mountWith();
    await entry("target-7").trigger("mouseenter");
    expect(wrapper.get('[data-testid="exploration-readout-lead"]').text()).toBe("店長");
    expect(readoutText()).toBe("交談／公會服務");
    await entry("target-7").trigger("mouseleave");
    expect(readoutText()).toMatch(/^出口 \d · 在場 1$/);
  });

  it("opening is local: the verb card, the standee, the speaker line, and the cockpit stepping away", async () => {
    await mountWith();
    await entry("target-7").trigger("click");
    await settle();

    expect(sender.sent.actions).toHaveLength(0);
    expect(store.router.depth()).toBe(1);
    expect(cardRows().map((row) => row.text())).toEqual(["1交談", "2公會服務", "3查看", "返回"]);
    expect(document.activeElement).toBe(card().element);
    // The rail fades out (kept mounted, hidden and inert).
    expect(rail().attributes("style")).toContain("display: none");
    expect(rail().attributes("inert")).toBeDefined();
    // The command panel is inert and dims; the map anchor steps away.
    expect(stage().attributes("data-person-focus")).toBe("true");
    expect(stage().attributes("data-card-open")).toBe("true");
    expect(wrapper.get('[data-anchor="band-command"]').attributes("inert")).toBeDefined();
    expect(wrapper.get('[data-anchor="map"]').attributes("inert")).toBeDefined();
    // The standee in actor-right and the speaker line.
    expect(standee().exists()).toBe(true);
    expect(wrapper.get('[data-testid="message-name-plate"]').text()).toContain("店長");
  });

  it("a target without a portrait uses the dialogue silhouette treatment", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    expect(standee().exists()).toBe(true);
    expect(standee().find("img").exists()).toBe(false);
    expect(standee().text()).toContain("店長");
  });

  it("Escape and 返回 close the card and return focus to the medallion that opened it", async () => {
    await mountWith();
    for (const close of ["escape", "back-row"]) {
      await entry("target-7").trigger("click");
      await settle();
      expect(card().exists(), close).toBe(true);
      if (close === "escape") {
        key(card().element, "Escape");
      } else {
        await cardRows().at(-1).trigger("click");
      }
      await settle();
      expect(card().exists(), close).toBe(false);
      expect(standee().exists(), close).toBe(false);
      expect(stage().attributes("data-person-focus"), close).toBeUndefined();
      expect(document.activeElement, close).toBe(rail().element);
      expect(
        document.getElementById(rail().attributes("aria-activedescendant")).dataset.entryKey,
        close,
      ).toBe("target-7");
    }
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("查看 submits one explore.look and closes the card", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    key(card().element, "3");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.look", payload: { target_id: 7 } });
    expect(card().exists()).toBe(false);
    expect(document.activeElement).toBe(rail().element);
  });

  it("a card owns the digits: `1` picks its first row, never the rail's", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    key(card().element, "1");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({ action_id: "explore.talk_open", payload: { npc_id: 7 } });
  });

  it("the focused person leaves: the card closes in that commit and the readout flashes", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    await commit({ exploration: exploration({ interact: [], look: { entities: [] } }), local_map: fx.localMapPanel() });
    expect(card().exists()).toBe(false);
    expect(standee().exists()).toBe(false);
    expect(readoutText()).toBe("店長 已經離開了。");
    expect(wrapper.get('[data-testid="exploration-readout"]').attributes("data-flash")).toBe("true");
  });

  it("a committed move closes the card and leaves the dock on the new room's exploration root", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    await commit({
      exploration: exploration({ look: { room: { identity: 77, display_name: "渡口", room: true } } }),
      local_map: fx.localMapPanel(),
    });
    expect(card().exists()).toBe(false);
    expect(store.view.dockSource).toBe("exploration.root");
    expect(wrapper.find('#action-dock [data-testid="exploration-root"]').exists()).toBe(true);
  });

  it("交談 hands the same standee element to the dialogue screen", async () => {
    await mountWith();
    store.activatePresence("target-7");
    await settle();
    const before = standee().element;
    expect(store.activatePresenceVerb("talk-open").sent).toBe(true);
    await settle();
    revision += 1;
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision,
          mode: "dialogue",
          panels: {
            status: fx.statusPanel(),
            exploration: exploration(),
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
            art: artPanel(),
            dialogue: {
              schema_version: 2,
              available: true,
              kind: "dialogue",
              host: { identity: 7, display_name: "店長", portrait_ref: null },
              bond_stage: "熟識",
              line: "歡迎。",
              choices: [{ keyword_id: "news", label: "最近有什麼消息？" }],
            },
          },
        }),
      ],
      {},
    );
    await settle();
    expect(store.view.mode).toBe("dialogue");
    expect(card().exists()).toBe(false);
    expect(standee().element).toBe(before);
    expect(wrapper.findAll('[data-testid="anchor-actor-right"] [data-testid="stage-actor"]')).toHaveLength(1);
    // The card held focus when 交談 committed: focus goes to the dialogue's
    // focus home (the message page or the choice list), never the body.
    const active = document.activeElement;
    expect(active).not.toBe(document.body);
    expect(
      active.matches('[data-testid="message-page"]') || active.matches('[data-testid="dialogue-choices"]'),
    ).toBe(true);
  });

  it("the overflow card lists the rest, objects marked ◇, and a pick opens that person's card", async () => {
    const crowd = [1, 2, 3, 4, 5].map((n) => ({ identity: 100 + n, display_name: `旅人${n}`, portrait_ref: null, affordances: [] }));
    await mountWith(exploration({ interact: crowd, look: { entities: [], objects: [{ identity: 3, display_name: "木箱" }, { identity: 4, display_name: "告示板" }] } }));
    const slots = rail().findAll('[data-testid="presence-entry"]');
    expect(slots).toHaveLength(6);
    expect(slots[5].text()).toContain("＋2");
    await slots[5].trigger("click");
    await settle();
    expect(card().attributes("data-card-kind")).toBe("overflow");
    expect(cardRows().map((row) => row.text())).toEqual(["1◇ 木箱", "2◇ 告示板", "返回"]);
    key(card().element, "Escape");
    await settle();
    expect(document.getElementById(rail().attributes("aria-activedescendant")).dataset.entryKey).toBe("presence-more");
  });

  it("rail digits: `1` opens the card from anywhere, and a digit past the rail is claimed and does nothing", async () => {
    await mountWith();
    expect(store.focusPress("5")).toBe(true);
    expect(card().exists()).toBe(false);
    expect(store.focusPress("1")).toBe(true);
    await settle();
    expect(card().exists()).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("opening a card stops the compass", async () => {
    await mountWith();
    const compass = wrapper.get('[data-testid="exit-compass"]');
    expect(compass.classes()).not.toContain("exit-compass--inactive");
    store.activatePresence("target-7");
    await settle();
    expect(compass.classes()).toContain("exit-compass--inactive");
    store.closePresenceCard();
    await settle();
    expect(compass.classes()).not.toContain("exit-compass--inactive");
  });

  it("Tab walks compass → rail → 查看房間 → 等待 → 建議, and Shift+Tab walks back", async () => {
    await mountWith();
    const compass = wrapper.get('[data-testid="exit-compass"]').element;
    const look = wrapper.get('[data-anchor="map"] [data-testid="place-card-look"]').element;
    const wait = wrapper.get('[data-anchor="map"] [data-testid="place-card-wait"]').element;
    const pill = wrapper.get('#action-dock [data-testid="suggestions-pill"]').element;
    compass.focus();
    key(compass, "Tab");
    expect(document.activeElement).toBe(rail().element);
    key(rail().element, "Tab");
    expect(document.activeElement).toBe(look);
    key(look, "Tab");
    expect(document.activeElement).toBe(wait);
    key(wait, "Tab");
    expect(document.activeElement).toBe(pill);
    key(pill, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(wait);
    key(wait, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(look);
    key(look, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(rail().element);
    key(rail().element, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(compass);
  });

  it("the Tab chain skips a zone that is absent or inert", async () => {
    await mountWith();
    const compass = wrapper.get('[data-testid="exit-compass"]').element;
    const look = wrapper.get('[data-anchor="map"] [data-testid="place-card-look"]').element;
    // An empty room: no rail, so the compass hands over to 查看房間.
    await commit({ exploration: exploration({ interact: [], look: { ...exploration().look, entities: [], objects: [] } }) });
    expect(rail().exists()).toBe(false);
    compass.focus();
    key(compass, "Tab");
    expect(document.activeElement).toBe(look);
    key(look, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(compass);
    // An inert map anchor (person focus takes the place card away): the
    // chain skips the place card's buttons.
    wrapper.get('[data-anchor="map"]').element.setAttribute("inert", "");
    const pill = wrapper.get('#action-dock [data-testid="suggestions-pill"]').element;
    compass.focus();
    key(compass, "Tab");
    expect(document.activeElement).toBe(pill);
    key(pill, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(compass);
    wrapper.get('[data-anchor="map"]').element.removeAttribute("inert");
  });
});
