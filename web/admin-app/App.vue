<script setup>
// GM root view (gm-portal-s1-foundation): the shell around the routed page.
// The operator identity in the header comes from the shared session state;
// the permission-denied route never loads it (no fetch, no guard loop).
import { computed, inject, nextTick, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import GmShell from "./components/GmShell.vue";
import { GM_SECTIONS } from "./lib/sections.js";

const config = inject("gmConfig");
const session = inject("gmSession");
const route = useRoute();
const router = useRouter();

const title = computed(() => route.meta.title ?? "GM 控制台");
const activeKey = computed(() => route.meta.section ?? "");

watch(
  () => route.name,
  async (name, previous) => {
    if (name && name !== "forbidden" && session.state.status === "idle") session.load();
    document.title = `${title.value}｜Elosern GM 控制台`;
    if (previous) {
      await nextTick();
      document.getElementById("gm-main")?.focus({ preventScroll: true });
    }
  },
  { immediate: true },
);

function navigate(item) {
  if (item.route) router.push({ name: item.route });
}
</script>

<template>
  <GmShell
    :sections="GM_SECTIONS"
    :active-key="activeKey"
    :title="title"
    eyebrow="ELOSERN · 營運者介面"
    :account="session.state.data?.account_name ?? ''"
    :permission-level="session.state.data?.permission_level ?? ''"
    :logout-url="config.logoutUrl"
    :wide="Boolean(route.meta.wide)"
    @navigate="navigate"
  >
    <RouterView />
  </GmShell>
</template>
