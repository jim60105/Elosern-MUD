<script setup>
// Approved visual prototype of the quest drawer redesign
// (docs/superpowers/specs/2026-10-09-quest-drawer-redesign-design.md).
// Reference only: self-contained mock data, not wired to any payload.
import { computed, ref, watch } from "vue";
import { BOARD, BOOK, GRADES, PLAYER_RANK } from "./prototype-data.js";

const props = defineProps({
  initialTab: { type: String, default: "book" },
  atCounter: { type: Boolean, default: true },
});

const ICONS = {
  book: "M6 3.5h11a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2zM6 3.5a2 2 0 0 0-2 2V8h2M9.5 8.5h6M9.5 12h6M9.5 15.5h3.5",
  guild: "M12 2.8 4.5 5.6v6c0 4.8 3.2 8 7.5 9.6 4.3-1.6 7.5-4.8 7.5-9.6v-6zM12 7v9.5M8.5 10.5h7",
  in_progress: "M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9M10 18.5h4",
  completed: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8 12.4l2.8 2.8 5.4-5.6",
  failed: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9 9l6 6M15 9l-6 6",
  討伐: "M19.5 4.5v3.2L10.4 16.8 7.2 13.6l9.1-9.1zM5.3 11.7l7 7M8.8 15.2l-4.3 4.3",
  護衛: "M12 3 5 6v5.5c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z",
  探索: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM15.5 8.5l-2 5-5 2 2-5z",
  採集: "M6 18c0-7 5-12 13-12 0 8-5 13-12 13M6 18l7-7",
  緊急: "M12 3 2.5 20h19zM12 9.5v5M12 17.2v.3",
  track: "M6.5 21V4h11l-2.4 4 2.4 4h-11",
  coin: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  merit: "M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z",
  item: "M9 3h6M10 3v4.5L6 15a4 4 0 0 0 3.6 6h4.8A4 4 0 0 0 18 15l-4-7.5V3",
  hourglass: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2",
  close: "M6 6l12 12M18 6 6 18",
  quests: "M6 3h12v2h2v5h-2v9a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V5H5V3h1z",
};

const STATE_TABS = [
  { key: "in_progress", label: "進行中" },
  { key: "completed", label: "已完成" },
  { key: "failed", label: "失敗" },
];

const top = ref(props.atCounter ? props.initialTab : "book");
const stateTab = ref("in_progress");
const gradeTab = ref(PLAYER_RANK.rank);
const selectedId = ref(null);

const countByState = computed(() =>
  Object.fromEntries(STATE_TABS.map((t) => [t.key, BOOK.filter((q) => q.state === t.key).length])),
);
const countByGrade = computed(() =>
  Object.fromEntries(GRADES.map((g) => [g, BOARD.filter((q) => q.grade === g).length])),
);

const list = computed(() =>
  top.value === "book"
    ? BOOK.filter((q) => q.state === stateTab.value)
    : BOARD.filter((q) => q.grade === gradeTab.value),
);

watch(
  list,
  (rows) => {
    if (!rows.some((r) => r.id === selectedId.value)) selectedId.value = rows[0]?.id ?? null;
  },
  { immediate: true },
);

const selected = computed(() => list.value.find((r) => r.id === selectedId.value) ?? null);
const isBoard = computed(() => top.value === "counter");

const gradeIndex = (g) => GRADES.indexOf(g);
const gradeLocked = (g) => gradeIndex(g) > gradeIndex(PLAYER_RANK.rank);

const pct = (q) => Math.round((Math.min(q.progress ?? 0, q.target) / q.target) * 100);
const fmt = (n) => new Intl.NumberFormat("zh-TW").format(n);

const meterPct = computed(() =>
  Math.round((Math.min(PLAYER_RANK.merit, PLAYER_RANK.next_threshold) / PLAYER_RANK.next_threshold) * 1000) / 10,
);

const armedAbandon = ref(false);
watch(selectedId, () => (armedAbandon.value = false));
</script>

