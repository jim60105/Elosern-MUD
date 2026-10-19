// The skill-use group of the composed Elosern store
// (skillbook-authoritative-casting D6/D7, webclient-party-skill-tab): the
// party window 技能 tab's 施放 entry for the viewed member, the hand-over of
// casting to the single dock router once the authoritative preview commits
// (the window closes first), the dock-side skill-use interactions, the
// return to the tab on Escape, and the lifecycle that clears a flow the
// committed state no longer supports.
//
// The tab never hosts a router frame and the store never decides
// availability: the committed `skill_use` panel (resolved through the frame
// registry) is the only source of rows, payloads, and reasons.

import SkillUseMenu from "../../lib/skill_use_menu.js";
import { partyWindowTab } from "../../components/party-window-memory.js";

const SKILL_USE_SOURCES = new Set(["skilluse.root", "skilluse.scale", "skilluse.opening"]);

export function isSkillUseSource(descriptor) {
  return !!descriptor && SKILL_USE_SOURCES.has(descriptor.source);
}

export function applySkillUse(ctx) {
  // null | { phase: "pending" | "active", skillKey, requestId, epoch, generation }
  ctx.skillUse = null;
  // Set by the router's own Escape pop while the flow is active, consumed by
  // the next settle: an Escape out of the flow returns to the 技能 tab; a
  // settle-driven pop (cast committed, mode changed) does not.
  ctx.skillUseEscaped = false;
  // Monotonic DOM-focus requests the shell honours after the drawer unmounts.
  ctx.dockFocusRequest = 0;
  // `{ actorId, skillKey, seq }` — the 技能 tab reopens focused on this
  // member's row's 施放.
  ctx.bookReturn = null;
  ctx.bookReturnSeq = 0;
  // The last refused entry (`{ actorId, skillKey, message }`), shown in the tab.
  ctx.skillUseNotice = null;

  // True while the party window is open on its 技能 tab: the only surface a
  // preview may hand over from.
  function skillTabOpen() {
    return ctx.hudDrawer.value === "party" && partyWindowTab() === "skills";
  }

  function currentDescriptor() {
    return ctx.router.depth() > 0 ? ctx.router.currentDescriptor() : null;
  }

  // The caster the tab's skills belong to: the committed `character` panel's
  // `member_id` (the viewed party member). The `status` panel is deliberately
  // not consulted — it names the controlled figure, which may differ from the
  // member whose skills the tab lists. Null when the character panel is
  // missing or unavailable; the tab then refuses locally instead of naming an
  // invented caster or falling back to the commander.
  function controlledActorId(rs) {
    const character = rs.panels && rs.panels.character;
    if (!character || character.available !== true) {
      return null;
    }
    const value = character.member_id;
    return Number.isSafeInteger(value) && value > 0 ? value : null;
  }

  // The tab's 施放 entry. Exploration: request the authoritative preview
  // for the viewed member (nothing else is sent until the player confirms in
  // the dock). Any other mode, combat included, refuses locally and sends
  // nothing: the tab disables 施放 in combat, where casting stays on the
  // command card.
  ctx.beginSkillUse = function beginSkillUse(skillKey) {
    const rs = ctx.reducer.getState();
    const contextActions = (rs.panels && rs.panels.context_actions) || null;
    if (
      (contextActions && contextActions.kind === "combat") ||
      rs.mode !== "exploration" ||
      typeof skillKey !== "string" ||
      skillKey === ""
    ) {
      return { route: "refused" };
    }
    ctx.skillUseNotice = null;
    const actorId = controlledActorId(rs);
    if (actorId === null) {
      return { route: "refused" };
    }
    const requestId = ctx.dispatchAction(
      SkillUseMenu.PREVIEW_ACTION,
      { actor_id: actorId, skill_key: skillKey },
      null,
    );
    if (requestId === null) {
      return { route: "refused" };
    }
    ctx.skillUse = {
      phase: "pending",
      actorId,
      skillKey,
      requestId,
      epoch: rs.activeEpoch,
      generation: rs.generation,
    };
    ctx.publishView();
    return { route: "preview", requestId };
  };

  // True while the hand-over itself runs: the drawer close and the frame
  // push publish synchronously, and those nested commits must not judge a
  // half-entered flow.
  let entering = false;

  function enterDock(flow) {
    entering = true;
    try {
      // The window closes BEFORE the dock frame mounts (the drawer's own
      // close teardown may re-home the exploration root first).
      ctx.closeHudDrawer();
      ctx.pushFrame(
        { source: "skilluse.root", params: { skillKey: flow.skillKey, actorId: flow.actorId } },
        null,
      );
      flow.phase = "active";
      ctx.skillUseEscaped = false;
      ctx.dockFocusRequest += 1;
    } finally {
      entering = false;
    }
  }

  // The commit hook (publishView, after the frame-stack settle).
  ctx.syncSkillUse = function syncSkillUse(prev, rs) {
    const flow = ctx.skillUse;
    if (entering) {
      return;
    }
    if (!flow) {
      ctx.skillUseEscaped = false;
      return;
    }
    // A new transport generation or presentation epoch retires the flow;
    // nothing is resubmitted (the reconnect adopts canonical state only).
    if (rs.generation !== flow.generation || rs.activeEpoch !== flow.epoch) {
      ctx.skillUse = null;
      return;
    }
    if (flow.phase === "pending") {
      if (ctx.inFlight && ctx.inFlight.requestId === flow.requestId) {
        return; // the preview result or its revision is not adopted yet
      }
      const result = rs.lastActionResult;
      if (!result || result.requestId !== flow.requestId) {
        return;
      }
      const preview = (rs.panels && rs.panels.skill_use) || null;
      const ready =
        result.outcome === "success" &&
        preview &&
        preview.available === true &&
        preview.actor_id === flow.actorId &&
        preview.skill.key === flow.skillKey &&
        rs.mode === "exploration";
      if (!ready) {
        ctx.skillUseNotice = {
          actorId: flow.actorId,
          skillKey: flow.skillKey,
          message:
            typeof result.message === "string" && result.message.trim() !== ""
              ? result.message
              : "目前無法施放這項技能。",
        };
        ctx.skillUse = null;
        return;
      }
      if (!skillTabOpen()) {
        // The player closed the window, or left its 技能 tab, while the
        // preview was in flight: the flow ends without taking over the dock.
        ctx.skillUse = null;
        return;
      }
      enterDock(flow);
      return;
    }
    // Active: the flow lives while one of its frames is current AND the
    // committed preview still names the same caster and skill. A replacement
    // preview for another caster retires the flow instead of silently
    // re-binding the open confirmation to that actor.
    if (isSkillUseSource(currentDescriptor())) {
      const preview = (rs.panels && rs.panels.skill_use) || null;
      const stillCurrent =
        preview &&
        preview.available === true &&
        preview.actor_id === flow.actorId &&
        preview.skill.key === flow.skillKey;
      if (!stillCurrent) {
        ctx.skillUse = null;
        return;
      }
      ctx.skillUseEscaped = false;
      return;
    }
    const escaped = ctx.skillUseEscaped;
    ctx.skillUseEscaped = false;
    ctx.skillUse = null;
    if (escaped && rs.mode === "exploration" && ctx.hudDrawer.value === null) {
      ctx.bookReturnSeq += 1;
      ctx.bookReturn = { actorId: flow.actorId, skillKey: flow.skillKey, seq: ctx.bookReturnSeq };
      // The retired drawer name opens the party window on 技能 (hud.js).
      ctx.openHudDrawer("skill");
    }
  };

  // The router's Escape pop (menu-closed) out of the flow's root frame.
  ctx.noteSkillUseEscape = function noteSkillUseEscape() {
    if (ctx.skillUse && ctx.skillUse.phase === "active" && !isSkillUseSource(currentDescriptor())) {
      ctx.skillUseEscaped = true;
    }
  };

  // Dock-side activations of the flow's local rows. Returns true when the
  // item belonged to the flow (handled or deliberately ignored).
  ctx.handleSkillUseItem = function handleSkillUseItem(name, item) {
    const descriptor = currentDescriptor();
    if (!isSkillUseSource(descriptor)) {
      return false;
    }
    const skillKey = descriptor.params && descriptor.params.skillKey;
    const actorId = descriptor.params && descriptor.params.actorId;
    const model = ctx.frameResolver.skillUseModel(skillKey, actorId);
    if (!model) {
      return true;
    }
    if (item.actionId === "toggle-skilluse-target") {
      if (item.payload) {
        SkillUseMenu.toggle(model, item.payload.identity);
      }
      ctx.publishView();
      return true;
    }
    if (name === "space") {
      return true;
    }
    if (item.actionId === "open-skilluse-scale") {
      ctx.pushFrame(
        { source: "skilluse.scale", params: { skillKey, actorId } },
        item.key,
      );
      ctx.publishView();
      return true;
    }
    if (item.actionId === "choose-skilluse-scale" && item.payload) {
      // A rung asks the server for a fresh preview; the use frame's confirms
      // stay locked by the router until that revision is adopted.
      if (item.payload.scale !== model.panel.scale) {
        const request = ctx.dispatchAction(
          SkillUseMenu.PREVIEW_ACTION,
          {
            actor_id: model.panel.actor_id,
            skill_key: skillKey,
            scale: item.payload.scale,
          },
          null,
        );
        if (request === null) {
          // Refused locally (another request is in flight): stay on the
          // rungs so the shown scale never disagrees with the request.
          ctx.pushToast({ title: "目前無法變更威力，請稍後再試。", tone: "info" });
          ctx.publishView();
          return true;
        }
      }
      ctx.inStackMutation = true;
      try {
        ctx.router.popMenu();
      } finally {
        ctx.inStackMutation = false;
      }
      ctx.publishView();
      return true;
    }
    if (item.actionId === "open-skilluse-opening" && item.payload) {
      ctx.pushFrame(
        {
          source: "skilluse.opening",
          params: { skillKey, actorId, identity: item.payload.identity },
        },
        item.key,
      );
      ctx.publishView();
      return true;
    }
    if (item.key === "cancel-opening") {
      ctx.inStackMutation = true;
      try {
        ctx.router.popMenu();
      } finally {
        ctx.inStackMutation = false;
      }
      ctx.publishView();
      return true;
    }
    if (item.actionId === SkillUseMenu.CAST_ACTION) {
      const payload = item.confirm ? SkillUseMenu.areaPayload(model) : item.payload;
      if (payload) {
        ctx.dispatchAction(SkillUseMenu.CAST_ACTION, payload, item.commandDisplay || null);
      }
      return true;
    }
    return true;
  };

  // The dock detail pane's committed model for the current flow frame.
  ctx.skillUseView = function skillUseView(rs, currentItem) {
    const descriptor = currentDescriptor();
    if (!isSkillUseSource(descriptor)) {
      return null;
    }
    const model = ctx.frameResolver.skillUseModel(
      descriptor.params && descriptor.params.skillKey,
      descriptor.params && descriptor.params.actorId,
    );
    if (!model) {
      return null;
    }
    const panel = model.panel;
    const skill = panel.skill;
    const openingNames = {};
    skill.openings.forEach((row) => {
      openingNames[row.identity] = row.label;
    });
    let focused = null;
    if (currentItem) {
      const reason = currentItem.disabledReason || null;
      const lineUp = Array.isArray(currentItem.lineUp)
        ? currentItem.lineUp
        : typeof currentItem.key === "string" && currentItem.key.startsWith("opening-")
          ? (skill.openings.find((row) => `opening-${row.identity}` === currentItem.key) || {}).target_ids || []
          : [];
      focused = {
        key: currentItem.key,
        kind: currentItem.kind || null,
        reason: reason ? reason.message : null,
        lineUpCount: lineUp.length,
      };
    }
    return {
      skillKey: skill.key,
      label: skill.label,
      description: skill.description,
      targetSpec: skill.target_spec,
      costText: SkillUseMenu.costText(skill.cost),
      scale: panel.scale,
      scaled: Array.isArray(skill.freeform_scales) && skill.freeform_scales.length > 0,
      enabled: skill.enabled,
      reason: skill.disabled_reason ? skill.disabled_reason.message : null,
      selected: model.selected.slice(),
      focused,
    };
  };
}
