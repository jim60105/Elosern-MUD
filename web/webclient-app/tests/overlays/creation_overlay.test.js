import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../../AppClient.vue";
import CreationOverlay from "../../components/CreationOverlay.vue";
import { useElosernStore } from "../../stores/elosern.js";
import {
  CREATION_PANEL_SAMPLE,
  CREATION_PANEL_PRESET_DRAFT_SAMPLE,
  CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
  CREATION_PANEL_PROPOSAL_SAMPLE,
  CREATION_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";
import * as fx from "../store/protocol_fixtures.js";

// Payload values referenced from the committed creation sample instead of
// restating shipped identifiers in this test's source
// (test-data-independence): the wizard drives whatever descriptors the server
// authored into the panel.
const SAMPLE_PRESET_KEY = CREATION_PANEL_SAMPLE.presets[0].key;
const SUBRACED_RACE_KEY = CREATION_PANEL_SAMPLE.custom.races.find((race) => (race.subraces ?? []).length > 0).key;
const SUBRACED_SUBRACE_KEY = SUBRACED_RACE_KEY ? CREATION_PANEL_SAMPLE.custom.races.find((race) => race.key === SUBRACED_RACE_KEY).subraces[0] : null;

// CreationOverlay (B5 overlays family): the character-creation wizard over
// the committed `creation` v5 panel — preset pick, custom form with the
// age bounds gate on BOTH age fields (design D1), the transient concept proposal
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
  it("steps only valid allocations within the advertised bounds and preserves invalid direct entry", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE } });
    const axis = CREATION_PANEL_SAMPLE.custom.profiles[0].axes[0];
    const input = wrapper.get(`[data-testid="creation-field-${axis.axis}"]`);
    const up = wrapper.get(`[data-testid="creation-step-${axis.axis}-up"]`);
    const down = wrapper.get(`[data-testid="creation-step-${axis.axis}-down"]`);
    await input.setValue(axis.minimum);
    expect(down.attributes("disabled")).toBeDefined();
    await up.trigger("click");
    expect(input.element.value).toBe(String(axis.minimum + 1));
    await input.setValue(axis.maximum);
    expect(up.attributes("disabled")).toBeDefined();
    await down.trigger("click");
    expect(input.element.value).toBe(String(axis.maximum - 1));
    for (const invalid of ["", axis.minimum - 1, axis.maximum + 1, 0.5]) {
      await input.setValue(invalid);
      expect(up.attributes("disabled")).toBeDefined();
      expect(down.attributes("disabled")).toBeDefined();
      await up.trigger("click");
      expect(input.element.value).toBe(String(invalid));
      await wrapper.get('[data-testid="creation-submit"]').trigger("click");
      expect(lastAction(wrapper, "creation.custom")).toBeNull();
      expect(wrapper.get('[data-testid="creation-form-message"]').attributes("role")).toBe("alert");
    }
    // Preview clipping cannot normalize a submitted value: an over-bound axis
    // with a balancing decrement still reaches the existing server validator.
    await input.setValue(axis.maximum + 1);
    const other = CREATION_PANEL_SAMPLE.custom.profiles[0].axes[1];
    await wrapper.get(`[data-testid="creation-field-${other.axis}"]`).setValue(
      CREATION_PANEL_CUSTOM_DRAFT_SAMPLE.draft.allocations[other.axis] - 1,
    );
    await wrapper.get('[data-testid="creation-submit"]').trigger("click");
    expect(lastAction(wrapper, "creation.custom").payload.allocations[axis.axis]).toBe(axis.maximum + 1);
    wrapper.unmount();
  });

  // -- Custom state + age bounds gate ---------------------------------------
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

  it("the custom payload carries the nine required keys when the default sex stands (blank background and no affinity emit JSON-safe defaults)", async () => {
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

  it("an explicit non-default sex ships as the optional tenth payload key", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-displayName"]').setValue("無名者");
    wrapper.get('[data-testid="creation-field-age"]').setValue(21);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(21);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
    wrapper.get('[data-testid="creation-sex"]').setValue("female");
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    const event = lastAction(wrapper, "creation.custom");
    expect(Object.keys(event.payload).sort()).toEqual([
      "affinity_elements",
      "age",
      "allocations",
      "apparent_age",
      "background",
      "display_name",
      "persona",
      "race",
      "sex",
      "subrace",
    ]);
    expect(event.payload.sex).toBe("female");
  });

  it("the age bounds gate rejects a negative age (gate error, no creation.custom)", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-age"]').setValue(-1);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(21);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    await nextTick();
    expect(wrapper.get('[data-testid="creation-form-message"]').exists()).toBe(true);
    expect(lastAction(wrapper, "creation.custom")).toBeNull();
  });

  it("the age bounds gate rejects a negative apparent_age (gate error, no creation.custom)", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-age"]').setValue(21);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(-1);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    await nextTick();
    expect(wrapper.get('[data-testid="creation-form-message"]').exists()).toBe(true);
    expect(lastAction(wrapper, "creation.custom")).toBeNull();
  });

  it("both ages at the 0 bound pass the gate and emit creation.custom end-to-end", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-age"]').setValue(0);
    wrapper.get('[data-testid="creation-field-apparentAge"]').setValue(0);
    setAllocations(wrapper, { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    const event = lastAction(wrapper, "creation.custom");
    expect(event).not.toBeNull();
    expect(event.payload.age).toBe(0);
    expect(event.payload.apparent_age).toBe(0);
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
          pendingPresetKey: SAMPLE_PRESET_KEY,
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
          pendingPresetKey: SAMPLE_PRESET_KEY,
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
  it("resumes a preset draft with the saved preset marked and expanded", () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_PRESET_DRAFT_SAMPLE } });
    expect(wrapper.get('[data-testid="creation-overlay"]').attributes("data-mode")).toBe("preset");
    const cards = wrapper.findAll('[data-testid="creation-preset-card"]');
    const selected = cards.filter((card) => card.attributes("data-selected") === "true");
    expect(selected.length).toBe(1);
    expect(selected[0].attributes("data-preset-key")).toBe(CREATION_PANEL_PRESET_DRAFT_SAMPLE.draft.preset_key);
    expect(selected[0].attributes("data-expanded")).toBe("true");
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
    // The saved concrete sex member restores into the select.
    expect(wrapper.get('[data-testid="creation-sex"]').element.value).toBe("male");
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
    wrapper.get('[data-testid="creation-race"]').setValue(SUBRACED_RACE_KEY);
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
    wrapper.get('[data-testid="creation-subrace"]').setValue(SUBRACED_SUBRACE_KEY);
    await nextTick();
    expect(wrapper.find('[data-testid="creation-field-hp"]').exists()).toBe(true);
    setAllocations(wrapper, { hp: 9, mp: 4, sp: 4, atk_phys: 3, agility: 3, defense: 3, magic_power: 4 });
    wrapper.get('[data-testid="creation-submit"]').trigger("click");
    const ev = lastAction(wrapper, "creation.custom");
    expect(ev).not.toBeNull();
    expect(ev.payload.race).toBe(SUBRACED_RACE_KEY);
    expect(ev.payload.subrace).toBe(SUBRACED_SUBRACE_KEY);
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

  it("open=false hides the overlay", () => {
    const wrapper = mount(CreationOverlay, {
      props: { creation: CREATION_PANEL_SAMPLE, open: false },
    });
    expect(wrapper.find('[data-testid="creation-overlay"]').exists()).toBe(false);
  });

  // -- Sex select + name roll (namegen-creation-ui D6) -----------------------
  it("the sex select renders the server descriptor verbatim with the default preselected", async () => {
    const wrapper = mount(CreationOverlay, { props: { creation: CREATION_PANEL_SAMPLE } });
    await switchToCustom(wrapper);
    const select = wrapper.get('[data-testid="creation-sex"]');
    expect(select.findAll("option").map((option) => [option.attributes("value"), option.text()])).toEqual([
      ["female", "女性"],
      ["male", "男性"],
      ["other", "其他"],
    ]);
    expect(select.element.value).toBe("other");
  });

  it("the fresh-form roll dispatches the displayed selection through the admitted gate", async () => {
    const dispatchState = { inFlight: null, submittedRequestId: null };
    const dispatch = vi.fn((intent) => {
      if (dispatchState.inFlight !== null) return null;
      dispatchState.inFlight = "r-1";
      dispatchState.submittedRequestId = "r-1";
      return "r-1";
    });
    const wrapper = mount(CreationOverlay, {
      props: { creation: CREATION_PANEL_SAMPLE, dispatch, dispatchState },
    });
    await switchToCustom(wrapper);
    await wrapper.get('[data-testid="creation-roll-name"]').trigger("click");
    expect(dispatch).toHaveBeenCalledTimes(1);
    expect(dispatch).toHaveBeenCalledWith({
      action_id: "creation.roll_name",
      payload: { race: "human", subrace: null, sex: "other" },
    });
    // In flight: the button is disabled (own pending state) and a second
    // click dispatches nothing; the shared gate (released via new props
    // identity) also keeps it disabled.
    expect(wrapper.get('[data-testid="creation-roll-name"]').attributes("disabled")).toBeDefined();
    await wrapper.setProps({ dispatchState: { ...dispatchState } });
    await wrapper.get('[data-testid="creation-roll-name"]').trigger("click");
    expect(dispatch).toHaveBeenCalledTimes(1);
  });

  it("a matched success result backfills the name field exactly once", async () => {
    const dispatchState = { inFlight: null, submittedRequestId: null };
    const wrapper = mount(CreationOverlay, {
      props: {
        creation: CREATION_PANEL_SAMPLE,
        dispatch: () => {
          dispatchState.inFlight = "r-7";
          dispatchState.submittedRequestId = "r-7";
          return "r-7";
        },
        dispatchState,
      },
    });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-displayName"]').setValue("自己打的");
    await wrapper.get('[data-testid="creation-roll-name"]').trigger("click");
    await wrapper.setProps({
      result: {
        requestId: "r-7",
        epoch: "a".repeat(22),
        outcome: "success",
        code: "name_rolled",
        message: "已擲出一個候選名字。",
        presentationRevision: 1,
        data: { display_name: "加斯帕‧斯諾" },
      },
    });
    expect(wrapper.get('[data-testid="creation-field-displayName"]').element.value).toBe(
      "加斯帕‧斯諾",
    );
    // A replayed identical result never re-backfills over later edits: the
    // in-flight flag already settled, and a foreign id would not match.
    wrapper.get('[data-testid="creation-field-displayName"]').setValue("玩家覆寫");
    await wrapper.setProps({
      result: {
        requestId: "r-OTHER",
        epoch: "a".repeat(22),
        outcome: "success",
        code: "name_rolled",
        message: "別人的結果",
        presentationRevision: 2,
        data: { display_name: "不該回填" },
      },
    });
    expect(wrapper.get('[data-testid="creation-field-displayName"]').element.value).toBe("玩家覆寫");
  });

  it("a foreign or non-success roll result settles without touching the name", async () => {
    const dispatchState = { inFlight: null, submittedRequestId: null };
    const wrapper = mount(CreationOverlay, {
      props: {
        creation: CREATION_PANEL_SAMPLE,
        dispatch: () => {
          dispatchState.inFlight = "r-7";
          dispatchState.submittedRequestId = "r-7";
          return "r-7";
        },
        dispatchState,
      },
    });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-field-displayName"]').setValue("不動名");
    await wrapper.get('[data-testid="creation-roll-name"]').trigger("click");
    await wrapper.setProps({
      result: {
        requestId: "r-OTHER",
        epoch: "a".repeat(22),
        outcome: "success",
        code: "name_rolled",
        message: "別人在擲名",
        presentationRevision: 1,
        data: { display_name: "不該出現" },
      },
    });
    expect(wrapper.get('[data-testid="creation-field-displayName"]').element.value).toBe("不動名");
    await wrapper.setProps({
      result: {
        requestId: "r-7",
        epoch: "a".repeat(22),
        outcome: "rejected",
        code: "unknown_race",
        message: "找不到這個種族。",
        presentationRevision: 1,
      },
    });
    expect(wrapper.get('[data-testid="creation-field-displayName"]').element.value).toBe("不動名");
    // Settled: the store releases the shared gate and the button re-enables.
    await wrapper.setProps({ dispatchState: { inFlight: null, submittedRequestId: "r-7" } });
    expect(wrapper.get('[data-testid="creation-roll-name"]').attributes("disabled")).toBeUndefined();
  });

  it("the roll sends the displayed non-default sex", async () => {
    const dispatch = vi.fn(() => "r-2");
    const wrapper = mount(CreationOverlay, {
      props: {
        creation: CREATION_PANEL_SAMPLE,
        dispatch,
        dispatchState: { inFlight: null, submittedRequestId: null },
      },
    });
    await switchToCustom(wrapper);
    wrapper.get('[data-testid="creation-sex"]').setValue("male");
    wrapper.get('[data-testid="creation-race"]').setValue("elf");
    wrapper.get('[data-testid="creation-roll-name"]').trigger("click");
    expect(dispatch).toHaveBeenCalledWith({
      action_id: "creation.roll_name",
      payload: { race: "elf", subrace: null, sex: "male" },
    });
  });
});

