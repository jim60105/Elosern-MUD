<script setup>
// The entrance creation form of the 入口 E / 外部入口 E tools (frontend design
// §4.2, §4.3, §4.4). On a settlement: a wilderness gate onto the picked node
// (with its return direction) or the one-way entry from the starting room.
// In an interior: the exterior doorway of the picked room onto a settlement
// node, or a special link to a room of any interior (two-way in the same
// record with a return name). Endpoints on another map are chosen with the
// qualified-object selector, so the submitted value is always a qualified
// ID. Submitting emits one named command on the owning document; the
// service validates it. Typed values live in the page-owned creation
// request, so a remount keeps them.
// Authored text renders through text interpolation only.
import { computed, nextTick, ref } from "vue";
import ObjectSelector from "./ObjectSelector.vue";
import { COMPASS, findSettlement } from "../lib/settlement.js";
import { findInterior } from "../lib/interior.js";
import {
  cityGateRef,
  createGate,
  createLink,
  exteriorRef,
  gateRef,
  linkRef,
  nodeRef,
  roomRef,
  setCityGate,
  setExterior,
} from "../lib/relationships.js";

const props = defineProps({
  world: { type: Object, required: true },
  catalog: { type: Map, required: true },
  domain: { type: String, required: true },
  mapId: { type: String, default: null },
  creation: { type: Object, required: true },
});
const emit = defineEmits(["create", "cancel"]);

const form = props.creation.defaults;
const submitted = ref(false);
const settlement = computed(() => (props.domain === "settlement" ? findSettlement(props.world, props.mapId) : null));
const interior = computed(() => (props.domain === "interior" ? findInterior(props.world, props.mapId) : null));
const nodeOptions = computed(() => (settlement.value?.nodes ?? []).map((row) => ({ value: nodeRef(settlement.value.id, row.id), label: `${row.key} · ${row.id}` })));
const roomOptions = computed(() => (interior.value?.rooms ?? []).map((row) => ({ value: roomRef(interior.value.id, row.id), label: `${row.name_zh} · ${row.id}` })));
const takenDirections = computed(() => new Set((settlement.value?.wilderness_entry?.gates ?? []).map((gate) => gate.return_direction)));
const lines = (text) => String(text ?? "").split("\n").map((item) => item.trim()).filter(Boolean);

const selecting = ref(null);
const trigger = ref(null);
const setTrigger = (element) => {
  if (element) trigger.value = element;
};
const RULES = { node: { kind: "node", mapId: null }, target: { kind: "room", mapId: null } };
function chooseTarget(key, value) {
  form[key] = value;
  closeSelector();
}
function closeSelector() {
  selecting.value = null;
  nextTick(() => trigger.value?.focus());
}

const error = computed(() => {
  const trimmed = (value) => String(value ?? "").trim();
  if (props.domain === "settlement") {
    if (!nodeOptions.value.some((option) => option.value === form.node)) return "請選擇這個據點的節點。";
    if (form.kind === "gate") {
      if (!form.direction) return "請選擇回程方向（不會依位置推斷）。";
      if (takenDirections.value.has(form.direction)) return "這個方向已有野外入口。";
      return null;
    }
    return trimmed(form.exit_key) ? null : "請輸入出口名稱。";
  }
  if (!roomOptions.value.some((option) => option.value === form.room)) return "請選擇這個室內的房間。";
  if (form.kind === "exterior") {
    if (!form.node) return "請用選擇器選擇據點節點。";
    return trimmed(form.doorway_key) ? null : "請輸入入口名稱。";
  }
  if (!form.target) return "請用選擇器選擇目標房間。";
  if (form.target === form.room) return "連結不能回到同一個房間。";
  if (!trimmed(form.label)) return "請輸入去程名稱。";
  if (form.two_way && !trimmed(form.return_label)) return "建立雙向時請輸入回程名稱。";
  return null;
});

function submit() {
  submitted.value = true;
  if (error.value) return;
  const trimmed = (value) => String(value ?? "").trim();
  if (props.domain === "settlement") {
    const id = settlement.value.id;
    if (form.kind === "gate") {
      emit("create", createGate(id, form.direction, form.node), gateRef(id, form.direction));
    } else {
      emit("create", setCityGate(id, { node: form.node, exit_key: trimmed(form.exit_key), exit_aliases: lines(form.exit_aliases) }), cityGateRef(id));
    }
    return;
  }
  const id = interior.value.id;
  if (form.kind === "exterior") {
    const value = { room: form.room, node: form.node, doorway_key: trimmed(form.doorway_key), doorway_aliases: lines(form.doorway_aliases) };
    emit("create", setExterior(id, value), exteriorRef(id));
    return;
  }
  const back = form.two_way ? trimmed(form.return_label) : null;
  const [, targetInterior, targetRoom] = /^interior_room:([^:]+):([^:]+)$/.exec(form.target);
  const sourceRoom = form.room.split(":").at(-1);
  const label = trimmed(form.label);
  emit(
    "create",
    createLink(id, form.room, form.target, label, back),
    linkRef(id, { source_room: sourceRoom, target_interior: targetInterior, target_room: targetRoom, label }),
  );
}

function onKey(event) {
  if (event.target.closest?.("[data-object-selector]")) return;
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    emit("cancel");
  } else if (event.key === "Enter" && !event.isComposing && event.target.tagName !== "TEXTAREA") {
    event.preventDefault();
    submit();
  }
}
</script>

