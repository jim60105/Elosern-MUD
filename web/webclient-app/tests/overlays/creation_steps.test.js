import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import CreationOverlay from "../../components/CreationOverlay.vue";
import CreationPortraitSlot from "../../components/CreationPortraitSlot.vue";
import { FIELD_STEP, STEPS } from "../../composables/use-creation-steps.js";
import { CREATION_PANEL_CUSTOM_DRAFT_SAMPLE } from "../../stories/fixtures.js";

// creation-stepped-form: the custom form as three freely navigable steps over
// the existing form state. Every value below is derived from the synthetic
// story panel (its profiles, budgets, races and silhouette table), so these
// tests pin the step mechanics and never shipped data, copy or markup.
const PANEL = CREATION_PANEL_CUSTOM_DRAFT_SAMPLE;
const CUSTOM = PANEL.custom;
const DRAFT = PANEL.draft;
const DRAFT_PROFILE = CUSTOM.profiles.find((p) => p.race === DRAFT.race && (p.subrace ?? null) === (DRAFT.subrace ?? null));
const SUBRACED = CUSTOM.races.find((race) => Array.isArray(race.subraces) && race.subraces.length > 0);
const OTHER_PLAIN = CUSTOM.races.find((race) => race.key !== DRAFT.race && !race.subraces
  && CUSTOM.profiles.some((p) => p.race === race.key && p.budget !== DRAFT_PROFILE.budget));
const STEP_KEYS = STEPS.map((step) => step.key);

let wrapper = null;
afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
});

function mountDraft(panel = PANEL) {
  wrapper = mount(CreationOverlay, { props: { creation: panel }, attachTo: document.body });
  return wrapper;
}

const tid = (id) => `[data-testid="${id}"]`;
const panelOf = (key) => wrapper.get(tid(`creation-steps-panel-${key}`));
const railItem = (key) => wrapper.get(tid(`creation-steps-tab-${key}`)).element.closest("li");
const actions = (id) => (wrapper.emitted("action") ?? []).filter(([a]) => a.action_id === id);
const sum = (values) => Object.values(values).reduce((total, value) => total + value, 0);

async function openStep(key) {
  await wrapper.get(tid(`creation-steps-tab-${key}`)).trigger("click");
  await nextTick();
}

function visibleStep() {
  return STEP_KEYS.filter((key) => panelOf(key).isVisible());
}

async function submit() {
  await wrapper.get(tid("creation-submit")).trigger("click");
  await nextTick();
  await nextTick();
}

