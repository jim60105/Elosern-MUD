<script setup>
// Explicit continent editing controls (frontend design §4.1, §6 non-drag
// paths): control points with frame-labelled numeric fields and
// insert/remove actions, ridge and terrain parameters, passes, waterways,
// region prose/classifier fields, reserved sites, locations (with 開啟本地圖
// or 無本地圖), districts with a structured landmark selector, footprint
// masks and settlement bindings, the tool creation forms, and the derived
// results section. Every change is emitted as one named single-document
// command descriptor; the service validates it. Nothing is pre-disabled.
// Authored text renders through text interpolation only.
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import DraftField from "./DraftField.vue";
import FootprintGrid from "./FootprintGrid.vue";
import {
  FRAME_CELL,
  FRAME_KM,
  FRAME_LOCAL_M,
  RIDGE,
  addPass,
  addSite,
  addWaterway,
  binding,
  createLocation,
  districtField,
  featurePoints,
  footprintCell,
  footprintRef,
  fordFeatureRef,
  frameOf,
  insertPoint,
  locationField,
  movePoint,
  neighbourPoint,
  parseContinentRef,
  passRef,
  pointRef,
  regionField,
  removePass,
  removePoint,
  removeWaterway,
  setPass,
  siteField,
  terrainParameter,
  waterwayRef,
} from "../lib/continent.js";
import { partitionChip, partitionRevision } from "../lib/status.js";
import { createSettlement } from "../lib/settlement.js";

const props = defineProps({
  world: { type: Object, required: true },
  workspace: { type: Object, default: null },
  selected: { type: String, default: null },
  creation: { type: Object, default: null },
  hint: { type: String, default: null },
});
const emit = defineEmits(["send", "create", "cancel", "select", "follow", "drafts", "create-map", "partition"]);

// Draft counts of every open field, summed for the page's follow hold.
const counts = reactive({});
const total = computed(() => Object.values(counts).reduce((sum, value) => sum + value, 0));
watch(total, (value) => emit("drafts", value), { immediate: true });
onBeforeUnmount(() => emit("drafts", 0));
const track = (key) => (value) => {
  counts[key] = value;
};

const continent = computed(() => props.world.continent);
const parsed = computed(() => parseContinentRef(props.selected));
const locationId = computed(() => /^location:([a-z][a-z0-9_]*)$/.exec(props.selected ?? "")?.[1] ?? null);
const location = computed(() => props.world.locations.find((row) => row.id === locationId.value) ?? null);

const point = computed(() => {
  const p = parsed.value;
  if (!p?.feature || p.index === null) return null;
  const points = featurePoints(props.world, p.feature);
  const entry = points[p.index];
  return entry ? { ...entry, points, index: p.index, ford: p.kind === "ford" } : null;
});
const waterway = computed(() =>
  parsed.value?.kind === "waterway" && parsed.value.index === null
    ? continent.value.waterways.find((row) => row.id === parsed.value.id) ?? null
    : null,
);
const ridge = computed(() => (parsed.value?.kind === "ridge" ? continent.value.ridge : null));
const pass = computed(() => (parsed.value?.kind === "pass" ? continent.value.ridge?.passes?.[parsed.value.index] ?? null : null));
const site = computed(() =>
  parsed.value?.kind === "site" ? (continent.value.harbor_sites ?? []).find((row) => row.id === parsed.value.id) ?? null : null,
);
const region = computed(() =>
  parsed.value?.kind === "region" ? (continent.value.regions ?? []).find((row) => row.id === parsed.value.id) ?? null : null,
);
const district = computed(() =>
  parsed.value?.kind === "district" ? (props.world.districts ?? []).find((row) => row.id === parsed.value.id) ?? null : null,
);
const footprintSettlement = computed(() =>
  parsed.value?.kind === "footprint" ? props.world.settlements.find((row) => row.id === parsed.value.id) ?? null : null,
);
const locationSettlements = computed(() =>
  location.value ? props.world.settlements.filter((row) => row.location_ref === location.value.id) : [],
);

