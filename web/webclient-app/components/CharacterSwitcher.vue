<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

// CharacterSwitcher (MC5, multichar-05-topbar-switcher-ui):
// Mounted in TopBar.vue's top-right cluster beside the meta pill.
// Collapsed: current character's portrait thumbnail and name (width-bounded).
// Expanded: popover listing roster characters, single shared lock note,
// and trailing confirmation-gated create-character control.
// Closes only on Escape, outside pointer activation, or committed epoch change.
const props = defineProps({
  available: { type: Boolean, default: false },
  characters: { type: Array, default: () => [] },
  canCreate: { type: Boolean, default: false },
  switchLocked: { type: Boolean, default: false },
  lockReason: { type: String, default: null },
  locked: { type: Boolean, default: false },
  epoch: { type: [Number, String], default: null },
  initialExpanded: { type: Boolean, default: false },
});

const emit = defineEmits({
  "switch-character": (characterId) => typeof characterId === "number",
  "create-character": () => true,
});

const expanded = ref(props.initialExpanded);
const confirmingCreate = ref(false);
const switcherRef = ref(null);
const triggerRef = ref(null);
const cancelBtnRef = ref(null);
const confirmSubmitRef = ref(null);

const currentCharacter = computed(() => {
  if (!Array.isArray(props.characters)) return null;
  return props.characters.find((char) => char.current === true) || null;
});

const isRenderable = computed(() => {
  return props.available === true && currentCharacter.value !== null;
});

function toggleExpanded() {
  if (props.locked) return;
  expanded.value = !expanded.value;
  if (!expanded.value) {
    confirmingCreate.value = false;
  }
}

function closePopover(restoreFocus = true) {
  expanded.value = false;
  confirmingCreate.value = false;
  if (restoreFocus && triggerRef.value && typeof triggerRef.value.focus === "function") {
    triggerRef.value.focus();
  }
}

function openCreateConfirmation() {
  if (props.locked || !props.canCreate) return;
  confirmingCreate.value = true;
  nextTick(() => {
    if (confirmSubmitRef.value && typeof confirmSubmitRef.value.focus === "function") {
      confirmSubmitRef.value.focus();
    }
  });
}

function cancelCreateConfirmation() {
  confirmingCreate.value = false;
  nextTick(() => {
    const createBtn = switcherRef.value?.querySelector('[data-testid="character-create-control"]');
    if (createBtn && typeof createBtn.focus === "function") {
      createBtn.focus();
    }
  });
}

function confirmCreate() {
  if (props.locked || !props.canCreate) return;
  emit("create-character");
}

function selectCharacter(identity) {
  if (props.locked || props.switchLocked) return;
  emit("switch-character", identity);
}

function onKeydown(event) {
  if (event.key === "Escape") {
    if (confirmingCreate.value) {
      event.preventDefault();
      event.stopPropagation();
      cancelCreateConfirmation();
    } else if (expanded.value) {
      event.preventDefault();
      event.stopPropagation();
      closePopover(true);
    }
  }
}

function onDocumentPointerDown(event) {
  if (!expanded.value) return;
  if (switcherRef.value && !switcherRef.value.contains(event.target)) {
    closePopover(false);
  }
}

watch(
  () => props.epoch,
  () => {
    closePopover(false);
  },
);

onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown);
});

onUnmounted(() => {
  document.removeEventListener("pointerdown", onDocumentPointerDown);
});
</script>

