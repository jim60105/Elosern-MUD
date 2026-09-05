<script setup>
// C3 (webclient-vue-09-wire-transport-mount): the store-bound live renderers
// (design D3: passive, emit only user-intent dispatches). Every surface
// reads the C1 store's committed slices; panels render only when their
// backing OOB read model is present (the truthful-data scope, roadmap §7 —
// no surface is invented for a panel without a backing model).
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useElosernStore } from "./stores/elosern.js";
import LocalMapLogic from "./lib/local_map.js";
import { classifyPane } from "./components/dock-panes.js";
import { formatCopper } from "./components/character-identity.js";
import AppShell from "./components/AppShell.vue";
import ActionDock from "./components/ActionDock.vue";
import ArtPanel from "./components/ArtPanel.vue";
import CreationOverlay from "./components/CreationOverlay.vue";
import DockMenu from "./components/DockMenu.vue";
import ParticipantFrame from "./components/ParticipantFrame.vue";
import SkillDetailPane from "./components/SkillDetailPane.vue";
import FullLogOverlay from "./components/FullLogOverlay.vue";
import CharacterStatusDrawer from "./components/CharacterStatusDrawer.vue";
import HudDrawer from "./components/HudDrawer.vue";
import InventoryPanel from "./components/InventoryPanel.vue";
import LocalMap from "./components/LocalMap.vue";
import LoreDrawer from "./components/LoreDrawer.vue";
import MapOverlay from "./components/MapOverlay.vue";
import QuestBoard from "./components/QuestBoard.vue";
import RestForm from "./components/RestForm.vue";
import SceneBackdrop from "./components/SceneBackdrop.vue";
import SettingsOverlay from "./components/SettingsOverlay.vue";
import ShopPanel from "./components/ShopPanel.vue";
import TitleBallotMenu from "./components/TitleBallotMenu.vue";
import SkillBook from "./components/SkillBook.vue";
import StatusPanel from "./components/StatusPanel.vue";
import OverlayHost from "./components/OverlayHost.vue";
import HelpOverlay from "./components/HelpOverlay.vue";
import LineagePanel from "./components/LineagePanel.vue";
import TitleCodexPanel from "./components/TitleCodexPanel.vue";
import ToastQueue from "./components/ToastQueue.vue";
import PartyStrip from "./components/PartyStrip.vue";
import PartyDrawer from "./components/PartyDrawer.vue";
import { dialogueViewModel, DIALOGUE_TAB_KEY, DIALOGUE_TAB_LABEL } from "./stores/dialogue-view.js";
import ObjectiveTracker from "./components/ObjectiveTracker.vue";

const store = useElosernStore();

