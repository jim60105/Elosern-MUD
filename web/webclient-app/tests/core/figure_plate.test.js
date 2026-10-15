// webclient-combat-formation (design D4): the glance plate each combat figure
// other than the controlled one carries in the stage's `plates` layer — the
// full and compact forms, the readout, the stroke and its trailing segment,
// the accessible name, the repeated-name token and the playback value — and
// the client filling the layer from the formation's plate slots.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import FigurePlate from "../../components/FigurePlate.vue";
import AppClient from "../../AppClient.vue";
import { combatFormation } from "../../components/combat-formation.js";
import { plateHpCurrent, plateHpPercent, plateLabel, repeatedNames } from "../../components/figure-plate.js";
import { useElosernStore } from "../../stores/elosern.js";
import { PARTY_PANEL_FULL_SAMPLE } from "../../stories/fixtures/party_panels.js";
import { ART_PANEL_SAMPLE } from "../../stories/fixtures.js";
import * as fx from "../store/protocol_fixtures.js";

const APP_ROOT = join(process.cwd(), "web/webclient-app");
const BOX = { left: 900, top: 180, width: 112, height: 52 };

describe("FigurePlate", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("reads name, stroke and both numbers on the full plate, at its slot", () => {
    wrapper = mount(FigurePlate, {
      props: { name: "蕾娜", token: "a2", side: "party", hpCurrent: 42, hpMaximum: 120, form: "full", box: BOX, identity: 101 },
    });
    const plate = wrapper.get('[data-testid="figure-plate"]');
    expect(plate.attributes("data-form")).toBe("full");
    expect(plate.attributes("data-side")).toBe("party");
    expect(plate.attributes("data-identity")).toBe("101");
    const style = plate.element.style;
    expect([style.left, style.top, style.width, style.height]).toEqual(["900px", "180px", "112px", "52px"]);
    // Line 1: the name (no token: the name does not repeat).
    expect(plate.get(".figure-plate__name").text()).toBe("蕾娜");
    expect(plate.find('[data-testid="figure-plate-token"]').exists()).toBe(false);
    // Line 2: the stroke filled to 35% and the readout, current then `/ max`.
    const stroke = plate.get('[data-testid="figure-plate-stroke"]');
    expect(stroke.attributes("data-percent")).toBe(String((42 / 120) * 100));
    expect(stroke.get(".figure-plate__fill").element.style.width).toBe(`${(42 / 120) * 100}%`);
    // The trailing segment shares the target width; CSS delays it.
    expect(stroke.get(".figure-plate__trail").element.style.width).toBe(`${(42 / 120) * 100}%`);
    const readout = plate.get('[data-testid="figure-plate-readout"]');
    expect(readout.get(".figure-plate__current").text()).toBe("42");
    expect(readout.get(".figure-plate__maximum").text()).toBe("/120");
    // Line 3 is kept empty for the condition glyphs.
    expect(plate.get('[data-testid="figure-plate-glyphs"]').text()).toBe("");
    // Display-only: a named group, nothing focusable.
    expect(plate.attributes("role")).toBe("group");
    expect(plate.attributes("aria-label")).toBe("蕾娜 a2，我方，生命 42/120");
    expect(plate.findAll("button, a, input, [tabindex]")).toHaveLength(0);
  });

  it("keeps only the stroke and the current value on the compact plate", () => {
    wrapper = mount(FigurePlate, {
      props: { name: "哥布林", token: "e6", side: "foes", hpCurrent: 18, hpMaximum: 30, form: "compact", box: BOX },
    });
    const plate = wrapper.get('[data-testid="figure-plate"]');
    expect(plate.attributes("data-form")).toBe("compact");
    // The name leaves the layout (CSS) and the accessibility tree, and stays
    // the plate's accessible name.
    expect(plate.get(".figure-plate__name").attributes("aria-hidden")).toBe("true");
    expect(plate.attributes("aria-label")).toBe("哥布林 e6，敵方，生命 18/30");
    expect(plate.get(".figure-plate__current").text()).toBe("18");
    expect(plate.find(".figure-plate__maximum").exists()).toBe(false);
    const css = readFileSync(join(APP_ROOT, "components/FigurePlate.vue"), "utf8");
    expect(css).toMatch(/\.figure-plate\[data-form="compact"\] \.figure-plate__name \{\s*display: none;/);
    expect(css).toMatch(/\.figure-plate\[data-form="compact"\] \.figure-plate__stroke \{\s*min-width: calc\(30px \* var\(--ui-scale\)\);/);
    expect(css).toMatch(/\.figure-plate__stroke \{[^}]*min-width: calc\(40px \* var\(--ui-scale\)\);/);
  });

  it("shows the session token only when asked, and keeps the full name for a long one", () => {
    const long = "灰袍盜賊與北境巡防隊長的漫長稱號";
    wrapper = mount(FigurePlate, { props: { name: long, token: "e1", showToken: true, side: "foes", hpCurrent: 9, hpMaximum: 24 } });
    expect(wrapper.get('[data-testid="figure-plate-token"]').text()).toBe("e1");
    // Ellipsized by CSS; the full name stays in the DOM and in the title.
    expect(wrapper.get(".figure-plate__name-text").text()).toBe(long);
    expect(wrapper.get(".figure-plate__name").attributes("title")).toBe(long);
  });

  it("follows a changing value, and states the non-colour cues", async () => {
    wrapper = mount(FigurePlate, { props: { name: "狼", token: "e4", side: "foes", hpCurrent: 30, hpMaximum: 30 } });
    expect(wrapper.get(".figure-plate__fill").element.style.width).toBe("100%");
    await wrapper.setProps({ hpCurrent: 0, target: true, acting: true });
    expect(wrapper.get(".figure-plate__fill").element.style.width).toBe("0%");
    expect(wrapper.get(".figure-plate__current").text()).toBe("0");
    expect(wrapper.attributes("data-target")).toBe("true");
    expect(wrapper.attributes("data-acting")).toBe("true");
    // Missing numbers read as a dash, never as a fabricated value.
    await wrapper.setProps({ hpCurrent: null, hpMaximum: null });
    expect(wrapper.get(".figure-plate__current").text()).toBe("--");
    expect(wrapper.get(".figure-plate__fill").element.style.width).toBe("0%");
  });

  it("names every duration through the motion tokens, the trail after the vitals' delay", () => {
    const css = readFileSync(join(APP_ROOT, "components/FigurePlate.vue"), "utf8");
    expect(css).not.toMatch(/(transition|animation)[a-z-]*:[^;]*[0-9]m?s/);
    expect(css).toMatch(/\.figure-plate__trail \{[^}]*transition: width var\(--motion-trail\) ease var\(--motion-trail-delay\);/);
    expect(css).toMatch(/\.figure-plate__fill \{[^}]*transition: width var\(--motion-slow\) var\(--ease-standard\);/);
    // No box: no border, radius or shadow on the plate itself.
    const base = /\n\.figure-plate \{[^}]*\}/.exec(css)[0];
    expect(base).not.toMatch(/(^|\s)(border|border-radius|box-shadow)\s*:/m);
  });
});