describe("name roll tab pinning real-store integration (fix-creation-roll-tab-pinning)", () => {
  let store;
  let sender;
  let host;
  let appWrapper;
  let revision;

  function openCreation() {
    store.beginTransport(1);
    store.setConnected(true);
    revision = 2;
    expect(
      store.receive(
        1,
        "ui_snapshot",
        [fx.snapshot({ mode: "creation", revision, panels: { creation: { ...CREATION_PANEL_SAMPLE } } })],
        {},
      ).accepted,
    ).toBe(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    revision = 2;
  });

  afterEach(() => {
    appWrapper?.unmount();
    document.body.innerHTML = "";
    host = null;
    appWrapper = null;
    store.$dispose();
  });

  it("custom tab stays pinned through synchronous roll dispatch, settlement, and unchanged-stage publish", async () => {
    openCreation();
    host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    appWrapper = mount(AppClient, { attachTo: host });
    await appWrapper.vm.$nextTick();

    const overlayEl = host.querySelector('[data-testid="creation-overlay"]');
    expect(overlayEl).not.toBeNull();
    expect(overlayEl.getAttribute("data-mode")).toBe("preset");

    // Pointer-click the custom tab without touching any form input.
    await appWrapper.find('[data-testid="creation-mode-custom"]').trigger("click");
    expect(overlayEl.getAttribute("data-mode")).toBe("custom");

    // Click the name roll button.
    await appWrapper.find('[data-testid="creation-roll-name"]').trigger("click");

    // 1. Exactly one creation.roll_name dispatch, button disabled, data-mode stays custom.
    expect(sender.sent.actions).toHaveLength(1);
    const dispatchedAction = sender.sent.actions[0];
    expect(dispatchedAction.action_id).toBe("creation.roll_name");
    const rollButton = host.querySelector('[data-testid="creation-roll-name"]');
    expect(rollButton.hasAttribute("disabled")).toBe(true);
    expect(overlayEl.getAttribute("data-mode")).toBe("custom");

    // 2. Deliver matching-request success action result with data.display_name.
    const submittedRequestId = dispatchedAction.request_id;
    expect(
      store.receive(
        1,
        "ui_action_result",
        [fx.actionResult({ request_id: submittedRequestId, outcome: "success", code: "name_rolled", data: { display_name: "加斯帕‧斯諾" } })],
        {},
      ).accepted,
    ).toBe(true);
    await appWrapper.vm.$nextTick();

    // Backfill landed, button re-enabled, data-mode remains custom.
    const nameInput = host.querySelector('[data-testid="creation-field-displayName"]');
    expect(nameInput.value).toBe("加斯帕‧斯諾");
    expect(rollButton.hasAttribute("disabled")).toBe(false);
    expect(overlayEl.getAttribute("data-mode")).toBe("custom");

    // 3. Additional unchanged-stage publish (fresh object identity).
    revision += 1;
    expect(store.receive(1, "ui_update", [fx.update({ mode: "creation", revision, panels: { creation: { ...CREATION_PANEL_SAMPLE } } })], {}).accepted).toBe(true);
    await appWrapper.vm.$nextTick();
    expect(overlayEl.getAttribute("data-mode")).toBe("custom");

      // 4. Genuine stage change resumes mirroring.
      store.view.creationView = { stage: "presets", confirmItems: [], confirmLabel: null, confirmAction: null, pendingPresetKey: null };
    await appWrapper.vm.$nextTick();
      expect(overlayEl.getAttribute("data-mode")).toBe("preset");
  });
});