<template>
  <section class="qd" aria-label="任務">
    <!-- ── Header: title + first-level icon tabs ─────────────────────── -->
    <header class="qd-head">
      <span class="qd-head__seal" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path :d="ICONS.quests" /></svg>
      </span>
      <h2 class="qd-head__title">任務</h2>

      <div class="qd-top" role="tablist" aria-label="任務分類">
        <button
          v-for="t in [{ key: 'book', label: '任務簿', icon: 'book' }, { key: 'counter', label: '公會櫃檯', icon: 'guild' }]"
          :key="t.key"
          type="button"
          role="tab"
          class="qd-top__tab"
          :class="{ 'is-active': top === t.key }"
          :aria-selected="top === t.key"
          :aria-label="t.label"
          :data-tip="t.key === 'counter' && !atCounter ? '公會櫃檯 · 需在公會職員面前' : t.label"
          :disabled="t.key === 'counter' && !atCounter"
          @click="top = t.key"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS[t.icon]" /></svg>
        </button>
      </div>

      <button type="button" class="qd-head__close" aria-label="關閉">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS.close" /></svg>
      </button>
    </header>

    <div class="qd-body">
      <!-- ── Second-level rail ─────────────────────────────────────────── -->
      <nav class="qd-rail" role="tablist" :aria-label="isBoard ? '委託難度' : '任務狀態'" aria-orientation="vertical">
        <template v-if="!isBoard">
          <button
            v-for="t in STATE_TABS"
            :key="t.key"
            type="button"
            role="tab"
            class="qd-rail__tab"
            :class="[{ 'is-active': stateTab === t.key }, `qd-rail__tab--${t.key}`]"
            :aria-selected="stateTab === t.key"
            :aria-label="`${t.label}（${countByState[t.key]}）`"
            :data-tip="t.label"
            @click="stateTab = t.key"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS[t.key]" /></svg>
            <span v-if="countByState[t.key]" class="qd-rail__count" :class="{ 'qd-rail__count--hot': t.key === 'completed' && atCounter && BOOK.some((q) => q.state === 'completed' && q.turnin) }">{{ countByState[t.key] }}</span>
          </button>
        </template>
        <template v-else>
          <button
            v-for="g in GRADES"
            :key="g"
            type="button"
            role="tab"
            class="qd-rail__tab qd-rail__tab--grade"
            :class="{
              'is-active': gradeTab === g,
              'is-empty': !countByGrade[g],
              'is-mine': g === PLAYER_RANK.rank,
              'is-locked': gradeLocked(g),
            }"
            :aria-selected="gradeTab === g"
            :aria-label="`${g} 級委託（${countByGrade[g]}）`"
            :data-tip="g === PLAYER_RANK.rank ? `${g} 級 · 你的等級` : gradeLocked(g) ? `${g} 級 · 尚未開放` : `${g} 級`"
            @click="gradeTab = g"
          >
            <span class="qd-gem" :class="`qd-gem--${g}`" aria-hidden="true"><span>{{ g }}</span></span>
            <span v-if="countByGrade[g]" class="qd-rail__count">{{ countByGrade[g] }}</span>
          </button>
        </template>
      </nav>

      <!-- ── List column ────────────────────────────────────────────── -->
      <div class="qd-list">
        <!-- Counter: the existing rank card, kept as-is (compact host). -->
        <section v-if="isBoard" class="qd-rank" aria-label="公會等級">
          <div class="qd-rank__head">
            <span class="qd-rank__crest" aria-hidden="true"><span>{{ PLAYER_RANK.rank }}</span></span>
            <div class="qd-rank__text">
              <p class="qd-rank__level">等級 <span>{{ PLAYER_RANK.rank }}</span></p>
              <p class="qd-rank__next">下一階 <span>{{ PLAYER_RANK.next_rank }}</span> 級</p>
            </div>
            <p class="qd-rank__merit"><span>累積功績</span><b>{{ fmt(PLAYER_RANK.merit) }}</b></p>
          </div>
          <div class="qd-rank__meter"><span :style="{ width: `${meterPct}%` }"></span></div>
          <div class="qd-rank__foot">
            <span>◇ 功績未達標 · 尚差 {{ fmt(PLAYER_RANK.next_threshold - PLAYER_RANK.merit) }}</span>
            <span class="qd-rank__scale">升等門檻 {{ fmt(PLAYER_RANK.next_threshold) }}</span>
          </div>
          <button type="button" class="qd-rank__exam">預約升等考核 <small>→ {{ PLAYER_RANK.next_rank }} 級</small></button>
        </section>

        <header class="qd-list__head">
          <span class="qd-list__kicker">
            {{ isBoard ? `${gradeTab} 級委託` : STATE_TABS.find((t) => t.key === stateTab).label }}
          </span>
          <span class="qd-list__rule" aria-hidden="true"></span>
          <span class="qd-list__n">{{ list.length }}</span>
        </header>

        <ul v-if="list.length" class="qd-rows" role="listbox" :aria-label="isBoard ? '任務板' : '任務'">
          <li
            v-for="q in list"
            :key="q.id"
            role="option"
            tabindex="0"
            class="qd-row"
            :class="{ 'is-selected': q.id === selectedId, [`is-${q.state}`]: q.state }"
            :aria-selected="q.id === selectedId"
            @click="selectedId = q.id"
            @keydown.enter="selectedId = q.id"
          >
            <span class="qd-row__cat" aria-hidden="true">
              <svg viewBox="0 0 24 24"><path :d="ICONS[q.category]" /></svg>
            </span>
            <span class="qd-row__main">
              <span class="qd-row__name">
                {{ q.name }}
                <svg v-if="q.tracked" class="qd-row__pin" viewBox="0 0 24 24" aria-label="追蹤中"><path :d="ICONS.track" /></svg>
              </span>
              <span v-if="!isBoard && q.state === 'in_progress'" class="qd-row__prog">
                <span class="qd-row__bar"><span :style="{ width: `${pct(q)}%` }"></span></span>
                <span class="qd-row__num">{{ q.progress }}/{{ q.target }}</span>
              </span>
              <span v-else class="qd-row__sub">{{ q.issuer.kind === 'guild' ? '公會委託' : q.issuer.label }}<template v-if="q.deadline"> · {{ q.deadline }}</template></span>
            </span>
            <span class="qd-gem qd-gem--sm" :class="`qd-gem--${q.grade}`" aria-label="等級">
              <span>{{ q.grade }}</span>
            </span>
          </li>
        </ul>
        <div v-else class="qd-empty">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS.book" /></svg>
          <p>{{ isBoard ? (gradeLocked(gradeTab) ? `${gradeTab} 級委託要等你的公會等級提升後才會開放。` : `目前沒有 ${gradeTab} 級委託。`) : "這裡還沒有任務。" }}</p>
        </div>
      </div>

      <!-- ── Detail column ──────────────────────────────────────────── -->
      <article v-if="selected" class="qd-detail" :key="selected.id">
        <div class="qd-detail__scroll">
          <header class="qd-hero">
            <span class="qd-ribbon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS[selected.category]" /></svg>
              {{ selected.category }}{{ selected.issuer.kind === 'guild' ? '委託' : ' · 私人委託' }}
            </span>
            <h3 class="qd-hero__title">{{ selected.name }}</h3>
            <p class="qd-hero__objective">{{ selected.objective }}</p>
            <p v-if="selected.variants" class="qd-hero__variants">{{ selected.variants }}</p>

            <span v-if="selected.grade" class="qd-gem qd-gem--lg qd-hero__gem" :class="`qd-gem--${selected.grade}`" aria-label="等級">
              <span>{{ selected.grade }}</span>
            </span>
            <span v-if="selected.state === 'completed'" class="qd-stamp">達成</span>
            <span v-else-if="selected.state === 'failed'" class="qd-stamp qd-stamp--failed">失敗</span>
          </header>

          <!-- Progress (book, in progress): pips for small counts. -->
          <section v-if="!isBoard && selected.state === 'in_progress'" class="qd-progress" aria-label="進度">
            <div class="qd-progress__meta">
              <span>階段 {{ selected.stage }} / {{ selected.stages }}</span>
              <b>{{ selected.progress }}<small> / {{ selected.target }}</small></b>
            </div>
            <div v-if="selected.target <= 12" class="qd-pips">
              <span v-for="i in selected.target" :key="i" :class="{ 'is-on': i <= selected.progress }"></span>
            </div>
            <div v-else class="qd-bar"><span :style="{ width: `${pct(selected)}%` }"></span></div>
          </section>

          <div class="qd-cond">
            <section v-if="isBoard || selected.rationale" class="qd-cond__cell">
              <h4 class="qd-label">{{ isBoard ? '接取條件' : '評價' }}</h4>
              <p v-if="isBoard" class="qd-cond__line">{{ selected.grade }} 級以上</p>
              <p v-if="selected.rationale" class="qd-cond__text">{{ selected.rationale }}</p>
            </section>
            <section class="qd-cond__cell">
              <h4 class="qd-label">期限</h4>
              <p class="qd-cond__line">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS.hourglass" /></svg>
                {{ selected.deadline ?? '無期限' }}
              </p>
              <p class="qd-cond__text">{{ selected.deadline ? '超過期限即判定失敗。' : '這份委託沒有時間限制。' }}</p>
            </section>
          </div>

          <section class="qd-client">
            <h4 class="qd-label">委託人</h4>
            <p class="qd-client__name">{{ selected.issuer.label }}</p>
            <p v-if="selected.flavor" class="qd-client__letter">{{ selected.flavor }}</p>
            <p v-else class="qd-client__letter qd-muted">委託人沒有留下說明。</p>
            <svg class="qd-client__mark" viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS.guild" /></svg>
          </section>

          <section class="qd-reward" aria-label="報酬">
            <h4 class="qd-label">報酬</h4>
            <ul class="qd-reward__list">
              <li>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS.coin" /></svg>
                <b>{{ fmt(selected.reward.copper) }}</b><span>銅</span>
              </li>
              <li v-if="selected.reward.merit">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS.merit" /></svg>
                <b>{{ fmt(selected.reward.merit) }}</b><span>功績</span>
              </li>
              <li v-for="it in selected.reward.items" :key="it.name">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS.item" /></svg>
                <span>{{ it.name }}</span><b>× {{ it.qty }}</b>
              </li>
            </ul>
            <p class="qd-reward__settle">{{ selected.settlement === 'counter' ? '回公會櫃檯領取' : '完成即結算' }}</p>
          </section>
        </div>

        <!-- ── Action bar ─────────────────────────────────────────────── -->
        <footer class="qd-actions">
          <template v-if="isBoard">
            <p v-if="!selected.accept.enabled" class="qd-actions__why">{{ selected.accept.reason }}</p>
            <button type="button" class="qd-btn qd-btn--primary" :disabled="!selected.accept.enabled">接取委託</button>
          </template>
          <template v-else-if="selected.state === 'in_progress'">
            <template v-if="armedAbandon">
              <p class="qd-actions__why qd-actions__why--danger">放棄後任務會判定失敗，且無法回復。</p>
              <button type="button" class="qd-btn" @click="armedAbandon = false">取消</button>
              <button type="button" class="qd-btn qd-btn--danger">確認放棄</button>
            </template>
            <template v-else>
              <button v-if="selected.abandon && atCounter" type="button" class="qd-btn qd-btn--ghost" @click="armedAbandon = true">放棄委託</button>
              <span class="qd-actions__spacer"></span>
              <button type="button" class="qd-btn" :class="{ 'is-on': selected.tracked }" :aria-pressed="selected.tracked">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="ICONS.track" /></svg>
                {{ selected.tracked ? '追蹤中' : '追蹤' }}
              </button>
            </template>
          </template>
          <template v-else-if="selected.state === 'completed'">
            <button v-if="atCounter && selected.turnin" type="button" class="qd-btn qd-btn--primary">交付委託</button>
            <p v-else-if="selected.claimed" class="qd-actions__why">報酬已領取</p>
            <p v-else class="qd-actions__why">回到公會櫃檯即可交付並領取報酬。</p>
          </template>
          <template v-else>
            <p class="qd-actions__why">此委託已失敗，沒有報酬。</p>
          </template>
        </footer>
      </article>
      <div v-else class="qd-detail qd-detail--empty"></div>
    </div>
  </section>
