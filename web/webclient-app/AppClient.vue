<script setup>
// C3 (webclient-vue-09-wire-transport-mount): the store-bound live renderers
// (design D3: passive, emit only user-intent dispatches). Every surface
// reads the C1 store's committed slices; panels render only when their
// backing OOB read model is present (the truthful-data scope, roadmap §7 —
// no surface is invented for a panel without a backing model).
import { computed, nextTick, ref, watch } from "vue";
import { useElosernStore } from "./stores/elosern.js";
import AppShell from "./components/AppShell.vue";
import ActionDock from "./components/ActionDock.vue";
import ArtPanel from "./components/ArtPanel.vue";
import CharacterPanel from "./components/CharacterPanel.vue";
import CreationOverlay from "./components/CreationOverlay.vue";
import DockMenu from "./components/DockMenu.vue";
import FullLogOverlay from "./components/FullLogOverlay.vue";
import InventoryPanel from "./components/InventoryPanel.vue";
import LocalMap from "./components/LocalMap.vue";
import LoreDrawer from "./components/LoreDrawer.vue";
import QuestBoard from "./components/QuestBoard.vue";
import RestForm from "./components/RestForm.vue";
import SceneBackdrop from "./components/SceneBackdrop.vue";
import ShopPanel from "./components/ShopPanel.vue";
import SkillBook from "./components/SkillBook.vue";
import StatusPanel from "./components/StatusPanel.vue";

const store = useElosernStore();

// The shell instance handle: the store-driven freeform dialogue entry point
// (a freeform affordance) requests the command drawer open + field focus
// through the exposed AppShell method.
const shellRef = ref(null);
watch(
  () => store.view.drawerRequest,
  (request) => {
    if (request > 0) {
      shellRef.value?.openDrawer();
    }
  },
);
// A successful dock-borrowed send (freeform dialogue) closes the drawer and
// restores action-dock focus (webclient-desktop-shell: the borrowed-drawer
// send returns focus to the dock).
watch(
  () => store.view.drawerCloseRequest,
  (request) => {
    if (request > 0) {
      shellRef.value?.closeDrawer(true);
    }
  },
);
// The wait/rest entry point (openRestForm) requests the bounded rest-duration
// form open (the exploration rest form, `exploration-rest-form`).
watch(
  () => store.view.restFormRequest,
  (request) => {
    if (request > 0) {
      restFormOpen.value = true;
      restFormError.value = null;
    }
  },
);

function panel(name) {
  return (store.view.panels && store.view.panels[name]) || null;
}

function panelAvailable(name) {
  const p = panel(name);
  return !!p && p.available !== false;
}

// H1 contextual HUD (design D4/D9): the bounded caption card's `完整日誌`
// control opens the full-log overlay; the overlay presents the complete
// retained narrative through the same markup renderer (one markup path).
const fullLogOpen = ref(false);
const fullLogRef = ref(null);

function openFullLog() {
  fullLogOpen.value = true;
  void nextTick().then(() => fullLogRef.value?.focusSelf());
}

function closeFullLog(restoreFocus) {
  fullLogOpen.value = false;
  if (restoreFocus) {
    // Focus is restored to the caption card's control (the opener) by the
    // overlay itself (it remembers the opener element internally); the
    // shell's mode watcher routes focus to the dock when a mode change hides
    // a focused surface.
  }
}

// The open-surface registry (design D9): a single reactive set of open
// surfaces drives the stage recession; the mark clears only when no
// surface remains open. The registry carries the full-log overlay and the
// mounted creation overlay; H4's drawers will register into the same set.
const openSurfaces = computed(() => {
  const surfaces = [];
  if (fullLogOpen.value) {
    surfaces.push("full-log");
  }
  if (panelAvailable("creation")) {
    surfaces.push("creation");
  }
  return surfaces;
});

