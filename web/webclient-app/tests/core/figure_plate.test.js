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
import CombatMenu from "../../lib/combat_menu.js";
import { combatFormation } from "../../components/combat-formation.js";
import { bySeverity, isLowPlateHp, plateHpCurrent, plateHpPercent, plateLabel, repeatedNames } from "../../components/figure-plate.js";
import { useElosernStore } from "../../stores/elosern.js";
import { PARTY_PANEL_FULL_SAMPLE } from "../../stories/fixtures/party_panels.js";
import { ART_PANEL_SAMPLE } from "../../stories/fixtures.js";
import * as fx from "../store/protocol_fixtures.js";

// Every journey here mounts the whole shell and drives real commits, so an
// individual test can exceed Vitest's default budget on a shared runner: the
// file carries the same explicit headroom the project's other mount-heavy
// suites use.
vi.setConfig({ testTimeout: 20000 });

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
    // Line 3 holds the condition glyphs: none committed, none drawn.
    expect(plate.get('[data-testid="figure-plate-glyphs"]').text()).toBe("");
    // A named group, a stop of the plates group only (tabindex -1), with
    // nothing of its own in the tab order.
    expect(plate.attributes("role")).toBe("group");
    expect(plate.attributes("tabindex")).toBe("-1");
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

// webclient-combat-figure-plates (design D2/D3/D5): the glyph line, the
// low-HP alarm and the accessible name with the conditions.
const cond = (code, label, severity) => ({ code, label, severity });
const POISON = cond("poison", "中毒", "harmful");
const BLESS = cond("bless", "祝福", "beneficial");
const FIVE = [cond("c1", "灼燒", "harmful"), cond("c2", "疾風", "beneficial"), cond("c3", "迷霧", "informational"), cond("c4", "暈眩", "critical"), cond("c5", "遲緩", "warning")];
const EIGHT = [...FIVE, cond("c6", "護盾", "beneficial"), cond("c7", "流血", "harmful"), cond("c8", "恐懼", "warning")];

