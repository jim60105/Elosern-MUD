// The action-dock surface (H3): the committed `context_actions` frame
// normalization shared by the keyboard router and the visible DockMenu, the
// root/navigation tab entries, the exploration root's live flag, the
// detail-pane derivation, and the dock's pointer-activation handlers. Extracted verbatim
// from AppClient.vue so the SFC stays a passive renderer.
import { computed } from "vue";
import { badgeCount, badgeVisible, classifyPane } from "../components/dock-panes.js";

export function useDock(store, { panel, dispatchIntent }) {
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
  // The committed combat skill-descriptor count (the root's 技能 row).
  const skillsCount = computed(() => badgeCount("skills", store.view));

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
          // H3 (task 5.5): the pane vocabulary fields the dock's nav /
          // affordance variants read directly (the renderer never re-parses
          // the label).
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
        normalized.kind = item.kind ?? null;
        // The vertical command lists (webclient-combat-command-window): the
        // `command` flag selects the list form; the count is the committed
        // descriptor count (the root's 技能 row, a category, a group).
        if (item.command === true) {
          normalized.command = true;
          const count = item.key === "skills" ? skillsCount.value : item.skillCount;
          if (badgeVisible(count)) {
            normalized.count = count;
          }
        }
        if (item.team) {
          normalized.team = item.team;
        }
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

  // The exploration root pane (exploration-room-actions design D2): the
  // exit compass, the shared readout, and the 建議 pill, while the router's
  // current frame is the (empty) exploration root. A degraded root still
  // renders through DockMenu's single marker row.
  const explorationRootShown = computed(
    () => !store.view.degradedRoot && store.view.dockSource === "exploration.root",
  );

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
  const detailTestId = computed(() => (dockKind.value === "combat" ? "combat-detail" : "dock-detail"));
  // The detail pane renders only in combat (and on the combat panel's
  // deeper frames). The exploration screen has no detail pane: its shared
  // readout is where server-authored reasons appear (exploration-room-actions
  // design D6).
  const showDetail = computed(() => store.view.mode === "combat" || dockKind.value === "combat");

  function onAction(intent) {
    // One dispatch intent per activation; the store is the single writer.
    dispatchIntent(intent.action_id, intent.payload);
  }

  // DockMenu pointer activation follows the same router confirmation path as
  // Enter.
  function onDockActivate() {
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
    detailTestId,
    navigationItems,
    onAction,
    onDockActivate,
    onDockBack,
    onDockFocusChange,
    onTabClick,
    explorationRootShown,
    rowPrefix,
    rootItems,
    showDetail,
  };
}
