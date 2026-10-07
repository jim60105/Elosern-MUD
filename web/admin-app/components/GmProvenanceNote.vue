<script setup>
// Where the shown data comes from (gm-portal-s4-world-data §4).
//
// Every world-data page names its repository-relative source path and says how
// a change takes effect: ``loaded`` values are what the server process loaded
// (edit the source, then restart); ``disk`` text is the file as it is on disk,
// not necessarily what is loaded; ``reloadable`` adds the prompt library's one
// exception (it can be reloaded in place). The path links to the source viewer
// when the page can name an allowlisted source file.
import { computed } from "vue";
import GmStatusBadge from "./GmStatusBadge.vue";
import { AUTHORED_GLYPH, PROVENANCE_COPY, sourceTarget } from "../lib/world.js";

const props = defineProps({
  path: { type: String, required: true },
  variant: {
    type: String,
    default: "loaded",
    validator: (value) => ["loaded", "disk", "reloadable"].includes(value),
  },
  // An allowlisted source name (``prompts/art.yaml``) to link the path to.
  sourceName: { type: String, default: "" },
});

const lines = computed(() => {
  if (props.variant === "loaded") return [PROVENANCE_COPY.loaded];
  if (props.variant === "disk") return [PROVENANCE_COPY.disk];
  return [PROVENANCE_COPY.disk.split("。")[0] + "。", PROVENANCE_COPY.reloadable];
});
</script>

<template>
  <aside class="gm-provenance" :class="`gm-provenance--${variant}`" aria-label="資料來源">
    <span class="gm-provenance__glyph" aria-hidden="true">{{ AUTHORED_GLYPH }}</span>
    <div class="gm-provenance__body">
      <p class="gm-provenance__source">
        <span class="gm-provenance__label">{{ variant === "loaded" ? "原始碼" : "磁碟檔案" }}</span>
        <RouterLink
          v-if="sourceName && $router"
          class="gm-provenance__path gm-chip"
          :to="sourceTarget(sourceName)"
          :title="path"
        >{{ path }}</RouterLink>
        <code v-else class="gm-provenance__path gm-chip" :title="path">{{ path }}</code>
        <GmStatusBadge v-if="variant !== 'loaded'" status="warn" label="磁碟內容" />
        <GmStatusBadge v-if="variant === 'reloadable'" status="neutral" label="可重新載入" />
      </p>
      <p v-for="line in lines" :key="line" class="gm-provenance__copy">{{ line }}</p>
    </div>
  </aside>
</template>

<style scoped>
.gm-provenance {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
  min-width: 0;
  padding: var(--sp-2) var(--sp-4) var(--sp-2) var(--sp-3);
  background:
    linear-gradient(90deg, var(--gold-glow), transparent 38%) no-repeat,
    var(--ink-860);
  border-left: 2px solid var(--gold-600);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.gm-provenance--disk,
.gm-provenance--reloadable {
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--warn) 9%, transparent), transparent 38%) no-repeat,
    var(--ink-860);
  border-left-color: var(--warn);
}

.gm-provenance__glyph {
  padding-top: 2px;
  font-size: var(--text-sm);
  color: var(--gold-500);
}

.gm-provenance--disk .gm-provenance__glyph,
.gm-provenance--reloadable .gm-provenance__glyph {
  color: var(--warn);
}

.gm-provenance__body {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.gm-provenance__source {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
}

.gm-provenance__label {
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--paper-500);
}

.gm-provenance__path {
  max-width: min(100%, 48ch);
  color: var(--paper-200);
  text-decoration: none;
}

a.gm-provenance__path:hover {
  color: var(--gold-300);
  border-color: var(--gold-600);
}

a.gm-provenance__path:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-provenance__copy {
  font-size: var(--text-xs);
  line-height: 1.7;
  color: var(--paper-400);
}
</style>
