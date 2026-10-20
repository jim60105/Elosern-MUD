<script setup>
// WindowFrame (webclient-window-primitives, design §9): the shared window
// chrome the party window and the shop compose, extracted from the quest
// drawer frame. It is a HudDrawer — the seal glyph, the title and the close
// control are the drawer's own DrawerHeader, and the modal focus trap,
// Escape, scrim and slide motion are HudDrawer's contract, unchanged — with
// the quest drawer's head row under it: the first-level IconTabs on the
// header rule and a header-extras slot (purse, quota) at its right end. The
// tab body is one tabpanel and owns no scrolling of its own (ListDetail
// does). The parent mounts the frame only while the window is open, exactly
// as AppClient mounts HudDrawer.
import { computed, ref, useId } from "vue";
import HudDrawer from "./HudDrawer.vue";
import IconTabs from "./IconTabs.vue";

const props = defineProps({
  title: { type: String, required: true },
  // HudDrawer's muted header subtitle (the shop's 營業中 / 已打烊 state).
  subtitle: { type: String, default: "" },
  // The seal: a `dock-icons.js` glyph key drawn in the header medallion.
  seal: { type: String, default: null },
  // IconTabs tabs ([{ key, label, glyph, disabled?, reason?, ... }]).
  tabs: { type: Array, default: () => [] },
  // The selected first-level tab key.
  modelValue: { type: String, default: null },
  tabsLabel: { type: String, default: null },
  drawerKey: { type: String, default: "" },
  closeGuard: { type: Function, default: null },
});

const emit = defineEmits(["update:modelValue", "close"]);

const uid = useId();
const panelId = `window-frame-${uid}-panel`;
// The dialog is named by its header title (HudDrawer's aria-labelledby).
const titleId = `window-frame-${uid}-title`;

// The host's confirmed discard: close past the close guard while still
// restoring focus to the opener (HudDrawer's forceClose).
const drawer = ref(null);
defineExpose({ forceClose: () => drawer.value?.forceClose() });

const frameTabs = computed(() => props.tabs.map((tab) => (tab.controls ? tab : { ...tab, controls: panelId })));
const selectedTab = computed(() => props.tabs.find((tab) => tab.key === props.modelValue) ?? null);
</script>

<template>
  <HudDrawer
    ref="drawer"
    :open="true"
    :title="title"
    :subtitle="subtitle"
    :icon="seal"
    :drawer-key="drawerKey"
    :close-guard="closeGuard"
    :title-id="titleId"
    body-flush
    @close="emit('close')"
  >
    <section class="window-frame" data-testid="window-frame">
      <div class="window-frame__head">
        <IconTabs
          v-if="tabs.length"
          class="window-frame__tabs"
          data-testid="window-frame__tabs"
          orientation="horizontal"
          show-labels
          :aria-label="tabsLabel"
          :tabs="frameTabs"
          :model-value="modelValue"
          @update:model-value="(key) => emit('update:modelValue', key)"
        />
        <div v-if="$slots.extras" class="window-frame__extras" data-testid="window-frame__extras">
          <slot name="extras" />
        </div>
      </div>
      <div
        :id="panelId"
        class="window-frame__body"
        role="tabpanel"
        :aria-label="selectedTab?.label || title"
        data-testid="window-frame__body"
      >
        <slot />
      </div>
    </section>
  </HudDrawer>
</template>

<style scoped>
/* The approved prototype's `.pm` frame and `.pm-head` row
   (docs/design/party-member-management/prototype.css), split as the quest
   drawer splits it: HudDrawer's header carries the seal, title and close;
   this head row carries the tabs and the extras on the header rule. */
.window-frame {
  --window-frame-line: rgba(185, 154, 96, 0.28);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;
  color: var(--paper-200);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  background:
    radial-gradient(120% 80% at 70% 0%, rgba(185, 154, 96, 0.07), transparent 60%),
    linear-gradient(180deg, #16181dfa, #0e1014fa);
}

.window-frame__head {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: flex-end;
  gap: var(--sp-3);
  padding: var(--sp-1) var(--sp-5) 0;
  border-bottom: calc(1px * var(--ui-scale)) solid var(--window-frame-line);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.25), transparent);
}

.window-frame__tabs {
  align-self: flex-end;
}

.window-frame__extras {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-left: auto;
  align-self: center;
  color: var(--gold-400);
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.window-frame__body {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
</style>
