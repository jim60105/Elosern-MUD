<script setup>
// 找不到頁面 (gm-portal-s1-foundation): an unknown client path under /gm/.
// Undelivered sections have no route, so they would land here too — their
// navigation entries are disabled and never link to it.
import { useRoute, useRouter } from "vue-router";
import StatusPage from "./StatusPage.vue";

const route = useRoute();
const router = useRouter();
</script>

<template>
  <StatusPage eyebrow="HTTP 404" title="此路徑沒有對應的頁面" badge-label="無此頁面">
    <p>GM 控制台中沒有這個路徑：</p>
    <p class="gm-requested-path"><code>/gm{{ route.fullPath }}</code></p>
    <template #actions>
      <button type="button" class="ui-btn" @click="router.push({ name: 'overview' })">回到總覽</button>
    </template>
  </StatusPage>
</template>

<style scoped>
.gm-requested-path {
  margin-top: var(--sp-2);
  overflow-wrap: anywhere;
}

.gm-requested-path code {
  font-size: var(--text-sm);
  color: var(--paper-200);
}
</style>