describe("CreationCustomSteps: local step navigation (creation-stepped-form)", () => {
  it("opens on the first step and moves freely, including between nonadjacent steps", async () => {
    mountDraft();
    expect(visibleStep()).toEqual([STEP_KEYS[0]]);
    await openStep(STEP_KEYS[2]);
    expect(visibleStep()).toEqual([STEP_KEYS[2]]);
    expect(wrapper.get(tid(`creation-steps-tab-${STEP_KEYS[2]}`)).attributes("aria-current")).toBe("step");
    await openStep(STEP_KEYS[0]);
    expect(visibleStep()).toEqual([STEP_KEYS[0]]);
    await wrapper.get(tid("creation-steps-next")).trigger("click");
    await nextTick();
    expect(visibleStep()).toEqual([STEP_KEYS[1]]);
    await wrapper.get(tid("creation-steps-prev")).trigger("click");
    await nextTick();
    expect(visibleStep()).toEqual([STEP_KEYS[0]]);
    expect(wrapper.get(tid("creation-steps-prev")).attributes("disabled")).toBeDefined();
    await openStep(STEP_KEYS[2]);
    expect(wrapper.find(tid("creation-steps-next")).exists()).toBe(false);
    expect(wrapper.emitted("action")).toBeUndefined();
  });

  it("previous/next moves focus into the newly shown step", async () => {
    mountDraft();
    await wrapper.get(tid("creation-steps-next")).trigger("click");
    await nextTick();
    await nextTick();
    expect(panelOf(STEP_KEYS[1]).element.contains(document.activeElement)).toBe(true);
  });

  it("keeps unsent values across step changes without sending anything", async () => {
    mountDraft();
    const axis = DRAFT_PROFILE.axes[0].axis;
    await wrapper.get(tid("creation-field-displayName")).setValue("尚未送出");
    await openStep("story");
    await wrapper.get(tid("creation-persona-habit")).setValue("未送出的習慣");
    await openStep("allocation");
    await wrapper.get(tid(`creation-field-${axis}`)).setValue(DRAFT.allocations[axis] - 1);
    await openStep("identity");
    expect(wrapper.get(tid("creation-field-displayName")).element.value).toBe("尚未送出");
    expect(wrapper.get(tid("creation-persona-habit")).element.value).toBe("未送出的習慣");
    expect(wrapper.get(tid(`creation-field-${axis}`)).element.value).toBe(String(DRAFT.allocations[axis] - 1));
    expect(wrapper.emitted("action")).toBeUndefined();
  });

  it("the footer confirmation is mounted and submits from every step", async () => {
    mountDraft();
    for (const [index, key] of STEP_KEYS.entries()) {
      await openStep(key);
      expect(wrapper.get(tid("creation-submit")).isVisible()).toBe(true);
      await submit();
      expect(actions("creation.custom")).toHaveLength(index + 1);
      expect(visibleStep()).toEqual([key]);
    }
  });

  it("every rendered field identifier belongs to the static step map, on its own step", () => {
    mountDraft();
    for (const key of STEP_KEYS) {
      for (const el of panelOf(key).findAll("[data-creation-field]")) {
        expect(FIELD_STEP[el.attributes("data-creation-field")]).toBe(key);
      }
    }
  });
});

describe("CreationCustomSteps: remaining points on the rail", () => {
  const remaining = () => wrapper.get(tid("creation-steps-remaining")).attributes("data-remaining");

  it("shows budget minus the entered sum on every step and follows edits", async () => {
    mountDraft();
    const expected = String(DRAFT_PROFILE.budget - sum(DRAFT.allocations));
    for (const key of STEP_KEYS) {
      await openStep(key);
      expect(remaining()).toBe(expected);
    }
    const axis = DRAFT_PROFILE.axes[0].axis;
    await wrapper.get(tid(`creation-field-${axis}`)).setValue(DRAFT.allocations[axis] - 2);
    await openStep("identity");
    expect(remaining()).toBe(String(DRAFT_PROFILE.budget - sum(DRAFT.allocations) + 2));
  });

  it("never clamps: an over-budget sum shows a negative remainder and the input keeps its value", async () => {
    mountDraft();
    const axis = DRAFT_PROFILE.axes[0];
    await openStep("allocation");
    await wrapper.get(tid(`creation-field-${axis.axis}`)).setValue(axis.point_cap + 5);
    const expected = DRAFT_PROFILE.budget - (sum(DRAFT.allocations) - DRAFT.allocations[axis.axis] + axis.point_cap + 5);
    expect(expected).toBeLessThan(0);
    expect(remaining()).toBe(String(expected));
    expect(wrapper.get(tid(`creation-field-${axis.axis}`)).element.value).toBe(String(axis.point_cap + 5));
  });

  it("follows the selected server profile, and shows absence without one", async () => {
    mountDraft();
    const otherProfile = CUSTOM.profiles.find((p) => p.race === OTHER_PLAIN.key);
    await wrapper.get(tid("creation-race")).setValue(OTHER_PLAIN.key);
    expect(remaining()).toBe(String(otherProfile.budget - sum(DRAFT.allocations)));
    // A subrace-bearing race with no subrace chosen resolves no profile.
    await wrapper.get(tid("creation-race")).setValue(SUBRACED.key);
    expect(remaining()).toBe("");
    expect(wrapper.find(tid("creation-allocation-total")).exists()).toBe(false);
  });
});

