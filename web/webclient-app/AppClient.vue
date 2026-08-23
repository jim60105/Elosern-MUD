<script setup>
// C3 (webclient-vue-09-wire-transport-mount): the store-bound live renderers
// (design D3: passive, emit only user-intent dispatches). Every surface
// reads the C1 store's committed slices; panels render only when their
// backing OOB read model is present (the truthful-data scope, roadmap §7 —
// no surface is invented for a panel without a backing model).
import { computed, ref, watch } from "vue";
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
import RestForm from "./components/RestForm.vue";
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

// C4: one-sync-per-episode resync (the legacy requestResync contract). The
// real "renderer cannot render" signal is the committed view's `protocolError`
// (set when the server reports a panel/presentation error, e.g.
// `malformed_envelope` / `unsupported_version`). When it transitions
// null -> set while connected, the renderer auto-requests exactly one
// `ui_sync` for the failure episode; the bridge's guard blocks a second
// request in the same transport generation. When the error clears (the
// server re-synced / reconnected), the episode re-arms.
function resyncActions() {
  return (window.Elosern && window.Elosern.actions) || null;
}

// A `ui_protocol_error` is only auto-resynced when it is recoverable: a
// version mismatch (`unsupported_version`) or a reload-required error cannot
// be fixed by a fresh sync, so no request is sent for those (the graphical
// controls stay locked and the text fallback carries the game).
const RESYNCABLE_ERROR_CODES = new Set([
  "malformed_envelope",
  "presentation_unavailable",
  "no_puppet",
  "internal_error",
]);

function isResyncableError(error) {
  return (
    !!error &&
    RESYNCABLE_ERROR_CODES.has(error.code) &&
    error.reloadRequired !== true
  );
}

// The combined "renderer cannot render" failure state: true when EITHER a
// locally-rejected malformed presentation (`lastPanelRejection`) OR a
// recoverable server `ui_protocol_error` is active. A single shared
// one-sync-per-episode guard ("presentation") is re-armed only when BOTH
// signals are cleared, so the guard truly represents one whole-presentation
// failure episode (one sync per episode, no premature re-arm).
const presentationFailure = computed(() => {
  const resyncableError = isResyncableError(store.view.protocolError);
  return !!store.lastPanelRejection || resyncableError;
});

watch(
  presentationFailure,
  (failing, prevFailing) => {
    const actions = resyncActions();
    if (!actions || !store.view.connected) {
      return;
    }
    if (failing && !prevFailing) {
      // A failure signal just became active (a malformed presentation was
      // rejected, or a recoverable protocol error committed): request one
      // ui_sync for this whole-presentation failure episode. The bridge's
      // one-sync-per-episode guard blocks a second request in the same
      // transport generation.
      actions.requestResync("presentation");
    }
    if (!failing && prevFailing) {
      // Both failure signals cleared (a fresh snapshot accepted AND no active
      // recoverable protocol error): re-arm the episode so the next failure
      // can request once more.
      actions.resetResyncEpisode("presentation");
    }
  }
);

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
    // The combat dock follows the preserved keyboard hierarchy (Option B):
    // it renders the keyboard router's current menu frame (root / skills /
    // scale / target), normalized to the DockMenu item contract.
    const menu = store.view.combatMenu;
    const items = (menu && menu.items) || [];
    const selectedIds = store.view.combatSelected || [];
    return items.map((item) => {
      const normalized = {
        key: item.key,
        label: item.label,
        enabled: item.enabled !== false,
      };
      // AREA candidate cells (actionId "toggle-target") show the "✓" marker
      // when their identity is in the client-local selected set.
      if (item.actionId === "toggle-target" && item.payload) {
        normalized.selected = selectedIds.includes(item.payload.identity);
      }
      if (item.disabledReason) {
        normalized.disabled_reason = {
          code: item.disabledReason.code,
          message: item.disabledReason.message,
        };
      }
      if (item.actionId) {
        normalized.action_id = item.actionId;
        normalized.params = item.payload || {};
      } else {
        // Open items (Attack / Skills / Forfeit) drive local submenus, not an
        // OOB action — classify them as local navigation cells.
        normalized.navigation = true;
        normalized.surface = item.key;
      }
      if (item.description) {
        normalized.description = item.description;
      }
      // A skill item's cost text (e.g. "MP 20") — the detail pane names the
      // focused skill's cost.
      if (item.costText) {
        normalized.cost_text = item.costText;
      }
      return normalized;
    });
  }
  return [];
});

