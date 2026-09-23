// The HUD surface controller group of the composed Elosern store: the active
// sub-dock record, the reference-drawer controller (H4), and the full-screen
// overlay controller (H5).
//
// H4 (webclient-hud-04-reference-drawers, design D3): the reference
// drawer controller. `view.hudDrawer` is the single open-drawer name
// (null | skill | inventory | shop | quest | lore | status); at most one
// drawer is open at a time (structural: a single value). Unknown names
// are rejected, not coerced. The store is the single writer and owns the
// teardown on a mode change, an epoch reset, or a transport loss.
//
// H5 (webclient-hud-05-overlays-and-command-line, design D7/D8): the
// full-screen overlay controller. `view.hudOverlay` is the single
// open-overlay name (null | map | settings | help | lineage); at most one
// overlay is open at a time (structural: a single value). Unknown names are
// rejected, not coerced. Opening an overlay closes any open reference
// drawer (design D8: an overlay and a drawer are never open together,
// so at most one focus-trapped surface exists at any moment), and the
// opener control is captured at open time so the host's focus
// restoration returns to the trigger that opened the most recent overlay.
// The store is the single writer and owns the teardown on a mode change
// into creation, an epoch reset, or a transport loss (same events as
// the drawer teardown in `syncHudDrawer`).

import { ref } from "vue";

export function applyHud(ctx) {
  // The active sub-dock surface (null | "character"): which re-homed
  // sub-dock currently owns the action-dock surface. The
  // suggestions section must never render while one is active (spec
  // webclient-options-surface). Set by the sub-dock panels on mount/unmount.
  // Declared before the initial view so `buildView` can read it.
  const activeSubDock = ref(null);
  ctx.activeSubDock = activeSubDock;
  ctx.setActiveSubDock = function setActiveSubDock(value) {
    activeSubDock.value = value;
    // Publish so `store.view.activeSubDock` (read by the action dock)
    // reflects the change; the view is a rebuilt snapshot, not live-bound.
    ctx.publishView();
  };

  const HUD_DRAWER_NAMES = new Set(["skill", "inventory", "shop", "quest", "lore", "status", "party"]);
  const FRAMELESS_DRAWER_NAMES = new Set(["inventory", "party", "quest", "shop"]);
  const hudDrawer = ref(null);
  ctx.hudDrawer = hudDrawer;

  ctx.openHudDrawer = function openHudDrawer(name) {
    if (!HUD_DRAWER_NAMES.has(name)) {
      console.warn(`openHudDrawer: unknown drawer "${name}" rejected (not coerced)`);
      return false;
    }
    // Mutual exclusion (H5, design D8): opening a drawer closes the open
    // overlay so at most one focus-trapped surface exists.
    ctx.closeOverlay();
    hudDrawer.value = name;
    ctx.publishView();
    return true;
  };

  ctx.closeHudDrawer = function closeHudDrawer() {
    if (hudDrawer.value === null) {
      return false;
    }
    // make-inventory-drawer-frameless + make-shop-drawer-frameless +
    // make-quest-drawer-frameless + webclient-align-05-party-hud: the 背包,
    // 商店, 任務, and 同伴 drawers never host a router frame, so closing them
    // leaves the router alone — no menu level is popped and the action dock
    // frame is current at close time.
    // Every other drawer keeps the teardown below byte-for-byte.
    if (FRAMELESS_DRAWER_NAMES.has(hudDrawer.value)) {
      hudDrawer.value = null;
      ctx.publishView();
      return true;
    }
    // When closing a drawer while an exploration sub-dock (character)
    // owns the action dock, clear the sub-dock and
    // re-home the exploration root frame — the same teardown the router's
    // `escape-root` handler performs. The drawer's own Escape handler now
    if (
      ctx.dockOnExplorationForm(ctx.reducer.getState()) &&
      activeSubDock.value
    ) {
      ctx.setActiveSubDock(null);
      ctx.inStackMutation = true;
      try {
        ctx.router.replaceFrame(ctx.EXPLORATION_ROOT_DESCRIPTOR, { openerKey: null });
      } finally {
        ctx.inStackMutation = false;
      }
    }
    hudDrawer.value = null;
    ctx.publishView();
    return true;
  };

  const HUD_OVERLAY_NAMES = new Set(["map", "settings", "help", "lineage", "codex", "gallery"]);
  const hudOverlay = ref(null);
  const hudOverlayOpener = ref(null);
  ctx.hudOverlay = hudOverlay;
  ctx.hudOverlayOpener = hudOverlayOpener;

  ctx.openOverlay = function openOverlay(name, openerEl = null) {
    if (!HUD_OVERLAY_NAMES.has(name)) {
      console.warn(`openOverlay: unknown overlay "${name}" rejected (not coerced)`);
      return false;
    }
    // Mutual exclusion (design D8): opening the overlay closes the open
    // drawer so exactly one focus-trapped surface exists.
    ctx.closeHudDrawer();
    hudOverlay.value = name;
    // The opener is captured at open time, not in the host's onMounted:
    // an overlay that replaces another must restore focus to its own
    // trigger, never to the trigger of the closed overlay (design D7).
    hudOverlayOpener.value = openerEl;
    ctx.publishView();
    return true;
  };

  ctx.closeOverlay = function closeOverlay() {
    if (hudOverlay.value === null) {
      return false;
    }
    hudOverlay.value = null;
    hudOverlayOpener.value = null;
    ctx.publishView();
    return true;
  };
}
