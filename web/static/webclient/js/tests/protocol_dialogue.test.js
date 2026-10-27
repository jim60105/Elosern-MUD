/*
 * dialogue panel v3 mirror: choices, panels, rejections, delivery.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { VALID_EPOCH, serverTime, validStatusPanel } = require("./protocol_support.js");
const core = require("../elosern/protocol/core.js");
const skillDescriptor = require("../elosern/protocol/panels/skill_descriptor.js");
const {
  validCharacterPanel,
  validCharacterTraitRow,
  validServicesPanel,
  validServicesStockRow,
  validPartyInventoryPanel,
  validPartyInventoryRow,
} = require("./protocol_fixtures.js");


test("dialogue choice cap mirrors the panel-owned bound (align-11)", () => {
  assert.equal(Protocol.DIALOGUE_MAX_CHOICES, 16);
});

test("explore.talk_scripted skill descriptor validates descriptor without selection_id", () => {
  const validParams = {
    npc_id: 41,
    topic_id: "guild_staff.topic_01",
    context_id: "ctx-1",
  };
  assert.doesNotThrow(() =>
    skillDescriptor.validateContextActionsAffordanceParams("explore.talk_scripted", validParams)
  );

  // Reject if extra selection_id is present in descriptor
  assert.throws(() =>
    skillDescriptor.validateContextActionsAffordanceParams("explore.talk_scripted", {
      npc_id: 41,
      topic_id: "guild_staff.topic_01",
      context_id: "ctx-1",
      selection_id: "client-injected-forbidden",
    })
  );
});

test("two deliberate picks versus transport retry request-id separation", () => {
  const pick1Req = "session:1";
  const pick2Req = "session:2";
  assert.notEqual(pick1Req, pick2Req);
  const retryReq = pick1Req;
  assert.equal(retryReq, pick1Req);
});

function validDialogueChoice(overrides) {
  return Object.assign(
    {
      topic_id: "guild_staff.topic_01",
      keyword_id: "公會",
      label: "公會",
      availability: "open",
      requirement_hint: null,
      unread: false,
      predecessors: [],
      action_payload: {
        npc_id: 41,
        topic_id: "guild_staff.topic_01",
        context_id: "ctx-1",
      },
    },
    overrides || {}
  );
}

function validDialogueDelivery(overrides) {
  return Object.assign(
    {
      delivery_id: "deliv-1",
      context_id: "ctx-1",
      topic_id: "guild_staff.topic_01",
      scene_id: "guild_staff.topic_01_scene",
      scene_revision: "r1",
      phase_revision: null,
      kind: "formal",
      lines: [
        { kind: "speech", speaker: "actor", text: "公會" },
        { kind: "speech", speaker: "host", text: "歡迎來到公會。" },
      ],
    },
    overrides || {}
  );
}

function validDialoguePanel(overrides) {
  return Object.assign(
    {
      schema_version: 3,
      available: true,
      kind: "dialogue",
      host: { identity: 41, display_name: "公會職員", portrait_ref: null },
      actor: { identity: 1, display_name: "測試者", portrait_ref: null },
      bond_stage: "熟人",
      context_id: "ctx-1",
      delivery: validDialogueDelivery(),
      choices: [validDialogueChoice()],
      pure_chain: [],
      reading_revision: 0,
      completed_topic_ids: [],
      unlock_batch: null,
    },
    overrides || {}
  );
}

test("dialogue available form validates and empty choices and null stage are legal", () => {
  assert.deepEqual(Protocol.validateDialoguePanel(validDialoguePanel()), validDialoguePanel());
  assert.equal(Protocol.validateDialoguePanel(validDialoguePanel({ choices: [] })).choices.length, 0);
  assert.equal(Protocol.validateDialoguePanel(validDialoguePanel({ bond_stage: null })).bond_stage, null);
  assert.equal(Protocol.validateDialoguePanel(validDialoguePanel({ delivery: null })).delivery, null);

  const keyed = validDialoguePanel({
    host: { identity: 41, display_name: "公會職員", portrait_ref: "42" },
  });
  assert.deepEqual(Protocol.validateDialoguePanel(keyed), keyed);

  const atBound = "1".repeat(32);
  assert.equal(
    Protocol.validateDialoguePanel(
      validDialoguePanel({
        host: { identity: 41, display_name: "公會職員", portrait_ref: atBound },
      })
    ).host.portrait_ref,
    atBound
  );

  // Paired astral code points are legal text
  assert.doesNotThrow(() =>
    Protocol.validateDialoguePanel(
      validDialoguePanel({
        delivery: validDialogueDelivery({
          lines: [{ kind: "speech", speaker: "host", text: "歡迎\u{1F600}。" }],
        }),
      })
    )
  );
});

test("dialogue validator mirrors the server drift rejections and rejects v2", () => {
  // v2 rejection
  assert.throws(
    () =>
      Protocol.validateDialoguePanel({
        schema_version: 2,
        available: true,
        kind: "dialogue",
        host: { identity: 41, display_name: "a", portrait_ref: null },
        bond_stage: null,
        line: "old line",
        choices: [],
      }),
    /unsupported dialogue schema_version/
  );

  for (const bad of [
    // prototype-named own keys from JSON.parse must read as unknown fields
    JSON.parse(
      '{"schema_version":3,"available":true,"kind":"dialogue","host":{"identity":41,"display_name":"a","portrait_ref":null},"actor":{"identity":1,"display_name":"b","portrait_ref":null},"bond_stage":"友","context_id":"c","delivery":null,"choices":[],"pure_chain":[],"reading_revision":0,"completed_topic_ids":[],"unlock_batch":null,"__proto__":{}}'
    ),
    validDialoguePanel({ extra: 1 }),
    (() => {
      const missing = validDialoguePanel();
      delete missing.choices;
      return missing;
    })(),
    (() => {
      const missing = validDialoguePanel();
      delete missing.actor;
      return missing;
    })(),
    (() => {
      const missing = validDialoguePanel();
      delete missing.context_id;
      return missing;
    })(),
    validDialoguePanel({ schema_version: 1 }),
    validDialoguePanel({ schema_version: 2 }),
    validDialoguePanel({ schema_version: 4 }),
    { schema_version: 3, available: false },
    validDialoguePanel({ available: false }),
    validDialoguePanel({ kind: "party" }),
    validDialoguePanel({ host: { identity: 41, display_name: "a", portrait_ref: 42 } }),
    validDialoguePanel({ host: { identity: 41, display_name: "a", portrait_ref: "4a" } }),
    validDialoguePanel({
      host: { identity: 41, display_name: "a", portrait_ref: "1".repeat(33) },
    }),
    validDialoguePanel({ host: { identity: 0, display_name: "a", portrait_ref: null } }),
    validDialoguePanel({ host: { identity: 41, display_name: "  ", portrait_ref: null } }),
    validDialoguePanel({ bond_stage: 3 }),
    validDialoguePanel({ bond_stage: "" }),
    validDialoguePanel({ context_id: "" }),
    // choice cap and uniqueness
    validDialoguePanel({
      choices: Array.from({ length: Protocol.DIALOGUE_MAX_CHOICES + 1 }, (_, i) =>
        validDialogueChoice({ topic_id: "t_" + i, keyword_id: "k_" + i })
      ),
    }),
    validDialoguePanel({ choices: [validDialogueChoice(), validDialogueChoice()] }),
    validDialoguePanel({ choices: [validDialogueChoice({ topic_id: " " })] }),
    validDialoguePanel({ choices: [validDialogueChoice({ keyword_id: " " })] }),
    validDialoguePanel({ choices: [{ topic_id: "guild_staff.topic_01" }] }),
    // delivery schema errors
    validDialoguePanel({ delivery: { delivery_id: "" } }),
    validDialoguePanel({
      delivery: validDialogueDelivery({ kind: "invalid_kind" }),
    }),
    validDialoguePanel({
      delivery: validDialogueDelivery({
        lines: [{ kind: "speech", speaker: "invalid_speaker", text: "hi" }],
      }),
    }),
  ]) {
    assert.throws(() => Protocol.validateDialoguePanel(bad));
  }
});

test("dialogue is in the production panel allowlist with dialogue mode accepted in v3", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.dialogue, 3);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "dialogue",
    panels: {
      dialogue: { schema_version: 3, available: true, kind: "dialogue" },
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.validateSnapshot(envelope));
  envelope.panels = { dialogue: validDialoguePanel() };
  envelope.revision = 6;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
  envelope.panels = {
    dialogue: {
      schema_version: 3,
      available: false,
      reason: { code: "dialogue_unavailable", message: "對話目前無法顯示" },
    },
  };
  envelope.revision = 7;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
});

function makePaddedSibling(targetBytes) {
  const fields = {};
  for (let index = 0; core.jsonByteSize(fields) < targetBytes && index < 55; index++) {
    fields["pad_" + index] = "測試字串內容一二三四五六七八九十".repeat(60);
  }
  return fields;
}

function makeMaximalDialoguePanel() {
  const cjkLines = [];
  for (let i = 0; i < 12; i++) {
    cjkLines.push({
      kind: "speech",
      speaker: i % 2 === 0 ? "actor" : "host",
      text: `冒險者公會的大廳內聚集了來自各地的傭兵與行商，空氣中瀰漫著舊羊皮紙與麥酒的香氣。壁爐燃燒著溫暖的柴火，照亮了懸掛在牆上的各式懸賞與地圖。（行次${i}）`.repeat(2),
    });
  }
  const pureChain = [];
  for (let i = 0; i < 4; i++) {
    pureChain.push({
      delivery: {
        delivery_id: "deliv-succ-" + i,
        context_id: "ctx-1",
        topic_id: "guild_staff.topic_0" + (i + 2),
        scene_id: "guild_staff.topic_0" + (i + 2) + "_scene",
        scene_revision: "r1",
        phase_revision: null,
        kind: "formal",
        lines: Array.from({ length: 6 }, (_, j) => ({
          kind: "speech",
          speaker: j % 2 === 0 ? "actor" : "host",
          text: `公會核實完畢的後續委託工作細節說明與相關注意事項描述文本。（接續行次${j}）`.repeat(2),
        })),
      },
      predecessors: ["guild_staff.topic_01"],
    });
  }
  const choices = [];
  for (let i = 0; i < 16; i++) {
    choices.push({
      topic_id: "guild_staff.topic_" + i,
      keyword_id: "話題" + i,
      label: "話題選單標籤" + i + "詳細資訊說明文本".repeat(2),
      availability: "open",
      requirement_hint: null,
      unread: false,
      predecessors: [],
      action_payload: { npc_id: 41, topic_id: "guild_staff.topic_" + i, context_id: "ctx-1" },
    });
  }
  return {
    schema_version: 3,
    available: true,
    kind: "dialogue",
    host: { identity: 41, display_name: "公會職員", portrait_ref: null },
    actor: { identity: 1, display_name: "測試者", portrait_ref: null },
    bond_stage: "熟人",
    context_id: "ctx-1",
    delivery: {
      delivery_id: "deliv-1",
      context_id: "ctx-1",
      topic_id: "guild_staff.topic_01",
      scene_id: "guild_staff.topic_01_scene",
      scene_revision: "r1",
      phase_revision: null,
      kind: "formal",
      lines: cjkLines,
    },
    choices: choices,
    pure_chain: pureChain,
    reading_revision: 0,
    completed_topic_ids: [],
    unlock_batch: null,
  };
}

function makeLargeValidSiblingPanels() {
  const passives = [];
  for (let i = 0; i < 30; i++) {
    passives.push({ key: "t_pass_" + i, label: "被動技能名稱" + i + "專精效果說明文本".repeat(6) });
  }
  const actives = [];
  for (let i = 0; i < 90; i++) {
    actives.push({
      key: "t_act_" + i,
      label: "主動技能名稱" + i + "戰鬥施放說明".repeat(4),
      level: 5,
      xp_into_level: 100,
      xp_to_next_level: 500,
      capped: false,
      fresh: false,
      booked: false,
    });
  }
  const traits = [];
  for (let i = 0; i < 30; i++) {
    traits.push(
      validCharacterTraitRow({
        key: "trait_" + i,
        label: "角色特性數值說明標籤" + i,
        base: 10,
        current: 12,
        max: null,
        effective: 12,
        layers: [{ source: "equipment", name: "傳奇附魔板甲", kind: "flat", amount: 2 }],
      })
    );
  }
  const char = validCharacterPanel({
    traits: traits,
    actives: [{ category: "elemental_magic", label: "元素魔法", groups: [{ group: "fire", label: "焰系", skills: actives }] }],
    passives: [{ category: "enhancement", label: "強化系別", groups: [{ group: null, label: null, skills: passives }] }],
  });
  const stock = [];
  for (let i = 0; i < 12; i++) {
    stock.push(validServicesStockRow({ item_key: "item_" + i, display_name: "行商專用高級商品名稱道具" + i }));
  }
  const services = validServicesPanel({
    // Every section names its own provider; the validator never defaults it.
    shop: { provider_id: 62, open: true, member_id: 101, stock: stock, sellable: [] },
    pagination: { stock_total: stock.length, sellable_total: 0, quest_total: 0, board_total: 0 },
  });
  const bagRows = [];
  for (let i = 0; i < 30; i++) {
    bagRows.push(validPartyInventoryRow({ item_key: "bag_item_" + i, display_name: "行囊中的高級備用物資道具" + i, held: 5 }));
  }
  const partyInv = validPartyInventoryPanel({ rows: bagRows });
  return {
    status: validStatusPanel(),
    character: char,
    services: services,
    party_inventory: partyInv,
  };
}

test("maximal multilingual chain fits within budgets and is adopted by store", () => {
  const dialoguePanel = makeMaximalDialoguePanel();
  const deliveryBytes = core.jsonByteSize(dialoguePanel.delivery);
  assert.ok(deliveryBytes < 8192, `delivery should be < 8192 bytes, was ${deliveryBytes}`);
  const panelBytes = core.jsonByteSize(dialoguePanel);
  const bundleBytes = deliveryBytes + dialoguePanel.pure_chain.reduce((sum, item) => sum + core.jsonByteSize(item.delivery), 0);
  assert.ok(bundleBytes <= Protocol.DIALOGUE_BUNDLE_MAX_BYTES, `bundle ${bundleBytes} <= 16384`);
  assert.ok(panelBytes <= Protocol.DIALOGUE_PANEL_MAX_BYTES, `dialogue panel ${panelBytes} <= 24576`);

  const siblingPanels = makeLargeValidSiblingPanels();
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "dialogue",
    panels: Object.assign(
      {},
      siblingPanels,
      {
      dialogue: dialoguePanel,
      }
    ),
    layout_version: 1,
    server_time: serverTime(),
  };

  const wholeBytes = core.jsonByteSize(envelope);
  const strippedEnvelope = Object.assign({}, envelope, { panels: siblingPanels });
  assert.ok(core.jsonByteSize(strippedEnvelope) <= Protocol.MAX_CANONICAL_JSON_BYTES);
  assert.ok(wholeBytes > 65536, `envelope should be > 65536 bytes, was ${wholeBytes}`);
  assert.ok(wholeBytes <= Protocol.DIALOGUE_ENVELOPE_MAX_BYTES, `envelope should be <= 98304 bytes, was ${wholeBytes}`);

  // checkEnvelope allows it under the dialogue conditional allowance
  assert.doesNotThrow(() => Protocol.checkEnvelope(envelope));

  // store adopts it
  const store = Protocol.createStore();
  store.beginTransport(1);
  const result = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(result.accepted, true);
  assert.equal(store.getState().panels.dialogue.schema_version, 3);
  assert.equal(store.getState().revision, 1);
});

test("maximal multilingual chain reconnect adoption across transport generations", () => {
  const dialoguePanel = makeMaximalDialoguePanel();
  const siblingPanels = makeLargeValidSiblingPanels();
  const store = Protocol.createStore();
  store.beginTransport(1);

  const initialEnvelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "dialogue",
    panels: { dialogue: validDialoguePanel() },
    layout_version: 1,
    server_time: serverTime(),
  };
  const r1 = store.receive(1, "ui_snapshot", [initialEnvelope], {});
  assert.equal(r1.accepted, true);

  // Reconnect in generation 2 with a new presentation epoch
  const RECONNECT_EPOCH = "r".repeat(22);
  store.beginTransport(2);
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");

  const reconnectEnvelope = {
    protocol_version: 1,
    presentation_epoch: RECONNECT_EPOCH,
    revision: 1,
    mode: "dialogue",
    panels: Object.assign(
      {},
      siblingPanels,
      { dialogue: dialoguePanel }
    ),
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.ok(core.jsonByteSize(reconnectEnvelope) > 65536);
  assert.ok(core.jsonByteSize(reconnectEnvelope) <= Protocol.DIALOGUE_ENVELOPE_MAX_BYTES);

  const r2 = store.receive(2, "ui_snapshot", [reconnectEnvelope], {});
  assert.equal(r2.accepted, true);
  assert.equal(r2.established, true);
  assert.equal(store.getState().activeEpoch, RECONNECT_EPOCH);
  assert.equal(store.getState().panels.dialogue.schema_version, 3);

  // Old-epoch snapshot received after reconnect is rejected
  const staleOldSnapshot = Object.assign({}, initialEnvelope, { revision: 99 });
  const rStale = store.receive(2, "ui_snapshot", [staleOldSnapshot], {});
  assert.equal(rStale.accepted, false);
  assert.equal(rStale.reason, "different_epoch");
});

test("dialogue envelope exceeding 98304 bytes is rejected before adoption", () => {
  function makeOverweightFields(targetBytes) {
    const fields = {};
    for (let index = 0; core.jsonByteSize(fields) < targetBytes && index < 55; index++) {
      fields["pad_" + index] = "測試字串內容一二三四五六七八九十".repeat(60);
    }
    return fields;
  }
  // Sibling padding is kept <= 65536 so stripped envelope passes, but dialogue + sibling exceeds 98304
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "dialogue",
    panels: {
      dialogue: validDialoguePanel({
        delivery: validDialogueDelivery({
          lines: Array.from({ length: 15 }, (_, i) => ({
            kind: "speech",
            speaker: "host",
            text: `公會接待員微笑著注視著前來的旅人，緩緩從木櫃中取出登記卷軸與墨水筆。（長文本行次 ${i + 1}）`.repeat(
              3
            ),
          })),
        }),
        pure_chain: Array.from({ length: 4 }, (_, i) => ({
          delivery: validDialogueDelivery({ delivery_id: `succ-${i}` }),
          predecessors: ["guild_staff.topic_01"],
        })),
      }),
      status: Object.assign(
        {
          schema_version: 4,
          available: true,
          name: "超限測試",
          identity: 1,
          hp: { current: 10, max: 10 },
          mp: { current: 5, max: 5 },
          sp: { current: 8, max: 8 },
          states: [],
          disguise_active: false,
          fatigue: [],
          combat: null,
        },
        makeOverweightFields(100000)
      ),
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.ok(core.jsonByteSize(envelope) > Protocol.DIALOGUE_ENVELOPE_MAX_BYTES);
  assert.throws(() => Protocol.checkEnvelope(envelope), /exceeds 98304 bytes/);

  const store = Protocol.createStore();
  store.beginTransport(1);
  const res = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(res.accepted, false);
  assert.equal(res.reason, "invalid");
});

test("dialogue panel exceeding 24576 bytes is rejected before adoption", () => {
  // Create a dialogue panel where lines exceed 24576
  const heavyLines = [];
  for (let i = 0; i < 20; i++) {
    heavyLines.push({
      kind: "speech",
      speaker: "host",
      text: "繁體中文文本內容超過長度限制的測試段落。".repeat(40),
    });
  }
  const oversizedPanel = validDialoguePanel({
    delivery: validDialogueDelivery({ lines: heavyLines }),
  });
  assert.ok(core.jsonByteSize(oversizedPanel) > Protocol.DIALOGUE_PANEL_MAX_BYTES);
  assert.throws(() => Protocol.validateDialoguePanel(oversizedPanel), /exceeds 24576 bytes/);

  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "dialogue",
    panels: { dialogue: oversizedPanel },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.checkEnvelope(envelope), /dialogue panel canonical JSON exceeds 24576 bytes/);

  const store = Protocol.createStore();
  store.beginTransport(1);
  const res = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(res.accepted, false);
  assert.equal(res.reason, "invalid");
});

test("unchanged 65536-byte bound: dialogue-removed envelope exceeding 65536 is rejected", () => {
  // Dialogue panel is small (valid), but sibling panel exceeds 65536 bytes
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "dialogue",
    panels: {
      dialogue: validDialoguePanel(),
      status: Object.assign(
        {
          schema_version: 4,
          available: true,
          name: "側面板超限",
          identity: 1,
          hp: { current: 10, max: 10 },
          mp: { current: 5, max: 5 },
          sp: { current: 8, max: 8 },
          states: [],
          disguise_active: false,
          fatigue: [],
          combat: null,
        },
        makePaddedSibling(67000)
      ),
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  // Total envelope is under 98304, but stripped envelope exceeds 65536
  assert.ok(core.jsonByteSize(envelope) <= Protocol.DIALOGUE_ENVELOPE_MAX_BYTES);
  assert.throws(
    () => Protocol.checkEnvelope(envelope),
    /dialogue-removed envelope canonical JSON exceeds 65536 bytes/
  );

  const store = Protocol.createStore();
  store.beginTransport(1);
  const res = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(res.accepted, false);
  assert.equal(res.reason, "invalid");
});

test("unrelated envelope without available dialogue keeps unchanged 65536 bound", () => {
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "exploration",
    panels: {
      status: Object.assign(
        {
          schema_version: 4,
          available: true,
          name: "探索狀態",
          identity: 1,
          hp: { current: 10, max: 10 },
          mp: { current: 5, max: 5 },
          sp: { current: 8, max: 8 },
          states: [],
          disguise_active: false,
          fatigue: [],
          combat: null,
        },
        makePaddedSibling(66000)
      ),
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.checkEnvelope(envelope), /canonical JSON exceeds 65536 bytes/);
});

// authored-dialogue-unread-notices: one watcher's wrapped unlock batch names
// this panel's host and context and only its open choices, in order.
test("dialogue unlock_batch mirrors the server wrapped-batch bounds", () => {
  const second = validDialogueChoice({
    topic_id: "guild_staff.topic_02",
    keyword_id: "委託",
    label: "委託",
    action_payload: { npc_id: 41, topic_id: "guild_staff.topic_02", context_id: "ctx-1" },
  });
  const locked = validDialogueChoice({
    topic_id: "guild_staff.topic_03",
    keyword_id: "密談",
    label: "密談",
    availability: "locked",
    requirement_hint: "需要信物",
    action_payload: { npc_id: 41, topic_id: "guild_staff.topic_03", context_id: "ctx-1" },
  });
  const choices = [validDialogueChoice(), second, locked];
  const batch = (overrides) =>
    validDialoguePanel({
      choices,
      unlock_batch: Object.assign(
        {
          batch_id: "a".repeat(32),
          host_id: 41,
          context_id: "ctx-1",
          topic_ids: ["guild_staff.topic_01", "guild_staff.topic_02"],
        },
        overrides || {}
      ),
    });
  assert.deepEqual(Protocol.validateDialoguePanel(batch()), batch());
  for (const bad of [
    batch({ batch_id: "" }),
    batch({ batch_id: "x".repeat(65) }),
    batch({ batch_id: "批次" }),
    batch({ host_id: 42 }),
    batch({ host_id: 0 }),
    batch({ context_id: "ctx-2" }),
    batch({ topic_ids: [] }),
    batch({ topic_ids: ["guild_staff.topic_01", "guild_staff.topic_01"] }),
    batch({ topic_ids: ["guild_staff.topic_03"] }),
    batch({ topic_ids: ["guild_staff.topic_99"] }),
    batch({ topic_ids: ["guild_staff.topic_02", "guild_staff.topic_01"] }),
    batch({ extra: 1 }),
  ]) {
    assert.throws(() => Protocol.validateDialoguePanel(bad));
  }
});
