<script setup>
// CreationCustomSteps (creation-stepped-form; design §6): the custom form as
// three freely navigable steps (identity, story, allocation) under a step
// rail that always shows the remaining allocation points. It is a passive
// renderer of the overlay's existing form state: `form` is the flat binding
// set from useCreationOverlay, passed as is, so every v-model writes the very
// refs the draft sync, proposal fill and submit builder already own. There is
// no second form model and no new validation rule.
//
// All three steps stay mounted; `v-show` hides the inactive ones, which keeps
// them out of focus order and the accessibility tree while their native
// validity stays inspectable. The footer confirmation belongs to the overlay
// and calls `submit()` below, which only decides where an error is shown
// before and after running the existing `confirmCustom` unchanged.
import { computed, nextTick, ref } from "vue";
import { STEPS, stepOfField } from "../composables/use-creation-steps.js";
import { formatPointRange } from "../composables/use-creation-custom.js";

const props = defineProps({
  // The useCreationOverlay binding object (a plain object of refs, computeds
  // and handlers). Never wrap it in reactive(): the refs below must stay refs.
  form: { type: Object, required: true },
});

const {
  custom,
  name,
  age,
  apparentAge,
  race,
  subrace,
  allocations,
  background,
  sex,
  sexOptions,
  persona,
  affinitySelected,
  minimumAge,
  minimumApparentAge,
  races,
  raceInfo,
  hasSubraces,
  subraceOptions,
  affinityMax,
  affinityElements,
  currentProfile,
  allocationTotal,
  budgetBriefing,
  allocationPreview,
  needsAllocation,
  formErrorFields,
  reviewPrompt,
  onRaceChange,
  onSubraceChange,
  toggleAffinity,
  confirmCustom,
  rollName,
  rollDisabled,
  currentStep,
  stepIndex,
  goToStep,
  previousStep,
  nextStep,
  nativeErrorField,
  errorSteps,
} = props.form;

const root = ref(null);
const pad = (n) => String(n).padStart(2, "0");
// The panels are named by their plain step title; the rail button's own name
// also carries the live remaining points and the error flag.
const STEP_TITLE = Object.fromEntries(STEPS.map((step) => [step.key, step.title]));
const nextTitle = computed(() => STEPS[stepIndex.value + 1]?.title ?? null);

// Presentation arithmetic only: the server profile's budget minus the entered
// sum, never clamped. Without a resolved profile there is no budget to show.
const remaining = computed(() => (
  currentProfile.value ? currentProfile.value.budget - allocationTotal.value : null
));

function stepState(key, index) {
  if (errorSteps.value.has(key)) return "error";
  if (key === currentStep.value) return "active";
  return index < stepIndex.value ? "done" : "todo";
}

// Error presentation for one control: its field id, aria-invalid while the
// last submit reported it, and the form message as its description when the
// message is about this field.
function fieldAttrs(field, describedBy = null) {
  const reported = formErrorFields.value.includes(field);
  const invalid = reported || nativeErrorField.value === field;
  const ids = [describedBy, reported ? "creation-form-message" : null].filter(Boolean);
  return {
    "data-creation-field": field,
    "aria-invalid": invalid ? "true" : null,
    "aria-describedby": ids.length ? ids.join(" ") : null,
  };
}

// Presentation-only stepping: invalid direct entry is never repaired here.
// Budget admission and server validation remain in the existing form pipeline.
function canStep(axis, direction) {
  const value = allocations[axis.axis];
  return Number.isInteger(value)
    && value >= 0 && value <= axis.point_cap
    && value + direction >= 0 && value + direction <= axis.point_cap;
}

function stepAllocation(axis, direction) {
  if (canStep(axis, direction)) allocations[axis.axis] += direction;
}

// A zero-cap axis admits no points. It locks only while its value is already
// zero, so a stale non-zero value stays correctable through the number field.
// The axis whose number field holds focus never locks mid-edit (clearing a
// stale value to 0 must not drop keyboard/IME focus); it locks on blur.
const editingAxis = ref(null);
function isLocked(axis) {
  return axis.point_cap === 0 && allocations[axis.axis] === 0 && editingAxis.value !== axis.axis;
}

function fieldElements() {
  return root.value ? [...root.value.querySelectorAll("[data-creation-field]")] : [];
}

