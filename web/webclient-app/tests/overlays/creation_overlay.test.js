import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import CreationOverlay from "../../components/CreationOverlay.vue";
import {
  CREATION_PANEL_SAMPLE,
  CREATION_PANEL_PRESET_DRAFT_SAMPLE,
  CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
  CREATION_PANEL_PROPOSAL_SAMPLE,
  CREATION_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

// CreationOverlay (B5 overlays family): the character-creation wizard over
// the committed `creation` v2 panel — preset pick, custom form with the
// adult gate on BOTH age fields (design D1), the transient concept proposal
// fill (retool-concept-transient-fill), and the server-persisted draft
// resume. Every assertion checks the exact `creation.*` envelopes (no
// invented fields) and the registry-owned unavailable reason; the server
// remains authoritative.

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
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
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
        allocations: { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 },
        background: "測試背景。",
        affinity_elements: ["fire", "wind"],
        persona: null,
      },
    });
  });

  it("the custom payload always carries the exact nine keys (blank background and no affinity emit JSON-safe defaults)", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-displayName"]').setValue("無名者");
    wrapper.get('[data-testid="creation-field-age"]').setValue(21);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(21);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    const event = lastAction(wrapper, "creation.custom");
    expect(event).not.toBeNull();
    expect(Object.keys(event.payload).sort()).toEqual([
      "affinity_elements",
      "age",
      "allocations",
      "apparent_age",
      "background",
      "display_name",
      "persona",
      "race",
      "subrace",
    ]);
    expect(event.payload.background).toBeNull();
    expect(event.payload.affinity_elements).toEqual([]);
    expect(event.payload.persona).toBeNull();
  });

  it("the adult gate rejects age below 18 (gate error, no creation.custom)", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-age"]').setValue(17);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(21);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
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
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
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
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
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

  // -- Transient proposal fill (retool-concept-transient-fill) --------------
  it("a proposal fills the form silently without submitting anything (banner retired)", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_PROPOSAL_SAMPLE } });
    // retool-concept-fill-navigation retired the in-form notice and its
    // 開啟表單 button: the fill lands immediately and the tab stays where
    // the player left it (no navigation, no confirmation outside a pending
    // apply). Opening the custom tab is a plain tab click.
    expect(wrapper.find('[data-testid="creation-proposal-notice"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("preset");
    wrapper.get('[data-testid="creation-mode-custom"]').trigger("click");
    await nextTick();
    expect(wrapper.get('[data-testid="creation-field-hp"]').element.value).toBe("6");
    expect(wrapper.get('[data-testid="creation-field-mp"]').element.value).toBe("6");
    expect(wrapper.get('[data-testid="creation-persona-personality"]').element.value).toBe("沉穩內斂");
    expect(wrapper.get('[data-testid="creation-persona-life_story"]').element.value).toBe("燈下研讀古籍的年輕學者。");
    expect(wrapper.get('[data-testid="creation-persona-habit"]').element.value).toBe("睡前必整理書架。");
    // Nothing auto-submits.
    expect(lastAction(wrapper, "creation.custom")).toBeNull();
    expect(lastAction(wrapper, "creation.concept")).toBeNull();
  });

  it("a rebuild at the same revision never overwrites player edits", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_PROPOSAL_SAMPLE } });
    wrapper.get('[data-testid="creation-mode-custom"]').trigger("click");
    await nextTick();
    wrapper.get('[data-testid="creation-persona-personality"]').setValue("我改過的個性");
    await nextTick();
    // A panel re-publish carrying the SAME revision must not touch the edit.
    wrapper.setProps({ creation: { ...CREATION_PANEL_PROPOSAL_SAMPLE } });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-persona-personality"]').element.value).toBe(
      "我改過的個性",
    );
    // A fresh revision with byte-identical content DOES replace the fields.
    wrapper.setProps({
      creation: {
        ...CREATION_PANEL_PROPOSAL_SAMPLE,
        proposal: { ...CREATION_PANEL_PROPOSAL_SAMPLE.proposal, revision: 2 },
      },
    });
    await nextTick();
    expect(wrapper.get('[data-testid="creation-persona-personality"]').element.value).toBe(
      "沉穩內斂",
    );
  });

  it("a partially-filled persona blocks submission locally with no action", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-displayName"]').setValue("半填者");
    wrapper.get('[data-testid="creation-field-age"]').setValue(21);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(21);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
    wrapper.get('[data-testid="creation-persona-personality"]').setValue("只有個性有填");
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    await nextTick();
    expect(wrapper.get('[data-testid="creation-form-message"]').text()).toContain("全部填寫或全部留空");
    expect(lastAction(wrapper, "creation.custom")).toBeNull();
    // Filling the other two unblocks and ships the trimmed block.
    wrapper.get('[data-testid="creation-persona-life_story"]').setValue("邊境小村");
    wrapper.get('[data-testid="creation-persona-habit"]').setValue("清晨練劍");
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    const event = lastAction(wrapper, "creation.custom");
    expect(event.payload.persona).toEqual({
      personality: "只有個性有填",
      life_story: "邊境小村",
      habit: "清晨練劍",
    });
  });

  it("a race-changing proposal over local persona prose shows a non-blocking review prompt", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-persona-personality"]').setValue("玩家自己打的個性");
    wrapper.get('[data-testid="creation-persona-life_story"]').setValue("玩家自己的生平");
    wrapper.get('[data-testid="creation-persona-habit"]').setValue("玩家自己的習慣");
    await nextTick();
    // A new proposal for a different race arrives while prose exists locally.
    wrapper.setProps({
      creation: { ...CREATION_PANEL_PROPOSAL_SAMPLE, proposal: { ...CREATION_PANEL_PROPOSAL_SAMPLE.proposal } },
    });
    await nextTick();
    const prompt = wrapper.get('[data-testid="creation-proposal-review"]');
    expect(prompt.text()).toContain("elf");
    // Non-blocking: the player's own text stays and the form stays submittable.
    wrapper.get('[data-testid="creation-field-displayName"]').setValue("審視後仍送出");
    wrapper.get('[data-testid="creation-field-age"]').setValue(21);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(21);
    setAllocations(wrapper, { hp: 6, mp: 6, sp: 2, atk_phys: 2, agility: 4, defense: 2, magic_power: 4 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    expect(lastAction(wrapper, "creation.custom")).not.toBeNull();
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

  // -- Server-result presentation (webclient-action-result-feedback) --------
  // While the overlay is mounted it is THE presenting surface for a
  // recognized non-success result: the message renders verbatim in one
  // always-reachable result region on every stage (the store suppresses the
  // narrative line for the same result), never the code, and a success
  // result shows nothing.
  const REJECTED = {
    requestId: "session:1",
    epoch: "a".repeat(22),
    outcome: "rejected",
    code: "name_taken",
    message: "這個名字已經有人使用了。",
    presentationRevision: 1,
  };

  it("renders a rejected result verbatim on the preset stage (message, not code)", () => {
    const wrapper = mount(CreationOverlay, {
      props: { creation: CREATION_PANEL_SAMPLE, result: REJECTED },
    });
    const region = wrapper.get('[data-testid="creation-result-message"]');
    expect(region.text()).toBe("這個名字已經有人使用了。");
    expect(region.attributes("data-outcome")).toBe("rejected");
    // The code is never the presented text.
    expect(region.text()).not.toContain("name_taken");
  });

  it("renders a stale result verbatim on the custom stage", async () => {
    const wrapper = mount(CreationOverlay, {
      props: {
        creation: CREATION_PANEL_SAMPLE,
        result: { ...REJECTED, outcome: "stale", code: "stale", message: "畫面狀態已更新，請重新操作" },
      },
    });
    await switchToCustom(wrapper);
    expect(wrapper.get('[data-testid="creation-result-message"]').text()).toBe(
      "畫面狀態已更新，請重新操作",
    );
  });

  it("renders the result region on the confirm stage too (always reachable)", () => {
    const wrapper = mount(CreationOverlay, {
      props: {
        creation: CREATION_PANEL_SAMPLE,
        result: { ...REJECTED, outcome: "error", code: "internal", message: "伺服器發生錯誤。" },
        stage: {
          stage: "confirm",
          confirmItems: [{ key: "confirm-creation.activate", label: "確認啟用？", actionId: "creation.activate" }],
          confirmLabel: "確認啟用？",
          confirmAction: "creation.activate",
          pendingPresetKey: "human_wanderer",
        },
      },
    });
    expect(wrapper.get('[data-testid="creation-confirm"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="creation-result-message"]').text()).toBe("伺服器發生錯誤。");
  });

  it("shows the stable fallback line for a message-less non-success", () => {
    const wrapper = mount(CreationOverlay, {
      props: { creation: CREATION_PANEL_SAMPLE, result: { ...REJECTED, message: "   " } },
    });
    // Byte-identical to the store's narrative fallback constant.
    expect(wrapper.get('[data-testid="creation-result-message"]').text()).toBe(
      "動作未生效，請重試或返回上層。",
    );
  });

  it("renders no result region and no form message for a successful result", () => {
    const wrapper = mount(CreationOverlay, {
      props: {
        creation: CREATION_PANEL_SAMPLE,
        result: { ...REJECTED, outcome: "success", code: "completed", message: "完成" },
      },
    });
    expect(wrapper.find('[data-testid="creation-result-message"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="creation-form-message"]').exists()).toBe(false);
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
    // The player-owned persona block resumes verbatim (v2 D3).
    expect(wrapper.get('[data-testid="creation-persona-personality"]').element.value).toBe("沉穩寡言");
    expect(wrapper.get('[data-testid="creation-persona-life_story"]').element.value).toBe(
      "在霧骨渡口搬運貨物長大的年輕人。",
    );
    expect(wrapper.get('[data-testid="creation-persona-habit"]').element.value).toBe("每天清晨沿河岸慢跑。");
    expect(wrapper.get('[data-testid="creation-affinity-fire"]').element.checked).toBe(true);
    expect(wrapper.get('[data-testid="creation-affinity-wind"]').element.checked).toBe(true);
    // The budget briefing states the human budget and the seven-axis spans.
    expect(wrapper.get('[data-testid="creation-budget-briefing"]').text()).toContain("28");
    expect(lastAction(wrapper, "creation.custom")).toBeNull(); // not auto-emitted on resume
  });

  it("the three persona textareas always render in custom mode", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    // No draft, no proposal: the block renders empty and editable (D5).
    expect(wrapper.get('[data-testid="creation-persona-personality"]').element.value).toBe("");
    expect(wrapper.get('[data-testid="creation-persona-life_story"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="creation-persona-habit"]').exists()).toBe(true);
    // The retired generated indicator never renders.
    expect(wrapper.find('[data-testid="creation-concept-indicator"]').exists()).toBe(false);
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
    // the beastfolk/wolf profile budget (30) or confirm stays blocked.
    wrapper.get('[data-testid="creation-subrace"]').setValue("subrace_wolf");
    await nextTick();
    expect(wrapper.find('[data-testid="creation-field-hp"]').exists()).toBe(true);
    setAllocations(wrapper, { hp: 9, mp: 4, sp: 4, atk_phys: 3, agility: 3, defense: 3, magic_power: 4 });
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
