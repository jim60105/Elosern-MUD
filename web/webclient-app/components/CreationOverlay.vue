<script setup>
// CreationOverlay (B5 overlays family): the full-viewport character-creation
// wizard for the committed `creation` v5 panel (web/webclient/presentation/
// creation.py). Sub-states stay separate and testable (design D-risk): a
// preset-pick state, the custom form (name/age/race/subrace/allocation/
// affinity/background/persona), and the concept state. The panel carries
// the player-owned draft `persona` block and the optional transient concept
// `proposal` slot (retool-concept-transient-fill): the slot pre-fills the
// custom form revision-gated and never auto-submits. The age bounds gate
// (design D1) rejects BOTH the age and apparent_age fields below the
// descriptor's minimum before activation. Every action emits the exact OOB `creation.*`
// envelope — no field is invented; the server remains authoritative.
// The behavior groups live in ./composables/use-creation-*.js (each watch
// stays with the state it mutates); every binding below is a group's verbatim
// state/handler, destructured so the template is unchanged.
import { useCreationOverlay } from "../composables/use-creation-overlay.js";

const props = defineProps({
  // The committed `creation` v5 panel payload (the available form, a
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
  // A return-bearing dispatch callback (AppClient wraps `store.dispatchAction`):
  // returns the requestId when the mutation is admitted, null when the
  // single-mutation-in-flight gate rejects it. The concept apply sets its
  // loading state ONLY after admission, so a gate-rejected apply never
  // sticks a spinner (retool-concept-fill-navigation D1). Without the prop
  // (standalone mounts/tests) the apply falls back to the `action` event.
  dispatch: { type: Function, default: null },
  // The store's `view.dispatch` slice ({inFlight, submittedRequestId}): the
  // failure-match correlation and the global-gate release safety net (D1).
  dispatchState: { type: Object, default: null },
  // The action-feedback queue API (add-action-feedback-toasts). The form is
  // the SOLE writer of the concept-apply success confirmation toast (D3);
  // the store writes only failure crits.
  pushToast: { type: Function, default: null },
});

const emit = defineEmits(["action", "request-reset", "cancel-confirm"]);

const creation = useCreationOverlay(props, emit);
const {
  available,
  reason,
  presets,
  custom,
  mode,
  setMode,
  selectPreset,
  selectedPresetKey,
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
  conceptText,
  conceptPending,
  applyFrozen,
  minimumAge,
  minimumApparentAge,
  races,
  raceDisplayName,
  raceInfo,
  hasSubraces,
  subraceOptions,
  affinityMax,
  affinityElements,
  currentProfile,
  allocationTotal,
  budgetBriefing,
  formMessage,
  resultMessage,
  onRaceChange,
  toggleAffinity,
  confirmCustom,
  applyConcept,
  rollName,
  rollDisabled,
  reviewPrompt,
  requestReset,
  confirmCurrent,
  cancelConfirm,
} = creation;

// Presentation-only stepping: invalid direct entry is never repaired here.
// Budget admission and server validation remain in the existing form pipeline.
function canStep(axis, direction) {
  const value = allocations[axis.axis];
  return Number.isInteger(value)
    && value >= axis.minimum && value <= axis.maximum
    && value + direction >= axis.minimum && value + direction <= axis.maximum;
}

function stepAllocation(axis, direction) {
  if (canStep(axis, direction)) allocations[axis.axis] += direction;
}

