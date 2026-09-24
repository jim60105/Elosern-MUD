// The committed-view group of the composed Elosern store: `buildView` (the
// single view projection over the reducer's committed state plus the
// client-local slices) and `publishView` (the commit hook ordering).
//
// D2: every reducer commit publishes one new committed view object, replaced
// wholesale — no subscriber ever observes a partially applied panel state.

import { computed } from "vue";
import OptionCards from "../../lib/option_cards.js";
import LocalMap from "../../lib/local_map.js";
import { gaugeRatio, isLowHp, isVitalsVisible } from "../../components/vitals.js";
import {
  NAVIGATION_ITEM_KEYS,
  resolveLocationLabel,
  formatTimeLabel,
  connectionStatusFor,
  readPanel,
} from "./shared.js";

export function applyView(ctx) {
  ctx.buildView = function buildView(prev, rs) {
    const panels = rs.panels || {};
    const panel = panels.context_actions || null;
    const suggestions = panel && panel.suggestions ? panel.suggestions : null;
    // Pre-session totality: before the first publish mounts the root
    // descriptor the stack is empty (the mount point is `settleFrameStack`),
    // where frame-content reads would throw. `mounted` guards every read.
    const mounted = ctx.router.depth() > 0;
    const currentItem = mounted ? ctx.router.currentItem() : null;
    const navigationMenu = mounted ? ctx.frameResolver.resolve(ctx.rootDescriptorFor(rs)) : null;
    // The combat selection reads resolve through the resolver's one model —
    // calling it here is the adoption point; outside combat form it is null.
    const combatNow = panel && panel.kind === "combat" ? ctx.frameResolver.combatModel() : null;
    // The creation confirm copy is deleted: the overlay's confirm intent
    // resolves through the current confirm descriptor at view-build time.
    const resolvedConfirmItems =
      ctx.creation && ctx.creation.view === "confirm" && ctx.creation.confirmDescriptor
        ? (() => {
            const menu = ctx.frameResolver.resolve(ctx.creation.confirmDescriptor);
            return menu && !menu.unresolvable && Array.isArray(menu.items) ? menu.items : [];
          })()
        : [];

    // The derived vitals slice (H2, design D5): the three gauge ratios plus
    // the low-HP presentation state, computed from the committed `status`
    // payload alone — no new payload field, no server call. An unavailable
    // status panel yields null ratios and `lowHp: false` (not true by
    // default); the state is non-load-bearing, so the numerals and the 危險
    // marker carry the same information at every value.
    const statusPanel = panels.status;
    let vitals;
    if (statusPanel && statusPanel.available !== false && statusPanel.resources) {
      const lowHp = isLowHp(statusPanel.resources);
      vitals = {
        hp: gaugeRatio(statusPanel.resources.hp),
        mp: gaugeRatio(statusPanel.resources.mp),
        sp: gaugeRatio(statusPanel.resources.sp),
        lowHp,
        visible: isVitalsVisible({
          mode: rs.mode,
          resources: statusPanel.resources,
          conditions: statusPanel.conditions,
          lowHp,
        }),
      };
    } else {
      vitals = { hp: null, mp: null, sp: null, lowHp: false, visible: false };
    }

    // Party read model (webclient-align-05-party-hud): committed party slots
    // from the available `party` panel (empty array when unavailable or absent).
    const partyPanel = readPanel(rs, "party");
    const partyAvailable = !!partyPanel && partyPanel.available === true;
    const partySlots = partyAvailable && Array.isArray(partyPanel.slots) ? partyPanel.slots : [];

    // Objectives read model (webclient-align-09-objective-tracker-ui): committed
    // tracked quest rows from the available `objectives` panel (empty array when
    // unavailable or absent).
    const objectivesPanel = readPanel(rs, "objectives");
    const objectivesAvailable = !!objectivesPanel && objectivesPanel.available === true;
    const objectivesRows =
      objectivesAvailable && Array.isArray(objectivesPanel.rows) ? objectivesPanel.rows : [];

    // Roster read model (webclient-character-roster, multichar-02-roster-read-model):
    // committed account roster rows and capacity/lock facts (empty/default when
    // unavailable or absent).
    const rosterPanel = readPanel(rs, "roster");
    const rosterAvailable = !!rosterPanel && rosterPanel.available === true;
    const rosterCharacters =
      rosterAvailable && Array.isArray(rosterPanel.characters) ? rosterPanel.characters : [];
    const rosterCanCreate =
      rosterAvailable && typeof rosterPanel.can_create === "boolean" ? rosterPanel.can_create : false;
    const rosterMaxCharacters =
      rosterAvailable && typeof rosterPanel.max_characters === "number" ? rosterPanel.max_characters : 0;
    const rosterSwitchLocked =
      rosterAvailable && typeof rosterPanel.switch_locked === "boolean" ? rosterPanel.switch_locked : false;
    const rosterLockReason =
      rosterAvailable && typeof rosterPanel.lock_reason === "string" ? rosterPanel.lock_reason : null;

    // Combat participants (webclient-align-05-party-hud): committed combat participants
    // when context_actions is kind: 'combat' (empty array otherwise).
    const combatParticipants = panel && panel.kind === "combat" && Array.isArray(panel.participants)
      ? panel.participants
      : [];

    // Committed exploration interact targets (webclient-align-05-party-hud):
    // exposed so the party drawer can resolve invite/leave preconditions.
    const explorationPanel = readPanel(rs, "exploration");
    const explorationInteract =
      explorationPanel && explorationPanel.available !== false && Array.isArray(explorationPanel.interact)
        ? explorationPanel.interact
        : [];

    return {
      generation: rs.generation,
      phase: rs.phase,
      epoch: rs.activeEpoch,
      revision: rs.revision,
      mode: rs.mode,
      layoutVersion: rs.layoutVersion,
      serverTime: rs.serverTime,
      panels,
      mutationsLocked: rs.mutationsLocked,
      protocolError: rs.protocolError,
      lastActionResult: rs.lastActionResult,
      retiredEpochCount: rs.retiredEpochCount,
      connected: rs.connected,
      loggedIn: ctx.loggedIn,

      connectionStatus: connectionStatusFor(rs.connected, ctx.loggedIn, rs.phase),
      vitals,
      statusSlice: {
        connected: rs.connected,
        locationLabel: resolveLocationLabel(panels),
        timeLabel: formatTimeLabel(rs.serverTime),
      },
      prompt: ctx.prompt,
      lastSurface: ctx.lastSurface,
      lastTarget: ctx.lastTarget,
      drawerRequest: ctx.drawerRequest,
      drawerCloseRequest: ctx.drawerCloseRequest,
      restFormRequest: ctx.restFormRequest,
      partyAvailable,
      partySlots,
      objectivesAvailable,
      objectivesRows,
      rosterAvailable,
      rosterCharacters,
      rosterCanCreate,
      rosterMaxCharacters,
      rosterSwitchLocked,
      rosterLockReason,
      combatParticipants,
      explorationInteract,
      activeSubDock: ctx.activeSubDock.value,
      // H4 (task 4.1): the single open-drawer name (null | skill | inventory
      // | shop | quest | lore | status); at most one drawer is open at a
      // time (structural: one value).
      hudDrawer: ctx.hudDrawer.value,
      // H5 (task 5.2): the single open-overlay name (null | map | settings
      // | help | lineage), plus the opener element captured at open time —
      // the anchor
      // for the host's focus restoration (design D7).
      hudOverlay: ctx.hudOverlay.value,
      hudOverlayOpener: ctx.hudOverlayOpener.value,
      // H5 (task 7.5/7.8): the client-local presentation preferences the
      // settings surface owns — the narrative prose scale, the text-to-HTML
      // narrative toggle, the optional reduced-motion override and the
      // colorblind status palette. No setting dispatches a `ui_action`; the
      // store applies each to the document's presentation tokens and
      // persists it through the versioned layout store.
      fontScale: ctx.prefs.fontScale,
      textToHtml: ctx.prefs.text2html,
      reducedMotion: ctx.prefs.reducedMotion,
      colorblind: ctx.prefs.colorblind,

      contextActions: panel,
      suggestions,
      suggestionsView: OptionCards.buildOptionsView(panel || {}),
      suggestionsSignature: OptionCards.suggestionsSignature(suggestions),
      localMapModel: panels.local_map
        ? {
            ...LocalMap.reducePanel(panels.local_map),
            available: panels.local_map.available !== false,
            // The registry-owned unavailable reason so the island and the map
            // overlay can render it (H5 offline-degradation, task 8.9).
            reason: panels.local_map.reason,
          }
        : null,
      // The keyboard router's current combat menu frame (root/skills/scale/
      // target) so the visible dock follows keyboard navigation (Option B).
      combatMenu: mounted ? ctx.router.currentMenu() : null,
      // H3 (task 3.2): the root frame's menu — the dock's tab bar renders
      // the root frame's items while the pane follows the current frame,
      // both from one commit. Null while the root is degraded: the marker
      // row is pane content (below), never a tab (the router keeps it out
      // of `rootMenu` for exactly this reason).
      rootMenu: mounted ? ctx.router.rootMenu() : null,
      navigationItems: (navigationMenu?.items || []).filter((item) => NAVIGATION_ITEM_KEYS.has(item.key)),
      // The degraded-root presentation (webclient-frame-resolution): the
      // single disabled marker-reason row the pane host renders while the
      // root frame itself is unresolvable; null in every normal state.
      degradedRoot: mounted ? ctx.router.degradedRoot() : null,
      // The keyboard router's menu depth (1 = the root frame, 2+ = a submenu
      // frame is active). The action dock's detail pane renders only at
      // depth 2+ (or in combat mode), not at the exploration root.
      dockDepth: ctx.router.depth(),
      dockSource: mounted ? ctx.router.currentDescriptor().source : null,
      // H3: the full frame stack (root -> current), the data source for
      // the dock's breadcrumb (HudFrame's crumb strip renders these).
      dockTrail: mounted ? ctx.router.trail() : [],
      // The focused AREA skill's selected candidate identities (the client-
      // local selection the Space toggle mutates); drives the "✓" marker.
      combatSelected:
        combatNow && combatNow.focusSkillKey && combatNow.skillByKey[combatNow.focusSkillKey]
          ? combatNow.skillByKey[combatNow.focusSkillKey].selected
          : [],
      // H3 (task 6.5): the focused skill model for the master-detail pane —
      // the `SkillDetailPane` renders this committed model, never inventing
      // a `戰鬥外` badge (design D14).
      focusedSkill:
        combatNow && combatNow.focusSkillKey && combatNow.skillByKey[combatNow.focusSkillKey]
          ? combatNow.skillByKey[combatNow.focusSkillKey]
          : null,

      // The character-creation dock stage (the legacy creation dock port): the
      // keyboard-router menu the overlay mirrors. Null outside creation mode.
      creationView: ctx.creation
        ? {
            stage: ctx.creation.view,
            confirmItems: resolvedConfirmItems,
            confirmLabel: resolvedConfirmItems.length > 0 ? resolvedConfirmItems[0].label : null,
            confirmAction:
              resolvedConfirmItems.length > 0 ? resolvedConfirmItems[0].actionId : null,
            pendingPresetKey: ctx.creation.pendingActivateKey,
          }
        : null,

      focus: currentItem
        ? {
            key: currentItem.key !== undefined ? currentItem.key : currentItem.label,
            label: currentItem.label,
            enabled: currentItem.enabled,
            description: currentItem.description,
          }
        : { key: null, label: null, enabled: null, description: null },

      dispatch: {
        inFlight: ctx.inFlight ? { requestId: ctx.inFlight.requestId, presentationRevision: ctx.inFlight.presentationRevision } : null,
        uncertain: ctx.uncertain,
        submittedRequestId: ctx.lastSubmittedRequestId,
        // Whether a mutation was submitted and its result not yet confirmed
        // (the client-local uncertain-marking precondition, exposed for the
        // browser harness).
        mutationSubmitted: ctx.mutationSubmitted,
      },

      // The live client-local toast queue (webclient-action-feedback D1): the
      // same reactive array reference on every publish; the reducer's
      // committed snapshot never carries it and nothing persists it.
      toasts: ctx.toasts.value,
    };
  };

  ctx.publishView = function publishView() {
    const prev = ctx.view.value;
    const rs = ctx.reducer.getState();
    ctx.handleTransportLifecycle(prev, rs);
    ctx.handleActionResult(rs);
    ctx.releaseIfReady(rs);
    ctx.rebuildCreationDock(prev, rs);
    ctx.syncRouterGates();
    ctx.settleFrameStack(rs);
    ctx.syncHudDrawer(prev, rs);
    ctx.view.value = ctx.buildView(prev, rs);
  };

  ctx.markNarrativeSeen = function markNarrativeSeen() {
    ctx.seenIndex.value = ctx.narrative.value.length;
  };

  ctx.unreadCount = computed(() =>
    ctx.narrative.value
      .slice(ctx.seenIndex.value)
      .filter((line) => line.kind === "out")
      .length
  );

  const partyAvailable = computed(() => !!ctx.view.value.partyAvailable);
  const partySlots = computed(() => ctx.view.value.partySlots || []);
  const objectivesAvailable = computed(() => !!ctx.view.value.objectivesAvailable);
  const objectivesRows = computed(() => ctx.view.value.objectivesRows || []);
  const rosterAvailable = computed(() => !!ctx.view.value.rosterAvailable);
  const rosterCharacters = computed(() => ctx.view.value.rosterCharacters || []);
  const rosterCanCreate = computed(() => !!ctx.view.value.rosterCanCreate);
  const rosterMaxCharacters = computed(() => ctx.view.value.rosterMaxCharacters || 0);
  const rosterSwitchLocked = computed(() => !!ctx.view.value.rosterSwitchLocked);
  const rosterLockReason = computed(() => ctx.view.value.rosterLockReason || null);
  const combatParticipants = computed(() => ctx.view.value.combatParticipants || []);
  const explorationInteract = computed(() => ctx.view.value.explorationInteract || []);
  Object.assign(ctx.computed, {
    partyAvailable,
    partySlots,
    objectivesAvailable,
    objectivesRows,
    rosterAvailable,
    rosterCharacters,
    rosterCanCreate,
    rosterMaxCharacters,
    rosterSwitchLocked,
    rosterLockReason,
    combatParticipants,
    explorationInteract,
  });
}
