// webclient-party-status-tab: the party window's 狀態 tab. The first trait
// with layers is selected on open and a changed viewed member resets the
// selection; the waterfall lists base, every committed layer in payload
// order with its source text label, then the effective total; raised and
// lowered totals are signed and glyphed besides their colour; no gem or
// merit renders without a rank; a condition shows its source, remaining time
// and modifiers; an active disguise is a labelled footer that never replaces
// a true row; the tab renders the committed values in combat and has no
// possession input.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import PartyStatusTab from "../../components/PartyStatusTab.vue";
import PartyWindow from "../../components/PartyWindow.vue";
import { rememberPartyWindowTab, resetPartyWindowMemory } from "../../components/party-window-memory.js";
import {
  defaultSelection,
  formatLayerAmount,
  formatRemaining,
  layerSource,
  signedDelta,
  SEVERITIES,
  statusTraits,
} from "../../components/party-status-model.js";
import {
  CHARACTER_PANEL_SAMPLE,
  CHARACTER_PANEL_UNDISGUISED_SAMPLE,
  CHARACTER_STATUS_COMPANION_SAMPLE,
} from "../../stories/fixtures/character_panels.js";
import { PARTY_PANEL_EMPTY_SAMPLE, PARTY_WINDOW_PANEL_SAMPLE } from "../../stories/fixtures/party_panels.js";

const SCOPE = "1|1";
const LENA = PARTY_WINDOW_PANEL_SAMPLE.slots.find((row) => row.identity === 101);
const COMMANDER = PARTY_PANEL_EMPTY_SAMPLE.slots[0];

