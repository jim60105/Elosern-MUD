<script setup>
// Every displayed identifier is a link (gm-portal-s3-runtime-state §6).
//
// One renderer for the wire ``{"kind","id","label","owner"}`` link descriptor
// the readers emit: an object/record kind becomes a router link to its entity
// page (or the raw route for an uncurated object), a call identifier becomes a
// button that asks the host page to open the existing S2 drawer, and a media
// identifier becomes a plain external link. An unaddressable link degrades to
// verbatim text — never a fabricated target.
//
// The anchor always carries a real href so modified clicks (new tab) and
// no-router contexts work; a plain left click is handed to the SPA router when
// one is installed.
import { computed, getCurrentInstance } from "vue";
import { linkTarget, targetHref } from "../lib/runtime.js";

const props = defineProps({
  link: { type: Object, default: null },
  label: { type: String, default: "" },
  mono: { type: Boolean, default: true },
  // A short prefix glyph conveying the target class (▸ room, ↩ source …).
  glyph: { type: String, default: "" },
});

const emit = defineEmits(["open-call"]);

const instance = getCurrentInstance();
const router = instance?.appContext?.config?.globalProperties?.$router ?? null;

const target = computed(() => linkTarget(props.link));
const href = computed(() => targetHref(target.value));
const text = computed(() => props.label || props.link?.label || String(props.link?.id ?? "—"));
const isCall = computed(() => Boolean(target.value?.callId));
const isMedia = computed(() => Boolean(target.value?.href));

function follow(event) {
  if (!router || !target.value || event.defaultPrevented) return;
  // Leave modified clicks (new tab/window) to the browser.
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  router.push({ name: target.value.name, params: target.value.params, query: target.value.query });
}
</script>

<template>
  <button
    v-if="isCall"
    type="button"
    class="gm-entity-link gm-entity-link--call"
    :title="`開啟呼叫明細 ${link.id}`"
    @click="emit('open-call', target.callId)"
  >
    <span v-if="glyph" class="gm-entity-link__glyph" aria-hidden="true">{{ glyph }}</span>
    <span :class="{ 'gm-mono': mono }">{{ text }}</span>
  </button>
  <a
    v-else-if="href"
    class="gm-entity-link"
    :href="href"
    :title="String(link.id)"
    :target="isMedia ? '_blank' : null"
    :rel="isMedia ? 'noopener' : null"
    :data-kind="link.kind"
    @click="follow"
  >
    <span v-if="glyph" class="gm-entity-link__glyph" aria-hidden="true">{{ glyph }}</span>
    <span :class="{ 'gm-mono': mono }">{{ text }}</span>
  </a>
  <span v-else class="gm-entity-link gm-entity-link--plain" :title="String(link?.id ?? '')">
    <span v-if="glyph" class="gm-entity-link__glyph" aria-hidden="true">{{ glyph }}</span>
    <span :class="{ 'gm-mono': mono }">{{ text }}</span>
  </span>
</template>

<style scoped>
.gm-entity-link {
  display: inline-flex;
  align-items: baseline;
  gap: var(--sp-1);
  max-width: 100%;
  padding: 0;
  font: inherit;
  color: var(--gold-400);
  text-align: start;
  text-decoration: underline;
  text-decoration-color: color-mix(in srgb, var(--gold-500) 45%, transparent);
  text-underline-offset: 3px;
  background: none;
  border: 0;
  cursor: pointer;
}

.gm-entity-link:hover {
  color: var(--gold-300);
  text-decoration-color: currentColor;
}

.gm-entity-link:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-entity-link > span:last-child {
  min-width: 0;
  overflow-wrap: anywhere;
}

.gm-entity-link__glyph {
  color: var(--paper-500);
  font-family: var(--f-sans);
}

.gm-entity-link--call {
  color: var(--gold-300);
}

.gm-entity-link--plain {
  color: var(--paper-300);
  text-decoration: none;
  cursor: default;
}
</style>
