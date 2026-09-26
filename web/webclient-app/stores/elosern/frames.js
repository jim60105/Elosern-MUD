// The declarative-frame-stack group of the composed Elosern store.
//
// Every family's frames are DECLARATIVE (webclient-declarative-frame-stack,
// completed by webclient-services-combat-creation-frames): a push stores
// only a `{source, params}` descriptor; every read of the frame resolves
// through the injected registry seam at access time, so a committed push
// ALWAYS reaches an open frame — no copy-based refresh, signature gate,
// re-home, or raw-row resync machinery exists anywhere.
//
// The keyboard router (design D4) owns the focus state; its events are
// routed through the same store actions (a broken renderer must never
// break the reducer). The declarative-frame resolver is injected so every
// read of a declarative frame resolves at access time (webclient-
// declarative-frame-stack D-A); the router never copies a resolved menu.

import KeyboardRouter from "../../lib/keyboard_router.js";
import CombatMenu from "../../lib/combat_menu.js";
import { actionIntentForItem } from "../../components/dock-items.js";

// The committed exploration room identity (webclient-scene-overview-swap D2):
// the exploration panel's own stable movement key — `look.room.identity`. It
// changes exactly on movement and needs no narrative parsing (a
// `local_map.current_node` change would miss rooms without map knowledge).
// Null when the panel is absent or in its unavailable form: an unavailable
// panel never resets the stack.
function explorationRoomIdentity(rs) {
  const panel = (rs && rs.panels && rs.panels.exploration) || null;
  const room = (panel && panel.look && panel.look.room) || null;
  const identity = room ? room.identity : null;
  return identity === undefined ? null : identity;
}