// A mode transition into creation closes the full-log overlay (a
// non-creation surface must not persist into creation) — task 5.8. The
// shell's mode watcher handles the focus rescue to the dock.
watch(
  () => store.view.mode,
  (mode) => {
    if (mode === "creation" && fullLogOpen.value) {
      fullLogOpen.value = false;
    }
  },
);

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
    // G2: the exploration dock renders the keyboard router's current frame —
    // the stable hierarchical root (Move/Look/Interact/Character/Quests/
    // Inventory/Wait) or an active submenu (move exits / look targets /
    // interact targets / wait dayparts). It is never a flat affordance list,
    // so pointer and keyboard users navigate the identical router path.
    const menu = store.view.combatMenu;
    const items = (menu && menu.items) || [];
    return items.map((item) => {
      const normalized = {
        key: item.key,
        label: item.label,
        enabled: item.enabled !== false,
      };
      if (item.actionId) {
        normalized.action_id = item.actionId;
        normalized.params = item.payload || {};
      } else {
        // A local cell (submenu opener, target/keyword opener, freeform row,
        // confirmation cancel, or a disabled placeholder such as
        // `interact-empty` / `target-empty`) is never an OOB action — classify
        // it as a navigation cell so `classify` never throws.
        normalized.navigation = true;
        normalized.surface = item.key;
      }
      if (item.disabledReason) {
        normalized.disabled_reason = {
          code: item.disabledReason.code,
          message: item.disabledReason.message,
        };
      }
      if (item.description) {
        normalized.description = item.description;
      }
      return normalized;
    });
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
// The detail pane renders only in combat mode or while a submenu frame is
// active (router depth 2+); the exploration root (depth 1) draws no visible
// detail pane (the shell mockup contract).
const showDetail = computed(() => {
  const v = store.view;
  return v.mode === "combat" || v.dockDepth > 1;
});

// The re-homed services confirmation screen (webclient-service-menus: an explicit
// confirm/cancel screen in front of the destructive `guild.quest_abandon`). When
// the keyboard router's current frame is the service confirm menu (item keys
// `confirm-*` / `cancel-*`) and the services sub-dock is active, render the
// `.services-confirm` element. No mutation is dispatched until the player
// confirms.
const servicesConfirm = computed(() => {
  if (store.view.activeSubDock !== "services") {
    return null;
  }
  const menu = store.view.combatMenu;
  if (!menu || !Array.isArray(menu.items) || menu.items.length === 0) {
    return null;
  }
  const isConfirmMenu = menu.items.every(
    (i) => i.key && (i.key.startsWith("confirm-") || i.key.startsWith("cancel-"))
  );
  if (!isConfirmMenu) {
    return null;
  }
  const confirmItem = menu.items.find((i) => i.key && i.key.startsWith("confirm-"));
  return {
    label: confirmItem ? confirmItem.label : "確認",
    actionId: confirmItem ? confirmItem.actionId : null,
    payload: confirmItem ? confirmItem.payload : null,
  };
});


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
  // `explore.move` payload requires exactly `{ exit_ref, current_node }`,
  // where `current_node` is the actor's current node (the committed
  // `local_map.current_node`), not the destination.
  store.dispatchAction("explore.move", {
    exit_ref: moveData.exit_ref,
    current_node: store.view.localMapModel?.currentNode ?? null,
  });
}

function onCreationAction(intent) {
  store.dispatchAction(intent.action_id, intent.payload);
}

function onCreationRequestReset() {
  store.requestCreationReset();
}

