<script setup>
// One world save as a ledger row (gm-portal-s5-saves). The row is a subgrid
// of its list's columns — kind, identity, time, characters, size, actions —
// so twenty slots scan as columns; narrow viewports stack it. The kind badge
// never uses seal-red: a manual save wears a gold seal (the operator's own,
// deletable work), automatic kinds stay neutral, and a staged restore adds
// the dashed 待套用 warning. Identifiers render verbatim in mono. Deletion is
// offered for manual saves only; automatic ones say who manages them.
import { computed, useId } from "vue";
import GmError from "./GmError.vue";
import GmStatusBadge from "./GmStatusBadge.vue";
import { formatBytes, formatCreated, formatGameDate, kindInfo } from "../lib/saves.js";

const props = defineProps({
  save: { type: Object, required: true },
  // A create/restore/delete request is in flight somewhere on the page.
  locked: { type: Boolean, default: false },
  downloadState: {
    type: String,
    default: "idle",
    validator: (value) => ["idle", "busy", "done"].includes(value),
  },
  error: { type: Object, default: null },
  arrived: { type: Boolean, default: false },
  timeZone: { type: String, default: "" },
});

const emit = defineEmits(["restore", "download", "delete"]);

const labelId = `gm-save-${useId()}`;
const kind = computed(() => kindInfo(props.save.kind));
const gameDate = computed(() => formatGameDate(props.save.clock));
const created = computed(() =>
  formatCreated(props.save.created_at, props.timeZone ? { timeZone: props.timeZone } : {}),
);
const players = computed(() => (Array.isArray(props.save.players) ? props.save.players : []));
const shownPlayers = computed(() => players.value.slice(0, 2));
const morePlayers = computed(() => players.value.slice(2));
const downloadLabel = computed(
  () => ({ idle: "下載", busy: "下載中…", done: "已下載 ✓" })[props.downloadState],
);
</script>

<template>
  <li
    class="gm-save-slot"
    :class="{ 'is-pending': save.pending, 'gm-arrived': arrived }"
    :data-save="save.id"
    :data-kind="save.kind"
  >
    <article class="gm-save-slot__row" :aria-labelledby="labelId">
      <div class="gm-save-slot__kind">
        <span class="gm-visually-hidden">種類：</span>
        <span
          v-if="save.kind === 'manual'"
          class="status-marker gm-save-slot__badge gm-save-slot__badge--manual"
        >{{ kind.label }}</span>
        <GmStatusBadge
          v-else
          :status="kind.status"
          :label="kind.label"
          class="gm-save-slot__badge"
          :class="`gm-save-slot__badge--${save.kind}`"
        />
        <GmStatusBadge v-if="save.pending" status="warn" label="待套用" class="gm-save-slot__badge" />
      </div>

      <div class="gm-save-slot__identity">
        <h3 :id="labelId" class="gm-save-slot__label" :class="{ 'is-unnamed': !save.label }">
          {{ save.label || "未命名存檔" }}
        </h3>
        <code class="gm-save-slot__id" :title="save.id">{{ save.id }}</code>
      </div>

      <div class="gm-save-slot__time">
        <span class="gm-visually-hidden">建立時間：</span>
        <time :datetime="save.created_at" :title="save.created_at">{{ created }}</time>
        <span class="gm-save-slot__game">
          <span class="gm-visually-hidden">遊戲內時間：</span>
          <template v-if="gameDate">
            {{ gameDate }}
            <span class="gm-chip">tick {{ save.clock.tick }}</span>
          </template>
          <span v-else class="gm-muted">無世界時鐘</span>
        </span>
      </div>

      <div class="gm-save-slot__players">
        <span class="gm-visually-hidden">玩家角色：</span>
        <ul v-if="players.length" class="gm-save-slot__people">
          <li v-for="(player, index) in shownPlayers" :key="index">
            <span class="gm-save-slot__name">{{ player.name }}</span>
            <span class="gm-save-slot__at" aria-hidden="true">@</span>
            <span class="gm-visually-hidden">位於</span>
            <span v-if="player.location" class="gm-chip">{{ player.location }}</span>
            <span v-else class="gm-muted">（無位置）</span>
          </li>
          <li v-if="morePlayers.length">
            <details class="gm-save-slot__more">
              <summary>另 {{ morePlayers.length }} 位</summary>
              <ul class="gm-save-slot__people">
                <li v-for="(player, index) in morePlayers" :key="index">
                  <span class="gm-save-slot__name">{{ player.name }}</span>
                  <span class="gm-save-slot__at" aria-hidden="true">@</span>
                  <span v-if="player.location" class="gm-chip">{{ player.location }}</span>
                </li>
              </ul>
            </details>
          </li>
        </ul>
        <span v-else class="gm-muted">無玩家角色</span>
      </div>

      <div class="gm-save-slot__size">
        <span class="gm-visually-hidden">大小：</span>
        <span class="gm-num">{{ formatBytes(save.size_bytes) }}</span>
        <span class="gm-save-slot__files">{{ save.file_count }} 檔</span>
      </div>

      <div class="gm-save-slot__actions">
        <button
          type="button"
          class="ui-btn ui-btn--sm"
          data-action="restore"
          :aria-disabled="locked || save.pending ? 'true' : null"
          :aria-describedby="labelId"
          @click="!(locked || save.pending) && emit('restore', save)"
        >
          讀取
        </button>
        <button
          type="button"
          class="ui-btn ui-btn--ghost ui-btn--sm"
          data-action="download"
          :aria-disabled="downloadState === 'busy' ? 'true' : null"
          :aria-describedby="labelId"
          @click="downloadState !== 'busy' && emit('download', save)"
        >
          {{ downloadLabel }}
        </button>
        <button
          v-if="save.deletable"
          type="button"
          class="ui-btn ui-btn--danger ui-btn--sm gm-save-slot__delete"
          data-action="delete"
          :aria-disabled="locked || save.pending ? 'true' : null"
          :aria-describedby="labelId"
          @click="!(locked || save.pending) && emit('delete', save)"
        >
          刪除
        </button>
        <span v-else class="gm-save-slot__managed" title="自動存檔由保留規則清理，不能手動刪除">保留規則<br>自動清理</span>
      </div>

      <div v-if="error" class="gm-save-slot__error">
        <GmError compact :title="error.title" :message="error.message" :code="error.code" />
      </div>
    </article>
  </li>
