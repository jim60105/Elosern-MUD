<script setup>
// CreationOverlay (B5 overlays family): the full-viewport character-creation
// wizard for the committed `creation` v1 panel (web/webclient/presentation/
// creation.py). Sub-states stay separate and testable (design D-risk): a
// preset-pick state, the custom form (name/adult/race/subrace/allocation/
// background/affinity), and the concept state. The adult gate (design D1)
// rejects BOTH the age and apparent_age fields below the descriptor's 18
// minimum before activation. Every action emits the exact OOB `creation.*`
// envelope — no field is invented; the server remains authoritative.
import { computed, reactive, ref, watch } from "vue";

const props = defineProps({
  // The committed `creation` v1 panel payload (the available form, a
  // server-persisted wizard draft, or the registry-owned unavailable form).
  creation: { type: Object, required: true },
  open: { type: Boolean, default: true },
  // The store's last `ui_action_result` (or null): a rejected creation
  // action renders its code/message in the form message (the legacy
  // `creation-form-message` hook).
  result: { type: Object, default: null },
  // The store-driven creation dock stage (the legacy creation dock port):
  // null outside creation mode, otherwise the dock stage the keyboard router
  // and the confirmation screens mirror (root/presets/custom/confirm).
  stage: { type: Object, default: null },
});

const emit = defineEmits(["action", "close", "request-reset", "cancel-confirm"]);

const available = computed(() => props.creation.available === true);
const reason = computed(() => props.creation.reason?.message ?? "");
const presets = computed(() => (Array.isArray(props.creation.presets) ? props.creation.presets : []));
const custom = computed(() => props.creation.custom);
const draft = computed(() => props.creation.draft);

// The wizard resumes from the draft's own stage; without a draft it opens
// the preset state. Live snapshot updates to the `creation` prop re-sync the
// wizard from the server-persisted draft (webclient-character-creation-ui:
// the server owns the draft — the browser resumes at the saved stage).
const stageMode = (stage) =>
  stage === "custom_filled" ? "custom" : stage === "concept_filled" ? "concept" : "preset";
const mode = ref("preset");

// Form state (custom + concept sub-states).
const name = ref("");
const age = ref(18);
const apparentAge = ref(18);
const race = ref("human");
const subrace = ref(null);
const allocations = reactive({ hp: 0, mp: 0, sp: 0, atk_phys: 0, agility: 0, defense: 0 });
const background = ref("");
const affinitySelected = ref(new Set());
const conceptText = ref("");
const selectedPresetKey = ref(null);

function zeroAllocations() {
  allocations.hp = 0;
  allocations.mp = 0;
  allocations.sp = 0;
  allocations.atk_phys = 0;
  allocations.agility = 0;
  allocations.defense = 0;
}

// Tracks any local form input since the last server draft: a no-draft
// snapshot must never discard typed values (e.g. a pointer-opened custom form
// hit by a reconnect snapshot without a draft). Draft-driven field fills are
// guarded by `syncingDraft` so they never count as user input, and leaving
// the form (preset mode) clears the flag.
const formTouched = ref(false);
let syncingDraft = false;
function markFormTouched() {
  if (!syncingDraft) {
    formTouched.value = true;
  }
}
watch(
  [name, age, apparentAge, race, subrace, background, conceptText, allocations],
  markFormTouched,
  { deep: true, flush: "sync" },
);
watch(mode, (m) => {
  if (m === "preset") {
    formTouched.value = false;
  }
});

