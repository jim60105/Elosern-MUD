<script setup>
// PartyLineageTab (webclient-party-lineage-tab, design §6.5): the party
// window's 系譜 tab for the viewed member, after the approved prototype
// docs/design/party-member-management/tabs/LineageTab.vue. It renders the
// committed `lineage` v2 panel
// alone (the server builds it for the viewed member).
//
// The list column groups the graphs by their element/style label; each row
// names its graph by the supplied root names joined with ‧, draws one
// diamond per node (filled: capped, half-filled: owned, dashed: locked),
// shows the committed owned/total and marks 可解鎖 when a node is ready. The
// detail column draws the selected graph: one row per `depth`, each node
// once (a merge node too), every edge labelled with its minimum level, and
// each state told apart by border style and text as well as colour.
// Activating an owned node emits `open-skill` and the window opens that
// skill on 技能; a node not yet owned has no 技能 row to open.
//
// Nothing here evaluates a growth rule: levels, XP bands, 見頂, 可解鎖,
// prerequisite lines and every count are the payload's. An unavailable
// panel shows its committed reason and a graph the payload omits is never
// drawn.
import { computed, nextTick, ref, watch } from "vue";
import ListDetail from "./ListDetail.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { panelReason } from "./party-window-model.js";
import {
  NODE_STATE_LABEL,
  graphLayout,
  graphOfSkill,
  graphReady,
  groupGraphs,
  lineageGraphs,
  nodeGrowth,
  nodeState,
  prereqParts,
  rootName,
  stateSummary,
} from "./party-lineage-model.js";

const props = defineProps({
  // The selected committed `party` v3 row (the viewed member).
  member: { type: Object, default: null },
  // The committed `lineage` v2 panel for the viewed member.
  lineage: { type: Object, default: null },
  // A skill the 技能 tab linked from: its graph opens and its node is marked.
  focusSkill: { type: String, default: null },
  // Story seam: the graph selected on open.
  initialGraph: { type: String, default: null },
  // True while a rail selection is in flight: the payload still describes
  // the previous member, so no node may open a skill on 技能.
  pending: { type: Boolean, default: false },
});

const emit = defineEmits(["open-skill"]);

const reason = computed(() => panelReason(props.lineage));
const available = computed(() => props.lineage?.available === true);
const graphs = computed(() => lineageGraphs(props.lineage));
const groups = computed(() => groupGraphs(props.lineage));

// ---------------------------------------------------------------- selection

const selectedId = ref(null);
const graphById = (id) => graphs.value.find((graph) => graph.graph_id === id) ?? null;

// The linked skill's graph, else (on open only) the story seam's graph,
// else the first.
function preferredSelection(opening = false) {
  const linked = graphOfSkill(props.lineage, props.focusSkill);
  if (linked) return linked.graph_id;
  if (opening && props.initialGraph && graphById(props.initialGraph)) return props.initialGraph;
  return graphs.value[0]?.graph_id ?? null;
}
selectedId.value = preferredSelection(true);

// A republished payload keeps the selection while its graph remains (a
// payload committed after the tab opened still finds the linked graph). A
// new viewed member chooses again; when the rail flipped before that
// member's payload landed, the next payload chooses once more, so the
// previous member's graphs never keep the selection.
let awaitingMemberPayload = false;
watch([graphs, () => props.member?.identity], ([list, id], [previousList, previousId]) => {
  if (id !== previousId) {
    awaitingMemberPayload = list === previousList;
    selectedId.value = preferredSelection();
  } else if (awaitingMemberPayload) {
    awaitingMemberPayload = false;
    selectedId.value = preferredSelection();
  } else if (!graphById(selectedId.value)) {
    selectedId.value = preferredSelection();
  }
});

const graph = computed(() => graphById(selectedId.value));
const layout = computed(() => (graph.value ? graphLayout(graph.value) : null));
const currentKey = computed(() => (graph.value && graphOfSkill(props.lineage, props.focusSkill) === graph.value ? props.focusSkill : null));

// The listbox keeps one tab stop (the selected row) and moves focus with the
// arrow keys, Home and End; Enter, Space and click select.
const listbox = ref(null);
function onListKeydown(event) {
  const options = [...(listbox.value?.querySelectorAll('[role="option"]') ?? [])];
  const index = options.indexOf(document.activeElement);
  if (index === -1) return;
  let next = null;
  if (event.key === "ArrowDown") next = Math.min(index + 1, options.length - 1);
  else if (event.key === "ArrowUp") next = Math.max(index - 1, 0);
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = options.length - 1;
  if (next === null) return;
  event.preventDefault();
  // Inside the focus-trapped window the list owns its arrows.
  event.stopPropagation();
  options[next].focus();
}

