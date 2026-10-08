/*
 * Elosern DOM-independent SkillBook use menu model
 * (skillbook-authoritative-casting D6).
 *
 * Transforms a validated `skill_use` panel (one owned active skill previewed
 * at one scale) into the dock frames the single keyboard router hosts after
 * the book hands casting over: the use frame (scale opener, the NONE/SELF
 * explicit confirmation, SINGLE target rows, AREA toggle rows plus their
 * confirm row, and monster openings), the scale frame, and the opening
 * confirmation frame. Every identity, label, cost, reason, and line-up is the
 * server's; the model only lays them out and keeps the client-local AREA
 * selection until the deliberate confirmation. It never decides
 * availability: a row is enabled exactly when the panel says so.
 *
 * No `document` or `window` access at load time; Node tests exercise the
 * model directly.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.SkillUseMenu = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var CAST_ACTION = "explore.cast";
  var PREVIEW_ACTION = "explore.skill_preview";
  var DAMAGE_ONLY_CODE = "damage_requires_monster_target";

  function costText(cost) {
    var parts = [];
    Object.keys(cost || {}).forEach(function (key) {
      if (cost[key] > 0) {
        parts.push(key.toUpperCase() + " " + cost[key]);
      }
    });
    return parts.length > 0 ? parts.join("、") : "無消耗";
  }

  function hasScales(skill) {
    return Array.isArray(skill.freeform_scales) && skill.freeform_scales.length > 0;
  }

  function scaleLabel(panel) {
    var found = null;
    (panel.skill.freeform_scales || []).forEach(function (entry) {
      if (entry.scale === panel.scale) {
        found = entry.label;
      }
    });
    if (found !== null) {
      return found;
    }
    return panel.scale === 1 ? "1" : String(panel.scale);
  }

  // The cast payload base: the skill key plus the previewed scale, sent only
  // for a skill whose panel advertises scale rungs (every other payload
  // stays `{skill_key}` plus its target form).
  function payloadBase(panel) {
    var payload = { skill_key: panel.skill.key };
    if (hasScales(panel.skill) || panel.scale !== 1) {
      payload.scale = panel.scale;
    }
    return payload;
  }

  function reasonOf(row) {
    return row && row.disabled_reason ? row.disabled_reason : null;
  }

  // A fresh client-local selection for one previewed skill.
  function createModel(panel, previous) {
    var skill = panel.skill;
    var selected = [];
    if (previous && previous.skillKey === skill.key && skill.target_spec === "area") {
      // Reconcile against the newer panel: a vanished or now-disabled
      // candidate leaves the selection; nothing is ever added implicitly.
      var enabled = {};
      skill.targets.forEach(function (row) {
        if (row.enabled) {
          enabled[row.identity] = true;
        }
      });
      selected = previous.selected.filter(function (identity) {
        return enabled[identity] === true;
      });
    }
    return { panel: panel, skillKey: skill.key, selected: selected };
  }

  function toggle(model, identity) {
    var skill = model.panel.skill;
    if (skill.target_spec !== "area") {
      return false;
    }
    var row = null;
    skill.targets.forEach(function (candidate) {
      if (candidate.identity === identity) {
        row = candidate;
      }
    });
    if (!row || !row.enabled) {
      return false;
    }
    var index = model.selected.indexOf(identity);
    if (index === -1) {
      model.selected.push(identity);
    } else {
      model.selected.splice(index, 1);
    }
    return true;
  }

  // The ordinary AREA payload: the selected identities in presenter order,
  // or null when nothing is selected.
  function areaPayload(model) {
    if (model.selected.length === 0) {
      return null;
    }
    var chosen = {};
    model.selected.forEach(function (identity) {
      chosen[identity] = true;
    });
    var ids = model.panel.skill.targets
      .filter(function (row) {
        return chosen[row.identity] === true;
      })
      .map(function (row) {
        return row.identity;
      });
    var payload = payloadBase(model.panel);
    payload.target_ids = ids;
    return payload;
  }

  function targetLabels(model, ids) {
    var byId = {};
    model.panel.skill.targets.forEach(function (row) {
      byId[row.identity] = row.label;
    });
    return ids.map(function (id) {
      return byId[id];
    });
  }

  // True when every ordinary row is refused only because the skill damages:
  // the rows collapse into one explanation instead of a column of refusals.
  function damageOnly(skill) {
    return (
      skill.targets.length > 0 &&
      skill.targets.every(function (row) {
        return !row.enabled && reasonOf(row) && reasonOf(row).code === DAMAGE_ONLY_CODE;
      })
    );
  }

  // The use frame: the dock's first frame after the book hands over.
  function useMenu(model) {
    var panel = model.panel;
    var skill = panel.skill;
    var items = [];
    var display = { skillLabel: skill.label };
    if (hasScales(skill)) {
      items.push({
        key: "scale-open",
        label: "威力 ×" + scaleLabel(panel),
        description: costText(skill.cost) + " ‧ 調整威力",
        enabled: true,
        actionId: "open-skilluse-scale",
        payload: null,
        kind: "scale",
      });
    }
    var spec = skill.target_spec;
    if (spec === "none" || spec === "self") {
      items.push({
        key: "cast-" + spec,
        label: spec === "self" ? "對自己施展" : "施展「" + skill.label + "」",
        description: costText(skill.cost),
        enabled: skill.enabled,
        disabledReason: reasonOf(skill),
        actionId: skill.enabled ? CAST_ACTION : null,
        payload: skill.enabled ? payloadBase(panel) : null,
        commandDisplay: display,
        kind: "confirm",
      });
      return finish(items, skill);
    }
    if (damageOnly(skill)) {
      items.push({
        key: "targets-damage-only",
        label: "傷害技能只能對魔物出手",
        description: skill.openings.length > 0 ? "請從下方選擇要開戰的對象。" : "附近沒有可開戰的魔物。",
        enabled: false,
        disabledReason: reasonOf(skill.targets[0]),
        actionId: null,
        payload: null,
        kind: "note",
      });
    } else if (spec === "single") {
      skill.targets.forEach(function (row) {
        var payload = payloadBase(panel);
        payload.target_ids = [row.identity];
        items.push({
          key: "target-" + row.identity,
          label: row.label,
          enabled: row.enabled,
          disabledReason: reasonOf(row),
          actionId: row.enabled ? CAST_ACTION : null,
          payload: row.enabled ? payload : null,
          commandDisplay: { skillLabel: skill.label, targetLabel: row.label },
          kind: "target",
        });
      });
    } else {
      skill.targets.forEach(function (row) {
        items.push({
          key: "area-" + row.identity,
          label: row.label,
          enabled: row.enabled,
          disabledReason: reasonOf(row),
          actionId: row.enabled ? "toggle-skilluse-target" : null,
          payload: row.enabled ? { identity: row.identity } : null,
          selectable: true,
          selected: model.selected.indexOf(row.identity) !== -1,
          kind: "target",
        });
      });
      if (skill.targets.length > 0) {
        var count = model.selected.length;
        var payloadArea = areaPayload(model);
        items.push({
          key: "area-confirm",
          label: count > 0 ? "確認施展（已選 " + count + "）" : "確認施展",
          description: count > 0 ? null : "以 Space 選取至少一名對象。",
          enabled: count > 0,
          disabledReason: count > 0 ? null : { code: "no_selection", message: "尚未選取對象。" },
          actionId: count > 0 ? CAST_ACTION : null,
          payload: payloadArea,
          confirm: true,
          commandDisplay: payloadArea
            ? { skillLabel: skill.label, targetLabels: targetLabels(model, payloadArea.target_ids) }
            : display,
          kind: "confirm",
        });
      }
    }
    skill.openings.forEach(function (row) {
      items.push({
        key: "opening-" + row.identity,
        label: row.label,
        enabled: row.enabled,
        disabledReason: reasonOf(row),
        actionId: row.enabled ? "open-skilluse-opening" : null,
        payload: row.enabled ? { identity: row.identity } : null,
        kind: "opening",
        team: "foes",
      });
    });
    return finish(items, skill);
  }

  function finish(items, skill) {
    var hasAction = items.some(function (item) {
      return item.kind !== "scale";
    });
    if (!hasAction) {
      items.push({
        key: "skilluse-empty",
        label: skill.disabled_reason ? skill.disabled_reason.message : "附近沒有可施放的對象。",
        enabled: false,
        disabledReason: reasonOf(skill),
        actionId: null,
        payload: null,
        kind: "note",
      });
    }
    return {
      items: items,
      focusKey: null,
      grid: true,
      gridCols: 1,
      title: "施放 ‧ " + skill.label,
    };
  }

  // The 威力 frame: one row per advertised rung; activating a rung asks the
  // server for a fresh preview at that scale (never a local cost guess).
  function scaleMenu(model) {
    var panel = model.panel;
    var rungs = panel.skill.freeform_scales || [];
    var items = rungs.map(function (entry) {
      var current = entry.scale === panel.scale;
      return {
        key: "scale-" + entry.label,
        label: "威力 ×" + entry.label,
        description: "MP " + entry.mp_cost + (current ? " ‧ 目前選擇" : ""),
        enabled: true,
        actionId: "choose-skilluse-scale",
        payload: { scale: entry.scale },
        scaleChoice: true,
        current: current,
        kind: "scale",
      };
    });
    return {
      items: items,
      focusKey: "scale-" + scaleLabel(panel),
      grid: true,
      gridCols: 1,
      title: "威力",
    };
  }

  // The opening confirmation: restates the consequence (combat starts, and
  // for AREA every listed monster joins) before the one deliberate submit.
  function openingMenu(model, identity) {
    var panel = model.panel;
    var skill = panel.skill;
    var opening = null;
    skill.openings.forEach(function (row) {
      if (row.identity === identity) {
        opening = row;
      }
    });
    if (!opening || !opening.enabled) {
      return null;
    }
    var payload = payloadBase(panel);
    payload.opening_target_id = opening.identity;
    var names = {};
    skill.openings.forEach(function (row) {
      names[row.identity] = row.label;
    });
    return {
      items: [
        {
          key: "confirm-opening",
          label: "開戰並施放",
          description: opening.label,
          enabled: true,
          actionId: CAST_ACTION,
          payload: payload,
          commandDisplay: { skillLabel: skill.label, actionLabel: opening.label },
          kind: "confirm",
          lineUp: opening.target_ids.slice(),
        },
        {
          key: "cancel-opening",
          label: "取消",
          enabled: true,
          actionId: null,
          payload: null,
          kind: "cancel",
        },
      ],
      focusKey: null,
      grid: true,
      gridCols: 2,
      title: "開戰確認",
      opening: opening,
    };
  }

  return {
    CAST_ACTION: CAST_ACTION,
    PREVIEW_ACTION: PREVIEW_ACTION,
    costText: costText,
    createModel: createModel,
    toggle: toggle,
    areaPayload: areaPayload,
    useMenu: useMenu,
    scaleMenu: scaleMenu,
    openingMenu: openingMenu,
  };
});