<template>
  <div
    v-if="isRenderable"
    ref="switcherRef"
    class="character-switcher"
    data-testid="character-switcher"
    @keydown="onKeydown"
  >
    <button
      ref="triggerRef"
      type="button"
      class="character-switcher__pill"
      data-testid="character-switcher-trigger"
      :class="{ 'is-expanded': expanded, 'is-locked': locked }"
      :disabled="locked"
      :aria-expanded="expanded ? 'true' : 'false'"
      aria-haspopup="dialog"
      :aria-controls="expanded ? 'character-switcher-popover' : undefined"
      @click="toggleExpanded"
    >
      <span class="character-switcher__thumb-wrapper">
        <img
          v-if="currentCharacter.portrait && currentCharacter.portrait.url"
          class="character-switcher__thumb"
          :src="currentCharacter.portrait.url"
          :alt="currentCharacter.portrait.alt || currentCharacter.name"
        />
        <span
          v-else
          class="character-switcher__thumb-placeholder"
          data-testid="character-switcher-placeholder"
        >
          {{
            (currentCharacter.portrait &&
              currentCharacter.portrait.placeholder &&
              (currentCharacter.portrait.placeholder.label ||
                currentCharacter.portrait.placeholder.kind)) ||
            currentCharacter.name.slice(0, 1)
          }}
        </span>
      </span>
      <span
        class="character-switcher__name"
        data-testid="character-switcher-name"
        :title="currentCharacter.name"
      >
        {{ currentCharacter.name }}
      </span>
      <span class="character-switcher__caret" aria-hidden="true">▾</span>
    </button>

    <div
      v-if="expanded"
      id="character-switcher-popover"
      class="character-switcher__popover"
      data-testid="character-switcher-popover"
      role="dialog"
      aria-label="角色切換"
    >
      <div
        v-if="switchLocked && lockReason"
        class="character-switcher__lock-note"
        data-testid="character-switcher-lock-note"
      >
        {{ lockReason }}
      </div>

      <template v-if="!confirmingCreate">
        <div class="character-switcher__list">
          <button
            v-for="char in characters"
            :key="char.identity"
            type="button"
            class="character-switcher__row"
            :class="{
              'is-current': char.current,
              'is-pending': char.pending,
              'is-disabled': char.current || switchLocked || locked,
            }"
            :data-testid="`character-row-${char.identity}`"
            :disabled="char.current || switchLocked || locked"
            :aria-current="char.current ? 'true' : undefined"
            @click="selectCharacter(char.identity)"
          >
            <span class="character-switcher__row-thumb-wrapper">
              <img
                v-if="char.portrait && char.portrait.url"
                class="character-switcher__row-thumb"
                :src="char.portrait.url"
                :alt="char.portrait.alt || char.name"
              />
              <span
                v-else
                class="character-switcher__row-thumb-placeholder"
              >
                {{
                  (char.portrait &&
                    char.portrait.placeholder &&
                    (char.portrait.placeholder.label ||
                      char.portrait.placeholder.kind)) ||
                  char.name.slice(0, 1)
                }}
              </span>
            </span>
            <span class="character-switcher__row-name" :title="char.name">
              {{ char.name }}
            </span>
            <span
              v-if="char.pending"
              class="character-switcher__pending-badge"
              data-testid="character-pending-badge"
            >
              建立中
            </span>
            <span
              v-if="char.current"
              class="character-switcher__current-badge"
            >
              目前角色
            </span>
          </button>
        </div>

        <div class="character-switcher__create-wrapper">
          <button
            type="button"
            class="character-switcher__create-btn"
            data-testid="character-create-control"
            :class="{ 'is-disabled': !canCreate || locked }"
            :disabled="!canCreate || locked"
            @click="openCreateConfirmation"
          >
            <span class="character-switcher__create-label">＋ 新增角色</span>
            <span
              v-if="!canCreate"
              class="character-switcher__capacity-reason"
              data-testid="character-switcher-capacity-reason"
            >
              角色數量已達上限
            </span>
          </button>
        </div>
      </template>

      <div
        v-else
        class="character-switcher__confirm-panel"
        data-testid="character-create-confirm-panel"
      >
        <p
          class="character-switcher__confirm-message"
          data-testid="character-create-confirm-message"
        >
          即將離開當前角色並進入角色建立流程。
        </p>
        <div class="character-switcher__confirm-actions">
          <button
            ref="cancelBtnRef"
            type="button"
            class="character-switcher__confirm-cancel"
            data-testid="character-create-cancel"
            @click="cancelCreateConfirmation"
          >
            取消
          </button>
          <button
            ref="confirmSubmitRef"
            type="button"
            class="character-switcher__confirm-submit"
            data-testid="character-create-confirm"
            :disabled="locked || !canCreate"
            @click="confirmCreate"
          >
            確認建立
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.character-switcher {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.character-switcher__pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: var(--line);
  border-radius: 999px;
  padding: 4px 10px 4px 5px;
  box-shadow: var(--shadow);
  font-size: 11.5px;
  color: var(--paper-200);
  cursor: pointer;
  max-width: 170px;
  height: 32px;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.character-switcher__pill:hover:not(:disabled) {
  border-color: var(--gold-400);
}

.character-switcher__pill:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.character-switcher__pill.is-expanded {
  border-color: var(--gold-400);
  box-shadow: 0 0 8px rgba(217, 119, 6, 0.25);
}

.character-switcher__thumb-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--paper-800);
  border: 1px solid var(--paper-700);
  flex-shrink: 0;
}