function select(id) {
  selectedId.value = id;
}

// ---------------------------------------------------------------- nodes

function openNode(node) {
  if (nodeState(node) === "locked" || props.pending) return;
  emit("open-skill", node.skill_key);
}

function nodeStyle(node) {
  const pos = layout.value?.positions[node.skill_key];
  if (!pos) return {};
  return { left: `${pos.x}%`, top: `${pos.y}%`, "--lineage-span": pos.span };
}

// A linked node is scrolled into the detail column's view on open.
const canvas = ref(null);
watch(
  currentKey,
  (key) => {
    if (!key) return;
    nextTick(() => {
      const el = canvas.value?.querySelector(`[data-key="${key}"]`);
      if (el && typeof el.scrollIntoView === "function") el.scrollIntoView({ block: "nearest" });
    });
  },
  { immediate: true },
);

const glyph = (name) => ({ d: glyphPath(name), attrs: glyphAttrs(name) });
</script>

<template>
  <div class="party-lineage-tab" data-testid="party-lineage-tab" :data-member="member ? member.identity : undefined">
    <ListDetail list-label="系譜" detail-label="系譜圖">
      <template #rail><slot name="rail" /></template>

      <template #list>
        <p
          v-if="reason"
          class="party-lineage-tab__reason"
          role="status"
          data-testid="party-window__tab-unavailable"
          :data-reason-code="reason.code || undefined"
        >{{ reason.message }}</p>

        <template v-else-if="available">
          <p class="party-lineage-tab__summary" data-testid="party-lineage-tab__summary">
            已完成 <b>{{ lineage.completed_count }}</b> / {{ lineage.total_count }} 樹
          </p>

          <p v-if="!graphs.length" class="party-lineage-tab__empty" data-testid="party-lineage-tab__empty">尚無可追蹤的技能系譜。</p>

          <div
            v-else
            ref="listbox"
            class="party-lineage-tab__groups"
            role="listbox"
            aria-label="技能系譜"
            data-testid="party-lineage-tab__list"
            @keydown="onListKeydown"
          >
            <div v-for="group in groups" :key="group.label" role="group" :aria-label="group.label" class="party-lineage-tab__group" data-testid="party-lineage-tab__group">
              <p class="party-lineage-tab__sech" aria-hidden="true">
                <span class="party-lineage-tab__sech-mark"><svg viewBox="0 0 24 24" fill="none"><path :d="glyph('lineage').d" stroke="currentColor" stroke-width="1.6" v-bind="glyph('lineage').attrs" /></svg></span>
                <span class="party-lineage-tab__sech-label" data-testid="party-lineage-tab__group-label">{{ group.label }}</span>
                <span class="party-lineage-tab__sech-rule"></span>
              </p>
              <button
                v-for="item in group.graphs"
                :key="item.graph_id"
                type="button"
                role="option"
                class="party-lineage-tab__row"
                :class="{ 'is-selected': item.graph_id === selectedId, 'is-consumed': item.consumed === true }"
                :aria-selected="item.graph_id === selectedId ? 'true' : 'false'"
                :tabindex="item.graph_id === selectedId ? 0 : -1"
                data-testid="party-lineage-tab__row"
                :data-graph="item.graph_id"
                @click="select(item.graph_id)"
              >
                <span class="party-lineage-tab__row-main">
                  <span class="party-lineage-tab__row-name">
                    <span class="party-lineage-tab__row-label" data-testid="party-lineage-tab__row-name">{{ rootName(item) }}</span>
                    <span v-if="graphReady(item)" class="party-lineage-tab__tag party-lineage-tab__tag--ready" data-testid="party-lineage-tab__ready">可解鎖</span>
                    <span v-if="item.consumed === true" class="party-lineage-tab__tag party-lineage-tab__tag--consumed" data-testid="party-lineage-tab__consumed">已全數見頂</span>
                  </span>
                  <span class="party-lineage-tab__sr" data-testid="party-lineage-tab__state-summary">（{{ stateSummary(item) }}）</span>
                  <span class="party-lineage-tab__pips" aria-hidden="true" data-testid="party-lineage-tab__pips">
                    <i
                      v-for="pip in item.nodes"
                      :key="pip.skill_key"
                      class="party-lineage-tab__pip"
                      :class="`is-${nodeState(pip)}`"
                      :data-state="nodeState(pip)"
                      data-testid="party-lineage-tab__pip"
                    ></i>
                  </span>
                </span>
                <span class="party-lineage-tab__row-end" data-testid="party-lineage-tab__count"><b>{{ item.owned_count }}</b> / {{ item.total_count }}</span>
              </button>
            </div>
          </div>
        </template>
      </template>

      <template #detail>
        <div v-if="graph && layout" class="party-lineage-tab__detail" data-testid="party-lineage-tab__detail">
          <div class="party-lineage-tab__head">
            <span class="party-lineage-tab__ribbon" data-testid="party-lineage-tab__ribbon">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="glyph('lineage').d" stroke="currentColor" stroke-width="1.6" v-bind="glyph('lineage').attrs" /></svg>{{ graph.group_label_zh }}
            </span>
            <h3 class="party-lineage-tab__title" aria-live="polite" data-testid="party-lineage-tab__title">{{ rootName(graph) }}</h3>
            <span class="party-lineage-tab__owned" data-testid="party-lineage-tab__owned">已習得 <b>{{ graph.owned_count }}</b> / {{ graph.total_count }}<template v-if="graph.consumed"> ‧ <span class="party-lineage-tab__consumed" data-testid="party-lineage-tab__detail-consumed">已全數見頂</span></template></span>
          </div>

          <div class="party-lineage-tab__scroller">
          <div
            ref="canvas"
            class="party-lineage-tab__canvas"
            :style="{ '--lineage-rows': layout.rows, '--lineage-widest': layout.widest }"
            data-testid="party-lineage-tab__canvas"
            :data-rows="layout.rows"
            :aria-busy="pending ? 'true' : undefined"
          >
            <svg class="party-lineage-tab__edges" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
              <path
                v-for="line in layout.edges"
                :key="line.key"
                :d="line.d"
                :class="{ 'is-locked': line.locked }"
                vector-effect="non-scaling-stroke"
                data-testid="party-lineage-tab__edge"
                :data-from="line.from"
                :data-to="line.to"
              />
            </svg>
            <span
              v-for="line in layout.edges"
              :key="`label-${line.key}`"
              class="party-lineage-tab__edge-label"
              :class="{ 'is-locked': line.locked }"
              :style="{ left: `${line.lx}%`, top: `${line.ly}%` }"
              data-testid="party-lineage-tab__edge-label"
              :data-from="line.from"
              :data-to="line.to"
              aria-hidden="true"
            >Lv {{ line.level }}</span>

            <button
              v-for="item in graph.nodes"
              :key="item.skill_key"
              type="button"
              class="party-lineage-tab__node"
              :class="[`is-${nodeState(item)}`, { 'is-ready': item.ready === true, 'is-current': item.skill_key === currentKey }]"
              :style="nodeStyle(item)"
              :aria-disabled="nodeState(item) === 'locked' || pending ? 'true' : undefined"
              :aria-current="item.skill_key === currentKey ? 'true' : undefined"
              :data-state="nodeState(item)"
              :data-key="item.skill_key"
              data-testid="party-lineage-tab__node"
              @click="openNode(item)"
            >
              <span class="party-lineage-tab__node-name">
                <i class="party-lineage-tab__pip" :class="`is-${nodeState(item)}`" aria-hidden="true"></i>
                <b>{{ item.display_name_zh }}</b>
                <span class="party-lineage-tab__sr">（{{ NODE_STATE_LABEL[nodeState(item)] }}）</span>
              </span>
              <template v-if="nodeGrowth(item)">
                <span class="party-lineage-tab__node-line" :class="{ 'is-capped': nodeGrowth(item).capped }" data-testid="party-lineage-tab__node-growth">
                  <template v-if="nodeGrowth(item).capped">見頂</template>
                  <template v-else>{{ nodeGrowth(item).levelText }} <small data-testid="party-lineage-tab__node-meter">{{ nodeGrowth(item).xpText }}</small></template>
                </span>
                <span class="party-lineage-tab__meter" :class="{ 'is-capped': nodeGrowth(item).capped }" aria-hidden="true"><i :style="{ width: `${nodeGrowth(item).percent}%` }"></i></span>
              </template>
              <span v-if="item.prereq_text_zh" class="party-lineage-tab__node-prereq" data-testid="party-lineage-tab__node-prereq"><span v-for="(part, index) in prereqParts(item.prereq_text_zh)" :key="index" class="party-lineage-tab__prereq-part">{{ part }}</span></span>
              <span v-if="item.ready === true" class="party-lineage-tab__node-ready" data-testid="party-lineage-tab__node-ready">可解鎖</span>
            </button>
          </div>
          </div>
        </div>
      </template>
    </ListDetail>
  </div>
