<script setup>
// The GM shell (gm-portal-s1-foundation): desktop-first ledger layout with
// the side navigation on the left, the page header across the top, and the
// panel/table content area. Below 860px the grid collapses to one column and
// the navigation becomes a horizontal strip — usable, not separately designed.
import GmNav from "./GmNav.vue";
import GmPageHeader from "./GmPageHeader.vue";

defineProps({
  sections: { type: Array, required: true },
  activeKey: { type: String, default: "" },
  activeRoute: { type: String, default: "" },
  activeParams: { type: Object, default: () => ({}) },
  title: { type: String, required: true },
  eyebrow: { type: String, default: "" },
  account: { type: String, default: "" },
  permissionLevel: { type: String, default: "" },
  logoutUrl: { type: String, default: "" },
  // Dense data pages (the operations dashboard) may use a wider measure.
  wide: { type: Boolean, default: false },
});

const emit = defineEmits(["navigate"]);
</script>

<template>
  <div class="gm-shell gm-root">
    <a class="gm-shell__skip ui-btn" href="#gm-main">跳至主要內容</a>
    <aside class="gm-shell__aside">
      <GmNav
        :items="sections"
        :active-key="activeKey"
        :active-route="activeRoute"
        :active-params="activeParams"
        @navigate="emit('navigate', $event)"
      />
    </aside>
    <GmPageHeader
      class="gm-shell__header"
      :title="title"
      :eyebrow="eyebrow"
      :account="account"
      :permission-level="permissionLevel"
      :logout-url="logoutUrl"
    />
    <main id="gm-main" class="gm-shell__main" tabindex="-1">
      <div class="gm-shell__content" :class="{ 'gm-shell__content--wide': wide }"><slot /></div>
    </main>
  </div>
</template>

<style scoped>
.gm-shell {
  display: grid;
  grid-template-columns: 272px minmax(0, 1fr);
  grid-template-rows: auto 1fr;
  grid-template-areas:
    "aside header"
    "aside main";
  min-height: 100dvh;
}

.gm-shell__skip {
  position: absolute;
  top: var(--sp-2);
  left: var(--sp-2);
  z-index: 10;
  transform: translateY(-200%);
}

.gm-shell__skip:focus-visible {
  transform: none;
}

.gm-shell__aside {
  grid-area: aside;
  position: sticky;
  top: 0;
  height: 100dvh;
  overflow-y: auto;
  background:
    radial-gradient(120% 36% at 0 0, color-mix(in srgb, var(--gold-500) 7%, transparent), transparent 70%),
    var(--ink-950);
  border-right: var(--line);
}

.gm-shell__header {
  grid-area: header;
  position: sticky;
  top: 0;
  z-index: 1;
}

.gm-shell__main {
  grid-area: main;
  min-width: 0;
  padding: var(--sp-8);
  outline: none;
}

.gm-shell__content {
  max-width: 1200px;
}

.gm-shell__content--wide {
  max-width: 1600px;
}

@media (max-width: 1099px) {
  .gm-shell__main {
    padding: var(--sp-6);
  }
}

@media (max-width: 859px) {
  .gm-shell {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto auto 1fr;
    grid-template-areas:
      "aside"
      "header"
      "main";
  }

  .gm-shell__aside {
    position: static;
    height: auto;
    overflow: visible;
    border-right: 0;
    border-bottom: var(--line);
  }

  .gm-shell__header {
    position: static;
  }

  .gm-shell__main {
    padding: var(--sp-4);
  }
}
</style>