describe("PartyStatusTab (webclient-party-status-tab)", () => {
  let wrapper;

  beforeEach(() => {
    resetPartyWindowMemory();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountTab(props = {}) {
    wrapper = mount(PartyStatusTab, {
      attachTo: document.body,
      props: { member: LENA, character: CHARACTER_STATUS_COMPANION_SAMPLE, ...props },
    });
    return wrapper;
  }

  function mountWindow(props = {}) {
    rememberPartyWindowTab(SCOPE, "status");
    wrapper = mount(PartyWindow, {
      attachTo: document.body,
      props: { party: PARTY_WINDOW_PANEL_SAMPLE, character: CHARACTER_STATUS_COMPANION_SAMPLE, memoryScope: SCOPE, ...props },
    });
    return wrapper;
  }

  const byTestId = (id) => wrapper.get(`[data-testid="${id}"]`);
  const findTestId = (id) => wrapper.find(`[data-testid="${id}"]`);

  it("selects the first trait with layers on open and lists only the four static traits", () => {
    mountTab();
    const options = wrapper.findAll('[data-testid^="party-status-tab__trait--"]').map((node) => node.attributes("data-testid"));
    expect(options).toEqual([
      "party-status-tab__trait--atk_phys",
      "party-status-tab__trait--agility",
      "party-status-tab__trait--defense",
      "party-status-tab__trait--magic_power",
    ]);
    // 攻擊 has no layers, so 敏捷 (the first layered trait) is selected.
    expect(byTestId("party-status-tab__trait--agility").attributes("aria-selected")).toBe("true");
    expect(byTestId("party-status-tab__trait--agility").attributes("tabindex")).toBe("0");
    expect(byTestId("party-status-tab__trait--atk_phys").attributes("tabindex")).toBe("-1");
    expect(byTestId("party-status-tab__detail-title").text()).toBe("敏捷 10");
  });

  it("shows the 魔力 waterfall: base, four labelled layers in order, then 27", async () => {
    mountTab();
    await byTestId("party-status-tab__trait--magic_power").trigger("click");
    expect(byTestId("party-status-tab__step--base").text()).toContain("18");
    const layers = wrapper.findAll('[data-testid^="party-status-tab__layer--"]');
    expect(layers.map((node) => node.find(".party-status-tab__step-name").text())).toEqual([
      "樺木法杖裝備 ‧ 固定值",
      "月石墜裝備 ‧ 固定值",
      "冥想技能 ‧ 固定值",
      "月之祝福狀態 ‧ 百分比",
    ]);
    expect(layers.map((node) => node.attributes("data-source"))).toEqual(["equipment", "equipment", "skill", "condition"]);
    expect(byTestId("party-status-tab__layer-amount--3").text()).toBe("+8%");
    expect(byTestId("party-status-tab__layer-amount--0").classes()).toContain("is-up");
    expect(byTestId("party-status-tab__step--total").text()).toContain("27");
    // The waterfall is an ordered list ending at the effective total.
    const steps = wrapper.findAll('[data-testid="party-status-tab__waterfall"] > li');
    expect(steps).toHaveLength(6);
    expect(steps.at(-1).attributes("data-testid")).toBe("party-status-tab__step--total");
  });

  it("signs and glyphs a raised and a lowered total besides its colour", () => {
    mountTab();
    const raised = byTestId("party-status-tab__trait--magic_power");
    expect(raised.attributes("data-trend")).toBe("up");
    expect(raised.classes()).toContain("is-up");
    expect(byTestId("party-status-tab__effective--magic_power").text()).toBe("27");
    expect(byTestId("party-status-tab__delta--magic_power").text()).toBe("▲ +9");
    expect(raised.attributes("aria-label")).toContain("+9");
    const lowered = byTestId("party-status-tab__trait--agility");
    expect(lowered.classes()).toContain("is-down");
    expect(byTestId("party-status-tab__delta--agility").text()).toBe("▼ −2");
    expect(byTestId("party-status-tab__delta--atk_phys").text()).toBe("");
  });

  it("renders every layer of the 16-layer bound without truncation", async () => {
    mountTab({ member: COMMANDER, character: CHARACTER_PANEL_SAMPLE, initialTrait: "defense" });
    expect(byTestId("party-status-tab__trait--defense").attributes("aria-selected")).toBe("true");
    const layers = wrapper.findAll('[data-testid^="party-status-tab__layer--"]');
    expect(layers).toHaveLength(16);
    expect(layers.map((node) => node.find(".party-status-tab__step-name").element.firstChild.textContent)).toEqual(
      CHARACTER_PANEL_SAMPLE.traits.find((row) => row.key === "defense").layers.map((layer) => layer.name),
    );
    expect(byTestId("party-status-tab__layer-amount--2").text()).toBe("×1.5");
    expect(byTestId("party-status-tab__layer-amount--7").text()).toBe("−15%");
    expect(byTestId("party-status-tab__layer-amount--7").classes()).toContain("is-down");
  });

  it("labels an unknown layer source or kind as 其他", () => {
    expect(layerSource({ source: "unregistered", kind: "flat" }).label).toBe("其他");
    expect(layerSource({ source: "skill", kind: "exp" }).label).toBe("其他");
    expect(layerSource({ source: "skill", kind: "flat" }).label).toBe("技能");
  });

  it("shows the gem and merit with a rank, and neither without one", () => {
    mountTab();
    expect(byTestId("party-status-tab__guild").find('[role="img"]').attributes("aria-label")).toBe("公會階級 F");
    expect(byTestId("party-status-tab__merit").text()).toBe("功績 20");
    expect(byTestId("party-status-tab__title").text()).toBe("F級冒險者　月下藥師");
    wrapper.unmount();
    mountTab({ member: COMMANDER, character: CHARACTER_PANEL_UNDISGUISED_SAMPLE });
    expect(findTestId("party-status-tab__guild").exists()).toBe(false);
    expect(wrapper.find(".grade-gem").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("功績");
    // No composed title: the hero omits the line rather than guessing one.
    expect(findTestId("party-status-tab__title").exists()).toBe(false);
  });

  it("draws the gauges from the party row with a label and numbers", () => {
    mountTab();
    for (const [key, label, value] of [["hp", "HP", "180 / 220"], ["mp", "MP", "60 / 80"], ["sp", "SP", "24 / 40"]]) {
      const gauge = byTestId(`party-status-tab__gauge--${key}`);
      expect(gauge.text()).toContain(label);
      expect(gauge.text()).toContain(value);
    }
    expect(byTestId("party-status-tab__name").text()).toBe("蕾娜");
  });

  it("shows a condition's glyph, remaining time and modifiers, and its detail", async () => {
    mountTab();
    const row = byTestId("party-status-tab__condition--light_fatigue");
    expect(row.find(".party-status-tab__sev").text()).toBe("▼");
    expect(row.text()).toContain("減益");
    expect(byTestId("party-status-tab__remaining--light_fatigue").text()).toBe("剩 40 分");
    expect(byTestId("party-status-tab__modifiers--light_fatigue").text()).toBe("敏捷 -2");
    await row.trigger("click");
    expect(row.attributes("aria-selected")).toBe("true");
    expect(byTestId("party-status-tab__detail-title").text()).toBe("輕微疲勞");
    expect(byTestId("party-status-tab__severity").text()).toBe("▼減益");
    expect(byTestId("party-status-tab__fact--source").text()).toBe("狀態");
    expect(byTestId("party-status-tab__fact--remaining").text()).toBe("40 分");
    expect(byTestId("party-status-tab__fact--modifiers").text()).toBe("敏捷 -2");
    expect(findTestId("party-status-tab__waterfall").exists()).toBe(false);
  });

  it("gives each severity its own glyph shape", () => {
    const glyphs = Object.values(SEVERITIES).map((entry) => entry.glyph);
    expect(new Set(glyphs).size).toBe(5);
    const conditions = Object.keys(SEVERITIES).map((severity, index) => ({
      code: `c${index}`,
      label: severity,
      severity,
      remaining_seconds: null,
      modifiers: {},
      source: "狀態",
    }));
    mountTab({ character: { ...CHARACTER_STATUS_COMPANION_SAMPLE, conditions } });
    const shown = wrapper.findAll(".party-status-tab__sev").map((node) => node.text());
    expect(shown).toEqual(glyphs);
    expect(byTestId("party-status-tab__remaining--c0").text()).toBe("無時限");
  });

  it("formats remaining time exactly and the indefinite case", () => {
    expect(formatRemaining(0)).toBe("0 秒");
    expect(formatRemaining(59)).toBe("59 秒");
    expect(formatRemaining(3600)).toBe("1 小時");
    expect(formatRemaining(3725)).toBe("1 小時 2 分 5 秒");
    expect(formatRemaining(null)).toBe("無時限");
    expect(formatRemaining(-1)).toBe("");
  });

  it("keeps fractional totals exact in the signed delta and layer amounts", () => {
    expect(signedDelta({ base: 0.1, effective: 0.30000000000000004 })).toBe("+0.2");
    expect(signedDelta({ base: 12, effective: 14.5 })).toBe("+2.5");
    expect(formatLayerAmount("mult", -1.2)).toBe("×−1.2");
    expect(formatLayerAmount("flat", -2)).toBe("−2");
  });

  it("shows an active disguise as a labelled footer and keeps every true row", () => {
    mountTab();
    expect(byTestId("party-status-tab__disguise-description").text()).toBe("以旅行的藥草師示人");
    expect(byTestId("party-status-tab__disguise-displayed").text()).toBe("對外顯示：魔力 12、攻擊 8");
    // The true values stay on the rows: 魔力 27 and 攻擊 6, never 12 or 8.
    expect(byTestId("party-status-tab__effective--magic_power").text()).toBe("27");
    expect(byTestId("party-status-tab__effective--atk_phys").text()).toBe("6");
    // The footer sits at the detail's foot, outside the scroll region.
    expect(wrapper.get('[data-testid="list-detail__actions"]').find('[data-testid="party-status-tab__disguise"]').exists()).toBe(true);
    wrapper.unmount();
    mountTab({ member: COMMANDER, character: CHARACTER_PANEL_UNDISGUISED_SAMPLE });
    expect(findTestId("party-status-tab__disguise").exists()).toBe(false);
    expect(byTestId("party-status-tab__no-conditions").text()).toBe("無");
  });

  it("resets the selection when the viewed member changes", async () => {
    mountTab();
    await byTestId("party-status-tab__trait--magic_power").trigger("click");
    await wrapper.setProps({ member: COMMANDER, character: CHARACTER_PANEL_SAMPLE });
    expect(byTestId("party-status-tab__trait--atk_phys").attributes("aria-selected")).toBe("true");
  });

  it("shows no character section for a payload about another member", () => {
    mountTab({ character: CHARACTER_PANEL_SAMPLE });
    expect(byTestId("party-status-tab__name").text()).toBe("蕾娜");
    expect(findTestId("party-status-tab__listbox").exists()).toBe(false);
    expect(findTestId("party-status-tab__guild").exists()).toBe(false);
    expect(findTestId("party-status-tab__waterfall").exists()).toBe(false);
  });

  it("states an unavailable character panel's committed reason", () => {
    mountTab({ character: { schema_version: 9, available: false, kind: "character", reason: { code: "character_unavailable", message: "角色資料目前無法顯示" } } });
    expect(byTestId("party-window__tab-unavailable").text()).toBe("角色資料目前無法顯示");
    expect(findTestId("party-status-tab__listbox").exists()).toBe(false);
  });

  it("moves focus across both groups with the arrow keys, Home and End", async () => {
    mountTab();
    const listbox = byTestId("party-status-tab__listbox");
    expect(listbox.attributes("aria-label")).toBe("屬性與狀態");
    expect(listbox.findAll('[role="group"]').map((node) => node.attributes("aria-label"))).toEqual(["屬性", "狀態"]);
    byTestId("party-status-tab__trait--magic_power").element.focus();
    await listbox.trigger("keydown", { key: "ArrowDown" });
    expect(document.activeElement.dataset.testid).toBe("party-status-tab__condition--moon_blessing");
    await listbox.trigger("keydown", { key: "End" });
    expect(document.activeElement.dataset.testid).toBe("party-status-tab__condition--light_fatigue");
    await listbox.trigger("keydown", { key: "Home" });
    expect(document.activeElement.dataset.testid).toBe("party-status-tab__trait--atk_phys");
  });

  it("opens inside the party window and keeps the values in combat", () => {
    mountWindow({ combat: true });
    expect(byTestId("party-window").attributes("data-tab")).toBe("status");
    expect(findTestId("party-window__tab-unavailable").exists()).toBe(false);
    expect(byTestId("party-status-tab__effective--magic_power").text()).toBe("27");
    expect(byTestId("party-status-tab__trait--agility").attributes("aria-selected")).toBe("true");
  });

  it("selects the trait a story names through the window", () => {
    mountWindow({ statusTrait: "magic_power" });
    expect(byTestId("party-status-tab__detail-title").text()).toBe("魔力 27");
  });

  it("renders identically whatever the player controls: it has no possession input", () => {
    expect(Object.keys(PartyStatusTab.props)).not.toContain("possessing");
    mountWindow();
    const first = byTestId("party-status-tab").html();
    wrapper.unmount();
    mountWindow();
    expect(byTestId("party-status-tab").html()).toBe(first);
    expect(wrapper.text()).not.toMatch(/你|自己|操控中/);
  });

  it("selects the first layered trait when the payload arrives after the member", async () => {
    mountTab({ character: null, initialTrait: "defense" });
    expect(findTestId("party-status-tab__listbox").exists()).toBe(false);
    await wrapper.setProps({ character: CHARACTER_STATUS_COMPANION_SAMPLE });
    // The first selection still honours the requested trait.
    expect(byTestId("party-status-tab__trait--defense").attributes("aria-selected")).toBe("true");
    // A later payload that drops the selected row falls back to the first
    // layered trait, not to the requested one again.
    await byTestId("party-status-tab__condition--moon_blessing").trigger("click");
    await wrapper.setProps({ character: { ...CHARACTER_STATUS_COMPANION_SAMPLE, conditions: [] } });
    expect(byTestId("party-status-tab__trait--agility").attributes("aria-selected")).toBe("true");
  });

  it("keeps two rows of the same condition code apart", async () => {
    const twice = CHARACTER_STATUS_COMPANION_SAMPLE.conditions[1];
    mountTab({ character: { ...CHARACTER_STATUS_COMPANION_SAMPLE, conditions: [twice, { ...twice, source: "裝備", remaining_seconds: 60 }] } });
    await byTestId("party-status-tab__condition--light_fatigue#2").trigger("click");
    expect(wrapper.findAll('[role="option"][aria-selected="true"]')).toHaveLength(1);
    expect(byTestId("party-status-tab__fact--source").text()).toBe("裝備");
  });

  it("renders no empty 狀態 group inside the listbox without conditions", () => {
    mountTab({ member: COMMANDER, character: CHARACTER_PANEL_UNDISGUISED_SAMPLE });
    const groups = byTestId("party-status-tab__listbox").findAll('[role="group"]');
    expect(groups.map((node) => node.attributes("aria-label"))).toEqual(["屬性"]);
    expect(byTestId("party-status-tab__no-conditions").text()).toBe("無");
  });

  it("pairs each gauge with an icon shape besides its label", () => {
    mountTab();
    const paths = ["hp", "mp", "sp"].map((key) => byTestId(`party-status-tab__gauge--${key}`).get("svg path").attributes("d"));
    expect(new Set(paths).size).toBe(3);
  });

  it("falls back to the first trait, then the first condition", () => {
    const traits = statusTraits(CHARACTER_PANEL_UNDISGUISED_SAMPLE);
    expect(defaultSelection(traits, [])).toEqual({ type: "trait", key: "atk_phys" });
    expect(defaultSelection([], [{ code: "regen" }])).toEqual({ type: "condition", key: "regen" });
    expect(defaultSelection([], [])).toBeNull();
  });
});