// The shell instance handle (H5, design D1/D6): the store-driven freeform
// dialogue entry point (a freeform affordance) requests command-line field
// focus through the exposed AppShell method — the field is permanently
// present, so there is no open/closed state to toggle.
const shellRef = ref(null);
// Test hook (the repository's __-prefixed harness-hook convention): the
// managed-browser pending-scene journey seeds the client-local prior-image
// memory through this handle (SceneBackdrop's exposed setPriorImage).
const sceneBackdropRef = ref(null);
watch(
  () => store.view.drawerRequest,
  (request) => {
    if (request > 0) {
      shellRef.value?.focusCommandField();
    }
  },
);
// A successful dock-borrowed send (freeform dialogue) restores action-dock
// focus (webclient-desktop-shell: the borrowed send returns focus to the
// dock). The field is never closed, so the completion signal is the focus
// return, not a surface close (H5, design D6).
watch(
  () => store.view.drawerCloseRequest,
  (request) => {
    if (request > 0) {
      shellRef.value?.releaseCommandField(true);
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

// The dialogue surface source (webclient-align-08-dialogue-surface): the ONE
// derived view model over the committed `dialogue` panel, shared by the feed
// variant (prop) and derived again per access by the dock's `dialogue.root`
// resolver — the client never keeps a second copy of the picks.
const dialogueVM = computed(() =>
  store.view.mode === "dialogue" ? dialogueViewModel(panel("dialogue")) : null,
);
// Whether the dock presents the dialogue FORM: the root frame resolved as the
// dialogue form (an unavailable panel resolves to the marker instead, which
// keeps the regular chrome shape and the shared degradation row).
const dialogueRootForm = computed(() => !!(store.view.rootMenu && store.view.rootMenu.dialogueForm === true));
// The CURRENT frame resolved as the dialogue form (pane rows source).
const dialogueFramePresented = computed(
  () => !!(store.view.combatMenu && store.view.combatMenu.dialogueForm === true),
);

// Feed-variant activation shares the dock's dispatch contract (the store owns
// the single dispatch entry and the freeform-borrow path).
function onDialoguePick(pick) {
  store.dispatchAction(pick.actionId, pick.payload || {}, pick.commandDisplay || null);
}
function onDialogueFreeform() {
  store.borrowDialogueCommand();
}

// Tab-completion candidates from the committed exploration panel only
// (webclient-align-02-quickbar-shortcuts): exit move-row labels and
// interact-target display names. An unavailable or absent panel contributes
// nothing — the client never reads uncommitted state.
const completionCandidates = computed(() => {
  const p = panelAvailable("exploration") ? panel("exploration") : null;
  if (!p) {
    return [];
  }
  const exits = Array.isArray(p.move) ? p.move.map((row) => row?.label).filter(Boolean) : [];
  const targets = Array.isArray(p.interact)
    ? p.interact.map((row) => row?.display_name).filter(Boolean)
    : [];
  return [...exits, ...targets];
});

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
  // H4 (task 3.4): the open reference drawer registers into the same
  // open-surface set so the stage recession (H1) applies without a second
  // mechanism.
  if (store.view.hudDrawer) {
    surfaces.push(store.view.hudDrawer);
  }
  // H5 (task 5.4): the open full-screen overlay registers into the same
  // open-surface set; the stage's recession mark clears only when no
  // surface remains open.
  if (store.view.hudOverlay) {
    surfaces.push(store.view.hudOverlay);
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
  // The degraded exploration root (webclient-declarative-frame-stack): the
  // root frame itself is unresolvable, so the pane presents the router's
  // single disabled marker-reason row (server-authored reason verbatim,
  // local fallback otherwise); it submits nothing.
  const degraded = store.view.degradedRoot;
  if (degraded) {
    return [
      {
        key: degraded.key || "degraded-root",
        label: degraded.reason || degraded.fallback,
        enabled: false,
        navigation: true,
        surface: "degraded-root",
      },
    ];
  }
  // The dialogue form's pane rows (webclient-align-08-dialogue-surface): the
  // SAME committed rows the router resolved for the dialogue root frame (one
  // derived source shared with the feed). Normalization matches the
  // exploration branch; activation routes through the router's confirm so
  // pointer, Enter, and digit picks dispatch identically.
  if (dialogueFramePresented.value) {
    const items = (store.view.combatMenu && store.view.combatMenu.items) || [];
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
        // The free-dialogue row is local navigation (it borrows the command
        // line through the store; it is never an OOB action).
        normalized.navigation = true;
        normalized.surface = item.key;
      }
      return normalized;
    });
  }
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
        // H3 (task 5.4/5.5): the pane vocabulary fields the dock's outlet /
        // nav variants read directly (the renderer never re-parses the label).
        normalized.direction = item.direction ?? null;
        normalized.destination = item.destination ?? null;
        normalized.kind = item.kind ?? null;
        normalized.openSubmenu = item.openSubmenu ?? null;
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
      // H3 (task 5.1): the pane-kind classifier reads these fields off the
      // normalized items (the scale step is detected by the `choose-scale`
      // action, the AREA targets by `selected` / `toggle-target`).
      normalized.scaleChoice = item.scaleChoice === true;
      normalized.direction = item.direction ?? null;
      normalized.destination = item.destination ?? null;
      normalized.kind = item.kind ?? null;
      return normalized;
    });
  }
    return [];
});

// H3 (task 3.2): the active frame's pane kind, derived from the committed
// `dockItems` (the single navigation state, design D1). Exposed here so the
// dock's tab bar + pane render from one commit; the pane host (DockMenu)
// re-derives the same kind internally for its row variants.
const dockPaneKind = computed(() => classifyPane({ items: dockItems.value }));