// Phase-0 audit §2.3: the preserved `#combat-row-<i>` row frames and the
// REMAP-TO-TESTID detail pane. The row prefix and detail testid are keyed
// off the `context_actions.kind` (not `store.view.mode`), so the pane and
// rows always match the active dock surface.
const contextActionsPanel = computed(() => panel("context_actions"));
const dockKind = computed(() => (contextActionsPanel.value && contextActionsPanel.value.kind) || null);
const rowPrefix = computed(() => (dockKind.value === "combat" ? "combat-row" : "exploration-row"));
const detailTestId = computed(() => (dockKind.value === "combat" ? "combat-detail" : "exploration-detail"));

// C4: the rest-duration form opens when the activated dock item is the
// `explore.wait` rest item (the legacy `openRestForm` behavior).
const restFormOpen = ref(false);
const restFormError = ref(null);

function onRestFormSubmit(seconds) {
  restFormOpen.value = false;
  restFormError.value = null;
  // One dispatch through the single store entry (the bounded `explore.wait`
  // payload the server validates).
  store.dispatchAction("explore.wait", { seconds });
}

function onRestFormClose() {
  restFormOpen.value = false;
}

function onRestFormError(message) {
  restFormError.value = message;
}

// Panel action intents (C4: every surface's emitted intent routes through
// the single store dispatch entry — no component mutates state directly).
function onShopBuy(intent) {
  store.dispatchAction(intent.action_id, intent.payload);
}

function onShopSell(intent) {
  store.dispatchAction(intent.action_id, intent.payload);
}

function onMapMove(moveData) {
  // The minimap node action carries `exit_ref` + `destination`; the
  // `explore.move` payload requires exactly `{ exit_ref, current_node }`.
  store.dispatchAction("explore.move", {
    exit_ref: moveData.exit_ref,
    current_node: moveData.destination,
  });
}

function onCreationAction(intent) {
  store.dispatchAction(intent.action_id, intent.payload);
}

function onQuestAction(intent) {
  store.dispatchAction(intent.action_id, intent.payload);
}

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

// DockMenu pointer activation follows the same router confirmation path as
// Enter. The rest-duration form is the sole local UI exception: confirming
// its action opens the form before any OOB action is dispatched.
function onDockActivate(payload) {
  const intent = payload && payload.intent;
  if (intent && intent.action_id === "explore.wait") {
    restFormOpen.value = true;
    restFormError.value = null;
    return;
  }
  store.focusConfirm("pointer");
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
        :mode="store.view.mode || 'explore'"
      :connected="store.view.connected"
      :location-label="store.view.statusSlice.locationLabel"
      :time-label="store.view.statusSlice.timeLabel"
      :narrative="store.narrative"
      :connection-status="store.view.connectionStatus"
      :offline="!store.view.connected"
      :uncertain="store.view.dispatch.uncertain"
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
          @move="onMapMove"
        />
        <ArtPanel v-if="panelAvailable('art')" :art="panel('art')" />
      </template>
      <template #panel-right>
        <CharacterPanel v-if="panelAvailable('character')" :character="panel('character')" />
        <SkillBook v-if="skillRowsAvailable()" :skills="panel('character')" />
        <ShopPanel
          v-if="panelAvailable('services')"
          :services="panel('services')"
          @buy="onShopBuy"
          @sell="onShopSell"
        />
        <QuestBoard
          v-if="panelAvailable('services')"
          :services="panel('services')"
          @quest_register="onQuestAction"
          @quest_accept="onQuestAction"
          @quest_abandon="onQuestAction"
          @quest_turnin="onQuestAction"
          @exam_start="onQuestAction"
        />
        <LoreDrawer v-if="panelAvailable('services')" :services="panel('services')" />
        <InventoryPanel v-if="panelAvailable('services')" :services="panel('services')" />
      </template>
      <template #action-dock>
        <ActionDock
          v-if="dockItems.length > 0 || !!store.view.suggestions"
          :mode="store.view.mode || 'explore'"
          :suggestions="store.view.suggestions"
          @action="onAction"
        >
          <DockMenu
            v-if="dockItems.length"
            :items="dockItems"
            :focused-key="store.view.focus.key"
            :id-prefix="rowPrefix"
            :detail-test-id="detailTestId"
            :detail-message="restFormError"
            :grid-cols="store.view.combatMenu ? store.view.combatMenu.gridCols : null"
            @focus-change="onDockFocusChange"
            @activate="onDockActivate"
          />
          <RestForm v-if="restFormOpen" @submit="onRestFormSubmit" @close="onRestFormClose" @error="onRestFormError" />
        </ActionDock>
      </template>
    </AppShell>

    <CreationOverlay
      v-if="panelAvailable('creation')"
      :creation="panel('creation')"
      :result="store.view.lastActionResult"
      @action="onCreationAction"
    />
  </div>
</template>

<style>
/* Carry the mount container's viewport height down to the shell so the
   shell grid's 1fr row clamps to the available space (the root div broke
   the 100% height chain, letting the shell grow to its content height). */
.elosern-root {
  height: 100%;
  width: 100%;
}
</style>
