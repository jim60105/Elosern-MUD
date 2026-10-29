<script setup>
// The offline capture host: the shared map surface at an exact pixel frame,
// with no camera controls, selection, chrome, inspector or status. The entry
// (`src/capture.js`) owns the request, the camera and readiness; this
// component only places the frame and exposes the surface it measured.
import { ref } from "vue";
import MapSurface from "./MapSurface.vue";

const props = defineProps({
  state: { type: Object, required: true },
});

const surface = ref(null);

defineExpose({ surface });
</script>

<template>
  <div
    class="capture"
    :style="{ width: `${state.frame?.width ?? 0}px`, height: `${state.frame?.height ?? 0}px` }"
    data-capture-stage
  >
    <MapSurface ref="surface" :scene="state.scene" :view="state.view" :frame="state.frame" :label="state.label" />
  </div>
</template>