// H3 (task 3.2): the root frame's items (the stable hierarchical root or the
// combat root) normalized for the dock's tab bar — the tab bar renders these
// while the pane follows the current frame, both from one commit.
const rootItems = computed(() => {
  const menu = store.view.rootMenu;
  // The dialogue root renders as the draft's SINGLE `對話選項` tab: the root
  // frame's rows belong to the pane, not the tab bar (one tab, one pane —
  // the tab is inert navigation; clicking it focuses no pick).
  if (dialogueRootForm.value) {
    return [
      {
        key: DIALOGUE_TAB_KEY,
        label: DIALOGUE_TAB_LABEL,
        enabled: true,
        navigation: true,
        surface: DIALOGUE_TAB_KEY,
      },
    ];
  }
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
      normalized.navigation = true;
      normalized.surface = item.key;
    }
    if (item.disabledReason) {
      normalized.disabled_reason = {
        code: item.disabledReason.code,
        message: item.disabledReason.message,
      };
    }
    return normalized;
  });
});

// H3 (task 4.5): a non-current tab click pops to the root frame, focuses the
// tab's item, and confirms it ("pointer") — one deliberate activation, no
// stray `ui_action`. Bounded by `router.depth()`.
function onTabClick(key) {
  store.tabToRootAndConfirm(key, "pointer");
}

// H3 (task 4.6): the crumb's back chevron pops exactly one router level —
// matching the keyboard Escape path.
function onDockBack() {
  store.focusEscape();
}

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

  // H4 (R3, webclient-hud-04-reference-drawers): whether the open reference
  // drawer is hosting the keyboard router's current service frame. When true,
  // the drawer body renders that frame's rows through the shared row renderer
  // (DockMenu) beside the surface's own presentation, and the dock suppresses
  // the duplicate copy of those rows.
  const drawerHostsServiceFrame = computed(() => {
    const d = store.view.hudDrawer;
    // The frameless drawers never host a frame: skill / lore / status by
    // design, and inventory by construction (make-inventory-drawer-frameless
    // removed the 背包 menu, so no inventory frame can be current — the
    // exclusion makes the frameless guarantee explicit and fails safe).
    if (!d || d === "skill" || d === "lore" || d === "status" || d === "inventory") {
      return false;
    }
   return (
     store.view.activeSubDock === "services" &&
     typeof store.currentFrameIsServiceFrame === "function" &&
     store.currentFrameIsServiceFrame()
   );
 });


// C4: the rest-duration form opens when the activated dock item is the
// `explore.wait` rest item (the legacy `openRestForm` behavior).
const restFormOpen = ref(false);
const restFormError = ref(null);
// webclient-action-feedback (busy-drop feedback): dispatchAction returns null
// when the single-writer gate refuses the dispatch (an in-flight action, a
// locked mutation phase, or a disconnected session). Surfaces that fire and
// forget would otherwise silently swallow the player's deliberate activation,
// so every ignored-return dispatch routes through this helper, which leaves a
// visible busy toast at the client boundary instead of dropping it silently.
// Return-bearing seams (the concept apply) keep calling the store directly.
function dispatchIntent(actionId, payload, display) {
  if (store.dispatchAction(actionId, payload, display) === null) {
    store.pushToast({ title: "目前無法執行此操作，請稍後再試。", tone: "info" });
  }
}

function onRestFormSubmit(seconds) {
  restFormOpen.value = false;
  restFormError.value = null;
  // One dispatch through the single store entry (the bounded `explore.wait`
  // payload the server validates).
  dispatchIntent("explore.wait", { seconds });
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
  dispatchIntent(intent.action_id, intent.payload);
}

function onShopSell(intent) {
  dispatchIntent(intent.action_id, intent.payload);
}

// Inventory row-action intents (add-inventory-item-actions, task 6.3): both
// the confirmed item use and the direct equipment toggle route through the
// single store dispatch entry — one deliberate activation, one dispatch.
function onInventoryItemAction(intent) {
  dispatchIntent(intent.action_id, intent.payload);
}

// The pending 異名提名 ballot (title-epithet-nomination): the menu's
// accept/decline intents ride the same single dispatch entry as the shop
// and quest surfaces.
function onTitleBallotAction(intent) {
  dispatchIntent(intent.action_id, intent.payload);
}

// The 稱號冊 window (title-codex-removal): equip/remove/ballot intents ride
// the same single dispatch entry; the rules writer re-validates every gate
// at execution, so the window forwards without client-side rules.
function onTitleCodexAction(intent) {
  dispatchIntent(intent.action_id, intent.payload);
}