describe("the plate helpers", () => {
  it("fills the stroke from the numbers, clamped, and empty without a maximum", () => {
    expect(plateHpPercent(18, 30)).toBe(60);
    expect(plateHpPercent(45, 30)).toBe(100);
    expect(plateHpPercent(-3, 30)).toBe(0);
    expect(plateHpPercent(5, 0)).toBe(0);
    expect(plateHpPercent(null, 30)).toBeNull();
  });

  it("reads the displayed playback value by portrait reference, else the committed one", () => {
    const row = { hp_current: 30, portrait_ref: "31" };
    expect(plateHpCurrent(row, { 31: 18 })).toBe(18);
    expect(plateHpCurrent(row, { 32: 18 })).toBe(30);
    expect(plateHpCurrent(row, null)).toBe(30);
    // A null reference keeps the committed value even if a key matches.
    expect(plateHpCurrent({ hp_current: 30, portrait_ref: null }, { null: 1 })).toBe(30);
  });

  it("composes the accessible name with side and token", () => {
    expect(plateLabel({ name: "哥布林", token: "e1", side: "foes", current: 9, maximum: 24 })).toBe("哥布林 e1，敵方，生命 9/24");
    expect(plateLabel({ name: "幽", token: "", side: "party", current: null, maximum: null })).toBe("幽，我方，生命 --");
  });

  it("finds the names two or more drawn figures share", () => {
    expect([...repeatedNames(["哥布林", "哥布林", "狼", "哥布林", "", null])]).toEqual(["哥布林"]);
    expect(repeatedNames(["狼"]).size).toBe(0);
  });
});

