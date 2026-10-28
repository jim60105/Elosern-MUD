<script setup>
// The qualified-object selector (frontend design §4.4, §6): search the
// allowed objects by name or ID; every result names its parent map and its
// qualified ID, and equal names are marked, so the choice is never a
// display-name match. The chosen value is always the qualified ID.
// Keyboard: ArrowUp/ArrowDown move, Enter chooses, Escape closes (the page's
// single-key shortcuts never act inside `[data-object-selector]`); the host
// returns focus to the trigger when it closes.
// Authored names render through text interpolation only.
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { endpointChoices } from "../lib/relationships.js";

const props = defineProps({
  catalog: { type: Map, required: true },
  rule: { type: Object, required: true },
  label: { type: String, required: true },
  current: { type: String, default: null },
  selectorKey: { type: String, default: "endpoint" },
});
const emit = defineEmits(["choose", "close"]);

const query = ref("");
const active = ref(0);
const input = ref(null);
const choices = computed(() => endpointChoices(props.catalog, props.rule, query.value));
const listId = computed(() => `object-selector-${props.selectorKey}`);
watch(query, () => (active.value = 0));

onMounted(() => nextTick(() => input.value?.focus()));

function pick(choice) {
  if (choice) emit("choose", choice.ref);
}

function onKey(event) {
  if (event.isComposing) return;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    const count = choices.value.length;
    if (!count) return;
    active.value = (active.value + (event.key === "ArrowDown" ? 1 : count - 1)) % count;
  } else if (event.key === "Enter") {
    event.preventDefault();
    pick(choices.value[active.value]);
  }
}

function onEscape(event) {
  if (event.isComposing) return;
  event.preventDefault();
  event.stopPropagation();
  emit("close");
}
</script>

<template>
  <div class="object-selector" role="group" :aria-label="label" data-object-selector :data-selector="selectorKey" @keydown.escape="onEscape">
    <label class="draft-field">
      <span class="draft-field__label">{{ label }}</span>
      <input
        ref="input"
        v-model="query"
        class="draft-field__input"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded="true"
        :aria-controls="listId"
        :aria-activedescendant="choices.length ? `${listId}-${active}` : null"
        placeholder="名稱、ID 或限定 ID"
        data-selector-query
        @keydown="onKey"
      />
    </label>
    <p v-if="current" class="inspector__muted">目前：<span class="mono">{{ current }}</span></p>
    <ul :id="listId" class="plain object-selector__results" role="listbox" :aria-label="label">
      <li
        v-for="(choice, index) in choices"
        :id="`${listId}-${index}`"
        :key="choice.ref"
        role="option"
        class="object-selector__choice"
        :class="{ 'object-selector__choice--active': index === active }"
        :aria-selected="index === active ? 'true' : 'false'"
        :data-selector-choice="choice.ref"
        @mousedown.prevent
        @click="pick(choice)"
      >
        <span>{{ choice.label }}</span>
        <span v-if="choice.sameLabel > 1" class="warn">（同名 {{ choice.sameLabel }} 個）</span>
        <span class="results__parent">{{ choice.parent }}</span>
        <span class="mono results__path">{{ choice.ref }}</span>
      </li>
    </ul>
    <p v-if="!choices.length" class="inspector__muted">沒有符合的物件。</p>
    <div class="inspector__actions">
      <button type="button" class="button" data-selector-cancel @click="emit('close')">取消 Esc</button>
    </div>
  </div>
</template>