function elementOf(field) {
  return fieldElements().find((el) => el.dataset.creationField === field) ?? null;
}

function focusFirstControl(stepKey) {
  const panel = root.value?.querySelector(`[data-step-panel="${stepKey}"]`);
  panel?.querySelector("input:not(:disabled), select:not(:disabled), textarea:not(:disabled), button:not(:disabled)")
    ?.focus();
}

async function stepBy(move) {
  move();
  await nextTick();
  focusFirstControl(currentStep.value);
}

// A browser-raised `invalid` (e.g. from reportValidity) reveals its step.
function onInvalid(event) {
  const step = stepOfField(event.target?.dataset?.creationField);
  if (step) goToStep(step);
}

// Editing a step retires the errors the last submit reported on it; the form
// message itself keeps its existing lifetime (until the next submit).
function onEdit(event) {
  const field = event.target?.dataset?.creationField;
  const step = stepOfField(field);
  if (!step) return;
  if (formErrorFields.value.some((f) => stepOfField(f) === step)) {
    formErrorFields.value = formErrorFields.value.filter((f) => stepOfField(f) !== step);
  }
  if (nativeErrorField.value === field && event.target.validity?.valid) {
    nativeErrorField.value = null;
  }
}

// The footer confirmation. Native constraints are inspected, never enforced:
// the existing pipeline runs unchanged (and still sends whatever it sent
// before). Afterwards the first reported field in display order is revealed
// and focused. Always resolves, so the caller never runs a second submit.
async function submit() {
  const nativeEl = fieldElements().find((el) => !el.disabled && el.validity && !el.validity.valid) ?? null;
  nativeErrorField.value = nativeEl ? nativeEl.dataset.creationField : null;
  confirmCustom();
  const candidates = [nativeEl, ...formErrorFields.value.map(elementOf)].filter(Boolean);
  if (candidates.length === 0) return;
  const target = candidates.reduce((first, el) => (
    first.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_PRECEDING ? el : first
  ));
  goToStep(stepOfField(target.dataset.creationField));
  await nextTick();
  target.focus();
  if (target === nativeEl && typeof target.reportValidity === "function") target.reportValidity();
}

defineExpose({ submit });
</script>

