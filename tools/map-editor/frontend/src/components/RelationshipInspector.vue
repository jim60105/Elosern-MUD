<script setup>
// The entrance relationship inspector (frontend design §4.4): each endpoint
// with its domain, its qualified ID as a link and its directional label;
// 前往另一端 to the far end (the page keeps the return context for
// 「← 返回」/Alt+←); 更換端點… through the qualified-object selector; the
// labels, aliases, direction and (for an interior link) the return label;
// and the explicit removal. Every change is one named command on the owning
// document, sent through `submit`; the service validates it. The heading,
// owner (one record) and direction are the panel's record rows.
// Authored text renders through text interpolation only.
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from "vue";
import DraftField from "./DraftField.vue";
import ObjectSelector from "./ObjectSelector.vue";
import { COMPASS } from "../lib/settlement.js";
import {
  editCommand,
  editableRoles,
  endpointRule,
  otherEnd,
  relationshipView,
  removeWildernessEntry,
} from "../lib/relationships.js";

const props = defineProps({
  world: { type: Object, required: true },
  catalog: { type: Map, required: true },
  selected: { type: String, required: true },
  domain: { type: String, required: true },
  mapId: { type: String, default: null },
  // Queues one command descriptor and resolves with the service's answer.
  submit: { type: Function, required: true },
  // Selects a reference; a plain callback because the answer can arrive
  // after this instance unmounted (an edit can change the reference).
  choose: { type: Function, required: true },
});
const emit = defineEmits(["follow", "delete", "drafts"]);

const counts = reactive({});
const total = computed(() => Object.values(counts).reduce((sum, value) => sum + value, 0));
watch(total, (value) => emit("drafts", value), { immediate: true });
onBeforeUnmount(() => emit("drafts", 0));
const track = (key) => (value) => {
  counts[key] = value;
};

const view = computed(() => relationshipView(props.world, props.selected));
const far = computed(() => otherEnd(view.value, { domain: props.domain, mapId: props.mapId }));
const editable = computed(() => new Set(editableRoles(view.value)));
const ROLE_LABELS = { wilderness: "野外端", start: "起始端", node: "據點端點", room: "室內端點", source: "起點", target: "終點" };
const directionOptions = COMPASS.map((item) => ({ value: item.value, label: `${item.label} · ${item.value}` }));

// `focusRole`: the endpoint whose 更換端點… keeps focus. An edit that changes
// the reference re-keys this inspector, so focus is restored on the new one.
function edit(patch, focusRole = null) {
  const current = view.value;
  if (!current) return;
  const { descriptor, ref: next } = editCommand(current, patch);
  props.submit(descriptor).then((result) => {
    if (!(result?.changed && next && next !== props.selected)) return;
    props.choose(next);
    if (focusRole) nextTick(() => document.querySelector(`[data-change-endpoint="${focusRole}"]`)?.focus());
  });
}

// -- 更換端點… -----------------------------------------------------------------
const selecting = ref(null);
const triggers = ref({});
function openSelector(role) {
  selecting.value = role;
}
function closeSelector() {
  const role = selecting.value;
  selecting.value = null;
  nextTick(() => triggers.value[role]?.focus());
}
function chooseEndpoint(role, value) {
  closeSelector();
  edit({ [role]: value }, role);
}
</script>