export function applyFrames(ctx) {
  // D4: the imported keyboard router owns the focus state.
  const router = KeyboardRouter.createRouter({
    // The router is created before `onRouterEvent` is assigned (the original
    // relied on the function declaration being hoisted); events only fire on
    // key entry, long after composition, so the indirection is inert.
    onEvent: (name, payload) => ctx.onRouterEvent(name, payload),
    resolve: (descriptor) => {
      const menu = ctx.frameResolver.resolve(descriptor);
      if (descriptor.source === "exploration.suggestions" && Array.isArray(menu.items)) {
        // Readable cards and action choices share a vertical keyboard list.
        menu.gridCols = 1;
      }
      if (descriptor.source === "exploration.wait" && Array.isArray(menu.items)) {
        menu.gridCols = 3;
      }
      return menu;
    },
  });
  // The live keyboard-router instance (C4 harness re-map): the managed
  // browser suite reads `depth()` / `currentItem()` off it; the store owns
  // the focus router (design D4), so it is exposed read-only for the harness.
  ctx.router = router;

  // The exploration root descriptor (webclient-declarative-frame-stack): the
  // one source for root pushes, replaces, and teardown re-homes.
  const EXPLORATION_ROOT_DESCRIPTOR = Object.freeze({
    source: "exploration.root",
    params: Object.freeze({}),
  });
  ctx.EXPLORATION_ROOT_DESCRIPTOR = EXPLORATION_ROOT_DESCRIPTOR;
  // The per-mode root descriptors (webclient-services-combat-creation-frames):
  // teardown and the explicit root reset post EXACTLY one root frame in every
  // mode — the empty-stack `router.reset` fuse is deleted, the stack never
  // empties in a live mode.
  const MODE_ROOT_DESCRIPTORS = Object.freeze({
    exploration: EXPLORATION_ROOT_DESCRIPTOR,
    combat: Object.freeze({ source: "combat.root", params: Object.freeze({}) }),
    creation: Object.freeze({ source: "creation.root", params: Object.freeze({}) }),
  });
  ctx.rootDescriptorFor = function rootDescriptorFor(rs) {
    // webclient-align-11-dialogue-ux: dialogue mode has NO dock form of its
    // own. The committed `dialogue` panel renders in the narrative caption;
    // the dock stays on the exploration root — the scene overview
    // (webclient-scene-overview-swap) — through a talk (the heuristic below
    // serves `exploration.root`, because the context_actions panel keeps its
    // exploration kind while talking), so movement, services, and the
    // interact affordances stay reachable mid-conversation.
    // The combat family is keyed on the committed panel form (panel.kind),
    // exactly as the deleted copy push sites were; creation on the session
    // mode; everything else on the exploration root.
    const panel = (rs && rs.panels && rs.panels.context_actions) || null;
    if (panel && panel.kind === "combat") {
      return MODE_ROOT_DESCRIPTORS.combat;
    }
    if (rs && rs.mode === "creation") {
      return MODE_ROOT_DESCRIPTORS.creation;
    }
    return MODE_ROOT_DESCRIPTORS.exploration;
  };
  // The shared lifecycle predicate (webclient-align-11-dialogue-ux, design D8):
  // modes whose dock is served by the exploration form. Every exploration-only
  // lifecycle guard (drawer close/re-home, Escape/menu-close sub-dock cleanup,
  // settle-driven teardown, the submit gates) accepts BOTH modes, so a
  // services/character sub-dock opened while talking closes, re-homes, and
  // settles exactly as in exploration mode. Partial widening is the known
  // failure mode this guards.
  ctx.dockOnExplorationForm = function dockOnExplorationForm(rs) {
    return rs.mode === "exploration" || rs.mode === "dialogue";
  };
  // The single root-reset entry (replaces the deleted menu-less
  // `router.reset` the browser helpers used): post the committed mode's root
  // descriptor as the one-frame stack. Browser helpers use it to normalize
  // the stack.
  ctx.resetFramesToRoot = function resetFramesToRoot() {
    ctx.inStackMutation = true;
    try {
      router.resetFrame(ctx.rootDescriptorFor(ctx.reducer.getState()), { openerKey: null });
    } finally {
      ctx.inStackMutation = false;
    }
  };

  // The one declarative push (webclient-services-combat-creation-frames):
  // every family mounts ONLY a descriptor; content resolves at access time.
  // `openerKey` restores the parent's focus on a degradation; `unresolvable`
  // "root" exits the whole stack (the suggestions status split).
  ctx.pushFrame = function pushFrame(descriptor, openerKey, unresolvable) {
    ctx.inStackMutation = true;
    try {
      router.pushFrame(descriptor, {
        openerKey: openerKey === undefined ? null : openerKey,
        unresolvableAction: unresolvable || "pop",
      });
    } finally {
      ctx.inStackMutation = false;
    }
  };

  ctx.onRouterEvent = function onRouterEvent(name, payload) {
    if (name === "settle-pop") {
      ctx.settlePopSeen = true;
      return;
    }
    if (name === "focus" || name === "disabled") {
      const combat = ctx.frameResolver.combatModel();
      if (name === "focus" && combat) {
        const item = payload && payload.item;
        // A focused skill row (its key is in the committed `skillByKey`) sets
        // the focused-skill model so the detail pane renders the skill's
        // (possibly disabled) reason — even for a disabled skill whose row
        // carries no `open-skill` action.
        if (
          item &&
          typeof item.key === "string" &&
          combat.skillByKey &&
          combat.skillByKey[item.key]
        ) {
          combat.focusSkillKey = item.key;
        }
        // A combat target-row focus is a client-local selection (spec: focus
        // and selection remain client-local until submission); record the
        // selected identity without dispatching any OOB action.
        if (
          item &&
          typeof item.key === "string" &&
          item.key.startsWith("target-") &&
          item.payload &&
          Array.isArray(item.payload.target_ids) &&
          item.payload.target_ids.length > 0
        ) {
          ctx.lastTarget = String(item.payload.target_ids[0]);
        }
      }
      ctx.publishView();
      return;
    }
    if (name === "menu-closed" || name === "escape-root") {
      if (ctx.creation) {
        ctx.handleCreationMenuEvent(name);
      }
      // Escape from an exploration re-homed sub-dock (character / services):
      // clear the sub-dock and re-home the exploration root frame.
      else if (ctx.dockOnExplorationForm(ctx.reducer.getState()) && ctx.activeSubDock.value) {
        ctx.setActiveSubDock(null);
        // The sub-dock owned the surface, not the frame stack: re-home the
        // declarative exploration root (the sub-dock frames were legacy).
        ctx.inStackMutation = true;
        try {
          router.replaceFrame(EXPLORATION_ROOT_DESCRIPTOR, { openerKey: null });
        } finally {
          ctx.inStackMutation = false;
        }
      }
      return;
    }
    if (name === "toggle-drawer") {
      // The `/` key routes bridge -> router -> here. Bump `drawerRequest`
      // so the shell's watcher expands the command line and focuses the field.
      ctx.drawerRequest += 1;
      ctx.publishView();
      return;
    }
    if (name !== "submit" && name !== "space") {
      return;
    }
    const item = payload && payload.item;
    if (!item) {
      return;
    }
    // Activation reads the RAW committed row (the focus projection strips the
    // intent fields): re-sync the key map for the current frame first (the
    // frame did not change between the focus event and this activation).
    // (webclient-services-combat-creation-frames: the router emits the full
    // resolved row — the dockRawByKey re-sync seam is deleted.)
    // The creation dock owns the router in creation mode (the legacy
    // creation_dock.js keyboard journey): submenu opens, preset-card saves,
    // confirmation dispatches, and cancel pops one level.
    if (ctx.creation && ctx.handleCreationItem(item)) {
      return;
    }
    // The exploration dock owns the router in exploration mode (the G2
    // hierarchical root + submenus): root entries open Move/Look/Interact/Wait
    // submenus and the Character/Quests/Inventory sub-docks, submenu rows
    // dispatch their `explore.*` actions.
    if (ctx.handleExplorationItem(item)) {
      return;
    }
    // Combat keyboard hierarchy (the preserved CombatMenu model, mirroring the
    // legacy elosern_ui plugin's routing): open-skill / attack open a skill's
    // scale or target frame, skills / forfeit open their submenus, Space
    // toggles AREA candidates, and confirm submits the exact payload. The one
    // model instance is the registry's (the declared selection home).
    const combat = ctx.frameResolver.combatModel();
    if (combat) {
      if (name === "space") {
        if (item.actionId === "toggle-target" && item.payload && combat.focusSkillKey) {
          CombatMenu.toggleArea(combat, combat.focusSkillKey, item.payload.identity);
          ctx.publishView();
        }
        return;
      }
      // An AREA candidate row activated deliberately (pointer click or Enter on
      // the row) toggles the client-local selection exactly like Space; it is
      // never an OOB action (the server registers no `toggle-target`).
      if (item.actionId === "toggle-target") {
        if (item.payload && combat.focusSkillKey) {
          CombatMenu.toggleArea(combat, combat.focusSkillKey, item.payload.identity);
        }
        ctx.publishView();
        return;
      }
      // "open" items push a submenu (no OOB packet is sent).
      if (item.actionId === "open-skill" && item.payload) {
        ctx.openCombatSkill(item.payload.skillKey);
        return;
      }
      // H3: the skills tab pushes the category frame; a category with a
      // single skill group skips the group frame (openCategory collapses it),
      // a multi-group category pushes the group frame, and a group pushes
      // that group's skill frame (open-group).
      if (item.actionId === "open-category" && item.payload) {
        ctx.pushFrame(
          { source: "combat.category", params: { categoryIndex: item.payload.categoryIndex || 0 } },
          item.key
        );
        ctx.publishView();
        return;
      }
      if (item.actionId === "open-group" && item.payload) {
        ctx.pushFrame(
          {
            source: "combat.group",
            params: { categoryIndex: item.payload.categoryIndex || 0, groupIndex: item.payload.groupIndex || 0 },
          },
          item.key
        );
        ctx.publishView();
        return;
      }
      if (item.actionId === "choose-scale" && item.payload) {
        if (combat.focusSkillKey && CombatMenu.chooseScale(combat, combat.focusSkillKey, item.payload.scale)) {
          // The scale step confirmed: the target frame mounts the same
          // focused skill key; the resolver opens targets through the model.
          ctx.pushFrame({ source: "combat.target", params: { skillKey: combat.focusSkillKey } }, item.key);
          ctx.publishView();
          return;
        }
        return;
      }
      if (item.actionId === "choose-shorthand" && item.payload) {
        if (combat.focusSkillKey) {
          CombatMenu.chooseShorthand(combat, combat.focusSkillKey, item.payload.shorthand);
          ctx.publishView();
        }
        return;
      }
      if (item.key === "attack") {
        ctx.openCombatSkill(CombatMenu.BASIC_ATTACK_KEY);
        return;
      }
      if (item.key === "skills") {
        // H3: the skills tab opens the category frame (master-detail
        // navigation), replacing the flat paginated skill list.
        ctx.pushFrame({ source: "combat.categories", params: {} }, item.key);
        ctx.publishView();
        return;
      }
      if (item.key === "forfeit") {
        ctx.pushFrame({ source: "combat.forfeit", params: {} }, item.key);
        ctx.publishView();
        return;
      }
      // The client-local 背包 drawer row (add-inventory-item-actions, task
      // 6.3): activation opens the frameless inventory drawer without a
      // dispatch, an invented gameplay action, or a router frame.
      if (item.openDrawer === "inventory") {
        ctx.openHudDrawer("inventory");
        return;
      }
      // AREA confirm: build the exact payload from the live selection.
      if (item.confirm && combat.focusSkillKey) {
        const skill = combat.skillByKey[combat.focusSkillKey];
        if (skill && skill.targetSpec === "area") {
          const areaPayload = CombatMenu.areaPayload(skill);
          if (areaPayload) {
            ctx.dispatchAction(
              "combat.cast",
              areaPayload,
              ctx.castSubmitDisplay(skill, areaPayload, item.commandDisplay)
            );
          }
          return;
        }
      }
      // SINGLE-target rows: focus and selection remain client-local until
      // submission (no focus/selection mutation is ever sent); a deliberate
      // confirmation submits the OOB cast. Pointer activation performs the
      // identical confirmation the keyboard performs — exactly one
      // `combat.cast` with the same action ID and payload
      // (webclient-pointer-activation).
      if (
        typeof item.key === "string" &&
        item.key.startsWith("target-") &&
        item.payload &&
        Array.isArray(item.payload.target_ids) &&
        item.payload.target_ids.length > 0
      ) {
        ctx.lastTarget = String(item.payload.target_ids[0]);
        const focusSkill = combat.focusSkillKey
          ? combat.skillByKey[combat.focusSkillKey]
          : null;
        ctx.dispatchAction(
          "combat.cast",
          item.payload,
          focusSkill
            ? ctx.castSubmitDisplay(focusSkill, item.payload, item.commandDisplay)
            : item.commandDisplay || null
        );
        ctx.publishView();
        return;
      }
      // Real OOB action items (combat.cast / combat.flee / combat.forfeit).
      if (item.actionId) {
        ctx.dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
        return;
      }
    }
    // The router emits the full resolved row (the focus PROJECTION in the
    // view is what strips intent fields, not the event): the OOB intent,
    // navigation surface, and target identity read straight off it.
    const raw = item;
    const intent = actionIntentForItem(raw);
    if (intent) {
      ctx.dispatchAction(intent.action_id, intent.payload);
      return;
    }
    if (raw.navigation === true && typeof raw.surface === "string") {
      ctx.lastSurface = raw.surface;
    } else if (raw.identity !== undefined) {
      ctx.lastTarget = String(raw.identity);
    }
    ctx.publishView();
  };

  // The exploration-family push map: a root `openSubmenu` key or submenu frame
  // title -> the descriptor of its declarative frame. The map is the ONE
  // place naming exploration frame sources; the frame content itself comes
  // only from the resolver.
  ctx.EXPLORATION_SUBMENU_PUSHES = {
    wait: { source: "exploration.wait", params: {} },
    suggestions: { source: "exploration.suggestions", params: {} },
  };
  // The suggestions frame leaves the WHOLE stack when its envelope commits
  // `unavailable` (the options-surface no-pane rule): exit to the root
  // without a reason row. Every other exploration submenu pops one level.
  ctx.UNRESOLVABLE_ACTION = { "exploration.suggestions": "root" };

  // The declarative-frame mutation window (webclient-declarative-frame-stack
  // D-A): the ONE commit hook for the exploration dock. A committed push
  // never re-pushes anything — the next access re-resolves. This window only
  // (a) settles the stack so a degradation pops synchronously at the commit,
  // and (b) discards the sub-dock the frame stack no longer hosts.
  // The combat/creation settle follows the same descriptor-driven rules;
  // no family has a copy-based refresh path any more.
  ctx.settleFrameStack = function settleFrameStack(rs) {
    if (ctx.inStackMutation) {
      return;
    }
    // The stack is never empty in a live mode; depth 0 only exists between
    // store creation and the first commit (the pre-session window), where
    // there is nothing to settle.
    // A settle-driven pop is observed through the router's `settle-pop`
    // event (recorded here, cleared per window): the depth BEFORE a settle
    // cannot be sampled — every accessor settles first, so a pre-read would
    // consume the very pop the rules below must observe.
    ctx.settlePopSeen = false;
    const depthBefore = router.depth();
    if (depthBefore === 0) {
      // The stack mount: an empty stack only exists before the first
      // teardown/publish, where the committed mode's root descriptor is
      // posted as the one-frame stack (it degrades to the marker-reason row
      // until its panel commits, then recovers). After this point the stack
      // never empties in a live mode.
      ctx.resetFramesToRoot();
      return;
    }
    ctx.inStackMutation = true;
    let descriptor = null;
    try {
      router.depth(); // access-time settle: pops/cascades/degrades, zero timers
      descriptor = router.currentDescriptor();
      // Family re-home: a committed panel-form switch (exploration panel ->
      // combat panel on the SAME stack) re-posts the root DESCRIPTOR of the
      // new family when the root frame is current — the declarative form of
      // the deleted combat signature gate. No copy is built; the new root
      // re-resolves from the committed state on every access.
      if (router.depth() === 1) {
        const want = ctx.rootDescriptorFor(rs);
        if (descriptor && want && descriptor.source !== want.source) {
          router.replaceFrame(want, { openerKey: null });
          descriptor = router.currentDescriptor();
        }
      }
      // Return to the overview on a room change (webclient-scene-overview-swap
      // D2). The committed room identity changes exactly on movement; a move
      // from the minimap or a typed command bypasses the dock's own push
      // sites, so the reset lives here, after the access-time settle (a
      // popover already popped by a departed target is not double-handled).
      // The identity is recorded on every settle: the first settle after
      // mount carries no previous identity and never resets, and an
      // unavailable panel records null.
      if (ctx.dockOnExplorationForm(rs)) {
        const roomIdentity = explorationRoomIdentity(rs);
        if (
          roomIdentity !== ctx.lastRoomIdentity &&
          ctx.lastRoomIdentity !== null &&
          router.depth() > 1
        ) {
          router.resetFrame(EXPLORATION_ROOT_DESCRIPTOR, { openerKey: null });
          descriptor = router.currentDescriptor();
        }
        ctx.lastRoomIdentity = roomIdentity;
      }
    } finally {
      ctx.inStackMutation = false;
    }
    const popped = ctx.settlePopSeen;
    // Sub-dock rule (unchanged): a cascade that popped everything the
    // exploration sub-dock hosts leaves the root, so the sub-dock closes.
    if (
      ctx.dockOnExplorationForm(rs) &&
      ctx.activeSubDock.value &&
      popped &&
      (!descriptor || descriptor.source === "exploration.root")
    ) {
      ctx.setActiveSubDock(null);
    }
  };

  // One declarative exploration push: the store mutation window covers the
  // push itself (the push-time resolve focuses the first item; an
  // immediately-unresolvable push settles per its policy before the focus
  // event reaches the store). `openerKey` is the activated row's key so a
  // later degradation restores focus to it.
  ctx.pushExplorationFrame = function pushExplorationFrame(descriptor, openerKey) {
    // The suggestions status split: `unavailable` exits the whole stack
    // to the root (the no-pane rule); every other submenu pops one level.
    ctx.pushFrame(descriptor, openerKey, ctx.UNRESOLVABLE_ACTION[descriptor.source] || "pop");
  };
}