</template>

<style scoped>
/* The approved prototype's 系譜 tab (docs/design/party-member-management/
   tabs/LineageTab.vue and prototype.css `.pm-sech`, `.pm-row`, `.pm-tag`,
   `.pm-meter`, `.pm-ribbon`). Every state that has a colour also has a shape
   or text: capped nodes are filled diamonds with a solid border and 見頂,
   owned nodes half-filled with a solid border and their level, locked nodes
   dashed with their prerequisite line, ready nodes say 可解鎖. */
.party-lineage-tab {
  --lineage-line: rgba(185, 154, 96, 0.28);
  --lineage-line-soft: rgba(185, 154, 96, 0.14);
  --lineage-node-width: calc(200px * var(--ui-scale));
  --lineage-row-pitch: calc(116px * var(--ui-scale));
  --lineage-rows: 1;
  --lineage-widest: 1;
  --lineage-span: 1;
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.party-lineage-tab__reason,
.party-lineage-tab__empty {
  margin: var(--sp-4) 0 0;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.party-lineage-tab__summary {
  margin: 0 0 var(--sp-1);
  text-align: right;
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
  letter-spacing: 0.08em;
}

.party-lineage-tab__summary b {
  color: var(--gold-300);
  font: 500 var(--text-sm) var(--f-num);
  font-variant-numeric: tabular-nums;
}

/* ── list ─────────────────────────────────────────────────────── */
.party-lineage-tab__group + .party-lineage-tab__group {
  margin-top: var(--sp-2);
}

.party-lineage-tab__sech {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: var(--sp-3) 0 var(--sp-1);
  padding: calc(2px * var(--ui-scale)) var(--sp-1);
  color: var(--gold-300);
  font: var(--text-base) var(--f-display);
  letter-spacing: 0.06em;
}

.party-lineage-tab__sech-mark {
  display: grid;
  flex: none;
  place-items: center;
  width: calc(24px * var(--ui-scale));
  height: calc(24px * var(--ui-scale));
  color: var(--gold-400);
  border: calc(1px * var(--ui-scale)) solid var(--lineage-line);
  border-radius: 50%;
}

.party-lineage-tab__sech-mark svg {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}

.party-lineage-tab__sech-rule {
  flex: 1;
  min-width: var(--sp-4);
  height: calc(1px * var(--ui-scale));
  background: linear-gradient(90deg, var(--lineage-line), transparent);
}

.party-lineage-tab__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--sp-3);
  align-items: center;
  width: 100%;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100);
  text-align: left;
  background: transparent;
  border: calc(1px * var(--ui-scale)) solid transparent;
  border-bottom: calc(1px * var(--ui-scale)) dashed var(--lineage-line-soft);
  cursor: pointer;
  transition: background-color var(--motion-fast) ease, border-color var(--motion-fast) ease;
}

