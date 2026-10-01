/*
 * Exact JavaScript mirror of the compact NPC character card contract (D6).
 * Pure normalization, code-point counting, and validation matching world.lore.npc_card.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.NpcPersonaCard = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var NPC_CARD_FORMAT = 1;
  var NPC_PERSONA_CONTENT_GENERATION = 1;

  var LEAF_LIMIT = 600;
  var IDENTITY_SECTION_LIMIT = 600;
  var CARD_BLOCK_LIMIT = 2000;

  var NPC_CARD_FIELDS = [
    "identity",
    "appearance",
    "personality",
    "speech_style",
    "life_story",
    "habit",
    "social_connection",
  ];

  var NPC_CARD_RENDER_ORDER = [
    "identity",
    "appearance",
    "personality",
    "speech_style",
    "life_story",
    "habit",
    "social_connection",
  ];

  var REQUIRED_TEXT_LEAVES = [
    "identity.public",
    "appearance",
    "personality",
    "speech_style",
    "life_story",
    "habit",
  ];

  var OPTIONAL_TEXT_LEAVES = [
    "identity.hidden",
    "social_connection",
  ];

  var CARD_FIELD_LABELS = {
    identity: "身分：",
    appearance: "外觀：",
    personality: "性格：",
    speech_style: "說話風格：",
    life_story: "生平：",
    habit: "習慣：",
    social_connection: "人際關係：",
  };

  var IDENTITY_PUBLIC_LABEL = "公開：";
  var IDENTITY_HIDDEN_LABEL = "隱秘：";

  var CRLF_REGEX = /\r\n|\r/g;

  function countCodePoints(str) {
    if (typeof str !== "string") {
      return 0;
    }
    return Array.from(str).length;
  }

  function normalizeText(text) {
    if (typeof text !== "string") {
      return "";
    }
    return text.replace(CRLF_REGEX, "\n").trim();
  }

  function normalizeCard(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      var err = new Error("card_not_object");
      err.code = "card_not_object";
      err.field = null;
      throw err;
    }

    var keys = Object.keys(raw).sort();
    var expectedKeys = NPC_CARD_FIELDS.slice().sort();
    if (keys.length !== expectedKeys.length || !keys.every(function (k, i) { return k === expectedKeys[i]; })) {
      for (var i = 0; i < expectedKeys.length; i++) {
        if (!(expectedKeys[i] in raw)) {
          var missingErr = new Error("missing_field: " + expectedKeys[i]);
          missingErr.code = "missing_field";
          missingErr.field = expectedKeys[i];
          throw missingErr;
        }
      }
      for (var j = 0; j < keys.length; j++) {
        if (expectedKeys.indexOf(keys[j]) === -1) {
          var unknownErr = new Error("unknown_field: " + keys[j]);
          unknownErr.code = "unknown_field";
          unknownErr.field = keys[j];
          throw unknownErr;
        }
      }
    }

    var identityRaw = raw.identity;
    if (!identityRaw || typeof identityRaw !== "object" || Array.isArray(identityRaw)) {
      var notTxtId = new Error("not_text: identity");
      notTxtId.code = "not_text";
      notTxtId.field = "identity";
      throw notTxtId;
    }

    var idKeys = Object.keys(identityRaw).sort();
    var expectedIdKeys = ["hidden", "public"];
    if (idKeys.length !== expectedIdKeys.length || !idKeys.every(function (k, i) { return k === expectedIdKeys[i]; })) {
      for (var ik = 0; ik < expectedIdKeys.length; ik++) {
        if (!(expectedIdKeys[ik] in identityRaw)) {
          var idMissing = new Error("missing_field: identity." + expectedIdKeys[ik]);
          idMissing.code = "missing_field";
          idMissing.field = "identity." + expectedIdKeys[ik];
          throw idMissing;
        }
      }
      for (var jk = 0; jk < idKeys.length; jk++) {
        if (expectedIdKeys.indexOf(idKeys[jk]) === -1) {
          var idUnknown = new Error("unknown_field: identity." + idKeys[jk]);
          idUnknown.code = "unknown_field";
          idUnknown.field = "identity." + idKeys[jk];
          throw idUnknown;
        }
      }
    }

    if (typeof identityRaw.public !== "string") {
      var pubErr = new Error("not_text: identity.public");
      pubErr.code = "not_text";
      pubErr.field = "identity.public";
      throw pubErr;
    }
    if (typeof identityRaw.hidden !== "string") {
      var hidErr = new Error("not_text: identity.hidden");
      hidErr.code = "not_text";
      hidErr.field = "identity.hidden";
      throw hidErr;
    }

    var normPublic = normalizeText(identityRaw.public);
    var normHidden = normalizeText(identityRaw.hidden);

    if (countCodePoints(normPublic) === 0) {
      var reqPub = new Error("required_empty: identity.public");
      reqPub.code = "required_empty";
      reqPub.field = "identity.public";
      throw reqPub;
    }

    if (countCodePoints(normPublic) > LEAF_LIMIT) {
      var pubLimit = new Error("leaf_too_long: identity.public");
      pubLimit.code = "leaf_too_long";
      pubLimit.field = "identity.public";
      throw pubLimit;
    }

    if (countCodePoints(normHidden) > LEAF_LIMIT) {
      var hidLimit = new Error("leaf_too_long: identity.hidden");
      hidLimit.code = "leaf_too_long";
      hidLimit.field = "identity.hidden";
      throw hidLimit;
    }

    // Check identity section total rendered length
    var renderedId = CARD_FIELD_LABELS.identity + "\n  " + IDENTITY_PUBLIC_LABEL + normPublic;
    if (normHidden.length > 0) {
      renderedId += "\n  " + IDENTITY_HIDDEN_LABEL + normHidden;
    }
    if (countCodePoints(renderedId) > IDENTITY_SECTION_LIMIT) {
      var idSecLimit = new Error("identity_section_too_long: identity");
      idSecLimit.code = "identity_section_too_long";
      idSecLimit.field = "identity";
      throw idSecLimit;
    }

    var normalized = {
      identity: {
        public: normPublic,
        hidden: normHidden,
      },
    };

    for (var f = 0; f < NPC_CARD_FIELDS.length; f++) {
      var fKey = NPC_CARD_FIELDS[f];
      if (fKey === "identity") continue;
      var val = raw[fKey];
      if (typeof val !== "string") {
        var notTxt = new Error("not_text: " + fKey);
        notTxt.code = "not_text";
        notTxt.field = fKey;
        throw notTxt;
      }
      var normVal = normalizeText(val);
      if (OPTIONAL_TEXT_LEAVES.indexOf(fKey) === -1 && countCodePoints(normVal) === 0) {
        var reqEmp = new Error("required_empty: " + fKey);
        reqEmp.code = "required_empty";
        reqEmp.field = fKey;
        throw reqEmp;
      }
      if (countCodePoints(normVal) > LEAF_LIMIT) {
        var lfLimit = new Error("leaf_too_long: " + fKey);
        lfLimit.code = "leaf_too_long";
        lfLimit.field = fKey;
        throw lfLimit;
      }
      normalized[fKey] = normVal;
    }

    // Check card total rendered block length
    var renderedBlock = renderCardBlock(normalized);
    if (countCodePoints(renderedBlock) > CARD_BLOCK_LIMIT) {
      var totalLimit = new Error("card_too_long");
      totalLimit.code = "card_too_long";
      totalLimit.field = null;
      throw totalLimit;
    }

    return normalized;
  }

  function renderCardBlock(card) {
    var lines = [];
    lines.push(CARD_FIELD_LABELS.identity);
    lines.push("  " + IDENTITY_PUBLIC_LABEL + card.identity.public);
    if (card.identity.hidden && card.identity.hidden.length > 0) {
      lines.push("  " + IDENTITY_HIDDEN_LABEL + card.identity.hidden);
    }

    for (var i = 0; i < NPC_CARD_RENDER_ORDER.length; i++) {
      var key = NPC_CARD_RENDER_ORDER[i];
      if (key === "identity") continue;
      var val = card[key];
      if (val && val.length > 0) {
        lines.push(CARD_FIELD_LABELS[key] + val);
      }
    }
    return lines.join("\n");
  }

  function cardBudget(card) {
    var perLeaf = {
      "identity.public": countCodePoints(card.identity.public),
      "identity.hidden": countCodePoints(card.identity.hidden),
      appearance: countCodePoints(card.appearance),
      personality: countCodePoints(card.personality),
      speech_style: countCodePoints(card.speech_style),
      life_story: countCodePoints(card.life_story),
      habit: countCodePoints(card.habit),
      social_connection: countCodePoints(card.social_connection),
    };

    var renderedId = CARD_FIELD_LABELS.identity + "\n  " + IDENTITY_PUBLIC_LABEL + card.identity.public;
    if (card.identity.hidden.length > 0) {
      renderedId += "\n  " + IDENTITY_HIDDEN_LABEL + card.identity.hidden;
    }
    var idTotal = countCodePoints(renderedId);

    var rendered = renderCardBlock(card);
    var total = countCodePoints(rendered);

    return {
      per_leaf: perLeaf,
      identity_section: idTotal,
      total: total,
      remaining_total: Math.max(0, CARD_BLOCK_LIMIT - total),
      remaining_identity_section: Math.max(0, IDENTITY_SECTION_LIMIT - idTotal),
    };
  }

  return {
    NPC_CARD_FORMAT: NPC_CARD_FORMAT,
    NPC_PERSONA_CONTENT_GENERATION: NPC_PERSONA_CONTENT_GENERATION,
    LEAF_LIMIT: LEAF_LIMIT,
    IDENTITY_SECTION_LIMIT: IDENTITY_SECTION_LIMIT,
    CARD_BLOCK_LIMIT: CARD_BLOCK_LIMIT,
    NPC_CARD_FIELDS: NPC_CARD_FIELDS,
    NPC_CARD_RENDER_ORDER: NPC_CARD_RENDER_ORDER,
    REQUIRED_TEXT_LEAVES: REQUIRED_TEXT_LEAVES,
    OPTIONAL_TEXT_LEAVES: OPTIONAL_TEXT_LEAVES,
    CARD_FIELD_LABELS: CARD_FIELD_LABELS,
    countCodePoints: countCodePoints,
    normalizeText: normalizeText,
    normalizeCard: normalizeCard,
    renderCardBlock: renderCardBlock,
    cardBudget: cardBudget,
  };
});
