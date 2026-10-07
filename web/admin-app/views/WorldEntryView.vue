<script setup>
// One authored entry (gm-portal-s4-world-data §4.1): every converted field in
// the shared JSON tree with declared references linked at their exact field
// path, the entries this one references, and its referrers grouped by the
// declaration's inverse name. All three stay rendered side by side so a field
// and its relationships can be cross-checked.
import { computed, inject, reactive, watch } from "vue";
import GmCodeBlock from "../components/GmCodeBlock.vue";
import GmEmpty from "../components/GmEmpty.vue";
import GmError from "../components/GmError.vue";
import GmJsonTree from "../components/GmJsonTree.vue";
import GmPanel from "../components/GmPanel.vue";
import GmProvenanceNote from "../components/GmProvenanceNote.vue";
import GmReferenceList from "../components/GmReferenceList.vue";
import { AUTHORED_GLYPH, WORLD_ROUTE, entryPath, referenceLinks, registryTarget } from "../lib/world.js";

const props = defineProps({
  registry: { type: String, required: true },
  entryKey: { type: String, required: true },
});

const api = inject("gmApi");
const state = reactive({ status: "loading", data: null, error: null });

//: Referrer groups at or under this size start open.
const OPEN_GROUP_LIMIT = 8;

async function load() {
  state.status = "loading";
  try {
    state.data = await api.get(entryPath(props.registry, props.entryKey));
    state.status = "ready";
    state.error = null;
  } catch (error) {
    state.status = "error";
    state.error = error;
  }
}

const meta = computed(() => state.data?.registry ?? null);
const links = computed(() => referenceLinks(state.data?.references ?? []));
const outgoing = computed(() =>
  (state.data?.references ?? []).map((item) => ({
    registry: item.registry,
    registryLabel: item.registry_label,
    key: item.key,
    label: item.label,
    fieldPath: item.field_path,
    missing: !item.exists,
  })),
);
const missingCount = computed(() => outgoing.value.filter((item) => item.missing).length);
const groups = computed(() =>
  (state.data?.referrers ?? []).map((group) => ({
    inverse: group.inverse,
    items: group.items.map((item) => ({
      registry: item.registry,
      registryLabel: item.registry_label,
      key: item.key,
      label: item.label,
      fieldPath: item.field_path,
      missing: false,
    })),
  })),
);
const referrerCount = computed(() => groups.value.reduce((sum, group) => sum + group.items.length, 0));

watch(() => [props.registry, props.entryKey], load, { immediate: true });
</script>

<template>
  <div class="gm-world-entry">
    <nav class="gm-crumbs" aria-label="位置">
      <RouterLink :to="{ name: WORLD_ROUTE.home }">世界資料</RouterLink>
      <span aria-hidden="true">／</span>
      <RouterLink :to="registryTarget(registry)">{{ meta?.label ?? registry }}</RouterLink>
      <span aria-hidden="true">／</span>
      <span class="gm-mono" aria-current="page">{{ entryKey }}</span>
    </nav>

    <div v-if="state.status === 'loading'" class="gm-world-entry__loading" aria-busy="true">
      <p class="gm-skeleton" style="width: 40%"></p>
      <p class="gm-skeleton" style="width: 25%"></p>
      <p v-for="n in 4" :key="n" class="gm-skeleton" :style="{ width: `${70 - n * 8}%` }"></p>
    </div>

    <GmError
      v-else-if="state.status === 'error'"
      :title="state.error.code === 'entry_not_found' ? '找不到這個條目' : state.error.code === 'registry_not_found' ? '找不到這個登錄表' : '無法載入條目'"
      :message="state.error.message"
      :code="state.error.code"
    >
      <template #actions>
        <RouterLink v-if="state.error.code === 'entry_not_found'" class="ui-btn ui-btn--sm" :to="registryTarget(registry)">
          回到登錄表清單
        </RouterLink>
        <button v-else type="button" class="ui-btn ui-btn--sm" @click="load">重試</button>
      </template>
    </GmError>

    <template v-else>
      <header class="gm-world-entry__head">
        <p class="gm-world-entry__eyebrow">
          <span aria-hidden="true">{{ AUTHORED_GLYPH }}</span>
          {{ meta.label }} · <span class="gm-mono">{{ meta.name }}</span>
        </p>
        <h2 class="gm-world-entry__key gm-mono">{{ state.data.key }}</h2>
        <p v-if="state.data.label" class="gm-world-entry__label">{{ state.data.label }}</p>
        <p class="gm-world-entry__type">型別 <code class="gm-mono">{{ state.data.type }}</code></p>
      </header>

      <GmProvenanceNote :path="meta.source_path" variant="loaded" />

      <nav class="gm-world-entry__anchors" aria-label="條目區塊">
        <a href="#fields">欄位</a>
        <a href="#references">引用 <span class="gm-chip">{{ outgoing.length }}</span>
          <span v-if="missingCount" class="gm-world-entry__broken">✕ {{ missingCount }}</span>
        </a>
        <a href="#referrers">被引用 <span class="gm-chip">{{ referrerCount }}</span></a>
      </nav>

      <div class="gm-world-entry__grid">
        <div id="fields" class="gm-world-entry__fields">
          <GmPanel title="欄位" description="條目的所有欄位；宣告為引用的欄位以 ◇ 連到目標條目。">
            <template #actions>
              <GmCodeBlock :text="state.data.fields" copy-only copy-label="複製 JSON" />
            </template>
            <GmJsonTree :value="state.data.fields" :links="links" :open-depth="3" />
          </GmPanel>
        </div>

        <div class="gm-world-entry__relations">
          <div id="references">
            <GmPanel title="引用" description="此條目引用的其他條目">
              <GmError
                v-if="missingCount"
                compact
                live="off"
                title="有引用指向不存在的條目"
                :message="`共 ${missingCount} 個引用的目標不在已載入的登錄表中。`"
              />
              <GmReferenceList v-if="outgoing.length" :items="outgoing" mode="outgoing" />
              <GmEmpty v-else title="沒有宣告的引用" message="這個條目沒有任何宣告為引用的欄位值。" />
            </GmPanel>
          </div>

          <div id="referrers">
            <GmPanel title="被引用" description="引用此條目的其他條目，依反向名稱分組">
              <GmEmpty v-if="groups.length === 0" title="沒有其他條目引用此條目" />
              <details
                v-for="group in groups"
                :key="group.inverse"
                class="gm-world-entry__group"
                :open="groups.length === 1 || group.items.length <= OPEN_GROUP_LIMIT"
              >
                <summary class="gm-world-entry__group-summary">
                  <span class="gm-world-entry__chevron" aria-hidden="true">▸</span>
                  <span class="gm-mono">{{ group.inverse }}</span>
                  <span class="gm-chip">{{ group.items.length }}</span>
                </summary>
                <GmReferenceList :items="group.items" mode="incoming" />
              </details>
            </GmPanel>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.gm-world-entry {
  display: grid;
  gap: var(--sp-4);
  min-width: 0;
}

