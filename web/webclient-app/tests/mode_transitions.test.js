// webclient-mode-transitions (C11c): the mode changes transition at the
// motion level. The component-level half of design D8:
// - the live mode-change signal (`nextModeChange`, `data-mode-change`), which
//   a mount, a reconnect, and a same-mode resync never set;
// - the collapsed command region is inert exactly in dialogue, and the flash
//   and the veil are decorative layers rendered in every mode;
// - the host actor is inert while it leaves, and neither edge of a reconnect
//   leaves a leaving copy behind;
// - the dialogue choice rows carry their stagger index, keep the one-tab-stop
//   menu contract, and take a digit before any animation ends.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { foeLineupSpan } from "../components/foe-lineup.js";
import AppClient from "../AppClient.vue";
import HudFrame from "../components/HudFrame.vue";
import DialogueChoices from "../components/DialogueChoices.vue";
import { nextModeChange } from "../composables/use-mode-change.js";
import { dialogueViewModel } from "../stores/dialogue-view.js";
import { useElosernStore } from "../stores/elosern.js";
import { ART_PANEL_SAMPLE } from "../stories/fixtures.js";
import * as fx from "./store/protocol_fixtures.js";

const DIALOGUE = {
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
};

describe("nextModeChange", () => {
  it("names a change between two known modes", () => {
    expect(nextModeChange(null, "exploration", "combat")).toBe("exploration-combat");
    expect(nextModeChange("exploration-combat", "combat", "exploration")).toBe("combat-exploration");
  });
  it("clears on a null endpoint (a transport reset, the first snapshot)", () => {
    expect(nextModeChange("exploration-dialogue", "dialogue", null)).toBe(null);
    expect(nextModeChange(null, null, "combat")).toBe(null);
  });
  it("keeps the last change on a same-mode resync", () => {
    expect(nextModeChange("exploration-combat", "combat", "combat")).toBe("exploration-combat");
  });
});

describe("HudFrame mode layers", () => {
  for (const mode of ["exploration", "combat", "dialogue", "creation"]) {
    it(`renders the decorative flash and veil in ${mode}, and makes the command region inert only in dialogue`, () => {
      const wrapper = mount(HudFrame, { props: { mode } });
      const flash = wrapper.get('[data-testid="stage-flash"]');
      const veil = wrapper.get('[data-testid="stage-combat-veil"]');
      expect(flash.attributes("aria-hidden")).toBe("true");
      expect(veil.attributes("aria-hidden")).toBe("true");
      const region = wrapper.get('[data-anchor="band-command"]');
      expect(region.attributes("inert") !== undefined).toBe(mode === "dialogue");
      expect(wrapper.get('[data-testid="elosern-stage"]').attributes("data-mode-change")).toBeUndefined();
      wrapper.unmount();
    });
  }

  it("flips the command panel once per live combat change, never on a later remount", async () => {
    const wrapper = mount(HudFrame, { props: { mode: "exploration" } });
    const region = () => wrapper.get('[data-anchor="band-command"]');
    expect(region().attributes("data-flip")).toBeUndefined();
    await wrapper.setProps({ mode: "combat", modeChange: "exploration-combat" });
    expect(region().attributes("data-flip")).toBe("exploration-combat");
    // The flip's own end clears the one-shot key, while the stage keeps its
    // persistent `data-mode-change`, so a dock remounted later never flips.
    const end = new Event("animationend", { bubbles: true });
    end.animationName = "elosern-panel-flip-in";
    region().element.dispatchEvent(end);
    await wrapper.vm.$nextTick();
    expect(region().attributes("data-flip")).toBeUndefined();
    expect(wrapper.get('[data-testid="elosern-stage"]').attributes("data-mode-change")).toBe("exploration-combat");
    await wrapper.setProps({ mode: "exploration", modeChange: "combat-exploration" });
    expect(region().attributes("data-flip")).toBe("combat-exploration");
    // A dialogue change flips nothing.
    await wrapper.setProps({ mode: "dialogue", modeChange: "exploration-dialogue" });
    expect(region().attributes("data-flip")).toBeUndefined();
    wrapper.unmount();
  });

  it("renders the mode change it is given on the stage root", async () => {
    const wrapper = mount(HudFrame, { props: { mode: "combat", modeChange: "exploration-combat" } });
    const stage = () => wrapper.get('[data-testid="elosern-stage"]');
    expect(stage().attributes("data-mode-change")).toBe("exploration-combat");
    await wrapper.setProps({ mode: "exploration", modeChange: "combat-exploration" });
    expect(stage().attributes("data-mode-change")).toBe("combat-exploration");
    wrapper.unmount();
  });
});

