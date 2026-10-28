<script setup>
// Explicit interior editing controls (frontend design §4.3, §6 non-drag
// paths): room fields (name, multiline description, scene from the current
// index, art key) with the read-only room ID and the read-only service
// identity of a joined room, directed named connections with explicit
// endpoint selectors and labels (two-way in one operation), duplication with
// a new ID, and the open interior's actions (new room, 自動排列, new
// interior, removing the document). Every change is emitted as one named
// single-document command descriptor through `submit`; the service
// validates it. Interiors have no coordinates or distances: layout positions
// are editor-only and never shown as metres.
// Authored text renders through text interpolation only.
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import DraftField from "./DraftField.vue";
import {
  IDENTIFIER,
  blankRoom,
  connectionRef,
  connectionRows,
  createConnection,
  createInterior,
  createRoom,
  duplicateRoom,
  findConnection,
  findInterior,
  parseInteriorRef,
  reverseOf,
  roomFields,
  roomName,
  roomRef,
  serviceIdentity,
  setConnection,
} from "../lib/interior.js";
import { nextId } from "../lib/continent.js";

const props = defineProps({
  world: { type: Object, required: true },
  workspace: { type: Object, default: null },
  interiorId: { type: String, default: null },
  selection: { type: Array, default: () => [] },
  creation: { type: Object, default: null },
  hint: { type: String, default: null },
  // Queues one command descriptor and resolves with the service's answer.
  submit: { type: Function, required: true },
  // Selects a reference; a plain callback because the answer can arrive
  // after this instance unmounted (the old reference left the snapshot).
  choose: { type: Function, required: true },
});
const emit = defineEmits(["create", "cancel", "select", "drafts", "open", "delete", "arrange", "delete-interior"]);

const counts = reactive({});
const total = computed(() => Object.values(counts).reduce((sum, value) => sum + value, 0));
watch(total, (value) => emit("drafts", value), { immediate: true });
onBeforeUnmount(() => emit("drafts", 0));
const track = (key) => (value) => {
  counts[key] = value;
};
const send = (descriptor) => props.submit(descriptor);

const single = computed(() => (props.selection.length === 1 ? parseInteriorRef(props.selection[0]) : null));
const interior = computed(() => findInterior(props.world, single.value?.interiorId ?? props.interiorId));
const room = computed(() =>
  single.value?.kind === "room" ? interior.value?.rooms.find((row) => row.id === single.value.roomId) ?? null : null,
);
const connection = computed(() =>
  single.value?.kind === "connection"
    ? findConnection(interior.value, single.value.source, single.value.destination, single.value.label)
    : null,
);
const roomOptions = computed(() => (interior.value?.rooms ?? []).map((row) => ({ value: row.id, label: `${row.name_zh} · ${row.id}` })));

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

// -- room ------------------------------------------------------------------------
function setField(key, value) {
  send(roomFields(interior.value.id, room.value.id, { [key]: value }));
}
const rows = computed(() => (room.value ? connectionRows(interior.value, room.value.id) : { outgoing: [], incoming: [] }));
const services = computed(() =>
  room.value ? serviceIdentity(props.workspace?.external_incoming_references ?? {}, room.value.qualified_ref) : [],
);
function allRoomIds() {
  return props.world.interiors.flatMap((row) => row.rooms.map((item) => item.id));
}
function openDuplicate() {
  emit("open", { type: "duplicate", defaults: { room_id: room.value.id, id: nextId(room.value.id, allRoomIds()) } });
}
function openConnection(source, destination = "") {
  emit("open", { type: "connection", defaults: { source, destination, label: "", two_way: false, return_label: "" } });
}

// -- connection ------------------------------------------------------------------
const reverse = computed(() => (connection.value ? reverseOf(interior.value, connection.value) : null));
function retarget(part, value) {
  const current = connection.value;
  const next = { source: current.source, destination: current.destination, label: current.label, [part]: value };
  if (part === "label") next.label = String(value ?? "").trim();
  if (!next.label) return;
  const id = interior.value.id;
  send(setConnection(id, current.source, current.destination, current.label, next)).then((result) => {
    // The editor-local reference names the endpoints and the label: follow it.
    if (result?.changed) props.choose(connectionRef(id, next.source, next.destination, next.label));
  });
}

