// The character-creation dock group of the composed Elosern store (the
// legacy creation_dock.js port): the dock stage state (`creation`), the
// panel-signature rebuild, the confirmation flow, and the router event
// handling, plus the commit-path drawer sync (H4 task 4.3/4.4).

import stableStringify from "../../lib/stable_stringify.js";
import CreationMenu from "../../lib/creation_menu.js";

export function applyCreation(ctx) {
  // The legacy character-creation dock port (the preserved CreationMenu model
  // driving the keyboard router in creation mode, design D4): the current dock
  // stage (root/presets/custom/concept/confirm) and the save awaiting its
  // confirmation. The built menus and the confirm items are NOT stored: every
  // frame content resolves from the committed panel through the resolver
  // registry (webclient-services-combat-creation-frames). Null outside
  // creation mode.
  // ctx.creation holds {view, confirmDescriptor, pendingActivate,
  // pendingActivateKey, pendingSaveRequestId, returnStage, panelSig}.

  // The committed `creation` panel, or null unless the session is in creation
  // mode with an available panel (the legacy `panelAvailable` check).
  function creationPanelOf(rs) {
    const panel = (rs.panels && rs.panels.creation) || null;
    if (!panel || panel.available !== true || rs.mode !== "creation") {
      return null;
    }
    return panel;
  }

  // The legacy `_panelSignature`: the preset keys, the race keys, and the
  // canonical draft. Any change rebuilds the creation menus and resumes the
  // server-persisted stage.
  function creationPanelSignature(panel) {
    const custom = panel.custom || {};
    return stableStringify({
      presets: (panel.presets || []).map((card) => card.key),
      races: (custom.races || []).map((race) => race.key),
      draft: panel.draft || null,
    });
  }

  // Open the confirmation stage for the just-saved draft (preset/custom) or
  // the destructive reset, pushing the confirm items as the single router
  // frame (the legacy `_openPendingConfirm` / `_openResetConfirm`). The stage
  // the player was on is remembered so cancel restores exactly that view.
  function openCreationConfirm(kind, presetKey, returnStage) {
    if (!ctx.creation || ctx.creation.view === "confirm") {
      return;
    }
    ctx.creation.pendingActivate = kind;
    ctx.creation.pendingActivateKey = kind === "preset" ? presetKey || null : null;
    ctx.creation.pendingSaveRequestId = null;
    ctx.creation.returnStage = returnStage || ctx.creation.view || "root";
    ctx.creation.view = "confirm";
    ctx.creation.confirmDescriptor = {
      source: "creation.confirm",
      params: { kind, presetKey: kind === "preset" ? presetKey || null : null },
    };
    // The confirm frame content resolves from the committed panel every
    // access — the confirm copy (`creation.confirmItems`) is deleted.
    ctx.pushFrame(ctx.creation.confirmDescriptor, null);
  }
  ctx.openCreationConfirm = openCreationConfirm;

  // Router submit for a creation item (the legacy `handleItem`): submenu opens,
  // preset-card saves, confirm dispatches, and cancel pops one level. Returns
  // true when the item belonged to the creation dock.
  ctx.handleCreationItem = function handleCreationItem(item) {
    if (!ctx.creation) {
      return false;
    }
    if (item.openSubmenu === "presets") {
      ctx.creation.view = "presets";
      ctx.pushFrame({ source: "creation.presets", params: {} }, item.key);
      return true;
    }
    if (item.openSubmenu === "custom") {
      ctx.creation.view = "custom";
      // A marker frame gives Escape a level to pop without discarding values.
      ctx.pushFrame({ source: "creation.form", params: { view: "custom" } }, item.key);
      return true;
    }
    if (item.openSubmenu === "concept") {
      ctx.creation.view = "concept";
      // The concept entry point opens the free-text concept field; a marker
      // frame gives Escape a level to pop without discarding typed values.
      ctx.pushFrame({ source: "creation.form", params: { view: "concept" } }, item.key);
      return true;
    }
    if (item.presetKey) {
      const requestId = ctx.dispatchAction(CreationMenu.PRESET_ACTION, {
        preset_key: item.presetKey,
      });
      if (requestId !== null) {
        ctx.creation.pendingSaveRequestId = requestId;
        ctx.creation.pendingActivate = "preset";
        ctx.creation.pendingActivateKey = item.presetKey;
      }
      return true;
    }
    if (
      item.actionId === CreationMenu.ACTIVATE_ACTION ||
      item.actionId === CreationMenu.RESET_ACTION
    ) {
      ctx.dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
      return true;
    }
    if (item.key && item.key.indexOf("cancel-") === 0) {
      ctx.inStackMutation = true;
      try {
        ctx.router.popMenu();
      } finally {
        ctx.inStackMutation = false;
      }
      ctx.creation.view = ctx.creation.pendingActivate === "preset" ? "presets" : "custom";
      ctx.creation.pendingActivate = null;
      ctx.creation.pendingActivateKey = null;
      ctx.creation.confirmDescriptor = null;
      // The guarded pop suppresses the focus-driven publish; publish the
      // restored view here so the overlay slice loses the confirm rows.
      ctx.publishView();
      return true;
    }
    return false;
  };

  // Router escape/menu-closed for creation: pop exactly one menu level and
  // restore the matching view without discarding the server draft (the legacy
  // `onRouterEvent` menu handling). The custom form's marker menu and the
  // confirm screens all restore to root / presets / custom.
  ctx.handleCreationMenuEvent = function handleCreationMenuEvent(name) {
    if (!ctx.creation) {
      return;
    }
    if (ctx.creation.view === "presets") {
      ctx.creation.view = "root";
    } else if (ctx.creation.view === "confirm") {
      // Restore exactly the stage the confirmation was opened from (a reset
      // confirm opened on the preset page returns to presets, one opened on
      // the custom form returns to custom, ...).
      ctx.creation.view = ctx.creation.returnStage || "root";
      ctx.creation.returnStage = null;
      ctx.creation.pendingActivate = null;
      ctx.creation.pendingActivateKey = null;
      ctx.creation.confirmDescriptor = null;
    } else if (ctx.creation.view === "custom") {
      ctx.creation.view = "root";
    } else if (ctx.creation.view === "concept") {
      ctx.creation.view = "root";
    }
    if (name === "escape-root") {
      // escape-root does not pop a router level: re-sync the router to the
      // frame matching the restored view (declaratively).
      pushOrReplaceFrameForView(ctx.creation.view);
    }
    ctx.publishView();
  };

  // The creation stage -> frame descriptor map (the one source for the
  // root-reset and escape-root re-syncs).
  function descriptorForCreationView(viewName) {
    if (viewName === "presets") {
      return { source: "creation.presets", params: {} };
    }
    if (viewName === "custom" || viewName === "concept") {
      return { source: "creation.form", params: { view: viewName } };
    }
    if (viewName === "confirm" && ctx.creation && ctx.creation.confirmDescriptor) {
      return ctx.creation.confirmDescriptor;
    }
    return { source: "creation.root", params: {} };
  }

  function pushOrReplaceFrameForView(viewName) {
    const descriptor = descriptorForCreationView(viewName);
    ctx.inStackMutation = true;
    try {
      if (ctx.router.depth() > 0) {
        ctx.router.replaceFrame(descriptor, { openerKey: null });
      } else {
        ctx.router.pushFrame(descriptor, { openerKey: null });
      }
    } finally {
      ctx.inStackMutation = false;
    }
  }

  // Rebuild the creation dock state for the committed view (the legacy
  // creation_dock.js subscribe/mount logic): mount on entering creation mode,
  // rebuild menus when the panel signature changes, resume the server-
  // persisted draft stage, and resolve the pending save's confirmation.
  ctx.rebuildCreationDock = function rebuildCreationDock(prev, rs) {
    const panel = creationPanelOf(rs);
    if (!panel) {
      if (ctx.creation) {
        ctx.creation = null;
      }
      return;
    }
    if (!ctx.creation) {
      ctx.creation = {
        view: "root",
        confirmDescriptor: null,
        pendingActivate: null,
        pendingActivateKey: null,
        pendingSaveRequestId: null,
        returnStage: null,
        panelSig: null,
      };
    }
    // Resolve a pending save's confirmation BEFORE the panel-signature
    // refresh (the legacy dock's ordering): the just-saved draft's panel
    // arrives with or right after the save result, so the refresh must open
    // — and never clobber — the confirmation for the just-saved draft
    // (fix-creation-finalization-safety D1): success opens the confirmation;
    // rejection or error stays on the current view.
    if (ctx.creation.pendingSaveRequestId !== null) {
      const result = rs.lastActionResult || null;
      const prevResult = prev ? prev.lastActionResult || null : null;
      if (result && result !== prevResult && result.requestId === ctx.creation.pendingSaveRequestId) {
        ctx.creation.pendingSaveRequestId = null;
        if (result.outcome === "success") {
          const kind = ctx.creation.pendingActivate || "preset";
          // A successful preset save opens the confirmation from the preset
          // list; a custom/concept save from the form.
          openCreationConfirm(
            kind,
            ctx.creation.pendingActivateKey,
            kind === "preset" ? "presets" : "custom",
          );
          return;
        }
        ctx.creation.pendingActivate = null;
        ctx.creation.pendingActivateKey = null;
      }
    }
    const sig = creationPanelSignature(panel);
    if (ctx.creation.panelSig !== sig) {
      ctx.creation.panelSig = sig;
      const draft = panel.draft || null;
      if (draft && draft.mode === "preset") {
        openCreationConfirm("preset", draft.preset_key || null, "presets");
      } else if (draft && (draft.mode === "custom" || draft.mode === "concept")) {
        if (ctx.creation.view !== "confirm") {
          ctx.creation.view = "custom";
          // The custom-form marker frame is the one-frame stack (Escape
          // resumes the root). Declarative: the frame is the descriptor.
          ctx.router.resetFrame({ source: "creation.form", params: { view: "custom" } }, { openerKey: null });
        }
      } else if (ctx.creation.view !== "confirm") {
        ctx.creation.view = "root";
        // The root frame re-posts from the committed panel on every genuine
        // signature change (same reset semantics; no menu copy is built).
        ctx.router.resetFrame({ source: "creation.root", params: {} }, { openerKey: null });
      }
    }
  };

  ctx.syncRouterGates = function syncRouterGates() {
    ctx.router.setMutationInFlight(!!ctx.inFlight);
    ctx.router.setAwaitingRevision(ctx.inFlight && ctx.inFlight.presentationRevision !== null ? ctx.inFlight.presentationRevision : null);
  };

  // H4 (task 4.3/4.4): the drawer controller's commit-path sync. Runs on
  // every committed view (the store is the single writer). It (a) tears
  // down the drawers on a mode change, an epoch reset, or a transport loss
  // (design D3). The status drawer's payload is available in every mode, so it
  // stays openable in combat.
  ctx.syncHudDrawer = function syncHudDrawer(prev, rs) {
    // Re-entrancy guard: a router stack mutation emits `focus`, which
    // re-enters `publishView`. The old signature gates stopped that loop
    // for the copy path; with declarative frames the guard is explicit —
    // the outer mutation already applied the teardown, a nested pass must
    // mutate nothing (the legacy copy families' rebuilds were exactly the
    // recursion the old `lastMenuSig` existed to break).
    if (ctx.inStackMutation) {
      return;
    }
    const modeChanged = !!prev && prev.mode !== rs.mode;
    const epochChanged = !!prev && prev.epoch !== rs.activeEpoch;
    const transportLost = !!prev && prev.connected && !rs.connected;
    // No-puppet detach is a teardown event in its own right: the reducer
    // retains the epoch and the mode on a `no_puppet` protocol error, so
    // the three transitions above never fire for it. Without this
    // condition a depth >1 exploration stack would survive the character
    // leaving the puppet.
    const detached = !!prev && prev.phase !== "detached" && rs.phase === "detached";

    if (modeChanged || epochChanged || transportLost || detached) {
      // A committed mode change out of exploration, an epoch reset, or a
      // transport loss each close the services-backed drawers and discard
      // local selection, quantity, and confirmation state (the quantity
      // form is also nulled by the panel-replacement logic above).
      const d = ctx.hudDrawer.value;
      if (d === "quest" || d === "shop" || d === "inventory") {
        ctx.hudDrawer.value = null;
      }
      if (rs.mode === "creation" && d === "party") {
        ctx.hudDrawer.value = null;
      }
      if (transportLost || epochChanged || detached) {
        if (ctx.hudDrawer.value) {
          ctx.hudDrawer.value = null;
        }
      }
      // H5 (webclient-hud-05-overlays-and-command-line, design D7): the
      // open full-screen overlay is force-closed on the same three events
      // (mode change into creation, epoch reset, transport loss); the host
      // restores focus to the overlay's own trigger (the opener element
      // captured at open time, design D7).
      if (ctx.hudOverlay.value !== null) {
        ctx.hudOverlay.value = null;
        ctx.hudOverlayOpener.value = null;
      }
      // Teardown final form (webclient-services-combat-creation-frames):
      // every event above yields EXACTLY one root frame — the committed
      // mode's declarative root descriptor. The mode the teardown targets
      // may not have its panel committed yet; the root then degrades to the
      // marker-reason row and recovers on the next commit (no copy rebuild,
      // no empty-stack fuse).
      ctx.resetFramesToRoot();
      return;
    }


    // webclient-align-05-party-hud: on a committed transition where party
    // data becomes unavailable, or mode transitions into creation, close the party drawer.
    const prevPartyPanel = (prev && prev.panels && prev.panels.party) || null;
    const nextPartyPanel = (rs.panels && rs.panels.party) || null;
    const partyBecameUnavailable =
      !!prevPartyPanel && prevPartyPanel.available === true && (!nextPartyPanel || nextPartyPanel.available !== true);

    if (ctx.hudDrawer.value === "party" && (partyBecameUnavailable || rs.mode === "creation")) {
      ctx.hudDrawer.value = null;
    }
  };
}
