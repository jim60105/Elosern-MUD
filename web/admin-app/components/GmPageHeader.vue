<script setup>
// The GM page header (gm-portal-s1-foundation): the page title in the
// display face, the operator account verbatim in mono with its permission
// level, and 登出. Logout posts to the project's existing logout view with
// the Django CSRF token — no GM write endpoint. It is a neutral ghost
// action: ending a session changes no game state.
import { ref } from "vue";
import { readCookie } from "../lib/api.js";

defineProps({
  title: { type: String, required: true },
  eyebrow: { type: String, default: "" },
  account: { type: String, default: "" },
  permissionLevel: { type: String, default: "" },
  logoutUrl: { type: String, default: "" },
});

const csrfToken = ref("");

function attachToken() {
  csrfToken.value = readCookie("csrftoken", globalThis.document?.cookie ?? "");
}
</script>

<template>
  <header class="gm-page-header">
    <div class="gm-page-header__titles">
      <p v-if="eyebrow" class="gm-page-header__eyebrow">{{ eyebrow }}</p>
      <h1 class="gm-page-header__title">{{ title }}</h1>
    </div>
    <div v-if="account || logoutUrl" class="gm-page-header__operator">
      <template v-if="account">
        <span class="gm-page-header__account" :title="account">{{ account }}</span>
        <span v-if="permissionLevel" class="gm-page-header__level" :title="`權限等級：${permissionLevel}`">{{ permissionLevel }}</span>
      </template>
      <span v-if="account && logoutUrl" class="gm-page-header__sep" aria-hidden="true">·</span>
      <form v-if="logoutUrl" class="gm-page-header__logout" method="post" :action="logoutUrl" @submit="attachToken">
        <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken">
        <button type="submit" class="ui-btn ui-btn--ghost ui-btn--sm">登出</button>
      </form>
    </div>
  </header>
</template>

<style scoped>
.gm-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  min-height: 72px;
  padding: var(--sp-2) var(--sp-8);
  background: color-mix(in srgb, var(--ink-900) 92%, transparent);
  backdrop-filter: blur(6px);
  border-bottom: var(--line);
}

.gm-page-header__titles {
  min-width: 0;
}

.gm-page-header__eyebrow {
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
  line-height: 1.4;
  color: var(--paper-500);
}

.gm-page-header__title {
  font-family: var(--f-display);
  font-size: var(--text-2xl);
  font-weight: 400;
  line-height: 1.2;
  color: var(--paper-50);
}

.gm-page-header__operator {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-3);
}

.gm-page-header__account {
  max-width: 24ch;
  overflow: hidden;
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  color: var(--paper-200);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-page-header__level {
  padding: 1px var(--sp-2);
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  line-height: 1.5;
  color: var(--gold-400);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
}

.gm-page-header__sep {
  color: var(--paper-700);
}

.gm-page-header__logout {
  margin: 0;
}

@media (max-width: 859px) {
  .gm-page-header {
    flex-wrap: wrap;
    padding: var(--sp-3) var(--sp-4);
  }
}
</style>