function onCreationCancelConfirm() {
  store.focusEscape();
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

function onDrawerClosed() {
  // A cancelled command drawer releases the pending freeform dialogue target
  // so later ordinary commands are never captured as dialogue speech.
  store.clearFreeformTarget();
}

function onChoiceAction(intent) {
  // The narrative stream-end choice-point card/dismiss intents (C4): the
  // same single dispatch entry as the dock (store is the sole writer).
  store.dispatchAction(intent.action_id, intent.payload);
}
</script>

<template>
  <div class="elosern-root" data-testid="elosern-client-root">
      <AppShell
        ref="shellRef"
        :mode="store.view.mode || 'exploration'"
        :connected="store.view.connected"
        :location-label="store.view.statusSlice.locationLabel"
        :time-label="store.view.statusSlice.timeLabel"
        :narrative="store.narrative"
        :connection-status="store.view.connectionStatus"
        :offline="!store.view.connected"
        :uncertain="store.view.dispatch.uncertain"
        :prompt="store.view.prompt"
        :command-history="store.commandHistory"
        :suggestions="store.view.suggestions"
        :mutations-locked="store.view.mutationsLocked"
        :open-surfaces="openSurfaces"
        :low-hp="store.view.vitals.lowHp"
        @submit-command="onSubmitCommand"
        @choice-action="onChoiceAction"
        @drawer-closed="onDrawerClosed"
        @open-full-log="openFullLog"
      >
        <!-- The scene backdrop is the lowest stage layer (design D3/D8):
             it renders the committed `art` panel's scene truthfully — the
             done image, the dimmed prior image, or the mode gradient with a
             truthful placeholder. -->
        <template #backdrop>
          <SceneBackdrop :art="panel('art') || {}" :mode="store.view.mode || 'exploration'" />
        </template>
        <template #panel-left>
        <StatusPanel
          v-if="panelAvailable('status') || panelAvailable('character')"
          :status="panel('status') || {}"
          :character="panel('character') || {}"
          :low-hp="store.view.vitals.lowHp"
          :revision="store.view.revision"
          :epoch="store.view.epoch"
        />
        <ArtPanel v-if="panelAvailable('art')" :art="panel('art')" />
      </template>
      <template #panel-right>
        <!-- The minimap island (H2, design D9): the stage's right anchor,
             beneath H1's top-meta pill. The `@move` wiring and `explore.move`
             submission are untouched. -->
        <LocalMap
          v-if="store.view.localMapModel"
          :local-map="store.view.localMapModel"
          @move="onMapMove"
        />
        <CharacterPanel v-if="panelAvailable('character')" :character="panel('character')" />
        <SkillBook v-if="skillRowsAvailable()" :skills="panel('character')" />
        <ShopPanel
          v-if="panelAvailable('services')"
          :services="panel('services')"
          :quantity-form="store.quantityForm"
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
          v-if="dockItems.length > 0 || !!store.view.suggestions || (store.view.mode === 'creation' && panelAvailable('creation'))"
          :mode="store.view.mode || 'exploration'"
          :suggestions="store.view.suggestions"
          :active-sub-dock="store.view.activeSubDock"
          @action="onAction"
        >
          <DockMenu
            v-if="dockItems.length"
            :items="dockItems"
            :focused-key="store.view.focus.key"
            :id-prefix="rowPrefix"
             :detail-test-id="detailTestId"
             :show-detail="showDetail"
             :detail-message="restFormError"
            :grid-cols="store.view.combatMenu ? store.view.combatMenu.gridCols : null"
            @focus-change="onDockFocusChange"
            @activate="onDockActivate"
          />
          <RestForm v-if="restFormOpen" @submit="onRestFormSubmit" @close="onRestFormClose" @error="onRestFormError" />
          <div v-if="servicesConfirm" class="services-confirm">
            <div class="services-confirm-title" data-testid="services-confirm-title">
              {{ servicesConfirm.label }}
            </div>
          </div>
        </ActionDock>
      </template>
    </AppShell>

    <CreationOverlay
      v-if="panelAvailable('creation')"
      :creation="panel('creation')"
      :result="store.view.lastActionResult"
      :stage="store.view.creationView"
      @action="onCreationAction"
      @request-reset="onCreationRequestReset"
      @cancel-confirm="onCreationCancelConfirm"
    />

    <!-- The full-log surface (design D4): the complete retained narrative,
         reachable in one action from the caption card's control; focus-
         trapped, Escape-closing, with focus restored to the opener. -->
    <FullLogOverlay
      v-if="fullLogOpen"
      ref="fullLogRef"
      :lines="store.narrative"
      :suggestions="store.view.suggestions"
      @close="closeFullLog(true)"
      @choice-action="onChoiceAction"
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
