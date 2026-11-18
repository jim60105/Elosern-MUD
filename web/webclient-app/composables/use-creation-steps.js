// The custom form's local step model (creation-stepped-form; design §6): the
// current step, free navigation between the three steps, and the static map
// from form fields to the step that displays them. The step is browser-local
// presentation state: it never enters the draft and never sends an action.
// Validation stays in use-creation-custom.js; this group only says WHERE an
// error the existing pipeline reported is displayed.
import { computed, ref } from "vue";
import { ALLOCATION_AXES } from "./use-creation-form.js";

export const STEPS = Object.freeze([
  Object.freeze({ key: "identity", title: "身分" }),
  Object.freeze({ key: "story", title: "角色故事" }),
  Object.freeze({ key: "allocation", title: "能力配置" }),
]);

const STEP_KEYS = STEPS.map((step) => step.key);

// Field identifier -> step. Field identifiers are the payload paths the form
// writes (`persona.<key>`, `allocations.<axis>`), plus the name-roll control.
export const FIELD_STEP = Object.freeze({
  display_name: "identity",
  name_roll: "identity",
  sex: "identity",
  age: "identity",
  apparent_age: "identity",
  race: "identity",
  subrace: "identity",
  affinity_elements: "story",
  background: "story",
  "persona.personality": "story",
  "persona.life_story": "story",
  "persona.habit": "story",
  ...Object.fromEntries(ALLOCATION_AXES.map((axis) => [`allocations.${axis}`, "allocation"])),
});

export function stepOfField(field) {
  return FIELD_STEP[field] ?? null;
}

export function useCreationSteps({ errorFields }) {
  const currentStep = ref(STEP_KEYS[0]);
  const stepIndex = computed(() => STEP_KEYS.indexOf(currentStep.value));

  function goToStep(key) {
    if (STEP_KEYS.includes(key)) currentStep.value = key;
  }

  function previousStep() {
    if (stepIndex.value > 0) currentStep.value = STEP_KEYS[stepIndex.value - 1];
  }

  function nextStep() {
    if (stepIndex.value < STEP_KEYS.length - 1) currentStep.value = STEP_KEYS[stepIndex.value + 1];
  }

  // The first control the browser itself found invalid at the last submit
  // (written by CreationCustomSteps, which owns the DOM). Overlay-lifetime
  // state: cleared on the next submit or once that control becomes valid.
  const nativeErrorField = ref(null);

  // Every step that holds a field the last submit reported.
  const errorSteps = computed(() => {
    const fields = [...(errorFields.value ?? [])];
    if (nativeErrorField.value) fields.push(nativeErrorField.value);
    return new Set(fields.map(stepOfField).filter(Boolean));
  });

  return { currentStep, stepIndex, goToStep, previousStep, nextStep, nativeErrorField, errorSteps };
}
