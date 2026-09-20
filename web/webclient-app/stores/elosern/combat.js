// The combat + echo-display group of the composed Elosern store: the
// CombatMenu keyboard/pointer steps and the CommandEcho descriptor fill
// (complete-ui-command-echo D3, webclient-input-narrative).

import CombatMenu from "../../lib/combat_menu.js";

export function applyCombat(ctx) {
  // Open one skill's target (or 威力 scale) menu from the root/skills menu,
  // mirroring the legacy plugin's `openCombatSkill`. The frame carries only
  // the skill key; the resolver opens the skill through the shared model.
  ctx.openCombatSkill = function openCombatSkill(skillKey) {
    const combat = ctx.frameResolver.combatModel();
    if (!combat) {
      return;
    }
    combat.focusSkillKey = skillKey;
    const menu = CombatMenu.openSkill(combat, skillKey);
    if (menu) {
      ctx.pushFrame({ source: "combat.skill", params: { skillKey } }, skillKey);
      if (menu.items.length > 0 && menu.items[0].scaleChoice) {
        // The freeform scale step preselects 威力×1 (the default behavior).
        ctx.router.focusItemByKey("scale-1");
      }
    }
    ctx.publishView();
  };

  // The participant display names (server-authored committed combat panel
  // rows) for one payload-ordered identity list; `null` when any identity has
  // no committed row, so a partial target list is never echoed as complete
  // (D3b).
  function participantNamesByIdentity(identities) {
    const rs = ctx.reducer.getState();
    const panel = (rs.panels && rs.panels.context_actions) || {};
    const byId = new Map();
    if (panel.kind !== "combat") {
      return null;
    }
    (Array.isArray(panel.participants) ? panel.participants : []).forEach((p) => {
      if (p && typeof p.display_name === "string" && p.display_name !== "") {
        byId.set(String(p.identity), p.display_name);
      }
    });
    const names = [];
    for (const identity of identities) {
      const name = byId.get(String(identity));
      if (!name) {
        return null;
      }
      names.push(name);
    }
    return names;
  }

  // The echo descriptor for one combat.cast submit (D3): the row descriptor
  // plus the chosen NON-DEFAULT freeform magnitude label and — for payloads
  // with explicit selected targets — the payload-ordered target labels
  // (D3b). Display-only: the payload is never touched here.
  ctx.castSubmitDisplay = function castSubmitDisplay(skill, payload, baseDisplay) {
    const display = Object.assign({}, baseDisplay || {});
    if (!display.skillLabel && typeof skill.label === "string" && skill.label !== "") {
      display.skillLabel = skill.label;
    }
    if (
      display.scaleLabel === undefined &&
      Array.isArray(skill.freeformScales) &&
      skill.freeformScales.length > 0 &&
      skill.scale !== 1
    ) {
      const scaleLabel = CombatMenu.scaleLabelFor(skill);
      if (scaleLabel !== null) {
        display.scaleLabel = scaleLabel;
      }
    }
    if (
      display.targetLabel === undefined &&
      display.targetLabels === undefined &&
      Array.isArray(payload.target_ids) &&
      payload.target_ids.length > 0 &&
      !payload.target_shorthand
    ) {
      const names = participantNamesByIdentity(payload.target_ids);
      if (names !== null) {
        display.targetLabels = names;
      }
    }
    return display;
  };

  // One committed exploration interact target's server-authored display name
  // by identity, or null (the freeform-talk lookup, factored out).
  function explorationTargetName(identity) {
    if (identity === undefined || identity === null) {
      return null;
    }
    const rs = ctx.reducer.getState();
    const panel = (rs.panels && rs.panels.exploration) || {};
    for (const target of panel.interact || []) {
      if (String(target.identity) === String(identity)) {
        return typeof target.display_name === "string" && target.display_name !== ""
          ? target.display_name
          : null;
      }
    }
    return null;
  }

  // The committed combat-form `context_actions` panel's skill label for one
  // skill key (the v3 nested categories -> groups -> skills shape flattened),
  // or null.
  function combatSkillLabel(skillKey) {
    if (typeof skillKey !== "string" || skillKey === "") {
      return null;
    }
    const rs = ctx.reducer.getState();
    const panel = (rs.panels && rs.panels.context_actions) || {};
    if (panel.kind !== "combat") {
      return null;
    }
    for (const category of panel.skills || []) {
      for (const group of category.groups || []) {
        for (const skill of group.skills || []) {
          if (skill && skill.key === skillKey) {
            return typeof skill.label === "string" && skill.label !== ""
              ? skill.label
              : null;
          }
        }
      }
    }
    return null;
  }

  // The central descriptor fill (complete-ui-command-echo D3, intent
  // surfaces): component intents carry only {action_id, payload}, so missing
  // echo labels are read VERBATIM from committed store state at dispatch time
  // (the freeform-talk branch generalized). The fill never overwrites an
  // explicitly provided field, never composes or invents a label, and feeds
  // only the catalog call — the `ui_action` envelope is untouched. Absent
  // state leaves the field absent (catalog silence, audited by the
  // per-surface table).
  ctx.fillDisplayFor = function fillDisplayFor(actionId, payload, display) {
    const base = display || null;
    const filled = Object.assign({}, base || {});
    // Declared-field semantics: an empty array counts as ABSENT (a caller
    // handing over `targetLabels: []` has no labels, and committed state may
    // supply them); any other present value — including falsy strings — is
    // never overwritten.
    const has = (field) => {
      const value = base && base[field];
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      return value !== undefined && value !== null && value !== "";
    };
    const panels = (ctx.reducer.getState().panels) || {};
    if (actionId === "shop.buy" || actionId === "shop.sell") {
      if (!has("itemLabel")) {
        const shop = (panels.services && panels.services.shop) || {};
        const rows =
          (actionId === "shop.buy" ? shop.stock : shop.sellable) || [];
        for (const row of rows) {
          if (
            row &&
            row.item_key === payload.item_key &&
            typeof row.display_name === "string" &&
            row.display_name !== ""
          ) {
            filled.itemLabel = row.display_name;
            break;
          }
        }
      }
    } else if (
      actionId === "explore.talk_scripted" ||
      actionId === "explore.talk_freeform" ||
      actionId === "explore.party_invite" ||
      actionId === "explore.party_leave" ||
      actionId === "explore.possess"
    ) {
      if (!has("npcLabel")) {
        const name = explorationTargetName(payload.npc_id);
        if (name !== null) {
          filled.npcLabel = name;
        }
      }
    } else if (actionId === "explore.engage" || actionId === "explore.look") {
      if (!has("targetLabel")) {
        // `explore.engage` carries `monster_id`; `explore.look` carries
        // `target_id` (both are interact-target identities in the committed
        // exploration panel).
        const identity =
          actionId === "explore.engage" ? payload.monster_id : payload.target_id;
        const name = explorationTargetName(identity);
        if (name !== null) {
          filled.targetLabel = name;
        }
      }
    } else if (actionId === "combat.cast") {
      if (!has("skillLabel")) {
        const label = combatSkillLabel(payload.skill_key);
        if (label !== null) {
          filled.skillLabel = label;
        }
      }
      if (
        !has("targetLabel") &&
        !has("targetLabels") &&
        Array.isArray(payload.target_ids) &&
        payload.target_ids.length > 0 &&
        !payload.target_shorthand
      ) {
        const names = participantNamesByIdentity(payload.target_ids);
        if (names !== null) {
          filled.targetLabels = names;
        }
      }
    } else if (actionId === "creation.activate" || actionId === "creation.reset") {
      // The creation overlay's confirm intent emits only {action_id, payload}
      // — the descriptor rides the confirmation item resolved from the
      // current confirm descriptor at echo time (no stored confirm copy).
      let confirmItem = null;
      if (ctx.creation && ctx.creation.view === "confirm" && ctx.creation.confirmDescriptor) {
        const menu = ctx.frameResolver.resolve(ctx.creation.confirmDescriptor);
        if (menu && !menu.unresolvable && Array.isArray(menu.items) && menu.items.length > 0) {
          confirmItem = menu.items[0];
        }
      }
      const carried = confirmItem && confirmItem.commandDisplay;
      if (carried) {
        for (const field of Object.keys(carried)) {
          if (!has(field)) {
            filled[field] = carried[field];
          }
        }
      }
    }
    return filled;
  };

  // H3 (task 6.6): the 威力 scale step and the AREA shorthand step — the
  // pointer path mirrors the keyboard `choose-scale` / `choose-shorthand`
  // dispatch (the store is the single writer).
  ctx.chooseScale = function chooseScale(scale) {
    const combat = ctx.frameResolver.combatModel();
    if (combat && combat.focusSkillKey && CombatMenu.chooseScale(combat, combat.focusSkillKey, scale)) {
      // The pointer path mirrors the keyboard step: the target frame is the
      // declarative `{skillKey}` descriptor; content resolves at access.
      ctx.pushFrame({ source: "combat.target", params: { skillKey: combat.focusSkillKey } }, null);
      ctx.publishView();
    }
  };

  ctx.chooseShorthand = function chooseShorthand(shorthand) {
    const combat = ctx.frameResolver.combatModel();
    if (combat && combat.focusSkillKey) {
      CombatMenu.chooseShorthand(combat, combat.focusSkillKey, shorthand);
      ctx.publishView();
    }
  };
}
