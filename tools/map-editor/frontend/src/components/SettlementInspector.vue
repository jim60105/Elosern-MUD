<script setup>
// Explicit settlement editing controls (frontend design §4.2, §6 non-drag
// paths): the local map's options, node fields typed from the core schema
// (name, prototype with its anchor location, scene from the current index,
// typeclass, description), the position in `m 地方`, duplication with a new
// ID, directed roads with explicit endpoint and direction selectors, bends
// with numeric rows and insert/remove, the core's route preview, the
// one-document multi-selection with mixed values and a group move, and the
// node, road and duplicate creation forms. Every change is emitted as one
// named single-document command descriptor through `submit`; the service
// validates it.
// Directions are always chosen, never inferred from positions.
// Authored text renders through text interpolation only.
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import DraftField from "./DraftField.vue";
import {
  COMPASS,
  FRAME_LOCAL_M,
  IDENTIFIER,
  bendInsertion,
  bendRef,
  blankNode,
  compassLabel,
  createNode,
  createRoad,
  duplicateNode,
  findRoad,
  findSettlement,
  groupMoves,
  incomingRows,
  insertBend,
  mixedValue,
  moveBend,
  moveNodes,
  nextId,
  nodeFieldSpecs,
  nodeFields,
  nodeName,
  oneDocumentNodes,
  outgoingRows,
  parseSettlementRef,
  prototypeFields,
  removeBend,
  roadLabel,
  roadRef,
  setRoad,
  settlementField,
} from "../lib/settlement.js";

const props = defineProps({
  world: { type: Object, required: true },
  workspace: { type: Object, default: null },
  settlementId: { type: String, default: null },
  selection: { type: Array, default: () => [] },
  creation: { type: Object, default: null },
  hint: { type: String, default: null },
  // Queues one command descriptor and resolves with the service's answer.
  submit: { type: Function, required: true },
});
const emit = defineEmits(["create", "cancel", "select", "follow", "drafts", "open", "delete"]);

// Draft counts of every open field and form, summed for the follow hold.
const counts = reactive({});
const total = computed(() => Object.values(counts).reduce((sum, value) => sum + value, 0));
watch(total, (value) => emit("drafts", value), { immediate: true });
onBeforeUnmount(() => emit("drafts", 0));
const track = (key) => (value) => {
  counts[key] = value;
};
const send = (descriptor) => props.submit(descriptor);

const single = computed(() => (props.selection.length === 1 ? parseSettlementRef(props.selection[0]) : null));
const settlement = computed(() => findSettlement(props.world, single.value?.settlementId ?? props.settlementId));
const node = computed(() =>
  single.value?.kind === "node" ? settlement.value?.nodes.find((row) => row.id === single.value.nodeId) ?? null : null,
);
const road = computed(() =>
  single.value && single.value.kind !== "node" ? findRoad(settlement.value, single.value.source, single.value.destination) : null,
);
const bend = computed(() => (single.value?.kind === "bend" && road.value ? road.value.bends[single.value.index] ?? null : null));
const group = computed(() => (props.selection.length > 1 ? oneDocumentNodes(props.selection) : null));
const groupSettlement = computed(() => (group.value ? findSettlement(props.world, group.value.settlementId) : null));
const groupNodes = computed(() =>
  groupSettlement.value ? groupSettlement.value.nodes.filter((row) => group.value.nodeIds.includes(row.id)) : [],
);
const specs = computed(() => nodeFieldSpecs(props.workspace?.schema));
const specOf = (key) => specs.value.find((spec) => spec.key === key) ?? null;
const textSpecs = computed(() => specs.value.filter((spec) => !spec.reference && spec.type !== "select"));
const prototypeOptions = computed(() => specOf("prototype_parent")?.options ?? []);
const locationOptions = computed(() => props.world.locations.map((row) => ({ value: row.id, label: `${row.display_name_zh} · ${row.id}` })));
const nodeOptions = computed(() => (settlement.value?.nodes ?? []).map((row) => ({ value: row.id, label: `${row.key} · ${row.id}` })));
const directionOptions = [{ value: "", label: "（請選擇方向）" }, ...COMPASS.map((item) => ({ value: item.value, label: `${item.label} · ${item.value}` }))];
const FIELD_LABELS = { key: "名稱", desc: "描述", typeclass: "類型類別（空白為無）", prototype_parent: "原型", anchor_key: "錨點地點", scene_archetype: "場景" };

