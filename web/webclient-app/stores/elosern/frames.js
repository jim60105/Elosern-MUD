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
import {
  committedSubject,
  crossSide,
  crossSideQuestion,
  factsFor,
  targetSetFor,
} from "./cross_side.js";

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
  // The single-target identities a combat row's payload names: a skill row
  // carries the array `target_ids`, an item's or a basic action's row the
  // scalar `target_id` (the closed v7 wire union).
  function singleTargetIds(payload) {
    const body = payload || {};
    if (Array.isArray(body.target_ids)) {
      return body.target_ids;
    }
    return body.target_id === undefined || body.target_id === null ? [] : [body.target_id];
  }

  // D4: the imported keyboard router owns the focus state.
  const router = KeyboardRouter.createRouter({
    // The router is created before `onRouterEvent` is assigned (the original
    // relied on the function declaration being hoisted); events only fire on
    // key entry, long after composition, so the indirection is inert.
    onEvent: (name, payload) => ctx.onRouterEvent(name, payload),
    resolve: (descriptor) => ctx.frameResolver.resolve(descriptor),
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
    // The presence and room cards are not frames, but a root reset leaves no
    // card open.
    ctx.resetPresence?.();
    ctx.resetRoomCard?.();
    // Nor the cross-side question: a root reset drops the held cast unsent.
    ctx.crossSideConfirm = null;
    // Nor a pending actor query: a root reset abandons the local intent, so a
    // late commit never yanks the dock back to the root unprompted.
    ctx.pendingActorSelection = null;
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
  // "root" exits the whole stack.
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

  // ---- The commanded actor and the guarded command envelope ----------------
  // (webclient-party-command-selection)
  //
  // null, or the read-only choices query awaiting its committed panel
  // `{actorId, requestId, generation, sessionId, roundRevision}`.
  ctx.pendingActorSelection = null;
  // null, or the one-shot record of the last combat.command this client
  // dispatched `{requestId, generation, sessionId, roundRevision}`. It lets
  // exactly one committed nonfinal draft save advance to the next missing
  // member; it is never derived from restored draft entries, so a reconnect
  // or a re-observed result can never replay an intent.
  ctx.pendingCombatAdvance = null;
  // The committed combat identity (`session:actor`) the held client-local
  // selection belongs to; a change drops the unconfirmed selection.
  ctx.lastCombatIdentity = null;

  // The committed panel's commanded actor, or null.
  function commandedActorId(panel) {
    return panel && panel.choices && panel.choices.actor_id !== null && panel.choices.actor_id !== undefined
      ? panel.choices.actor_id
      : null;
  }

  // The open entry of the actor selector frame: one deliberate push of the
  // `combat.actor` descriptor from the card chrome. Refused while a mutation
  // is in flight, a round plays, or the cross-side question holds the dock.
  ctx.openCombatActor = function openCombatActor() {
    const rs = ctx.reducer.getState();
    if (!committedCombat(rs) || ctx.inFlight || ctx.beatLocked() || ctx.crossSideConfirm) {
      return false;
    }
    const item = ctx.router.depth() > 0 ? ctx.router.currentItem() : null;
    ctx.pushFrame({ source: "combat.actor", params: {} }, item ? item.key : null);
    // The 變更成員 control disappears once the frame mounts, so hand DOM
    // focus to the dock (never the document body).
    ctx.dockFocusRequest += 1;
    ctx.publishView();
    return true;
  };

  // Activate one actor selector row: the already-commanded actor returns to
  // the root in one deliberate transition; any other member asks the server
  // for that member's canonical choices (one read-only query) and opens the
  // same root flow once its panel commits.
  ctx.selectCombatActor = function selectCombatActor(actorId) {
    const rs = ctx.reducer.getState();
    const panel = committedCombat(rs);
    if (!panel || actorId === null || actorId === undefined) {
      return false;
    }
    if (String(actorId) === String(commandedActorId(panel))) {
      ctx.resetFramesToRoot();
      ctx.dockFocusRequest += 1;
      ctx.publishView();
      return true;
    }
    return ctx.requestCombatActor(actorId);
  };

  // One read-only `combat.actor_choices` query with the committed
  // session/revision/actor. Returns false when the dispatch was refused.
  ctx.requestCombatActor = function requestCombatActor(actorId) {
    const rs = ctx.reducer.getState();
    const panel = committedCombat(rs);
    if (!panel || !panel.session || actorId === null || actorId === undefined) {
      return false;
    }
    const requestId = ctx.dispatchAction("combat.actor_choices", {
      session_id: panel.session.session_id,
      round_revision: panel.session.round_revision,
      actor_id: actorId,
    });
    if (requestId === null || requestId === undefined) {
      return false;
    }
    ctx.pendingActorSelection = {
      actorId,
      requestId,
      generation: rs.generation,
      sessionId: panel.session.session_id,
      roundRevision: panel.session.round_revision,
    };
    return true;
  };

  // The guarded v7 `combat.command` payload for the committed panel, or null.
  // Read at submit time, so the envelope never carries a stale version.
  ctx.buildCombatCommand = function buildCombatCommand(command) {
    return CombatMenu.commandEnvelope(committedCombat(ctx.reducer.getState()), command);
  };

  // Send one already-built envelope through the single dispatch entry and
  // record the one-shot advance correlation for the committed result.
  ctx.submitCombatEnvelope = function submitCombatEnvelope(envelope, display) {
    if (!envelope) {
      return null;
    }
    const rs = ctx.reducer.getState();
    const requestId = ctx.dispatchAction("combat.command", envelope, display);
    if (requestId === null || requestId === undefined) {
      return null;
    }
    ctx.pendingCombatAdvance = {
      requestId,
      generation: rs.generation,
      sessionId: envelope.session_id,
      roundRevision: envelope.round_revision,
    };
    return requestId;
  };

  // One skill command: build the envelope from the committed panel, then send.
  ctx.submitCombatCommand = function submitCombatCommand(command, display) {
    return ctx.submitCombatEnvelope(ctx.buildCombatCommand(command), display);
  };

  // The in-combat drawer's item use (webclient-party-items-tactics): a usable
  // item chosen from the bag is the commanded actor's own round choice, so it
  // enters the canonical item review/target step — the same frame the 道具
  // row opens — and never the actorless `inventory.use`. Refused for an item
  // outside the actor's current usable stock or while a mutation, a played
  // round or the cross-side question holds the dock.
  ctx.useCombatItem = function useCombatItem(itemKey) {
    const rs = ctx.reducer.getState();
    const panel = committedCombat(rs);
    if (!panel || ctx.inFlight || ctx.beatLocked() || ctx.crossSideConfirm) {
      return false;
    }
    const combat = ctx.frameResolver.combatModel();
    if (!combat || typeof itemKey !== "string") {
      return false;
    }
    const item = combat.itemByKey ? combat.itemByKey[itemKey] : null;
    if (!item || !item.enabled) {
      return false;
    }
    // The drawer yields to the card's own target/review step: one frame, the
    // same one the 道具 row pushes, with the card's focus handoff.
    ctx.closeHudDrawer();
    ctx.pushFrame({ source: "combat.item", params: { itemKey: itemKey } }, null);
    ctx.dockFocusRequest += 1;
    ctx.publishView();
    return true;
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
        if (item && typeof item.key === "string" && item.key.startsWith("target-")) {
          const ids = singleTargetIds(item.payload);
          if (ids.length > 0) {
            ctx.lastTarget = String(ids[0]);
          }
        }
      }
      ctx.publishView();
      return;
    }
    if (name === "menu-closed" || name === "escape-root") {
      if (name === "menu-closed") {
        ctx.noteSkillUseEscape();
      }
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
    // The cross-side question is open (webclient-combat-cross-side-confirm
    // D2): the router behind the dialog never activates anything.
    if (ctx.crossSideConfirm) {
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
    // The SkillBook use flow owns its own frames (skillbook-authoritative-
    // casting D6): local rows (AREA toggles, the scale and opening steps)
    // never reach the generic exploration dispatch below.
    if (ctx.handleSkillUseItem(name, item)) {
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
      // The actor selector (webclient-party-command-selection): activating a
      // member row never dispatches a command — it either returns to the root
      // (the already-commanded member) or asks for that member's canonical
      // choices through one read-only query.
      if (
        name === "submit" &&
        typeof item.key === "string" &&
        item.key.startsWith("actor-") &&
        item.actorId !== undefined
      ) {
        ctx.selectCombatActor(item.actorId);
        return;
      }
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
      // The commanded actor's own items and basic actions
      // (webclient-party-items-tactics): 道具 opens the committed stock, one
      // item row opens that item's review/target frame, and 防禦 / 閃避 /
      // 挑釁 open their confirm or enemy-target frame. No local row submits a
      // command of its own.
      if (item.key === "items") {
        ctx.pushFrame({ source: "combat.items", params: {} }, item.key);
        ctx.publishView();
        return;
      }
      if (item.actionId === "open-item" && item.payload) {
        ctx.pushFrame(
          { source: "combat.item", params: { itemKey: item.payload.itemKey } },
          item.key
        );
        ctx.publishView();
        return;
      }
      if (item.key === "defend" || item.key === "dodge" || item.key === "taunt") {
        ctx.pushFrame({ source: "combat.tactic", params: { key: item.key } }, item.key);
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
            const command = { kind: "skill", payload: areaPayload };
            const display = ctx.castSubmitDisplay(skill, areaPayload, item.commandDisplay);
            if (ctx.askCrossSide("skill", "area", item.key, command, display)) {
              return;
            }
            ctx.submitCombatCommand(command, display);
          }
          return;
        }
      }
      // SINGLE-target rows: focus and selection remain client-local until
      // submission (no focus/selection mutation is ever sent); a deliberate
      // confirmation submits the OOB cast. Pointer activation performs the
      // identical confirmation the keyboard performs — exactly one
      // `combat.command` with the same payload
      // (webclient-pointer-activation). An item's and a basic action's
      // SINGLE row carries the same command kind in `commandKind`
      // (webclient-party-items-tactics), so one path covers all three kinds.
      const singleIds = singleTargetIds(item.payload);
      if (typeof item.key === "string" && item.key.startsWith("target-") && singleIds.length > 0) {
        const kind = item.commandKind === undefined ? "skill" : item.commandKind;
        ctx.lastTarget = String(singleIds[0]);
        const focusSkill =
          kind === "skill" && combat.focusSkillKey
            ? combat.skillByKey[combat.focusSkillKey]
            : null;
        const display = focusSkill
          ? ctx.castSubmitDisplay(focusSkill, item.payload, item.commandDisplay)
          : item.commandDisplay || null;
        const command = { kind: kind, payload: item.payload };
        if (ctx.askCrossSide(kind, "single", item.key, command, display)) {
          return;
        }
        ctx.submitCombatCommand(command, display);
        ctx.publishView();
        return;
      }
      // The NONE and SELF confirms (no target field): the same cross-side
      // check before the guarded command submission. The stale focused skill
      // is never used to label an item's submission: the row's own kind
      // selects whether a skill descriptor takes part in the display.
      if (item.key === "none-confirm" || item.key === "self-confirm") {
        const kind = item.commandKind === undefined ? "skill" : item.commandKind;
        const focusSkill =
          kind === "skill" && combat.focusSkillKey
            ? combat.skillByKey[combat.focusSkillKey]
            : null;
        const inner = item.payload || {};
        const command = { kind: kind, payload: inner };
        const display = focusSkill
          ? ctx.castSubmitDisplay(focusSkill, inner, item.commandDisplay)
          : item.commandDisplay || null;
        if (ctx.askCrossSide(kind, item.key === "self-confirm" ? "self" : "none", item.key, command, display)) {
          return;
        }
        ctx.submitCombatCommand(command, display);
        return;
      }
      // Any remaining guarded party command row (a producer missed above):
      // wrap the inner payload once at this single submit boundary.
      if (item.actionId === "combat.command") {
        ctx.submitCombatCommand(
          { kind: item.commandKind === undefined ? "skill" : item.commandKind, payload: item.payload || {} },
          item.commandDisplay || null
        );
        return;
      }
      // Real OOB action items (flee / forfeit; items and tactics belong to
      // webclient-party-items-tactics, exit confirmation to
      // webclient-party-exit-confirmation).
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
      // frame already popped by the settle is not double-handled).
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

  // ---- The cross-side question (webclient-combat-cross-side-confirm D2) ----
  // null, or the cast held back at submission: `{ envelope, display, question,
  // sides, subjectKind, subjectKey, form, frameSource, focusKey, actorId,
  // sessionId, roundRevision, draftVersion }`. The subject is a skill or an
  // item (webclient-party-items-tactics); a basic action has no polar fact and
  // never opens the question. Nothing is sent while it is set; 是 sends the
  // stored envelope verbatim (webclient-party-command-selection: the guarded
  // command envelope, bound to the commanded actor and the committed versions,
  // is the held unit).
  ctx.crossSideConfirm = null;

  function committedCombat(rs) {
    const panel = rs && rs.panels && rs.panels.context_actions;
    return panel && panel.kind === "combat" ? panel : null;
  }

  // Called at each target-step submission with the payload exactly as it
  // would be sent. Returns true when the cast is held for the question.
  // The predicate over the committed state for one held (or about to be
  // held) payload: null, or `{ sides, question }`. `kind` is the submitted
  // command's kind (`skill`, `item` or `tactic`); the facts, candidates and
  // label come from that kind's committed descriptor.
  function evaluateCrossSide(rs, kind, form, payload) {
    const panel = committedCombat(rs);
    const key = subjectKeyOf(kind, payload);
    if (!panel || key === null) {
      return null;
    }
    const facts = factsFor(panel, kind, key);
    const raw = committedSubject(panel, kind, key);
    const participants = Array.isArray(panel.participants) ? panel.participants : [];
    // The commanded actor, never the controlled portrait
    // (webclient-party-command-selection): a companion's SELF reach and cross
    // side are the companion's own.
    const actor = commandedActorId(panel);
    const targets = targetSetFor({
      form,
      payload,
      candidates: raw && Array.isArray(raw.targets) ? raw.targets : [],
      participants,
      actorIdentity: actor,
    });
    const outcome = crossSide(facts, targets, participants, actor);
    return outcome ? { sides: outcome.sides, question: crossSideQuestion(outcome.sides, facts.label) } : null;
  }

  // The subject key one command kind carries on the wire (`skill_key`,
  // `item_key`, or a basic action's `key`), or null.
  function subjectKeyOf(kind, payload) {
    const body = payload || {};
    if (kind === "item") return typeof body.item_key === "string" ? body.item_key : null;
    if (kind === "tactic") return typeof body.key === "string" ? body.key : null;
    return typeof body.skill_key === "string" ? body.skill_key : null;
  }

  // `kind` is the submitted command's kind and `command` the closed
  // `{kind, payload}` union member. The held unit is the fully built
  // envelope, so 是 sends exactly the versions and actor the question was
  // worded for.
  ctx.askCrossSide = function askCrossSide(kind, form, focusKey, command, display) {
    const rs = ctx.reducer.getState();
    const panel = committedCombat(rs);
    const payload = command ? command.payload : null;
    const key = subjectKeyOf(kind, payload);
    if (!panel || !ctx.frameResolver.combatModel() || key === null) {
      return false;
    }
    const envelope = CombatMenu.commandEnvelope(panel, command);
    if (!envelope) {
      return false;
    }
    const outcome = evaluateCrossSide(rs, kind, form, payload);
    if (!outcome) {
      return false;
    }
    const descriptor = router.depth() > 0 ? router.currentDescriptor() : null;
    ctx.crossSideConfirm = {
      envelope,
      display,
      question: outcome.question,
      sides: outcome.sides,
      subjectKind: kind,
      subjectKey: key,
      form,
      frameSource: descriptor ? descriptor.source : null,
      focusKey,
      actorId: envelope.actor_id,
      sessionId: envelope.session_id,
      roundRevision: envelope.round_revision,
      draftVersion: envelope.draft_version,
    };
    ctx.publishView();
    return true;
  };

  // 是: send the held cast through the single dispatch entry (its in-flight
  // lock and echo). A lock keeps the question open and sends nothing.
  ctx.confirmCrossSide = function confirmCrossSide() {
    const pending = ctx.crossSideConfirm;
    if (!pending) {
      return null;
    }
    if (router.isMutationInFlight() || router.isAwaitingRevision()) {
      return null;
    }
    // The same submission helper the direct path uses, so 是 also records the
    // one-shot advance correlation for its own accepted nonfinal save.
    const requestId = ctx.submitCombatEnvelope(pending.envelope, pending.display);
    if (requestId === null || requestId === undefined) {
      return null;
    }
    ctx.crossSideConfirm = null;
    ctx.dockFocusRequest += 1;
    ctx.publishView();
    return requestId;
  };

  // 否 / ✕ / Escape: back to the target step with the same focused position;
  // the AREA selection lives in the model and is untouched. Nothing was
  // sent, so the router's held-Enter guard for that row is released.
  ctx.cancelCrossSide = function cancelCrossSide() {
    const pending = ctx.crossSideConfirm;
    if (!pending) {
      return false;
    }
    ctx.crossSideConfirm = null;
    if (router.depth() > 0 && pending.focusKey) {
      router.focusItemByKey(pending.focusKey);
    }
    router.clearRepeatGuard();
    ctx.dockFocusRequest += 1;
    ctx.publishView();
    return true;
  };

  // The commit-time invalidation (run in every publish after the frame
  // stack settles): a mode other than combat, a playing round, or a
  // committed panel that no longer backs the held cast (the skill gone or
  // disabled, a chosen target or the shorthand no longer a candidate, the
  // target frame gone) closes the question without sending. An unrelated
  // replacement keeps it.
  ctx.settleCrossSide = function settleCrossSide(rs) {
    const pending = ctx.crossSideConfirm;
    if (!pending) {
      return;
    }
    const drop = (focusDock) => {
      ctx.crossSideConfirm = null;
      if (focusDock) {
        ctx.dockFocusRequest += 1;
      }
    };
    if (rs.mode !== "combat") {
      // The shell's own mode-change focus path takes the new mode's home.
      drop(false);
      return;
    }
    const panel = committedCombat(rs);
    if (!panel || ctx.beatLocked()) {
      drop(true);
      return;
    }
    // The held envelope is bound to the commanded actor and the committed
    // versions (webclient-party-command-selection): a switch of the actor, the
    // session, the round revision or the draft version cancels it without
    // sending. Nothing is silently re-versioned.
    if (
      String(commandedActorId(panel)) !== String(pending.actorId) ||
      !panel.session ||
      panel.session.session_id !== pending.sessionId ||
      panel.session.round_revision !== pending.roundRevision ||
      !panel.draft ||
      panel.draft.draft_version !== pending.draftVersion
    ) {
      drop(true);
      return;
    }
    const raw = committedSubject(panel, pending.subjectKind, pending.subjectKey);
    if (!raw || !raw.enabled) {
      drop(true);
      return;
    }
    const candidates = new Set((raw.targets || []).map(String));
    const payload = (pending.envelope && pending.envelope.command && pending.envelope.command.payload) || {};
    const ids = Array.isArray(payload.target_ids)
      ? payload.target_ids.map(String)
      : payload.target_id === undefined || payload.target_id === null
        ? []
        : [String(payload.target_id)];
    if (ids.some((id) => !candidates.has(id))) {
      drop(true);
      return;
    }
    if (typeof payload.target_shorthand === "string" && !(raw.shorthands || []).includes(payload.target_shorthand)) {
      drop(true);
      return;
    }
    const descriptor = router.depth() > 0 ? router.currentDescriptor() : null;
    const params = (descriptor && descriptor.params) || {};
    // The frame's own subject parameter: a skill frame names `skillKey`, an
    // item frame `itemKey`, a basic-action frame `key`.
    const frameKey =
      params.skillKey !== undefined
        ? params.skillKey
        : params.itemKey !== undefined
          ? params.itemKey
          : params.key;
    if (!descriptor || descriptor.source !== pending.frameSource || frameKey !== pending.subjectKey) {
      drop(true);
      return;
    }
    // The question re-reads the committed facts, teams and label: a cast
    // that no longer crosses sides needs no question, and one that crosses
    // differently is worded for what 是 would now send.
    const outcome = evaluateCrossSide(rs, pending.subjectKind, pending.form, payload);
    if (!outcome) {
      drop(true);
      return;
    }
    pending.sides = outcome.sides;
    pending.question = outcome.question;
  };

  // ---- The commanded-actor transition (webclient-party-command-selection) --
  //
  // Runs in the settle window, before the view is built, and never
  // dispatches: it consumes a completed read-only choices query and, on any
  // committed actor/session change, drops the unconfirmed client-local
  // selection and the held warning. Confirmed server draft entries are never
  // touched here — they are the server's.
  ctx.settleCombatActorSelection = function settleCombatActorSelection(rs) {
    if (ctx.inStackMutation) {
      // A router mutation already owns this window; the outer publish's own
      // settle pass re-enters and handles the transition there.
      return;
    }
    const panel = committedCombat(rs);
    const actorId = commandedActorId(panel);
    const pending = ctx.pendingActorSelection;
    if (pending) {
      const settled =
        !!panel &&
        !!panel.choices &&
        String(actorId) === String(pending.actorId) &&
        rs.generation === pending.generation &&
        panel.session &&
        panel.session.session_id === pending.sessionId;
      if (settled) {
        ctx.pendingActorSelection = null;
        ctx.frameResolver.resetCombatSelection();
        // Return to exactly one root, whatever frame the query was issued
        // from: an EXPLICIT switch starts in the actor frame, while the
        // automatic advance starts in the submitted skill/target frame of the
        // PREVIOUS actor. Keeping that frame would leave the new actor in a
        // stale skill/scale/target step (the resolver still mounts it when
        // both actors own the skill), so the plan never carries over.
        if (router.depth() > 0) {
          ctx.resetFramesToRoot();
          ctx.dockFocusRequest += 1;
        }
      } else if (!ctx.inFlight) {
        // Refused, rejected or superseded: drop the local intent.
        ctx.pendingActorSelection = null;
      }
    }
    // The committed combat identity: a change (an actor switch, a reconnect
    // fallback, a restored default) drops every unconfirmed local selection.
    const sessionId = panel && panel.session ? panel.session.session_id : null;
    // The transport generation is part of the identity: a reconnect rebuilds
    // the committed entries but never restores an unconfirmed local selection.
    const identity = panel
      ? String(rs.generation) + ":" + String(sessionId) + ":" + String(actorId)
      : null;
    if (identity !== ctx.lastCombatIdentity) {
      ctx.frameResolver.resetCombatSelection();
      ctx.crossSideConfirm = null;
      ctx.pendingCombatAdvance = null;
      ctx.lastCombatIdentity = identity;
    }
  };

  // The one-shot advance after this client's own nonfinal draft save: query
  // the first required member still needing a command, once, read-only. It
  // runs after the view publication so the query's outer envelope carries the
  // freshly committed epoch/revision, and it is driven solely by this
  // client's own dispatch correlation — a restored or re-observed result, a
  // reconnect or a typed round never schedules navigation.
  ctx.autoAdvanceCombatActor = function autoAdvanceCombatActor(rs) {
    const record = ctx.pendingCombatAdvance;
    if (!record || ctx.inFlight || ctx.beatLocked() || ctx.crossSideConfirm) {
      return;
    }
    const panel = committedCombat(rs);
    if (!panel || !panel.session || !panel.draft || !panel.choices) {
      ctx.pendingCombatAdvance = null;
      return;
    }
    if (rs.mode !== "combat" || rs.generation !== record.generation || panel.session.session_id !== record.sessionId) {
      ctx.pendingCombatAdvance = null;
      return;
    }
    const result = rs.lastActionResult;
    if (!result || result.requestId !== record.requestId) {
      return;
    }
    ctx.pendingCombatAdvance = null;
    if (result.code !== "draft_saved") {
      // A terminal round, a needs-selection preflight, a stale command or a
      // rejection: never advance, never replay.
      return;
    }
    const needs = new Set((panel.draft.needs_selection_ids || []).map(String));
    const commandable = new Set(
      (panel.actors || []).filter((actor) => actor.commandable).map((actor) => String(actor.identity))
    );
    const next = (panel.draft.required_actor_ids || []).find(
      (id) =>
        needs.has(String(id)) &&
        commandable.has(String(id)) &&
        String(id) !== String(commandedActorId(panel))
    );
    if (next === undefined) {
      return;
    }
    if (ctx.requestCombatActor(next)) {
      ctx.publishView();
    }
  };
}
