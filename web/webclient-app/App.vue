<script setup>
// Vue SPA root build stub (A2). The real AppShell lands in B1
// (webclient-vue-02-showcase-core); this stub exists so the offline-load
// gate can prove the bundle, tokens, and self-hosted fonts render from the
// project origin with every non-local request blocked.
</script>

<template>
  <section
    class="elosern-foundation"
    data-testid="elosern-vue-root"
    data-elosern-stage="foundation-stub"
    aria-label="Elosern"
  >
    <h1 class="elosern-foundation__title">霧落</h1>
    <p class="elosern-foundation__note">
      Vue 基礎構架已離線載入 — 設計稿 tokens 與自托管字型就位。
    </p>
  </section>
</template>

<style scoped>
.elosern-foundation {
  box-sizing: border-box;
  display: flex;
  min-height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--sp-3);
  background: var(--ink-950);
  color: var(--paper-100);
  font-family: var(--f-sans);
}

.elosern-foundation__title {
  margin: 0;
  font-family: var(--f-display);
  font-size: 48px;
  letter-spacing: 0.2em;
  color: var(--paper-50);
}

.elosern-foundation__note {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--paper-500);
}
</style>