describe("FigurePlate conditions and alarm", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.replaceChildren();
  });
  const glyphs = (w) => w.findAll('[data-testid^="figure-plate__condition--"]');
  const overflow = (w) => w.find('[data-testid="figure-plate__condition-overflow"]');
  const tip = () => document.querySelector('[data-testid="figure-plate__condition-tooltip"]');

  it("shows a full plate's conditions as glyphs on the third line, three and +N at most", () => {
    wrapper = mount(FigurePlate, { props: { name: "哥布林", token: "e1", side: "foes", hpCurrent: 20, hpMaximum: 24, form: "full", conditions: [POISON, BLESS] } });
    const line = wrapper.get('[data-testid="figure-plate-glyphs"]');
    expect(glyphs(wrapper).map((g) => g.get(".glyph").text())).toEqual(["▼", "▲"]);
    expect(glyphs(wrapper).map((g) => g.attributes("data-code"))).toEqual(["poison", "bless"]);
    expect(line.findAll("button").every((b) => b.attributes("tabindex") === "-1")).toBe(true);
    expect(glyphs(wrapper)[0].attributes("aria-label")).toBe("中毒");
    // No condition word is permanently visible.
    expect(wrapper.text()).not.toContain("中毒");
    expect(overflow(wrapper).exists()).toBe(false);
    // The name and the stroke keep their own lines.
    expect(wrapper.get(".figure-plate__name").find("button").exists()).toBe(false);
    expect(wrapper.get(".figure-plate__line").find("button").exists()).toBe(false);
  });

  it("caps a full plate at three glyphs, most severe first, and a +N whose tooltip lists the hidden ones", async () => {
    wrapper = mount(FigurePlate, { attachTo: document.body, props: { name: "蕾娜", side: "party", hpCurrent: 90, hpMaximum: 120, form: "full", conditions: EIGHT } });
    // critical, then harmful (committed order), …
    expect(glyphs(wrapper).map((g) => g.attributes("data-code"))).toEqual(["c4", "c1", "c7"]);
    expect(overflow(wrapper).text()).toBe("+5");
    await overflow(wrapper).trigger("mouseenter");
    expect([...tip().querySelectorAll(".tip-item .detail-label")].map((n) => n.textContent)).toEqual(["遲緩", "恐懼", "迷霧", "疾風", "護盾"]);
    await overflow(wrapper).trigger("mouseleave");
    expect(tip()).toBeNull();
    // A five-condition companion: three glyphs and +2.
    await wrapper.setProps({ conditions: FIVE });
    expect(glyphs(wrapper)).toHaveLength(3);
    expect(overflow(wrapper).text()).toBe("+2");
    // Four fit the line's four boxes: no +N.
    await wrapper.setProps({ conditions: FIVE.slice(0, 4) });
    expect(glyphs(wrapper)).toHaveLength(4);
    expect(overflow(wrapper).exists()).toBe(false);
    // Low, the 危險 tag opens the line and two boxes remain: a glyph and +N.
    await wrapper.setProps({ hpCurrent: 20 });
    const line = wrapper.get('[data-testid="figure-plate-glyphs"]');
    expect(line.element.firstElementChild.getAttribute("data-testid")).toBe("figure-plate-danger");
    expect(glyphs(wrapper).map((g) => g.attributes("data-code"))).toEqual(["c4"]);
    expect(overflow(wrapper).text()).toBe("+3");
    await wrapper.setProps({ conditions: [POISON, BLESS] });
    expect(glyphs(wrapper)).toHaveLength(2);
    expect(overflow(wrapper).exists()).toBe(false);
  });

  it("shows a compact plate's most severe glyph and +N, in severity order", () => {
    wrapper = mount(FigurePlate, { props: { name: "狼", side: "foes", hpCurrent: 20, hpMaximum: 24, form: "compact", conditions: [BLESS, POISON, cond("x", "暈眩", "critical")] } });
    expect(glyphs(wrapper).map((g) => g.attributes("data-code"))).toEqual(["x"]);
    expect(overflow(wrapper).text()).toBe("+2");
    expect(wrapper.attributes("aria-label")).toBe("狼，敵方，生命 20/24，狀態：祝福、中毒、暈眩");
    expect(wrapper.find('[data-testid="figure-plate-danger"]').exists()).toBe(false);
  });

  it("folds a low compact plate's +N into its glyph to make room for 危險", async () => {
    wrapper = mount(FigurePlate, { attachTo: document.body, props: { name: "狼", side: "foes", hpCurrent: 6, hpMaximum: 24, form: "compact", conditions: [BLESS, POISON, cond("x", "暈眩", "critical")] } });
    const line = wrapper.get('[data-testid="figure-plate-glyphs"]');
    expect(line.get('[data-testid="figure-plate-danger"]').text()).toBe("危險");
    expect(overflow(wrapper).exists()).toBe(false);
    const carrier = glyphs(wrapper)[0];
    expect(carrier.attributes("data-code")).toBe("x");
    expect(carrier.attributes("data-carries")).toBe("2");
    expect(carrier.attributes("aria-label")).toBe("暈眩；中毒；祝福");
    await carrier.trigger("focus");
    expect([...tip().querySelectorAll(".tip-item .detail-label")].map((n) => n.textContent)).toEqual(["暈眩", "中毒", "祝福"]);
    expect(wrapper.attributes("aria-label")).toBe("狼，敵方，生命 6/24，危險，狀態：祝福、中毒、暈眩");
  });

  it.each(["full", "compact"])("raises the 危險 alarm at exactly 25%% and not at 26%% (%s)", async (form) => {
    wrapper = mount(FigurePlate, { props: { name: "蕾娜", side: "party", hpCurrent: 25, hpMaximum: 100, form } });
    expect(wrapper.attributes("data-low-hp")).toBe("true");
    expect(wrapper.get('[data-testid="figure-plate-danger"]').text()).toBe("危險");
    expect(wrapper.get(".figure-plate__current").classes()).toContain("figure-plate__current--low");
    // The tag opens the glyph line in both forms; the name keeps its line.
    expect(wrapper.get('[data-testid="figure-plate-glyphs"]').find('[data-testid="figure-plate-danger"]').exists()).toBe(true);
    expect(wrapper.get(".figure-plate__name").find('[data-testid="figure-plate-danger"]').exists()).toBe(false);
    await wrapper.setProps({ hpCurrent: 26 });
    expect(wrapper.attributes("data-low-hp")).toBeUndefined();
    expect(wrapper.find('[data-testid="figure-plate-danger"]').exists()).toBe(false);
    expect(wrapper.get(".figure-plate__current").classes()).not.toContain("figure-plate__current--low");
  });

  it("closes an open tooltip on the close signal, keeps it across a same-content commit, and closes it when the condition goes", async () => {
    wrapper = mount(FigurePlate, { attachTo: document.body, props: { name: "哥布林", side: "foes", hpCurrent: 20, hpMaximum: 24, conditions: [POISON, BLESS] } });
    await glyphs(wrapper)[0].trigger("mouseenter");
    expect(tip().textContent).toContain("中毒");
    // A new revision with the same content keeps it open.
    await wrapper.setProps({ conditions: [{ ...POISON }, { ...BLESS }] });
    expect(tip()).not.toBeNull();
    await wrapper.setProps({ closeSignal: 1 });
    expect(tip()).toBeNull();
    await glyphs(wrapper)[0].trigger("mouseenter");
    expect(tip()).not.toBeNull();
    await wrapper.setProps({ conditions: [BLESS] });
    expect(tip()).toBeNull();
  });

  it("keeps the glyph styling in the component, its hit boxes inside the slot", () => {
    const plateCss = readFileSync(join(APP_ROOT, "components/FigurePlate.vue"), "utf8");
    expect(plateCss).toMatch(/\.figure-plate__glyphs \{[^}]*align-self: end;[^}]*height: calc\(24px \* var\(--ui-scale\)\);/);
    const chipsCss = readFileSync(join(APP_ROOT, "components/ConditionChips.vue"), "utf8");
    expect(chipsCss).toMatch(/\.conditions--plate \.chip \{[^}]*width: calc\(24px \* var\(--ui-scale\)\);[^}]*height: calc\(24px \* var\(--ui-scale\)\);/);
    // The app shell carries no duplicate of these rules (web/webclient-app/AGENTS.md).
    const shell = readFileSync(join(APP_ROOT, "styles/app-shell.css"), "utf8");
    expect(shell).not.toMatch(/figure-plate|conditions--plate|condition-tip/);
  });
});

