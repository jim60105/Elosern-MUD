<script setup>
// TitleCodexPanel (title-codex-removal): the big-window 稱號冊 rendered
// inside OverlayHost's body slot over the committed `title_codex` v1 panel.
// Design D5/D7: the window is a host, not a data source — the full-title
// preview, every row, the ★ equipment mark, and the server-computed
// `can_remove` verdict render verbatim; the client evaluates NO gate rule and
// owns no delete logic. Clicking an unlocked fixed card or an epithet row
// emits a `title.equip` intent; the 移除 button (rendered only where the
// server row says `can_remove`) opens a client-local review card whose 確認
// emits the `title.remove` intent — the rules writer re-validates both gates
// at execution, so the card carries no server state. There is no 卸裝 control
// anywhere (the equip surface is swap-only by design D8).
//
// The 「提名中」 tab presents the codex payload's pending ballot with the
// same accept/decline intents the ballot menu uses. A panel delivered in its
// unavailable form renders the registry reason line; no placeholder rows.
import { computed, ref } from "vue";

const props = defineProps({
  // The committed `title_codex` v1 panel payload (null when absent).
  codex: { type: Object, default: null },
});

const emit = defineEmits(["action"]);

const FALLBACK_REASON = "稱號冊目前無法顯示";

const available = computed(
  () => !!props.codex && props.codex.available === true,
);

const fixedRows = computed(() =>
  available.value && Array.isArray(props.codex.fixed_rows)
    ? props.codex.fixed_rows
    : [],
);
const epithetRows = computed(() =>
  available.value && Array.isArray(props.codex.epithet_rows)
    ? props.codex.epithet_rows
    : [],
);
const pendingBallot = computed(() =>
  available.value && Array.isArray(props.codex.pending_ballot)
    ? props.codex.pending_ballot
    : [],
);

// Closed category taxonomy (server enum); the tab labels are the authored
// zh-tw names for the five members.
const CATEGORY_TABS = [
  { category: "combat", label: "戰鬥" },
  { category: "spell", label: "法術" },
  { category: "explore", label: "探索" },
  { category: "guild", label: "公會" },
  { category: "romance", label: "風流韻事" },
];

// Client-local view state only: which block is open, which category tab is
// active, and which epithet row (if any) shows its removal review card.
const block = ref("fixed");
const activeCategory = ref("guild");
const confirming = ref(null);

const shownFixedRows = computed(() =>
  fixedRows.value.filter((row) => row.category === activeCategory.value),
);

const activeBlock = computed(() => {
  if (block.value === "ballot" && pendingBallot.value.length === 0) {
    return "fixed";
  }
  return block.value;
});

function selectBlock(name) {
  block.value = name;
  confirming.value = null;
}

function selectCategory(category) {
  activeCategory.value = category;
  confirming.value = null;
}

function equipFixed(row) {
  // Locked cards carry no affordance: the click target only exists for
  // unlocked rows, and the guard keeps a stale render inert.
  if (!row.unlocked) {
    return;
  }
  emit("action", {
    action_id: "title.equip",
    payload: { kind: "fixed", identifier: row.key },
  });
}

function equipEpithet(row) {
  emit("action", {
    action_id: "title.equip",
    payload: { kind: "epithet", identifier: row.display },
  });
}

function askRemove(row) {
  confirming.value = row.display;
}

function cancelRemove() {
  confirming.value = null;
}

function confirmRemove(row) {
  confirming.value = null;
  emit("action", {
    action_id: "title.remove",
    payload: { display: row.display },
  });
}

function acceptVote(index) {
  emit("action", { action_id: "title.accept", payload: { index: index + 1 } });
}

function declineBallot() {
  emit("action", { action_id: "title.decline", payload: {} });
}
</script>