// -- Preset card wall (creation-preset-card-wall) ---------------------------
// Synthetic cards only: the wall renders whatever the panel supplies, so the
// keys, names and count below are invented and never a shipped roster.
const WALL_CARDS = ["t_wall_ash", "t_wall_birch", "t_wall_cedar", "t_wall_dune"].map((key, index) => ({
  key,
  display_name: `測試卡${index + 1}`,
  race: CREATION_PANEL_SAMPLE.custom.races[0].key,
  race_description: "測試種族描述。",
  subrace: null,
  emphasis: "測試專長",
  background: "測試來歷。",
  artwork: { ...structuredClone(CREATION_PANEL_SAMPLE.presets[0].artwork), subject_id: `creation:preset:${key}` },
}));
const wallPanel = (overrides = {}) => ({ ...CREATION_PANEL_SAMPLE, presets: WALL_CARDS, draft: null, ...overrides });

function keydown(target, key, init = {}) {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...init });
  target.dispatchEvent(event);
  return event;
}

function expandedKeyOf(root) {
  const open = root.querySelectorAll('[data-testid="creation-preset-card"][data-expanded="true"]');
  expect(open.length).toBe(1);
  return open[0].getAttribute("data-preset-key");
}

describe("CreationPresetWall: local browsing until deliberate selection", () => {
  let wrapper;
  let bubbled;
  const onBubble = (event) => bubbled.push(event.key);

  function mountWall(props = {}) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(CreationOverlay, { props: { creation: wallPanel(), ...props }, attachTo: host });
    return wrapper;
  }
  const wall = () => wrapper.get('[data-testid="creation-preset-wall"]').element;
  const expanded = () => wall().querySelector('[data-expanded="true"]');
  const actions = () => (wrapper.emitted("action") ?? []).map(([intent]) => intent);

  beforeEach(() => {
    bubbled = [];
    // Stands in for the bubble-phase keyboard bridge: a consumed wall key
    // must never reach it.
    document.addEventListener("keydown", onBubble);
  });
  afterEach(() => {
    document.removeEventListener("keydown", onBubble);
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders every supplied card, opens the first on entry and focuses it", async () => {
    mountWall();
    await nextTick();
    const cards = wall().querySelectorAll('[data-testid="creation-preset-card"]');
    expect([...cards].map((card) => card.getAttribute("data-preset-key"))).toEqual(WALL_CARDS.map((c) => c.key));
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[0].key);
    expect(expanded().getAttribute("aria-current")).toBe("true");
    expect(document.activeElement).toBe(expanded());
    // Collapsed cards are named native opening buttons; the expanded card's
    // primary button is never nested inside an opening button.
    const openers = wall().querySelectorAll('[data-testid="creation-preset-open"]');
    expect(openers.length).toBe(WALL_CARDS.length - 1);
    openers.forEach((button) => {
      expect(button.tagName).toBe("BUTTON");
      expect(button.getAttribute("aria-label")).toBeTruthy();
    });
    expect(wall().querySelector('[data-testid="creation-preset-choose"]').closest('[data-testid="creation-preset-open"]')).toBeNull();
  });

  it("restores a surviving draft card on entry, and falls back to the first card", () => {
    mountWall({ creation: wallPanel({ draft: { mode: "preset", stage: "preset_selected", preset_key: WALL_CARDS[2].key } }) });
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[2].key);
    wrapper.unmount();
    mountWall({ creation: wallPanel({ draft: { mode: "preset", stage: "preset_selected", preset_key: "t_wall_gone" } }) });
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[0].key);
  });

  it("keeps a surviving local browse on republication and replaces a vanished one", async () => {
    mountWall();
    keydown(expanded(), "3");
    await nextTick();
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[2].key);
    await wrapper.setProps({ creation: wallPanel({ presets: WALL_CARDS.map((card) => ({ ...card })) }) });
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[2].key);
    await wrapper.setProps({ creation: wallPanel({ presets: WALL_CARDS.filter((card) => card.key !== WALL_CARDS[2].key) }) });
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[0].key);
    expect(actions()).toEqual([]);
  });

  it("pointer opening only moves the expansion and sends nothing", async () => {
    mountWall();
    const opener = wall().querySelector(`[data-preset-key="${WALL_CARDS[1].key}"] [data-testid="creation-preset-open"]`);
    opener.focus();
    opener.click();
    await nextTick();
    await nextTick();
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[1].key);
    // Focus follows the card that had it, instead of dropping to the body.
    expect(document.activeElement).toBe(expanded());
    expect(actions()).toEqual([]);
  });

  it("horizontal arrows move the expansion, clamp at the ends and never reach the bridge", async () => {
    mountWall();
    const left = keydown(expanded(), "ArrowLeft");
    expect(left.defaultPrevented).toBe(true);
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[0].key);
    for (let i = 0; i < WALL_CARDS.length + 2; i++) {
      keydown(document.activeElement, "ArrowRight");
      await nextTick();
    }
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[WALL_CARDS.length - 1].key);
    expect(document.activeElement).toBe(expanded());
    expect(bubbled).toEqual([]);
    expect(actions()).toEqual([]);
  });

  it("a digit opens the supplied ordinal; a missing ordinal is inert", async () => {
    mountWall();
    keydown(expanded(), "2");
    await nextTick();
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[1].key);
    const missing = keydown(document.activeElement, String(WALL_CARDS.length + 1));
    await nextTick();
    expect(missing.defaultPrevented).toBe(true);
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[1].key);
    expect(bubbled).toEqual([]);
    expect(actions()).toEqual([]);
  });

  it("ignores repeated, modified and composing keys and leaves them unclaimed", () => {
    mountWall();
    const ignored = [
      ["2", { repeat: true }],
      ["2", { ctrlKey: true }],
      ["2", { shiftKey: true }],
      ["2", { altKey: true }],
      ["ArrowRight", { metaKey: true }],
      ["2", { isComposing: true }],
      ["Enter", { isComposing: true }],
    ];
    for (const [key, init] of ignored) {
      expect(keydown(expanded(), key, init).defaultPrevented).toBe(false);
    }
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[0].key);
    expect(actions()).toEqual([]);
  });

  it("leaves text entry and Escape to their owners", () => {
    mountWall();
    const field = document.createElement("input");
    wall().appendChild(field);
    expect(keydown(field, "3").defaultPrevented).toBe(false);
    expect(keydown(field, "ArrowRight").defaultPrevented).toBe(false);
    expect(keydown(field, "Enter").defaultPrevented).toBe(false);
    expect(keydown(expanded(), "Escape").defaultPrevented).toBe(false);
    expect(bubbled).toContain("Escape");
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[0].key);
    expect(actions()).toEqual([]);
  });

  it("Enter on the expanded card chooses it exactly once through the preset save", async () => {
    mountWall();
    keydown(expanded(), "3");
    await nextTick();
    const enter = keydown(document.activeElement, "Enter");
    expect(enter.defaultPrevented).toBe(true);
    expect(actions()).toEqual([{ action_id: "creation.preset", payload: { preset_key: WALL_CARDS[2].key } }]);
    expect(bubbled).toEqual([]);
  });

  it("the primary button chooses once; Enter on wall buttons stays native and a held Enter is swallowed", async () => {
    mountWall();
    const choose = wall().querySelector('[data-testid="creation-preset-choose"]');
    // The wall leaves Enter on its own buttons to the native click.
    expect(keydown(choose, "Enter").defaultPrevented).toBe(false);
    const opener = wall().querySelector('[data-testid="creation-preset-open"]');
    expect(keydown(opener, "Enter").defaultPrevented).toBe(false);
    expect(keydown(choose, "Enter", { repeat: true }).defaultPrevented).toBe(true);
    expect(actions()).toEqual([]);
    choose.click();
    expect(actions()).toEqual([{ action_id: "creation.preset", payload: { preset_key: WALL_CARDS[0].key } }]);
  });

  it("holds the choose while a mutation is in flight, browsing stays live", async () => {
    mountWall({ dispatchState: { inFlight: { requestId: "session:9" }, submittedRequestId: "session:9" } });
    expect(wall().querySelector('[data-testid="creation-preset-choose"]').disabled).toBe(true);
    keydown(expanded(), "2");
    await nextTick();
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[1].key);
    keydown(document.activeElement, "Enter");
    expect(actions()).toEqual([]);
  });

  it("routes dock-focused keys only while the dock stands on the preset frame", async () => {
    const dock = document.createElement("div");
    dock.id = "action-dock";
    dock.tabIndex = 0;
    document.body.appendChild(dock);
    mountWall({ stage: { stage: "root" } });
    dock.focus();
    // At the root frame the dock keeps its own digits and Enter: the keys
    // travel on to the bridge and the wall does not move.
    keydown(dock, "2");
    keydown(dock, "Enter");
    expect(bubbled).toEqual(["2", "Enter"]);
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[0].key);
    await wrapper.setProps({ stage: { stage: "presets" } });
    bubbled = [];
    expect(keydown(dock, "ArrowRight").defaultPrevented).toBe(true);
    await nextTick();
    expect(keydown(dock, "4").defaultPrevented).toBe(true);
    await nextTick();
    expect(expandedKeyOf(wall())).toBe(WALL_CARDS[3].key);
    // A dock-driven change never takes the dock's focus.
    expect(document.activeElement).toBe(dock);
    expect(actions()).toEqual([]);
    keydown(dock, "Enter");
    expect(actions()).toEqual([{ action_id: "creation.preset", payload: { preset_key: WALL_CARDS[3].key } }]);
    expect(bubbled).toEqual([]);
  });

  it("removes its document listener when the wall unmounts", async () => {
    mountWall();
    const removed = vi.spyOn(document, "removeEventListener");
    await wrapper.get('[data-testid="creation-mode-custom"]').trigger("click");
    expect(removed.mock.calls.some(([type, , capture]) => type === "keydown" && capture === true)).toBe(true);
    removed.mockRestore();
  });
});