const LOCATION_KINDS = [
  { value: "capital", label: "capital · 首都" },
  { value: "elven_village", label: "elven_village · 精靈村落" },
  { value: "dungeon", label: "dungeon · 地城" },
];
const DISTRICT_KINDS = [
  { value: "voronoi", label: "voronoi · 依地標分割" },
  { value: "region", label: "region · 整個地形區" },
];
const regionOptions = computed(() => (continent.value.regions ?? []).map((row) => ({ value: row.id, label: `${row.id} · ${row.display_name_zh}` })));
const RIDGE_FIELDS = [
  { key: "base_x", label: "中心欄 base_x", unit: "欄 · 1 km 格" },
  { key: "period", label: "彎折週期 period", unit: "列數 · 1 km 格" },
  { key: "step", label: "彎折幅度 step", unit: "欄數 · 1 km 格" },
  { key: "min_x", label: "最西欄 min_x", unit: "欄 · 1 km 格" },
  { key: "max_x", label: "最東欄 max_x", unit: "欄 · 1 km 格" },
  { key: "north_limit_y", label: "北端列 north_limit_y", unit: "列 · 1 km 格" },
  { key: "mountain_corridor_half_width", label: "山地廊道半寬", unit: "欄數 · 1 km 格" },
];

const send = (descriptor) => emit("send", descriptor);

// -- control points -----------------------------------------------------------
function setAxis(axis, value) {
  const stored = [...point.value.stored];
  stored[axis] = value;
  send(movePoint(props.selected, stored));
}

function insertNear(before) {
  const p = parsed.value;
  const stored = neighbourPoint(point.value.points, point.value.index, before);
  send(insertPoint(p.feature, before ? point.value.index : point.value.index + 1, stored));
}

function addFord(id) {
  const route = featurePoints(props.world, waterwayRef(id));
  const fords = featurePoints(props.world, fordFeatureRef(id));
  const stored = route.length > 1 ? [Math.floor((route[0].stored[0] + route[1].stored[0]) / 2), Math.floor((route[0].stored[1] + route[1].stored[1]) / 2)] : route[0].stored;
  send(insertPoint(fordFeatureRef(id), fords.length, stored));
}

// -- districts ----------------------------------------------------------------
const landmark = reactive({ domain: "wilderness_cell", map_id: null, object_id: null, x: "", y: "" });
function loadLandmark() {
  const source = district.value?.landmark ?? {};
  landmark.domain = source.domain ?? "wilderness_cell";
  landmark.map_id = source.map_id ?? null;
  landmark.object_id = source.object_id ?? null;
  landmark.x = source.cell ? String(source.cell[0]) : "";
  landmark.y = source.cell ? String(source.cell[1]) : "";
}
watch(() => [props.selected, JSON.stringify(district.value?.landmark ?? null)], loadLandmark, { immediate: true });
const landmarkMaps = computed(() => {
  if (landmark.domain === "settlement_node") return props.world.settlements.map((row) => row.id);
  if (landmark.domain === "interior_room") return props.world.interiors.map((row) => row.id);
  return [];
});
const landmarkObjects = computed(() => {
  if (landmark.domain === "location") return props.world.locations.map((row) => ({ id: row.id, label: row.display_name_zh }));
  if (landmark.domain === "settlement_node") {
    const settlement = props.world.settlements.find((row) => row.id === landmark.map_id);
    return (settlement?.nodes ?? []).map((row) => ({ id: row.id, label: row.key }));
  }
  if (landmark.domain === "interior_room") {
    const interior = props.world.interiors.find((row) => row.id === landmark.map_id);
    return (interior?.rooms ?? []).map((row) => ({ id: row.id, label: row.name_zh }));
  }
  return [];
});
const landmarkValue = computed(() => {
  const scoped = landmark.domain === "settlement_node" || landmark.domain === "interior_room";
  const cell = landmark.domain === "wilderness_cell";
  const x = Number(landmark.x);
  const y = Number(landmark.y);
  return {
    domain: landmark.domain,
    map_id: scoped ? landmark.map_id : null,
    object_id: cell ? null : landmark.object_id,
    cell: cell ? [x, y] : null,
  };
});
const landmarkError = computed(() => {
  if (landmark.domain === "wilderness_cell") {
    return /^\d+$/.test(String(landmark.x).trim()) && /^\d+$/.test(String(landmark.y).trim()) ? null : "格座標需要非負整數（1 km 格）。";
  }
  return landmark.object_id ? null : "請選擇目標物件。";
});
const landmarkDraft = computed(() => {
  const source = district.value?.landmark;
  return Boolean(source) && JSON.stringify(landmarkValue.value) !== JSON.stringify({ ...source, cell: source.cell ?? null });
});
watch(landmarkDraft, (open) => {
  counts.landmark = open ? 1 : 0;
});
function onLandmarkDomain() {
  landmark.map_id = landmarkMaps.value[0] ?? null;
  landmark.object_id = null;
}
function onLandmarkMap() {
  landmark.object_id = null;
}
function submitLandmark() {
  if (landmarkError.value || !landmarkDraft.value) return;
  send(districtField(district.value.id, "landmark", landmarkValue.value));
}

