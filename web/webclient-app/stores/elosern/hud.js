// The HUD surface controller group of the composed Elosern store: the active
// sub-dock record, the bounded services quantity form, the reference-drawer
// controller (H4), the full-screen overlay controller (H5), and the
// service-surface bookkeeping (hosted-frame detection + surface maps).
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
import ServiceMenu from "../../lib/service_menu.js";

export function applyHud(ctx) {
  // The active sub-dock surface (null | "character" | "services"): which
  // re-homed sub-dock currently owns the action-dock surface. The
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

  // The bounded services quantity form (webclient-service-menus: buy/sell
  // quantity validation with exact-copper outcomes). A local UI exception: the
  // player focuses a stock/sell row (a bounded trade row carrying a
  // `quantity` {min,max}), opens the form, types a digit quantity, and only
  // a valid quantity dispatches the `shop.buy` / `shop.sell` action. The
  // unsubmitted quantity is discarded on a `services` panel replacement
  // (reconnect), so the form is purely client-local.
  const quantityForm = ref(null);
  ctx.quantityForm = quantityForm;
  ctx.openQuantityForm = function openQuantityForm(item) {
    const qty = item.quantity;
    quantityForm.value = {
      itemKey: item.itemKey,
      actionId: item.actionId,
      // The echo label is captured at open time (the row's server-authored
      // display name) and replayed on the Enter submit
      // (complete-ui-command-echo D3).
      itemLabel: (item.commandDisplay && item.commandDisplay.itemLabel) || null,
      state: ServiceMenu.quantityState(qty.min, qty.max),
      open: true,
    };
    ctx.serviceSurface.value = "shop";
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

  ctx.closeHudDrawer = function closeHudDrawer(options = {}) {
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
    // A drawer hosting a service frame: closing it pops exactly one menu
    // level (the hosted/discard rules live in `settleFrameStack`; a
    // descendant pop keeps the drawer, a hosted-frame pop closes it and
    // discards its local state). A frameless drawer (status / skill / lore)
    // closes without touching the frame stack.
    let poppedHostedFrame = false;
    if (options.popFrame && ctx.currentFrameIsServiceFrame()) {
      poppedHostedFrame = true;
      ctx.inStackMutation = true;
      try {
        ctx.router.popMenu();
      } finally {
        ctx.inStackMutation = false;
      }
      // The hosted-frame teardown the settle would have performed (the
      // pop above is settle-guarded): a quest/shop drawer close discards
      // the surface record and the hosted surface's local state — the
      // quantity form (shop); the quest drawer's selection/confirmation
      // state is component-local and dies on unmount.
      if (hudDrawer.value === "quest" || hudDrawer.value === "shop") {
        ctx.setServiceSurface(null);
        if (hudDrawer.value === "shop") {
          quantityForm.value = null;
        }
        // Same settle-rule mirror as the commit-time path: when the pop
        // left a NON-service frame current, the exploration sub-dock has
        // lost everything it hosts and closes with the drawer (a hosted
        // parent frame still current keeps the sub-dock alive).
        if (
          ctx.dockOnExplorationForm(ctx.reducer.getState()) &&
          activeSubDock.value &&
          !ctx.descriptorIsServiceFrame(ctx.router.currentDescriptor())
        ) {
          ctx.setActiveSubDock(null);
        }
      }
    }
    // When closing a NON-hosted drawer while an exploration sub-dock
    // (character / services) owns the action dock, clear the sub-dock and
    // re-home the exploration root frame — the same teardown the router's
    // `escape-root` handler performs. The drawer's own Escape handler now
    // owns the key (focus is trapped in the drawer), so the router no
    // longer sees the Escape and would not clear the sub-dock. A close
    // that popped a hosted frame does NOT re-home: the popped-to frame
    // (the hosted parent, or the root via the settle cascade) stands.
    if (
      !poppedHostedFrame &&
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
    ctx.closeHudDrawer({});
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

  // The service surface that the current service frame belongs to, recorded
  // at frame-push time (design D2's "record the surface at push time").
  // `null` when no service frame is active. Kept alongside the new
  // descriptor-derived surface so the quantity form's shop assignment and
  // the surface-owning views stay byte-for-byte.
  const serviceSurface = ref(null);
  ctx.serviceSurface = serviceSurface;
  ctx.setServiceSurface = function setServiceSurface(value) {
    serviceSurface.value = value;
  };

  // Declarative hosting (webclient-services-combat-creation-frames): the
  // current frame IS a service frame exactly when its descriptor's source
  // is a hosted services source (anything in the services family except
  // the navigation-only `services.root`). One source of truth — the
  // descriptor — never the menu title.
  const HOSTED_SERVICE_SOURCES = new Set([
    "services.guild",
    "services.board",
    "services.quests",
    "services.quest-detail",
    "services.confirm",
    "services.shop",
    "services.stock",
    "services.sell",
  ]);
  ctx.descriptorIsServiceFrame = function descriptorIsServiceFrame(descriptor) {
    return !!(descriptor && HOSTED_SERVICE_SOURCES.has(descriptor.source));
  };
  // H4 (R3, webclient-hud-04-reference-drawers): whether the keyboard
  // router's current frame is a service frame (guild / shop)
  // so the drawer layer can render that frame's rows through the shared
  // row renderer beside the surface's own presentation.
  ctx.currentFrameIsServiceFrame = function currentFrameIsServiceFrame() {
    return ctx.descriptorIsServiceFrame(ctx.router.currentDescriptor());
  };

  // The service surface -> reference drawer map (design D2): the guild
  // service frames (board / quests / quest-detail / abandon-confirm) present
  // the 任務 drawer and the shop frames (stock / sell) present the 商店
  // drawer. The 背包 drawer is not here: it opens frameless
  // (make-inventory-drawer-frameless) and never hosts a service frame.
  ctx.SERVICE_SURFACE_DRAWERS = {
    guild: "quest",
    shop: "shop",
  };
  // The descriptor -> service-surface map: the guild-family frames carry
  // the quest surface, the shop family the shop surface.
  ctx.SERVICE_SURFACE_FOR_SOURCE = {
    "services.guild": "guild",
    "services.board": "guild",
    "services.quests": "guild",
    "services.quest-detail": "guild",
    "services.confirm": "guild",
    "services.shop": "shop",
    "services.stock": "shop",
    "services.sell": "shop",
  };
}