describe("AppClient live mode changes", () => {
  let store, wrapper, revision, generation, epoch;

  beforeEach(async () => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    // The real Transition components, so leaving copies exist in the DOM.
    wrapper = mount(AppClient, {
      attachTo: document.body,
      global: { stubs: { transition: false, "transition-group": false } },
    });
    generation = 1;
    epoch = fx.EPOCH_A;
    store.beginTransport(generation);
    store.setConnected(true);
    store.setLoggedIn(true);
    revision = 1;
    commit("exploration");
    await nextTick();
    await nextTick();
  });
  afterEach(() => {
    wrapper.unmount();
    document.body.replaceChildren();
  });

  function commit(mode, extra = {}) {
    const panels = {
      status: fx.statusPanel(),
      exploration: fx.explorationPanel(),
      context_actions: mode === "combat" ? fx.combatActions() : fx.explorationActions(),
      local_map: fx.localMapPanel(),
      art: ART_PANEL_SAMPLE,
      ...extra,
    };
    const response = store.receive(generation, "ui_snapshot", [fx.snapshot({ presentation_epoch: epoch, revision, mode, panels })], {});
    expect(response.accepted).toBe(true);
    revision += 1;
  }

  const stage = () => wrapper.get('[data-testid="elosern-stage"]');
  // The host is actor-right's own child; the foe line-up's actors sit
  // inside its row (webclient-combat-foes-on-stage).
  const hosts = () => wrapper.findAll('[data-anchor="actor-right"] > [data-testid="stage-actor"]');
  const lineups = () => wrapper.findAll('[data-anchor="actor-right"] > [data-testid="foe-lineup"]');
  const clientRoot = () => wrapper.get('[data-testid="elosern-client-root"]').element;
  const twoFoes = (defeatFirst = false) => ({
    context_actions: fx.combatActions({
      participants: [
        { identity: 7, token: "e1", display_name: "灰袍盜賊", team: "foes", state: defeatFirst ? "defeated" : "active", hp_current: defeatFirst ? 0 : 40, hp_maximum: 60, portrait_ref: null },
        { identity: 9, token: "e2", display_name: "盜賊頭目", team: "foes", state: "active", hp_current: 90, hp_maximum: 90, portrait_ref: null },
        { identity: 8, token: "a1", display_name: "同行劍士", team: "party", state: "active", hp_current: 100, hp_maximum: 100, portrait_ref: null },
      ],
    }),
  });

  it("the first snapshot sets no mode change; live changes name themselves", async () => {
    expect(stage().attributes("data-mode-change")).toBeUndefined();
    commit("combat");
    await nextTick();
    expect(stage().attributes("data-mode-change")).toBe("exploration-combat");
    // A same-mode resync keeps the last change.
    commit("combat");
    await nextTick();
    expect(stage().attributes("data-mode-change")).toBe("exploration-combat");
    commit("exploration");
    await nextTick();
    expect(stage().attributes("data-mode-change")).toBe("combat-exploration");
  });

  it("the leaving host is inert while it animates out, and the dock is back in reach at once", async () => {
    store.setMotionLevel("full");
    await nextTick();
    commit("dialogue", { dialogue: DIALOGUE });
    await nextTick();
    expect(hosts()).toHaveLength(1);
    expect(wrapper.get('[data-anchor="band-command"]').attributes("inert")).toBeDefined();
    commit("exploration", { dialogue: { schema_version: 2, available: false, reason: { code: "dialogue_unavailable", message: "對話已結束" } } });
    await nextTick();
    expect(stage().attributes("data-mode-change")).toBe("dialogue-exploration");
    expect(wrapper.get('[data-anchor="band-command"]').attributes("inert")).toBeUndefined();
    const leaving = hosts();
    expect(leaving).toHaveLength(1);
    expect(leaving[0].element.inert).toBe(true);
    expect(leaving[0].classes()).toContain("actor-enter-leave-active");
  });

  it("leaving dialogue focuses the returning dock without scrolling any ancestor", async () => {
    // The command region starts its return beyond the stage's right edge, so
    // a plain focus() would scroll an ancestor towards it and drag the whole
    // stage sideways; the dock takes focus with `preventScroll`.
    store.setMotionLevel("full");
    await nextTick();
    commit("dialogue", { dialogue: DIALOGUE });
    await nextTick();
    await nextTick();
    const focus = vi.spyOn(HTMLElement.prototype, "focus");
    try {
      commit("exploration", { dialogue: { schema_version: 2, available: false, reason: { code: "dialogue_unavailable", message: "對話已結束" } } });
      await nextTick();
      await nextTick();
      await nextTick();
      const dock = document.getElementById("action-dock");
      expect(document.activeElement).toBe(dock);
      const dockCalls = focus.mock.contexts
        .map((context, index) => [context, focus.mock.calls[index]])
        .filter(([context]) => context === dock);
      expect(dockCalls.length).toBeGreaterThan(0);
      for (const [, args] of dockCalls) {
        expect(args[0]).toEqual({ preventScroll: true });
      }
    } finally {
      focus.mockRestore();
    }
  });

  it("a reconnect mid-dialogue plays nothing on either edge", async () => {
    store.setMotionLevel("full");
    await nextTick();
    commit("dialogue", { dialogue: DIALOGUE });
    await nextTick();
    await nextTick();
    expect(stage().attributes("data-mode-change")).toBe("exploration-dialogue");
    expect(hosts()).toHaveLength(1);

    // The transport reset nulls the committed mode: the host and the name
    // plate go in that frame, with no leaving copy.
    generation = 2;
    store.beginTransport(generation);
    await nextTick();
    expect(stage().attributes("data-mode-change")).toBeUndefined();
    expect(hosts()).toHaveLength(0);
    expect(wrapper.find('[data-testid="message-name-plate"]').exists()).toBe(false);

    // The resync snapshot (a new presentation epoch) commits dialogue again:
    // every surface at rest.
    store.setConnected(true);
    epoch = fx.EPOCH_B;
    revision = 1;
    commit("dialogue", { dialogue: DIALOGUE });
    await nextTick();
    expect(stage().attributes("data-mode-change")).toBeUndefined();
    expect(hosts()).toHaveLength(1);
    expect(hosts()[0].classes()).not.toContain("actor-enter-enter-active");
    const plate = wrapper.find('[data-testid="message-name-plate"]');
    expect(plate.exists()).toBe(true);
    expect(plate.classes()).not.toContain("plate-enter-active");
    const list = wrapper.find('[data-anchor="choices"] [data-testid="dialogue-choices"]');
    expect(list.exists()).toBe(true);
    expect(list.classes()).toContain("dialogue-choices--still");
  });

  it("a live entry animates the host and the choice list", async () => {
    store.setMotionLevel("full");
    await nextTick();
    commit("dialogue", { dialogue: DIALOGUE });
    await nextTick();
    expect(hosts()[0].classes()).toContain("actor-enter-enter-active");
    const list = wrapper.get('[data-anchor="choices"] [data-testid="dialogue-choices"]');
    expect(list.classes()).not.toContain("dialogue-choices--still");
  });

  it("a live entry into combat slides the foe line-up in; leaving fades it out inert", async () => {
    // webclient-combat-foes-on-stage D3.
    store.setMotionLevel("full");
    await nextTick();
    commit("combat", twoFoes());
    await nextTick();
    expect(lineups()).toHaveLength(1);
    const row = lineups()[0];
    expect(row.classes()).toContain("foes-enter-enter-active");
    expect(row.findAll('[data-testid="foe-slot"]').map((s) => s.attributes("data-portrait-ref"))).toEqual(["", ""]);
    // Party members never stand on the stage; the frame still lists them.
    expect(row.text()).not.toContain("同行劍士");
    expect(clientRoot().style.getPropertyValue("--foe-lineup-span")).not.toBe("0");

    commit("exploration");
    await nextTick();
    const leaving = lineups();
    expect(leaving).toHaveLength(1);
    expect(leaving[0].element.inert).toBe(true);
    expect(leaving[0].classes()).toContain("foes-enter-leave-active");
    // The caption keeps clearing the row until the fade has ended.
    expect(clientRoot().style.getPropertyValue("--foe-lineup-span")).not.toBe("0");
  });

  it("a foe defeated inside combat leaves the row inert while the other steps forward", async () => {
    store.setMotionLevel("full");
    await nextTick();
    commit("combat", twoFoes());
    await nextTick();
    await nextTick();
    const heldSpan = clientRoot().style.getPropertyValue("--foe-lineup-span");
    commit("combat", twoFoes(true));
    await nextTick();
    // The caption keeps the two-foe room until the fallen foe has faded.
    expect(clientRoot().style.getPropertyValue("--foe-lineup-span")).toBe(heldSpan);
    const slots = lineups()[0].findAll('[data-testid="foe-slot"]');
    const leaving = slots.filter((s) => s.element.inert);
    expect(leaving).toHaveLength(1);
    expect(leaving[0].classes()).toContain("foe-leave-active");
    const staying = slots.filter((s) => !s.element.inert);
    expect(staying).toHaveLength(1);
    expect(staying[0].element.style.right).toBe("0%");
    expect(lineups()[0].attributes("data-count")).toBe("1");
    expect(wrapper.get('[data-testid="participant-frame"]').text()).toContain("已敗退");
  });

  it("a reconnect mid-combat mounts the line-up at rest", async () => {
    store.setMotionLevel("full");
    await nextTick();
    commit("combat", twoFoes());
    await nextTick();
    await nextTick();
    generation = 2;
    store.beginTransport(generation);
    await nextTick();
    expect(lineups()).toHaveLength(0);
    store.setConnected(true);
    epoch = fx.EPOCH_B;
    revision = 1;
    commit("combat", twoFoes());
    await nextTick();
    expect(lineups()).toHaveLength(1);
    expect(lineups()[0].classes()).not.toContain("foes-enter-enter-active");
  });

  it("at the off level the line-up comes and goes in the commit's frame", async () => {
    store.setMotionLevel("off");
    await nextTick();
    commit("combat", twoFoes());
    await nextTick();
    expect(clientRoot().style.getPropertyValue("--foe-lineup-span")).toBe(String(foeLineupSpan(2)));
    // A fallen foe leaves at once, and so does the room it held.
    commit("combat", twoFoes(true));
    await nextTick();
    expect(clientRoot().style.getPropertyValue("--foe-lineup-span")).toBe("1");
    commit("combat", twoFoes());
    await nextTick();
    expect(lineups()).toHaveLength(1);
    expect(lineups()[0].classes()).not.toContain("foes-enter-enter-active");
    commit("exploration");
    await nextTick();
    expect(lineups()).toHaveLength(0);
    expect(clientRoot().style.getPropertyValue("--foe-lineup-span")).toBe("0");
  });

  it("at the off level the host has no CSS phase and goes in the commit's frame", async () => {
    store.setMotionLevel("off");
    await nextTick();
    commit("dialogue", { dialogue: DIALOGUE });
    await nextTick();
    expect(hosts()).toHaveLength(1);
    expect(hosts()[0].classes()).not.toContain("actor-enter-enter-active");
    commit("exploration");
    await nextTick();
    expect(hosts()).toHaveLength(0);
  });
});