// -- scene references (current index only) -------------------------------------
const indexCurrent = computed(() => Boolean(props.workspace?.external_context_status?.current));
const scenes = computed(() => (indexCurrent.value ? props.workspace?.external_identifiers?.scene_archetypes ?? [] : null));
function sceneOptions(value) {
  const options = [{ value: null, label: "（無）" }, ...(scenes.value ?? []).map((id) => ({ value: id, label: id }))];
  if (value && !(scenes.value ?? []).includes(value)) options.push({ value, label: `${value}（✕ 不在目前場景目錄）` });
  return options;
}
const SCENE_STATUS = {
  valid: { glyph: "✓", text: "場景在目前索引中", tone: "ok" },
  invalid: { glyph: "✕", text: "場景不在目前索引中", tone: "error" },
  unavailable: { glyph: "▲", text: "外部索引不可用，無法驗證場景", tone: "warn" },
  none: null,
};

// -- node ------------------------------------------------------------------------
function setField(key, value) {
  send(nodeFields(settlement.value.id, node.value.id, { [key]: value }));
}
function setPrototype(value) {
  const anchor = value === "anchor_room" ? node.value.anchor_key ?? settlement.value.location_ref : null;
  send(nodeFields(settlement.value.id, node.value.id, prototypeFields(value, anchor)));
}
function setPosition(axis, value) {
  const position = [...node.value.local_m];
  position[axis] = value;
  send(moveNodes(settlement.value.id, [{ node_id: node.value.id, x_m: position[0], y_m: position[1] }]));
}
const outgoing = computed(() => (node.value ? outgoingRows(settlement.value, node.value.id) : []));
const incoming = computed(() => (node.value ? incomingRows(settlement.value, node.value.id) : []));
function openDuplicate() {
  const ids = settlement.value.nodes.map((row) => row.id);
  emit("open", {
    type: "duplicate",
    defaults: {
      node_id: node.value.id,
      id: nextId(node.value.id, ids),
      x: String(node.value.local_m[0] + 20),
      y: String(node.value.local_m[1]),
      anchor: node.value.prototype_parent === "anchor_room",
    },
  });
}
function openRoad(source, destination = "") {
  emit("open", { type: "road", defaults: { source, destination, direction: "", two_way: false, return_direction: "" } });
}

// -- route preview (the core planner over the published snapshot) ---------------
const route = reactive({ destination: "", result: null, error: null, busy: false });
watch(() => props.selection.join("|"), () => Object.assign(route, { destination: "", result: null, error: null }));
const routeStale = computed(
  () => route.result && route.result.snapshot_revision !== props.workspace?.snapshot_revision,
);
async function queryRoute() {
  if (!route.destination || !node.value) return;
  route.busy = true;
  route.error = null;
  try {
    const query = new URLSearchParams({ source: node.value.id, destination: route.destination });
    const response = await window.fetch(`/api/settlements/${settlement.value.id}/route?${query}`, { cache: "no-store" });
    const body = await response.json();
    if (!response.ok) throw new Error(body?.error?.message ?? `HTTP ${response.status}`);
    route.result = body;
  } catch (error) {
    route.result = null;
    route.error = String(error?.message ?? error);
  } finally {
    route.busy = false;
  }
}

// -- road and bends ----------------------------------------------------------------
const reverse = computed(() => (road.value ? findRoad(settlement.value, road.value.destination, road.value.source) : null));
function retarget(part, value) {
  const next = { source: road.value.source, destination: road.value.destination, direction: road.value.direction, [part]: value };
  if (!next.direction) return;
  send(setRoad(settlement.value.id, road.value.source, road.value.destination, next)).then((result) => {
    if (result?.changed && part !== "direction") emit("select", roadRef(settlement.value.id, next.source, next.destination));
  });
}
function setBendAxis(index, axis, value) {
  const point = [...road.value.bends[index]];
  point[axis] = value;
  send(moveBend(settlement.value.id, road.value.source, road.value.destination, index, point));
}
function addBend(index, before) {
  const insertion = bendInsertion(settlement.value, road.value, index, before);
  send(insertBend(settlement.value.id, road.value.source, road.value.destination, insertion.index, insertion.point)).then((result) => {
    if (result?.changed) emit("select", bendRef(roadRef(settlement.value.id, road.value?.source ?? single.value.source, road.value?.destination ?? single.value.destination), insertion.index));
  });
}
function dropBend(index) {
  const owner = single.value.road;
  send(removeBend(settlement.value.id, road.value.source, road.value.destination, index)).then((result) => {
    if (result?.changed) emit("select", owner);
  });
}