// Re-sync every wizard field from the server-confirmed draft carried by the
// latest `creation` panel payload; with no draft, reset to the preset state
// with default field values.
function syncFromDraft() {
  const d = props.creation.draft;
  if (!d) {
    // With no server draft the wizard resets to the preset state UNLESS the
    // store-driven dock stage is already on a form (keyboard navigation into
    // the custom/concept form must survive a fresh snapshot that carries no
    // draft, e.g. a stale-save rejection) or the player has typed into the
    // local form (a pointer-opened form must survive a no-draft snapshot too).
    const stage = props.stage ? props.stage.stage : null;
    if (stage !== "custom" && stage !== "concept" && !formTouched.value) {
      mode.value = "preset";
      selectedPresetKey.value = null;
    }
    return;
  }
  syncingDraft = true;
  try {
    // A live concept apply flips the store-driven dock stage to "custom" so the
    // pre-filled custom form shows; a resumed concept draft (no stage flip) keeps
    // the concept field (stageMode maps concept_filled -> concept).
    const stage = props.stage ? props.stage.stage : null;
    mode.value = stage === "custom" ? "custom" : stageMode(d.stage);
    if (d.mode === "preset") {
      selectedPresetKey.value = d.preset_key ?? null;
      return;
    }
    name.value = d.display_name ?? "";
    age.value = d.age ?? 18;
    apparentAge.value = d.apparent_age ?? 18;
    race.value = d.race ?? "human";
    subrace.value = d.subrace ?? null;
    zeroAllocations();
    if (d.allocations) {
      for (const axis of Object.keys(allocations)) {
        allocations[axis] = d.allocations[axis] ?? 0;
      }
    }
    background.value = d.background ?? "";
    affinitySelected.value = new Set(d.affinity_elements ?? []);
    if (d.mode === "concept") {
      conceptText.value = d.background ?? "";
    }
    formTouched.value = false;
  } finally {
    syncingDraft = false;
  }
}

syncFromDraft();
watch(() => props.creation.draft, syncFromDraft, { deep: true });

// -- Preset state -----------------------------------------------------------
function setMode(next) {
  mode.value = next;
}

function selectPreset(card) {
  selectedPresetKey.value = card.key;
  emit("action", { action_id: "creation.preset", payload: { preset_key: card.key } });
}

// -- Custom state -----------------------------------------------------------
const minimumAge = computed(() => custom.value?.adult?.age_minimum ?? 18);
const minimumApparentAge = computed(() => custom.value?.adult?.apparent_age_minimum ?? 18);

const races = computed(() => (Array.isArray(custom.value?.races) ? custom.value.races : []));

const raceInfo = computed(() => races.value.find((r) => r.key === race.value));
const hasSubraces = computed(() => Array.isArray(raceInfo.value?.subraces));
const subraceOptions = computed(() => {
  const list = raceInfo.value?.subraces ?? [];
  const registry = custom.value?.subraces ?? {};
  return list.map((key) => ({ key, label: registry[key]?.display_name_zh ?? key }));
});
const affinity = computed(() => custom.value?.affinity?.[race.value]);
const affinityMax = computed(() => affinity.value?.maximum ?? 0);
const affinityElements = computed(() => affinity.value?.elements ?? []);

// Strict (race, subrace) match only — no same-race or first-profile
// fallback, so a missing profile shows no briefing rather than a wrong one.
const currentProfile = computed(() => {
  const profiles = Array.isArray(custom.value?.profiles) ? custom.value.profiles : [];
  const sub = subrace.value ?? null;
  return profiles.find((p) => p.race === race.value && (p.subrace ?? null) === sub) ?? null;
});

// Allocation briefing (character-creation-ux contract): before the
// allocation inputs, state the profile budget, each axis's 0–span range, and
// the rule that the total must equal the budget.
const allocationTotal = computed(() =>
  Object.values(allocations).reduce((sum, value) => sum + (Number(value) || 0), 0));
const budgetBriefing = computed(() => {
  const profile = currentProfile.value;
  if (!profile) return "";
  const ranges = profile.axes.map((a) => `${a.label} ${a.minimum}-${a.maximum}`).join(" · ");
  return `點數額度 ${profile.budget}｜${ranges}｜總和須等於額度 ${profile.budget}`;
});

