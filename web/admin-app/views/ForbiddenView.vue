<script setup>
// 權限不足 (gm-portal-s1-foundation): reached when an API answers 403
// `forbidden`. It never fetches, so it cannot re-trigger the guard; a full
// reload asks the server to re-check access.
import StatusPage from "./StatusPage.vue";

function reload() {
  globalThis.location.assign("/gm/");
}
</script>

<template>
  <StatusPage eyebrow="HTTP 403" title="需要 Developer 權限" badge-status="warn" badge-label="存取受限">
    <p>此帳號目前沒有 <code>Developer</code> 權限，無法使用 GM 控制台。若權限剛調整過，請重新載入後再試。</p>
    <template #actions>
      <button type="button" class="ui-btn" @click="reload">重新載入</button>
      <a class="ui-btn ui-btn--ghost" href="/">返回首頁</a>
    </template>
  </StatusPage>
</template>