describe("CreationCustomSteps: errors open the first invalid field's step", () => {
  const flagged = (key) => railItem(key).getAttribute("data-state") === "error";

  it("a missing subrace opens identity and focuses the subrace select", async () => {
    mountDraft();
    await wrapper.get(tid("creation-race")).setValue(SUBRACED.key);
    await openStep("allocation");
    await submit();
    expect(actions("creation.custom")).toHaveLength(0);
    expect(visibleStep()).toEqual(["identity"]);
    const select = wrapper.get(tid("creation-subrace"));
    expect(document.activeElement).toBe(select.element);
    expect(select.attributes("aria-invalid")).toBe("true");
    expect(select.attributes("aria-describedby")).toContain("creation-form-message");
    expect(wrapper.get("#creation-form-message").attributes("role")).toBe("alert");
    expect(flagged("identity")).toBe(true);
    expect(railItem("identity").querySelector(tid("creation-steps-error"))).not.toBeNull();
  });

  it("a partial persona opens the story step at its first empty textarea", async () => {
    mountDraft();
    await openStep("story");
    await wrapper.get(tid("creation-persona-life_story")).setValue("");
    await openStep("allocation");
    await submit();
    expect(actions("creation.custom")).toHaveLength(0);
    expect(visibleStep()).toEqual(["story"]);
    expect(document.activeElement).toBe(wrapper.get(tid("creation-persona-life_story")).element);
    expect(flagged("story")).toBe(true);
    expect(flagged("identity")).toBe(false);
  });

  it("a budget mismatch opens the allocation step at its first axis", async () => {
    mountDraft();
    const first = DRAFT_PROFILE.axes[0].axis;
    await openStep("allocation");
    await wrapper.get(tid(`creation-field-${first}`)).setValue(DRAFT.allocations[first] - 1);
    await openStep("identity");
    await submit();
    expect(actions("creation.custom")).toHaveLength(0);
    expect(visibleStep()).toEqual(["allocation"]);
    expect(document.activeElement).toBe(wrapper.get(tid(`creation-field-${first}`)).element);
    expect(flagged("allocation")).toBe(true);
  });

  it("an out-of-cap value is reported and focused, and nothing ships", async () => {
    mountDraft();
    const [over, balance] = DRAFT_PROFILE.axes.filter((axis) => DRAFT.allocations[axis.axis] > axis.minimum).slice(-2);
    await openStep("allocation");
    await wrapper.get(tid(`creation-field-${over.axis}`)).setValue(over.point_cap + 1);
    const delta = over.point_cap + 1 - DRAFT.allocations[over.axis];
    await wrapper.get(tid(`creation-field-${balance.axis}`)).setValue(DRAFT.allocations[balance.axis] - delta);
    await openStep("identity");
    await submit();
    // The cap is a server-declared bound: the form refuses locally rather than
    // shipping a point value activation would reject.
    expect(actions("creation.custom")).toHaveLength(0);
    expect(visibleStep()).toEqual(["allocation"]);
    const input = wrapper.get(tid(`creation-field-${over.axis}`));
    expect(document.activeElement).toBe(input.element);
    expect(input.attributes("aria-invalid")).toBe("true");
    expect(flagged("allocation")).toBe(true);
    expect(wrapper.get("#creation-form-message").text()).toContain(`0~${over.point_cap}`);
  });

  it("opens the allocation step for an out-of-cap value even with a persona gap", async () => {
    mountDraft();
    const [over, balance] = DRAFT_PROFILE.axes.filter((axis) => DRAFT.allocations[axis.axis] > axis.minimum).slice(-2);
    await openStep("allocation");
    // The out-of-cap gate runs with the allocation gates (before the persona
    // gate), so the allocation field is the reported one: an over-cap point
    // value is never sent, whatever the rest of the form holds.
    await wrapper.get(tid(`creation-field-${over.axis}`)).setValue(over.point_cap + 1);
    const delta = over.point_cap + 1 - DRAFT.allocations[over.axis];
    await wrapper.get(tid(`creation-field-${balance.axis}`)).setValue(DRAFT.allocations[balance.axis] - delta);
    await openStep("story");
    await wrapper.get(tid("creation-persona-habit")).setValue("");
    await openStep("allocation");
    await submit();
    expect(actions("creation.custom")).toHaveLength(0);
    expect(visibleStep()).toEqual(["allocation"]);
    expect(document.activeElement).toBe(wrapper.get(tid(`creation-field-${over.axis}`)).element);
    expect(flagged("allocation")).toBe(true);
  });

  it("an age below the advertised minimum opens identity with no action", async () => {
    mountDraft();
    await openStep("story");
    await wrapper.get(tid("creation-field-age")).setValue(CUSTOM.age.age_minimum - 1);
    await submit();
    expect(actions("creation.custom")).toHaveLength(0);
    expect(visibleStep()).toEqual(["identity"]);
    expect(document.activeElement).toBe(wrapper.get(tid("creation-field-age")).element);
    expect(wrapper.get(tid("creation-field-apparentAge")).attributes("aria-invalid")).toBeUndefined();
  });

  it("editing the reported step retires its rail mark", async () => {
    mountDraft();
    await wrapper.get(tid("creation-race")).setValue(SUBRACED.key);
    await submit();
    expect(flagged("identity")).toBe(true);
    await wrapper.get(tid("creation-subrace")).setValue(SUBRACED.subraces[0]);
    expect(flagged("identity")).toBe(false);
    expect(wrapper.get(tid("creation-subrace")).attributes("aria-invalid")).toBeUndefined();
  });
});