// The adult gate (design D1): reject when EITHER age field is below the
// descriptor's minimum (18) — the server stays authoritative.
const gatePassed = computed(
  () => Number(age.value) >= minimumAge.value && Number(apparentAge.value) >= minimumApparentAge.value,
);
const gateError = ref(false);
const budgetError = ref(false);
const subraceError = ref(false);

// The legacy `creation-form-message` hook (Phase-0 audit §2.3 REMAP-TO-TESTID):
// a single form-message element that surfaces a server rejection (result.code /
// result.message) or the first active local validation error. The element is
// rendered only while a message is active.
const formMessage = computed(() => {
  const r = props.result;
  if (r && r.outcome === "rejected") {
    return r.code || r.message || "";
  }
  if (gateError.value) return `年齡與外觀年齡皆須 ≥ ${minimumAge.value}`;
  if (subraceError.value) return "已選擇有血統的種族時，必須先選擇血統";
  if (budgetError.value) return `點數總和 ${allocationTotal.value} 不等於額度 ${currentProfile.value?.budget}`;
  return "";
});

function onRaceChange() {
  const info = races.value.find((r) => r.key === race.value);
  if (!info || !Array.isArray(info.subraces)) subrace.value = null;
  const max = affinityMax.value;
  const keys = [...affinitySelected.value];
  if (keys.length > max) affinitySelected.value = new Set(keys.slice(0, max));
}

function toggleAffinity(elementKey) {
  const next = new Set(affinitySelected.value);
  if (next.has(elementKey)) {
    next.delete(elementKey);
  } else if (next.size < affinityMax.value) {
    next.add(elementKey);
  }
  affinitySelected.value = next;
}

// The custom form cannot submit without a subrace for a subrace-bearing
// race (webclient-character-creation-ui: the form SHALL require a subrace
// selection; the "no subrace" radio is never rendered) — send nothing.
function confirmCustom() {
  gateError.value = false;
  budgetError.value = false;
  subraceError.value = false;
  if (!gatePassed.value) {
    gateError.value = true;
    return;
  }
  if (hasSubraces.value && !subrace.value) {
    subraceError.value = true;
    return;
  }
  const profile = currentProfile.value;
  if (profile && allocationTotal.value !== profile.budget) {
    budgetError.value = true;
    return;
  }
  const payload = {
    display_name: name.value,
    age: Number(age.value),
    apparent_age: Number(apparentAge.value),
    race: race.value,
    subrace: subrace.value,
    // The wire payload always carries the exact eight keys (the server
    // revalidates the set); blank fields emit their JSON-safe defaults, the
    // same convention as the legacy creation menu.
    background: background.value.trim() !== "" ? background.value.trim() : null,
    affinity_elements: [...affinitySelected.value],
    allocations: {
      hp: Number(allocations.hp),
      mp: Number(allocations.mp),
      sp: Number(allocations.sp),
      atk_phys: Number(allocations.atk_phys),
      agility: Number(allocations.agility),
      defense: Number(allocations.defense),
    },
  };
  emit("action", { action_id: "creation.custom", payload });
}

// -- Concept state -----------------------------------------------------------
function applyConcept() {
  emit("action", { action_id: "creation.concept", payload: { concept: conceptText.value } });
}

// -- Frame actions -----------------------------------------------------------
// Activation and the destructive reset always traverse the confirmation
// screen (the legacy creation dock contract): the store opens the confirm
// stage after a successful save or on a reset request, and only the confirm
// screen's 確認 button dispatches `creation.activate` / `creation.reset`.
function requestReset() {
  emit("request-reset");
}

function close() {
  emit("close");
}

// The store-driven creation dock stage mirrors the wizard's mode so keyboard
// and pointer share one flow: root/presets -> preset, custom -> custom,
// concept -> concept, confirm -> the confirmation screen overlays the body.
// Only a stage VALUE change re-syncs (a pointer tab click must not be
// overridden by an unchanged root stage re-publish).
let lastStage = null;
watch(
  () => props.stage,
  (s) => {
    const value = s ? s.stage : null;
    if (value === null || value === lastStage) {
      return;
    }
    lastStage = value;
    if (value === "custom") {
      mode.value = "custom";
    } else if (value === "concept") {
      mode.value = "concept";
    } else if (value === "root" || value === "presets") {
      mode.value = "preset";
    }
  },
);