<template>
  <div v-if="view" class="relationship" :data-relationship="view.kind">
    <h3 class="section-label">端點</h3>
    <dl class="inspector__fields relationship__ends">
      <template v-for="end in view.endpoints" :key="end.role">
        <dt>{{ ROLE_LABELS[end.role] ?? end.role }}</dt>
        <dd :data-endpoint="end.role">
          <span>{{ end.domainLabel }} · </span>
          <button
            v-if="end.ref && end.present"
            type="button"
            class="link mono"
            :data-follow="end.ref"
            :data-endpoint-follow="end.role"
            @click="emit('follow', end.ref)"
          >{{ end.ref }}</button>
          <span v-else class="mono">{{ end.ref ?? end.name }}</span>
          <span class="relationship__name">（{{ end.name }}）</span>
          <br />
          <span class="relationship__label">{{ end.label }}</span>
          <template v-if="end.position"><br /><span class="inspector__muted">{{ end.position }}</span></template>
          <p v-if="!end.present" class="warn" data-endpoint-missing>▲ 這個端點不在目前的快照中；診斷列出它的來源檔案與欄位。</p>
          <div v-if="editable.has(end.role)" class="inspector__actions">
            <button
              :ref="(element) => (triggers[end.role] = element)"
              type="button"
              class="button"
              :aria-expanded="selecting === end.role"
              :data-change-endpoint="end.role"
              @click="openSelector(end.role)"
            >✎ 更換端點…</button>
          </div>
          <ObjectSelector
            v-if="selecting === end.role"
            :catalog="catalog"
            :rule="endpointRule(view, end.role)"
            :label="`${ROLE_LABELS[end.role] ?? end.role}：選擇物件`"
            :current="end.ref"
            :selector-key="end.role"
            @choose="chooseEndpoint(end.role, $event)"
            @close="closeSelector"
          />
        </dd>
      </template>
    </dl>
    <div class="inspector__actions">
      <button v-if="far" type="button" class="button" data-action="other-end" @click="emit('follow', far.ref)">⇄ 前往另一端</button>
    </div>
    <p v-if="!far" class="inspector__muted" data-other-end="none">這個關係沒有可前往的地圖物件端點。</p>

    <h3 class="section-label">標籤與方向</h3>
    <template v-if="view.kind === 'gate'">
      <DraftField
        label="回程方向（由野外進入據點的方向）"
        field-key="gate-direction"
        type="select"
        :options="directionOptions"
        :value="view.values.direction"
        @confirm="edit({ direction: $event })"
      />
      <p class="inspector__note">野外端的格位由核心依佔地與方向計算，唯讀；佔地在大陸的「佔地」工具中編輯。</p>
    </template>
    <template v-else-if="view.kind === 'city_gate'">
      <DraftField
        :key="`${selected}-exit-key`"
        label="出口名稱"
        field-key="city-gate-exit_key"
        :value="view.values.exit_key"
        @confirm="edit({ exit_key: $event })"
        @drafts="track('exit-key')($event)"
      />
      <DraftField
        :key="`${selected}-exit-aliases`"
        label="別名（一行一個）"
        field-key="city-gate-exit_aliases"
        type="lines"
        :value="view.values.exit_aliases"
        @confirm="edit({ exit_aliases: $event })"
        @drafts="track('exit-aliases')($event)"
      />
      <p class="inspector__note" data-one-way-fixed>起始房間入口固定為單向：沒有回程欄位，也不能改為雙向。</p>
    </template>
    <template v-else-if="view.kind === 'exterior'">
      <DraftField
        :key="`${selected}-doorway`"
        label="入口名稱（由據點進入）"
        field-key="exterior-doorway_key"
        :value="view.values.doorway_key"
        @confirm="edit({ doorway_key: $event })"
        @drafts="track('doorway')($event)"
      />
      <DraftField
        :key="`${selected}-aliases`"
        label="別名（一行一個）"
        field-key="exterior-doorway_aliases"
        type="lines"
        :value="view.values.doorway_aliases"
        @confirm="edit({ doorway_aliases: $event })"
        @drafts="track('aliases')($event)"
      />
      <p class="inspector__note">雙向：離開室內的返回出口由遊戲提供；兩個方向都記錄在這一筆外部入口中。</p>
    </template>
    <template v-else>
      <DraftField
        :key="`${selected}-label`"
        label="去程名稱"
        field-key="link-label"
        :value="view.values.label"
        @confirm="edit({ label: $event })"
        @drafts="track('label')($event)"
      />
      <DraftField
        :key="`${selected}-return`"
        label="回程名稱（空白為單向）"
        field-key="link-return_label"
        type="nullable"
        :value="view.values.return_label"
        @confirm="edit({ return_label: $event })"
        @drafts="track('return')($event)"
      />
      <p class="inspector__note">雙向的意義只記錄在這一筆連結中，不會寫入另一端的文件。</p>
    </template>

    <div class="inspector__actions">
      <button type="button" class="button" data-action="delete-relationship" @click="emit('delete')">✕ 移除這個關係</button>
      <button
        v-if="view.kind === 'gate'"
        type="button"
        class="button"
        data-action="remove-wilderness-entry"
        @click="submit(removeWildernessEntry(view.ownerId)).then((result) => result?.changed && choose(null))"
      >✕ 移除整個野外入口（含佔地遮罩）</button>
    </div>
    <p class="inspector__note">移除關係只寫入 {{ view.ownerPath }}，不會連帶刪除任何端點；之後可另外刪除端點物件。</p>
  </div>
</template>