// -- multi-selection ---------------------------------------------------------------
const delta = reactive({ x: "0", y: "0" });
const deltaError = computed(() =>
  /^-?\d+$/.test(String(delta.x).trim()) && /^-?\d+$/.test(String(delta.y).trim()) ? null : "位移需要整數公尺。",
);
watch(
  () => delta.x !== "0" || delta.y !== "0",
  (open) => {
    counts.delta = open ? 1 : 0;
  },
);
function applyDelta() {
  if (deltaError.value || !group.value) return;
  const dx = Number(delta.x);
  const dy = Number(delta.y);
  if (!dx && !dy) return;
  send(moveNodes(group.value.settlementId, groupMoves(groupSettlement.value, group.value.nodeIds, dx, dy)));
  delta.x = "0";
  delta.y = "0";
}

// -- map section ---------------------------------------------------------------------
const mapSettlement = computed(() => (!props.selection.length ? findSettlement(props.world, props.settlementId) : null));
const options = reactive({ map_visual_range: "", map_mode: "" });
function loadOptions() {
  const current = mapSettlement.value?.options;
  options.map_visual_range = current ? String(current.map_visual_range) : "";
  options.map_mode = current ? current.map_mode : "";
}
watch(() => JSON.stringify(mapSettlement.value?.options ?? null) + (mapSettlement.value?.id ?? ""), loadOptions, { immediate: true });
const optionsDraft = computed(() => {
  const current = mapSettlement.value?.options;
  return current
    ? options.map_visual_range !== String(current.map_visual_range) || options.map_mode !== current.map_mode
    : Boolean(options.map_visual_range || options.map_mode);
});
watch(optionsDraft, (open) => {
  counts.options = open ? 1 : 0;
});
const optionsError = computed(() =>
  /^\d+$/.test(String(options.map_visual_range).trim()) && String(options.map_mode).trim() ? null : "視野需要整數，模式不可空白。",
);
function submitOptions() {
  if (!optionsDraft.value || optionsError.value) return;
  send(settlementField(mapSettlement.value.id, "options", { map_visual_range: Number(options.map_visual_range), map_mode: options.map_mode.trim() }));
}

// -- creation forms ---------------------------------------------------------------------
const form = reactive({});
watch(
  () => props.creation,
  (creation) => {
    for (const key of Object.keys(form)) delete form[key];
    if (creation) Object.assign(form, creation.defaults ?? {});
  },
  { immediate: true },
);
watch(
  () => Boolean(props.creation),
  (open) => {
    counts.creation = open ? 1 : 0;
  },
  { immediate: true },
);
const formSettlement = computed(() => findSettlement(props.world, props.settlementId));
const submitted = ref(false);
watch(() => props.creation, () => (submitted.value = false));
const formError = computed(() => {
  const creation = props.creation;
  if (!creation) return null;
  const nodes = formSettlement.value?.nodes ?? [];
  const known = (id) => nodes.some((row) => row.id === id);
  const integer = (value) => /^-?\d+$/.test(String(value ?? "").trim());
  if (creation.type === "road") {
    if (!known(form.source) || !known(form.destination)) return "請選擇現有的起點與終點節點。";
    if (form.source === form.destination) return "起點與終點不可相同。";
    if (!form.direction) return "請選擇去程方向（不會依位置推斷）。";
    if (form.two_way && !form.return_direction) return "建立雙向時請選擇回程方向。";
    return null;
  }
  if (!IDENTIFIER.test(String(form.id ?? ""))) return "ID 需為小寫英文、數字與底線，並以字母開頭。";
  if (known(form.id)) return "這個 ID 已存在；新節點需要新的 ID。";
  if (!integer(form.x) || !integer(form.y)) return "位置需要整數公尺。";
  if (creation.type === "duplicate") return known(form.node_id) ? null : "原節點已不存在。";
  if (!String(form.key ?? "").trim()) return "需要名稱。";
  if (form.prototype_parent === "anchor_room" && !form.anchor_key) return "錨點房間需要選擇地點。";
  return null;
});
function submitCreation() {
  submitted.value = true;
  const creation = props.creation;
  if (!creation || formError.value) return;
  const id = formSettlement.value.id;
  if (creation.type === "road") {
    const reverseRoad = form.two_way ? { direction: form.return_direction, bends: [] } : null;
    emit("create", createRoad(id, form.source, form.destination, form.direction, [], reverseRoad), roadRef(id, form.source, form.destination));
  } else if (creation.type === "duplicate") {
    emit("create", duplicateNode(id, form.node_id, form.id, [Number(form.x), Number(form.y)]), `settlement_node:${id}:${form.id}`);
  } else {
    const fields = {
      ...blankNode(Number(form.x), Number(form.y), { key: form.key, desc: form.desc ?? "" }),
      ...prototypeFields(form.prototype_parent ?? "grid_room", form.anchor_key ?? null),
      scene_archetype: String(form.scene_archetype ?? "").trim() || null,
    };
    emit("create", createNode(id, form.id, fields), `settlement_node:${id}:${form.id}`);
  }
}
function onFormKey(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    emit("cancel");
  } else if (event.key === "Enter" && !event.isComposing && event.target.tagName !== "TEXTAREA") {
    event.preventDefault();
    submitCreation();
  }
}
const TITLES = { node: "新節點", road: "新道路", duplicate: "複製為新節點" };
</script>

