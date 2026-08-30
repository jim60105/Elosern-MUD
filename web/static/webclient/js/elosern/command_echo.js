/*
 * Elosern display-only command-line catalog.
 *
 * Resolves a button-triggered `ui_action` mutation into exactly one readable
 * display command line: `commandLine(actionId, payload, display)` returns a
 * bounded string or `null`. The `display` argument is a bounded descriptor of
 * server-authored labels attached to the menu item at build time (exit label,
 * NPC display name, keyword label, skill label, quantity, seconds/daypart), so
 * the catalog never guesses a name from an opaque id.
 *
 * The catalog is pure client presentation: it never submits, never replays,
 * never alters dispatch payloads, and never touches the transport. Command
 * spellings are pinned against `commands/*.py` by the Node suite; the three
 * actions without a typed command (`combat.flee`, exit traversal,
 * `creation.reset`) emit a bounded action label of the activating control as
 * an action description (the server exit label where the panel carries one,
 * a verbatim-pinned client-owned control label otherwise) and never invent a
 * command. Declared silent presentation controls (`options.dismiss`) return
 * `null` by declaration.
 *
 * No `document` or `window` access at load time; Node tests exercise the
 * module directly.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.CommandEcho = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Bounds: any server label is truncated before it is embedded, and the
  // full emitted line is bounded so a hostile label can never flood the log.
  var MAX_LABEL_LENGTH = 60;
  var MAX_LINE_LENGTH = 120;

  function isNonEmpty(value) {
    return typeof value === "string" && value.trim() !== "";
  }

  // Bounded single-line label: non-strings and oversized values degrade to
  // null (the catalog stays silent rather than fabricating a name).
  function label(value) {
    if (!isNonEmpty(value)) {
      return null;
    }
    var text = value.replace(/[\r\n\t]+/g, " ").trim();
    if (text.length > MAX_LABEL_LENGTH) {
      text = text.slice(0, MAX_LABEL_LENGTH);
    }
    return text;
  }

  // Bounded joined payload value (speech text): preserve the player's typed
  // speech inside the echoed line, collapsed and truncated.
  function payloadText(value) {
    if (typeof value !== "string") {
      return null;
    }
    var text = value.replace(/[\r\n\t]+/g, " ").trim();
    if (text === "") {
      return null;
    }
    if (text.length > MAX_LABEL_LENGTH) {
      text = text.slice(0, MAX_LABEL_LENGTH);
    }
    return text;
  }

  function join(parts) {
    return parts.filter(isNonEmpty).join(" ");
  }

  // Declared silent presentation controls (design D4): UI visibility
  // controls with no game action and no typed equivalent. `commandLine`
  // checks this list first, so the declaration and the silence share one
  // code path.
  var SILENT_PRESENTATION_CONTROLS = ["options.dismiss"];

  function isSilentPresentationControl(actionId) {
    return SILENT_PRESENTATION_CONTROLS.indexOf(actionId) !== -1;
  }

  // Resolver table: actionId -> (payload, display) => string | null. Every
  // resolver returns null when a descriptor it needs is missing.
  var RESOLVERS = {
    // Evennia's stock `look` command: bare for the room, named for a target.
    "explore.look": function (payload, display) {
      if (display && display.room) {
        return "look";
      }
      var target = label(display && display.targetLabel);
      return target === null ? null : join(["look", target]);
    },
    "explore.talk_scripted": function (payload, display) {
      var npc = label(display && display.npcLabel);
      var keyword = label(display && display.keywordLabel);
      if (npc === null || keyword === null) {
        return null;
      }
      return join(["talk", npc, keyword]);
    },
    "explore.talk_freeform": function (payload, display) {
      var npc = label(display && display.npcLabel);
      var speech = payloadText(payload && payload.speech);
      if (npc === null || speech === null) {
        return null;
      }
      return join(["talk", npc, speech]);
    },
    "explore.party_invite": function (payload, display) {
      var npc = label(display && display.npcLabel);
      if (npc === null) {
        return null;
      }
      var message = payloadText(payload && payload.message);
      return message === null
        ? join(["invite", npc])
        : join(["invite", npc, message]);
    },
    "explore.party_leave": function (payload, display) {
      var npc = label(display && display.npcLabel);
      return npc === null ? null : join(["leave", npc]);
    },
    "explore.engage": function (payload, display) {
      var target = label(display && display.targetLabel);
      return target === null ? null : join(["engage", target]);
    },
    "explore.wait": function (payload, display) {
      if (payload && payload.sleep) {
        return "sleep";
      }
      if (isNonEmpty(payload && payload.daypart)) {
        return join(["wait until", payload.daypart]);
      }
      var seconds = payload && payload.seconds;
      if (typeof seconds === "number" && seconds >= 0) {
        return join(["rest", String(seconds) + "s"]);
      }
      // The descriptor carries the server-authored wait label; nothing here
      // invents a daypart or duration.
      var fallback = label(display && display.waitLabel);
      return fallback;
    },
    // Exit traversal has no `move` command; the exit's server label is the
    // documented action description, never a guessed command.
    "explore.move": function (payload, display) {
      return label(display && display.exitLabel);
    },
    "combat.cast": function (payload, display) {
      var skill = label(display && display.skillLabel);
      if (skill === null) {
        return null;
      }
      var target = null;
      if (isNonEmpty(payload && payload.target_shorthand)) {
        target = payload.target_shorthand;
      } else if (isNonEmpty(display && display.targetLabel)) {
        target = display.targetLabel;
      } else if (Array.isArray(display && display.targetLabels)) {
        // D3b: explicit multi-target AREA payloads echo every selected
        // participant label in payload order (bounded, joined with 、).
        var names = display.targetLabels
          .map(label)
          .filter(isNonEmpty);
        if (names.length > 0) {
          target = names.join("、");
        }
      }
      // The chosen freeform magnitude is echoed as a display-only suffix
      // (e.g. 「施展 風刃術（威力×2）」), composed from the server-authored
      // canonical scale label carried by the menu descriptor.
      var scaleSuffix = label(display && display.scaleLabel);
      var skillPart = scaleSuffix === null
        ? skill
        : skill + "（威力×" + scaleSuffix + "）";
      return target === null
        ? join(["cast", skillPart])
        : join(["cast", skillPart + "=" + target]);
    },
    "combat.forfeit": function () {
      return "combat forfeit";
    },
    // No typed flee command exists; the server-authored button label is the
    // action description (design decision, pinned by the Node suite).
    "combat.flee": function (payload, display) {
      return label(display && display.actionLabel);
    },
    "guild.register": function () {
      return "guild register";
    },
    "guild.quest_accept": function (payload) {
      var key = payload && payload.definition_key;
      return isNonEmpty(key) ? join(["guild accept", key]) : null;
    },
    "guild.quest_abandon": function (payload) {
      var id = payload && payload.quest_id;
      return isNonEmpty(id) ? join(["guild abandon", id]) : null;
    },
    "guild.quest_turnin": function (payload) {
      var id = payload && payload.quest_id;
      return isNonEmpty(id) ? join(["guild turnin", id]) : null;
    },
    "guild.exam_start": function (payload) {
      var rank = payload && payload.target_rank;
      return isNonEmpty(rank) ? join(["guild exam", rank]) : "guild exam";
    },
    "shop.buy": function (payload, display) {
      var item = label(display && display.itemLabel);
      var quantity = payload && payload.quantity;
      if (item === null || typeof quantity !== "number" || quantity < 1) {
        return null;
      }
      return join(["buy", item, String(quantity)]);
    },
    "shop.sell": function (payload, display) {
      var item = label(display && display.itemLabel);
      var quantity = payload && payload.quantity;
      if (item === null || typeof quantity !== "number" || quantity < 1) {
        return null;
      }
      return join(["sell", item, String(quantity)]);
    },
    // The backpack surface echoes the keyboard it teaches: the typed
    // `使用`/`use` and `裝備`/`equip` commands (commands/items.py) accept the
    // literal `item_key` as their first argument, so the line is exactly
    // what the keyboard replays. `裝備`/`equip` IS the equipment toggle —
    // both directions echo `equip` (design D1/D2; no typed `unequip` exists).
    "inventory.use": function (payload) {
      var key = label(payload && payload.item_key);
      return key === null ? null : join(["use", key]);
    },
    "inventory.toggle_equip": function (payload) {
      var key = label(payload && payload.item_key);
      return key === null ? null : join(["equip", key]);
    },
    // Ballot answers replay the typed `title accept <編號>` / `title decline`
    // commands (commands/title.py) verbatim: the numbered choice only, never
    // free text. A missing or out-of-cap index stays silent.
    "title.accept": function (payload) {
      var index = payload && payload.index;
      if (
        typeof index !== "number" ||
        !Number.isInteger(index) ||
        index < 1 ||
        index > 3
      ) {
        return null;
      }
      return join(["title", "accept", String(index)]);
    },
    "title.decline": function () {
      return "title decline";
    },
    "creation.preset": function (payload) {
      var key = payload && payload.preset_key;
      return isNonEmpty(key) ? join(["character preset", key]) : null;
    },
    "creation.custom": function () {
      return "character create";
    },
    "creation.concept": function (payload) {
      var concept = payload && payload.concept;
      return isNonEmpty(concept) ? join(["character concept", concept]) : null;
    },
    // The wizard's activation step re-runs the chosen draft path; the reset
    // control has no typed equivalent and falls back to its button label.
    "creation.activate": function (payload, display) {
      var key = display && display.presetKey;
      return isNonEmpty(key) ? join(["character preset", key]) : "character create";
    },
    "creation.reset": function (payload, display) {
      return label(display && display.actionLabel);
    },
  };

  function commandLine(actionId, payload, display) {
    if (typeof actionId !== "string") {
      return null;
    }
    if (isSilentPresentationControl(actionId)) {
      return null;
    }
    var resolve = RESOLVERS[actionId];
    if (!resolve) {
      return null;
    }
    var line = resolve(payload || {}, display || {});
    if (!isNonEmpty(line)) {
      return null;
    }
    if (line.length > MAX_LINE_LENGTH) {
      line = line.slice(0, MAX_LINE_LENGTH);
    }
    return line;
  }

  return {
    commandLine: commandLine,
    isSilentPresentationControl: isSilentPresentationControl,
    SILENT_PRESENTATION_CONTROLS: SILENT_PRESENTATION_CONTROLS.slice(),
    MAX_LABEL_LENGTH: MAX_LABEL_LENGTH,
    MAX_LINE_LENGTH: MAX_LINE_LENGTH,
  };
});