const titleBallotPanel = computed(() => panel("title_ballot"));
const titleBallotCandidates = computed(() => {
  const p = titleBallotPanel.value;
  return !!p && p.available === true && Array.isArray(p.candidates) ? p.candidates : [];
});

function onMapMove(moveData) {
  // The minimap node action carries `exit_ref` + `destination`; the
  // `explore.move` payload requires exactly `{ exit_ref, current_node }`,
  // where `current_node` is the actor's current node (the committed
  // `local_map.current_node`), not the destination. The echo label is the
  // uniquely matching traversable edge label (else the destination node's
  // committed label; else nothing — never an invented exit, D3).
  const model = store.view.localMapModel ?? null;
  const exitLabel = LocalMapLogic.exitLabelFor(
    model,
    model?.currentNode ?? null,
    moveData.destination ?? null
  );
  dispatchIntent(
    "explore.move",
    {
      exit_ref: moveData.exit_ref,
      current_node: model?.currentNode ?? null,
    },
    exitLabel ? { exitLabel } : null
  );
}

// H5 (webclient-hud-05-overlays-and-command-line, tasks 5.2/6.4): the
// overlay opener is captured at open time (the focused element before the
// overlay renders). Closing the host restores focus to the trigger that
// opened it; when a second overlay replaces the first, the host
// re-initializes its focus trap with the new opener (design D7).
function openOverlayByName(name) {
  const opener = document.activeElement;
  store.openOverlay(name, opener);
}

// The command line's 設定/說明 utility controls (design D10) open the
// settings / help overlays through the same opener-captured path.
function onOpenOverlay(name) {
  openOverlayByName(name);
}

// The minimap island's 展開全地圖 control (task 6.2) opens the map surface.
function onMapExpand() {
  openOverlayByName("map");
}

// The host's close control and Escape both route here (task 5.2): the host
// restores focus to the opener before emitting.
function onOverlayClose() {
  store.closeOverlay();
}

function onCreationAction(intent) {
  dispatchIntent(intent.action_id, intent.payload);
}

// The return-bearing dispatch seam (retool-concept-fill-navigation D1a): the
// concept apply needs the admission result (requestId / null) to gate its
// loading state; every other creation intent keeps the fire-and-forget route.
function onCreationDispatch(intent) {
  return store.dispatchAction(intent.action_id, intent.payload);
}

function onCreationRequestReset() {
  store.requestCreationReset();
}

function onCreationCancelConfirm() {
  store.focusEscape();
}

function onQuestAction(intent) {
  dispatchIntent(intent.action_id, intent.payload);
}

// add-persona-edit-surface: one drawer persona edit submits exactly one
// character.persona.update action with the section's field key and the
// edited text (null clears).
function onPersonaEdit(intent) {
  dispatchIntent("character.persona.update", { field: intent.field, text: intent.text });
}

// H4 (task 7.4): the reference drawer layer. The drawer title/subtitle is
// derived from the single open-drawer name the store publishes.
const DRAWER_TITLES = {
  skill: "技能書",
  inventory: "背包 · 裝備",
  shop: "商店",
  quest: "任務",
  lore: "世界圖鑑",
  status: "角色狀態",
  party: "同伴 · 隊伍",
};
const drawerTitle = computed(() => DRAWER_TITLES[store.view.hudDrawer] || "");

// The skill drawer's head subtitle: the owner's active/passive skill counts,
// counted from the `character` panel exactly the way `SkillBook` counts its
// rows (the counting logic moved up one level so the drawer head is the
// single place the counts render). Empty when the drawer is not the skill
// drawer or the `character` panel is missing/unavailable (degrade without
// inventing data).
function skillCount(rows) {
  let count = 0;
  for (const category of rows ?? []) {
    for (const group of category.groups ?? []) {
      count += (group.skills ?? []).length;
    }
  }
  return count;
}
const skillBookSubtitle = computed(() => {
  if (store.view.hudDrawer !== "skill" || !panelAvailable("character")) {
    return "";
  }
  const character = panel("character");
  return `主動 ${skillCount(character?.actives)} · 被動 ${skillCount(character?.passives)}`;
});