.party-lineage-tab__row:hover {
  background: rgba(255, 255, 255, 0.025);
}

.party-lineage-tab__row:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-lineage-tab__row.is-selected {
  background: linear-gradient(90deg, rgba(207, 68, 68, 0.22), rgba(228, 200, 142, 0.06));
  border: calc(1px * var(--ui-scale)) solid var(--seal-700);
  border-radius: var(--radius-sm);
  box-shadow: inset calc(3px * var(--ui-scale)) 0 0 var(--seal-500);
}

.party-lineage-tab__row.is-selected:focus-visible {
  box-shadow: inset calc(3px * var(--ui-scale)) 0 0 var(--seal-500), var(--focus);
}

.party-lineage-tab__row-main {
  min-width: 0;
}

.party-lineage-tab__row-name {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
  font: var(--text-sm) var(--f-serif);
}

.party-lineage-tab__row-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.party-lineage-tab__tag {
  flex: none;
  padding: 0 calc(4px * var(--ui-scale));
  font: var(--text-xs) var(--f-sans);
  line-height: 1.5;
  border-radius: calc(2px * var(--ui-scale));
}

.party-lineage-tab__tag--consumed {
  color: var(--gold-300);
  border: calc(1px * var(--ui-scale)) solid var(--gold-600);
}

.party-lineage-tab__consumed {
  color: var(--gold-300);
}