</template>

<style scoped>
/* ── Frame ─────────────────────────────────────────────────────────── */
.qd {
  --qd-line: rgba(185, 154, 96, 0.28);
  --qd-line-soft: rgba(185, 154, 96, 0.14);
  --qd-rail-w: calc(68px * var(--ui-scale));
  position: relative;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  box-sizing: border-box;
  color: var(--paper-200);
  font-family: var(--f-sans);
  background:
    radial-gradient(120% 80% at 70% 0%, rgba(185, 154, 96, 0.07), transparent 60%),
    linear-gradient(180deg, #16181dfa, #0e1014fa);
  border: 1px solid rgba(185, 154, 96, 0.45);
  border-radius: var(--radius);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55), inset 0 0 0 1px rgba(0, 0, 0, 0.6);
  overflow: hidden;
}
svg { fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linejoin: round; stroke-linecap: round; }

/* ── Header ────────────────────────────────────────────────────────── */
.qd-head {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-5) 0;
  border-bottom: 1px solid var(--qd-line);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.25), transparent);
}
.qd-head__seal {
  display: grid; place-items: center;
  width: calc(38px * var(--ui-scale)); height: calc(38px * var(--ui-scale));
  margin-bottom: var(--sp-3);
  color: var(--gold-400);
  border: 1px solid var(--gold-600);
  border-radius: 50%;
  background: radial-gradient(circle at 50% 35%, rgba(185, 154, 96, 0.18), transparent 70%);
}
.qd-head__seal svg { width: 55%; height: 55%; }
.qd-head__title {
  margin: 0 var(--sp-4) var(--sp-3) 0;
  color: var(--paper-50);
  font: var(--text-2xl) var(--f-display);
  letter-spacing: 0.08em;
}
.qd-head__close {
  display: grid; place-items: center;
  width: calc(36px * var(--ui-scale)); height: calc(36px * var(--ui-scale));
  margin-bottom: var(--sp-3);
  color: var(--paper-400);
  background: transparent;
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.qd-head__close svg { width: 55%; height: 55%; }
.qd-head__close:hover { color: var(--paper-50); border-color: var(--gold-500); }

/* First-level tabs: icon + small caption under; the active tab sits on
   the header rule with a seal-red underline and a gold glow. */
.qd-top { display: flex; align-self: end; gap: var(--sp-1); }
.qd-top__tab {
  position: relative;
  display: grid; justify-items: center; gap: 2px;
  min-width: calc(64px * var(--ui-scale));
  padding: var(--sp-2) var(--sp-3) var(--sp-3);
  color: var(--paper-500);
  background: transparent;
  border: 0;
  cursor: pointer;
  transition: color var(--motion-fast) ease;
}
.qd-top [data-tip]::after { left: 50% !important; top: calc(100% + 8px) !important; transform: translateX(-50%) !important; }
.qd-top__tab svg { width: calc(28px * var(--ui-scale)); height: calc(28px * var(--ui-scale)); }
.qd-top__label { font-size: var(--text-xs); letter-spacing: 0.1em; }
.qd-top__tab::before {
  content: ""; position: absolute; left: 18%; right: 18%; bottom: -1px; height: 2px;
  background: transparent; border-radius: 2px;
}
.qd-top__tab:hover:not(:disabled) { color: var(--paper-100); }
.qd-top__tab.is-active { color: var(--gold-300); }
.qd-top__tab.is-active svg { filter: drop-shadow(0 0 6px rgba(228, 200, 142, 0.45)); }
.qd-top__tab.is-active::before { background: var(--seal-500); box-shadow: 0 0 10px var(--seal-glow); }
.qd-top__tab:disabled { opacity: 0.35; cursor: not-allowed; }
.qd-top__tab:focus-visible, .qd-rail__tab:focus-visible, .qd-row:focus-visible, .qd-btn:focus-visible {
  outline: none; box-shadow: var(--focus);
}

/* ── Body grid ─────────────────────────────────────────────────────── */
.qd-body {
  display: grid;
  grid-template-columns: var(--qd-rail-w) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
  min-height: 0;
}

/* Second-level rail: vertical icon tabs; the active one "opens" into
   the list column (no right border, list background). */
.qd-rail {
  display: flex; flex-direction: column; gap: var(--sp-2);
  padding: var(--sp-4) 0 var(--sp-4) var(--sp-2);
  background: rgba(0, 0, 0, 0.28);
  border-right: 1px solid var(--qd-line);
}
.qd-rail__tab {
  position: relative;
  display: grid; place-items: center;
  height: calc(58px * var(--ui-scale));
  margin-right: -1px;
  color: var(--paper-500);
  background: transparent;
  border: 1px solid transparent;
  border-right: 0;
  border-radius: var(--radius) 0 0 var(--radius);
  cursor: pointer;
  transition: color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}
.qd-rail__tab svg { width: calc(26px * var(--ui-scale)); height: calc(26px * var(--ui-scale)); }
.qd-rail__tab:hover { color: var(--paper-100); background: rgba(255, 255, 255, 0.03); }
.qd-rail__tab.is-active {
  color: var(--gold-300);
  background: #15171c;
  border-color: var(--qd-line);
}
.qd-rail__tab.is-active::before {
  content: ""; position: absolute; left: -1px; top: 22%; bottom: 22%; width: 3px;
  background: var(--seal-500); border-radius: 0 2px 2px 0; box-shadow: 0 0 8px var(--seal-glow);
}
.qd-rail__tab--completed.is-active { color: var(--gold-300); }
.qd-rail__tab--failed.is-active { color: var(--paper-200); }
.qd-rail__count {
  position: absolute; top: calc(6px * var(--ui-scale)); right: calc(6px * var(--ui-scale));
  min-width: calc(18px * var(--ui-scale)); height: calc(18px * var(--ui-scale));
  padding: 0 4px; box-sizing: border-box;
  display: grid; place-items: center;
  color: var(--paper-50);
  font: 600 calc(12px * var(--ui-scale)) / 1 var(--f-num);
  color: var(--gold-300);
  background: #0b0d10;
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-pill);
}
.qd-rail__count--hot { color: var(--paper-50); background: var(--seal-600); border-color: #0b0d10; box-shadow: 0 0 8px var(--seal-glow); }
.qd-rail__tab--grade { height: calc(52px * var(--ui-scale)); }
.qd-rail__tab--grade.is-empty .qd-gem { opacity: 0.38; filter: grayscale(0.7); }
.qd-rail__tab--grade.is-locked .qd-gem { opacity: 0.22; }
.qd-rail__tab--grade.is-locked::before {
  content: ""; position: absolute; right: calc(9px * var(--ui-scale)); bottom: calc(8px * var(--ui-scale));
  width: calc(9px * var(--ui-scale)); height: calc(7px * var(--ui-scale));
  border: 1.5px solid var(--paper-500); border-radius: 2px;
  box-shadow: 0 calc(-4px * var(--ui-scale)) 0 calc(-2px * var(--ui-scale)) var(--paper-500);
}
.qd-rail__tab--grade.is-mine::after {
  content: ""; position: absolute; right: calc(8px * var(--ui-scale)); bottom: calc(7px * var(--ui-scale));
  width: 5px; height: 5px; border-radius: 50%; background: var(--gold-400);
}

/* Tooltip for icon-only tabs (hover + keyboard focus). */
[data-tip] { position: relative; }
.qd-top [data-tip]:hover::after,
.qd-top [data-tip]:focus-visible::after,
.qd-rail [data-tip]:hover::after,
.qd-rail [data-tip]:focus-visible::after {
  content: attr(data-tip);
  position: absolute; left: calc(100% + 10px); top: 50%; transform: translateY(-50%);
  z-index: 5;
  padding: 4px 10px;
  white-space: nowrap;
  color: var(--paper-50);
  font: var(--text-xs) var(--f-sans);
  background: #0b0d10f2;
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.5);
  pointer-events: none;
}

