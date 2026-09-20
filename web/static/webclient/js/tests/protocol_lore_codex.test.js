/*
 * lore_codex panel v1 mirror: categories, payloads, rejections.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_LORE_PLACE, T_LORE_PLACE_TITLE, VALID_EPOCH, serverTime } = require("./protocol_support.js");


function validLoreCodexCategory(key, label, entries) {
  return {
    key: key,
    label: label,
    count: entries ? entries.length : 0,
    entries: entries || [],
  };
}

function validLoreCodexPayload(overrides) {
  var categories = [
    validLoreCodexCategory("race", "種族", [
      {
        key: "elf",
        title: "精靈",
        card: [
          { name: "key", value: "elf" },
          { name: "description", value: "長壽種族" },
        ],
      },
    ]),
    validLoreCodexCategory("nation", "國家", []),
    validLoreCodexCategory("region", "地域", []),
    validLoreCodexCategory("monster", "魔物", []),
    validLoreCodexCategory("element", "元素", []),
    validLoreCodexCategory("magic", "魔法", []),
    validLoreCodexCategory("anchor", "地點", [
      {
        key: T_LORE_PLACE,
        title: T_LORE_PLACE_TITLE,
        card: [
          { name: "display_name_zh", value: T_LORE_PLACE_TITLE },
          { name: "description", value: "帝國首都" },
        ],
      },
    ]),
    validLoreCodexCategory("guild", "公會", []),
  ];
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      categories: categories,
      discovered_total: 2,
    },
    overrides
  );
}

test("lore_codex pins bounds and validates available and empty payloads", () => {
  assert.equal(Protocol.LORE_CODEX_SCHEMA_VERSION, 1);
  assert.equal(Protocol.LORE_CODEX_MAX_ENTRIES_PER_CATEGORY, 32);
  assert.equal(Protocol.LORE_CODEX_MAX_TOTAL_ENTRIES, 256);
  assert.equal(Protocol.LORE_CODEX_MAX_CARD_FIELDS, 8);

  const payload = validLoreCodexPayload();
  const normalized = Protocol.validateLoreCodexPanel(payload);
  assert.equal(normalized.schema_version, 1);
  assert.equal(normalized.available, true);
  assert.equal(normalized.discovered_total, 2);
  assert.equal(normalized.categories.length, 8);
  assert.equal(normalized.categories[0].entries[0].title, "精靈");

  // Empty codex
  const emptyCategories = [
    validLoreCodexCategory("race", "種族", []),
    validLoreCodexCategory("nation", "國家", []),
    validLoreCodexCategory("region", "地域", []),
    validLoreCodexCategory("monster", "魔物", []),
    validLoreCodexCategory("element", "元素", []),
    validLoreCodexCategory("magic", "魔法", []),
    validLoreCodexCategory("anchor", "地點", []),
    validLoreCodexCategory("guild", "公會", []),
  ];
  const emptyPayload = {
    schema_version: 1,
    available: true,
    categories: emptyCategories,
    discovered_total: 0,
  };
  const emptyNormalized = Protocol.validateLoreCodexPanel(emptyPayload);
  assert.equal(emptyNormalized.discovered_total, 0);
});

test("lore_codex rejects wrong category order, extra category, and missing category", () => {
  // Missing category (only 7)
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories = payload.categories.slice(0, 7);
    payload.discovered_total = 2;
    Protocol.validateLoreCodexPanel(payload);
  });

  // Extra ninth category
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories = payload.categories.concat([
      validLoreCodexCategory("extra", "額外", []),
    ]);
    Protocol.validateLoreCodexPanel(payload);
  });

  // Reordered categories (nation before race)
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    const swapped = payload.categories.slice();
    const temp = swapped[0];
    swapped[0] = swapped[1];
    swapped[1] = temp;
    payload.categories = swapped;
    Protocol.validateLoreCodexPanel(payload);
  });
});

test("lore_codex rejects count and discovered_total mismatches", () => {
  // count mismatch in category group
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].count = 99;
    Protocol.validateLoreCodexPanel(payload);
  });

  // discovered_total mismatch
  assert.throws(() => {
    const payload = validLoreCodexPayload({ discovered_total: 99 });
    Protocol.validateLoreCodexPanel(payload);
  });
});

test("lore_codex rejects extra fields and empty names/titles", () => {
  // extra top-level field
  assert.throws(() =>
    Protocol.validateLoreCodexPanel(validLoreCodexPayload({ extra: "bad" }))
  );

  // extra entry field
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].extra = "bad";
    Protocol.validateLoreCodexPanel(payload);
  });

  // extra card field
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].card[0].extra = "bad";
    Protocol.validateLoreCodexPanel(payload);
  });

  // empty title
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].title = "   ";
    Protocol.validateLoreCodexPanel(payload);
  });

  // empty card field name
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].card[0].name = " ";
    Protocol.validateLoreCodexPanel(payload);
  });
});

test("lore_codex rejects lone surrogates in all string fields", () => {
  // lone surrogate in key
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].key = "bad\ud800key";
    Protocol.validateLoreCodexPanel(payload);
  });

  // lone surrogate in title
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].title = "bad\ud800title";
    Protocol.validateLoreCodexPanel(payload);
  });

  // lone surrogate in category label
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].label = "bad\ud800label";
    Protocol.validateLoreCodexPanel(payload);
  });

  // lone surrogate in card field name
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].card[0].name = "bad\ud800name";
    Protocol.validateLoreCodexPanel(payload);
  });

  // lone surrogate in card field value
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].card[0].value = "bad\ud800value";
    Protocol.validateLoreCodexPanel(payload);
  });
});

test("lore_codex is in panel allowlist and validates in snapshots and unavailable forms", () => {
  const validAvailable = validLoreCodexPayload();
  const unavailable = {
    schema_version: 1,
    available: false,
    reason: { code: "lore_codex_unavailable", message: "知識圖鑑目前無法顯示" },
  };

  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "exploration",
    panels: { lore_codex: validAvailable },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));

  envelope.panels = { lore_codex: unavailable };
  envelope.revision = 2;
  assert.doesNotThrow(() => Protocol.validateUpdate(envelope));

  assert.deepEqual(
    Protocol.validatePanel("lore_codex", Protocol.PANEL_ALLOWLIST.lore_codex, unavailable),
    unavailable
  );
});

test("lore_codex rejects string fields one code point over the bound", () => {
  // Title over bound
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].title = "字".repeat(
      Protocol.LORE_CODEX_MAX_TITLE_CODE_POINTS + 1
    );
    Protocol.validateLoreCodexPanel(payload);
  });

  // Category label over bound
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].label = "字".repeat(
      Protocol.LORE_CODEX_MAX_LABEL_CODE_POINTS + 1
    );
    Protocol.validateLoreCodexPanel(payload);
  });

  // Card field name over bound
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].card[0].name = "n".repeat(
      Protocol.LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS + 1
    );
    Protocol.validateLoreCodexPanel(payload);
  });

  // Card field value over bound
  assert.throws(() => {
    const payload = validLoreCodexPayload();
    payload.categories[0].entries[0].card[0].value = "v".repeat(
      Protocol.LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS + 1
    );
    Protocol.validateLoreCodexPanel(payload);
  });
});