.character-switcher__thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.character-switcher__thumb-placeholder {
  font-size: 10px;
  font-weight: 600;
  color: var(--paper-400);
  font-family: var(--f-display);
}

.character-switcher__name {
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  color: var(--paper-100);
}

.character-switcher__caret {
  font-size: 10px;
  color: var(--paper-400);
  margin-left: 2px;
}

.character-switcher__popover {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 20;
  width: 240px;
  max-height: 320px;
  overflow-y: auto;
  background: var(--panel);
  backdrop-filter: blur(12px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  padding: var(--sp-2);
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.character-switcher__lock-note {
  padding: var(--sp-2) var(--sp-3);
  font-size: 11px;
  color: var(--warn);
  background: rgba(239, 68, 68, 0.1);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(239, 68, 68, 0.2);
  text-align: center;
  font-weight: 500;
}

.character-switcher__list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.character-switcher__row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: transparent;
  color: var(--paper-200);
  font-size: 12px;
  cursor: pointer;
  text-align: left;
  transition: background 0.12s ease, border-color 0.12s ease;
}

.character-switcher__row:hover:not(:disabled) {
  background: var(--paper-800);
  border-color: var(--gold-500);
}

.character-switcher__row:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.character-switcher__row.is-current {
  background: rgba(217, 119, 6, 0.12);
  border-color: rgba(217, 119, 6, 0.35);
  color: var(--gold-300);
}

.character-switcher__row-thumb-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--paper-800);
  border: 1px solid var(--paper-700);
  flex-shrink: 0;
}

.character-switcher__row-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.character-switcher__row-thumb-placeholder {
  font-size: 10px;
  font-weight: 600;
  color: var(--paper-400);
}

.character-switcher__row-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.character-switcher__pending-badge {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.3);
  margin-left: auto;
  flex-shrink: 0;
}

.character-switcher__current-badge {
  font-size: 10px;
  color: var(--gold-400);
  font-weight: 600;
  margin-left: auto;
  flex-shrink: 0;
}

.character-switcher__create-wrapper {
  border-top: 1px solid var(--paper-800);
  margin-top: 4px;
  padding-top: 4px;
}

.character-switcher__create-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 6px 8px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}

.character-switcher__create-btn:hover:not(:disabled) {
  background: var(--paper-800);
  color: var(--gold-300);
}

.character-switcher__create-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.character-switcher__create-label {
  font-weight: 500;
}

.character-switcher__capacity-reason {
  font-size: 10.5px;
  color: var(--paper-500);
  margin-left: auto;
}

.character-switcher__confirm-panel {
  padding: var(--sp-3);
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.character-switcher__confirm-message {
  font-size: 12px;
  color: var(--paper-300);
  line-height: 1.5;
  margin: 0;
}

.character-switcher__confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--sp-2);
}

.character-switcher__confirm-cancel {
  padding: 4px 10px;
  font-size: 11.5px;
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--paper-800);
  color: var(--paper-200);
  cursor: pointer;
}

.character-switcher__confirm-submit {
  padding: 4px 10px;
  font-size: 11.5px;
  border: 1px solid var(--gold-500);
  border-radius: var(--radius-sm);
  background: var(--gold-600);
  color: #fff;
  cursor: pointer;
  font-weight: 600;
}

.character-switcher__confirm-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