describe("CreationCustomSteps: point ranges", () => {
  it("renders every axis point range with a tilde", async () => {
    mountDraft();
    await openStep("allocation");
    for (const axis of DRAFT_PROFILE.axes) {
      const help = wrapper.get(`#creation-axis-help-${axis.axis}`).text();
      expect(help).toContain(`0~${axis.point_cap}`);
      expect(help).not.toMatch(/0[-–]\d/);
    }
    const briefing = wrapper.get(tid("creation-budget-briefing")).text();
    expect(briefing).toContain(`0~${DRAFT_PROFILE.axes[0].point_cap}`);
    expect(briefing).not.toMatch(/0[-–]\d/);
  });
});

describe("CreationCustomSteps: allocation slider", () => {
  const field = (axis) => wrapper.get(tid(`creation-field-${axis}`));
  const slider = (axis) => wrapper.get(tid(`creation-slider-${axis}`));
  const capped = DRAFT_PROFILE.axes.find((axis) => axis.point_cap > 0);

  it("spans zero to the point cap in steps of one, after the number field", async () => {
    mountDraft();
    await openStep("allocation");
    for (const axis of DRAFT_PROFILE.axes) {
      const range = slider(axis.axis);
      expect(range.attributes("type")).toBe("range");
      expect(range.attributes("min")).toBe("0");
      expect(range.attributes("max")).toBe(String(axis.point_cap));
      expect(range.attributes("step")).toBe("1");
      const order = field(axis.axis).element.compareDocumentPosition(range.element);
      expect(order & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it("keeps the slider and the number field on the same value", async () => {
    mountDraft();
    await openStep("allocation");
    const draftValue = DRAFT.allocations[capped.axis];
    const viaSlider = draftValue === 0 ? 1 : draftValue - 1;
    await slider(capped.axis).setValue(viaSlider);
    expect(field(capped.axis).element.value).toBe(String(viaSlider));
    const viaField = viaSlider === 0 ? 1 : viaSlider - 1;
    await field(capped.axis).setValue(viaField);
    expect(slider(capped.axis).element.value).toBe(String(viaField));
  });

  it("submits the slider value as the allocation", async () => {
    mountDraft();
    await openStep("allocation");
    const lower = DRAFT_PROFILE.axes.find((axis) => DRAFT.allocations[axis.axis] > 0);
    const raise = DRAFT_PROFILE.axes.find((axis) => axis !== lower && DRAFT.allocations[axis.axis] < axis.point_cap);
    expect(sum(DRAFT.allocations)).toBe(DRAFT_PROFILE.budget);
    await slider(lower.axis).setValue(DRAFT.allocations[lower.axis] - 1);
    await slider(raise.axis).setValue(DRAFT.allocations[raise.axis] + 1);
    await submit();
    const sent = actions("creation.custom");
    expect(sent).toHaveLength(1);
    expect(sent[0][0].payload.allocations[lower.axis]).toBe(Number(slider(lower.axis).element.value));
    expect(sent[0][0].payload.allocations[raise.axis]).toBe(Number(slider(raise.axis).element.value));
    expect(sent[0][0].payload.allocations[lower.axis]).toBe(DRAFT.allocations[lower.axis] - 1);
  });

  it("never clamps the slider to the remaining budget", async () => {
    mountDraft();
    await openStep("allocation");
    const remaining = Number(wrapper.get(tid("creation-steps-remaining")).attributes("data-remaining"));
    const axis = DRAFT_PROFILE.axes.find((entry) => entry.point_cap > remaining);
    expect(axis).toBeDefined();
    expect(slider(axis.axis).attributes("max")).toBe(String(axis.point_cap));
  });

  it("follows a bound and value change made in the same render", async () => {
    const panel = structuredClone(PANEL);
    const profile = panel.custom.profiles.find((p) => p.race === OTHER_PLAIN.key);
    const target = profile.axes.find((axis) => axis.axis === capped.axis);
    const newCap = capped.point_cap + 2;
    target.point_cap = newCap;
    target.maximum = Math.max(target.maximum, target.minimum + newCap);
    target.value_at_cap = target.maximum;
    mountDraft(panel);
    await openStep("allocation");
    wrapper.get(tid("creation-race")).setValue(OTHER_PLAIN.key);
    field(capped.axis).setValue(newCap);
    await nextTick();
    await nextTick();
    expect(slider(capped.axis).attributes("max")).toBe(String(newCap));
    expect(slider(capped.axis).element.value).toBe(String(newCap));
  });
});

describe("CreationPortraitSlot: the persistent empty portrait", () => {
  const slot = () => wrapper.findComponent(CreationPortraitSlot);

  it("selects the matching server silhouette entry for each sex and apparent-age interval", async () => {
    mountDraft();
    for (const entry of CUSTOM.silhouettes) {
      for (const age of [entry.apparent_age_minimum, entry.apparent_age_maximum]) {
        await wrapper.get(tid("creation-sex")).setValue(entry.sex);
        await wrapper.get(tid("creation-field-apparentAge")).setValue(age);
        expect(slot().props("silhouette")).toStrictEqual(entry.artwork);
      }
    }
  });

  it("keeps a neutral slot when no single entry matches the input", async () => {
    mountDraft();
    const entry = CUSTOM.silhouettes[0];
    await wrapper.get(tid("creation-sex")).setValue(entry.sex);
    await wrapper.get(tid("creation-field-apparentAge")).setValue(entry.apparent_age_maximum + 0.5);
    expect(slot().props("silhouette")).toBeNull();
    await wrapper.get(tid("creation-field-apparentAge")).setValue("");
    expect(slot().props("silhouette")).toBeNull();
    expect(wrapper.find(tid("creation-portrait-silhouette")).exists()).toBe(false);
  });

  it("shows the current name or an unnamed state, stays on every step and emits nothing on its own", async () => {
    mountDraft();
    const name = wrapper.get(tid("creation-portrait-name"));
    expect(name.text()).toBe(DRAFT.display_name);
    expect(name.attributes("data-unnamed")).toBeUndefined();
    await wrapper.get(tid("creation-field-displayName")).setValue("   ");
    expect(wrapper.get(tid("creation-portrait-name")).attributes("data-unnamed")).toBe("true");
    expect(wrapper.get(tid("creation-portrait-name")).text()).not.toBe("");
    for (const key of STEP_KEYS) {
      await openStep(key);
      expect(wrapper.get(tid("creation-portrait-slot")).isVisible()).toBe(true);
      // The generation control (creation-draft-portrait) is the slot's only
      // action; merely showing the slot on a step uses none of it.
      expect(wrapper.get(tid("creation-portrait-slot")).findAll("button")).toHaveLength(1);
    }
    expect(slot().emitted()).toStrictEqual({});
  });
});
