<script setup>
// C3 (webclient-vue-09-wire-transport-mount): the store-bound live renderers
// (design D3: passive, emit only user-intent dispatches). Every surface
// reads the C1 store's committed slices; panels render only when their
// backing OOB read model is present (the truthful-data scope, roadmap §7 —
// no surface is invented for a panel without a backing model).
import { computed } from "vue";
import { useElosernStore } from "./stores/elosern.js";
import AppShell from "./components/AppShell.vue";
import ActionDock from "./components/ActionDock.vue";
import ArtPanel from "./components/ArtPanel.vue";
import CharacterPanel from "./components/CharacterPanel.vue";
import CreationOverlay from "./components/CreationOverlay.vue";
import DockMenu from "./components/DockMenu.vue";
import InventoryPanel from "./components/InventoryPanel.vue";
import LocalMap from "./components/LocalMap.vue";
import LoreDrawer from "./components/LoreDrawer.vue";
import QuestBoard from "./components/QuestBoard.vue";
import ShopPanel from "./components/ShopPanel.vue";
import SkillBook from "./components/SkillBook.vue";
import StatusPanel from "./components/StatusPanel.vue";

const store = useElosernStore();

function panel(name) {
  return (store.view.panels && store.view.panels[name]) || null;
}

function panelAvailable(name) {
  const p = panel(name);
  return !!p && p.available !== false;
}

// The committed `context_actions` dock frame: the exploration form's
// affordances (action + navigation entries) or the combat form's participants
// (target entries), normalized the same way the store's focus menu does.
// This is the single source the preserved keyboard router and the visible
// DockMenu both consume, so pointer and keyboard parity is maintained.
const dockItems = computed(() => {
  const p = panel("context_actions");
  if (!p || p.available !== true) {
    return [];
  }
  if (p.kind === "exploration") {
    return Array.isArray(p.affordances) ? p.affordances : [];
  }
  if (p.kind === "combat") {
    const parts = Array.isArray(p.participants) ? p.participants : [];
    return parts.map((participant) => ({
      identity: participant.identity == null ? "" : String(participant.identity),
      label: participant.display_name || participant.label || "",
      enabled: participant.enabled !== false,
    }));
  }
  return [];
});

// The character panel is the OOB read model that carries the skill book
// (``actives`` / ``passives`` category groups); the skill book renders only
// when that payload actually has the skill shape (truthful-data scope).
function skillRowsAvailable() {
  const p = panel("character");
  return !!p && p.available !== false && (
    (Array.isArray(p.actives) && p.actives.length > 0) ||
    (Array.isArray(p.passives) && p.passives.length > 0)
  );
}

function onAction(intent) {
  // One dispatch intent per activation; the store is the single writer.
  store.dispatchAction(intent.action_id, intent.payload);
}

// DockMenu (B2 dock family) pointer intents: an action entry carries the
// exact OOB action intent (dispatch through the store), a local
// navigation/target entry (``intent === null``) only updates the store's
// last-surface / last-target state.
function onDockActivate(payload) {
  const intent = payload && payload.intent;
  if (intent) {
    store.dispatchAction(intent.action_id, intent.payload);
  }
}

function onDockFocusChange(key) {
  // Pointer parity with the keyboard router (one tab stop per cell).
  store.focusItemByKey(key);
}

function onSubmitCommand(text) {
  // Ordinary text path: the store sends it through the single transport
  // seam (`sender.sendText` -> `Evennia.msg("text", ...)`).
  return store.sendText(text);
}
</script>

<template>
  <div class="elosern-root" data-testid="elosern-client-root">
    <AppShell
      :mode="store.view.mode || 'exploration'"
      :connected="store.view.connected"
      :location-label="store.view.statusSlice.locationLabel"
      :time-label="store.view.statusSlice.timeLabel"
      :narrative="store.narrative"
      :connection-status="store.view.connectionStatus"
      :offline="!store.view.connected"
      :prompt="store.view.prompt"
      :command-history="store.commandHistory"
      @submit-command="onSubmitCommand"
    >
      <template #panel-left>
        <StatusPanel
          v-if="panelAvailable('status') || panelAvailable('character')"
          :status="panel('status') || {}"
          :character="panel('character') || {}"
        />
        <LocalMap
          v-if="store.view.localMapModel"
          :local-map="store.view.localMapModel"
        />
        <ArtPanel v-if="panelAvailable('art')" :art="panel('art')" />
      </template>
      <template #panel-right>
        <CharacterPanel v-if="panelAvailable('character')" :character="panel('character')" />
        <SkillBook v-if="skillRowsAvailable()" :skills="panel('character')" />
        <ShopPanel v-if="panelAvailable('services')" :services="panel('services')" />
        <QuestBoard v-if="panelAvailable('services')" :services="panel('services')" />
        <LoreDrawer v-if="panelAvailable('services')" :services="panel('services')" />
        <InventoryPanel v-if="panelAvailable('services')" :services="panel('services')" />
      </template>
      <template #action-dock>
        <ActionDock
          :mode="store.view.mode || 'exploration'"
          :suggestions="store.view.suggestions"
          @action="onAction"
        >
          <DockMenu
            v-if="dockItems.length"
            :items="dockItems"
            :focused-key="store.view.focus.key"
            @focus-change="onDockFocusChange"
            @activate="onDockActivate"
          />
        </ActionDock>
      </template>
    </AppShell>

    <CreationOverlay
      v-if="panelAvailable('creation')"
      :creation="panel('creation')"
    />
  </div>
</template>
