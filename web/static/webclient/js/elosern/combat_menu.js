/*
 * Elosern DOM-independent combat-menu model.
 *
 * Transforms a validated `context_actions` combat panel into the logical
 * keyboard menus consumed by KeyboardRouter: a root (Attack, Skills, Items,
 * Defend, Dodge, Taunt, Retreat, Surrender), a paginated active-skill list,
 * target flows for every TargetSpec, Space multi-selection for AREA, and the
 * shared party-scope exit contract both Retreat and Surrender request through
 * (`partyExitPrompt`); the actor selector frame lists the server's allied actors
 * with their confirmed/needs-selection/reselection-reason status and the
 * compact progress line the card chrome renders. The module preserves the
 * originating skill focus on
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

  // The client-local root inventory (webclient-party-items-tactics): Attack,
  // Skills, Items, the Bag drawer opener, the three basic actions, Retreat and
  // Surrender. Dodge and Taunt join Defend as actor-scoped basic actions; no
  // placeholder row remains. Retreat and Surrender are party-scope operations
  // (webclient-party-exit-confirmation): the retired per-actor combat.flee /
  // combat.forfeit routes and their client-local confirmation frame are gone,
  // so neither row carries an action id of its own.
  var ROOT_ACTIONS = ["attack", "skills", "items", "bag", "defend", "dodge", "taunt", "retreat", "surrender"];
  var SECONDARY_ACTIONS = ["surrender"];
  var RECOVERY_SECONDARY_ACTIONS = ["surrender"];
  var PAGE_SIZE = 6;
  var BASIC_ATTACK_KEY = "basic_attack";
  // The two party-scope exit operations and their client display labels
  // (webclient-party-exit-confirmation). Both take the same server-bound
  // confirmation route: one read-only prompt request, then one confirmed
  // `combat.exit_confirm`; the token decides which operation runs.
  var PARTY_EXIT_OPERATIONS = ["retreat", "surrender"];
  var PARTY_EXIT_LABELS = { retreat: "撤退", surrender: "投降" };
  // The three basic actions' client display labels (the panel carries its own
  // label; this is the fallback for a tactic the panel does not offer).
  var TACTIC_LABELS = { defend: "防禦", dodge: "閃避", taunt: "挑釁" };

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

  // Flatten the v3 nested `category -> groups -> skills` payload back into a
  // plain ordered skill list, preserving the server's per-group order. The
  // nesting is presentation metadata for headings; the menu itself still
  // presents one complete active-skill list (the approved keyboard hierarchy
  // has Skills open the flat list, not category navigation).
  //
  // v7 publishes the requested actor's grouped catalog under `choices`; the
  // obsolete puppet-level `skills` field is gone (recovery carries null
  // choices, so it flattens to the empty list).
  function choicesSkills(panel) {
    return (panel && panel.choices && panel.choices.skills) || [];
  }

  function panelSkills(panel) {
    var skills = [];
    choicesSkills(panel).forEach(function (category) {
      (category.groups || []).forEach(function (subGroup) {
        (subGroup.skills || []).forEach(function (skill) {
          skills.push(skill);
        });
      });
    });
    return skills;
  }

  function panelParticipants(panel) {
    return (panel && panel.participants) || [];
  }

  // -------------------------------------------------------------------------
  // Root menus.
  // -------------------------------------------------------------------------

  // The root rows' client-local explanatory copy
  // (webclient-combat-command-window): what each command opens or does, shown
  // in the detail beside the highlighted row. It states no gameplay value;
  // the disabled placeholders explain themselves through their reason.
  var ROOT_COPY = {
    attack: "選擇一名目標，以普通攻擊出手。",
    skills: "從已習得的技能中選擇施展。",
    items: "使用這名成員身上的道具。",
    bag: "開啟背包，查看攜帶的物品。",
    defend: "這名成員這回合採取防禦。",
    dodge: "這名成員這回合採取閃避。",
    taunt: "挑釁一名敵人，把它的注意力引到這名成員身上。",
    retreat: "請求全隊撤退；確認前不會送出任何變更。",
    surrender: "請求全隊投降；確認前不會送出任何變更。",
  };

  // -------------------------------------------------------------------------
  // The commanded actor's own items and basic actions
  // (webclient-party-items-tactics).
  // -------------------------------------------------------------------------

  // The v7 panel's actor-local item and tactic choices: the commanded actor's
  // own usable stock and capability, never the commander's global inventory
  // and never a shared party bag.
  function panelItems(panel) {
    return (panel && panel.choices && panel.choices.items) || [];
  }

  function panelTactics(panel) {
    return (panel && panel.choices && panel.choices.tactics) || [];
  }

  // One item choice as the menu's immutable subject model: the committed
  // stock row (label, quantity, effect summary, target spec, legal targets
  // and polarity) verbatim.
  function itemModel(row) {
    return {
      key: row.item_key,
      label: row.label,
      summary: typeof row.summary === "string" ? row.summary : "",
      quantity: row.quantity,
      enabled: !!row.enabled,
      disabledReason: row.reason || null,
      targetSpec: row.target_spec,
      targets: (row.targets || []).slice(),
      hostile: !!row.hostile,
      beneficial: !!row.beneficial,
    };
  }

  // One basic-action row as the menu's subject model (its enabled state and
  // reason are the committed capability facts verbatim). 挑釁's shape is the
  // client-side fact of the closed vocabulary: it names exactly one enemy,
  // while 防禦 and 閃避 carry no target at all (`TACTIC_KEYS`), so the stage
  // target step stands only for 挑釁.
  function tacticModel(row) {
    return {
      key: row.key,
      label: row.label,
      enabled: !!row.enabled,
      disabledReason: row.reason || null,
      targetSpec: row.key === "taunt" ? "single" : "none",
      targets: (row.targets || []).slice(),
    };
  }

  function findTactic(tactics, key) {
    var found = null;
    tactics.forEach(function (tactic) {
      if (tactic.key === key) {
        found = tactic;
      }
    });
    return found;
  }

  // The commanded actor's committed basic-action rows as subject models.
  function tacticModels(panel) {
    return panelTactics(panel).map(tacticModel);
  }

  // The 道具 root row: it opens the commanded actor's own usable stock. An
  // actor with none carries the capability reason (the frame would have no
  // row to show, so the root row is where the fact must surface).
  function itemsRootRow(items) {
    var row = {
      key: "items",
      label: "道具",
      enabled: items.length > 0,
      actionId: null,
      payload: null,
      command: true,
      description: ROOT_COPY.items,
    };
    if (items.length === 0) {
      row.disabledReason = { code: "no_usable_item", message: "沒有可用的道具。" };
    }
    return row;
  }

  // One basic-action root row (防禦 / 閃避 / 挑釁): the committed tactic row's
  // own enabled state and reason. A tactic the panel does not offer stays
  // visible and unreachable instead of silently disappearing.
  function tacticRootRow(key, tactics) {
    var tactic = findTactic(tactics, key);
    var row = {
      key: key,
      label: (tactic && tactic.label) || TACTIC_LABELS[key],
      enabled: !!tactic && tactic.enabled,
      actionId: null,
      payload: null,
      command: true,
      description: ROOT_COPY[key],
    };
    if (!row.enabled) {
      row.disabledReason =
        (tactic && tactic.disabledReason) || {
          code: "unavailable",
          message: "目前無法採取這項戰術。",
        };
    }
    return row;
  }

  // Every root, category, and group row carries `command: true`: the dock
  // renders those frames as one vertical command list (a single column, so
  // Up/Down wrap and Left/Right are no-ops).
  //
  // One party-scope exit root row (撤退 / 投降, webclient-party-exit-
  // confirmation): reachable from every member's root and from the recovery
  // root, never gated on the commanded member being commandable — the request
  // itself is actor-independent. The row carries no action id: activating it
  // asks the server for the bound confirmation prompt (frames.js), and only
  // the question card's Yes sends the one `combat.exit_confirm`.
  function partyExitRow(operation) {
    return {
      key: operation,
      label: PARTY_EXIT_LABELS[operation],
      enabled: true,
      actionId: null,
      payload: null,
      exitOperation: operation,
      command: true,
      description: ROOT_COPY[operation],
    };
  }

  // The shared confirmation contract of both exit operations
  // (webclient-party-exit-confirmation): the exact bounded fields the
  // server's `party_exit_prompt` result carries, turned into the one question
  // the card renders — the whole party's scope, the operation's own label and
  // the server-authored consequence. `null` for anything the protocol would
  // not admit (the identity-loss degradation: no card, nothing to confirm).
  function partyExitPrompt(operation, data) {
    var row = data || {};
    if (PARTY_EXIT_OPERATIONS.indexOf(operation) === -1 || row.operation !== operation) {
      return null;
    }
    if (row.scope !== "party") {
      return null;
    }
    if (typeof row.confirmation_token !== "string" || row.confirmation_token === "") {
      return null;
    }
    if (typeof row.consequence !== "string" || row.consequence === "") {
      return null;
    }
    var label = PARTY_EXIT_LABELS[operation];
    return {
      operation: operation,
      label: label,
      question: "確定要全隊" + label + "？",
      consequence: row.consequence,
      scope: row.scope,
      token: row.confirmation_token,
    };
  }

  function rootItems(panel) {
    var recovery = panel && panel.session && panel.session.state === "recovery";
    // Retreat and Surrender always request the server-bound confirmation
    // prompt first; only its Yes sends the one `combat.exit_confirm`. In
    // recovery the root exposes exactly that confirmed Surrender path and
    // nothing else.
    if (recovery) {
      return [partyExitRow("surrender")];
    }
    return [
      { key: "attack", label: "攻擊", enabled: true, actionId: null, payload: null, command: true, description: ROOT_COPY.attack },
      { key: "skills", label: "技能", enabled: true, actionId: null, payload: null, command: true, description: ROOT_COPY.skills },
      itemsRootRow(panelItems(panel)),
      { key: "bag", label: "背包", enabled: true, actionId: null, payload: null, openDrawer: "inventory", command: true, description: ROOT_COPY.bag },
      tacticRootRow("defend", tacticModels(panel)),
      tacticRootRow("dodge", tacticModels(panel)),
      tacticRootRow("taunt", tacticModels(panel)),
      partyExitRow("retreat"),
      partyExitRow("surrender"),
    ];
  }

  // -------------------------------------------------------------------------
  // Skill list with deterministic pagination.
  // -------------------------------------------------------------------------

  // H3 (webclient-hud-03-action-dock): the skill master-detail replaces the
  // flat skill list. `categoryItems` is the category frame (one row per
  // committed `skills[]` category group, badged with its owned-skill count);
  // `groupItems` is the group frame, presented only when the category
  // carries more than one sub-group — a single-sub-group category opens the
  // skill frame directly, so no level ever offers a single choice (design
  // D11). The skill frame lists that group's descriptors beside the detail
  // pane (design D11/D15: no pagination — the bounded pane scrolls).
  function categoryItems(panel) {
    var items = [];
    choicesSkills(panel).forEach(function (category, index) {
      var count = 0;
      (category.groups || []).forEach(function (group) {
        count += (group.skills || []).length;
      });
      items.push({
        key: "skill-cat-" + index,
        label: category.label,
        enabled: true,
        actionId: "open-category",
        payload: { categoryIndex: index },
        skillCount: count,
        command: true,
      });
    });
    return items;
  }

  function groupItems(panel, categoryIndex) {
    var category = choicesSkills(panel)[categoryIndex];
    var groups = (category && category.groups) || [];
    var items = [];
    groups.forEach(function (group, index) {
      items.push({
        key: "skill-group-" + categoryIndex + "-" + index,
        label: group.label || group.group || "群組",
        enabled: true,
        actionId: "open-group",
        payload: { categoryIndex: categoryIndex, groupIndex: index },
        skillCount: (group.skills || []).length,
        command: true,
      });
    });
    return items;
  }

  // The skill frame for one category group: the group's descriptors in the
  // server's order, each row carrying the skill's label and resource cost
  // beside the detail pane (the draft's `.sk` row + `.skdetail`).
  function groupSkillItems(combat, categoryIndex, groupIndex) {
    var panel = combat.panel;
    var category = choicesSkills(panel)[categoryIndex];
    var group = ((category && category.groups) || [])[groupIndex];
    var items = [];
    ((group && group.skills) || []).forEach(function (skill) {
      var model = combat.skillByKey && combat.skillByKey[skill.key];
      if (!model) {
        return;
      }
      var item = {
        key: skill.key,
        label: model.label,
        description: model.description,
        costText: model.costText,
        enabled: model.enabled,
        disabledReason: model.disabledReason,
        actionId: null,
        payload: null,
      };
      if (model.enabled) {
        item.actionId = "open-skill";
        item.payload = { skillKey: skill.key };
      }
      items.push(item);
    });
    return items;
  }

  // Open a category: a single-sub-group category opens the skill frame
  // directly; a multi-group category opens the group frame (design D11).
  function openCategory(combat, categoryIndex) {
    var panel = combat.panel;
    var category = choicesSkills(panel)[categoryIndex];
    var groups = (category && category.groups) || [];
    if (groups.length === 1) {
      return {
        items: groupSkillItems(combat, categoryIndex, 0),
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: groups[0].label || groups[0].group || "技能",
      };
    }
    var items = groupItems(panel, categoryIndex);
    return {
      items: items,
      focusKey: null,
      grid: true,
      gridCols: 1,
      title: category.label,
    };
  }

  // H3: open one group's skill frame (a groupItem's confirm action,
  // `open-group`): the group's descriptors beside the detail pane.
  function openGroup(combat, categoryIndex, groupIndex) {
    var panel = combat.panel;
    var category = choicesSkills(panel)[categoryIndex];
    var group = ((category && category.groups) || [])[groupIndex];
    if (!group) {
      return null;
    }
    return {
      items: groupSkillItems(combat, categoryIndex, groupIndex),
      focusKey: null,
      grid: true,
      gridCols: 1,
      title: group.label || group.group || "技能",
    };
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
          actionId: "combat.command",
          commandKind: "skill",
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
          actionId: "combat.command",
          commandKind: "skill",
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
          team: participant.team || null,
          enabled: true,
          actionId: "combat.command",
          commandKind: "skill",
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
        team: participant.team || null,
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
      actionId: "combat.command",
      commandKind: "skill",
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
  // Actor selector, draft progress and the guarded command envelope.
  // -------------------------------------------------------------------------

  // The committed draft's status rows for the allies, keyed by actor identity.
  function draftStatus(panel) {
    var draft = (panel && panel.draft) || {};
    var confirmed = {};
    (draft.entries || []).forEach(function (entry) {
      confirmed[String(entry.actor_id)] = true;
    });
    var needs = {};
    (draft.needs_selection_ids || []).forEach(function (identity) {
      needs[String(identity)] = true;
    });
    var reasons = {};
    (draft.reselection_reasons || []).forEach(function (row) {
      reasons[String(row.actor_id)] = row.reason || null;
    });
    return { confirmed: confirmed, needs: needs, reasons: reasons };
  }

  // One actor selector row per committed allied actor, in the server's order.
  // The status is the authoritative draft progress: 已確認, 待選擇, or the
  // server-authored reselection reason; a noncommandable actor keeps its own
  // reason and disables the row (it stays visible and unreachable).
  function actorItems(panel) {
    var byId = participantById(panelParticipants(panel));
    var status = draftStatus(panel);
    var currentActor = panel && panel.choices ? panel.choices.actor_id : null;
    var actors = (panel && panel.actors) || [];
    // Display names shared by two or more allied actors take the session
    // token (the stage's target-name convention), so same-name members stay
    // distinguishable in the selector.
    var nameCounts = {};
    actors.forEach(function (actor) {
      var row = byId[actor.identity] || {};
      var name = typeof row.display_name === "string" ? row.display_name : "";
      if (name) {
        nameCounts[name] = (nameCounts[name] || 0) + 1;
      }
    });
    var rows = [];
    actors.forEach(function (actor) {
      var row = byId[actor.identity] || {};
      var key = String(actor.identity);
      var name = typeof row.display_name === "string" ? row.display_name : "";
      var token = typeof row.token === "string" ? row.token : "";
      var label =
        (name && nameCounts[name] > 1 && token ? name + "（" + token + "）" : name) ||
        token ||
        key;
      var description = null;
      if (status.confirmed[key]) {
        description = "已確認";
      } else if (status.needs[key]) {
        description = "待選擇";
      }
      var reason = status.reasons[key] || null;
      if (reason && reason.message) {
        description = reason.message;
      }
      var item = {
        key: "actor-" + key,
        label: label,
        enabled: !!actor.commandable,
        actionId: null,
        payload: null,
        command: true,
        actorId: actor.identity,
        token: token || null,
        current: String(actor.identity) === String(currentActor),
        actorStatus: status.confirmed[key]
          ? "confirmed"
          : status.needs[key]
            ? "needs-selection"
            : "available",
        description: description,
      };
      if (!actor.commandable) {
        item.disabledReason =
          actor.reason || { code: "not_commandable", message: "無法指揮。" };
        // The binding fact for a noncommandable member is its server reason:
        // it takes precedence over the progress text (a reselection reason,
        // when the server authored one, already sits in `description`).
        if (!reason && item.disabledReason.message) {
          item.description = item.disabledReason.message;
        }
      }
      rows.push(item);
    });
    return rows;
  }

  // The compact current-actor/progress line the card chrome renders: the
  // commanded actor's display name and the authoritative draft counts
  // (confirmed required members, and how many still need a command).
  function progressLine(panel) {
    if (!panel || !panel.choices || !panel.draft) {
      return null;
    }
    var byId = participantById(panelParticipants(panel));
    var actorId = panel.choices.actor_id;
    var row = byId[actorId] || {};
    var name = typeof row.display_name === "string" ? row.display_name : "";
    var token = typeof row.token === "string" ? row.token : "";
    var shared =
      name &&
      ((panel.actors || []).filter(function (actor) {
        var other = byId[actor.identity] || {};
        return other.display_name === name;
      }).length > 1);
    return {
      actorId: actorId,
      actorLabel:
        (shared && token ? name + "（" + token + "）" : name) || token || String(actorId),
      confirmed: (panel.draft.entries || []).length,
      total: (panel.draft.required_actor_ids || []).length,
      needsSelection: (panel.draft.needs_selection_ids || []).length,
    };
  }

  // The exact v7 `combat.command` payload for one command: the committed
  // session/round/draft versions and the commanded actor are read here, at
  // submit time, so the envelope never carries a stale version. `command` is
  // the closed `{kind, payload}` union member. Null outside a ready session.
  function commandEnvelope(panel, command) {
    if (
      !panel ||
      !panel.session ||
      !panel.choices ||
      !panel.draft ||
      !command ||
      typeof command.kind !== "string"
    ) {
      return null;
    }
    return {
      session_id: panel.session.session_id,
      round_revision: panel.session.round_revision,
      draft_version: panel.draft.draft_version,
      actor_id: panel.choices.actor_id,
      command: command,
    };
  }

  // -------------------------------------------------------------------------
  // Item and basic-action frames (webclient-party-items-tactics).
  // -------------------------------------------------------------------------

  // The disabled explanation row of an item/tactic frame: the same shape the
  // skill frame's `skill-disabled` row uses (focusable, explanation readable,
  // nothing submitted).
  function disabledRow(key, label, reason) {
    return {
      key: key,
      label: label,
      description: reason ? reason.message : null,
      enabled: false,
      actionId: null,
      payload: null,
      disabledReason: reason || null,
    };
  }

  // The 道具 frame's rows: one per committed actor-local item choice, carrying
  // the item's current quantity, its effect summary (the detail pane's copy)
  // and its own committed disabled reason. Every row is a command row, so the
  // frame stays one vertical list.
  function itemRows(panel) {
    return panelItems(panel)
      .map(itemModel)
      .map(function (item) {
        var row = {
          key: "item-" + item.key,
          label: item.label + " ×" + item.quantity,
          description: item.summary !== "" ? item.summary : null,
          enabled: item.enabled,
          actionId: null,
          payload: null,
          command: true,
        };
        if (item.enabled) {
          row.actionId = "open-item";
          row.payload = { itemKey: item.key };
        } else {
          row.disabledReason = item.disabledReason;
        }
        return row;
      });
  }

  // One confirmation/target row of an item's frame. The command is the closed
  // v7 `{kind: "item", payload: {item_key[, target_id]}}` union member; the
  // session/round/draft versions and the commanded actor are added to the
  // envelope at submit time.
  function itemCommandRow(item, key, label, targetFields) {
    var payload = { item_key: item.key };
    Object.keys(targetFields || {}).forEach(function (field) {
      payload[field] = targetFields[field];
    });
    return {
      key: key,
      label: label,
      enabled: true,
      actionId: "combat.command",
      commandKind: "item",
      payload: payload,
      commandDisplay: { itemLabel: item.label },
    };
  }

  // Open one committed item's review/target frame: NONE submits no target
  // field and SELF submits no target field (the server binds the commanded
  // actor to the effect), SINGLE reuses the stage single-target step over the
  // item's own server-listed legal targets. `null` for an unknown item (the
  // resolver's identity-loss degradation).
  function openItem(combat, itemKey) {
    var item = combat.itemByKey ? combat.itemByKey[itemKey] : null;
    if (!item) {
      return null;
    }
    if (!item.enabled) {
      return {
        items: [disabledRow("item-disabled", item.label, item.disabledReason)],
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: "道具",
      };
    }
    if (item.targetSpec === "none") {
      return {
        items: [itemCommandRow(item, "none-confirm", "使用", {})],
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: "道具",
      };
    }
    if (item.targetSpec === "self") {
      return {
        items: [itemCommandRow(item, "self-confirm", "對自己使用", {})],
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: "道具",
      };
    }
    var valid = {};
    item.targets.forEach(function (identity) {
      valid[identity] = true;
    });
    var rows = [];
    combat.participants.forEach(function (participant) {
      if (!valid[participant.identity]) {
        return;
      }
      rows.push({
        key: "target-" + participant.identity,
        label: participant.display_name,
        description: participant.state === "active" ? null : participant.state,
        team: participant.team || null,
        enabled: true,
        actionId: "combat.command",
        commandKind: "item",
        payload: { item_key: item.key, target_id: participant.identity },
        commandDisplay: {
          itemLabel: item.label,
          targetLabel: participant.display_name,
        },
      });
    });
    if (rows.length === 0) {
      return {
        items: [
          disabledRow(
            "item-disabled",
            item.label,
            item.disabledReason || { code: "no_target", message: "沒有合法的目標。" }
          ),
        ],
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: "道具",
      };
    }
    return {
      items: rows,
      focusKey: null,
      grid: true,
      gridCols: 1,
      title: "目標",
    };
  }

  // Open one basic action's frame: 防禦 and 閃避 confirm the personal round
  // choice (a zero-cost round action — nothing is charged, applied or
  // consumed here), 挑釁 reuses the stage single-target step over the
  // server-listed living enemies. The command is the closed v7
  // `{kind: "tactic", payload: {key[, target_id]}}` union member: the panel
  // echoes an admitted entry back in its own `tactical` draft spelling.
  function tacticMenu(combat, key) {
    var tactic = combat.tacticByKey ? combat.tacticByKey[key] : null;
    if (!tactic) {
      return null;
    }
    var title = tactic.label || TACTIC_LABELS[key] || "戰術";
    if (!tactic.enabled) {
      return {
        items: [disabledRow("tactic-disabled", title, tactic.disabledReason)],
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: title,
      };
    }
    if (key !== "taunt") {
      return {
        items: [
          {
            key: "tactic-confirm",
            label: "確認" + title,
            enabled: true,
            actionId: "combat.command",
            commandKind: "tactic",
            payload: { key: key },
            commandDisplay: { tacticLabel: title },
          },
        ],
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: title,
      };
    }
    var rows = [];
    combat.participants.forEach(function (participant) {
      if (tactic.targets.indexOf(participant.identity) === -1) {
        return;
      }
      rows.push({
        key: "target-" + participant.identity,
        label: participant.display_name,
        description: participant.state === "active" ? null : participant.state,
        team: participant.team || null,
        enabled: true,
        actionId: "combat.command",
        commandKind: "tactic",
        payload: { key: "taunt", target_id: participant.identity },
        commandDisplay: {
          tacticLabel: title,
          targetLabel: participant.display_name,
        },
      });
    });
    if (rows.length === 0) {
      return {
        items: [
          disabledRow(
            "tactic-disabled",
            title,
            tactic.disabledReason || { code: "no_target", message: "沒有可挑釁的敵人。" }
          ),
        ],
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: title,
      };
    }
    return {
      items: rows,
      focusKey: null,
      grid: true,
      gridCols: 1,
      title: "目標",
    };
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

    var rootItemsList = rootItems(panel);
    var categoryItemsList = categoryItems(panel);
    // The combat root and the category frame are vertical command lists
    // (webclient-combat-command-window): one column, in every state.
    var menus = {
      root: {
        items: rootItemsList,
        focusKey: state.focusKey || null,
        grid: true,
        gridCols: 1,
        title: "戰鬥",
      },
      categories: {
        items: categoryItemsList,
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: "技能",
      },
      // The actor selector (webclient-party-command-selection): one row per
      // committed allied actor, in the server's order, focused on the
      // commanded one.
      actor: {
        items: actorItems(panel),
        focusKey:
          panel.choices && panel.choices.actor_id !== null && panel.choices.actor_id !== undefined
            ? "actor-" + panel.choices.actor_id
            : null,
        grid: true,
        gridCols: 1,
        title: "成員",
      },
      // The 道具 frame (webclient-party-items-tactics): the commanded actor's
      // own usable stock, one command row per committed item choice.
      items: {
        items: itemRows(panel),
        focusKey: null,
        grid: true,
        gridCols: 1,
        title: "道具",
      },
    };

    var skillByKey = {};
    skills.forEach(function (skill) {
      skillByKey[skill.key] = skill;
    });
    var itemByKey = {};
    panelItems(panel).forEach(function (row) {
      var item = itemModel(row);
      itemByKey[item.key] = item;
    });
    var tacticByKey = {};
    panelTactics(panel).forEach(function (row) {
      var tactic = tacticModel(row);
      tacticByKey[tactic.key] = tactic;
    });

    return {
      panel: panel,
      recovery: panel.session.state === "recovery",
      participants: participants,
      skills: skills,
      skillByKey: skillByKey,
      items: panelItems(panel).map(itemModel),
      itemByKey: itemByKey,
      tacticByKey: tacticByKey,
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
        title: "威力",
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
    // A SINGLE / self / none frame is one vertical column like the rest of
    // the command window (webclient-combat-command-window); the AREA frame
    // keeps its two-column token grid.
    return {
      items: targetItemsFor(skill, combat.participants),
      focusKey: null,
      skillKey: skillKey,
      grid: true,
      gridCols: skill.targetSpec === "area" ? 2 : 1,
      title: "目標",
    };
  }

  // Apply one confirmed scale choice to the focused skill.
  // The initial focus of basic attack's SINGLE target frame
  // (webclient-combat-command-window): the first enabled opposing candidate
  // the server listed, else the first enabled candidate, else null (the
  // frame keeps its default focus). Candidate order is never changed and
  // nothing is selected or submitted; every other skill returns null.
  function initialTargetKey(combat, skillKey) {
    var skill = combat && combat.skillByKey ? combat.skillByKey[skillKey] : null;
    if (!skill || skillKey !== BASIC_ATTACK_KEY || skill.targetSpec !== "single" || !skill.enabled) {
      return null;
    }
    var items = targetItemsFor(skill, combat.participants || []);
    var firstEnabled = null;
    for (var i = 0; i < items.length; i += 1) {
      if (items[i].enabled === false) {
        continue;
      }
      if (items[i].team === "foes") {
        return items[i].key;
      }
      if (firstEnabled === null) {
        firstEnabled = items[i].key;
      }
    }
    return firstEnabled;
  }

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
    PARTY_EXIT_OPERATIONS: PARTY_EXIT_OPERATIONS.slice(),
    PAGE_SIZE: PAGE_SIZE,
    BASIC_ATTACK_KEY: BASIC_ATTACK_KEY,
    rootItems: rootItems,
    partyExitRow: partyExitRow,
    partyExitPrompt: partyExitPrompt,
    actorItems: actorItems,
    progressLine: progressLine,
    commandEnvelope: commandEnvelope,
    buildMenus: buildMenus,
    categoryItems: categoryItems,
    groupItems: groupItems,
    groupSkillItems: groupSkillItems,
    openCategory: openCategory,
    openGroup: openGroup,
    openSkill: openSkill,
    openSkillTargets: openSkillTargets,
    openItem: openItem,
    tacticMenu: tacticMenu,
    initialTargetKey: initialTargetKey,
    chooseScale: chooseScale,
    scaleLabelFor: scaleLabelFor,
    toggleArea: toggleArea,
    chooseShorthand: chooseShorthand,
    areaPayload: areaPayload,
    rebuildForPanel: rebuildForPanel,
  };
});
