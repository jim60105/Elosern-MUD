/*
 * Elosern DOM-independent character-creation menu model.
 *
 * Reduces a validated `creation` panel into the logical preset cards, the
 * custom-form geometry (selected race/subrace, the six allocation axes, and
 * the name plus two adult age fields), the saved-draft restoration, and the
 * exact wire payloads consumed by KeyboardRouter and the creation dock. The
 * server is authoritative for every bound and the adult gate; this model only
 * shapes the controls and produces advisory client feedback.
 *
 * No `document` or `window` access at load time; Node tests exercise the model
 * directly and the GoldenLayout creation dock binds it to the keyboard router
 * and the real form fields.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.CreationMenu = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var PRESET_ACTION = "creation.preset";
  var CUSTOM_ACTION = "creation.custom";
  var CONCEPT_ACTION = "creation.concept";
  var ACTIVATE_ACTION = "creation.activate";
  var RESET_ACTION = "creation.reset";

  // -------------------------------------------------------------------------
  // Root and preset menus.
  // -------------------------------------------------------------------------

  function rootItems(panel) {
    return [
      {
        key: "presets",
        label: "預設角色",
        enabled: true,
        actionId: null,
        payload: null,
        openSubmenu: "presets",
      },
      {
        key: "custom",
        label: "自訂角色",
        enabled: true,
        actionId: null,
        payload: null,
        openSubmenu: "custom",
      },
    ];
  }

  function presetItems(panel) {
    var items = [];
    (panel.presets || []).forEach(function (card, index) {
      items.push({
        key: "preset-" + index,
        label: card.display_name + "（" + card.race_description + "）",
        enabled: true,
        actionId: PRESET_ACTION,
        payload: { preset_key: card.key },
        presetKey: card.key,
        description:
          (card.emphasis || "") + " " + (card.background || ""),
      });
    });
    if (items.length === 0) {
      items.push({
        key: "presets-empty",
        label: "目前沒有可選擇的預設角色。",
        enabled: false,
        actionId: null,
        payload: null,
        description: "請使用自訂角色。",
      });
    }
    return items;
  }

  function presetCard(panel, presetKey) {
    var cards = panel.presets || [];
    for (var i = 0; i < cards.length; i++) {
      if (cards[i].key === presetKey) {
        return cards[i];
      }
    }
    return null;
  }

  // -------------------------------------------------------------------------
  // Custom-form geometry.
  // -------------------------------------------------------------------------

  function profileFor(panel, raceKey, subraceKey) {
    var profiles = panel.custom && panel.custom.profiles;
    if (!profiles) {
      return null;
    }
    for (var i = 0; i < profiles.length; i++) {
      var profile = profiles[i];
      if (profile.race === raceKey && (profile.subrace === null || profile.subrace === undefined ? null : profile.subrace) === (subraceKey || null)) {
        return profile;
      }
    }
    return null;
  }

  function raceOptions(panel) {
    return (panel.custom && panel.custom.races) || [];
  }

  function subraceOptions(panel, raceKey) {
    var race = null;
    raceOptions(panel).forEach(function (option) {
      if (option.key === raceKey) {
        race = option;
      }
    });
    if (!race || race.subraces === null) {
      return null;
    }
    var subraces = panel.custom && panel.custom.subraces;
    return race.subraces.map(function (key) {
      var entry = subraces && subraces[key];
      return {
        key: key,
        display_name_zh: (entry && entry.display_name_zh) || key,
        common_name_zh: (entry && entry.common_name_zh) || "",
        specialty: (entry && entry.specialty) || "",
      };
    });
  }

  function emptyAllocations() {
    return {
      hp: "",
      mp: "",
      sp: "",
      atk_phys: "",
      agility: "",
      defense: "",
    };
  }

  function defaultCustomState(panel) {
    var races = raceOptions(panel);
    return {
      displayName: "",
      age: "",
      apparentAge: "",
      raceKey: races.length > 0 ? races[0].key : null,
      subraceKey: null,
      allocations: emptyAllocations(),
      background: "",
      concept: "",
      affinityElements: [],
    };
  }

  function stateFromDraft(panel, draft) {
    var state = defaultCustomState(panel);
    if (!draft || (draft.mode !== "custom" && draft.mode !== "concept")) {
      return state;
    }
    // A concept draft pre-fills the finite controls (race/subrace/allocations)
    // while the name and both ages stay player-entered; a custom draft
    // restores every accepted value. The preserved background rides both
    // draft kinds: ``apply_concept_proposal`` carries a player-authored
    // background forward into the concept draft, so the restored form must
    // show it (fix-custom-creation-information-and-background D4).
    state.raceKey = draft.race || state.raceKey;
    state.subraceKey = draft.subrace || null;
    state.background = draft.background || "";
    state.affinityElements = (draft.affinity_elements || []).slice();
    var allocations = draft.allocations || {};
    Object.keys(allocations).forEach(function (axis) {
      if (state.allocations[axis] !== undefined) {
        state.allocations[axis] = String(allocations[axis]);
      }
    });
    if (draft.mode !== "custom") {
      return state;
    }
    state.displayName = draft.display_name || "";
    state.age = String(draft.age == null ? "" : draft.age);
    state.apparentAge = String(draft.apparent_age == null ? "" : draft.apparent_age);
    return state;
  }

  function raceItem(panel, option, index) {
    var subraceCount = option.subraces === null ? 0 : option.subraces.length;
    return {
      key: "race-" + index,
      label: option.key + (subraceCount > 0 ? "（子種族 " + subraceCount + "）" : ""),
      enabled: true,
      actionId: null,
      payload: null,
      raceKey: option.key,
      description: option.description,
    };
  }

  function subraceItem(entry, index) {
    return {
      key: "subrace-" + index,
      label: entry.display_name_zh,
      enabled: true,
      actionId: null,
      payload: null,
      subraceKey: entry.key,
      description: entry.specialty || entry.common_name_zh,
    };
  }

  function subraceItems(panel, state) {
    var options = subraceOptions(panel, state.raceKey);
    if (options === null) {
      return null;
    }
    var items = [];
    options.forEach(function (entry, index) {
      items.push(subraceItem(entry, index));
    });
    return items;
  }

  // The allocation briefing facts shown above the allocation fields: the total
  // budget, the six-axis count, each axis's 0–span, and the sum-must-equal-
  // budget rule. Derived entirely from the server-owned profile so the web
  // form can never drift from ``resolve_starting_profile`` (design D3).
  function briefingFor(panel, state) {
    var profile = profileFor(panel, state.raceKey, state.subraceKey);
    if (!profile) {
      return null;
    }
    var spans = profile.axes.map(function (axis) {
      return {
        axis: axis.axis,
        label: axis.label,
        minimum: axis.minimum,
        maximum: axis.maximum,
      };
    });
    return {
      budget: profile.budget,
      axisCount: spans.length,
      spans: spans,
      rule: "六項配點總和必須恰好等於 " + profile.budget + "。",
    };
  }

  // One field descriptor for an allocation axis of the active profile.
  function axisField(profile, axisKey) {
    var axes = (profile && profile.axes) || [];
    for (var i = 0; i < axes.length; i++) {
      if (axes[i].axis === axisKey) {
        return axes[i];
      }
    }
    return null;
  }

  function axisFields(panel, state) {
    var profile = profileFor(panel, state.raceKey, state.subraceKey);
    if (!profile) {
      return [];
    }
    return profile.axes.map(function (axis) {
      return {
        axis: axis.axis,
        label: axis.label,
        explanation: axis.explanation,
        minimum: axis.minimum,
        maximum: axis.maximum,
      };
    });
  }

  function budgetFor(panel, state) {
    var profile = profileFor(panel, state.raceKey, state.subraceKey);
    return profile ? profile.budget : null;
  }

  function allocatedTotal(state) {
    var total = 0;
    Object.keys(state.allocations).forEach(function (axis) {
      var value = parseInt(state.allocations[axis], 10);
      if (!isNaN(value)) {
        total += value;
      }
    });
    return total;
  }

  // Advisory client-side validation. The server is authoritative; these
  // messages only shape the field-bound announcements in the dock.
  function validateCustom(panel, state) {
    var errors = {};
    var name = (state.displayName || "").trim();
    if (name.length < 1 || name.length > 64) {
      errors.displayName = "角色姓名需為 1–64 個字元。";
    }
    var age = parseInt(state.age, 10);
    if (isNaN(age) || age < 18 || age > 10000) {
      errors.age = "實際年齡需為 18–10000 的整數。";
    }
    var apparentAge = parseInt(state.apparentAge, 10);
    if (isNaN(apparentAge) || apparentAge < 18 || apparentAge > 10000) {
      errors.apparentAge = "外表年齡需為 18–10000 的整數。";
    }
    var profile = profileFor(panel, state.raceKey, state.subraceKey);
    if (!profile) {
      if (!state.raceKey) {
        errors.race = "請選擇種族。";
      } else if (!state.subraceKey) {
        errors.subrace = "請選擇子種族。";
      } else {
        errors.race = "請選擇種族與子種族。";
      }
    } else {
      Object.keys(state.allocations).forEach(function (axis) {
        var field = axisField(profile, axis);
        var raw = state.allocations[axis];
        if (raw === "") {
          return;
        }
        var value = parseInt(raw, 10);
        if (isNaN(value) || value < field.minimum || value > field.maximum) {
          errors[axis] =
            field.label + " 配點需為 " + field.minimum + "–" + field.maximum + " 的整數。";
        }
      });
      var total = allocatedTotal(state);
      if (total !== profile.budget) {
        errors.budget = "配點總和需恰好等於 " + profile.budget + "（目前 " + total + "）。";
      }
    }
    return {
      valid: Object.keys(errors).length === 0,
      errors: errors,
    };
  }

  // The affinity picker geometry for the selected race, derived entirely from
  // the server-owned ``affinity`` descriptor so the web form can never drift
  // from ``max_affinity_elements`` (design D3/D4).
  function affinityFor(panel, raceKey) {
    var affinity = panel.custom && panel.custom.affinity;
    if (!affinity) {
      return null;
    }
    return affinity[raceKey] || null;
  }

  function affinityElementKeys(panel, raceKey) {
    var bounds = affinityFor(panel, raceKey);
    if (!bounds || !bounds.elements) {
      return [];
    }
    return bounds.elements.map(function (element) {
      return element.key;
    });
  }

  function affinityMaximum(panel, raceKey) {
    var bounds = affinityFor(panel, raceKey);
    return bounds ? bounds.maximum : 0;
  }

  // One choice descriptor for the affinity picker, derived from the
  // server-owned element list.
  function affinityChoice(panel, raceKey, elementKey) {
    var bounds = affinityFor(panel, raceKey);
    if (!bounds || !bounds.elements) {
      return null;
    }
    for (var i = 0; i < bounds.elements.length; i++) {
      if (bounds.elements[i].key === elementKey) {
        return {
          key: bounds.elements[i].key,
          label: bounds.elements[i].label,
        };
      }
    }
    return null;
  }

  function affinityChoices(panel, raceKey) {
    var bounds = affinityFor(panel, raceKey);
    if (!bounds || !bounds.elements) {
      return [];
    }
    return bounds.elements.map(function (element) {
      return { key: element.key, label: element.label };
    });
  }

  function affinityItems(panel, raceKey) {
    return affinityChoices(panel, raceKey).map(function (element, index) {
      return {
        key: "affinity-" + index,
        label: element.label + "（" + element.key + "）",
        enabled: true,
        actionId: null,
        payload: null,
        affinityKey: element.key,
        description: "",
      };
    });
  }

  function toggleAffinity(state, elementKey) {
    var index = state.affinityElements.indexOf(elementKey);
    if (index >= 0) {
      state.affinityElements.splice(index, 1);
      return state;
    }
    // The bound is only advisory here; the server re-validates every submit.
    state.affinityElements.push(elementKey);
    return state;
  }

  function affinitySelected(state, elementKey) {
    return state.affinityElements.indexOf(elementKey) >= 0;
  }

  // The exact wire payload for `creation.custom`. Undefined/blank fields are
  // emitted as their JSON-safe defaults so the server revalidates everything.
  function customPayload(state) {
    var allocations = {};
    Object.keys(state.allocations).forEach(function (axis) {
      var value = parseInt(state.allocations[axis], 10);
      allocations[axis] = isNaN(value) ? 0 : value;
    });
    return {
      display_name: (state.displayName || "").trim(),
      age: parseInt(state.age, 10) || 0,
      apparent_age: parseInt(state.apparentAge, 10) || 0,
      race: state.raceKey || "",
      subrace: state.subraceKey || "",
      background: (state.background || "").trim() || null,
      affinity_elements: state.affinityElements.slice(),
      allocations: allocations,
    };
  }

  // -------------------------------------------------------------------------
  // Confirmation screens.
  // -------------------------------------------------------------------------

  function confirmMenu(label, actionId, payload, itemLabel) {
    return {
      items: [
        {
          key: "confirm-" + actionId,
          label: label || "確認",
          enabled: true,
          actionId: actionId,
          payload: payload,
        },
        {
          key: "cancel-" + actionId,
          label: "取消",
          enabled: true,
          actionId: null,
          payload: null,
        },
      ],
      itemLabel: itemLabel || null,
    };
  }

  function activateConfirm(presetKey) {
    var label = presetKey ? "確認啟用此預設角色？" : "確認建立此角色？";
    return confirmMenu(label, ACTIVATE_ACTION, {}, presetKey || null);
  }

  // -------------------------------------------------------------------------
  // Menu model builder.
  // -------------------------------------------------------------------------

  function buildMenus(panel) {
    return {
      panel: panel,
      menus: {
        root: { items: rootItems(panel), focusKey: null },
        presets: { items: presetItems(panel), focusKey: null, grid: true, gridCols: 2 },
      },
    };
  }

  return {
    PRESET_ACTION: PRESET_ACTION,
    CUSTOM_ACTION: CUSTOM_ACTION,
    CONCEPT_ACTION: CONCEPT_ACTION,
    ACTIVATE_ACTION: ACTIVATE_ACTION,
    RESET_ACTION: RESET_ACTION,
    rootItems: rootItems,
    presetItems: presetItems,
    presetCard: presetCard,
    buildMenus: buildMenus,
    profileFor: profileFor,
    raceOptions: raceOptions,
    subraceOptions: subraceOptions,
    defaultCustomState: defaultCustomState,
    stateFromDraft: stateFromDraft,
    raceItem: raceItem,
    subraceItem: subraceItem,
    subraceItems: subraceItems,
    briefingFor: briefingFor,
    axisField: axisField,
    axisFields: axisFields,
    budgetFor: budgetFor,
    allocatedTotal: allocatedTotal,
    validateCustom: validateCustom,
    customPayload: customPayload,
    affinityFor: affinityFor,
    affinityElementKeys: affinityElementKeys,
    affinityMaximum: affinityMaximum,
    affinityChoice: affinityChoice,
    affinityChoices: affinityChoices,
    affinityItems: affinityItems,
    toggleAffinity: toggleAffinity,
    affinitySelected: affinitySelected,
    confirmMenu: confirmMenu,
    activateConfirm: activateConfirm,
  };
});