<template>
  <form class="creation" data-creation="entrance" @submit.prevent="submit" @keydown="onKey">
    <h3 class="section-label">{{ domain === "settlement" ? "新入口" : "新外部入口" }}</h3>
    <fieldset class="creation__kinds">
      <legend class="draft-field__label">種類</legend>
      <template v-if="domain === 'settlement'">
        <label class="check"><input v-model="form.kind" type="radio" value="gate" data-creation-field="kind-gate" /> 野外入口（雙向）</label>
        <label class="check"><input v-model="form.kind" type="radio" value="city_gate" data-creation-field="kind-city_gate" /> 起始房間入口（單向）</label>
      </template>
      <template v-else>
        <label class="check"><input v-model="form.kind" type="radio" value="exterior" data-creation-field="kind-exterior" /> 據點外部入口（雙向）</label>
        <label class="check"><input v-model="form.kind" type="radio" value="link" data-creation-field="kind-link" /> 室內連結</label>
      </template>
    </fieldset>

    <template v-if="domain === 'settlement'">
      <label class="draft-field">
        <span class="draft-field__label">據點節點</span>
        <select v-model="form.node" class="draft-field__input" data-creation-field="node">
          <option value="">（請選擇）</option>
          <option v-for="option in nodeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </label>
      <template v-if="form.kind === 'gate'">
        <label class="draft-field">
          <span class="draft-field__label">回程方向（由野外進入據點的方向）</span>
          <select v-model="form.direction" class="draft-field__input" data-creation-field="direction">
            <option value="">（請選擇方向）</option>
            <option v-for="item in COMPASS" :key="item.value" :value="item.value">{{ item.label }} · {{ item.value }}</option>
          </select>
        </label>
        <p class="inspector__muted">一次操作寫入這份據點文件；{{ settlement?.wilderness_entry ? "加入現有的野外入口。" : "沒有野外入口時會在錨點格建立單格入口，可再用大陸的佔地工具擴大。" }}</p>
      </template>
      <template v-else>
        <label class="draft-field">
          <span class="draft-field__label">出口名稱</span>
          <input v-model="form.exit_key" class="draft-field__input" data-creation-field="exit_key" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">別名（一行一個）</span>
          <textarea v-model="form.exit_aliases" class="draft-field__input" rows="2" data-creation-field="exit_aliases" />
        </label>
        <p class="inspector__muted">起始房間入口固定為單向。{{ settlement?.city_gate ? "會取代這個據點目前的起始房間入口。" : "" }}</p>
      </template>
    </template>

    <template v-else>
      <label class="draft-field">
        <span class="draft-field__label">房間</span>
        <select v-model="form.room" class="draft-field__input" data-creation-field="room">
          <option value="">（請選擇）</option>
          <option v-for="option in roomOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </label>
      <template v-for="key in [form.kind === 'exterior' ? 'node' : 'target']" :key="key">
        <p class="draft-field__label">{{ key === "node" ? "據點節點" : "目標房間（任何室內）" }}</p>
        <p class="mono" :data-creation-value="key">{{ form[key] || "（尚未選擇）" }}</p>
        <button
          v-if="selecting !== key"
          :ref="setTrigger"
          type="button"
          class="button"
          :data-creation-choose="key"
          @click="selecting = key"
        >✎ 選擇…</button>
        <ObjectSelector
          v-else
          :catalog="catalog"
          :rule="RULES[key]"
          :label="key === 'node' ? '選擇據點節點' : '選擇目標房間'"
          :current="form[key] || null"
          :selector-key="`creation-${key}`"
          @choose="chooseTarget(key, $event)"
          @close="closeSelector"
        />
      </template>
      <template v-if="form.kind === 'exterior'">
        <label class="draft-field">
          <span class="draft-field__label">入口名稱（由據點進入）</span>
          <input v-model="form.doorway_key" class="draft-field__input" data-creation-field="doorway_key" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">別名（一行一個）</span>
          <textarea v-model="form.doorway_aliases" class="draft-field__input" rows="2" data-creation-field="doorway_aliases" />
        </label>
        <p class="inspector__muted">雙向：返回出口由遊戲提供。只寫入這份室內文件。{{ interior?.exterior ? "會取代這個室內目前的外部入口。" : "" }}</p>
      </template>
      <template v-else>
        <label class="draft-field">
          <span class="draft-field__label">去程名稱</span>
          <input v-model="form.label" class="draft-field__input" data-creation-field="label" />
        </label>
        <label class="check">
          <input v-model="form.two_way" type="checkbox" data-creation-field="two_way" />
          建立雙向
        </label>
        <label v-if="form.two_way" class="draft-field">
          <span class="draft-field__label">回程名稱</span>
          <input v-model="form.return_label" class="draft-field__input" data-creation-field="return_label" />
        </label>
        <p class="inspector__muted">一筆連結記錄兩個方向的意義；只寫入這份室內文件，不會寫入目標室內。</p>
      </template>
    </template>

    <p v-if="submitted && error" class="draft-field__hint" data-field-error="creation">{{ error }}</p>
    <div class="inspector__actions">
      <button type="submit" class="button" data-creation-submit>＋ 建立</button>
      <button type="button" class="button" data-creation-cancel @click="emit('cancel')">取消 Esc</button>
    </div>
  </form>
</template>
