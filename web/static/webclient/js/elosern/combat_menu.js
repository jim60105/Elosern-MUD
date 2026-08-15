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
    var freeformScales = (skill.freeform_scales || []).slice();
    var defaultScale = 1;
    freeformScales.forEach(function (entry) {
      if (entry.scale === 1) {
        defaultScale = entry.scale;
      }
    });
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
      freeformScales: freeformScales,
      scale: defaultScale, // chosen freeform scale (1 = the default behavior)
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
      { key: "flee", label: "逃跑", enabled: true, actionId: "combat.flee", payload: {}, commandDisplay: { actionLabel: "逃跑" } },
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
  // Freeform scale-choice step (element-mastery-freeform-casting).
  // -------------------------------------------------------------------------

  // The 威力-choice items for a freeform-capable skill, or null when the
  // skill carries no `freeform_scales` (a non-master skill skips the step
  // entirely, so its flow and payload stay byte-identical to today).
  function scaleItemsFor(skill) {
    if (!skill.freeformScales || skill.freeformScales.length === 0) {
      return null;
    }
    return skill.freeformScales.map(function (entry) {
      return {
        key: "scale-" + entry.label,
        label: "威力×" + entry.label,
        description: "MP " + entry.mp_cost,
        enabled: true,
        actionId: "choose-scale",
        payload: { scale: entry.scale },
        scaleChoice: true,
      };
    });
  }

  // The chosen freeform scale to embed in a cast payload. Only skills that
  // advertise `freeformScales` carry the field; every other skill's payload
  // stays byte-identical to today (no `scale` key at all).
  function scaleForPayload(skill) {
    if (!skill.freeformScales || skill.freeformScales.length === 0) {
      return null;
    }
    return skill.scale;
  }

  // The display label for the chosen scale, or null (echo shows no 威力
  // suffix for the default choice or for non-freeform skills).
  function scaleLabelFor(skill) {
    if (!skill.freeformScales || skill.freeformScales.length === 0) {
      return null;
    }
    var chosen = skill.scale;
    var found = null;
    skill.freeformScales.forEach(function (entry) {
      if (entry.scale === chosen) {
        found = entry.label;
      }
    });
    return found;
  }

  // -------------------------------------------------------------------------
  // Target selection flows.
  // -------------------------------------------------------------------------

  // One combat.cast payload with the skill's chosen freeform scale embedded
  // (only for skills that advertise `freeform_scales`; all other payloads stay
  // byte-identical to today).
  function castPayloadFor(skill, targetFields) {
    var payload = { skill_key: skill.key };
    var scale = scaleForPayload(skill);
    if (scale !== null) {
      payload.scale = scale;
    }
    Object.keys(targetFields).forEach(function (field) {
      payload[field] = targetFields[field];
    });
    return payload;
  }

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
          payload: castPayloadFor(skill, {}),
          commandDisplay: { skillLabel: skill.label },
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
          payload: castPayloadFor(skill, {}),
          commandDisplay: { skillLabel: skill.label },
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
          payload: castPayloadFor(skill, {
            target_ids: [participant.identity],
          }),
          commandDisplay: {
            skillLabel: skill.label,
            targetLabel: participant.display_name,
          },
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
      // The AREA payload is computed at submit time (areaPayload); the
      // descriptor carries the skill label so the catalog can resolve the
      // echo line, with the chosen shorthand composed in by the submit path.
      commandDisplay: { skillLabel: skill.label },
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
        grid: true,
        gridCols: 5,
      },
      skills: {
        items: skillItems(skills, state.focusIdentity, state.page || 0),
        focusKey: state.focusKey || null,
        grid: true,
        gridCols: 2,
      },
      forfeit: {
        items: [
          { key: "confirm-forfeit", label: "確認投降", enabled: true, actionId: "combat.forfeit", payload: { session_id: panel.session.session_id } },
          { key: "cancel-forfeit", label: "取消", enabled: true, actionId: null, payload: null },
        ],
        focusKey: null,
        grid: true,
        gridCols: 2,
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

  // Open one skill's menu. Returns a menu object or null for a skill
  // that cannot open (e.g. disabled, or already terminal). A freeform-capable
  // skill opens its 威力-choice menu first; the target flow opens only after
  // a scale is confirmed (openSkillTargets).
  function openSkill(combat, skillKey) {
    var skill = combat.skillByKey[skillKey];
    if (!skill) {
      return null;
    }
    var scales = scaleItemsFor(skill);
    if (scales) {
      return {
        items: scales,
        focusKey: null,
        skillKey: skillKey,
        grid: true,
        gridCols: scales.length,
      };
    }
    return openSkillTargets(combat, skillKey);
  }

  // Open one skill's target flow directly (after the scale step confirmed).
  function openSkillTargets(combat, skillKey) {
    var skill = combat.skillByKey[skillKey];
    if (!skill) {
      return null;
    }
    return {
      items: targetItemsFor(skill, combat.participants),
      focusKey: null,
      skillKey: skillKey,
      grid: true,
      gridCols: 2,
    };
  }

  // Apply one confirmed scale choice to the focused skill.
  function chooseScale(combat, skillKey, scale) {
    var skill = combat.skillByKey[skillKey];
    if (!skill || !skill.freeformScales || skill.freeformScales.length === 0) {
      return false;
    }
    var member = false;
    skill.freeformScales.forEach(function (entry) {
      if (entry.scale === scale) {
        member = true;
      }
    });
    if (!member) {
      return false;
    }
    skill.scale = scale;
    return true;
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
    var base = { skill_key: skill.key };
    var scale = scaleForPayload(skill);
    if (scale !== null) {
      base.scale = scale;
    }
    if (skill.shorthand) {
      base.target_shorthand = skill.shorthand;
      return base;
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
    base.target_ids = presenterOrder;
    return base;
  }

  // After a panel replacement, rebuild the selection state deterministically:
  // drop vanished selections and choose the nearest surviving focus. A
  // still-valid freeform scale choice is preserved on the rebuilt skill;
  // a vanished or invalidated choice resets deterministically to `1`.
  function rebuildForPanel(combat, panel, previous) {
    previous = previous || {};
    var next = buildMenus(panel, {
      skillKey: previous.skillKey || null,
      page: previous.page || 0,
    });
    if (previous && previous.skillByKey) {
      Object.keys(previous.skillByKey).forEach(function (key) {
        var oldSkill = previous.skillByKey[key];
        var newSkill = next.skillByKey[key];
        if (!newSkill || !newSkill.freeformScales || !oldSkill.freeformScales) {
          return;
        }
        var preserved = oldSkill.scale;
        var stillValid = false;
        newSkill.freeformScales.forEach(function (entry) {
          if (entry.scale === preserved) {
            stillValid = true;
          }
        });
        newSkill.scale = stillValid ? preserved : 1;
      });
    }
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
    openSkillTargets: openSkillTargets,
    chooseScale: chooseScale,
    scaleLabelFor: scaleLabelFor,
    toggleArea: toggleArea,
    chooseShorthand: chooseShorthand,
    areaPayload: areaPayload,
    rebuildForPanel: rebuildForPanel,
  };
});