</template>

<style scoped>
.gm-save-slot {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  position: relative;
  border-bottom: 1px dashed var(--ink-700);
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.gm-save-slot:last-child {
  border-bottom: 0;
}

.gm-save-slot:hover {
  background: var(--ink-820);
}

.gm-save-slot.is-pending {
  box-shadow: inset 2px 0 0 var(--warn);
  background: color-mix(in srgb, var(--warn) 5%, transparent);
}

.gm-save-slot__row {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  align-items: start;
  column-gap: var(--sp-5);
  row-gap: var(--sp-2);
  padding: var(--sp-4) var(--sp-5);
}

.gm-save-slot__kind {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--sp-1);
  padding-top: 2px;
}

.gm-save-slot__badge {
  font-size: var(--text-xs);
}

/* A manual save: the operator's deliberate work, sealed in gold. */
.gm-save-slot__badge--manual {
  color: var(--gold-400);
  border-color: var(--gold-500);
  background: color-mix(in srgb, var(--gold-500) 8%, transparent);
  white-space: nowrap;
  line-height: 1.4;
}

.gm-save-slot__badge--manual::before {
  content: "◆" / "";
  font-size: 0.8em;
}

/* Automatic kinds stay neutral; the glyph and border style tell them apart
   without color (the text label carries the meaning). */
.gm-save-slot__kind .gm-save-slot__badge--auto_restore::before {
  content: "↺" / "";
}

.gm-save-slot__kind .gm-save-slot__badge--auto_intervention {
  border-style: dashed;
}

.gm-save-slot__kind .gm-save-slot__badge--auto_intervention::before {
  content: "⌁" / "";
}

.gm-save-slot__identity,
.gm-save-slot__time,
.gm-save-slot__size {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.gm-save-slot__label {
  display: -webkit-box;
  overflow: hidden;
  font-family: var(--f-sans);
  font-size: var(--text-md);
  font-weight: 600;
  line-height: 1.4;
  color: var(--paper-50);
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.gm-save-slot__label.is-unnamed {
  font-weight: 500;
  color: var(--paper-500);
}

.gm-save-slot__id {
  overflow: hidden;
  font-size: var(--text-xs);
  color: var(--paper-400);
  text-overflow: ellipsis;
  white-space: nowrap;
  user-select: all;
}

.gm-save-slot__time time {
  font-family: var(--f-mono);
  font-variant-numeric: tabular-nums;
  font-size: var(--text-sm);
  color: var(--paper-200);
}

.gm-save-slot__game {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--text-sm);
  color: var(--paper-400);
}

.gm-save-slot__players {
  min-width: 0;
  font-size: var(--text-sm);
}

.gm-save-slot__people {
  display: grid;
  gap: var(--sp-1);
  padding: 0;
  list-style: none;
}

.gm-save-slot__people > li {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  min-width: 0;
}

.gm-save-slot__name {
  overflow: hidden;
  color: var(--paper-100);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-save-slot__at {
  color: var(--paper-700);
}

.gm-save-slot__more summary {
  width: fit-content;
  color: var(--gold-400);
  cursor: pointer;
  border-radius: var(--radius-sm);
}

.gm-save-slot__more[open] summary {
  margin-bottom: var(--sp-1);
}

.gm-save-slot__size {
  justify-items: end;
}

.gm-save-slot__files {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

/* Fixed action slots, so 讀取 and 下載 line up down the whole ledger whether
   the third slot holds 刪除 or the retention note. */
.gm-save-slot__actions {
  display: grid;
  grid-template-columns: auto auto 6.5em;
  align-items: center;
  justify-content: end;
  gap: var(--sp-2);
}

.gm-save-slot__delete {
  justify-self: end;
  margin-left: var(--sp-2);
}

.gm-save-slot__managed {
  justify-self: end;
  margin-left: var(--sp-2);
  font-size: var(--text-xs);
  line-height: 1.35;
  color: var(--paper-500);
  text-align: end;
}

.gm-save-slot__error {
  grid-column: 1 / -1;
}

.gm-save-slot :is(button, summary):focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.gm-save-slot__actions .ui-btn[aria-disabled="true"] {
  opacity: 0.45;
  cursor: not-allowed;
}

/* Narrow: the subgrid gives way to a stacked ledger card. */
@container gm-saves (max-width: 959px) {
  .gm-save-slot,
  .gm-save-slot__row {
    display: block;
  }

  .gm-save-slot__row {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    gap: var(--sp-3);
  }

  .gm-save-slot__kind {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .gm-save-slot__time,
  .gm-save-slot__players,
  .gm-save-slot__size,
  .gm-save-slot__actions {
    grid-column: 1 / -1;
  }

  .gm-save-slot__size {
    display: flex;
    gap: var(--sp-3);
    justify-items: start;
  }

  .gm-save-slot__actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .gm-save-slot__delete,
  .gm-save-slot__managed {
    margin-left: var(--sp-4);
    text-align: start;
  }

  .gm-save-slot__actions .ui-btn {
    min-height: 40px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .gm-save-slot {
    transition: none;
  }
}
</style>