describe("DialogueChoices stagger", () => {
  const PICKS = dialogueViewModel(DIALOGUE).picks;
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    document.body.replaceChildren();
  });

  it("indexes every row for the stagger and keeps the one-tab-stop menu", () => {
    wrapper = mount(DialogueChoices, { attachTo: document.body, props: { picks: PICKS } });
    const root = wrapper.get('[data-testid="dialogue-choices"]');
    expect(root.attributes("role")).toBe("menu");
    expect(root.attributes("tabindex")).toBe("0");
    const rows = wrapper.findAll('[role="menuitem"]');
    expect(rows.length).toBe(PICKS.length + 3);
    rows.forEach((row, index) => {
      expect(row.element.style.getPropertyValue("--row-index")).toBe(String(index));
    });
    expect(root.classes()).not.toContain("dialogue-choices--still");
  });

  it("takes a digit in its first frame, before any entrance ends", async () => {
    wrapper = mount(DialogueChoices, { attachTo: document.body, props: { picks: PICKS } });
    await wrapper.get('[data-testid="dialogue-choices"]').trigger("keydown", { key: "2" });
    expect(wrapper.emitted("pick")).toEqual([[PICKS[1]]]);
  });

  it("shows at rest when mounted without an entrance, and staggers the rows of a later view swap", async () => {
    wrapper = mount(DialogueChoices, { attachTo: document.body, props: { picks: PICKS, entrance: false } });
    const root = () => wrapper.get('[data-testid="dialogue-choices"]');
    expect(root().classes()).toContain("dialogue-choices--still");
    expect(root().classes()).toContain("dialogue-choices--rows-still");
    // A later prop change never replays the entrance.
    await wrapper.setProps({ entrance: true });
    expect(root().classes()).toContain("dialogue-choices--still");
    await wrapper.get('[data-testid="dialogue-move"]').trigger("click");
    expect(root().classes()).not.toContain("dialogue-choices--rows-still");
    // The card itself never refades.
    expect(root().classes()).toContain("dialogue-choices--still");
  });
});
