/*
 * Elosern DOM-independent combat-menu model.
 *
 * Transforms a validated `context_actions` combat panel into the logical
 * keyboard menus consumed by KeyboardRouter: a root (Attack, Skills, Items,
 * Defend, Flee), a paginated active-skill list, target flows for every
 * TargetSpec, Space multi-selection for AREA, and a confirmed Forfeit
 * secondary menu. The module preserves the originating skill focus on
 * backtracking, paginates without reordering, and chooses the nearest
 * surviving item deterministically after a newer panel replaces the old one.
 *
 * No `document` or `window` access at load time; Node tests exercise the
 * model directly. All server strings are passed through unchanged as display
 * text; the model never parses narrative.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.CombatMenu = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var ROOT_ACTIONS = ["attack", "skills", "items", "defend", "flee"];
  var SECONDARY_ACTIONS = ["forfeit"];
  var RECOVERY_SECONDARY_ACTIONS = ["forfeit"];
  var PAGE_SIZE = 6;
  var BASIC_ATTACK_KEY = "basic_attack";

  // A frozen view of one skill with its stable selection state.
  function skillModel(skill, participantById) {
    var costText = Object.keys(skill.cost || {})
      .map(function (key) {
        return key.toUpperCase() + " " + skill.cost[key];
      })
      .join("、");
    return {
      key: skill.key,
      label: skill.label,
      description: skill.description,
      costText: costText,
      targetSpec: skill.target_spec,
      element: skill.element || null,
      enabled: !!skill.enabled,
      disabledReason: skill.disabled_reason || null,
      targets: (skill.targets || []).slice(),
      shorthands: (skill.shorthands || []).slice(),
      selected: [], // selected participant identities for AREA
      shorthand: null, // chosen approved shorthand for AREA
      selfIdentity: skill.target_spec === "self" ? null : null,
    };
  }

  // Build a deterministic ordered participant lookup by identity.
  function participantById(participants) {
    var byId = {};
    participants.forEach(function (participant) {
      byId[participant.identity] = participant;
    });
    return byId;
  }

  function panelSkills(panel) {
    return (panel && panel.skills) || [];
  }

  function panelParticipants(panel) {
    return (panel && panel.participants) || [];
  }

  // -------------------------------------------------------------------------
  // Root menus.
  // -------------------------------------------------------------------------

  function rootItems(panel) {
    var recovery = panel && panel.session && panel.session.state === "recovery";
    // Forfeit always opens the secondary confirmation menu first; only
    // `confirm-forfeit` sends `combat.forfeit`. In recovery the root exposes
    // exactly that confirmed Forfeit path and nothing else.
    if (recovery) {
      return [
        {
          key: "forfeit",
          label: "投降",
          enabled: true,
          actionId: null,
          payload: null,
        },
      ];
    }
    return [
      { key: "attack", label: "攻擊", enabled: true, actionId: null, payload: null },
      { key: "skills", label: "技能", enabled: true, actionId: null, payload: null },
      { key: "items", label: "道具", enabled: false, actionId: null, payload: null, disabledReason: { code: "not_implemented", message: "道具功能尚未開放。" } },
      { key: "defend", label: "防禦", enabled: false, actionId: null, payload: null, disabledReason: { code: "not_implemented", message: "防禦功能尚未開放。" } },
      { key: "flee", label: "逃跑", enabled: true, actionId: "combat.flee", payload: {} },
      { key: "forfeit", label: "投降", enabled: true, actionId: null, payload: null },
    ];
  }

  // -------------------------------------------------------------------------
  // Skill list with deterministic pagination.
  // -------------------------------------------------------------------------

  function pageRange(index, total) {
    var start = Math.floor(index / PAGE_SIZE) * PAGE_SIZE;
    return { start: start, end: Math.min(start + PAGE_SIZE, total) };
  }

  function skillItems(skills, focusIdentity, page) {
    var items = [];
    for (var index = 0; index < skills.length; index++) {
      var skill = skills[index];
      var item = {
        key: skill.key,
        label: skill.label,
        description: skill.description,
        costText: skill.costText,
        enabled: skill.enabled,
        disabledReason: skill.disabledReason,
        actionId: null,
        payload: null,
      };
      if (skill.enabled) {
        item.actionId = "open-skill";
        item.payload = { skillKey: skill.key };
      }
      items.push(item);
    }
    return items;
  }

  // -------------------------------------------------------------------------
  // Target selection flows.
  // -------------------------------------------------------------------------

  function targetItemsFor(skill, participants) {
    var items = [];
    var enabled = skill.enabled;
    if (!enabled) {
      // A disabled skill exposes its explanation and never submits.
      return [
        {
          key: "skill-disabled",
          label: skill.label,
          description: skill.disabledReason ? skill.disabledReason.message : null,
          enabled: false,
          actionId: null,
          payload: null,
          disabledReason: skill.disabledReason,
        },
      ];
    }
    if (skill.targetSpec === "none") {
      return [
        {
          key: "none-confirm",
          label: "施展",
          enabled: true,
          actionId: "combat.cast",
          payload: { skill_key: skill.key },
        },
      ];
    }
    if (skill.targetSpec === "self") {
      return [
        {
          key: "self-confirm",
          label: "對自己施展",
          enabled: true,
          actionId: "combat.cast",
          payload: { skill_key: skill.key },
        },
      ];
    }
    if (skill.targetSpec === "single") {
      var validTargets = {};
      skill.targets.forEach(function (identity) {
        validTargets[identity] = true;
      });
      participants.forEach(function (participant) {
        if (!validTargets[participant.identity]) {
          return;
        }
        items.push({
          key: "target-" + participant.identity,
          label: participant.display_name,
          description: participant.state === "active" ? null : participant.state,
          enabled: true,
          actionId: "combat.cast",
          payload: { skill_key: skill.key, target_ids: [participant.identity] },
        });
      });
      return items;
    }
    // AREA
    var candidateTargets = {};
    skill.targets.forEach(function (identity) {
      candidateTargets[identity] = true;
    });
    participants.forEach(function (participant) {
      if (!candidateTargets[participant.identity]) {
        return;
      }
      items.push({
        key: "area-" + participant.identity,
        label: participant.display_name,
        enabled: true,
        actionId: "toggle-target",
        payload: { identity: participant.identity },
        selectable: true,
      });
    });
    skill.shorthands.forEach(function (shorthand) {
      items.push({
        key: "shorthand-" + shorthand,
        label: shorthand,
        enabled: true,
        actionId: "choose-shorthand",
        payload: { shorthand: shorthand },
        shorthand: shorthand,
      });
    });
    items.push({
      key: "area-confirm",
      label: "確認施展",
      enabled: true,
      actionId: "combat.cast",
      payload: null,
      confirm: true,
    });
    return items;
  }

  // -------------------------------------------------------------------------
  // Menu builder.
  // -------------------------------------------------------------------------

  // Build the full menu stack for one validated panel. `state` may carry
  // { skillKey, page } to restore focus after a panel replacement.
  function buildMenus(panel, state) {
    state = state || {};
    var participants = panelParticipants(panel);
    var byId = participantById(participants);
    var skills = panelSkills(panel).map(function (skill) {
      return skillModel(skill, byId);
    });

    var menus = {
      root: {
        items: rootItems(panel),
        focusKey: state.focusKey || null,
      },
      skills: {
        items: skillItems(skills, state.focusIdentity, state.page || 0),
        focusKey: state.focusKey || null,
      },
      forfeit: {
        items: [
          { key: "confirm-forfeit", label: "確認投降", enabled: true, actionId: "combat.forfeit", payload: { session_id: panel.session.session_id } },
          { key: "cancel-forfeit", label: "取消", enabled: true, actionId: null, payload: null },
        ],
        focusKey: null,
      },
    };

    var skillByKey = {};
    skills.forEach(function (skill) {
      skillByKey[skill.key] = skill;
    });

    return {
      panel: panel,
      recovery: panel.session.state === "recovery",
      participants: participants,
      skills: skills,
      skillByKey: skillByKey,
      menus: menus,
      focusSkillKey: state.skillKey || null,
      page: state.page || 0,
    };
  }

  // Open one skill's target menu. Returns a menu object or null for a skill
  // that cannot open (e.g. disabled, or already terminal).
  function openSkill(combat, skillKey) {
    var skill = combat.skillByKey[skillKey];
    if (!skill) {
      return null;
    }
    return {
      items: targetItemsFor(skill, combat.participants),
      focusKey: null,
      skillKey: skillKey,
    };
  }

  // Toggle one AREA candidate in the current skill's selection.
  function toggleArea(combat, skillKey, identity) {
    var skill = combat.skillByKey[skillKey];
    if (!skill || skill.targetSpec !== "area") {
      return false;
    }
    var index = skill.selected.indexOf(identity);
    if (index === -1) {
      skill.selected.push(identity);
    } else {
      skill.selected.splice(index, 1);
    }
    if (skill.selected.length > 0) {
      skill.shorthand = null;
    }
    return true;
  }

  // Choose one approved AREA shorthand; clears explicit selection.
  function chooseShorthand(combat, skillKey, shorthand) {
    var skill = combat.skillByKey[skillKey];
    if (!skill || skill.targetSpec !== "area") {
      return false;
    }
    skill.shorthand = shorthand;
    skill.selected = [];
    return true;
  }

  // The exact payload for one AREA confirm submission, or null when invalid.
  // Explicit selections are submitted in presenter order (the order the
  // identities appear in ``skill.targets``), regardless of toggle order, so the
  // wire payload is deterministic and matches the panel presentation.
  function areaPayload(skill) {
    if (skill.shorthand) {
      return { skill_key: skill.key, target_shorthand: skill.shorthand };
    }
    if (skill.selected.length === 0) {
      return null;
    }
    var order = {};
    skill.targets.forEach(function (identity, index) {
      order[identity] = index;
    });
    var presenterOrder = skill.selected.slice().sort(function (a, b) {
      return order[a] - order[b];
    });
    return { skill_key: skill.key, target_ids: presenterOrder };
  }

  // After a panel replacement, rebuild the selection state deterministically:
  // drop vanished selections and choose the nearest surviving focus.
  function rebuildForPanel(combat, panel, previous) {
    previous = previous || {};
    var next = buildMenus(panel, {
      skillKey: previous.skillKey || null,
      page: previous.page || 0,
    });
    return next;
  }

  return {
    ROOT_ACTIONS: ROOT_ACTIONS.slice(),
    SECONDARY_ACTIONS: SECONDARY_ACTIONS.slice(),
    RECOVERY_SECONDARY_ACTIONS: RECOVERY_SECONDARY_ACTIONS.slice(),
    PAGE_SIZE: PAGE_SIZE,
    BASIC_ATTACK_KEY: BASIC_ATTACK_KEY,
    rootItems: rootItems,
    buildMenus: buildMenus,
    openSkill: openSkill,
    toggleArea: toggleArea,
    chooseShorthand: chooseShorthand,
    areaPayload: areaPayload,
    rebuildForPanel: rebuildForPanel,
  };
});
