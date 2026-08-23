import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import CreationOverlay from "../../components/CreationOverlay.vue";
import {
  CREATION_PANEL_SAMPLE,
  CREATION_PANEL_PRESET_DRAFT_SAMPLE,
  CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
  CREATION_PANEL_CONCEPT_DRAFT_SAMPLE,
  CREATION_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

// CreationOverlay (B5 overlays family): the character-creation wizard over
// the committed `creation` v1 panel — preset pick, custom form with the
// adult gate on BOTH age fields (design D1), the concept branch, and the
// server-persisted draft resume. Every assertion checks the exact
// `creation.*` envelopes (no invented fields) and the registry-owned
// unavailable reason; the server remains authoritative.

function lastAction(wrapper, actionId) {
  const actions = wrapper.emitted("action") ?? [];
  for (let i = actions.length - 1; i >= 0; i--) {
    if (actions[i][0].action_id === actionId) return actions[i][0];
  }
  return null;
}

async function switchToCustom(wrapper) {
  wrapper.get('[data-testid="creation-mode-custom"]').trigger("click");
  await nextTick();
}

function setAllocations(wrapper, values) {
  for (const [axis, value] of Object.entries(values)) {
    wrapper.get(`[data-testid="creation-field-${axis}"`).setValue(value);
  }
}

describe("CreationOverlay (B5 overlays family)", () => {
  // -- Preset state ---------------------------------------------------------
  it("renders the preset cards with count and labels", () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    const cards = wrapper.findAll('[data-testid="creation-preset-card"]');
    expect(cards.length).toBe(3);
    const names = wrapper.findAll('[data-testid="creation-preset-name"]').map((el) => el.text());
    expect(names).toEqual(["流浪劍客", "燈下學士", "碼頭腳夫"]);
  });

  it("activating a preset card emits creation.preset with the exact payload", () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    wrapper.findAll('[data-testid="creation-preset-card"]')[1].trigger("click");
    expect(lastAction(wrapper, "creation.preset")).toEqual({
      action_id: "creation.preset",
      payload: { preset_key: "preset_lantern_scholar" },
    });
  });

  // -- Custom state + adult gate --------------------------------------------
  it("custom confirm emits creation.custom with the exact payload fields", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-displayName"]').setValue("測試者");
    wrapper.get('[data-testid="creation-field-age"]').setValue(21);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(21);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2 });
    wrapper.get('[data-testid="creation-background"]').setValue("測試背景。");
    wrapper.get('[data-testid="creation-affinity-fire"]').element.checked = true;
    wrapper.get('[data-testid="creation-affinity-fire"]').trigger("change");
    wrapper.get('[data-testid="creation-affinity-wind"]').element.checked = true;
    wrapper.get('[data-testid="creation-affinity-wind"]').trigger("change");
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    expect(lastAction(wrapper, "creation.custom")).toEqual({
      action_id: "creation.custom",
      payload: {
        display_name: "測試者",
        age: 21,
        apparent_age: 21,
        race: "human",
        subrace: null,
        allocations: { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2 },
        background: "測試背景。",
        affinity_elements: ["fire", "wind"],
      },
    });
  });

  it("the adult gate rejects age below 18 (gate error, no creation.custom)", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-age"]').setValue(17);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(21);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    await nextTick();
    expect(wrapper.get('[data-testid="creation-form-message"]').exists()).toBe(true);
    expect(lastAction(wrapper, "creation.custom")).toBeNull();
  });

  it("the adult gate rejects apparent_age below 18 (gate error, no creation.custom)", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-age"]').setValue(21);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(17);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    await nextTick();
    expect(wrapper.get('[data-testid="creation-form-message"]').exists()).toBe(true);
    expect(lastAction(wrapper, "creation.custom")).toBeNull();
  });

  it("both ages at or above 18 pass the gate and emit creation.custom", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-age"]').setValue(30);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(25);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    const event = lastAction(wrapper, "creation.custom");
    expect(event).not.toBeNull();
    expect(event.payload.age).toBe(30);
    expect(event.payload.apparent_age).toBe(25);
    expect(wrapper.find('[data-testid="creation-form-message"]').exists()).toBe(false);
  });

  // -- Concept state ----------------------------------------------------------
  it("typing a concept and applying it emits creation.concept", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    wrapper.get('[data-testid="creation-mode-concept"]').trigger("click");
    await nextTick();
    wrapper.get('[data-testid="creation-field-concept"]').setValue("在燈下研讀古籍的學士。");
    wrapper.get('[data-testid="creation-concept-submit"]').trigger("click");
    expect(lastAction(wrapper, "creation.concept")).toEqual({
      action_id: "creation.concept",
      payload: { concept: "在燈下研讀古籍的學士。" },
    });
  });

  // -- Frame actions ----------------------------------------------------------
  it("the confirm stage renders the confirmation screen and confirms the pending action", async () => {
    const wrapper = mount(CreationOverlay, {
      props: {
        creation: CREATION_PANEL_SAMPLE,
        stage: {
          stage: "confirm",
          confirmItems: [
            { key: "confirm-creation.activate", label: "確認啟用此預設角色？", actionId: "creation.activate" },
            { key: "cancel-creation.activate", label: "取消" },
          ],
          confirmLabel: "確認啟用此預設角色？",
          confirmAction: "creation.activate",
          pendingPresetKey: "human_wanderer",
        },
      },
    });
    // The confirmation screen replaces the wizard body while the confirm stage
    // is active.
    expect(wrapper.get('[data-testid="creation-confirm"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="creation-confirm-title"]').text()).toContain("確認啟用此預設角色？");
    expect(wrapper.find('[data-testid="creation-preset-card"]').exists()).toBe(false);
    wrapper.get('[data-testid="creation-confirm-ok"]').trigger("click");
    expect(lastAction(wrapper, "creation.activate")).toEqual({
      action_id: "creation.activate",
      payload: {},
    });
    // The cancel button pops the confirmation (the AppClient routes it through
    // the keyboard router's escape).
    wrapper.get('[data-testid="creation-confirm-cancel"]').trigger("click");
    expect(wrapper.emitted("cancel-confirm")).toBeTruthy();
  });

  it("the reset button requests the destructive confirmation (no direct creation.reset)", () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    wrapper.get('[data-testid="creation-reset"]').trigger("click");
    expect(wrapper.emitted("request-reset")).toBeTruthy();
    expect(lastAction(wrapper, "creation.reset")).toBeNull();
  });

  // -- Draft resume ----------------------------------------------------------
  it("resumes a preset draft with the saved preset highlighted", () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_PRESET_DRAFT_SAMPLE } });
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("preset");
    const cards = wrapper.findAll('[data-testid="creation-preset-card"]');
    const selected = cards.filter((card) => card.attributes("data-selected") === "true");
    expect(selected.length).toBe(1);
    expect(selected[0].get('[data-testid="creation-preset-name"]').text()).toBe("燈下學士");
  });

  it("resumes a custom draft with the form pre-filled", () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE } });
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("custom");
    expect(wrapper.get('[data-testid="creation-field-displayName"]').element.value).toBe("林楓");
    expect(wrapper.get('[data-testid="creation-field-age"]').element.value).toBe("21");
    expect(wrapper.get('[data-testid="creation-field-apparentAge"]').element.value).toBe("21");
    expect(wrapper.get('[data-testid="creation-field-hp"]').element.value).toBe("8");
    expect(wrapper.get('[data-testid="creation-field-mp"]').element.value).toBe("4");
    expect(wrapper.get('[data-testid="creation-field-sp"]').element.value).toBe("4");
    expect(wrapper.get('[data-testid="creation-field-atk_phys"]').element.value).toBe("4");
    expect(wrapper.get('[data-testid="creation-field-agility"]').element.value).toBe("2");
    expect(wrapper.get('[data-testid="creation-field-defense"]').element.value).toBe("2");
    expect(wrapper.get('[data-testid="creation-background"]').element.value).toBe("從渡口學來運貨的年輕人。");
    expect(wrapper.get('[data-testid="creation-affinity-fire"]').element.checked).toBe(true);
    expect(wrapper.get('[data-testid="creation-affinity-wind"]').element.checked).toBe(true);
    // The budget briefing states the human budget and the six-axis spans.
    expect(wrapper.get('[data-testid="creation-budget-briefing"]').text()).toContain("24");
    expect(lastAction(wrapper, "creation.custom")).toBeNull(); // not auto-emitted on resume
  });

  it("resumes a concept draft: pre-filled concept, background preview with the generated indicator", () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_CONCEPT_DRAFT_SAMPLE } });
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("concept");
    expect(wrapper.get('[data-testid="creation-field-concept"]').element.value).toBe("燈下讀書的年輕學者。");
    const preview = wrapper.get('[data-testid="creation-background"]');
    expect(preview.attributes("data-background-generated")).toBe("true");
    expect(preview.text()).toBe("燈下讀書的年輕學者。");
  });

  // -- Unavailable -----------------------------------------------------------
  it("renders only the registry-owned reason for the unavailable panel", () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_UNAVAILABLE_SAMPLE } });
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-available")).toBe("false");
    expect(wrapper.get('[data-testid="creation-unavailable-reason"]').text()).toBe("角色創建目前無法顯示");
    // No wizard surfaces render in the unavailable form.
    expect(wrapper.find('[data-testid="creation-preset-card"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="creation-field-age"]').exists()).toBe(false);
  });

  // -- Frame: close + open prop ---------------------------------------------
  // -- Subrace-required gate ---------------------------------------------------
  it("a subrace-bearing race without a subrace cannot confirm (field error, no creation.custom)", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-age"]').setValue(21);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(21);
    // Pick the subrace-bearing race (beastfolk advertises subraces).
    wrapper.get('[data-testid="creation-race"]').setValue("beastfolk");
    await nextTick();
    // No subrace selected: the subrace field is shown (hasSubraces) but empty,
    // and no strict (race, subrace) profile match exists, so the allocation
    // inputs are not rendered.
    expect(wrapper.find('[data-testid="creation-subrace"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="creation-field-hp"]').exists()).toBe(false);
    // Confirming surfaces the subrace-required field error and emits no envelope.
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    await nextTick();
    expect(wrapper.get('[data-testid="creation-form-message"]').exists()).toBe(true);
    expect(lastAction(wrapper, "creation.custom")).toBeNull();
    // Selecting the subrace exposes the allocation inputs; the total must equal
    // the beastfolk/wolf profile budget (26) or confirm stays blocked.
    wrapper.get('[data-testid="creation-subrace"]').setValue("subrace_wolf");
    await nextTick();
    expect(wrapper.find('[data-testid="creation-field-hp"]').exists()).toBe(true);
    setAllocations(wrapper, { hp: 9, mp: 4, sp: 4, atk_phys: 3, agility: 3, defense: 3 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    const ev = lastAction(wrapper, "creation.custom");
    expect(ev).not.toBeNull();
    expect(ev.payload.race).toBe("beastfolk");
    expect(ev.payload.subrace).toBe("subrace_wolf");
  });

  // -- Snapshot (draft) re-sync ------------------------------------------------
  it("a later creation snapshot carrying a draft re-syncs the wizard at the saved stage", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    // A new snapshot arrives carrying the server-persisted custom draft:
    // the wizard must re-sync its mode and pre-fill the fields (reconnect
    // resume contract, webclient-character-creation-ui).
    wrapper.setProps({ creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("custom");
    expect(wrapper.get('[data-testid="creation-field-displayName"]').element.value).toBe("林楓");
    expect(wrapper.get('[data-testid="creation-field-hp"]').element.value).toBe("8");
    expect(wrapper.get('[data-testid="creation-background"]').element.value).toBe("從渡口學來運貨的年輕人。");
  });

  it("the confirm stage mirrors the dock stage into the wizard mode", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    // The store-driven dock stage (custom form open) syncs the wizard mode.
    wrapper.setProps({
      stage: { stage: "custom", confirmItems: [], confirmLabel: null, confirmAction: null, pendingPresetKey: null },
    });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("custom");
    // Returning to the preset stage restores the preset cards.
    wrapper.setProps({
      stage: { stage: "presets", confirmItems: [], confirmLabel: null, confirmAction: null, pendingPresetKey: null },
    });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("preset");
  });

  it("the close button emits close", () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    wrapper.get('[data-testid="creation-overlay-close"]').trigger("click");
    expect(wrapper.emitted("close")).toBeTruthy();
    expect(wrapper.emitted("close").length).toBe(1);
  });

  it("open=false hides the overlay", () => {
    const wrapper = mount(CreationOverlay, {
      props: { creation: CREATION_PANEL_SAMPLE, open: false },
    });
    expect(wrapper.find('[data-testid="creation-overlay"]').exists()).toBe(false);
  });
});