// The client fills the plates layer from the formation (jsdom lays nothing
// out, so the stage the formation measures is stubbed at 1451x790).
describe("the plates layer in the client", () => {
  let store, wrapper;
  beforeEach(() => {
    const original = Element.prototype.getBoundingClientRect;
    const PROBE = { "--actor-h": 489.8, "--header-h": 48, "--band-h": 220 };
    vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function rect() {
      const box = (width, height) => ({ left: 0, top: 0, x: 0, y: 0, width, height, right: width, bottom: height, toJSON() {} });
      if (this.getAttribute("data-testid") === "elosern-stage") return box(1451, 790);
      const metric = this.getAttribute("data-metric");
      if (metric && metric in PROBE) return box(1, PROBE[metric]);
      return original.call(this);
    });
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    wrapper = mount(AppClient, { attachTo: document.body, global: { stubs: { transition: false, "transition-group": false } } });
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
  });
  afterEach(() => {
    wrapper.unmount();
    document.body.replaceChildren();
    vi.restoreAllMocks();
  });

  const foeRow = (identity, token, name, hp) => ({
    identity, token, display_name: name, team: "foes", state: "active", hp_current: hp, hp_maximum: 24, portrait_ref: null, conditions: [],
  });

  it("gives every drawn figure but the controlled one its plate at its slot, with tokens only for repeated names", async () => {
    const slots = PARTY_PANEL_FULL_SAMPLE.slots.slice(0, 2);
    const participants = [
      foeRow(201, "e1", "哥布林", 24),
      foeRow(202, "e2", "哥布林", 9),
      foeRow(203, "e3", "哥布林", 24),
      foeRow(204, "e4", "狼", 20),
      { identity: 101, token: "a2", display_name: "蕾娜", team: "party", state: "active", hp_current: 42, hp_maximum: 120, portrait_ref: null, conditions: [] },
    ];
    store.receive(1, "ui_snapshot", [fx.snapshot({
      presentation_epoch: fx.EPOCH_A, revision: 1, mode: "combat",
      panels: {
        status: fx.statusPanel(),
        exploration: fx.explorationPanel(),
        party: { ...PARTY_PANEL_FULL_SAMPLE, slots },
        context_actions: fx.combatActions({ participants }),
        art: ART_PANEL_SAMPLE,
      },
    })], {});
    await nextTick();
    await nextTick();
    const layer = wrapper.get('[data-anchor="plates"]');
    const plates = layer.findAll('[data-testid="figure-plate"]');
    // Two companions and four foes; the controlled figure's values stay in the vitals.
    expect(plates.map((p) => `${p.attributes("data-side")}:${p.attributes("data-identity")}`)).toEqual([
      "party:101", "party:102", "foes:201", "foes:202", "foes:203", "foes:204",
    ]);
    const shape = combatFormation({
      stageWidth: 1451, stageHeight: 790, uiScale: 1, bandTop: 570, actorHeight: 489.8, topBandBottom: 48,
      vitalsDock: null, partyCount: 3, foeCount: 4,
    });
    const expectedSlots = [...shape.party.figures.slice(1), ...shape.foes.figures].map((f) => f.plate);
    plates.forEach((plate, index) => {
      const slot = expectedSlots[index];
      expect(plate.attributes("data-form")).toBe(slot.form);
      expect(plate.element.style.left).toBe(`${slot.left}px`);
      expect(plate.element.style.top).toBe(`${slot.top}px`);
    });
    const tokens = plates.map((p) => p.find('[data-testid="figure-plate-token"]').exists() ? p.get('[data-testid="figure-plate-token"]').text() : null);
    expect(tokens).toEqual([null, null, "e1", "e2", "e3", null]);
    // The companion's numbers come from its participant row; one with no row
    // reads a dash rather than a guessed value.
    expect(plates[0].attributes("aria-label")).toBe("蕾娜 a2，我方，生命 42/120");
    expect(plates[1].get(".figure-plate__current").text()).toBe("--");
    expect(plates[3].attributes("aria-label")).toBe("哥布林 e2，敵方，生命 9/24");
    // Leaving combat empties the layer.
    store.receive(1, "ui_update", [fx.update({ revision: 2, mode: "exploration", panels: { context_actions: fx.explorationActions() } })], {});
    await nextTick();
    await nextTick();
    expect(wrapper.get('[data-anchor="plates"]').findAll('[data-testid="figure-plate"]').filter((p) => !p.element.inert)).toHaveLength(0);
  });

  it("gives the player's own figure a plate while a companion is possessed, and none to the possessed one", async () => {
    // Possession (the controlled figure is the possessed companion): the
    // player's own figure stands as a non-controlled figure and carries its
    // plate, joined to its participant row by identity; the controlled
    // companion's values stay in the vitals dock.
    const roster = {
      schema_version: 3, available: true,
      characters: [{ identity: 1, name: "測試主角", current: true, pending: false, portrait: {
        subject_id: "portrait:character:1",
        revision: "1".repeat(64),
        generation_subject: "portrait:character:1",
        generation_state: "missing",
        attempts: [],
        terminal: null,
        retention_sources: [],
      } }],
      max_characters: 5, can_create: true, switch_locked: false, lock_reason: null,
    };
    const participants = [
      foeRow(201, "e1", "狼", 20),
      { identity: 1, token: "a1", display_name: "測試主角", team: "party", state: "active", hp_current: 80, hp_maximum: 100, portrait_ref: null, conditions: [] },
      { identity: 102, token: "a2", display_name: "幽", team: "party", state: "active", hp_current: 144, hp_maximum: 160, portrait_ref: null, conditions: [] },
    ];
    const response = store.receive(1, "ui_snapshot", [fx.snapshot({
      presentation_epoch: fx.EPOCH_A, revision: 1, mode: "combat",
      panels: {
        status: fx.statusPanel({ actor: { identity: "102" } }),
        roster,
        possession_banner: { schema_version: 1, available: true, host_name: "幽", since_tick: 1 },
        party: { ...PARTY_PANEL_FULL_SAMPLE, slots: PARTY_PANEL_FULL_SAMPLE.slots.slice(0, 2) },
        context_actions: fx.combatActions({ participants }),
        art: ART_PANEL_SAMPLE,
      },
    })], {});
    expect(response.accepted).toBe(true);
    await nextTick();
    await nextTick();
    const figures = wrapper.findAll('[data-testid="companion-figure"]').map((f) => [f.attributes("data-identity"), f.attributes("data-controlled")]);
    expect(figures).toEqual([["102", "true"], ["101", "false"], ["1", "false"]]);
    const plates = wrapper.findAll('[data-anchor="plates"] [data-testid="figure-plate"]');
    expect(plates.map((p) => `${p.attributes("data-side")}:${p.attributes("data-identity")}`)).toEqual([
      "party:101", "party:1", "foes:201",
    ]);
    expect(plates[1].attributes("aria-label")).toBe("測試主角 a1，我方，生命 80/100");
  });
});