// The inventory drawer's committed wallet figure (relocate-inventory-drawer-
// essentials; realign-inventory-drawer-layout D3): the validated integer
// copper from the `character` panel, null when:
//  - the `services` panel is unavailable or its `inventory` section is
//    absent (when the bag is unavailable or the section is absent the bag
//    states its registry-owned reason / absent message and fabricates no
//    wallet),
//  - the `character` panel is unavailable or carries no valid non-negative
//    integer balance (a missing or unavailable panel yields null — no
//    balance, and never a zero).
// The head subtitle and the bag's `金錢` row are both derived from this one
// figure (`services.inventory.wallet` is never read), so the two renderings
// of the drawer-layer wallet can never disagree.
const inventoryWalletCopper = computed(() => {
  const services = panel("services");
  const servicesAvailable = !!services && services.available !== false;
  const inventorySection = services ? (services.inventory ?? null) : null;
  if (!servicesAvailable || inventorySection === null) {
    return null;
  }
  if (!panelAvailable("character")) {
    return null;
  }
  const character = panel("character");
  const wallet = character?.wallet;
  if (typeof wallet !== "number" || !Number.isInteger(wallet) || wallet < 0) {
    return null;
  }
  return wallet;
});

// The inventory drawer's head subtitle: the committed wallet figure above,
// formatted as thousands-grouped integer copper (the shared
// `character-identity.js` formatter, the same one the character head card
// uses); blank for any other drawer or when the figure is null.
const inventoryWalletSubtitle = computed(() => {
  if (store.view.hudDrawer !== "inventory") {
    return "";
  }
  const wallet = inventoryWalletCopper.value;
  if (wallet === null) {
    return "";
  }
  return `錢袋 ${formatCopper(wallet)} 銅`;
});

const partyReason = computed(() => {
  const p = panel("party");
  return p?.reason?.message || "隊伍資訊目前無法顯示";
});

const showObjectiveTracker = computed(() => {
  return (
    store.objectivesAvailable &&
    store.objectivesRows.length > 0 &&
    store.view.mode !== "creation"
  );
});

// The skill drawer's footer: the client's own `/cast` syntax as static,
// client-local presentation copy (no OOB field carries it).
const SKILL_CAST_HINT = "施放入口：cast <技法>[@威力]=<代號>";

// The drawer chrome's close entry (Escape / close control / scrim): route
// through the store's single close entry, popping exactly one menu level
// when the drawer hosts a service frame (task 4.2).
function onHudDrawerClose() {
  store.closeHudDrawer({ popFrame: true });
}