// -- creation forms -----------------------------------------------------------------
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
const submitted = ref(false);
watch(() => props.creation, () => (submitted.value = false));
const takenRoom = (id) => props.world.interiors.find((row) => row.rooms.some((item) => item.id === id)) ?? null;
const formError = computed(() => {
  const creation = props.creation;
  if (!creation) return null;
  const rooms = interior.value?.rooms ?? [];
  const known = (id) => rooms.some((row) => row.id === id);
  if (creation.type === "connection") {
    if (!known(form.source) || !known(form.destination)) return "請選擇現有的起點與終點房間。";
    if (form.source === form.destination) return "起點與終點不可相同。";
    if (!String(form.label ?? "").trim()) return "請輸入連接名稱（出口名稱）。";
    if (form.two_way && !String(form.return_label ?? "").trim()) return "建立雙向時請輸入回程名稱。";
    return null;
  }
  if (creation.type === "interior") {
    if (!IDENTIFIER.test(String(form.interior_id ?? ""))) return "室內 ID 需為小寫英文、數字與底線，並以字母開頭。";
    if (findInterior(props.world, form.interior_id)) return "這個室內 ID 已存在。";
  }
  if (!IDENTIFIER.test(String(form.id ?? ""))) return "ID 需為小寫英文、數字與底線，並以字母開頭。";
  if (takenRoom(form.id)) return "這個房間 ID 已被使用；每個房間在所有室內中只有一個身分。";
  if (creation.type === "duplicate") return known(form.room_id) ? null : "原房間已不存在。";
  if (!String(form.name_zh ?? "").trim()) return "需要名稱。";
  return null;
});
// A new room ID that already exists links to the existing room (design §5.3).
const duplicateRef = computed(() => {
  if (!props.creation || props.creation.type === "connection") return null;
  const owner = takenRoom(form.id);
  return owner ? roomRef(owner.id, form.id) : null;
});
function submitCreation() {
  submitted.value = true;
  const creation = props.creation;
  if (!creation || formError.value) return;
  const fields = () => blankRoom({ name_zh: String(form.name_zh).trim(), desc_zh: form.desc_zh ?? "" });
  if (creation.type === "interior") {
    emit("create", createInterior(form.interior_id, form.id, fields()), roomRef(form.interior_id, form.id), form.interior_id);
    return;
  }
  const id = interior.value.id;
  if (creation.type === "connection") {
    const label = String(form.label).trim();
    const back = form.two_way ? String(form.return_label).trim() : null;
    emit("create", createConnection(id, form.source, form.destination, label, back), connectionRef(id, form.source, form.destination, label));
  } else if (creation.type === "duplicate") {
    emit("create", duplicateRoom(id, form.room_id, form.id), roomRef(id, form.id));
  } else {
    emit("create", createRoom(id, form.id, fields()), roomRef(id, form.id));
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
const TITLES = { interior: "新室內", room: "新房間", duplicate: "複製為新房間", connection: "新連接" };

function openRoom() {
  emit("open", { type: "room", defaults: { id: nextId("room", allRoomIds()), name_zh: "", desc_zh: "" } });
}
function openInterior() {
  const ids = props.world.interiors.map((row) => row.id);
  emit("open", { type: "interior", defaults: { interior_id: nextId("interior", ids), id: nextId("room", allRoomIds()), name_zh: "", desc_zh: "" } });
}
const mapInterior = computed(() => (!props.selection.length ? findInterior(props.world, props.interiorId) : null));
</script>

<template>
  <div class="interior-inspector" data-interior-inspector>
    <!-- creation forms -->
    <form v-if="creation" class="creation" :data-creation="creation.type" @submit.prevent="submitCreation" @keydown="onFormKey">
      <h3 class="section-label">{{ TITLES[creation.type] }}</h3>
      <template v-if="creation.type === 'connection'">
        <label class="draft-field">
          <span class="draft-field__label">起點房間</span>
          <select v-model="form.source" class="draft-field__input" data-creation-field="source">
            <option value="">（請選擇）</option>
            <option v-for="option in roomOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="draft-field">
          <span class="draft-field__label">終點房間</span>
          <select v-model="form.destination" class="draft-field__input" data-creation-field="destination">
            <option value="">（請選擇）</option>
            <option v-for="option in roomOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="draft-field">
          <span class="draft-field__label">去程名稱（出口名稱）</span>
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
        <p class="inspector__muted">
          {{ form.two_way ? "一次操作建立兩筆有向連接，寫入同一份室內文件。" : "只建立一筆有向連接（單向）。" }}室內連接沒有距離或路線長度。
        </p>
      </template>
      <template v-else>
        <label v-if="creation.type === 'interior'" class="draft-field">
          <span class="draft-field__label">室內 ID（建立後不可更改）</span>
          <input v-model="form.interior_id" class="draft-field__input mono" data-creation-field="interior_id" />
        </label>
        <label class="draft-field">
          <span class="draft-field__label">{{ creation.type === "interior" ? "第一個房間 ID" : "房間 ID" }}（建立後不可更改）</span>
          <input v-model="form.id" class="draft-field__input mono" data-creation-field="id" />
        </label>
        <p v-if="creation.type === 'duplicate'" class="inspector__muted" data-duplicate-note>
          複製名稱、描述、場景與美術鍵；不複製連接、外部入口、室內連結或地標，也不改寫任何指向原房間的引用。
        </p>
        <template v-else>
          <label class="draft-field">
            <span class="draft-field__label">名稱</span>
            <input v-model="form.name_zh" class="draft-field__input" data-creation-field="name_zh" />
          </label>
          <label class="draft-field">
            <span class="draft-field__label">描述</span>
            <textarea v-model="form.desc_zh" class="draft-field__input" rows="2" data-creation-field="desc_zh" />
          </label>
          <p class="inspector__muted">只寫入這份室內文件；不需要也不會建立服務、NPC 或版面紀錄。新房間先依清單位置顯示。</p>
        </template>
      </template>
      <p v-if="submitted && formError" class="draft-field__hint" data-field-error="creation">
        {{ formError }}
        <button v-if="duplicateRef" type="button" class="link" :data-follow="duplicateRef" @click="emit('select', duplicateRef)">前往現有房間</button>
      </p>
      <div class="inspector__actions">
        <button type="submit" class="button" data-creation-submit>＋ 建立</button>
        <button type="button" class="button" data-creation-cancel @click="emit('cancel')">取消 Esc</button>
      </div>
    </form>
    <p v-else-if="hint" class="inspector__reason" data-tool-hint>{{ hint }}</p>

    <!-- room -->
    <template v-if="room">
      <p class="inspector__muted">房間 ID <span class="mono">{{ room.id }}</span> 是穩定身分，建立後不可更改。</p>
      <DraftField
        :key="`${selection[0]}-name`"
        label="名稱"
        field-key="room-name_zh"
        :value="room.name_zh"
        @confirm="setField('name_zh', $event)"
        @drafts="track('room-name')($event)"
      />
      <DraftField
        :key="`${selection[0]}-desc`"
        label="描述"
        field-key="room-desc_zh"
        type="textarea"
        :value="room.desc_zh"
        @confirm="setField('desc_zh', $event)"
        @drafts="track('room-desc')($event)"
      />
      <DraftField
        v-if="scenes"
        label="場景"
        field-key="room-scene_archetype"
        type="select"
        :options="sceneOptions(room.scene_archetype)"
        :value="room.scene_archetype"
        @confirm="setField('scene_archetype', $event)"
      />
      <DraftField
        v-else
        :key="`${selection[0]}-scene`"
        label="場景（空白為無）"
        field-key="room-scene_archetype"
        type="nullable"
        :value="room.scene_archetype"
        @confirm="setField('scene_archetype', $event)"
        @drafts="track('room-scene')($event)"
      />
      <p v-if="SCENE_STATUS[room.scene_status]" :class="SCENE_STATUS[room.scene_status].tone" :data-scene-status="room.scene_status">
        {{ SCENE_STATUS[room.scene_status].glyph }} {{ SCENE_STATUS[room.scene_status].text }}
      </p>
      <DraftField
        :key="`${selection[0]}-art`"
        label="美術鍵（空白為無）"
        field-key="room-art_key"
        type="nullable"
        :value="room.art_key"
        @confirm="setField('art_key', $event)"
        @drafts="track('room-art')($event)"
      />
      <h3 class="section-label">服務 · 唯讀</h3>
      <ul v-if="services.length" class="plain" data-service-identity>
        <li v-for="(item, index) in services" :key="index">
          <span class="mono">{{ item.source }}</span>（{{ item.domain }}）<span class="mono relations__source">{{ item.file }}</span>
        </li>
      </ul>
      <p v-else class="inspector__muted" data-service-identity="none">沒有服務紀錄指向此房間（獨立房間不需要服務紀錄）。</p>
      <p class="inspector__note">服務以房間 ID 連結；編輯名稱或描述不會改變 ID，也不會建立新的室內。</p>
      <h3 class="section-label">連接 · 有向</h3>
      <ul class="plain" data-connection-rows>
        <li v-for="row in rows.outgoing" :key="row.ref" data-connection-row="out">
          <button type="button" class="link" :data-select-connection="row.ref" @click="emit('select', row.ref)">{{ row.label }}</button>
          <span v-if="row.oneWay" class="inspector__muted">（單向）</span>
          <span v-if="row.sameLabel" class="warn" data-same-label>▲ 此房間有另一個同名出口</span>
        </li>
        <li v-for="row in rows.incoming" :key="row.ref" class="inspector__muted" data-connection-row="in">
          <button type="button" class="link" :data-select-connection="row.ref" @click="emit('select', row.ref)">{{ row.label }}</button>
          <span v-if="row.oneWay">（單向）</span>
        </li>
        <li v-if="!rows.outgoing.length && !rows.incoming.length" class="inspector__muted">沒有連接（未完成的連通性可以存檔）。</li>
      </ul>
      <div class="inspector__actions">
        <button type="button" class="button" data-action="new-connection" @click="openConnection(room.id)">⟶ 新連接</button>
        <button type="button" class="button" data-action="duplicate-room" @click="openDuplicate">⧉ 複製為新房間</button>
      </div>
    </template>

    <!-- connection -->
    <template v-else-if="connection">
      <DraftField label="起點房間" field-key="connection-source" type="select" :options="roomOptions" :value="connection.source" @confirm="retarget('source', $event)" />
      <DraftField label="終點房間" field-key="connection-destination" type="select" :options="roomOptions" :value="connection.destination" @confirm="retarget('destination', $event)" />
      <DraftField
        :key="`${selection[0]}-label`"
        label="名稱（出口名稱）"
        field-key="connection-label"
        :value="connection.label"
        @confirm="retarget('label', $event)"
        @drafts="track('connection-label')($event)"
      />
      <p v-if="reverse" class="inspector__muted" data-connection-reverse>
        雙向：{{ connection.label }} ⇄ {{ reverse.label }} ·
        <button type="button" class="link" :data-select-connection="connectionRef(interior.id, reverse.source, reverse.destination, reverse.label)" @click="emit('select', connectionRef(interior.id, reverse.source, reverse.destination, reverse.label))">
          回程 {{ roomName(interior, reverse.source) }} → {{ roomName(interior, reverse.destination) }}
        </button>
      </p>
      <p v-else class="inspector__muted" data-connection-reverse="none">單向連接。</p>
      <p class="inspector__note">室內連接沒有距離或路線長度；畫布上的位置只是編輯器版面。</p>
      <div class="inspector__actions">
        <button v-if="!reverse" type="button" class="button" data-action="reverse-connection" @click="openConnection(connection.destination, connection.source)">⟵ 建立反向連接</button>
        <button type="button" class="button" data-action="delete-connection" @click="emit('delete')">✕ 刪除連接</button>
      </div>
    </template>

    <!-- the open interior (or none yet) -->
    <template v-else-if="!selection.length">
      <template v-if="mapInterior">
        <h3 class="section-label">室內 · {{ mapInterior.id }}</h3>
        <p class="inspector__muted">
          {{ mapInterior.rooms.length }} 個房間 · {{ mapInterior.connections.length }} 筆有向連接 ·
          <span class="mono">{{ mapInterior.relative_path }}</span>
        </p>
        <p class="inspector__muted" data-layout-document>
          版面（僅供編輯器）：<span class="mono">{{ mapInterior.layout_relative_path ?? "無版面文件，依清單排列" }}</span>
        </p>
        <div class="inspector__actions">
          <button type="button" class="button" data-action="new-room" @click="openRoom">＋ 新房間</button>
          <button type="button" class="button" data-action="arrange" :disabled="!mapInterior.rooms.length" @click="emit('arrange')">⊞ 自動排列（覆寫版面，可復原）</button>
        </div>
        <p class="inspector__note">自動排列只寫入版面文件，依入口房間與連接分欄；不代表距離或座標。</p>
      </template>
      <div class="inspector__actions">
        <button type="button" class="button" data-action="new-interior" @click="openInterior">＋ 新室內</button>
        <button v-if="mapInterior" type="button" class="button" data-action="delete-interior" @click="emit('delete-interior', mapInterior.id)">✕ 刪除室內文件</button>
      </div>
    </template>
  </div>
</template>
