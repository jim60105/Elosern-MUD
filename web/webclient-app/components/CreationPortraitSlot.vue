<script setup>
// CreationPortraitSlot (creation-stepped-form; design §7.1, empty state only):
// the persistent portrait column beside the custom steps. It only reads
// props: the host looks up the server's silhouette table for the current sex
// and apparent age and passes the matching canonical descriptor (or null
// when no single entry matches), plus the current name. The silhouette is
// decoration (aria-hidden); the slot has no action and emits nothing.
import { computed } from "vue";
import ArtworkPreview from "./ArtworkPreview.vue";

const props = defineProps({
  // The current (unsent) display name.
  name: { type: String, default: "" },
  // The matching `custom.silhouettes[].artwork` descriptor, or null.
  silhouette: { type: Object, default: null },
});

// ArtworkPreview judges availability against a panel; the overlay mounts the
// custom form only for an available creation panel.
const AVAILABLE_PANEL = Object.freeze({ available: true });

const trimmed = computed(() => (props.name ?? "").trim());
</script>

<template>
  <aside class="creation-portrait" data-testid="creation-portrait-slot" :data-state="silhouette ? 'silhouette' : 'neutral'">
    <div class="creation-portrait__frame" aria-hidden="true">
      <div v-if="silhouette" class="creation-portrait__figure" data-testid="creation-portrait-silhouette">
        <ArtworkPreview :artwork="silhouette" :panel="AVAILABLE_PANEL" />
      </div>
      <span class="creation-portrait__corner creation-portrait__corner--tl"></span>
      <span class="creation-portrait__corner creation-portrait__corner--br"></span>
    </div>
    <p
      class="creation-portrait__name"
      data-testid="creation-portrait-name"
      :data-unnamed="trimmed ? null : 'true'"
    >
      {{ trimmed || "尚未命名" }}
    </p>
  </aside>
</template>

<style scoped src="./creation-portrait-slot.css"></style>