function onAction(intent) {
  // One dispatch intent per activation; the store is the single writer.
  dispatchIntent(intent.action_id, intent.payload);
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

// MC5 (multichar-05-topbar-switcher-ui): route character switch/create actions
// through the store's single dispatchAction entry point.
function onSwitchCharacter(characterId) {
  store.dispatchAction("account.character.switch", { character_id: characterId });
}

function onCreateCharacter() {
  store.dispatchAction("account.character.create", {});
}

// Register the SceneBackdrop instance (its exposed interface) on the window
// bridge so the managed-browser pending-scene journey can seed the
// client-local prior-image memory (webclient-contextual-hud: a pending scene
// keeps its prior image dimmed and labelled, never presented as current).
onMounted(() => {
  const bridge = window.__elosernBridge;
  if (bridge) {
    bridge.backdrop = sceneBackdropRef.value;
  }
});
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
        :dialogue="dialogueVM"
        :art-panel="panel('art')"
        :connection-status="store.view.connectionStatus"
        :offline="!store.view.connected"
        :uncertain="store.view.dispatch.uncertain"
        :prompt="store.view.prompt"
        :command-history="store.commandHistory"
        :mutations-locked="store.view.mutationsLocked"
        :open-surfaces="openSurfaces"
        :low-hp="store.view.vitals.lowHp"
        :text-to-html="store.view.textToHtml"
        :in-flight="store.view.dispatch.inFlight !== null"
        :completion-candidates="completionCandidates"
        :roster-available="store.rosterAvailable"
        :roster-characters="store.rosterCharacters"
        :roster-can-create="store.rosterCanCreate"
        :roster-switch-locked="store.rosterSwitchLocked"
        :roster-lock-reason="store.rosterLockReason"
        :epoch="store.view.epoch"
        @submit-command="onSubmitCommand"
        @focus-lost="store.clearFreeformTarget()"
        @open-full-log="openFullLog"
        @dialogue-pick="onDialoguePick"
        @dialogue-freeform="onDialogueFreeform"
        @open-overlay="onOpenOverlay"
        @switch-character="onSwitchCharacter"
        @create-character="onCreateCharacter"
      >
        <!-- The scene backdrop is the lowest stage layer (design D3/D8):
             it renders the committed `art` panel's scene truthfully — the
             done image, the dimmed prior image, or the mode gradient with a
             truthful placeholder. -->
        <template #backdrop>
          <SceneBackdrop ref="sceneBackdropRef" :art="panel('art') || {}" :mode="store.view.mode || 'exploration'" />
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
        <PartyStrip
          v-if="store.partyAvailable && store.view.mode !== 'creation'"
          :slots="store.partySlots"
          :combat-participants="store.combatParticipants"
          :art-panel="panel('art')"
          @open-drawer="() => store.openHudDrawer('party')"
        />
        <!-- H3 (task 6.3): the art catalog strip is absent while the
             participant frame is mounted (combat mode); the frame owns the
             catalog there. -->
        <ArtPanel
          v-if="panelAvailable('art') && store.view.mode !== 'combat'"
          :art="panel('art')"
        />
      </template>
      <template #panel-right>
        <!-- The minimap island (H2, design D9): the stage's right anchor,
             beneath H1's top-meta pill. The `@move` wiring and `explore.move`
             submission are untouched. -->
        <LocalMap
          v-if="store.view.localMapModel"
          :local-map="store.view.localMapModel"
          @move="onMapMove"
          @open-map="onMapExpand"
        />
        <!-- H3 (tasks 6.1/6.2/6.3): the combat participant frame renders in
             the stage's right anchor, combat-only. -->
        <ParticipantFrame
          v-if="contextActionsPanel && contextActionsPanel.kind === 'combat' && Array.isArray(contextActionsPanel.participants)"
          :participants="contextActionsPanel.participants"
          :art-panel="panel('art')"
        />
        <!-- The epithet nomination ballot menu (title-epithet-nomination):
             mounted only while the committed `title_ballot` panel carries
             candidates; answering consumes the ballot and the targeted
             panel update unmounts it. -->
        <TitleBallotMenu
          v-if="titleBallotCandidates.length > 0"
          :ballot="titleBallotPanel"
          @accept="onTitleBallotAction"
          @decline="onTitleBallotAction"
        />
        <!-- H4 (task 7.4): the six reference panels moved into the drawer
             layer; the `#panel-right` anchor keeps only the minimap island
             and the combat participant frame. The `hud-right` anchor's
             geometry and the caption's width reservation are untouched
             (task 7.5) — H2 re-tenants that anchor. -->
      </template>
      <template #objectives>
        <ObjectiveTracker
          v-if="showObjectiveTracker"
          :rows="store.objectivesRows"
        />
      </template>
      <template #action-dock>
        <ActionDock
          v-if="rootItems.length > 0 || !!store.view.degradedRoot || !!store.view.suggestions || (store.view.mode === 'creation' && panelAvailable('creation'))"
          :mode="store.view.mode || 'exploration'"
          :root-items="rootItems"
          :focused-key="store.view.focus.key"
          :view="store.view"
          :dialogue-form="dialogueRootForm"
            @action="onAction"
          @tab-click="onTabClick"
          @back="onDockBack"
        >
          <div class="dock-pane-host">
             <DockMenu
               v-if="dockItems.length && !(store.view.dockDepth === 1 && dockPaneKind === 'plain' && !store.view.degradedRoot) && !drawerHostsServiceFrame"
               :items="dockItems"
              :focused-key="store.view.focus.key"
              :id-prefix="rowPrefix"
              :detail-test-id="detailTestId"
              :show-detail="showDetail"
              :detail-message="restFormError"
              :grid-cols="store.view.combatMenu ? store.view.combatMenu.gridCols : null"
              :depth="store.view.dockDepth"
              :view="store.view"
              :target-name="store.view.combatMenu ? store.view.combatMenu.title : null"
              :hide-generic-detail="!!store.view.focusedSkill"
              @focus-change="onDockFocusChange"
              @activate="onDockActivate"
            />
            <SkillDetailPane
              v-if="store.view.focusedSkill"
              :skill="store.view.focusedSkill"
              :selected="store.view.combatSelected"
              :scales="store.view.focusedSkill.freeformScales || []"
              :scale="store.view.focusedSkill.scale || 1"
              @choose-scale="(p) => store.chooseScale(p.scale)"
              @choose-shorthand="(p) => store.chooseShorthand(p.shorthand)"
            />
          </div>
          <RestForm v-if="restFormOpen" @submit="onRestFormSubmit" @close="onRestFormClose" @error="onRestFormError" />
          <div v-if="servicesConfirm" class="services-confirm">
            <div class="services-confirm-title" data-testid="services-confirm-title">
              {{ servicesConfirm.label }}
            </div>
          </div>
        </ActionDock>
      </template>
    </AppShell>

    <!-- H4 (task 7.4): the reference-drawer layer, mounted above the
         stage. A single `HudDrawer` chrome hosts the drawer body for the
         store's single open-drawer name; only the open drawer's surface is
         in the DOM (task 7.7: no reference surface while closed). -->
    <HudDrawer
      v-if="store.view.hudDrawer"
      :open="true"
      :title="drawerTitle"
      :subtitle="store.view.hudDrawer === 'inventory' ? inventoryWalletSubtitle : (store.view.hudDrawer === 'skill' ? skillBookSubtitle : (store.view.hudDrawer === 'party' ? `${(store.partySlots || []).length} / 4` : ''))"
      :icon="store.view.hudDrawer === 'inventory' ? 'inventory' : (store.view.hudDrawer === 'skill' ? 'skills' : (store.view.hudDrawer === 'party' ? 'party' : null))"
      :drawer-key="store.view.hudDrawer"
      :body-class="drawerHostsServiceFrame ? 'hud-drawer__body--dock' : ''"
      @close="onHudDrawerClose"
    >
      <SkillBook v-if="store.view.hudDrawer === 'skill'" :skills="panel('character') || {}" />
      <InventoryPanel
        v-else-if="store.view.hudDrawer === 'inventory'"
        :services="panel('services') || {}"
        :character="panel('character')"
        :wallet="inventoryWalletCopper"
        @use="onInventoryItemAction"
        @toggle-equip="onInventoryItemAction"
      />
      <ShopPanel
        v-else-if="store.view.hudDrawer === 'shop'"
        :services="panel('services') || {}"
        :quantity-form="store.quantityForm"
        @buy="onShopBuy"
        @sell="onShopSell"
      />
      <QuestBoard
        v-else-if="store.view.hudDrawer === 'quest'"
        :services="panel('services') || {}"
        @quest_register="onQuestAction"
        @quest_accept="onQuestAction"
        @quest_abandon="onQuestAction"
        @quest_turnin="onQuestAction"
        @quest_track="onQuestAction"
        @exam_start="onQuestAction"
        @open_lore="() => store.openHudDrawer('lore')"
      />
      <LoreDrawer v-else-if="store.view.hudDrawer === 'lore'" :services="panel('services') || {}" />
      <CharacterStatusDrawer
        v-else-if="store.view.hudDrawer === 'status'"
        :status="panel('status') || {}"
        :character="panel('character') || {}"
        :low-hp="store.view.vitals.lowHp"
        @open-skill="() => store.openHudDrawer('skill')"
        @persona-edit="onPersonaEdit"
      />
      <PartyDrawer
        v-else-if="store.view.hudDrawer === 'party'"
        :slots="store.partySlots"
        :combat-participants="store.combatParticipants"
        :art-panel="panel('art')"
        :interact-targets="store.explorationInteract"
        :mode="store.view.mode || 'exploration'"
        :available="store.partyAvailable"
        :reason="partyReason"
        @action="onAction"
        @close="onHudDrawerClose"
      />
      <!-- H4 (R3): when the drawer hosts the keyboard router's current service
           frame, render that frame's rows through the shared row renderer
           (DockMenu), beside the surface's own presentation; the dock no
           longer renders the duplicate copy of those rows. -->
      <DockMenu
        v-if="drawerHostsServiceFrame"
        :items="dockItems"
        :focused-key="store.view.focus.key"
        :id-prefix="rowPrefix"
        :grid-cols="store.view.combatMenu ? store.view.combatMenu.gridCols : null"
        :show-detail="showDetail"
        :depth="store.view.dockDepth"
        @focus-change="onDockFocusChange"
        @activate="onDockActivate"
      />
      <!-- The cast-syntax footer hint is skill-drawer-only: a conditional
           named slot means the other five drawers provide no `foot` slot, so
           `HudDrawer` renders no footer for them. -->
      <template v-if="store.view.hudDrawer === 'skill'" #foot>
        <p class="hud-drawer__cast-hint" data-testid="skill-book-cast-hint">{{ SKILL_CAST_HINT }}</p>
      </template>
    </HudDrawer>

    <!-- H5 (tasks 5.4/6.4): the single shared full-screen overlay surface.
         The host owns the geometry, the focus trap, the Escape handling and
         the labelled close control; the three stripped overlay bodies mount
         inside its body slot. An open overlay registers into `openSurfaces`
         so the stage recession applies without a second mechanism. The
         creation overlay is mode-driven and stays outside this single-open
         stack (task 5.5). -->
    <OverlayHost
      v-if="store.view.hudOverlay"
      :overlay="store.view.hudOverlay"
      :opener="store.view.hudOverlayOpener"
      :map-model="store.view.localMapModel"
      :location-label="store.view.statusSlice.locationLabel"
      @close="onOverlayClose"
      @move="onMapMove"
    >
      <template #default="{ overlay: openName, mapModel }">
        <MapOverlay
          v-if="openName === 'map'"
          :local-map="mapModel || {}"
          @move="onMapMove"
          @open-map="onMapExpand"
        />
        <SettingsOverlay
          v-else-if="openName === 'settings'"
          :font-scale="store.view.fontScale"
          :text-to-html="store.view.textToHtml"
          :reduced-motion="store.view.reducedMotion"
          :colorblind="store.view.colorblind"
          @scale-change="store.setFontScale"
          @text-html-change="store.setTextToHtml"
          @reduced-motion-change="store.setReducedMotion"
          @colorblind-change="store.setColorblind"
        />
        <!-- skill-lineage-panel (task 2.3): the big-window ledger renders the
             committed `lineage` panel verbatim — expanded chains carry per-node
             meters, collapsed chains their aggregate meter; the client
             computes no growth rules. -->
        <LineagePanel v-else-if="openName === 'lineage'" :lineage="panel('lineage')" />
        <!-- title-codex-removal: the big-window codex renders the committed
             `title_codex` panel verbatim — the server's `can_remove` flag
             alone decides whether a 移除 control exists; the client owns no
             gate rule and no 卸裝 control. -->
        <TitleCodexPanel
          v-else-if="openName === 'codex'"
          :codex="panel('title_codex')"
          @action="onTitleCodexAction"
        />
        <!-- The help surface renders the client-owned control reference and
             the statement of how the game's own `help` output is reached —
             no invented copy. -->
        <HelpOverlay v-else />
      </template>
    </OverlayHost>

    <CreationOverlay
      v-if="panelAvailable('creation')"
      :creation="panel('creation')"
      :result="store.view.lastActionResult"
      :stage="store.view.creationView"
      :dispatch="onCreationDispatch"
      :dispatch-state="store.view.dispatch"
      :push-toast="store.pushToast"
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
      @close="closeFullLog(true)"
    />

    <!-- The action-feedback toast queue (webclient-action-feedback D2): the
         LAST child of the client root so equal-tier surfaces stack above the
         overlays; the component owns its fixed modal-tier z-index. Always
         mounted — it renders nothing while the store's queue is empty. -->
    <ToastQueue :toasts="store.view.toasts" @dismiss="store.dismissToast" />
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

/* H3 (task 6.4): the skill master-detail layout — the skill list and the
   detail pane sit side by side inside the dock pane (the draft's `.skwrap`
   two-column grid, adapted to a flex row that fits the bounded pane). */
.dock-pane-host {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
  align-items: flex-start;
}

/* H4 (remove-redundant-dock-menu-layout): when the drawer body hosts a dock
   service frame, it becomes the host that owns the split, so the row region
   (`.dock-menu`) and its detail pane (`.dock-detail`) render as direct flex
   children side by side — the job the removed `.dock-menu-layout` wrapper used
   to do. The hosted service surface keeps its own full-width row (it wraps to
   the next line rather than being squished beside the rows), preserving the
   pre-change stacked reading. */
.hud-drawer__body--dock {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--sp-3);
}
.hud-drawer__body--dock > :not(.dock-menu):not(.dock-detail) {
  flex: 1 1 100%;
  min-width: 0;
}
</style>