function allocationFraction(axis) {
  const value = allocations[axis.axis];
  const span = axis.maximum - axis.minimum;
  return Number.isFinite(value) && span > 0
    ? Math.max(0, Math.min(1, (value - axis.minimum) / span))
    : 0;
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
      <div>
        <p class="creation-overlay__eyebrow">ELOSERN · 伊洛瑟恩</p>
        <h2 class="creation-overlay__title" data-testid="creation-overlay-title">角色創建</h2>
      </div>
      <p class="creation-overlay__intro">選擇起點，寫下你的故事。</p>
    </header>

    <div class="creation-overlay__body" data-testid="creation-body">
      <template v-if="available">
        <p
          v-if="resultMessage"
          class="creation-result-message"
          role="alert"
          data-testid="creation-result-message"
          :data-outcome="result && result.outcome"
        >
          {{ resultMessage }}
        </p>
        <template v-if="stage && stage.stage === 'confirm'">
          <div class="creation-confirm" data-testid="creation-confirm">
            <div class="creation-confirm-title" data-testid="creation-confirm-title">
              {{ stage.confirmLabel }}
            </div>
            <div class="creation-confirm-actions">
              <button
                type="button"
                class="ui-btn ui-btn--primary"
                data-testid="creation-confirm-ok"
                @click="confirmCurrent"
              >
                確認
              </button>
              <button
                type="button"
                class="ui-btn"
                data-testid="creation-confirm-cancel"
                @click="cancelConfirm"
              >
                取消
              </button>
            </div>
          </div>
        </template>
        <template v-else>
          <nav class="ui-tabs creation-overlay__modes" aria-label="建角方式">
            <button
              type="button"
              class="ui-tabs__tab creation-overlay__mode"
              :class="{ 'is-active': mode === 'preset' }"
              :aria-pressed="mode === 'preset'"
              data-testid="creation-mode-preset"
              @click="setMode('preset')"
            >
              預設
            </button>
            <button
              type="button"
              class="ui-tabs__tab creation-overlay__mode"
              :class="{ 'is-active': mode === 'custom' }"
              :aria-pressed="mode === 'custom'"
              data-testid="creation-mode-custom"
              @click="setMode('custom')"
            >
              自訂
            </button>
            <button
              type="button"
              class="ui-tabs__tab creation-overlay__mode"
              :class="{ 'is-active': mode === 'concept' }"
              :aria-pressed="mode === 'concept'"
              data-testid="creation-mode-concept"
              @click="setMode('concept')"
            >
              概念
            </button>
          </nav>

        <div v-if="mode === 'preset'" class="creation-overlay__presets">
          <button
            v-for="(card, index) in presets"
            :key="card.key"
            type="button"
            class="creation-preset-card"
            data-testid="creation-preset-card"
            :data-preset-key="card.key"
            :data-selected="selectedPresetKey === card.key ? 'true' : 'false'"
            :aria-pressed="selectedPresetKey === card.key"
            :aria-current="selectedPresetKey === card.key ? 'true' : undefined"
            @click="selectPreset(card)"
          >
            <span class="creation-preset-card__ornament" aria-hidden="true">
              <span>{{ String(index + 1).padStart(2, "0") }}</span>
            </span>
            <span class="creation-preset-card__name" data-testid="creation-preset-name">
              {{ card.display_name }}
            </span>
            <span class="creation-preset-card__race">{{ raceDisplayName(card.race) }}</span>
            <span class="creation-preset-card__emphasis">{{ card.emphasis }}</span>
            <span class="creation-preset-card__background">{{ card.background }}</span>
            <span class="creation-preset-card__choose">{{ selectedPresetKey === card.key ? "已選擇" : "選擇此角色" }}</span>
          </button>
        </div>

        <div v-else-if="mode === 'custom'" class="creation-overlay__custom">
          <section class="creation-region creation-identity" aria-labelledby="creation-identity-title">
          <h3 id="creation-identity-title" class="creation-region__title"><span aria-hidden="true">01</span> 身分</h3>
          <div class="creation-overlay__field">
            <div class="creation-overlay__name-line">
              <label for="creation-name-input">名稱</label>
              <span class="creation-overlay__name-row">
                <input
                  id="creation-name-input"
                  type="text"
                  data-testid="creation-field-displayName"
                  :minlength="custom?.name?.min_length ?? 1"
                  :maxlength="custom?.name?.max_length ?? 64"
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
          </div>

          <label class="creation-overlay__field">
            <span>性別</span>
            <select data-testid="creation-sex" v-model="sex">
              <option v-for="option in sexOptions" :key="option.key" :value="option.key">{{ option.label }}</option>
            </select>
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
              <option v-for="r in races" :key="r.key" :value="r.key">{{ r.display_name_zh || r.key }}</option>
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
          </section>

          <section class="creation-region creation-persona" aria-labelledby="creation-persona-title">
          <h3 id="creation-persona-title" class="creation-region__title"><span aria-hidden="true">02</span> 角色故事</h3>
          <p v-if="reviewPrompt" class="creation-proposal-review" role="status" data-testid="creation-proposal-review">
            {{ reviewPrompt }}
          </p>
          <p class="creation-region__hint">背景可留空；個性、生平與習慣請全部填寫，或全部留空。</p>
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

          <label class="creation-overlay__field">
            <span>個性</span>
            <textarea
              data-testid="creation-persona-personality"
              rows="3"
              maxlength="600"
              v-model="persona.personality"
            ></textarea>
          </label>
          <label class="creation-overlay__field">
            <span>生平</span>
            <textarea
              data-testid="creation-persona-life_story"
              rows="3"
              maxlength="600"
              v-model="persona.life_story"
            ></textarea>
          </label>
          <label class="creation-overlay__field">
            <span>習慣</span>
            <textarea
              data-testid="creation-persona-habit"
              rows="3"
              maxlength="600"
              v-model="persona.habit"
            ></textarea>
          </label>

          </section>

          <section class="creation-region creation-attributes" aria-labelledby="creation-attributes-title">
            <h3 id="creation-attributes-title" class="creation-region__title"><span aria-hidden="true">03</span> 能力配置</h3>
            <p v-if="budgetBriefing" class="creation-budget-briefing" data-testid="creation-budget-briefing">{{ budgetBriefing }}</p>
            <p v-else class="creation-region__hint">目前尚無對應的能力配置資料。</p>
            <p v-if="currentProfile" class="creation-allocation-total" data-testid="creation-allocation-total">
              已配置點數：{{ allocationTotal }} / {{ currentProfile.budget }}
            </p>
            <div class="creation-allocations">
              <div v-for="ax in currentProfile?.axes" :key="ax.axis" class="creation-allocation">
                <label :for="`creation-allocation-${ax.axis}`" class="creation-allocation__label">{{ ax.label }}</label>
                <p :id="`creation-axis-help-${ax.axis}`" class="creation-allocation__help">{{ ax.explanation }} · {{ ax.minimum }}–{{ ax.maximum }}</p>
                <div class="creation-stepper creation-overlay__field">
                  <button type="button" class="ui-icon-btn" :aria-label="`減少${ax.label}`"
                    :data-testid="`creation-step-${ax.axis}-down`" :disabled="!canStep(ax, -1)" @click="stepAllocation(ax, -1)">−</button>
                  <input :id="`creation-allocation-${ax.axis}`" type="number" :min="ax.minimum" :max="ax.maximum"
                    :aria-describedby="`creation-axis-help-${ax.axis}`"
                    v-model.number="allocations[ax.axis]" :data-testid="`creation-field-${ax.axis}`" />
                  <button type="button" class="ui-icon-btn" :aria-label="`增加${ax.label}`"
                    :data-testid="`creation-step-${ax.axis}-up`" :disabled="!canStep(ax, 1)" @click="stepAllocation(ax, 1)">+</button>
                </div>
                <div class="creation-allocation__bar" aria-hidden="true"><span :style="{ transform: `scaleX(${allocationFraction(ax)})` }"></span></div>
              </div>
            </div>
          </section>
        </div>

        <div v-else class="creation-overlay__concept">
          <div class="creation-concept-context">
            <p class="creation-overlay__eyebrow">角色構想</p>
            <h3 class="creation-region__title">從一段描述開始</h3>
            <p class="creation-region__hint">寫下角色的經歷或性格。套用概念後，仍可在自訂表單中檢視與修改，再確認角色。</p>
          </div>
          <div class="creation-concept-editor">
          <label class="creation-overlay__field">
            <span>角色概念</span>
            <textarea
              data-testid="creation-field-concept"
              rows="4"
              :disabled="conceptPending"
              v-model="conceptText"
            ></textarea>
          </label>
          <div
            v-if="conceptPending"
            class="creation-concept-loading"
            role="status"
            data-testid="creation-concept-loading"
          >
            <span class="creation-concept-spinner" aria-hidden="true"></span>
            <p class="creation-concept-loading-text">概念生成中，請稍候…</p>
          </div>
          </div>
        </div>

        <p v-if="formMessage" class="creation-form-message" role="alert" data-testid="creation-form-message">{{ formMessage }}</p>
        <!-- Outside the scrolling regions: errors and actions stay reachable. -->
        <footer class="creation-overlay__footer">
          <button
            type="button"
            class="ui-btn ui-btn--danger creation-reset"
            data-testid="creation-reset"
            @click="requestReset"
          >
            重設
          </button>
          <button
            v-if="mode === 'custom'"
            type="button"
            class="ui-btn ui-btn--primary creation-custom-confirm"
            data-testid="creation-submit"
            @click="confirmCustom"
          >
            確認自訂
          </button>
          <button
            v-else-if="mode === 'concept'"
            type="button"
            class="ui-btn ui-btn--primary creation-concept-apply"
            data-testid="creation-concept-submit"
            :disabled="applyFrozen"
            @click="applyConcept"
          >
            {{ conceptPending ? "生成中…" : "套用概念" }}
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

<style scoped src="./creation-overlay.css"></style>
