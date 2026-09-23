// The action-dock surface (H3): the committed `context_actions` frame
// normalization shared by the keyboard router and the visible DockMenu, the
// root/navigation tab entries, the interaction workspace, the detail-pane
// derivation, and the dock's pointer-activation handlers. Extracted verbatim
// from AppClient.vue so the SFC stays a passive renderer.
import { computed } from "vue";
import { classifyPane } from "../components/dock-panes.js";
import { portraitFor } from "../components/party-helpers.js";

export function useDock(store, { panel, shellRef, dispatchIntent, openRestForm }) {
  // Normalize the committed top navigation and action-root entries identically.
  function normalizeRootItems(items) {
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
  }
  const rootItems = computed(() => normalizeRootItems(store.view.rootMenu?.items || []));
  const navigationItems = computed(() => normalizeRootItems(store.view.navigationItems));

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
  const interactionOpen = computed(() =>
    ["exploration.interact", "exploration.target", "exploration.keywords"].includes(store.view.dockSource),
  );
  const interactionTarget = computed(() => interactionOpen.value ? store.view.combatMenu?.target : null);
  const interactionChoices = computed(() => store.explorationInteract.map((target) => ({
    ...target,
    portrait: portraitFor(panel("art"), target.portrait_ref),
  })));

  function onInteractionTarget(identity) {
    if (identity === interactionTarget.value?.identity) return;
    store.tabToRootAndConfirm("interact", "pointer");
    if (store.focusItemByKey(`target-${identity}`)) {
      store.focusConfirm("pointer");
    }
  }

  // H3 (task 4.5): a non-current tab click pops to the root frame, focuses the
  // tab's item, and confirms it ("pointer") — one deliberate activation, no
  // stray `ui_action`. Bounded by `router.depth()`.
  function onTabClick(key) {
    store.tabToRootAndConfirm(key, "pointer");
  }

  function onNavigateHome() {
    if (store.view.hudDrawer) store.closeHudDrawer({ popFrame: true });
    store.resetFramesToRoot();
    shellRef.value?.restoreDockFocus();
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
  // webclient-pointer-activation: a pointer activation on a disabled row SHALL
  // surface that row's explanation in the detail pane. The interaction
  // workspace normally suppresses the generic detail pane (its step prompt
  // owns the pane region), but when the focused row of the workspace's own
  // rendered frame is disabled, the disabled-explanation contract outranks
  // the pane-free layout and the pane stays readable.
  const focusedRowDisabled = computed(() => {
    const menu = store.view.combatMenu;
    const focused = store.view.focus && store.view.focus.key;
    if (!menu || !Array.isArray(menu.items) || !focused) {
      return false;
    }
    const row = menu.items.find((item) => item.key === focused);
    return !!row && row.enabled === false;
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
   // design, and inventory/shop by construction (make-inventory-drawer-frameless
   // removed the 背包 menu, make-shop-drawer-frameless makes the 商店 drawer
   // client-local, so no shop frame is hosted — the exclusion makes the
   // frameless guarantee explicit and fails safe).
   if (!d || d === "skill" || d === "lore" || d === "status" || d === "inventory" || d === "shop") {
      return false;
    }
   return (
     store.view.activeSubDock === "services" &&
     typeof store.currentFrameIsServiceFrame === "function" &&
     store.currentFrameIsServiceFrame()
   );
 });

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
      openRestForm();
      return;
    }
    store.focusConfirm("pointer");
  }

  function onDockFocusChange(key) {
    // Pointer parity with the keyboard router (one tab stop per cell).
    store.focusItemByKey(key);
  }

  return {
    contextActionsPanel,
    dockItems,
    dockPaneKind,
    drawerHostsServiceFrame,
    focusedRowDisabled,
    detailTestId,
    interactionOpen,
    interactionTarget,
    interactionChoices,
    navigationItems,
    onAction,
    onDockActivate,
    onDockBack,
    onDockFocusChange,
    onInteractionTarget,
    onNavigateHome,
    onTabClick,
    rowPrefix,
    rootItems,
    servicesConfirm,
    showDetail,
  };
}