function confirmCurrent() {
  const actionId = props.stage && props.stage.confirmAction;
  if (actionId) {
    emit("action", { action_id: actionId, payload: {} });
  }
}

function cancelConfirm() {
  emit("cancel-confirm");
}
</script>

<template>
  <section
    v-if="open"
    class="elosern creation-overlay"
    role="dialog"
    aria-modal="true"
    aria-label="角色創建"
    data-testid="creation-overlay"
    :data-available="available ? 'true' : 'false'"
    :data-mode="mode"
  >
    <header class="creation-overlay__header">
      <h2 class="creation-overlay__title" data-testid="creation-overlay-title">角色創建</h2>
      <button
        type="button"
        class="creation-overlay__close"
        data-testid="creation-overlay-close"
        @click="close"
      >
        ✕ 關閉
      </button>
    </header>

    <div class="creation-overlay__body" data-testid="creation-body">
      <template v-if="available">
        <template v-if="stage && stage.stage === 'confirm'">
          <div class="creation-confirm" data-testid="creation-confirm">
            <div class="creation-confirm-title" data-testid="creation-confirm-title">
              {{ stage.confirmLabel }}
            </div>
            <div class="creation-confirm-actions">
              <button
                type="button"
                class="creation-confirm-ok"
                data-testid="creation-confirm-ok"
                @click="confirmCurrent"
              >
                確認
              </button>
              <button
                type="button"
                class="creation-confirm-cancel"
                data-testid="creation-confirm-cancel"
                @click="cancelConfirm"
              >
                取消
              </button>
            </div>
          </div>
        </template>
        <template v-else>
          <nav class="creation-overlay__modes">
            <button
              type="button"
              class="creation-overlay__mode"
              :class="{ 'is-active': mode === 'preset' }"
              data-testid="creation-mode-preset"
              @click="setMode('preset')"
            >
              預設
            </button>
            <button
              type="button"
              class="creation-overlay__mode"
              :class="{ 'is-active': mode === 'custom' }"
              data-testid="creation-mode-custom"
              @click="setMode('custom')"
            >
              自訂
            </button>
            <button
              type="button"
              class="creation-overlay__mode"
              :class="{ 'is-active': mode === 'concept' }"
              data-testid="creation-mode-concept"
              @click="setMode('concept')"
            >
              概念
            </button>
          </nav>

        <div v-if="mode === 'preset'" class="creation-overlay__presets">
          <button
            v-for="card in presets"
            :key="card.key"
            type="button"
            class="creation-preset-card"
            data-testid="creation-preset-card"
            :data-preset-key="card.key"
            :data-selected="selectedPresetKey === card.key ? 'true' : 'false'"
            @click="selectPreset(card)"
          >
            <span class="creation-preset-card__name" data-testid="creation-preset-name">
              {{ card.display_name }}
            </span>
            <span class="creation-preset-card__race">{{ card.race }}</span>
            <span class="creation-preset-card__emphasis">{{ card.emphasis }}</span>
            <span class="creation-preset-card__background">{{ card.background }}</span>
          </button>
          <p v-if="formMessage" class="creation-form-message" data-testid="creation-form-message">{{ formMessage }}</p>
        </div>

        <div v-else-if="mode === 'custom'" class="creation-overlay__custom">
          <p
            v-if="draft && draft.background_generated"
            class="creation-concept-indicator"
            role="status"
            data-testid="creation-concept-indicator"
          >
            已套用構想草稿，背景已生成。
          </p>
          <p
            v-if="budgetBriefing"
            class="creation-budget-briefing"
            data-testid="creation-budget-briefing"
          >
            {{ budgetBriefing }}
          </p>

          <label class="creation-overlay__field">
            <span>名稱</span>
            <input
              type="text"
              data-testid="creation-field-displayName"
              :minlength="custom?.name?.min_length ?? 1"
              :maxlength="custom?.name?.max_length ?? 64"
              v-model="name"
            />
          </label>

          <label class="creation-overlay__field">
            <span>年齡</span>
            <input type="number" data-testid="creation-field-age" :min="minimumAge" v-model.number="age" />
          </label>
          <label class="creation-overlay__field">
            <span>外觀年齡</span>
            <input type="number" data-testid="creation-field-apparentAge" :min="minimumApparentAge" v-model.number="apparentAge" />
          </label>

          <label class="creation-overlay__field">
            <span>種族</span>
            <select v-model="race" data-testid="creation-race" @change="onRaceChange">
              <option v-for="r in races" :key="r.key" :value="r.key">{{ r.key }}</option>
            </select>
          </label>
          <p v-if="raceInfo?.description" class="creation-race-description" data-testid="creation-race-description">
            {{ raceInfo.description }}
          </p>

          <label v-if="hasSubraces" class="creation-overlay__field">
            <span>血統</span>
            <select v-model="subrace" data-testid="creation-subrace">
              <option v-for="o in subraceOptions" :key="o.key" :value="o.key">{{ o.label }}</option>
            </select>
          </label>

          <div class="creation-allocations">
            <label v-for="ax in currentProfile?.axes" :key="ax.axis" class="creation-overlay__field">
              <span>{{ ax.label }}（{{ ax.explanation }}）</span>
              <input
                type="number"
                :min="ax.minimum"
                :max="ax.maximum"
                v-model.number="allocations[ax.axis]"
                :data-testid="`creation-field-${ax.axis}`"
              />
            </label>
          </div>
           <p v-if="currentProfile" class="creation-allocation-total" data-testid="creation-allocation-total">
             已配置點數：{{ allocationTotal }} / {{ currentProfile.budget }}
           </p>

          <fieldset v-if="affinityMax > 0" class="creation-affinity" data-testid="creation-affinity">
            <legend>元素親和（上限 {{ affinityMax }}）</legend>
            <label v-for="el in affinityElements" :key="el.key" class="creation-affinity-item">
              <input
                type="checkbox"
                :checked="affinitySelected.has(el.key)"
                :disabled="!affinitySelected.has(el.key) && affinitySelected.size >= affinityMax"
                :data-testid="`creation-affinity-${el.key}`"
                @change="toggleAffinity(el.key)"
              />
              <span>{{ el.label }}</span>
            </label>
          </fieldset>

          <label class="creation-overlay__field">
            <span>背景（可選）</span>
            <textarea data-testid="creation-background" rows="3" v-model="background"></textarea>
          </label>

          <p v-if="formMessage" class="creation-form-message" data-testid="creation-form-message">{{ formMessage }}</p>
          <button type="button" class="creation-custom-confirm" data-testid="creation-submit" @click="confirmCustom">
            確認自訂
          </button>
        </div>

        <div v-else class="creation-overlay__concept">
          <p
            v-if="draft?.mode === 'concept' && draft.background"
            class="creation-background"
            data-testid="creation-background"
            :data-background-generated="draft.background_generated ? 'true' : 'false'"
          >
            {{ draft.background }}
          </p>
          <label class="creation-overlay__field">
            <span>角色概念</span>
            <textarea data-testid="creation-field-concept" rows="4" v-model="conceptText"></textarea>
          </label>
          <button type="button" class="creation-concept-apply" data-testid="creation-concept-submit" @click="applyConcept">
            套用概念
          </button>
        </div>

        <footer class="creation-overlay__footer">
          <button type="button" class="creation-reset" data-testid="creation-reset" @click="requestReset">
            重設
          </button>
        </footer>
        </template>
      </template>

      <p v-else class="creation-unavailable-reason" data-testid="creation-unavailable-reason">
        {{ reason }}
      </p>
    </div>
  </section>