<template>
  <div class="codex-panel" data-testid="title-codex-panel">
    <p
      v-if="!available"
      class="codex-panel__unavailable"
      data-testid="title-codex-unavailable"
    >
      {{ (codex && codex.reason && codex.reason.message) || FALLBACK_REASON }}
    </p>
    <template v-else>
      <header class="codex-panel__header" data-testid="title-codex-header">
        <span class="codex-panel__full-title" data-testid="title-codex-preview">
          {{ codex.full_title || "（尚無全銜）" }}
        </span>
        <span class="codex-panel__counter">
          已收集 {{ codex.unlocked }} / {{ codex.total }}
        </span>
      </header>
      <nav class="codex-panel__tabs" aria-label="稱號冊區塊">
        <button
          type="button"
          class="codex-panel__tab"
          :class="{ 'codex-panel__tab--active': activeBlock === 'fixed' }"
          data-testid="title-codex-tab-fixed"
          @click="selectBlock('fixed')"
        >
          稱號
        </button>
        <button
          type="button"
          class="codex-panel__tab"
          :class="{ 'codex-panel__tab--active': activeBlock === 'epithet' }"
          data-testid="title-codex-tab-epithet"
          @click="selectBlock('epithet')"
        >
          異名
        </button>
        <button
          v-if="pendingBallot.length > 0"
          type="button"
          class="codex-panel__tab"
          :class="{ 'codex-panel__tab--active': activeBlock === 'ballot' }"
          data-testid="title-codex-tab-ballot"
          @click="selectBlock('ballot')"
        >
          提名中
        </button>
      </nav>

      <div v-if="activeBlock === 'fixed'" class="codex-fixed">
        <div class="codex-fixed__categories" role="tablist" aria-label="稱號分類">
          <button
            v-for="tab in CATEGORY_TABS"
            :key="tab.category"
            type="button"
            class="codex-fixed__category"
            :class="{
              'codex-fixed__category--active': activeCategory === tab.category,
            }"
            :data-testid="`title-codex-category-${tab.category}`"
            @click="selectCategory(tab.category)"
          >
            {{ tab.label }}
          </button>
        </div>
        <ul class="codex-fixed__rows">
          <li
            v-for="row in shownFixedRows"
            :key="row.key"
            class="codex-card"
            :class="{ 'codex-card--locked': !row.unlocked }"
            :data-testid="`title-codex-fixed-${row.key}`"
          >
            <template v-if="row.unlocked">
              <button
                type="button"
                class="codex-card__button"
                :data-testid="`title-codex-fixed-equip-${row.key}`"
                @click="equipFixed(row)"
              >
                <span class="codex-card__name">{{ row.display }}</span>
                <span v-if="codex.equipped.fixed === row.key" class="codex-card__star"
                  >★</span
                >
                <span v-if="row.flavor" class="codex-card__flavor">{{ row.flavor }}</span>
              </button>
            </template>
            <template v-else>
              <span class="codex-card__locked" :data-testid="`title-codex-fixed-locked-${row.key}`">
                🔒 {{ row.display }}
                <span class="codex-card__hint">{{ row.hint }}</span>
              </span>
            </template>
          </li>
        </ul>
      </div>

      <div v-else-if="activeBlock === 'epithet'" class="codex-epithets">
        <p
          v-if="epithetRows.length === 0"
          class="codex-panel__empty"
          data-testid="title-codex-epithet-empty"
        >
          尚未取得任何異名。
        </p>
        <ul v-else class="codex-epithets__rows">
          <li
            v-for="(row, index) in epithetRows"
            :key="row.display"
            class="codex-epithet"
            :data-testid="`title-codex-epithet-${index}`"
          >
            <button
              type="button"
              class="codex-epithet__button"
              :data-testid="`title-codex-epithet-equip-${index}`"
              @click="equipEpithet(row)"
            >
              <span class="codex-epithet__name">{{ row.display }}</span>
              <span v-if="row.equipped" class="codex-epithet__star" data-testid="title-codex-star"
                >★</span
              >
            </button>
            <span class="codex-epithet__basis">— {{ row.basis }}</span>
            <button
              v-if="row.can_remove"
              type="button"
              class="codex-epithet__remove"
              :data-testid="`title-codex-epithet-remove-${index}`"
              @click="askRemove(row)"
            >
              移除
            </button>
            <div
              v-if="confirming === row.display"
              class="codex-removal-card"
              data-testid="title-codex-removal-card"
              role="group"
              aria-label="異名移除確認"
            >
              <p class="codex-removal-card__target">{{ row.display }}</p>
              <p class="codex-removal-card__basis">— {{ row.basis }}</p>
              <p class="codex-removal-card__warning">此操作不可恢復。</p>
              <div class="codex-removal-card__buttons">
                <button
                  type="button"
                  data-testid="title-codex-removal-confirm"
                  @click="confirmRemove(row)"
                >
                  確認移除
                </button>
                <button
                  type="button"
                  data-testid="title-codex-removal-cancel"
                  @click="cancelRemove"
                >
                  取消
                </button>
              </div>
            </div>
          </li>
        </ul>
      </div>

      <div v-else class="codex-ballot">
        <ul class="codex-ballot__rows">
          <li
            v-for="(entry, index) in pendingBallot"
            :key="index"
            class="codex-ballot__row"
            :data-testid="`title-codex-ballot-${index}`"
          >
            <span class="codex-ballot__name">{{ index + 1 }}. {{ entry.display }}</span>
            <span class="codex-ballot__basis">— {{ entry.basis }}</span>
            <button
              type="button"
              :data-testid="`title-codex-ballot-accept-${index}`"
              @click="acceptVote(index)"
            >
              接受
            </button>
          </li>
        </ul>
        <button
          type="button"
          class="codex-ballot__decline"
          data-testid="title-codex-ballot-decline"
          @click="declineBallot"
        >
          放棄提名
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.codex-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--ink, #e8e0cf);
}
.codex-panel__unavailable {
  opacity: 0.75;
  font-style: italic;
}
.codex-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  padding: 8px 10px;
  border: 1px solid rgba(232, 224, 207, 0.25);
  border-radius: 8px;
}
.codex-panel__full-title {
  font-weight: 700;
  letter-spacing: 0.04em;
}
.codex-panel__counter {
  opacity: 0.8;
  white-space: nowrap;
}
.codex-panel__tabs {
  display: flex;
  gap: 6px;
}
.codex-panel__tab {
  padding: 4px 14px;
  background: transparent;
  color: inherit;
  border: 1px solid rgba(232, 224, 207, 0.35);
  border-radius: 999px;
  cursor: pointer;
}
.codex-panel__tab--active {
  background: rgba(232, 224, 207, 0.16);
  border-color: rgba(232, 224, 207, 0.7);
}
.codex-fixed__categories {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.codex-fixed__category {
  padding: 2px 10px;
  background: transparent;
  color: inherit;
  border: 1px dashed rgba(232, 224, 207, 0.3);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9em;
}
.codex-fixed__category--active {
  border-style: solid;
  border-color: rgba(232, 224, 207, 0.75);
}
.codex-fixed__rows,
.codex-epithets__rows,
.codex-ballot__rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.codex-card,
.codex-epithet {
  border: 1px solid rgba(232, 224, 207, 0.2);
  border-radius: 8px;
  padding: 6px 10px;
}
.codex-card--locked {
  opacity: 0.65;
}
.codex-card__button,
.codex-epithet__button {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  width: 100%;
  background: transparent;
  color: inherit;
  border: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
}
.codex-card__name,
.codex-epithet__name {
  font-weight: 700;
}
.codex-card__star,
.codex-epithet__star {
  color: #e6b84c;
}
.codex-card__flavor,
.codex-card__hint,
.codex-epithet__basis {
  display: block;
  width: 100%;
  opacity: 0.75;
  font-size: 0.9em;
}
.codex-epithet {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: baseline;
}
.codex-epithet__basis {
  width: 100%;
}
.codex-epithet__remove {
  margin-left: auto;
  padding: 2px 10px;
  background: transparent;
  color: #d98c6a;
  border: 1px solid rgba(217, 140, 106, 0.6);
  border-radius: 6px;
  cursor: pointer;
}
.codex-removal-card {
  width: 100%;
  border: 1px solid rgba(217, 140, 106, 0.7);
  border-radius: 8px;
  padding: 8px 10px;
  background: rgba(217, 140, 106, 0.08);
}
.codex-removal-card__warning {
  color: #d98c6a;
  font-weight: 700;
}
.codex-removal-card__buttons {
  display: flex;
  gap: 8px;
}
.codex-removal-card__buttons button {
  padding: 3px 12px;
  background: transparent;
  color: inherit;
  border: 1px solid rgba(232, 224, 207, 0.5);
  border-radius: 6px;
  cursor: pointer;
}
.codex-panel__empty {
  opacity: 0.7;
  font-style: italic;
}
.codex-ballot__row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  border: 1px solid rgba(232, 224, 207, 0.2);
  border-radius: 8px;
  padding: 6px 10px;
}
.codex-ballot__name {
  font-weight: 700;
}
.codex-ballot__basis {
  opacity: 0.75;
  font-size: 0.9em;
}
.codex-ballot__row button,
.codex-ballot__decline {
  padding: 2px 12px;
  background: transparent;
  color: inherit;
  border: 1px solid rgba(232, 224, 207, 0.5);
  border-radius: 6px;
  cursor: pointer;
}
.codex-ballot__row button {
  margin-left: auto;
}
</style>
