/*
 * lore_codex panel v2 mirror: categories, groups, slots, rejections.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_LORE_PLACE, T_LORE_PLACE_TITLE, VALID_EPOCH, serverTime } = require("./protocol_support.js");
const { validArtwork } = require("./protocol_fixtures.js");

const LABELS = {
  race: "種族",
  nation: "國家",
  region: "地域",
  monster: "魔物",
  element: "元素",
  magic: "魔法",
  anchor: "地點",
  guild: "公會",
};

function placeholder() {
  return { placeholder: true };
}

function entry(key, title, extra) {
  return Object.assign(
    {
      key: key,
      title: title,
      stage: null,
      art: null,
      card: [
        { name: "display_name_zh", value: title },
        { name: "description", value: "合成描述" },
      ],
      locked_fields: [],
    },
    extra || {}
  );
}

function monsterEntry(stage) {
  return entry("t_beast", "合成獸", {
    stage: stage,
    card: [
      { name: "display_name_zh", value: "合成獸" },
      { name: "threat_tier", value: "合成級" },
    ],
    locked_fields: stage === "sighted" ? ["published_description_zh", "variants"] : [],
  });
}

function category(key, slots, groups) {
  const allGroups = groups || [{ key: key, label: null, slots: slots }];
  const allSlots = allGroups.flatMap((group) => group.slots);
  return {
    key: key,
    label: LABELS[key],
    discovered: allSlots.filter((slot) => !slot.placeholder).length,
    total: allSlots.length,
    groups: allGroups,
  };
}

function rebalance(payload) {
  payload.categories.forEach((cat) => {
    const slots = cat.groups.flatMap((group) => group.slots);
    cat.discovered = slots.filter((slot) => !slot.placeholder).length;
    cat.total = Math.max(cat.total, slots.length);
  });
  payload.discovered_total = payload.categories.reduce((sum, cat) => sum + cat.discovered, 0);
  payload.total = payload.categories.reduce((sum, cat) => sum + cat.total, 0);
  return payload;
}

function validLoreCodexPayload(overrides) {
  const categories = [
    category("race", [entry("t_duskmari", "暮色族裔"), placeholder()]),
    category("nation", [placeholder()]),
    category("region", [placeholder(), placeholder()]),
    category("monster", null, [
      { key: "t_tier_a", label: "甲級", slots: [monsterEntry("sighted"), placeholder()] },
      { key: "t_tier_b", label: "乙級", slots: [placeholder()] },
    ]),
    category("element", [placeholder()]),
    category("magic", []),
    category("anchor", [entry(T_LORE_PLACE, T_LORE_PLACE_TITLE)]),
    category("guild", [entry("t_rank", "合成階級", { art: validArtwork() })]),
  ];
  return Object.assign(
    rebalance({
      schema_version: 2,
      available: true,
      discovered_total: 0,
      total: 0,
      categories: categories,
    }),
    overrides
  );
}

function raceEntry(payload) {
  return payload.categories[0].groups[0].slots[0];
}

function monster(payload) {
  return payload.categories[3];
}

function rejects(edit) {
  const payload = validLoreCodexPayload();
  edit(payload);
  assert.throws(() => Protocol.validateLoreCodexPanel(payload));
}

test("lore_codex v2 accepts a valid payload and preserves slots in order", () => {
  const normalized = Protocol.validateLoreCodexPanel(validLoreCodexPayload());
  assert.equal(normalized.schema_version, 2);
  assert.equal(normalized.available, true);
  assert.equal(normalized.discovered_total, 4);
  assert.equal(normalized.total, 11);
  assert.deepEqual(
    normalized.categories.flatMap((cat) =>
      cat.groups.flatMap((group) => group.slots.map((slot) => [cat.key, slot.key || null]))
    ),
    [
      ["race", "t_duskmari"],
      ["race", null],
      ["nation", null],
      ["region", null],
      ["region", null],
      ["monster", "t_beast"],
      ["monster", null],
      ["monster", null],
      ["element", null],
      ["anchor", T_LORE_PLACE],
      ["guild", "t_rank"],
    ]
  );
  assert.deepEqual(normalized.categories[0].groups[0].slots[1], { placeholder: true });
});

test("lore_codex v2 accepts a monster category without groups and emptied groups", () => {
  const payload = validLoreCodexPayload();
  payload.categories[3] = category("monster", null, []);
  Protocol.validateLoreCodexPanel(rebalance(payload));
  const trimmed = validLoreCodexPayload();
  trimmed.categories[1].groups[0].slots = [];
  Protocol.validateLoreCodexPanel(trimmed);
});

test("lore_codex v2 rejects a wrong schema version and the removed v1 fields", () => {
  rejects((p) => (p.schema_version = 1));
  rejects((p) => (p.available = false));
  rejects((p) => (p.categories[0].count = 1));
  rejects((p) => (p.categories[0].entries = []));
  rejects((p) => delete p.total);
});

test("lore_codex v2 rejects a ninth, missing or reordered category", () => {
  rejects((p) => p.categories.push(category("race", [])));
  rejects((p) => (p.categories = p.categories.slice(0, 7)));
  rejects((p) => {
    const first = p.categories[0];
    p.categories[0] = p.categories[1];
    p.categories[1] = first;
  });
});

test("lore_codex v2 rejects an identifying placeholder", () => {
  for (const extra of [{ key: "t_hidden" }, { title: "隱藏" }, { art: null }, { stage: null }]) {
    rejects((p) => Object.assign(p.categories[0].groups[0].slots[1], extra));
  }
  rejects((p) => (p.categories[0].groups[0].slots[1].placeholder = 1));
});

test("lore_codex v2 rejects count mismatches and a slot count above total", () => {
  rejects((p) => (p.categories[0].discovered = 2));
  rejects((p) => (p.categories[0].total = 1));
  rejects((p) => (p.discovered_total = 99));
  rejects((p) => (p.total = 99));
  // A total above the shipped slots (a trimmed view) stays legal.
  const trimmed = validLoreCodexPayload();
  trimmed.categories[0].total += 3;
  trimmed.total += 3;
  Protocol.validateLoreCodexPanel(trimmed);
});

test("lore_codex v2 rejects extra fields at every level", () => {
  rejects((p) => (p.extra = 1));
  rejects((p) => (p.categories[0].extra = 1));
  rejects((p) => (p.categories[0].groups[0].extra = 1));
  rejects((p) => (raceEntry(p).extra = 1));
  rejects((p) => (raceEntry(p).card[0].extra = 1));
});

test("lore_codex v2 enforces the group rules per category", () => {
  rejects((p) => p.categories[0].groups.push({ key: "t_more", label: null, slots: [] }));
  rejects((p) => (p.categories[0].groups[0].label = "標籤"));
  rejects((p) => (monster(p).groups[0].label = null));
  rejects((p) => (monster(p).groups[1].key = "t_tier_a"));
  for (const key of ["", "t:tier", "k".repeat(Protocol.LORE_CODEX_MAX_KEY_CODE_POINTS + 1)]) {
    rejects((p) => (monster(p).groups[0].key = key));
  }
  rejects((p) => {
    monster(p).groups = [];
    for (let i = 0; i <= Protocol.LORE_CODEX_MAX_GROUPS_PER_CATEGORY; i++) {
      monster(p).groups.push({ key: "t_tier_" + i, label: "級", slots: [] });
    }
    rebalance(p);
  });
});

test("lore_codex v2 enforces the stage rules", () => {
  rejects((p) => (monster(p).groups[0].slots[0].stage = null));
  rejects((p) => (raceEntry(p).stage = "sighted"));
  const defeated = validLoreCodexPayload();
  monster(defeated).groups[0].slots[0] = monsterEntry("defeated");
  Protocol.validateLoreCodexPanel(defeated);
});

test("lore_codex v2 enforces the locked field rules", () => {
  rejects((p) => (monster(p).groups[0].slots[0].stage = "defeated"));
  rejects((p) => (monster(p).groups[0].slots[0].locked_fields = ["threat_tier"]));
  rejects((p) => (monster(p).groups[0].slots[0].locked_fields = ["variants", "variants"]));
  rejects((p) => {
    const locked = [];
    for (let i = 0; i <= Protocol.LORE_CODEX_MAX_CARD_FIELDS; i++) locked.push("t_locked_" + i);
    monster(p).groups[0].slots[0].locked_fields = locked;
  });
  rejects((p) => (raceEntry(p).locked_fields = ["description_more"]));
});

test("lore_codex v2 bounds the variant lines", () => {
  const payload = validLoreCodexPayload();
  const slot = monster(payload).groups[0].slots[0];
  slot.stage = "defeated";
  slot.locked_fields = [];
  slot.card.push({
    name: "variants",
    value: new Array(Protocol.LORE_CODEX_MAX_VARIANT_LINES).fill("型").join("\n"),
  });
  Protocol.validateLoreCodexPanel(payload);
  slot.card[slot.card.length - 1].value += "\n型";
  assert.throws(() => Protocol.validateLoreCodexPanel(payload));
});

test("lore_codex v2 enforces the card rules", () => {
  rejects((p) => {
    const card = [];
    for (let i = 0; i <= Protocol.LORE_CODEX_MAX_CARD_FIELDS; i++) card.push({ name: "f_" + i, value: "v" });
    raceEntry(p).card = card;
  });
  rejects((p) => (raceEntry(p).card[1].name = "display_name_zh"));
});

test("lore_codex v2 rejects malformed and duplicate entry keys", () => {
  for (const key of [null, 42, "", ":entry", "entry:other", "entry:", "bad\ud800key"]) {
    rejects((p) => (raceEntry(p).key = key));
  }
  rejects((p) => {
    p.categories[0].groups[0].slots[1] = entry("t_duskmari", "重複");
    rebalance(p);
  });
});

test("lore_codex v2 accepts a valid art descriptor and rejects a malformed one", () => {
  rejects((p) => (raceEntry(p).art = { subject_id: "t" }));
});

test("lore_codex v2 rejects empty and lone-surrogate strings", () => {
  rejects((p) => (raceEntry(p).title = "   "));
  rejects((p) => (raceEntry(p).title = "bad\ud800title"));
  rejects((p) => (raceEntry(p).card[0].name = " "));
  rejects((p) => (raceEntry(p).card[0].name = "bad\ud800name"));
  rejects((p) => (raceEntry(p).card[0].value = "bad\ud800value"));
  rejects((p) => (p.categories[0].label = ""));
  rejects((p) => (p.categories[0].label = "bad\ud800label"));
});

test("lore_codex v2 rejects string fields one code point over the bound", () => {
  rejects((p) => (raceEntry(p).key = "k".repeat(Protocol.LORE_CODEX_MAX_KEY_CODE_POINTS + 1)));
  rejects((p) => (raceEntry(p).title = "字".repeat(Protocol.LORE_CODEX_MAX_TITLE_CODE_POINTS + 1)));
  rejects((p) => (p.categories[0].label = "字".repeat(Protocol.LORE_CODEX_MAX_LABEL_CODE_POINTS + 1)));
  rejects((p) => (raceEntry(p).card[0].name = "n".repeat(Protocol.LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS + 1)));
  rejects((p) => (raceEntry(p).card[0].value = "v".repeat(Protocol.LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS + 1)));
});

test("lore_codex v2 bounds slots per category and in total", () => {
  rejects((p) => {
    p.categories[0].groups[0].slots = [];
    for (let i = 0; i <= Protocol.LORE_CODEX_MAX_SLOTS_PER_CATEGORY; i++) {
      p.categories[0].groups[0].slots.push(placeholder());
    }
    p.categories[0].total = Protocol.LORE_CODEX_MAX_SLOTS_PER_CATEGORY + 1;
    rebalance(p);
  });
  // 512 shipped slots pass; a top-level total of 513 does not, even though
  // no more than 512 slots ship.
  const payload = validLoreCodexPayload();
  const perCategory = Protocol.LORE_CODEX_MAX_TOTAL_SLOTS / Object.keys(LABELS).length;
  payload.categories.forEach((cat) => {
    cat.groups = [cat.groups[0] || { key: "t_tier_a", label: "甲級", slots: [] }];
    cat.groups[0].slots = new Array(perCategory).fill(null).map(placeholder);
    cat.total = perCategory;
  });
  Protocol.validateLoreCodexPanel(rebalance(payload));
  payload.categories[0].total += 1;
  assert.throws(() => Protocol.validateLoreCodexPanel(rebalance(payload)));
});

test("lore_codex is in panel allowlist and validates in snapshots and unavailable forms", () => {
  const validAvailable = validLoreCodexPayload();
  const unavailable = {
    schema_version: 2,
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
  envelope.base_revision = 1;
  envelope.removed_panels = [];
  assert.doesNotThrow(() => Protocol.validateUpdate(envelope));

  assert.deepEqual(
    Protocol.validatePanel("lore_codex", Protocol.PANEL_ALLOWLIST.lore_codex, unavailable),
    unavailable
  );
});