function setMembership(kind, regionKey) {
  const key = kind === "region" ? regionKey ?? district.value.region_key ?? regionOptions.value[0]?.value ?? null : null;
  send(districtField(district.value.id, "membership", { kind, region_key: key }));
}

// -- bindings ------------------------------------------------------------------
function setBinding(settlement, part, axis, value) {
  const anchor = [...settlement.binding.anchor_cell];
  const local = [...settlement.binding.local_anchor_m];
  (part === "anchor" ? anchor : local)[axis] = value;
  send(binding(props.world, settlement.id, anchor, local));
}

// -- creation forms ---------------------------------------------------------------
const form = reactive({});
watch(
  () => props.creation,
  (creation) => {
    for (const key of Object.keys(form)) delete form[key];
    if (!creation) return;
    Object.assign(form, creation.defaults ?? {});
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
const formError = computed(() => {
  if (!props.creation) return null;
  if (!/^[a-z][a-z0-9_]*$/.test(String(form.id ?? ""))) return "ID 需為小寫英文、數字與底線，並以字母開頭。";
  if (props.creation.type === "pass") {
    return /^-?\d+$/.test(String(form.y_min).trim()) && /^-?\d+$/.test(String(form.y_max).trim()) ? null : "列範圍需要整數。";
  }
  if (props.creation.type === "location" && !String(form.display_name_zh ?? "").trim() && form.as !== "site") return "需要名稱。";
  return null;
});
function submitCreation() {
  const creation = props.creation;
  if (!creation || formError.value) return;
  if (creation.type === "location" && form.as === "site") {
    emit("create", addSite(form.id, { display_name: form.display_name_zh || form.id, role: form.description ?? "", cell: creation.cell }), `continent:site:${form.id}`);
  } else if (creation.type === "location") {
    emit(
      "create",
      createLocation(form.id, {
        kind: form.kind,
        display_name_zh: form.display_name_zh,
        description: form.description ?? "",
        geographic_constraint: form.geographic_constraint ?? "",
        scene_archetype: String(form.scene_archetype ?? "").trim() || null,
        cell: creation.cell,
      }),
      `location:${form.id}`,
    );
  } else if (creation.type === "waterway") {
    emit("create", addWaterway(form.id, creation.route), waterwayRef(form.id));
  } else if (creation.type === "pass") {
    emit("create", addPass(Number(form.y_min), Number(form.y_max)), passRef(continent.value.ridge?.passes?.length ?? 0));
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

// -- a new local map for the selected location (one new settlement document) --
const mapForm = reactive({ open: false, id: "", anchor_x: "", anchor_y: "", local_e: "0", local_n: "0", range: "", mode: "" });
function openMapForm() {
  const taken = new Set(props.world.settlements.map((row) => row.id));
  let id = location.value.id;
  for (let n = 2; taken.has(id); n += 1) id = `${location.value.id}_${n}`;
  Object.assign(mapForm, {
    open: true,
    id,
    anchor_x: String(location.value.cell[0]),
    anchor_y: String(location.value.cell[1]),
    local_e: "0",
    local_n: "0",
    range: "",
    mode: "",
  });
}
watch(() => mapForm.open, (open) => {
  counts.mapForm = open ? 1 : 0;
});
watch(() => props.selected, () => {
  mapForm.open = false;
});
const mapFormError = computed(() => {
  if (!mapForm.open) return null;
  if (!/^[a-z][a-z0-9_]*$/.test(mapForm.id)) return "ID 需為小寫英文、數字與底線，並以字母開頭。";
  if (props.world.settlements.some((row) => row.id === mapForm.id)) return "這個據點 ID 已存在。";
  if (![mapForm.anchor_x, mapForm.anchor_y].every((value) => /^\d+$/.test(String(value).trim()))) return "錨點格需要非負整數（1 km 格）。";
  if (![mapForm.local_e, mapForm.local_n].every((value) => /^-?\d+$/.test(String(value).trim()))) return "地方錨點需要整數公尺。";
  const range = String(mapForm.range).trim();
  const mode = String(mapForm.mode).trim();
  if ((range || mode) && !(/^\d+$/.test(range) && mode)) return "地圖選項需同時填寫整數視野與模式，或都留空。";
  return null;
});
const mapFormShown = ref(false);
function submitMapForm() {
  mapFormShown.value = true;
  if (mapFormError.value) return;
  const range = String(mapForm.range).trim();
  const options = range ? { map_visual_range: Number(range), map_mode: String(mapForm.mode).trim() } : null;
  emit(
    "create-map",
    createSettlement(
      mapForm.id,
      location.value.id,
      [Number(mapForm.anchor_x), Number(mapForm.anchor_y)],
      [Number(mapForm.local_e), Number(mapForm.local_n)],
      options,
    ),
    mapForm.id,
  );
  mapForm.open = false;
  mapFormShown.value = false;
}

// -- derived results ---------------------------------------------------------------
const preview = computed(() => continent.value.terrain_preview ?? null);
const partition = computed(() => props.workspace?.partition_status ?? null);
const partitionState = computed(() => partitionChip(props.workspace));
const revision = computed(() => partitionRevision(props.workspace));
const job = computed(() => props.workspace?.partition_job ?? null);
const generating = computed(() => partitionState.value.state === "generating");
</script>

<template>
  <div class="continent-inspector" data-continent-inspector>
    <!-- tool creation form -->
    <form v-if="creation" class="creation" :data-creation="creation.type" @submit.prevent="submitCreation" @keydown="onFormKey">
      <h3 class="section-label">
        {{ { location: "新地點", waterway: "新水系", pass: "新隘口" }[creation.type] }}
      </h3>
      <label class="draft-field">
        <span class="draft-field__label">ID（建立後不可更改）</span>
        <input v-model="form.id" class="draft-field__input mono" data-creation-field="id" />
      </label>
      <template v-if="creation.type === 'location'">
        <p class="inspector__muted">格 {{ creation.cell[0] }}, {{ creation.cell[1] }}（{{ FRAME_CELL }}）· 不建立本地圖或房間</p>
        <label class="draft-field">
          <span class="draft-field__label">建立為</span>
          <select v-model="form.as" class="draft-field__input" data-creation-field="as">
            <option value="location">地點（locations.yaml）</option>
            <option value="site">保留地點（continent.yaml）</option>
          </select>
        </label>
        <label v-if="form.as !== 'site'" class="draft-field">
          <span class="draft-field__label">種類</span>
          <select v-model="form.kind" class="draft-field__input" data-creation-field="kind">
            <option v-for="option in LOCATION_KINDS" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="draft-field">
          <span class="draft-field__label">名稱</span>
          <input v-model="form.display_name_zh" class="draft-field__input" data-creation-field="display_name_zh" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">{{ form.as === "site" ? "角色" : "描述" }}</span>
          <textarea v-model="form.description" class="draft-field__input" rows="2" data-creation-field="description" />
        </label>
      </template>
      <template v-else-if="creation.type === 'waterway'">
        <p class="inspector__muted">
          起點格 {{ creation.route[0][0] }}, {{ creation.route[0][1] }} → 終點格 {{ creation.route[1][0] }}, {{ creation.route[1][1] }}（{{ FRAME_CELL }}）
        </p>
      </template>
      <template v-else-if="creation.type === 'pass'">
        <label class="draft-field">
          <span class="draft-field__label">南端列 y_min<span class="draft-field__unit">列 · {{ FRAME_CELL }}</span></span>
          <input v-model="form.y_min" class="draft-field__input mono" data-creation-field="y_min" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">北端列 y_max<span class="draft-field__unit">列 · {{ FRAME_CELL }}</span></span>
          <input v-model="form.y_max" class="draft-field__input mono" data-creation-field="y_max" />
        </label>
      </template>
      <p v-if="formError" class="draft-field__hint" data-field-error="creation">{{ formError }}</p>
      <div class="inspector__actions">
        <button type="submit" class="button" data-creation-submit>＋ 建立</button>
        <button type="button" class="button" data-creation-cancel @click="emit('cancel')">取消 Esc</button>
      </div>
    </form>
    <p v-else-if="hint" class="inspector__reason" data-tool-hint>{{ hint }}</p>

    <!-- control point -->
    <template v-if="point">
      <p class="inspector__muted">
        隸屬：<button type="button" class="link" data-owner-link @click="emit('select', point.ford ? waterwayRef(parsed.id) : parsed.feature)">
          {{ point.ford ? `水系 ${parsed.id}` : parsed.kind === "waterway" ? `水系 ${parsed.id}` : parsed.kind === "mainland" ? "大陸海岸線" : "北部林線" }}
        </button>
        （{{ point.points.length }} 個{{ point.ford ? "渡口" : "控制點" }}）
      </p>
      <DraftField
        v-for="(axis, index) in ['東向', '北向']"
        :key="`${selected}-${index}`"
        :label="axis"
        :field-key="`point-${index}`"
        type="int"
        :unit="frameOf(selected)"
        :value="point.stored[index]"
        @confirm="setAxis(index, $event)"
        @drafts="track(`point-${index}`)($event)"
      />
      <div class="inspector__actions">
        <template v-if="!point.ford">
          <button type="button" class="button" data-action="insert-before" @click="insertNear(true)">◇ 前方插入</button>
          <button type="button" class="button" data-action="insert-after" @click="insertNear(false)">◇ 後方插入</button>
        </template>
        <button type="button" class="button" data-action="remove-point" @click="send(removePoint(selected))">✕ 移除{{ point.ford ? "渡口" : "控制點" }}</button>
      </div>
    </template>

    <!-- waterway feature -->
    <template v-else-if="waterway">
      <h3 class="section-label">控制點 · {{ FRAME_CELL }}</h3>
      <ul class="plain">
        <li v-for="(cell, index) in waterway.route" :key="index">
          <button type="button" class="link" :data-select-point="pointRef(waterwayRef(waterway.id), index)" @click="emit('select', pointRef(waterwayRef(waterway.id), index))">
            控制點 {{ index + 1 }} · {{ cell[0] }}, {{ cell[1] }}
          </button>
        </li>
      </ul>
      <h3 class="section-label">渡口 · {{ FRAME_CELL }}</h3>
      <ul class="plain">
        <li v-for="(cell, index) in waterway.fords" :key="index">
          <button type="button" class="link" @click="emit('select', pointRef(fordFeatureRef(waterway.id), index))">渡口 {{ index + 1 }} · {{ cell[0] }}, {{ cell[1] }}</button>
        </li>
      </ul>
      <div class="inspector__actions">
        <button type="button" class="button" data-action="add-ford" @click="addFord(waterway.id)">＋ 加渡口</button>
        <button
          v-if="waterway.id !== continent.border_river_key"
          type="button"
          class="button"
          data-action="border-river"
          @click="send(terrainParameter('border_river_key', waterway.id))"
        >
          設為國界河
        </button>
        <button type="button" class="button" data-action="remove-waterway" @click="send(removeWaterway(waterway.id))">✕ 移除水系</button>
      </div>
    </template>

    <!-- mainland / forest features: their points -->
    <template v-else-if="parsed && parsed.feature && parsed.index === null">
      <h3 class="section-label">控制點 · {{ frameOf(selected) }}</h3>
      <ul class="plain">
        <li v-for="(entry, index) in featurePoints(world, selected)" :key="index">
          <button type="button" class="link" :data-select-point="pointRef(selected, index)" @click="emit('select', pointRef(selected, index))">
            控制點 {{ index + 1 }} · {{ entry.stored[0] }}, {{ entry.stored[1] }}
          </button>
        </li>
      </ul>
      <p class="inspector__muted">選取控制點後可輸入數值、插入或移除；也可用「加控制點 A」在畫布上點選位置。</p>
    </template>

    <!-- ridge -->
    <template v-else-if="ridge">
      <DraftField
        v-for="field in RIDGE_FIELDS"
        :key="`ridge-${field.key}`"
        :label="field.label"
        :field-key="`ridge-${field.key}`"
        type="int"
        :unit="field.unit"
        :value="ridge[field.key]"
        @confirm="send(terrainParameter(`ridge.${field.key}`, $event))"
        @drafts="track(`ridge-${field.key}`)($event)"
      />
      <DraftField
        label="海岸帶北界 coastal_y_max"
        field-key="coastal_y_max"
        type="int"
        unit="列 · 1 km 格"
        :value="continent.coastal_y_max"
        @confirm="send(terrainParameter('coastal_y_max', $event))"
        @drafts="track('coastal')($event)"
      />
      <h3 class="section-label">隘口</h3>
      <ul class="plain">
        <li v-for="(window, index) in ridge.passes" :key="index">
          <button type="button" class="link" @click="emit('select', passRef(index))">隘口 {{ index + 1 }} · 列 {{ window.y_min }}–{{ window.y_max }}</button>
        </li>
      </ul>
      <p class="inspector__muted">用「山脊」工具在畫布上點選列位置以新增隘口。</p>
    </template>

    <!-- pass -->
    <template v-else-if="pass">
      <DraftField
        label="南端列 y_min"
        :field-key="`pass-min-${parsed.index}`"
        type="int"
        unit="列 · 1 km 格"
        :value="pass.y_min"
        @confirm="send(setPass(parsed.index, $event, pass.y_max))"
        @drafts="track('pass-min')($event)"
      />
      <DraftField
        label="北端列 y_max"
        :field-key="`pass-max-${parsed.index}`"
        type="int"
        unit="列 · 1 km 格"
        :value="pass.y_max"
        @confirm="send(setPass(parsed.index, pass.y_min, $event))"
        @drafts="track('pass-max')($event)"
      />
      <p class="inspector__muted">隸屬：<button type="button" class="link" @click="emit('select', RIDGE)">中央山脊</button></p>
      <div class="inspector__actions">
        <button type="button" class="button" data-action="remove-pass" @click="send(removePass(parsed.index))">✕ 移除隘口</button>
      </div>
    </template>

    <!-- reserved site -->
    <template v-else-if="site">
      <DraftField label="名稱" field-key="site-name" :value="site.display_name" @confirm="send(siteField(site.id, 'display_name', $event))" @drafts="track('site-name')($event)" />
      <DraftField label="角色" field-key="site-role" :value="site.role" @confirm="send(siteField(site.id, 'role', $event))" @drafts="track('site-role')($event)" />
      <DraftField
        v-for="(axis, index) in ['東向格', '北向格']"
        :key="`site-${index}`"
        :label="axis"
        :field-key="`site-cell-${index}`"
        type="int"
        :unit="FRAME_CELL"
        :value="site.cell[index]"
        @confirm="send(siteField(site.id, 'cell', index ? [site.cell[0], $event] : [$event, site.cell[1]]))"
        @drafts="track(`site-cell-${index}`)($event)"
      />
    </template>

    <!-- region -->
    <template v-else-if="region">
      <DraftField label="名稱" field-key="region-name" :value="region.display_name_zh" @confirm="send(regionField(region.id, 'display_name_zh', $event))" @drafts="track('region-name')($event)" />
      <DraftField label="國家鍵（空白為無）" field-key="region-nation" type="nullable" :value="region.nation_key" @confirm="send(regionField(region.id, 'nation_key', $event))" @drafts="track('region-nation')($event)" />
      <DraftField label="名義國家鍵（逗號分隔）" field-key="region-nominal" type="list" :value="region.nominal_nation_keys ?? []" @confirm="send(regionField(region.id, 'nominal_nation_keys', $event))" @drafts="track('region-nominal')($event)" />
      <DraftField label="場景（空白為無）" field-key="region-scene" type="nullable" :value="region.scene_archetype" @confirm="send(regionField(region.id, 'scene_archetype', $event))" @drafts="track('region-scene')($event)" />
      <DraftField
        v-if="!(region.terrain_flavor_zh ?? []).some((line) => line.includes('\n'))"
        label="地形描述變體（每行一則）"
        field-key="region-flavor"
        type="lines"
        :value="region.terrain_flavor_zh ?? []"
        note="至少兩則；由核心結構檢查。"
        @confirm="send(regionField(region.id, 'terrain_flavor_zh', $event))"
        @drafts="track('region-flavor')($event)"
      />
      <p v-else class="inspector__muted">含換行的描述變體無法逐行編輯，請在外部修改。</p>
    </template>

    <!-- location -->
    <template v-else-if="location">
      <h3 class="section-label">本地圖</h3>
      <p v-if="!location.local_maps.length" class="inspector__muted" data-local-map="absent">無本地圖 · 不會顯示或建立任何房間；建立本地圖只寫入一份新的據點文件。</p>
      <ul v-else class="plain">
        <li v-for="mapId in location.local_maps" :key="mapId">
          <button type="button" class="button" :data-open-local-map="mapId" @click="emit('follow', `settlement:${mapId}`)">開啟本地圖 {{ mapId }}</button>
        </li>
      </ul>
      <button v-if="!mapForm.open" type="button" class="button" data-action="create-local-map" @click="openMapForm">＋ 建立本地圖</button>
      <form v-else class="creation" data-creation="settlement" @submit.prevent="submitMapForm" @keydown.esc.stop.prevent="mapForm.open = false">
        <label class="draft-field">
          <span class="draft-field__label">據點 ID（建立後不可更改）</span>
          <input v-model="mapForm.id" class="draft-field__input mono" data-map-field="id" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">錨點東向格<span class="draft-field__unit">{{ FRAME_CELL }}</span></span>
          <input v-model="mapForm.anchor_x" class="draft-field__input mono" data-map-field="anchor_x" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">錨點北向格<span class="draft-field__unit">{{ FRAME_CELL }}</span></span>
          <input v-model="mapForm.anchor_y" class="draft-field__input mono" data-map-field="anchor_y" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">地方錨點東<span class="draft-field__unit">{{ FRAME_LOCAL_M }}</span></span>
          <input v-model="mapForm.local_e" class="draft-field__input mono" data-map-field="local_e" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">地方錨點北<span class="draft-field__unit">{{ FRAME_LOCAL_M }}</span></span>
          <input v-model="mapForm.local_n" class="draft-field__input mono" data-map-field="local_n" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">地圖選項：視野（可留空）</span>
          <input v-model="mapForm.range" class="draft-field__input mono" data-map-field="range" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">地圖選項：模式（可留空）</span>
          <input v-model="mapForm.mode" class="draft-field__input mono" data-map-field="mode" />
        </label>
        <p class="inspector__muted">新地圖沒有節點或道路，會標示為未完成；不會寫入地點文件。</p>
        <p v-if="mapFormShown && mapFormError" class="draft-field__hint" data-field-error="local-map">{{ mapFormError }}</p>
        <div class="inspector__actions">
          <button type="submit" class="button" data-map-submit>＋ 建立本地圖</button>
          <button type="button" class="button" @click="mapForm.open = false">取消 Esc</button>
        </div>
      </form>
      <DraftField label="名稱" field-key="location-name" :value="location.display_name_zh" @confirm="send(locationField(location.id, 'display_name_zh', $event))" @drafts="track('location-name')($event)" />
      <DraftField label="種類" field-key="location-kind" type="select" :options="LOCATION_KINDS" :value="location.kind" @confirm="send(locationField(location.id, 'kind', $event))" />
      <DraftField label="描述" field-key="location-description" type="textarea" :value="location.description" @confirm="send(locationField(location.id, 'description', $event))" @drafts="track('location-description')($event)" />
      <DraftField label="地理限制" field-key="location-constraint" :value="location.geographic_constraint ?? ''" @confirm="send(locationField(location.id, 'geographic_constraint', $event))" @drafts="track('location-constraint')($event)" />
      <DraftField label="場景（空白為無）" field-key="location-scene" type="nullable" :value="location.scene_archetype" @confirm="send(locationField(location.id, 'scene_archetype', $event))" @drafts="track('location-scene')($event)" />
      <DraftField
        v-for="(axis, index) in ['東向格', '北向格']"
        :key="`location-${index}`"
        :label="axis"
        :field-key="`location-cell-${index}`"
        type="int"
        :unit="FRAME_CELL"
        :value="location.cell[index]"
        @confirm="send(locationField(location.id, 'cell', index ? [location.cell[0], $event] : [$event, location.cell[1]]))"
        @drafts="track(`location-cell-${index}`)($event)"
      />
      <template v-for="settlement in locationSettlements" :key="settlement.id">
        <p v-if="settlement.footprint" class="inspector__muted">
          佔地：<button type="button" class="link" :data-select-footprint="settlement.id" @click="emit('select', footprintRef(settlement.id))">{{ settlement.id }} 佔地</button>
        </p>
      </template>
    </template>

    <!-- district -->
    <template v-else-if="district">
      <DraftField label="分區名稱" field-key="district-name" :value="district.district_name_zh" @confirm="send(districtField(district.id, 'district_name_zh', $event))" @drafts="track('district-name')($event)" />
      <DraftField label="地標名稱" field-key="district-landmark-name" :value="district.landmark_name_zh" @confirm="send(districtField(district.id, 'landmark_name_zh', $event))" @drafts="track('district-landmark-name')($event)" />
      <DraftField label="種類" field-key="district-kind" type="select" :options="DISTRICT_KINDS" :value="district.kind" @confirm="setMembership($event, null)" />
      <DraftField
        v-if="district.kind === 'region'"
        label="地形區"
        field-key="district-region"
        type="select"
        :options="regionOptions"
        :value="district.region_key"
        @confirm="setMembership('region', $event)"
      />
      <h3 class="section-label">地標 · 穩定參照</h3>
      <form class="landmark" data-landmark-selector @submit.prevent="submitLandmark">
        <label class="draft-field">
          <span class="draft-field__label">領域</span>
          <select v-model="landmark.domain" class="draft-field__input" data-landmark-field="domain" @change="onLandmarkDomain">
            <option value="settlement_node">settlement_node · 據點節點</option>
            <option value="interior_room">interior_room · 室內房間</option>
            <option value="location">location · 地點</option>
            <option value="wilderness_cell">wilderness_cell · 野外格</option>
          </select>
        </label>
        <label v-if="landmarkMaps.length" class="draft-field">
          <span class="draft-field__label">地圖</span>
          <select v-model="landmark.map_id" class="draft-field__input" data-landmark-field="map_id" @change="onLandmarkMap">
            <option v-for="id in landmarkMaps" :key="id" :value="id">{{ id }}</option>
          </select>
        </label>
        <label v-if="landmark.domain !== 'wilderness_cell'" class="draft-field">
          <span class="draft-field__label">物件</span>
          <select v-model="landmark.object_id" class="draft-field__input" data-landmark-field="object_id">
            <option :value="null">（請選擇）</option>
            <option v-for="item in landmarkObjects" :key="item.id" :value="item.id">{{ item.label }} · {{ item.id }}</option>
          </select>
        </label>
        <template v-else>
          <label class="draft-field">
            <span class="draft-field__label">東向格<span class="draft-field__unit">{{ FRAME_CELL }}</span></span>
            <input v-model="landmark.x" class="draft-field__input mono" data-landmark-field="x" />
          </label>
          <label class="draft-field">
            <span class="draft-field__label">北向格<span class="draft-field__unit">{{ FRAME_CELL }}</span></span>
            <input v-model="landmark.y" class="draft-field__input mono" data-landmark-field="y" />
          </label>
        </template>
        <p v-if="landmarkDraft && landmarkError" class="draft-field__hint" data-field-error="landmark">{{ landmarkError }}</p>
        <p v-else-if="landmarkDraft" class="draft-field__hint">草稿 · 套用後存檔；送出的值永遠是限定參照。</p>
        <div class="inspector__actions">
          <button type="submit" class="button" data-landmark-submit>套用地標</button>
          <button v-if="landmarkDraft" type="button" class="button" @click="loadLandmark">取消</button>
        </div>
      </form>
    </template>

    <!-- footprint and binding -->
    <template v-else-if="footprintSettlement">
      <h3 class="section-label">佔地遮罩 · {{ FRAME_CELL }}</h3>
      <FootprintGrid
        :footprint="footprintSettlement.footprint"
        :settlement-id="footprintSettlement.id"
        @toggle="send(footprintCell(world, footprintSettlement.id, $event.cell, $event.filled))"
      />
      <p class="inspector__note">只寫入 {{ footprintSettlement.relative_path }}；「佔地」工具也可在畫布上逐格切換。</p>
      <h3 class="section-label">綁定 · 地方 ⇄ 世界</h3>
      <DraftField
        v-for="(axis, index) in ['錨點東向格', '錨點北向格']"
        :key="`anchor-${index}`"
        :label="axis"
        :field-key="`binding-anchor-${index}`"
        type="int"
        :unit="FRAME_CELL"
        :value="footprintSettlement.binding.anchor_cell[index]"
        @confirm="setBinding(footprintSettlement, 'anchor', index, $event)"
        @drafts="track(`binding-anchor-${index}`)($event)"
      />
      <DraftField
        v-for="(axis, index) in ['地方錨點東', '地方錨點北']"
        :key="`local-${index}`"
        :label="axis"
        :field-key="`binding-local-${index}`"
        type="int"
        :unit="FRAME_LOCAL_M"
        :value="footprintSettlement.binding.local_anchor_m[index]"
        @confirm="setBinding(footprintSettlement, 'local', index, $event)"
        @drafts="track(`binding-local-${index}`)($event)"
      />
      <p class="inspector__note">世界公尺 = 錨點格中心 + 地方公尺 − 地方錨點；室內房間沒有公尺座標。</p>
    </template>

    <!-- derived results (design §4.1) -->
    <template v-if="parsed || location">
      <h3 class="section-label">衍生結果 · 唯讀</h3>
      <p data-derived="terrain">
        地形預覽：
        <span v-if="preview?.status === 'current'" class="ok">✓ 依目前輸入由核心推導</span>
        <span v-else class="warn">▲ 無法推導（{{ preview?.reason ?? "—" }}）</span>
      </p>
      <p data-derived="partition" :data-partition-state="partitionState.state" :data-artifact-state="partition?.status ?? 'loading'">
        分區：{{ partitionState.glyph }} {{ partitionState.text }}
        <span v-if="revision" class="mono" data-partition-revision>
          （產物輸入 {{ revision.output }} · 現行輸入 {{ revision.current }}）
        </span>
      </p>
      <p v-if="revision?.older" class="warn" data-partition-older>▲ 畫面上的分區輪廓屬於舊輸入，重新產生成功前不可作為遊戲就緒。</p>
      <ul v-if="job?.state === 'failed' && job.problems?.length" class="inspector__muted" data-partition-problems>
        <li v-for="(line, index) in job.problems" :key="index" class="mono">{{ line }}</li>
      </ul>
      <div class="inspector__actions">
        <button v-if="generating" type="button" class="button" data-action="partition-cancel" @click="emit('partition', 'cancel')">
          ✕ 取消產生
        </button>
        <button v-else type="button" class="button" data-action="partition-generate" @click="emit('partition', 'generate')">
          ⟳ 重新產生分區
        </button>
      </div>
      <p class="inspector__muted">國界與分區由輸入推導，沒有可編輯的控制點；編輯不會自動重新產生分區，只有這個按鈕或狀態列的分區按鈕會產生。</p>
    </template>
  </div>
</template>
