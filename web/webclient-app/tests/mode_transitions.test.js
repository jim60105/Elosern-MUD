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
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { combatFormation } from "../components/combat-formation.js";
import AppClient from "../AppClient.vue";
import HudFrame from "../components/HudFrame.vue";
import DialogueChoices from "../components/DialogueChoices.vue";
import { nextModeChange } from "../composables/use-mode-change.js";
import { dialogueViewModel } from "../stores/dialogue-view.js";
import { useElosernStore } from "../stores/elosern.js";

import {
  ART_PANEL_SAMPLE,
  fixtureDigest,
  sceneBlock,
  sceneDescriptor,
  sceneResource,
} from "../stories/fixtures.js";
import * as fx from "./store/protocol_fixtures.js";
import { observeLoad } from "./support/scene_layers.js";

// Every journey here mounts the whole shell and drives real commits, so an
// individual test can exceed Vitest's default budget on a shared runner (two
// different journeys did, on two consecutive CI runs): the file carries the
// same explicit headroom the project's other mount-heavy suites use.
vi.setConfig({ testTimeout: 20000 });

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

  it("flips the band's returning dock only on leaving combat, once, never on a later remount", async () => {
    // Role: the band flip is one-shot and plays only where the dock is in the
    // band. Detects a flip keyed on entering combat (the dock has left the
    // band for the centred card, webclient-combat-command-card-centred D2) or
    // a flip that replays after its own end.
    const wrapper = mount(HudFrame, { props: { mode: "exploration" } });
    const region = () => wrapper.get('[data-anchor="band-command"]');
    expect(region().attributes("data-flip")).toBeUndefined();
    await wrapper.setProps({ mode: "combat", modeChange: "exploration-combat" });
    expect(region().attributes("data-flip")).toBeUndefined();
    expect(wrapper.get('[data-testid="elosern-stage"]').attributes("data-mode-change")).toBe("exploration-combat");
    await wrapper.setProps({ mode: "exploration", modeChange: "combat-exploration" });
    expect(region().attributes("data-flip")).toBe("combat-exploration");
    // The flip's own end clears the one-shot key, while the stage keeps its
    // persistent `data-mode-change`, so a dock remounted later never flips.
    const end = new Event("animationend", { bubbles: true });
    end.animationName = "elosern-panel-flip-out";
    region().element.dispatchEvent(end);
    await wrapper.vm.$nextTick();
    expect(region().attributes("data-flip")).toBeUndefined();
    // A dialogue change flips nothing.
    await wrapper.setProps({ mode: "dialogue", modeChange: "exploration-dialogue" });
    expect(region().attributes("data-flip")).toBeUndefined();
    wrapper.unmount();
  });

  it("keys the combat card's entrance on a live change into combat, after the flash, and drops the band flip-in", () => {
    // Role: the card enters only on a live change (mount and reconnect never
    // set data-mode-change) and waits for the flash. Detects an entrance keyed
    // on the mode itself (it would play on a reload) or one without the delay.
    const css = readFileSync(join(process.cwd(), "web/webclient-app/components/HudFrame.vue"), "utf8");
    const start = css.indexOf('.elosern-stage[data-mode-change$="-combat"] [data-anchor="choices"] .stage-card-host > .action-dock--card {');
    expect(start).toBeGreaterThanOrEqual(0);
    const rule = css.slice(start, css.indexOf("}", start) + 1);
    expect(rule).toContain("animation: elosern-combat-card-in var(--motion-reveal) var(--ease-enter) var(--motion-flash) backwards;");
    expect(css).toMatch(/@keyframes elosern-combat-card-in \{\s*from \{\s*opacity: 0;\s*transform: translateY\(calc\(var\(--motion-shift-sm\) \* var\(--motion-travel\)\)\);/);
    expect(css).not.toContain('[data-flip$="-combat"]');
    expect(css).toContain('[data-anchor="band-command"][data-flip="combat-exploration"] > *');
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

// jsdom lays nothing out, so the stage the formation measures is stubbed at
// the 1451x790 reference: the stage box, the metrics probe's three lengths,
// and no vitals dock. Every other element keeps jsdom's empty box.
const STAGE = { width: 1451, height: 790 };
const PROBE = { "--actor-h": 489.8, "--header-h": 48, "--band-h": 220 };
function stubStageLayout() {
  const original = Element.prototype.getBoundingClientRect;
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function rect() {
    const box = (width, height) => ({ left: 0, top: 0, x: 0, y: 0, width, height, right: width, bottom: height, toJSON() {} });
    if (this.getAttribute("data-testid") === "elosern-stage") return box(STAGE.width, STAGE.height);
    const metric = this.getAttribute("data-metric");
    if (metric && metric in PROBE) return box(1, PROBE[metric]);
    return original.call(this);
  });
}
// The engine's own answer for those measurements, to compare against.
const expectedFormation = (party, foes) =>
  combatFormation({
    stageWidth: STAGE.width, stageHeight: STAGE.height, uiScale: 1, bandTop: STAGE.height - PROBE["--band-h"],
    actorHeight: PROBE["--actor-h"], topBandBottom: PROBE["--header-h"], cardWidth: 264, vitalsDock: null,
    partyCount: party, foeCount: foes,
  });

describe("AppClient live mode changes", () => {
  let store, wrapper, revision, generation, epoch;

  afterEach(() => {
    vi.restoreAllMocks();
  });

  beforeEach(async () => {
    stubStageLayout();
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
  // `first`: the first foe's state — "active", "fled" (it leaves the line)
  // or "defeated" (it keeps its slot; webclient-combat-defeated-foes D5).
  const twoFoes = (first = "active") => ({
    context_actions: fx.combatActions({
      participants: [
        { identity: 7, token: "e1", display_name: "灰袍盜賊", team: "foes", state: first, hp_current: first === "defeated" ? 0 : 40, hp_maximum: 60, portrait_ref: null, conditions: [] },
        { identity: 9, token: "e2", display_name: "盜賊頭目", team: "foes", state: "active", hp_current: 90, hp_maximum: 90, portrait_ref: null, conditions: [] },
        { identity: 8, token: "a1", display_name: "同行劍士", team: "party", state: "active", hp_current: 100, hp_maximum: 100, portrait_ref: null, conditions: [] },
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

  it("leaving dialogue focuses the returning dock's compass without scrolling any ancestor", async () => {
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
      // Re-entering exploration hands focus on to the exit compass inside
      // the dock (exploration-exit-compass); every focus call on the way —
      // the dock's rescue and the compass's — avoids scrolling.
      const dock = document.getElementById("action-dock");
      const compass = dock.querySelector('[data-testid="exit-compass"]');
      expect(document.activeElement).toBe(compass);
      const homeCalls = focus.mock.contexts
        .map((context, index) => [context, focus.mock.calls[index]])
        .filter(([context]) => context === dock || context === compass);
      expect(homeCalls.length).toBeGreaterThan(0);
      for (const [, args] of homeCalls) {
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
    // A party row in the combat panel that no drawn figure stands for is
    // not a foe: it never stands in the foe line-up.
    expect(row.text()).not.toContain("同行劍士");
    // The caption clears the leftmost foe of the formation (stage px + 16).
    const shape = expectedFormation(1, 2);
    const leftmost = Math.min(...shape.foes.figures.map((f) => f.box.left));
    expect(clientRoot().style.getPropertyValue("--caption-right")).toBe(`${STAGE.width - leftmost + 16}px`);

    commit("exploration");
    await nextTick();
    const leaving = lineups();
    expect(leaving).toHaveLength(1);
    expect(leaving[0].element.inert).toBe(true);
    expect(leaving[0].classes()).toContain("foes-enter-leave-active");
    // The caption keeps clearing the row until the fade has ended; the party
    // side returns to the exploration rule at once.
    expect(clientRoot().style.getPropertyValue("--caption-right")).toBe(`${STAGE.width - leftmost + 16}px`);
    expect(clientRoot().style.getPropertyValue("--caption-left")).toBe("");
  });

  it("a foe defeated inside combat keeps its slot in its defeated look, and nothing re-forms", async () => {
    store.setMotionLevel("full");
    await nextTick();
    commit("combat", twoFoes());
    await nextTick();
    await nextTick();
    const edge = clientRoot().style.getPropertyValue("--caption-right");
    const before = lineups()[0].findAll('[data-testid="foe-slot"]').map((s) => s.element.style.left);
    commit("combat", twoFoes("defeated"));
    await nextTick();
    const slots = lineups()[0].findAll('[data-testid="foe-slot"]');
    expect(slots.map((s) => s.element.style.left)).toEqual(before);
    expect(slots.filter((s) => s.element.inert)).toHaveLength(0);
    expect(lineups()[0].attributes("data-count")).toBe("2");
    expect(clientRoot().style.getPropertyValue("--caption-right")).toBe(edge);
    expect(slots[0].attributes("data-fallen")).toBe("defeated");
    expect(slots[0].find('[data-testid="stage-actor-seal"]').exists()).toBe(true);
    expect(slots[1].attributes("data-fallen")).toBeUndefined();
    // Its plate stays and states the defeat.
    const plate = wrapper.find('[data-testid="figure-plate"][data-identity="7"]');
    expect(plate.attributes("data-fallen")).toBe("defeated");
    expect(plate.attributes("aria-label").endsWith("已擊破")).toBe(true);
  });

  it("a foe fleeing inside combat leaves the row inert while the other steps forward", async () => {
    store.setMotionLevel("full");
    await nextTick();
    commit("combat", twoFoes());
    await nextTick();
    await nextTick();
    const heldEdge = clientRoot().style.getPropertyValue("--caption-right");
    expect(heldEdge).not.toBe("");
    commit("combat", twoFoes("fled"));
    await nextTick();
    // The caption keeps the two-foe room until the fled foe has faded.
    expect(clientRoot().style.getPropertyValue("--caption-right")).toBe(heldEdge);
    const slots = lineups()[0].findAll('[data-testid="foe-slot"]');
    const leaving = slots.filter((s) => s.element.inert);
    expect(leaving).toHaveLength(1);
    expect(leaving[0].classes()).toContain("foe-leave-active");
    const staying = slots.filter((s) => !s.element.inert);
    expect(staying).toHaveLength(1);
    // The other foe steps to the one-foe formation's box.
    expect(staying[0].element.style.left).toBe(`${expectedFormation(1, 1).foes.figures[0].box.left}px`);
    expect(lineups()[0].attributes("data-count")).toBe("1");
    // The fled foe's plate leaves with it; the standing foe keeps its own.
    const plates = wrapper.findAll('[data-testid="figure-plate"]').filter((p) => !p.element.inert);
    expect(plates.map((p) => p.attributes("data-identity"))).toEqual(["9"]);
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
    const edge = (foes) => `${STAGE.width - Math.min(...expectedFormation(1, foes).foes.figures.map((f) => f.box.left)) + 16}px`;
    expect(clientRoot().style.getPropertyValue("--caption-right")).toBe(edge(2));
    // A fled foe leaves at once, and so does the room it held.
    commit("combat", twoFoes("fled"));
    await nextTick();
    expect(clientRoot().style.getPropertyValue("--caption-right")).toBe(edge(1));
    commit("combat", twoFoes());
    await nextTick();
    expect(lineups()).toHaveLength(1);
    expect(lineups()[0].classes()).not.toContain("foes-enter-enter-active");
    commit("exploration");
    await nextTick();
    expect(lineups()).toHaveLength(0);
    expect(clientRoot().style.getPropertyValue("--caption-right")).toBe("");
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

  it("holds combat backdrop decoration during terminal beat hold without freezing canonical scene identity", async () => {
    store.setMotionLevel("full");
    await nextTick();

    commit("combat", {
      ...twoFoes(),
    });

    const requestId = store.dispatchAction("combat.flee", "flee");
    store.appendText("out", "你擲出了骰子。");
    store.appendText("out", "灰袍盜賊倒下了。");

    // Terminal round publishes exploration mode with combat beats still playing.
    commit("exploration", {
      combat_beats: {
        schema_version: 1,
        available: true,
        round: "s-1/1",
        beats: [
          { seq: 0, action: 0, kind: "roll", actor: "42", target: "7", amount: null, hp_after: null, text: "你擲出了骰子。" },
          { seq: 1, action: 1, kind: "damage", actor: "42", target: "7", amount: 40, hp_after: 0, text: "灰袍盜賊倒下了。" },
        ],
      },
      context_actions: fx.explorationActions(),
      art: {
        ...ART_PANEL_SAMPLE,
        scene: sceneBlock(
          { label: "新城鎮", alt: "新城鎮的景象" },
          sceneDescriptor({
            attempts: [
              {
                type: "image",
                source_id: "scene.generated:scene:river_dawn",
                rank: 20,
                resource: sceneResource({
                  version: fixtureDigest("new-town"),
                  url: "/art/scenes/new_town.png",
                }),
              },
            ],
            terminal: null,
          }),
        ),
      },
    });
    store.receive(generation, "ui_action_result", [fx.actionResult({ request_id: requestId, presentation_revision: revision - 1 })], {});
    await nextTick();
    // Stage mode committed is exploration, beatHold is active.
    expect(store.view.beatHold).toBe(true);
    // Backdrop receives combat stage mode while art panel carries newly committed scene identity
    const backdrop = wrapper.getComponent({ name: "SceneBackdrop" });
    expect(backdrop.props("mode")).toBe("combat");
    // The committed scene's own element reports its pixels, exactly like the
    // browser's: only then does the caption row stand for a real bitmap.
    await observeLoad(wrapper, "/art/scenes/new_town.png");
    expect(wrapper.get('[data-testid="scene-backdrop-label"]').text()).toBe("新城鎮");
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

// webclient-combat-formation (design D3): both line-ups re-form on one
// shared rule — the same four box edges, duration and easing — so their
// heights stay equal through every change, and nothing glides below `full`.
describe("the shared formation glide", () => {
  const APP_ROOT = join(process.cwd(), "web/webclient-app");
  const source = (file) => readFileSync(join(APP_ROOT, file), "utf8");
  const transitionOf = (css, selector) => {
    const start = css.indexOf(selector);
    expect(start).toBeGreaterThanOrEqual(0);
    const block = css.slice(start, css.indexOf("}", start));
    return /transition:([^;]*);/.exec(block)[1].replace(/\s+/g, " ").trim();
  };
  const SHARED = ["left", "top", "width", "height"]
    .map((edge) => `${edge} calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard)`)
    .join(", ");

  it("uses one slot transition rule on both sides and on the plates", () => {
    expect(transitionOf(source("components/FoeLineup.vue"), ".foe-lineup__slot {")).toBe(SHARED);
    expect(
      transitionOf(source("components/CompanionLineup.vue"), '.companion-lineup[data-formation="true"] > .companion-lineup__slot {'),
    ).toBe(SHARED);
    expect(transitionOf(source("AppClient.vue"), '.figure-plates[data-glide="true"] > .figure-plate {')).toBe(SHARED);
  });

  describe("in the client", () => {
    let store, wrapper;
    beforeEach(() => {
      stubStageLayout();
      setActivePinia(createPinia());
      store = useElosernStore();
      store.setSender(fx.createFakeSender());
      wrapper = mount(AppClient, { attachTo: document.body });
      store.beginTransport(1);
      store.setConnected(true);
      store.setLoggedIn(true);
    });
    afterEach(() => {
      wrapper.unmount();
      document.body.replaceChildren();
      vi.restoreAllMocks();
    });
    const snapshot = (revision, mode) =>
      store.receive(1, "ui_snapshot", [fx.snapshot({
        presentation_epoch: fx.EPOCH_A, revision, mode,
        panels: {
          status: fx.statusPanel(),
          exploration: fx.explorationPanel(),
          context_actions: mode === "combat" ? fx.combatActions() : fx.explorationActions(),
          art: ART_PANEL_SAMPLE,
        },
      })], {});

    it.each([
      ["full", "true"],
      ["reduced", "false"],
      ["off", "false"],
    ])("glides at %s: %s", async (level, glide) => {
      store.setMotionLevel(level);
      snapshot(1, "exploration");
      await nextTick();
      snapshot(2, "combat");
      await nextTick();
      expect(wrapper.get('[data-testid="elosern-stage"]').attributes("data-formation")).toBe("true");
      expect(wrapper.get('[data-testid="companion-lineup"]').attributes("data-glide")).toBe(glide);
      expect(wrapper.get('[data-testid="foe-lineup"]').attributes("data-glide")).toBe(glide);
      // The party stands at the engine's box for the measured stage.
      const party = expectedFormation(1, wrapper.findAll('[data-testid="foe-slot"]').length).party.figures[0].box;
      expect(wrapper.get('[data-testid="companion-figure"]').element.style.height).toBe(`${party.height}px`);
    });
  });
});