</template>

<style scoped>
.creation-overlay {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: flex;
  flex-direction: column;
  background: var(--ink-950);
  color: var(--paper-100);
  font-family: var(--f-sans);
}

.creation-overlay__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-4) var(--sp-6);
  border-bottom: var(--line);
}

.creation-overlay__title {
  margin: 0;
  color: var(--paper-50);
  font-family: var(--f-display);
  font-size: 20px;
}

.creation-overlay__close {
  color: var(--paper-300);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-1) var(--sp-3);
  font-size: var(--text-sm);
  cursor: pointer;
}

.creation-overlay__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-4) var(--sp-6);
  overflow: auto;
}

.creation-overlay__modes {
  display: flex;
  gap: var(--sp-2);
}

.creation-overlay__mode {
  color: var(--paper-300);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-1) var(--sp-3);
  font-size: var(--text-sm);
  cursor: pointer;
}

.creation-overlay__mode.is-active {
  color: var(--paper-50);
  background: var(--ink-700);
  border-color: var(--seal-500);
}

.creation-overlay__presets {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--sp-3);
}

.creation-preset-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  box-sizing: border-box;
  padding: var(--sp-3);
  color: var(--paper-100);
  background: var(--ink-860);
  border: var(--line);
  border-left: 3px solid var(--seal-500);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
}