.party-lineage-tab__tag--ready {
  color: var(--paper-50);
  background: var(--seal-500);
  border: calc(1px * var(--ui-scale)) solid var(--seal-500);
}

.party-lineage-tab__pips {
  display: flex;
  flex-wrap: wrap;
  gap: calc(7px * var(--ui-scale));
  margin-top: calc(7px * var(--ui-scale));
  padding-left: calc(2px * var(--ui-scale));
}

/* One diamond per node: filled (capped), half-filled (owned), dashed (locked). */
.party-lineage-tab__pip {
  display: inline-block;
  flex: none;
  width: calc(10px * var(--ui-scale));
  height: calc(10px * var(--ui-scale));
  transform: rotate(45deg);
  border: calc(1px * var(--ui-scale)) solid var(--gold-500);
}

.party-lineage-tab__pip.is-capped {
  background: var(--gold-300);
  border-color: var(--gold-300);
  box-shadow: 0 0 calc(5px * var(--ui-scale)) rgba(228, 200, 142, 0.4);
}

.party-lineage-tab__pip.is-owned {
  background: linear-gradient(135deg, var(--gold-500) 50%, transparent 50%);
}

.party-lineage-tab__pip.is-locked {
  border-style: dashed;
  border-color: var(--paper-700);
}

.party-lineage-tab__row-end {
  min-width: calc(40px * var(--ui-scale));
  color: var(--paper-400);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

.party-lineage-tab__row-end b {
  color: var(--paper-100);
  font-weight: 500;
}

.party-lineage-tab__row.is-consumed .party-lineage-tab__row-end b {
  color: var(--gold-300);
}

/* ── detail ───────────────────────────────────────────────────── */
.party-lineage-tab__detail {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.party-lineage-tab__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  column-gap: var(--sp-4);
}

.party-lineage-tab__ribbon {
  display: inline-flex;
  flex-basis: 100%;
  align-items: center;
  align-self: flex-start;
  gap: var(--sp-2);
  max-width: max-content;
  margin-bottom: var(--sp-2);
  padding: calc(3px * var(--ui-scale)) var(--sp-5) calc(3px * var(--ui-scale)) var(--sp-3);
  color: var(--paper-50);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  background: var(--seal-600);
  clip-path: polygon(0 0, 100% 0, calc(100% - calc(10px * var(--ui-scale))) 50%, 100% 100%, 0 100%);
}

.party-lineage-tab__ribbon svg {
  width: 1.1em;
  height: 1.1em;
}

.party-lineage-tab__title {
  margin: 0;
  color: var(--paper-50);
  font: var(--text-2xl) var(--f-display);
  letter-spacing: 0.04em;
  overflow-wrap: anywhere;
}

.party-lineage-tab__owned {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
  letter-spacing: 0.08em;
}

.party-lineage-tab__owned b {
  color: var(--gold-300);
  font: 500 var(--text-sm) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.party-lineage-tab__scroller {
  display: flex;
  flex: 1 0 auto;
  flex-direction: column;
  margin-top: var(--sp-4);
  overflow-x: auto;
}

.party-lineage-tab__canvas {
  position: relative;
  /* A wide depth row keeps every node legible and scrolls sideways. */
  min-width: calc(var(--lineage-widest, 1) * calc(112px * var(--ui-scale)));
  flex: 1 0 auto;
  /* At least one pitch per depth; a taller detail column spreads the rows. */
  min-height: calc(var(--lineage-rows, 1) * var(--lineage-row-pitch));
  /* ...but never so far apart that a short graph floats in empty space. */
  max-height: calc(var(--lineage-rows, 1) * var(--lineage-row-pitch) * 1.45);
  /* A soft pool of light behind the drawing, no grid or legend. */
  background: radial-gradient(ellipse at 50% 40%, rgba(228, 200, 142, 0.05), transparent 70%);
}

.party-lineage-tab__edges {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.party-lineage-tab__edges path {
  fill: none;
  stroke: rgba(207, 172, 104, 0.6);
  stroke-width: 1.5;
}

.party-lineage-tab__edges path.is-locked {
  stroke: rgba(170, 166, 158, 0.38);
  stroke-dasharray: 4 4;
}

.party-lineage-tab__edge-label {
  position: absolute;
  z-index: 1;
  padding: 0 calc(6px * var(--ui-scale));
  color: var(--gold-300);
  font: var(--text-xs) var(--f-num);
  line-height: 1.6;
  white-space: nowrap;
  background: var(--ink-900, #121117);
  border: calc(1px * var(--ui-scale)) solid var(--lineage-line);
  border-radius: calc(9px * var(--ui-scale));
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.party-lineage-tab__edge-label.is-locked {
  color: var(--paper-500);
  border-style: dashed;
  border-color: var(--ink-600);
}

.party-lineage-tab__node {
  position: absolute;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: calc(3px * var(--ui-scale));
  width: min(var(--lineage-node-width), calc(100% / var(--lineage-span, 1) - var(--sp-3)));
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-400);
  font: var(--text-xs) var(--f-sans);
  line-height: 1.45;
  text-align: center;
  background: linear-gradient(180deg, rgba(36, 33, 40, 0.98), rgba(20, 19, 24, 0.98));
  border: calc(1px * var(--ui-scale)) solid var(--lineage-line);
  border-radius: var(--radius-sm);
  box-shadow: 0 calc(4px * var(--ui-scale)) calc(12px * var(--ui-scale)) rgba(0, 0, 0, 0.35);
  transform: translate(-50%, -50%);
  cursor: pointer;
  transition: border-color var(--motion-fast) ease, box-shadow var(--motion-fast) ease;
}

.party-lineage-tab__node:hover:not([aria-disabled="true"]) {
  border-color: var(--gold-400);
}

.party-lineage-tab__node:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-lineage-tab__node-name {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  min-width: 0;
}

.party-lineage-tab__node-name b {
  min-width: 0;
  overflow: hidden;
  color: var(--paper-50);
  font: 500 var(--text-sm) var(--f-serif);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.party-lineage-tab__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.party-lineage-tab__node-line {
  overflow: hidden;
  color: var(--paper-200);
  text-overflow: ellipsis;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.party-lineage-tab__node-line small {
  margin-left: calc(2px * var(--ui-scale));
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
}

.party-lineage-tab__node-line.is-capped {
  color: var(--gold-300);
  letter-spacing: 0.2em;
}

.party-lineage-tab__meter {
  display: block;
  height: calc(3px * var(--ui-scale));
  overflow: hidden;
  background: #2a2c30;
  border-radius: calc(2px * var(--ui-scale));
}

.party-lineage-tab__meter i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--gold-600), var(--gold-500));
  border-radius: inherit;
}

.party-lineage-tab__meter.is-capped i {
  background: var(--gold-300);
  box-shadow: 0 0 calc(6px * var(--ui-scale)) rgba(228, 200, 142, 0.45);
}

.party-lineage-tab__node-prereq {
  color: var(--paper-500);
  overflow-wrap: anywhere;
}

/* A line breaks between the prerequisite clauses, not inside a name. */
.party-lineage-tab__prereq-part {
  display: inline-block;
  max-width: 100%;
}

.party-lineage-tab__node-ready {
  align-self: center;
  padding: 0 calc(6px * var(--ui-scale));
  color: var(--paper-50);
  background: var(--seal-500);
  border-radius: calc(2px * var(--ui-scale));
}

/* capped: solid gold border with a soft glow. */
.party-lineage-tab__node.is-capped {
  border-color: var(--gold-400);
  box-shadow: 0 0 calc(10px * var(--ui-scale)) rgba(228, 200, 142, 0.22), 0 calc(4px * var(--ui-scale)) calc(12px * var(--ui-scale)) rgba(0, 0, 0, 0.35);
}

/* owned: solid border. */
.party-lineage-tab__node.is-owned {
  border-color: var(--gold-600);
}

/* locked: dashed border, dimmed, not activatable. */
.party-lineage-tab__node.is-locked {
  background: rgba(16, 15, 19, 0.96);
  border-style: dashed;
  border-color: var(--ink-600);
  box-shadow: none;
  cursor: default;
}

.party-lineage-tab__node.is-locked .party-lineage-tab__node-name b {
  color: var(--paper-400);
}

.party-lineage-tab__node.is-ready {
  border-color: var(--seal-700);
}

/* The skill the 技能 tab linked from. */
.party-lineage-tab__node.is-current {
  border-color: var(--seal-500);
  box-shadow: 0 0 0 calc(1px * var(--ui-scale)) var(--seal-700), 0 calc(4px * var(--ui-scale)) calc(12px * var(--ui-scale)) rgba(0, 0, 0, 0.35);
}

.party-lineage-tab__node.is-current:focus-visible,
.party-lineage-tab__node.is-capped:focus-visible {
  box-shadow: var(--focus);
}
</style>