/* ── Grade gem (diamond seal carrying the letter) ──────────────────── */
.qd-gem {
  --gem: calc(34px * var(--ui-scale));
  position: relative; display: grid; place-items: center;
  width: var(--gem); height: var(--gem); flex: none;
}
.qd-gem::before {
  content: ""; position: absolute; inset: 15%;
  transform: rotate(45deg);
  border: 1px solid var(--gem-rim, var(--gold-600));
  border-radius: 3px;
  background: radial-gradient(circle at 50% 30%, var(--gem-hi, #3a3833), var(--gem-lo, #17181b) 75%);
  box-shadow: inset 0 0 0 2px #0b0d10, inset 0 0 0 3px var(--gem-inner, rgba(185, 154, 96, 0.35));
}
.qd-gem > span {
  position: relative;
  color: var(--gem-ink, var(--paper-100));
  font: calc(15px * var(--ui-scale)) / 1 var(--f-display);
  text-shadow: 0 1px 0 #000;
}
.qd-gem--sm { --gem: calc(30px * var(--ui-scale)); }
.qd-gem--sm > span { font-size: calc(13px * var(--ui-scale)); }
.qd-gem--lg { --gem: calc(64px * var(--ui-scale)); }
.qd-gem--lg > span { font-size: var(--text-2xl); }
/* Material ladder: iron → bronze → silver → gold → seal-red. */
.qd-gem--F { --gem-hi: #3b3d42; --gem-lo: #1a1b1f; --gem-rim: #6d6a62; --gem-ink: #c9c4b9; }
.qd-gem--E { --gem-hi: #4a3b2b; --gem-lo: #1d1712; --gem-rim: #8a6a45; --gem-ink: #e1c29b; }
.qd-gem--D { --gem-hi: #5a4527; --gem-lo: #221a10; --gem-rim: #a27d45; --gem-ink: #ecd3a6; }
.qd-gem--C { --gem-hi: #55585e; --gem-lo: #1d1f23; --gem-rim: #a9adb3; --gem-ink: #eef0f2; }
.qd-gem--B { --gem-hi: #6a5730; --gem-lo: #261e0f; --gem-rim: var(--gold-500); --gem-ink: var(--gold-300); }
.qd-gem--A { --gem-hi: #7a6230; --gem-lo: #2c210c; --gem-rim: var(--gold-400); --gem-ink: #fff3d4; --gem-inner: var(--gold-500); }
.qd-gem--S { --gem-hi: var(--seal-600); --gem-lo: var(--seal-700); --gem-rim: var(--gold-400); --gem-ink: var(--gold-300); --gem-inner: var(--gold-500); }

/* ── List column ───────────────────────────────────────────────────── */
.qd-list {
  display: flex; flex-direction: column; gap: var(--sp-3);
  min-height: 0; overflow-y: auto;
  padding: var(--sp-4);
  background: #15171c;
  border-right: 1px solid var(--qd-line);
  scrollbar-width: thin; scrollbar-color: var(--ink-600) transparent;
}
.qd-list__head { display: flex; align-items: center; gap: var(--sp-3); }
.qd-list__kicker { color: var(--gold-400); font: var(--text-md) var(--f-display); letter-spacing: 0.12em; }
.qd-list__rule { flex: 1; height: 1px; background: linear-gradient(90deg, var(--qd-line), transparent); }
.qd-list__n { color: var(--paper-500); font: var(--text-xs) var(--f-num); font-variant-numeric: tabular-nums; }

.qd-rows { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.qd-row {
  position: relative;
  display: grid; grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center; gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-3) var(--sp-3) var(--sp-4);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background-color var(--motion-fast) ease, border-color var(--motion-fast) ease;
}
.qd-row::after {
  content: ""; position: absolute; left: var(--sp-4); right: var(--sp-3); bottom: -2px; height: 1px;
  background: repeating-linear-gradient(90deg, var(--qd-line-soft) 0 4px, transparent 4px 8px);
}
.qd-row:last-child::after { display: none; }
.qd-row:hover { background: rgba(255, 255, 255, 0.025); }
.qd-row.is-selected {
  background: linear-gradient(90deg, rgba(169, 50, 42, 0.32), rgba(185, 154, 96, 0.08) 70%, transparent);
  border-color: rgba(207, 68, 68, 0.35);
}
.qd-row.is-selected::before {
  content: ""; position: absolute; left: 0; top: 18%; bottom: 18%; width: 3px;
  background: var(--seal-500); border-radius: 0 2px 2px 0;
}
.qd-row__cat {
  display: grid; place-items: center;
  width: calc(30px * var(--ui-scale)); height: calc(30px * var(--ui-scale));
  color: var(--gold-500);
}
.qd-row__cat svg { width: 80%; height: 80%; }
.qd-row.is-selected .qd-row__cat { color: var(--gold-300); }
.qd-row__main { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.qd-row__name {
  display: flex; align-items: center; gap: var(--sp-2);
  color: var(--paper-50);
  font: var(--text-md) var(--f-serif);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.qd-row.is-failed .qd-row__name { color: var(--paper-400); }
.qd-row__pin { flex: none; width: calc(16px * var(--ui-scale)); height: calc(16px * var(--ui-scale)); color: var(--seal-400); fill: rgba(207, 68, 68, 0.35); }
.qd-row__prog { display: flex; align-items: center; gap: var(--sp-2); }
.qd-row__bar { flex: 1; height: 4px; border-radius: 4px; background: #0b0d10; box-shadow: inset 0 0 0 1px var(--ink-700); overflow: hidden; }
.qd-row__bar > span { display: block; height: 100%; background: linear-gradient(90deg, var(--gold-600), var(--gold-400)); }
.qd-row__num { color: var(--paper-400); font: var(--text-xs) var(--f-num); font-variant-numeric: tabular-nums; }
.qd-row__sub { color: var(--paper-500); font-size: var(--text-xs); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.qd-empty {
  flex: 1; display: grid; place-content: center; justify-items: center; gap: var(--sp-3);
  padding: var(--sp-8) var(--sp-4);
  color: var(--paper-500); text-align: center;
}
.qd-empty svg { width: calc(40px * var(--ui-scale)); height: calc(40px * var(--ui-scale)); color: var(--ink-600); }
.qd-empty p { margin: 0; max-width: 18em; line-height: 1.7; }

/* Rank card (existing design, compacted for the list column). */
.qd-rank {
  display: flex; flex-direction: column; gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  background: linear-gradient(110deg, var(--gold-glow), transparent 45%), var(--panel-hi);
}
.qd-rank__head { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: var(--sp-3); }
.qd-rank__crest { position: relative; display: grid; place-items: center; width: calc(var(--text-4xl) * 1.4); height: calc(var(--text-4xl) * 1.4); }
.qd-rank__crest::before {
  content: ""; position: absolute; inset: 14%; transform: rotate(45deg);
  border: 1px solid var(--gold-500); border-radius: var(--radius-sm);
  background: radial-gradient(circle at 50% 35%, var(--seal-600), var(--seal-700) 60%, var(--ink-900));
  box-shadow: inset 0 0 0 3px var(--ink-900), inset 0 0 0 4px var(--gold-600), 0 0 var(--sp-3) var(--seal-glow);
}
.qd-rank__crest > span { position: relative; color: var(--gold-300); font: var(--text-xl) / 1 var(--f-display); }
.qd-rank__text p { margin: 0; }
.qd-rank__level { color: var(--paper-50); font: var(--text-lg) var(--f-display); }
.qd-rank__level span, .qd-rank__next span { color: var(--gold-400); }
.qd-rank__next { color: var(--paper-400); font-size: var(--text-xs); }
.qd-rank__merit { margin: 0; display: flex; flex-direction: column; align-items: flex-end; }
.qd-rank__merit span { color: var(--paper-500); font-size: var(--text-xs); }
.qd-rank__merit b { color: var(--gold-300); font: 400 var(--text-xl) / 1.1 var(--f-num); }
.qd-rank__meter { height: var(--sp-2); border: 1px solid var(--ink-600); border-radius: var(--radius-pill); background: var(--ink-900); overflow: hidden; }
.qd-rank__meter span { display: block; height: 100%; background: linear-gradient(90deg, var(--gold-600), var(--gold-500)); }
.qd-rank__foot { display: flex; justify-content: space-between; color: var(--paper-300); font-size: var(--text-xs); }
.qd-rank__scale { color: var(--paper-500); }
.qd-rank__exam {
  align-self: flex-start;
  padding: var(--sp-1) var(--sp-4);
  color: var(--gold-300);
  font: var(--text-sm) var(--f-display);
  background: linear-gradient(var(--gold-glow), transparent);
  border: 1px solid var(--gold-500);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.qd-rank__exam small { font: var(--text-xs) var(--f-num); opacity: 0.85; }

/* ── Detail column ─────────────────────────────────────────────────── */
.qd-detail {
  position: relative;
  display: grid; grid-template-rows: minmax(0, 1fr) auto;
  min-height: 0;
  background:
    radial-gradient(90% 60% at 100% 0%, rgba(169, 50, 42, 0.08), transparent 70%),
    #121418;
  animation: qd-in var(--motion-reveal) ease-out;
}
@keyframes qd-in { from { opacity: 0; transform: translateX(6px); } }
.qd-detail__scroll {
  min-height: 0; overflow-y: auto;
  padding: var(--sp-5) var(--sp-8) var(--sp-6);
  display: flex; flex-direction: column; gap: var(--sp-5);
  scrollbar-width: thin; scrollbar-color: var(--ink-600) transparent;
}
.qd-detail__scroll > * { flex-shrink: 0; }

.qd-hero { position: relative; display: flex; flex-direction: column; gap: var(--sp-2); padding-right: calc(96px * var(--ui-scale)); }
.qd-ribbon {
  align-self: flex-start;
  display: inline-flex; align-items: center; gap: var(--sp-2);
  padding: 3px calc(22px * var(--ui-scale)) 3px var(--sp-3);
  color: var(--paper-50);
  font: var(--text-xs) var(--f-display); letter-spacing: 0.12em;
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  clip-path: polygon(0 0, 100% 0, calc(100% - 10px) 50%, 100% 100%, 0 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
.qd-ribbon svg { width: 1.1em; height: 1.1em; color: var(--gold-300); }
.qd-hero__title {
  margin: var(--sp-1) 0 0;
  color: var(--paper-50);
  font: var(--text-3xl) / 1.25 var(--f-display);
  letter-spacing: 0.04em;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
}
.qd-hero__objective {
  margin: 0;
  color: var(--gold-400);
  font: var(--text-lg) / 1.5 var(--f-serif);
}
.qd-hero__variants { margin: 0; color: var(--paper-500); font-size: var(--text-xs); }
.qd-hero__gem { position: absolute; top: 0; right: 0; }

.qd-stamp {
  position: absolute; right: calc(76px * var(--ui-scale)); top: calc(54px * var(--ui-scale));
  padding: 2px var(--sp-3);
  color: var(--seal-400);
  font: var(--text-xl) var(--f-display); letter-spacing: 0.3em;
  border: 3px double var(--seal-500);
  border-radius: var(--radius-sm);
  transform: rotate(-12deg);
  opacity: 0.85;
  mix-blend-mode: screen;
  pointer-events: none;
}
.qd-stamp--failed { color: var(--paper-500); border-color: var(--paper-700); }

.qd-label {
  margin: 0 0 var(--sp-2);
  display: flex; align-items: center; gap: var(--sp-2);
  color: var(--gold-500);
  font: var(--text-xs) var(--f-display); letter-spacing: 0.18em;
}
.qd-label::after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, var(--qd-line), transparent); }

.qd-progress { display: flex; flex-direction: column; gap: var(--sp-2); }
.qd-progress__meta { display: flex; justify-content: space-between; align-items: baseline; color: var(--paper-400); font-size: var(--text-xs); }
.qd-progress__meta b { color: var(--paper-50); font: 400 var(--text-xl) var(--f-num); font-variant-numeric: tabular-nums; }
.qd-progress__meta small { color: var(--paper-500); font-size: var(--text-xs); }
.qd-pips { display: flex; gap: var(--sp-2); }
.qd-pips span {
  flex: 1; max-width: calc(64px * var(--ui-scale)); height: calc(10px * var(--ui-scale));
  background: #0b0d10; border: 1px solid var(--ink-600);
  clip-path: polygon(6px 0, 100% 0, calc(100% - 6px) 100%, 0 100%);
}
.qd-pips span.is-on { background: linear-gradient(90deg, var(--gold-600), var(--gold-400)); border-color: var(--gold-500); box-shadow: 0 0 8px var(--gold-glow); }
.qd-bar { height: 8px; border-radius: 8px; background: #0b0d10; border: 1px solid var(--ink-600); overflow: hidden; }
.qd-bar span { display: block; height: 100%; background: linear-gradient(90deg, var(--gold-600), var(--gold-400)); }

.qd-cond { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-6); }
.qd-cond__cell { min-width: 0; }
.qd-cond__line { margin: 0 0 var(--sp-1); display: flex; align-items: center; gap: var(--sp-2); color: var(--paper-50); font-size: var(--text-md); }
.qd-cond__line svg { width: 1.1em; height: 1.1em; color: var(--gold-500); }
.qd-cond__text { margin: 0; color: var(--paper-300); font-size: var(--text-sm); line-height: 1.75; }
.qd-muted { color: var(--paper-500) !important; }

.qd-client {
  position: relative;
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
  background: linear-gradient(135deg, rgba(185, 154, 96, 0.09), rgba(185, 154, 96, 0.02) 60%);
  border: 1px solid var(--qd-line);
  border-left: 3px solid var(--gold-500);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  overflow: hidden;
}
.qd-client__name { margin: 0 0 var(--sp-2); color: var(--paper-50); font: var(--text-md) var(--f-serif); }
.qd-client__letter {
  position: relative; z-index: 1;
  margin: 0; max-width: 40em;
  color: var(--paper-200);
  font: var(--text-sm) / 1.9 var(--f-serif);
}
.qd-client__mark {
  position: absolute; right: calc(-8px * var(--ui-scale)); bottom: calc(-18px * var(--ui-scale));
  width: calc(130px * var(--ui-scale)); height: calc(130px * var(--ui-scale));
  color: var(--gold-500); opacity: 0.09; stroke-width: 1;
}

.qd-reward__list { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: var(--sp-2); }
.qd-reward__list li {
  display: inline-flex; align-items: baseline; gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-300);
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius-sm);
}
.qd-reward__list svg { align-self: center; width: calc(18px * var(--ui-scale)); height: calc(18px * var(--ui-scale)); color: var(--gold-400); }
.qd-reward__list b { color: var(--paper-50); font: 400 var(--text-md) var(--f-num); font-variant-numeric: tabular-nums; }
.qd-reward__settle { margin: var(--sp-2) 0 0; color: var(--paper-500); font-size: var(--text-xs); }

/* ── Action bar ────────────────────────────────────────────────────── */
.qd-actions {
  display: flex; align-items: center; justify-content: flex-end; gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-8);
  border-top: 1px solid var(--qd-line);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.15), rgba(0, 0, 0, 0.4));
  min-height: calc(64px * var(--ui-scale)); box-sizing: border-box;
}
.qd-actions__spacer { flex: 1; }
.qd-actions__why { margin: 0 auto 0 0; color: var(--paper-400); font-size: var(--text-sm); }
.qd-actions__why--danger { color: var(--seal-400); }
.qd-btn {
  display: inline-flex; align-items: center; gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-5);
  color: var(--paper-100);
  font: var(--text-md) var(--f-display); letter-spacing: 0.08em;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--motion-fast) ease, color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}
.qd-btn svg { width: 1em; height: 1em; }
.qd-btn:hover:not(:disabled) { border-color: var(--gold-500); color: var(--paper-50); }
.qd-btn.is-on { color: var(--gold-300); border-color: var(--gold-500); background: var(--gold-glow); }
.qd-btn.is-on svg { fill: rgba(228, 200, 142, 0.35); }
.qd-btn--primary {
  min-width: calc(160px * var(--ui-scale)); justify-content: center;
  color: var(--paper-50);
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  border-color: var(--gold-500);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 0 14px var(--seal-glow);
}
.qd-btn--primary:hover:not(:disabled) { background: linear-gradient(180deg, var(--seal-500), var(--seal-600)); }
.qd-btn--primary:disabled {
  color: var(--paper-500); background: transparent; border: 1px dashed var(--ink-600); box-shadow: none; cursor: not-allowed;
}
.qd-btn--ghost { color: var(--paper-400); border-color: transparent; background: transparent; }
.qd-btn--ghost:hover:not(:disabled) { color: var(--seal-400); border-color: rgba(207, 68, 68, 0.4); }
.qd-btn--danger { color: var(--paper-50); background: var(--seal-700); border-color: var(--seal-500); }

@media (prefers-reduced-motion: reduce) {
  .qd-detail { animation: none; }
}
</style>
