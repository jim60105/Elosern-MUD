<script setup>
// ArtworkAlpha — the shared alpha-mask fill primitive (change
// unified-image-loading-core).
//
// It consumes an already observed resource result and paints that resource's
// own alpha channel as a dark fill. It has no selector and no policy: it never
// chooses a demographic/source and never infers one. The fill paints only
// after the caller observed a *successful* load of the same URL, so an absent
// or failed resource can never stand in as an opaque rectangle.
import { computed } from "vue";

const props = defineProps({
  // The observed load result: { url, phase, dimensions? } or null.
  result: { type: Object, default: null },
});

const fill = computed(() => {
  const url = props.result?.url;
  const success = props.result?.phase === "success";
  return success && typeof url === "string" && url.length > 0
    ? { "--artwork-alpha-mask": `url('${url}')` }
    : null;
});
</script>

<template>
  <div class="artwork-alpha" data-testid="artwork-alpha">
    <span v-if="fill" class="artwork-alpha__fill" :style="fill" data-testid="artwork-alpha-fill"></span>
  </div>
</template>

<style scoped>
.artwork-alpha {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
}
/* The default is a fully transparent 1×1 mask, so the element paints nothing
   unless the caller supplied an observed same-URL success; coverage comes from
   the image's alpha channel only (mask-mode: alpha), never its RGB. */
.artwork-alpha__fill {
  --artwork-alpha-mask: url("data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7");
  position: absolute;
  inset: 0;
  background: #17191f;
  mask: var(--artwork-alpha-mask) bottom center / contain no-repeat;
  -webkit-mask: var(--artwork-alpha-mask) bottom center / contain no-repeat;
  mask-mode: alpha;
}
</style>