describe("CreationPresetWall real-store integration (creation-preset-card-wall)", () => {
  let store;
  let sender;
  let appWrapper;

  function openCreation(panel) {
    store.beginTransport(1);
    store.setConnected(true);
    expect(
      store.receive(1, "ui_snapshot", [fx.snapshot({ mode: "creation", revision: 2, panels: { creation: panel } })], {}).accepted,
    ).toBe(true);
  }

  async function mountApp() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    appWrapper = mount(AppClient, { attachTo: host });
    await nextTick();
    return host;
  }

  const echoes = () => store.narrative.filter((line) => line.kind === "in").length;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });
  afterEach(() => {
    appWrapper?.unmount();
    appWrapper = null;
    document.body.innerHTML = "";
    store.$dispose();
  });

  it("wall- and dock-focused browsing sends nothing; Enter saves once and confirmation follows its success", async () => {
    openCreation(wallPanel());
    const host = await mountApp();
    const wallEl = host.querySelector('[data-testid="creation-preset-wall"]');
    const echoBefore = echoes();
    // Wall-focused browsing.
    keydown(document.activeElement, "ArrowRight");
    await nextTick();
    keydown(document.activeElement, "3");
    await nextTick();
    expect(expandedKeyOf(wallEl)).toBe(WALL_CARDS[2].key);
    // Dock-focused browsing on the preset frame.
    expect(store.focusItemByKey("presets")).toBe(true);
    store.focusConfirm("pointer");
    await nextTick();
    expect(store.view.creationView.stage).toBe("presets");
    const dock = host.querySelector("#action-dock");
    dock.focus();
    keydown(dock, "2");
    keydown(dock, "ArrowRight");
    keydown(dock, "ArrowLeft");
    await nextTick();
    expect(expandedKeyOf(wallEl)).toBe(WALL_CARDS[1].key);
    expect(sender.sent.actions).toEqual([]);
    expect(echoes()).toBe(echoBefore);

    keydown(dock, "Enter");
    await nextTick();
    expect(sender.sent.actions.map((a) => [a.action_id, a.payload])).toEqual([
      ["creation.preset", { preset_key: WALL_CARDS[1].key }],
    ]);
    expect(store.view.creationView.stage).toBe("presets");
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: sender.sent.actions[0].request_id })], {});
    await nextTick();
    expect(store.view.creationView.stage).toBe("confirm");
    expect(store.view.creationView.pendingPresetKey).toBe(WALL_CARDS[1].key);
    expect(host.querySelector('[data-testid="creation-confirm"]')).not.toBeNull();
  });

  it("a rejected preset save opens no confirmation", async () => {
    openCreation(wallPanel());
    const host = await mountApp();
    keydown(document.activeElement, "Enter");
    await nextTick();
    expect(sender.sent.actions).toHaveLength(1);
    store.receive(
      1,
      "ui_action_result",
      [fx.actionResult({ request_id: sender.sent.actions[0].request_id, outcome: "rejected", code: "unknown_preset", message: "找不到。" })],
      {},
    );
    await nextTick();
    expect(store.view.creationView.stage).not.toBe("confirm");
    expect(host.querySelector('[data-testid="creation-confirm"]')).toBeNull();
    expect(host.querySelector('[data-testid="creation-preset-wall"]')).not.toBeNull();
  });
});