<template>
  <div
    ref="root"
    class="creation-steps"
    data-testid="creation-steps"
    :data-step="currentStep"
    @invalid.capture="onInvalid"
    @input.capture="onEdit"
    @change.capture="onEdit"
  >
    <p v-if="reviewPrompt" class="creation-proposal-review" role="status" data-testid="creation-proposal-review">
      {{ reviewPrompt }}
    </p>

    <nav class="creation-steps__rail" aria-label="建角步驟">
      <ol>
        <li v-for="(step, index) in STEPS" :key="step.key" :data-state="stepState(step.key, index)">
          <button
            :id="`creation-steps-tab-${step.key}`"
            type="button"
            class="creation-steps__tab"
            :data-testid="`creation-steps-tab-${step.key}`"
            :aria-current="step.key === currentStep ? 'step' : null"
            @click="goToStep(step.key)"
          >
            <span class="creation-steps__no" aria-hidden="true">{{ pad(index + 1) }}</span>
            <span class="creation-steps__title">{{ step.title }}</span>
            <span v-if="errorSteps.has(step.key)" class="creation-steps__flag" data-testid="creation-steps-error">
              <i aria-hidden="true"></i>需修正
            </span>
            <span
              v-if="step.key === 'allocation'"
              class="creation-steps__remaining"
              data-testid="creation-steps-remaining"
              :data-remaining="remaining ?? ''"
              :data-over="remaining !== null && remaining < 0 ? 'true' : null"
            >
              剩餘 <b>{{ remaining ?? "—" }}</b> 點
            </span>
          </button>
        </li>
      </ol>
    </nav>

    <div class="creation-steps__pages">
      <!-- 01 身分 -->
      <section
        v-show="currentStep === 'identity'"
        class="creation-steps__page creation-steps__page--identity"
        data-step-panel="identity"
        data-testid="creation-steps-panel-identity"
        :aria-label="STEP_TITLE.identity"
      >
        <div class="creation-field creation-field--name">
          <label for="creation-name-input">名稱</label>
          <span class="creation-field__row">
            <input
              id="creation-name-input"
              type="text"
              data-testid="creation-field-displayName"
              :minlength="custom?.name?.min_length ?? 1"
              :maxlength="custom?.name?.max_length ?? 64"
              v-bind="fieldAttrs('display_name')"
              v-model="name"
            />
            <button
              type="button"
              class="ui-icon-btn creation-roll-button"
              data-testid="creation-roll-name"
              aria-label="擲名"
              :disabled="rollDisabled"
              @click="rollName"
            >
              🎲
            </button>
          </span>
        </div>

        <label class="creation-field creation-field--sex">
          <span>性別</span>
          <select data-testid="creation-sex" v-bind="fieldAttrs('sex')" v-model="sex">
            <option v-for="option in sexOptions" :key="option.key" :value="option.key">{{ option.label }}</option>
          </select>
        </label>

        <label class="creation-field">
          <span>年齡</span>
          <input type="number" data-testid="creation-field-age" :min="minimumAge" v-bind="fieldAttrs('age')" v-model.number="age" />
        </label>
        <label class="creation-field">
          <span>外觀年齡</span>
          <input
            type="number"
            data-testid="creation-field-apparentAge"
            :min="minimumApparentAge"
            v-bind="fieldAttrs('apparent_age')"
            v-model.number="apparentAge"
          />
        </label>

        <label class="creation-field">
          <span>種族</span>
          <select v-model="race" data-testid="creation-race" v-bind="fieldAttrs('race')" @change="onRaceChange">
            <option v-for="r in races" :key="r.key" :value="r.key">{{ r.display_name_zh || r.key }}</option>
          </select>
        </label>
        <p v-if="raceInfo?.description" class="creation-race-description" data-testid="creation-race-description">
          {{ raceInfo.description }}
        </p>

        <label v-if="hasSubraces" class="creation-field">
          <span>血統</span>
          <select v-model="subrace" data-testid="creation-subrace" v-bind="fieldAttrs('subrace')" @change="onSubraceChange">
            <option v-for="o in subraceOptions" :key="o.key" :value="o.key">{{ o.label }}</option>
          </select>
        </label>
      </section>

      <!-- 02 角色故事 -->
      <section
        v-show="currentStep === 'story'"
        class="creation-steps__page creation-steps__page--story"
        data-step-panel="story"
        data-testid="creation-steps-panel-story"
        :aria-label="STEP_TITLE.story"
      >
        <p class="creation-steps__hint">背景可留空；個性、生平與習慣請全部填寫，或全部留空。</p>
        <fieldset v-if="affinityMax > 0" class="creation-affinity" data-testid="creation-affinity">
          <legend>元素親和（上限 {{ affinityMax }}）</legend>
          <label v-for="el in affinityElements" :key="el.key" class="creation-affinity-item">
            <input
              type="checkbox"
              :checked="affinitySelected.has(el.key)"
              :disabled="!affinitySelected.has(el.key) && affinitySelected.size >= affinityMax"
              :data-testid="`creation-affinity-${el.key}`"
              v-bind="fieldAttrs('affinity_elements')"
              @change="toggleAffinity(el.key)"
            />
            <span>{{ el.label }}</span>
          </label>
        </fieldset>

        <label class="creation-field">
          <span>背景（可選）</span>
          <textarea data-testid="creation-background" rows="3" v-bind="fieldAttrs('background')" v-model="background"></textarea>
        </label>
        <label class="creation-field">
          <span>個性</span>
          <textarea
            data-testid="creation-persona-personality"
            rows="3"
            maxlength="600"
            v-bind="fieldAttrs('persona.personality')"
            v-model="persona.personality"
          ></textarea>
        </label>
        <label class="creation-field">
          <span>生平</span>
          <textarea
            data-testid="creation-persona-life_story"
            rows="3"
            maxlength="600"
            v-bind="fieldAttrs('persona.life_story')"
            v-model="persona.life_story"
          ></textarea>
        </label>
        <label class="creation-field">
          <span>習慣</span>
          <textarea
            data-testid="creation-persona-habit"
            rows="3"
            maxlength="600"
            v-bind="fieldAttrs('persona.habit')"
            v-model="persona.habit"
          ></textarea>
        </label>
      </section>

      <!-- 03 能力配置 -->
      <section
        v-show="currentStep === 'allocation'"
        class="creation-steps__page creation-steps__page--allocation"
        data-step-panel="allocation"
        data-testid="creation-steps-panel-allocation"
        :aria-label="STEP_TITLE.allocation"
      >
        <div class="creation-allocation-head">
          <p v-if="currentProfile" class="creation-allocation-total" data-testid="creation-allocation-total">
            <span>已配置點數</span>
            <b>{{ allocationTotal }}</b><span class="creation-allocation-total__of">/ {{ currentProfile.budget }}</span>
          </p>
          <p v-if="budgetBriefing" class="creation-budget-briefing" data-testid="creation-budget-briefing">{{ budgetBriefing }}</p>
          <p v-else class="creation-steps__hint">目前尚無對應的能力配置資料。</p>
          <p v-if="needsAllocation" class="creation-budget-briefing" role="status" data-testid="creation-needs-allocation">
            先前的配點已不再適用，請重新配點並儲存，才能確認建立角色。
          </p>
        </div>
        <div class="creation-allocations">
          <div
            v-for="ax in currentProfile?.axes"
            :key="ax.axis"
            class="creation-allocation"
            :data-locked="isLocked(ax) ? 'true' : null"
          >
            <label :id="`creation-allocation-label-${ax.axis}`" :for="`creation-allocation-${ax.axis}`" class="creation-allocation__label">{{ ax.label }}</label>
            <p :id="`creation-axis-help-${ax.axis}`" class="creation-allocation__help">{{ ax.explanation }} ‧ 配點 {{ formatPointRange(0, ax.point_cap) }}</p>
            <div class="creation-stepper">
              <button type="button" class="ui-icon-btn" :aria-label="`減少${ax.label}`"
                :data-testid="`creation-step-${ax.axis}-down`" :disabled="!canStep(ax, -1)" @click="stepAllocation(ax, -1)">−</button>
              <input :id="`creation-allocation-${ax.axis}`" type="number" min="0" :max="ax.point_cap"
                v-bind="fieldAttrs(`allocations.${ax.axis}`, `creation-axis-help-${ax.axis}`)"
                :disabled="isLocked(ax)" @focus="editingAxis = ax.axis" @blur="editingAxis = null"
                v-model.number="allocations[ax.axis]" :data-testid="`creation-field-${ax.axis}`" />
              <button type="button" class="ui-icon-btn" :aria-label="`增加${ax.label}`"
                :data-testid="`creation-step-${ax.axis}-up`" :disabled="!canStep(ax, 1)" @click="stepAllocation(ax, 1)">+</button>
            </div>
            <!-- Keyed by the cap: a cap and value change in one render would
                 otherwise clamp the value to the old max (v-model runs first). -->
            <input
              :id="`creation-slider-${ax.axis}`"
              :key="`${ax.axis}:${ax.point_cap}`"
              type="range"
              class="creation-allocation__slider"
              min="0"
              :max="ax.point_cap"
              step="1"
              :aria-labelledby="`creation-allocation-label-${ax.axis}`"
              v-bind="fieldAttrs(`allocations.${ax.axis}`, `creation-axis-help-${ax.axis}`)"
              :disabled="ax.point_cap === 0"
              v-model.number="allocations[ax.axis]"
              :data-testid="`creation-slider-${ax.axis}`"
            />
            <p class="creation-allocation__help" :data-testid="`creation-preview-${ax.axis}`">
              預覽值 {{ allocationPreview.find((entry) => entry.axis === ax.axis)?.value ?? ax.minimum }}
            </p>
          </div>
        </div>
      </section>
    </div>

    <div class="creation-steps__nav">
      <button
        type="button"
        class="ui-btn ui-btn--ghost creation-steps__prev"
        data-testid="creation-steps-prev"
        :disabled="stepIndex === 0"
        @click="stepBy(previousStep)"
      >
        <span aria-hidden="true">‹</span> 上一步
      </button>
      <button
        v-if="nextTitle"
        type="button"
        class="ui-btn creation-steps__next"
        data-testid="creation-steps-next"
        @click="stepBy(nextStep)"
      >
        下一步：{{ nextTitle }} <span aria-hidden="true">›</span>
      </button>
    </div>
  </div>
</template>

<style scoped src="./creation-custom-steps.css"></style>
