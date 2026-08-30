<script setup>
// LineagePanel (skill-lineage-panel, task 2.3): the big-window skill-lineage
// ledger rendered inside OverlayHost's body slot. Every rendered value comes
// from the committed `lineage` panel payload alone — the client recomputes no
// growth rules: levels, meters, 見頂 marks, prerequisite lines, and the
// header counts are the server's derived view, serialized verbatim. A chain
// omitted from the payload (truncated) or the whole panel unavailable renders
// no placeholder chain and no invented progress.
//
// Tree interaction is client-local view state only: which chains are
// expanded. A collapsed chain renders its aggregate `meter` (shallowest
// unlocked node progress); expanding renders the per-node rows.
import { computed, ref } from "vue";

const props = defineProps({
  // The committed `lineage` panel payload (schema version 1), or null when
  // no panel has ever been committed.
  lineage: { type: Object, default: null },
});

const available = computed(
  () => !!props.lineage && props.lineage.available !== false,
);

// The fallback line for a panel that was never committed at all; a panel
// delivered in its unavailable form always carries the registry reason.
const FALLBACK_REASON = "技能系譜目前無法顯示";

const chains = computed(() =>
  available.value && Array.isArray(props.lineage.chains)
    ? props.lineage.chains
    : [],
);

// Client-local expand/collapse state, keyed by chain root skill key. The
// default is collapsed (the ledger reads as a per-tree progress board first).
const expanded = ref(new Set());

function toggleChain(rootKey) {
  const next = new Set(expanded.value);
  if (next.has(rootKey)) {
    next.delete(rootKey);
  } else {
    next.add(rootKey);
  }
  expanded.value = next;
}

function chainPercent(meter) {
  return Math.max(0, Math.min(100, Math.round(meter * 100)));
}

// Display-only normalization: practice XP is a float, the payload's
// xp_into_level / xp_to_next_level pair is the node's own level band. No
// growth rule is evaluated here — only the stored pair is formatted.
function formatXp(value) {
  return Number.isInteger(value) ? String(value) : String(Math.round(value * 10) / 10);
}

function nodeMeter(node) {
  return `${formatXp(node.xp_into_level)}/${formatXp(node.xp_into_level + node.xp_to_next_level)} → 下一階`;
}
</script>

<template>
  <div class="lineage-panel" data-testid="lineage-panel">
    <p
      v-if="!available"
      class="lineage-panel__unavailable"
      data-testid="lineage-panel-unavailable"
    >
      {{ (lineage && lineage.reason && lineage.reason.message) || FALLBACK_REASON }}
    </p>
    <template v-else>
      <p class="lineage-panel__header" data-testid="lineage-panel-header">
        已完成 {{ lineage.completed_count }} / {{ lineage.total_count }} 樹
      </p>
      <p
        v-if="chains.length === 0"
        class="lineage-panel__empty"
        data-testid="lineage-panel-empty"
      >
        目前尚無可追蹤的技能系譜。
      </p>
      <section
        v-for="chain in chains"
        :key="chain.root_skill_key"
        class="lineage-chain"
        :data-testid="`lineage-chain-${chain.root_skill_key}`"
      >
        <button
          type="button"
          class="lineage-chain__head"
          :aria-expanded="expanded.has(chain.root_skill_key) ? 'true' : 'false'"
          :data-testid="`lineage-chain-toggle-${chain.root_skill_key}`"
          @click="toggleChain(chain.root_skill_key)"
        >
          <svg
            class="lineage-chain__chevron"
            :class="{ 'lineage-chain__chevron--open': expanded.has(chain.root_skill_key) }"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.9"
            aria-hidden="true"
          >
            <path d="M9 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span class="lineage-chain__label">{{ chain.element_or_style_zh }}</span>
          <span
            v-if="chain.consumed"
            class="lineage-chain__consumed"
            data-testid="lineage-chain-consumed"
            >已全數見頂</span
          >
          <span v-else class="lineage-chain__percent">{{ chainPercent(chain.meter) }}%</span>
          <span
            class="lineage-chain__meter"
            role="img"
            :aria-label="`進度 ${chainPercent(chain.meter)}%`"
            :data-testid="`lineage-chain-meter-${chain.root_skill_key}`"
          >
            <span
              class="lineage-chain__meter-fill"
              :style="{ width: `${chainPercent(chain.meter)}%` }"
            ></span>
          </span>
        </button>
        <ul
          v-if="expanded.has(chain.root_skill_key)"
          class="lineage-chain__nodes"
          :data-testid="`lineage-chain-nodes-${chain.root_skill_key}`"
        >
          <li
            v-for="node in chain.nodes"
            :key="node.skill_key"
            class="lineage-node"
            :class="{ 'lineage-node--locked': !node.usable }"
            :data-testid="`lineage-node-${node.skill_key}`"
          >
            <span class="lineage-node__name"
              >{{ node.display_name_zh }} Lv.{{ node.level }}</span
            >
            <span
              v-if="node.capped"
              class="lineage-node__tip"
              data-testid="lineage-node-tip"
              >（見頂）</span
            >
            <span
              v-else-if="node.owned"
              class="lineage-node__meter"
              :data-testid="`lineage-node-meter-${node.skill_key}`"
              >{{ nodeMeter(node) }}</span
            >
            <span
              v-if="node.prereq_text_zh"
              class="lineage-node__prereq"
              :data-testid="`lineage-node-prereq-${node.skill_key}`"
              >{{ node.prereq_text_zh }}</span
            >
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.lineage-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.lineage-panel__unavailable,
.lineage-panel__empty {
  margin: 0;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.lineage-panel__header {
  margin: 0;
  font-family: var(--f-display);
  font-size: var(--text-lg);
  color: var(--gold-400);
}

.lineage-chain {
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel);
  overflow: hidden;
}

.lineage-chain__head {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  color: var(--paper-100);
  background: transparent;
  border: 0;
  cursor: pointer;
  text-align: left;
  font: inherit;
}

.lineage-chain__head:hover {
  background: rgba(255, 255, 255, 0.04);
}

.lineage-chain__head:focus-visible {
  outline: 1px solid var(--gold-400);
  outline-offset: -2px;
}

.lineage-chain__chevron {
  flex: none;
  width: 14px;
  height: 14px;
  color: var(--paper-500);
  transition: transform 120ms ease;
}

.lineage-chain__chevron--open {
  transform: rotate(90deg);
}

.lineage-chain__label {
  font-family: var(--f-display);
  font-size: var(--text-md);
  color: var(--paper-50);
}

.lineage-chain__consumed {
  color: var(--gold-400);
  font-size: var(--text-sm);
}

.lineage-chain__percent {
  color: var(--paper-500);
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums;
}

.lineage-chain__meter {
  flex: 1;
  min-width: 60px;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.lineage-chain__meter-fill {
  display: block;
  height: 100%;
  background: var(--gold-400);
}

.lineage-chain__nodes {
  margin: 0;
  padding: 4px 14px 12px 38px;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.lineage-node {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: var(--text-sm);
}

.lineage-node__name {
  color: var(--paper-50);
}

.lineage-node--locked .lineage-node__name {
  color: var(--paper-500);
}

.lineage-node__tip {
  color: var(--gold-400);
}

.lineage-node__meter {
  color: var(--paper-300);
  font-variant-numeric: tabular-nums;
}

.lineage-node__prereq {
  color: var(--seal-400);
}
</style>
