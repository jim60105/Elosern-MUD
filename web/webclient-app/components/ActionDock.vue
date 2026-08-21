<script setup>
// ActionDock (B2 action family): the non-closable bottom action surface —
// the preserved `#action-dock` composite element and documented focus target
// (Phase-0 audit §2.3, PRESERVE-SAME-HOOK), rendered as the framed dock with
// the guidance line (per-surface prefix plus the shared shortcut legend) and
// the default slot carrying the active menu frame (a DockMenu — a root menu,
// a sub-menu, or a target selection frame).
//
// The `context_actions` v5 `suggestions` slice renders below the menu frame
// exactly as the legacy dock section did: `generating` is one muted line,
// `ready` is the card row plus the shared dismiss control, `degraded` adds
// the muted unavailability note (zero cards render the empty-state line),
// and `unavailable` renders nothing at all. Card activation and dismiss
// emit the exact OOB action intent (`action` event) — one card renderer
// shared with the narrative choice-point.
import ChoiceCardRow from "./ChoiceCardRow.vue";

const props = defineProps({
  // The contextual dock mode slice (exploration/combat/...), rendered as
  // the preserved `#action-dock` data-mode attribute.
  mode: { type: String, default: "exploration" },
  // The per-surface guidance prefix (legacy dock chrome); the shared
  // shortcut legend is always appended.
  guidancePrefix: { type: String, default: null },
  // The committed `context_actions.suggestions` envelope, or null.
  suggestions: { type: Object, default: null },
});

const emit = defineEmits(["action"]);

const LEGEND = "方向鍵選擇・Enter 確認・Esc 返回・/ 開啟指令";
const SUGGESTION_STATUSES = ["generating", "ready", "degraded"];

const guidanceNote = props.guidancePrefix
  ? `${props.guidancePrefix}　${LEGEND}`
  : LEGEND;

const status = props.suggestions ? props.suggestions.status : null;
const showsSection = SUGGESTION_STATUSES.includes(status);
const cards =
  props.suggestions && Array.isArray(props.suggestions.cards)
    ? props.suggestions.cards
    : [];
</script>

<template>
  <section
    id="action-dock"
    class="action-dock"
    tabindex="0"
    :data-mode="mode"
    data-testid="action-dock"
  >
    <p class="action-dock__guidance" data-testid="action-dock-guidance">
      <span class="action-dock__guidance-note" data-testid="action-dock-description">
        {{ guidanceNote }}
      </span>
    </p>

    <slot />

    <div
      v-if="showsSection"
      class="suggestions-section"
      role="region"
      aria-label="AI 建議"
      data-testid="suggestions-section"
    >
      <div
        v-if="status === 'generating'"
        class="suggestions-generating"
        data-testid="suggestions-generating"
      >AI 正在構思建議…</div>
      <template v-else>
        <div class="suggestions-header">
          <span class="suggestions-title">AI 建議</span>
          <button
            type="button"
            class="suggestions-dismiss"
            data-testid="suggestions-dismiss"
            @click="emit('action', { action_id: 'options.dismiss', payload: {} })"
          >✕ 清除建議</button>
        </div>
        <div
          v-if="status === 'degraded'"
          class="suggestions-note"
          data-testid="suggestions-note"
        >AI 建議目前不可用</div>
        <div
          v-if="status === 'degraded' && cards.length === 0"
          class="suggestions-empty"
          data-testid="suggestions-empty"
        >現在沒有什麼值得做的動作</div>
        <ChoiceCardRow
          v-if="cards.length > 0"
          :cards="cards"
          @action="(intent) => emit('action', intent)"
        />
      </template>
    </div>
  </section>
</template>

<style scoped>
.action-dock {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  box-sizing: border-box;
  padding: var(--sp-3) var(--sp-4);
  background: var(--panel);
  border-top: 1px solid var(--seal-600);
  font-family: var(--f-sans);
}

.action-dock__guidance {
  margin: 0;
  color: var(--paper-500);
  font-size: 11px;
  line-height: 1.4;
}

.suggestions-section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  margin-top: var(--sp-1);
  padding-top: var(--sp-2);
  border-top: 1px solid var(--ink-700);
}

.suggestions-generating {
  color: var(--paper-500);
  font-size: 0.9em;
}

.suggestions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
}

.suggestions-title {
  color: var(--paper-300);
  font-size: 0.8em;
  letter-spacing: 0.08em;
}

.suggestions-note,
.suggestions-empty {
  color: var(--paper-500);
  font-size: 0.85em;
}

.suggestions-dismiss {
  padding: 2px var(--sp-2);
  color: var(--paper-300);
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 0.8em;
  cursor: pointer;
}
</style>
