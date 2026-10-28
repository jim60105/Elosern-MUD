<script setup>
// The read-only world browser: every loaded domain, its source ownership,
// diagnostics and the external-index/partition freshness, over the service's
// complete authoritative snapshot. Editing tools arrive in later slices.
// Authored text is rendered with text interpolation only (never v-html).
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import MapCanvas from "./components/MapCanvas.vue";
import { CONNECTING, createWorkspaceClient } from "./lib/workspace_client.js";
import { sceneFor } from "./lib/map_scene.js";
import { diagnosticCounts, indexChip, partitionChip, priorityBanner, syncChip } from "./lib/status.js";
import { inspect, mapTitle, sourcePathFor, worldTree } from "./lib/world_index.js";

const client = ref({ connection: CONNECTING, workspace: null, error: null });
const domain = ref("continent");
const mapIds = ref({ settlement: null, interior: null });
const selected = ref(null);
const diagnosticsOpen = ref(false);

const workspace = computed(() => client.value.workspace);
const world = computed(() => workspace.value?.world ?? null);

let workspaceClient = null;
onMounted(() => {
  workspaceClient = createWorkspaceClient({
    fetchImpl: (...args) => window.fetch(...args),
    EventSourceImpl: window.EventSource,
    onChange: (next) => {
      client.value = next;
    },
  });
  workspaceClient.start();
});
onBeforeUnmount(() => workspaceClient?.stop());

// Keep the open maps and the selection by stable identity across snapshots.
watch(world, (next) => {
  if (!next) return;
  const settlementIds = next.settlements.map((s) => s.id);
  const interiorIds = next.interiors.map((i) => i.id);
  if (!settlementIds.includes(mapIds.value.settlement)) mapIds.value.settlement = settlementIds[0] ?? null;
  if (!interiorIds.includes(mapIds.value.interior)) mapIds.value.interior = interiorIds[0] ?? null;
  if (selected.value && !inspect(next, selected.value)) selected.value = null;
});

const DOMAINS = [
  { key: "continent", label: "大陸", chip: "1" },
  { key: "settlement", label: "據點", chip: "2" },
  { key: "interior", label: "室內", chip: "3" },
];
const currentMapId = computed(() => (domain.value === "continent" ? null : mapIds.value[domain.value]));
const scene = computed(() => sceneFor(world.value, domain.value, currentMapId.value));
const title = computed(() => mapTitle(world.value, domain.value, currentMapId.value));
const sourcePath = computed(() => sourcePathFor(world.value, domain.value, currentMapId.value));
const tree = computed(() => worldTree(world.value));
const objects = computed(() => scene.value?.marks ?? []);
const record = computed(() => inspect(world.value, selected.value));
const banner = computed(() => priorityBanner(workspace.value, client.value.connection));
const chips = computed(() => [
  { key: "sync", name: "檔案同步", ...syncChip(workspace.value, client.value.connection) },
  { key: "index", name: "索引", ...indexChip(workspace.value) },
  { key: "partition", name: "分區", ...partitionChip(workspace.value) },
]);
const allDiagnostics = computed(() => [
  ...(workspace.value?.candidate_diagnostics ?? []),
  ...(workspace.value?.diagnostics ?? []),
]);
const counts = computed(() => diagnosticCounts(allDiagnostics.value));
const settlementOptions = computed(() => world.value?.settlements.map((s) => s.id) ?? []);
const interiorOptions = computed(() => world.value?.interiors.map((i) => i.id) ?? []);

function openDomain(key, mapId = null) {
  domain.value = key;
  if (mapId) mapIds.value = { ...mapIds.value, [key]: mapId };
  selected.value = null;
}
function openTreeEntry(entry) {
  if (entry.domain === "continent") {
    openDomain("continent");
    if (entry.id.startsWith("location:")) selected.value = entry.id;
  } else {
    openDomain(entry.domain, entry.mapId);
  }
}
function location(item) {
  if (!item.relative_path) return "（工作區）";
  return item.line ? `${item.relative_path}:${item.line}` : item.relative_path;
}
</script>

