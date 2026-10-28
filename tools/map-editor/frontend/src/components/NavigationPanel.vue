<script setup>
// Navigation column (frontend design §2): continent layers, the world tree,
// search with parent/source disambiguation and the object list, which is the
// keyboard/text alternative to the canvas. Ctrl/⌘ toggles a row into the
// selection and Shift extends it (click or Enter); search results may join a
// selection across maps and documents.
// Authored names render through text interpolation only.
import { CONTINENT_LAYERS } from "../lib/layers.js";

const props = defineProps({
  domain: { type: String, required: true },
  tree: { type: Array, default: () => [] },
  hidden: { type: Array, default: () => [] },
  objects: { type: Array, default: () => [] },
  selection: { type: Array, default: () => [] },
  query: { type: String, default: "" },
  results: { type: Array, default: () => [] },
  mapOptions: { type: Array, default: () => [] },
  currentMapId: { type: String, default: null },
});
const emit = defineEmits(["layer", "tree", "choose", "result", "query", "map"]);

function modifiers(event) {
  return { toggle: Boolean(event.ctrlKey || event.metaKey), range: Boolean(event.shiftKey) };
}

function choose(ref, event) {
  emit("choose", { ref, ...modifiers(event) });
}

function result(ref, event) {
  emit("result", { ref, toggle: Boolean(event.ctrlKey || event.metaKey) });
}
</script>

<template>
  <div class="nav">
    <template v-if="domain === 'continent'">
      <h2 class="section-label">圖層</h2>
      <ul class="plain">
        <li v-for="layer in CONTINENT_LAYERS" :key="layer.key">
          <label class="check">
            <input
              type="checkbox"
              :checked="!hidden.includes(layer.key)"
              :data-layer="layer.key"
              @change="emit('layer', layer.key)"
            />
            {{ layer.label }}
          </label>
        </li>
      </ul>
    </template>

    <h2 class="section-label">世界</h2>
    <ul class="tree" aria-label="世界樹">
      <li v-for="root in tree" :key="root.id">
        <button type="button" class="tree__row" :data-tree="root.id" @click="emit('tree', root)">{{ root.label }}</button>
        <ul class="tree">
          <li v-for="locationEntry in root.children" :key="locationEntry.id">
            <button type="button" class="tree__row" :data-tree="locationEntry.id" @click="emit('tree', locationEntry)">
              <span class="tree__label">{{ locationEntry.label }}</span>
              <span v-if="locationEntry.tag" class="tag">{{ locationEntry.tag }}</span>
            </button>
            <ul v-if="locationEntry.children.length" class="tree">
              <li v-for="map in locationEntry.children" :key="map.id">
                <button type="button" class="tree__row" :data-tree="map.id" @click="emit('tree', map)">
                  <span class="mono">{{ map.label }}</span> <span class="tag">{{ map.tag }}</span>
                </button>
                <ul v-if="map.children.length" class="tree">
                  <li v-for="interior in map.children" :key="interior.id">
                    <button type="button" class="tree__row" :data-tree="interior.id" @click="emit('tree', interior)">
                      <span class="mono">{{ interior.label }}</span> <span class="tag">{{ interior.tag }}</span>
                    </button>
                  </li>
                </ul>
              </li>
            </ul>
          </li>
        </ul>
      </li>
    </ul>

    <template v-if="domain !== 'continent'">
      <h2 class="section-label">地圖</h2>
      <select
        class="nav__map-select"
        :aria-label="domain === 'settlement' ? '據點地圖' : '室內地圖'"
        :value="currentMapId"
        @change="emit('map', $event.target.value)"
      >
        <option v-for="id in mapOptions" :key="id" :value="id">{{ id }}</option>
      </select>
    </template>

    <h2 class="section-label">搜尋</h2>
    <input
      class="nav__search"
      type="search"
      placeholder="搜尋名稱或 ID…"
      aria-label="搜尋名稱或 ID"
      aria-keyshortcuts="/ Control+K"
      data-search
      :value="query"
      @input="emit('query', $event.target.value)"
    />
    <ul v-if="query" class="results" aria-label="搜尋結果">
      <li v-if="!results.length" class="results__empty">沒有符合的物件。</li>
      <li v-for="item in results" :key="item.ref">
        <button
          type="button"
          class="results__row"
          :class="{ 'results__row--selected': selection.includes(item.ref) }"
          :data-search-result="item.ref"
          @click="result(item.ref, $event)"
          @keydown.enter.prevent="result(item.ref, $event)"
        >
          <span class="results__label">{{ item.label }}<span v-if="item.sameLabel > 1" class="tag">同名 {{ item.sameLabel }}</span></span>
          <span class="results__parent">{{ item.parentLabel }}</span>
          <span class="mono results__ref">{{ item.ref }}</span>
          <span class="mono results__path">{{ item.relativePath }}</span>
        </button>
      </li>
    </ul>

    <h2 class="section-label">物件 <span class="count">{{ objects.length }}</span></h2>
    <ul class="objects" aria-label="物件清單">
      <li v-for="mark in objects" :key="mark.id">
        <button
          type="button"
          class="objects__row"
          :class="{ 'objects__row--selected': selection.includes(mark.id) }"
          :aria-pressed="selection.includes(mark.id)"
          :data-object="mark.id"
          @click="choose(mark.id, $event)"
          @keydown.enter.prevent="choose(mark.id, $event)"
        >
          {{ mark.label }}
        </button>
      </li>
    </ul>
  </div>
</template>