describe("fallen plates (webclient-combat-defeated-foes D1)", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("replaces a defeated foe's numbers with ✕ 已擊破 over an empty dashed stroke, in both forms", async () => {
    wrapper = mount(FigurePlate, {
      props: { name: "哥布林", token: "e1", side: "foes", hpCurrent: 0, hpMaximum: 24, box: BOX, fallen: "defeated", conditions: [POISON] },
    });
    expect(wrapper.attributes("data-fallen")).toBe("defeated");
    expect(wrapper.get('[data-testid="figure-plate-fallen"]').text()).toBe("✕已擊破");
    expect(wrapper.get(".figure-plate__fallen-glyph").text()).toBe("✕");
    expect(wrapper.find('[data-testid="figure-plate-readout"]').exists()).toBe(false);
    expect(wrapper.get(".figure-plate__fill").attributes("style")).toContain("width: 0%");
    // The name stays; no alarm and no condition glyph on a defeated foe.
    expect(wrapper.get(".figure-plate__name-text").text()).toBe("哥布林");
    expect(wrapper.find('[data-testid="figure-plate-danger"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="figure-plate-glyphs"]').findAll(".chip")).toHaveLength(0);
    expect(wrapper.attributes("aria-label")).toBe("哥布林 e1，敵方，生命 0/24，已擊破");
    // Compact: the stroke spans its line, the glyph and the word stand on the glyph line.
    await wrapper.setProps({ form: "compact" });
    const fallen = wrapper.get('[data-testid="figure-plate-fallen"]');
    expect(fallen.text()).toBe("✕已擊破");
    expect(wrapper.get('[data-testid="figure-plate-glyphs"]').find('[data-testid="figure-plate-fallen"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="figure-plate-readout"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="figure-plate-stroke"]').exists()).toBe(true);
  });

  it("states a downed ally as ▼ 倒地 and keeps its conditions", () => {
    wrapper = mount(FigurePlate, {
      props: { name: "蕾娜", token: "a2", side: "party", hpCurrent: 0, hpMaximum: 120, box: BOX, fallen: "down", conditions: [POISON] },
    });
    expect(wrapper.attributes("data-fallen")).toBe("down");
    expect(wrapper.get('[data-testid="figure-plate-fallen"]').text()).toBe("▼倒地");
    expect(wrapper.find('[data-testid="figure-plate-danger"]').exists()).toBe(false);
    expect(wrapper.attributes("aria-label")).toBe("蕾娜 a2，我方，生命 0/120，狀態：中毒，倒地");
  });

  it("ends the accessible name with the fallen word", () => {
    const base = { name: "狼", token: "e4", side: "foes", current: 2, maximum: 20, conditions: [POISON] };
    expect(plateLabel({ ...base, fallen: "defeated" })).toBe("狼 e4，敵方，生命 2/20，已擊破");
    expect(plateLabel({ ...base, side: "party", fallen: "down" })).toBe("狼 e4，我方，生命 2/20，狀態：中毒，倒地");
    // A standing figure keeps its alarm and conditions.
    expect(plateLabel(base)).toBe("狼 e4，敵方，生命 2/20，危險，狀態：中毒");
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

  it("raises low hit points at the vitals threshold, never without numbers", () => {
    expect(isLowPlateHp(25, 100)).toBe(true);
    expect(isLowPlateHp(26, 100)).toBe(false);
    expect(isLowPlateHp(0, 30)).toBe(true);
    expect(isLowPlateHp(null, 30)).toBe(false);
    expect(isLowPlateHp(0, 0)).toBe(false);
  });

  it("orders conditions by severity, committed order within one", () => {
    const rows = [cond("a", "A", "beneficial"), cond("b", "B", "harmful"), cond("c", "C", "warning"), cond("d", "D", "harmful"), cond("e", "E", "critical"), cond("f", "F", "informational")];
    expect(bySeverity(rows).map((c) => c.code)).toEqual(["e", "b", "d", "c", "f", "a"]);
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

  // webclient-combat-stage-target-picking: in the stage target step the plates
  // are never dimmed (they carry the hit points the choice depends on); the
  // arrow markers stand at the candidates' marker slots in stage order with
  // the server-order digits; the focused one is the filled arrow.
  it("keeps the plates undimmed in a stage target step and marks the candidates above them", async () => {
    const attack = {
      key: CombatMenu.BASIC_ATTACK_KEY, label: "普通攻擊", description: "合成描述。", cost: {}, target_spec: "single", element: null,
      enabled: true, disabled_reason: null, targets: [201, 202, 203], shorthands: [], hostile: true, beneficial: false,
    };
    const participants = [foeRow(201, "e1", "哥布林", 24), foeRow(202, "e2", "狼", 20), foeRow(203, "e3", "蝙蝠", 12), foeRow(204, "e4", "史萊姆", 8)];
    store.receive(1, "ui_snapshot", [fx.snapshot({
      presentation_epoch: fx.EPOCH_A, revision: 1, mode: "combat",
      panels: {
        status: fx.statusPanel(), exploration: fx.explorationPanel(), art: ART_PANEL_SAMPLE,
        context_actions: fx.combatActions({ participants, skills: [{ category: "martial_arts", label: "武技", groups: [{ group: null, label: null, skills: [attack] }] }] }),
      },
    })], {});
    await nextTick();
    await nextTick();
    expect(wrapper.findAll('[data-testid="stage-target-marker"]')).toHaveLength(0);
    store.focusItemByKey("attack");
    store.focusPress("Enter");
    await nextTick();
    await nextTick();
    const markers = wrapper.findAll('[data-testid="stage-target-marker"]');
    expect(markers.map((m) => m.attributes("data-identity")).sort()).toEqual(["201", "202", "203"]);
    // Left to right on the stage equals the step's member order.
    const byLeft = [...markers].sort((a, b) => parseFloat(a.element.style.left) - parseFloat(b.element.style.left));
    expect(byLeft.map((m) => `target-${m.attributes("data-identity")}`)).toEqual(store.view.stageTarget.positions.map((p) => p.key));
    expect(markers.find((m) => m.attributes("data-identity") === "201").attributes("data-state")).toBe("focus");
    expect(markers.find((m) => m.attributes("data-identity") === "202").attributes("data-state")).toBe("selectable");
    expect(markers.find((m) => m.attributes("data-identity") === "202").text()).toBe("2");
    // The plates take no dim and no speaking state.
    for (const plate of wrapper.findAll('[data-anchor="plates"] [data-testid="figure-plate"]')) {
      expect(plate.attributes("data-speaking")).toBeUndefined();
      expect(plate.element.style.filter || "").toBe("");
    }
    // The non-candidate foe is dimmed and carries no hit area; Escape ends the step.
    const slot = wrapper.get('[data-testid="foe-slot"][data-identity="204"]');
    expect(slot.get('[data-testid="stage-actor"]').attributes("data-speaking")).toBe("false");
    expect(slot.find('[data-testid="stage-target-hit"]').exists()).toBe(false);
    store.focusEscape();
    await nextTick();
    expect(wrapper.findAll('[data-testid="stage-target-marker"]')).toHaveLength(0);
    expect(wrapper.findAll('[data-testid="stage-target-hit"]')).toHaveLength(0);
    expect(wrapper.get('[data-testid="foe-slot"][data-identity="204"] [data-testid="stage-actor"]').attributes("data-speaking")).toBe("true");
  });

  it("passes each participant's conditions and stage x to its plate, and closes a plate tooltip when a round starts", async () => {
    const participants = [
      { ...foeRow(201, "e1", "哥布林", 24), conditions: [POISON] },
      foeRow(202, "e2", "狼", 4),
    ];
    store.receive(1, "ui_snapshot", [fx.snapshot({
      presentation_epoch: fx.EPOCH_A, revision: 1, mode: "combat",
      panels: { status: fx.statusPanel(), exploration: fx.explorationPanel(), context_actions: fx.combatActions({ participants }), art: ART_PANEL_SAMPLE },
    })], {});
    await nextTick();
    await nextTick();
    const plates = wrapper.findAll('[data-anchor="plates"] [data-testid="figure-plate"]');
    expect(plates[0].find('[data-testid="figure-plate__condition--poison"]').exists()).toBe(true);
    expect(plates[0].attributes("aria-label")).toBe("哥布林 e1，敵方，生命 24/24，狀態：中毒");
    expect(plates[1].attributes("data-low-hp")).toBe("true");
    for (const plate of plates) {
      const style = plate.element.style;
      expect(Number(plate.attributes("data-stage-x"))).toBeCloseTo(parseFloat(style.left) + parseFloat(style.width) / 2, 3);
    }
    await plates[0].get('[data-testid="figure-plate__condition--poison"]').trigger("mouseenter");
    expect(document.querySelector('[data-testid="figure-plate__condition-tooltip"]')).not.toBeNull();
    store.view.dispatch.beatLocked = true;
    await nextTick();
    await nextTick();
    expect(document.querySelector('[data-testid="figure-plate__condition-tooltip"]')).toBeNull();
  });

  it("closes a plate tooltip when combat ends, even while the plate fades out", async () => {
    const participants = [{ ...foeRow(201, "e1", "哥布林", 24), conditions: [POISON] }];
    store.receive(1, "ui_snapshot", [fx.snapshot({
      presentation_epoch: fx.EPOCH_A, revision: 1, mode: "combat",
      panels: { status: fx.statusPanel(), exploration: fx.explorationPanel(), context_actions: fx.combatActions({ participants }), art: ART_PANEL_SAMPLE },
    })], {});
    await nextTick();
    await nextTick();
    await wrapper.get('[data-testid="figure-plate__condition--poison"]').trigger("mouseenter");
    expect(document.querySelector('[data-testid="figure-plate__condition-tooltip"]')).not.toBeNull();
    store.receive(1, "ui_update", [fx.update({ revision: 2, mode: "exploration", panels: { context_actions: fx.explorationActions() } })], {});
    await nextTick();
    await nextTick();
    expect(document.querySelector('[data-testid="figure-plate__condition-tooltip"]')).toBeNull();
  });

  it("states a defeated foe and a downed companion on their plates, and kneels the companion's figure", async () => {
    const slots = PARTY_PANEL_FULL_SAMPLE.slots.slice(0, 1);
    const participants = [
      { ...foeRow(201, "e1", "哥布林", 0), state: "defeated", conditions: [POISON] },
      { ...foeRow(202, "e2", "狼", 3), state: "knocked_out" },
      foeRow(203, "e3", "史萊姆", 20),
      { identity: slots[0].identity, token: "a2", display_name: slots[0].display_name, team: "party", state: "knocked_out", hp_current: 0, hp_maximum: 120, portrait_ref: null, conditions: [POISON] },
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
    const plate = (identity) => wrapper.get(`[data-anchor="plates"] [data-testid="figure-plate"][data-identity="${identity}"]`);
    expect(plate(201).attributes("data-fallen")).toBe("defeated");
    expect(plate(202).attributes("data-fallen")).toBe("defeated");
    expect(plate(203).attributes("data-fallen")).toBeUndefined();
    expect(plate(slots[0].identity).attributes("data-fallen")).toBe("down");
    expect(plate(201).attributes("aria-label")).toBe("哥布林 e1，敵方，生命 0/24，已擊破");
    expect(plate(slots[0].identity).attributes("aria-label")).toBe(
      `${slots[0].display_name} a2，我方，生命 0/120，狀態：中毒，倒地`,
    );
    // Every figure keeps its slot: three foes stand.
    expect(wrapper.findAll('[data-testid="foe-slot"]').map((s) => s.attributes("data-fallen") ?? null)).toEqual([
      "defeated", "defeated", null,
    ]);
    const companion = wrapper.get(`[data-testid="companion-figure"][data-identity="${slots[0].identity}"]`);
    expect(companion.attributes("data-fallen")).toBe("down");
    expect(companion.find('[data-testid="stage-actor-seal"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="companion-figure"][data-controlled="true"]').attributes("data-fallen")).toBeUndefined();
    // Outside combat nobody kneels.
    store.receive(1, "ui_update", [fx.update({ revision: 2, mode: "exploration", panels: { context_actions: fx.explorationActions() } })], {});
    await nextTick();
    await nextTick();
    expect(wrapper.get(`[data-testid="companion-figure"][data-identity="${slots[0].identity}"]`).attributes("data-fallen")).toBeUndefined();
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
