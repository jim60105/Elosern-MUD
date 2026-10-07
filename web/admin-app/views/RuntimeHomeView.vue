<script setup>
// 執行期狀態 home (gm-portal-s3-runtime-state §6): the navigation tree for the
// runtime section. Every curated kind is one entry; global search is its own
// route so an exact #dbref can never be swallowed by a kind path.
import { RouterLink } from "vue-router";
import { RUNTIME_KINDS, RUNTIME_ROUTE, kindListTarget } from "../lib/runtime.js";
</script>

<template>
  <div class="gm-runtime-home">
    <RouterLink class="gm-runtime-home__search" :to="{ name: RUNTIME_ROUTE.search }">
      <span class="gm-runtime-home__search-glyph" aria-hidden="true">⌕</span>
      <span class="gm-runtime-home__search-label">全域搜尋</span>
      <span class="gm-runtime-home__search-hint">以 #dbref、物件鍵、任務編號或來源識別查找</span>
    </RouterLink>

    <ul class="gm-runtime-home__tree">
      <li v-for="(kind, index) in RUNTIME_KINDS" :key="kind.key">
        <RouterLink class="gm-runtime-home__entry" :to="kindListTarget(kind.key)">
          <span class="gm-runtime-home__ordinal" aria-hidden="true">{{ String(index + 1).padStart(2, "0") }}</span>
          <span class="gm-runtime-home__body">
            <span class="gm-runtime-home__label">{{ kind.label }}</span>
            <span class="gm-runtime-home__blurb">{{ kind.blurb }}</span>
          </span>
          <span class="gm-runtime-home__key gm-mono">{{ kind.key }}</span>
        </RouterLink>
      </li>
    </ul>

    <p class="gm-runtime-home__note">
      執行期頁面僅在手動重新載入時更新，不會自動輪詢；所有檢視都是唯讀，不會建立或修改任何遊戲狀態。
    </p>
  </div>
</template>

<style scoped>
.gm-runtime-home {
  display: grid;
  gap: var(--sp-5);
  min-width: 0;
}

.gm-runtime-home__search {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-3);
  padding: var(--sp-4) var(--sp-5);
  color: var(--paper-100);
  text-decoration: none;
  background:
    linear-gradient(90deg, var(--gold-glow), transparent 60%) no-repeat,
    var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-runtime-home__search:hover {
  border-color: var(--gold-600);
}

.gm-runtime-home__search-glyph {
  font-size: var(--text-lg);
  color: var(--gold-400);
}

.gm-runtime-home__search-label {
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  font-weight: 600;
}

.gm-runtime-home__search-hint {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-runtime-home__tree {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
  gap: var(--sp-3);
  padding: 0;
  list-style: none;
}

.gm-runtime-home__entry {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  height: 100%;
  padding: var(--sp-3) var(--sp-4);
  color: var(--paper-100);
  text-decoration: none;
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}

.gm-runtime-home__entry:hover {
  background: var(--ink-820);
  border-color: var(--gold-600);
}

.gm-runtime-home__entry:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-runtime-home__ordinal {
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--gold-500);
}

.gm-runtime-home__body {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.gm-runtime-home__label {
  font-family: var(--f-serif);
  font-size: var(--text-md);
  font-weight: 600;
}

.gm-runtime-home__blurb {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-runtime-home__key {
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--paper-600, var(--paper-500));
}

.gm-runtime-home__note {
  padding-left: var(--sp-3);
  font-size: var(--text-xs);
  color: var(--paper-500);
  border-left: 2px solid var(--ink-700);
}
</style>