.creation-preset-card[data-selected="true"] {
  border-color: var(--seal-500);
  box-shadow: 0 0 0 2px var(--seal-glow);
}

.creation-preset-card__name {
  color: var(--paper-50);
  font-family: var(--f-display);
  font-size: var(--text-body);
}

.creation-preset-card__race {
  color: var(--paper-500);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

.creation-preset-card__emphasis {
  color: var(--gold-400);
}

.creation-preset-card__background {
  color: var(--paper-300);
}

.creation-overlay__custom,
.creation-overlay__concept {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.creation-budget-briefing {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-300);
  background: var(--panel-hi);
  border: 1px dashed var(--warn);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

.creation-overlay__field {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  color: var(--paper-300);
  font-size: var(--text-sm);
}

.creation-overlay__field input,
.creation-overlay__field select,
.creation-overlay__field textarea {
  color: var(--paper-100);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-1) var(--sp-2);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
}

.creation-allocations {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-2);
}

.creation-allocation-total {
  margin: 0;
  color: var(--paper-300);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

.creation-affinity {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.creation-affinity legend {
  color: var(--paper-500);
}

.creation-affinity-item {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  color: var(--paper-300);
}

.creation-form-message {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--seal-400);
  background: var(--panel-hi);
  border: 1px solid var(--seal-500);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}



.creation-overlay__footer {
  display: flex;
  gap: var(--sp-2);
}

.creation-reset {
  color: var(--paper-50);
  background: var(--seal-600);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-2) var(--sp-4);
  font-size: var(--text-sm);
  cursor: pointer;
}

.creation-confirm {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  padding: var(--sp-4);
  border: 1px solid var(--warn);
  border-radius: var(--radius-md);
  background: var(--panel-hi);
}

.creation-confirm-title {
  margin: 0;
  color: var(--paper-50);
  font-size: var(--text-lg);
}

.creation-confirm-actions {
  display: flex;
  gap: var(--sp-2);
}

.creation-confirm-ok,
.creation-confirm-cancel {
  color: var(--paper-50);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-2) var(--sp-4);
  font-size: var(--text-sm);
  cursor: pointer;
}

.creation-confirm-ok {
  background: var(--seal-600);
}

.creation-confirm-cancel {
  background: var(--ink-820);
}

.creation-unavailable-reason {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-300);
  background: var(--panel-hi);
  border: 1px dashed var(--warn);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}
</style>