.gm-crumbs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-world-entry__loading {
  display: grid;
  gap: var(--sp-2);
}

.gm-world-entry__head {
  display: grid;
  gap: var(--sp-1);
}

.gm-world-entry__eyebrow {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  font-size: var(--text-xs);
  letter-spacing: 0.1em;
  color: var(--gold-400);
}

.gm-world-entry__key {
  font-size: var(--text-2xl);
  font-weight: 600;
  line-height: 1.2;
  color: var(--paper-50);
  overflow-wrap: anywhere;
}

.gm-world-entry__label {
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  color: var(--paper-300);
}

.gm-world-entry__type {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-world-entry__anchors {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
  padding: var(--sp-1);
  background: color-mix(in srgb, var(--ink-900) 88%, transparent);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius);
  backdrop-filter: blur(6px);
}

.gm-world-entry__anchors a {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-1) var(--sp-3);
  font-size: var(--text-sm);
  color: var(--paper-200);
  text-decoration: none;
  border-radius: var(--radius-sm);
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.gm-world-entry__anchors a:hover {
  color: var(--paper-50);
  background: var(--ink-820);
}

.gm-world-entry__anchors a:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-world-entry__broken {
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--crit);
}

.gm-world-entry__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
  align-items: start;
  gap: var(--sp-5);
}

.gm-world-entry__relations {
  display: grid;
  gap: var(--sp-5);
  min-width: 0;
}

#fields,
#references,
#referrers {
  min-width: 0;
  scroll-margin-top: calc(var(--sp-8) + var(--sp-4));
}

.gm-world-entry__group {
  border-bottom: 1px solid var(--ink-700);
}

.gm-world-entry__group:last-child {
  border-bottom: 0;
}

.gm-world-entry__group-summary {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-2) 0;
  list-style: none;
  cursor: pointer;
  border-radius: var(--radius-sm);
}

.gm-world-entry__group-summary::-webkit-details-marker {
  display: none;
}

.gm-world-entry__group-summary:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-world-entry__chevron {
  display: inline-block;
  color: var(--gold-500);
  transition: transform var(--motion-fast) var(--ease-standard);
}

.gm-world-entry__group[open] .gm-world-entry__chevron {
  transform: rotate(90deg);
}

@media (prefers-reduced-motion: reduce) {
  .gm-world-entry__chevron {
    transition: none;
  }
}

@media (max-width: 1099px) {
  .gm-world-entry__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 859px) {
  .gm-world-entry__anchors {
    position: static;
  }
}
</style>