<template>
  <div class="editor" :data-preview-state="workspace?.preview_state ?? 'loading'" :data-connection="client.connection">
    <header class="editor__header" role="banner">
      <span class="editor__seal" aria-hidden="true">✎</span>
      <h1 class="editor__title">地圖編纂</h1>
      <nav class="editor__tabs" aria-label="領域">
        <button
          v-for="item in DOMAINS"
          :key="item.key"
          type="button"
          class="editor__tab"
          :class="{ 'editor__tab--active': domain === item.key }"
          :aria-pressed="domain === item.key"
          :data-domain-tab="item.key"
          @click="openDomain(item.key)"
        >
          {{ item.label }} <kbd class="editor__key">{{ item.chip }}</kbd>
        </button>
      </nav>
      <span class="editor__crumb">{{ title }}</span>
      <ul class="editor__chips" aria-label="工作區狀態">
        <li v-for="chip in chips" :key="chip.key" class="chip" :class="`chip--${chip.tone}`" :data-chip="chip.key">
          <span aria-hidden="true">{{ chip.glyph }}</span> {{ chip.text }}
        </li>
      </ul>
    </header>

    <div class="editor__banner-slot" aria-live="polite">
      <section v-if="banner" class="banner" :class="`banner--${banner.tone}`" :data-banner="banner.key">
        <strong class="banner__title">{{ banner.title }}</strong>
        <span class="banner__text">{{ banner.text }}</span>
      </section>
    </div>

    <nav class="editor__nav" aria-label="世界導覽">
      <h2 class="section-label">世界</h2>
      <ul class="tree">
        <li v-for="root in tree" :key="root.id">
          <button type="button" class="tree__row" @click="openTreeEntry(root)">{{ root.label }}</button>
          <ul class="tree">
            <li v-for="locationEntry in root.children" :key="locationEntry.id">
              <button type="button" class="tree__row" :data-tree="locationEntry.id" @click="openTreeEntry(locationEntry)">
                {{ locationEntry.label }}
                <span v-if="locationEntry.tag" class="tag">{{ locationEntry.tag }}</span>
              </button>
              <ul v-if="locationEntry.children.length" class="tree">
                <li v-for="map in locationEntry.children" :key="map.id">
                  <button type="button" class="tree__row" :data-tree="map.id" @click="openTreeEntry(map)">
                    <span class="mono">{{ map.label }}</span> <span class="tag">{{ map.tag }}</span>
                  </button>
                  <ul v-if="map.children.length" class="tree">
                    <li v-for="interior in map.children" :key="interior.id">
                      <button type="button" class="tree__row" :data-tree="interior.id" @click="openTreeEntry(interior)">
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
          class="editor__map-select"
          :aria-label="domain === 'settlement' ? '據點地圖' : '室內地圖'"
          :value="currentMapId"
          @change="openDomain(domain, $event.target.value)"
        >
          <option v-for="id in domain === 'settlement' ? settlementOptions : interiorOptions" :key="id" :value="id">{{ id }}</option>
        </select>
      </template>
      <h2 class="section-label">物件 <span class="count">{{ objects.length }}</span></h2>
      <ul class="objects">
        <li v-for="mark in objects" :key="mark.id">
          <button
            type="button"
            class="objects__row"
            :class="{ 'objects__row--selected': mark.id === selected }"
            :data-object="mark.id"
            @click="selected = mark.id"
          >
            {{ mark.label }}
          </button>
        </li>
      </ul>
    </nav>

    <main class="editor__canvas" :aria-label="title || '地圖'">
      <MapCanvas
        v-if="scene"
        :scene="scene"
        :selected="selected"
        :stale="workspace?.preview_state === 'stale'"
        :label="title"
        @select="selected = $event"
      />
      <div v-else-if="workspace && !world" class="no-preview" data-no-preview>
        <p class="no-preview__title">無可用預覽</p>
        <p>工作區目前無法載入；請依下方診斷在外部修正檔案。</p>
      </div>
      <div v-else-if="world" class="no-preview">
        <p>此領域沒有可顯示的地圖。</p>
      </div>
      <p v-if="sourcePath" class="editor__frame-label mono">{{ sourcePath }}</p>
    </main>

    <aside class="editor__inspector" aria-label="檢查器">
      <template v-if="record">
        <h2 class="inspector__title" data-inspector-title>{{ record.title }}</h2>
        <p class="mono inspector__id" data-inspector-ref>{{ record.qualifiedRef }}</p>
        <p class="mono inspector__path" data-inspector-path>{{ record.relativePath }}</p>
        <dl class="inspector__fields">
          <template v-for="(field, index) in record.fields" :key="index">
            <dt>{{ field.label }}</dt>
            <dd :data-field="field.label">{{ field.value }}</dd>
          </template>
        </dl>
      </template>
      <p v-else class="inspector__empty">選取地圖上的物件以檢視其欄位、來源文件與識別碼。</p>
    </aside>

    <section class="editor__diagnostics" aria-label="診斷">
      <button type="button" class="diagnostics__summary" :aria-expanded="diagnosticsOpen" @click="diagnosticsOpen = !diagnosticsOpen">
        <span data-count="errors">✕ {{ counts.errors }}</span>
        <span data-count="warnings">▲ {{ counts.warnings }}</span>
        <span>· {{ chips[1].text }}</span>
        <span>· {{ chips[2].text }}</span>
        <span class="diagnostics__hint">唯讀瀏覽 · 編輯工具尚未提供</span>
      </button>
      <ol v-if="diagnosticsOpen || workspace?.preview_state !== 'current'" class="diagnostics__list">
        <li v-for="(item, index) in allDiagnostics" :key="index" class="diagnostic" :class="`diagnostic--${item.category}`" :data-diagnostic="item.code">
          <span class="mono">{{ location(item) }}</span>
          <span class="mono">{{ item.code }}</span>
          <span>{{ item.message }}</span>
        </li>
      </ol>
    </section>
  </div>
</template>