<template>
  <div class="settlement-inspector" data-settlement-inspector>
    <!-- creation forms -->
    <form v-if="creation" class="creation" :data-creation="creation.type" @submit.prevent="submitCreation" @keydown="onFormKey">
      <h3 class="section-label">{{ TITLES[creation.type] }}</h3>
      <template v-if="creation.type === 'road'">
        <label class="draft-field">
          <span class="draft-field__label">起點節點</span>
          <select v-model="form.source" class="draft-field__input" data-creation-field="source">
            <option value="">（請選擇）</option>
            <option v-for="option in nodeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="draft-field">
          <span class="draft-field__label">終點節點</span>
          <select v-model="form.destination" class="draft-field__input" data-creation-field="destination">
            <option value="">（請選擇）</option>
            <option v-for="option in nodeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="draft-field">
          <span class="draft-field__label">去程方向</span>
          <select v-model="form.direction" class="draft-field__input" data-creation-field="direction">
            <option v-for="option in directionOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="check">
          <input v-model="form.two_way" type="checkbox" data-creation-field="two_way" />
          建立雙向
        </label>
        <label v-if="form.two_way" class="draft-field">
          <span class="draft-field__label">回程方向</span>
          <select v-model="form.return_direction" class="draft-field__input" data-creation-field="return_direction">
            <option v-for="option in directionOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <p class="inspector__muted">
          {{ form.two_way ? "一次操作建立兩筆有向道路，寫入同一份據點文件。" : "只建立一筆有向道路。" }}長度由核心依節點與彎點計算。
        </p>
      </template>
      <template v-else>
        <label class="draft-field">
          <span class="draft-field__label">ID（建立後不可更改）</span>
          <input v-model="form.id" class="draft-field__input mono" data-creation-field="id" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">東向<span class="draft-field__unit">{{ FRAME_LOCAL_M }}</span></span>
          <input v-model="form.x" class="draft-field__input mono" inputmode="numeric" data-creation-field="x" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">北向<span class="draft-field__unit">{{ FRAME_LOCAL_M }}</span></span>
          <input v-model="form.y" class="draft-field__input mono" inputmode="numeric" data-creation-field="y" />
        </label>
        <p v-if="creation.type === 'duplicate'" class="inspector__muted" data-duplicate-note>
          複製名稱、描述、場景、類型類別與原型的一般值；不複製道路、入口、城門或地標。{{ form.anchor ? "錨點房間的複本會成為一般房間（grid_room）。" : "" }}
        </p>
        <template v-else>
          <label class="draft-field">
            <span class="draft-field__label">名稱</span>
            <input v-model="form.key" class="draft-field__input" data-creation-field="key" />
          </label>
          <label class="draft-field">
            <span class="draft-field__label">描述</span>
            <textarea v-model="form.desc" class="draft-field__input" rows="2" data-creation-field="desc" />
          </label>
          <label class="draft-field">
            <span class="draft-field__label">原型</span>
            <select v-model="form.prototype_parent" class="draft-field__input" data-creation-field="prototype_parent">
              <option v-for="option in prototypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <label v-if="form.prototype_parent === 'anchor_room'" class="draft-field">
            <span class="draft-field__label">錨點地點</span>
            <select v-model="form.anchor_key" class="draft-field__input" data-creation-field="anchor_key">
              <option :value="null">（請選擇）</option>
              <option v-for="option in locationOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
        </template>
      </template>
      <p v-if="submitted && formError" class="draft-field__hint" data-field-error="creation">{{ formError }}</p>
      <div class="inspector__actions">
        <button type="submit" class="button" data-creation-submit>＋ 建立</button>
        <button type="button" class="button" data-creation-cancel @click="emit('cancel')">取消 Esc</button>
      </div>
    </form>
    <p v-else-if="hint" class="inspector__reason" data-tool-hint>{{ hint }}</p>

    <!-- node -->
    <template v-if="node">
      <DraftField
        v-for="spec in textSpecs"
        :key="`${selection[0]}-${spec.key}`"
        :label="FIELD_LABELS[spec.key] ?? spec.key"
        :field-key="`node-${spec.key}`"
        :type="spec.type"
        :value="node[spec.key]"
        @confirm="setField(spec.key, $event)"
        @drafts="track(`node-${spec.key}`)($event)"
      />
      <DraftField
        label="原型"
        field-key="node-prototype_parent"
        type="select"
        :options="prototypeOptions"
        :value="node.prototype_parent"
        @confirm="setPrototype($event)"
      />
      <DraftField
        v-if="node.prototype_parent === 'anchor_room'"
        label="錨點地點"
        field-key="node-anchor_key"
        type="select"
        :options="locationOptions"
        :value="node.anchor_key"
        @confirm="setField('anchor_key', $event)"
      />
      <DraftField
        v-if="scenes"
        label="場景"
        field-key="node-scene_archetype"
        type="select"
        :options="sceneOptions(node.scene_archetype)"
        :value="node.scene_archetype"
        @confirm="setField('scene_archetype', $event)"
      />
      <DraftField
        v-else
        label="場景（空白為無）"
        field-key="node-scene_archetype"
        type="nullable"
        :value="node.scene_archetype"
        @confirm="setField('scene_archetype', $event)"
        @drafts="track('node-scene')($event)"
      />
      <p v-if="SCENE_STATUS[node.scene_status]" :class="SCENE_STATUS[node.scene_status].tone" :data-scene-status="node.scene_status">
        {{ SCENE_STATUS[node.scene_status].glyph }} {{ SCENE_STATUS[node.scene_status].text }}
      </p>
      <h3 class="section-label">位置 · {{ FRAME_LOCAL_M }}</h3>
      <DraftField
        v-for="(axis, index) in ['東向', '北向']"
        :key="`${selection[0]}-position-${index}`"
        :label="axis"
        :field-key="`node-position-${index}`"
        type="int"
        :unit="FRAME_LOCAL_M"
        :value="node.local_m[index]"
        @confirm="setPosition(index, $event)"
        @drafts="track(`node-position-${index}`)($event)"
      />
      <p class="inspector__note">移動節點不會改變 ID 或已設定的道路方向；長度由核心重新計算。</p>
      <h3 class="section-label">道路 · 有向</h3>
      <ul class="plain" data-road-rows>
        <li v-for="row in outgoing" :key="row.road" data-road-row="out">
          <button type="button" class="link" :data-select-road="row.road" @click="emit('select', row.road)">{{ row.label }}</button>
        </li>
        <li v-for="row in incoming" :key="row.road" class="inspector__muted" data-road-row="in">
          <button type="button" class="link" :data-select-road="row.road" @click="emit('select', row.road)">{{ row.label }}</button>
        </li>
        <li v-if="!outgoing.length && !incoming.length" class="inspector__muted">沒有道路（未完成的連通性可以存檔）。</li>
      </ul>
      <div class="inspector__actions">
        <button type="button" class="button" data-action="new-road" @click="openRoad(node.id)">⟶ 新道路</button>
        <button type="button" class="button" data-action="duplicate-node" @click="openDuplicate">⧉ 複製為新節點</button>
      </div>
      <h3 class="section-label">路徑預覽 · 核心計算</h3>
      <form class="landmark" data-route-preview @submit.prevent="queryRoute">
        <label class="draft-field">
          <span class="draft-field__label">目的地</span>
          <select v-model="route.destination" class="draft-field__input" data-route-field="destination">
            <option value="">（請選擇）</option>
            <option v-for="option in nodeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <div class="inspector__actions">
          <button type="submit" class="button" data-route-submit>查詢路徑</button>
        </div>
      </form>
      <div v-if="route.result" :data-route-status="route.result.status" :data-route-stale="routeStale ? 'true' : null">
        <p v-if="routeStale" class="warn">▲ 檔案已更新，這個結果屬於較舊的快照；請重新查詢。</p>
        <template v-if="route.result.status === 'route'">
          <ol class="plain">
            <li v-for="(step, index) in route.result.steps" :key="index" data-route-step>
              {{ compassLabel(step.direction) }} → {{ nodeName(settlement, step.destination) }} · {{ Math.round(step.length_m) }} m
            </li>
          </ol>
          <p data-route-length>合計 {{ Math.round(route.result.length_m) }} m（實體路線長度）</p>
        </template>
        <p v-else-if="route.result.status === 'no_route'" class="warn">▲ 依有向道路無法抵達。</p>
        <p v-else class="warn">▲ 無法預覽路徑（{{ route.result.reason ?? route.result.status }}）。</p>
      </div>
      <p v-else-if="route.error" class="draft-field__hint" data-field-error="route">{{ route.error }}</p>
    </template>

    <!-- road -->
    <template v-else-if="road && !bend">
      <DraftField label="起點節點" field-key="road-source" type="select" :options="nodeOptions" :value="road.source" @confirm="retarget('source', $event)" />
      <DraftField label="終點節點" field-key="road-destination" type="select" :options="nodeOptions" :value="road.destination" @confirm="retarget('destination', $event)" />
      <DraftField
        label="方向（已設定的出口方向）"
        field-key="road-direction"
        type="select"
        :options="directionOptions.slice(1)"
        :value="road.direction"
        @confirm="retarget('direction', $event)"
      />
      <p data-road-length>長度：{{ road.length_m === null ? "—" : `${road.length_m} m` }}（核心依節點與彎點計算）</p>
      <p v-if="reverse" class="inspector__muted">
        反向：<button type="button" class="link" :data-select-road="roadRef(settlement.id, reverse.source, reverse.destination)" @click="emit('select', roadRef(settlement.id, reverse.source, reverse.destination))">{{ roadLabel(settlement, reverse) }}</button>
      </p>
      <p v-else class="inspector__muted">單向道路。</p>
      <h3 class="section-label">彎點 · {{ FRAME_LOCAL_M }}</h3>
      <ul class="plain">
        <li v-for="(point, index) in road.bends" :key="index">
          <button type="button" class="link" :data-select-bend="bendRef(single.road, index)" @click="emit('select', bendRef(single.road, index))">
            彎點 {{ index + 1 }} · {{ point[0] }}, {{ point[1] }}
          </button>
        </li>
        <li v-if="!road.bends.length" class="inspector__muted">沒有彎點（直線）。</li>
      </ul>
      <div class="inspector__actions">
        <button type="button" class="button" data-action="add-bend" @click="addBend(null, false)">◇ 加彎點</button>
        <button v-if="!reverse" type="button" class="button" data-action="reverse-road" @click="openRoad(road.destination, road.source)">⟵ 建立反向道路</button>
        <button type="button" class="button" data-action="delete-road" @click="emit('delete')">✕ 刪除道路</button>
      </div>
    </template>

    <!-- bend -->
    <template v-else-if="bend">
      <p class="inspector__muted">
        隸屬：<button type="button" class="link" data-owner-link @click="emit('select', single.road)">{{ roadLabel(settlement, road) }}</button>
        （{{ road.bends.length }} 個彎點）
      </p>
      <DraftField
        v-for="(axis, index) in ['東向', '北向']"
        :key="`${selection[0]}-${index}`"
        :label="axis"
        :field-key="`bend-${index}`"
        type="int"
        :unit="FRAME_LOCAL_M"
        :value="bend[index]"
        @confirm="setBendAxis(single.index, index, $event)"
        @drafts="track(`bend-${index}`)($event)"
      />
      <div class="inspector__actions">
        <button type="button" class="button" data-action="insert-bend-before" @click="addBend(single.index, true)">◇ 前方插入</button>
        <button type="button" class="button" data-action="insert-bend-after" @click="addBend(single.index, false)">◇ 後方插入</button>
        <button type="button" class="button" data-action="remove-bend" @click="dropBend(single.index)">✕ 移除彎點</button>
      </div>
    </template>

    <!-- one-document multi-selection -->
    <template v-else-if="group && groupNodes.length > 1">
      <h3 class="section-label">共同值</h3>
      <dl class="inspector__fields" data-mixed-values>
        <dt>原型</dt>
        <dd data-mixed="prototype_parent">{{ mixedValue(groupNodes, (row) => row.prototype_parent) }}</dd>
        <dt>場景</dt>
        <dd data-mixed="scene_archetype">{{ mixedValue(groupNodes, (row) => row.scene_archetype) }}</dd>
        <dt>東向</dt>
        <dd data-mixed="x">{{ mixedValue(groupNodes, (row) => row.local_m[0]) }}</dd>
        <dt>北向</dt>
        <dd data-mixed="y">{{ mixedValue(groupNodes, (row) => row.local_m[1]) }}</dd>
      </dl>
      <h3 class="section-label">整組位移 · {{ FRAME_LOCAL_M }}</h3>
      <form class="landmark" data-group-move @submit.prevent="applyDelta">
        <label class="draft-field">
          <span class="draft-field__label">東向位移<span class="draft-field__unit">{{ FRAME_LOCAL_M }}</span></span>
          <input v-model="delta.x" class="draft-field__input mono" inputmode="numeric" data-group-field="x" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">北向位移<span class="draft-field__unit">{{ FRAME_LOCAL_M }}</span></span>
          <input v-model="delta.y" class="draft-field__input mono" inputmode="numeric" data-group-field="y" />
        </label>
        <p v-if="deltaError" class="draft-field__hint" data-field-error="group">{{ deltaError }}</p>
        <div class="inspector__actions">
          <button type="submit" class="button" data-group-submit>套用位移（一次操作）</button>
          <button type="button" class="button" data-action="delete-nodes" @click="emit('delete')">✕ 刪除這些節點</button>
        </div>
      </form>
      <p class="inspector__note">同一份文件內的整組移動是一個可復原的操作；也可用 Shift+方向鍵每次移動 10 m。</p>
    </template>

    <!-- the open local map -->
    <template v-else-if="mapSettlement">
      <h3 class="section-label">本地圖 · {{ mapSettlement.id }}</h3>
      <p class="inspector__muted">
        地點 <span class="mono">{{ mapSettlement.location_ref }}</span> · {{ mapSettlement.nodes.length }} 個節點 · {{ mapSettlement.roads.length }} 條有向道路
      </p>
      <p v-if="!mapSettlement.nodes.length" class="warn" data-unfinished-map>▲ 尚無節點：這是未完成的地圖，不能作為可遊玩的地圖。用「節點 N」在畫布上新增。</p>
      <h3 class="section-label">地圖選項</h3>
      <form class="landmark" data-map-options @submit.prevent="submitOptions">
        <label class="draft-field">
          <span class="draft-field__label">視野 map_visual_range</span>
          <input v-model="options.map_visual_range" class="draft-field__input mono" inputmode="numeric" data-options-field="map_visual_range" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">模式 map_mode</span>
          <input v-model="options.map_mode" class="draft-field__input mono" data-options-field="map_mode" />
        </label>
        <p v-if="optionsDraft && optionsError" class="draft-field__hint" data-field-error="options">{{ optionsError }}</p>
        <div class="inspector__actions">
          <button type="submit" class="button" data-options-submit>套用選項</button>
          <button v-if="mapSettlement.options" type="button" class="button" data-action="remove-options" @click="send(settlementField(mapSettlement.id, 'options', null))">移除選項</button>
        </div>
      </form>
      <h3 class="section-label">出口原型</h3>
      <template v-if="mapSettlement.exit_prototype">
        <DraftField
          label="類型類別（空白為無）"
          field-key="exit-typeclass"
          type="nullable"
          :value="mapSettlement.exit_prototype.typeclass"
          @confirm="send(settlementField(mapSettlement.id, 'exit_prototype', { prototype_parent: mapSettlement.exit_prototype.prototype_parent, typeclass: $event }))"
          @drafts="track('exit-typeclass')($event)"
        />
        <button type="button" class="button" data-action="remove-exit-prototype" @click="send(settlementField(mapSettlement.id, 'exit_prototype', null))">移除出口原型</button>
      </template>
      <button v-else type="button" class="button" data-action="add-exit-prototype" @click="send(settlementField(mapSettlement.id, 'exit_prototype', { prototype_parent: 'xyz_exit', typeclass: null }))">
        ＋ 加入出口原型（xyz_exit）
      </button>
    </template>
  </div>
</template>
