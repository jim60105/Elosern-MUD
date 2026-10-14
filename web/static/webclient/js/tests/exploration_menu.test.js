/*
 * DOM-independent tests for the exploration-menu model.
 *
 * Runs with Node 24's built-in test runner; no npm packages. Covers the
 * scene-overview footer, the exit and presence-rail builders, the wait
 * submenu, the top navigation bar's entries, a target's verb card rows,
 * disabled-row non-submission, and the navigate-kind service affordance being
 * dock-navigation only (never submitted as an action).
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const ExplorationMenu = require("../elosern/exploration_menu.js");
const Protocol = require("../elosern/protocol.js");
const { SYNTH_ITEM } = require("./support/synthetic-data.js");

function validPanel(overrides) {
  return Object.assign(
    {
      schema_version: 4,
      available: true,
      kind: "exploration",
      move: [
        {
          exit_ref: "42",
          label: "東",
          destination: "room:7",
          enabled: true,
          disabled_reason: null,
        },
      ],
      look: {
        room: { identity: 3, display_name: "南門", room: true },
        entities: [{ identity: 5, display_name: "南門守衛", kind: "npc", portrait_ref: null }],
        objects: [{ identity: 6, display_name: "木箱" }],
      },
      interact: [
        {
          identity: 5,
          display_name: "南門守衛",
          portrait_ref: null,
          affordances: [
            {
              kind: "action",
              action_id: "explore.talk_open",
              label: "交談",
              enabled: true,
              disabled_reason: null,
            },
            {
              kind: "navigate",
              surface: "guild",
              label: "公會服務",
              enabled: true,
              disabled_reason: null,
            },
          ],
        },
      ],
      character: { available: true },
      quests: { available: true },
      inventory: { available: true },
    },
    overrides || {}
  );
}

test("the navigation builder carries 角色狀態 plus available quests and inventory", () => {
  const items = ExplorationMenu.navigationItems(validPanel());
  assert.deepEqual(
    items.map((item) => item.key),
    ["character", "quests", "inventory"]
  );
  // 任務 is a frameless drawer open (the 背包 precedent):
  // the exact shape carries openDrawer and no submenu/service-submenu field.
  const quests = items.find((item) => item.key === "quests");
  assert.deepEqual(quests, {
    key: "quests",
    label: "任務",
    enabled: true,
    actionId: null,
    payload: null,
    openDrawer: "quest",
  });
  // The 背包 row is a frameless drawer open (the 角色 row precedent):
  // the exact shape carries openDrawer and no submenu/service-submenu field.
  const inventory = items.find((item) => item.key === "inventory");
  assert.deepEqual(inventory, {
    key: "inventory",
    label: "背包",
    enabled: true,
    actionId: null,
    payload: null,
    openDrawer: "inventory",
  });
  assert.equal(items.find((item) => item.key === "character").openCharacter, true);
});

test("quests and inventory are omitted when the services capability is absent", () => {
  const items = ExplorationMenu.navigationItems(
    validPanel({ quests: { available: false }, inventory: { available: false } })
  );
  assert.deepEqual(items.map((item) => item.key), ["character"]);
});

test("move rows carry the exit_ref and canonical current_node payload", () => {
  const moveItem = ExplorationMenu.moveItems(validPanel(), "room:3")[0];
  assert.equal(moveItem.enabled, true);
  assert.equal(moveItem.actionId, "explore.move");
  assert.deepEqual(moveItem.payload, { exit_ref: "42", current_node: "room:3" });
});

test("a locked exit chip is disabled, never submits, and keeps its plain label", () => {
  const panel = validPanel({
    move: [
      {
        exit_ref: "42",
        label: "東",
        destination: "room:7",
        enabled: false,
        disabled_reason: { code: "locked", message: "此出口目前無法通行。" },
      },
    ],
  });
  const items = ExplorationMenu.moveItems(panel, "room:3");
  assert.equal(items.length, 1, "the chip builder carries no back row");
  const moveItem = items[0];
  assert.equal(moveItem.enabled, false);
  assert.equal(moveItem.actionId, null);
  assert.equal(moveItem.description, "此出口目前無法通行。");
  // The shared chip renderer owns the disabled marker: no per-frame suffix.
  assert.equal(moveItem.label, "東");
});

test("move rows disable without the local-map current_node, and an empty exit list yields no placeholder", () => {
  const moveItem = ExplorationMenu.moveItems(validPanel(), null)[0];
  assert.equal(moveItem.enabled, false);
  assert.equal(moveItem.actionId, null);
  // A room with no exits omits the overview's section instead of rendering a
  // dead `move-empty` row.
  assert.deepEqual(ExplorationMenu.moveItems({ move: [] }, "room:3"), []);
});

test("look rows cover the room marker plus entities and objects, with no back row", () => {
  const items = ExplorationMenu.lookItems(validPanel());
  assert.deepEqual(
    items.map((item) => item.key),
    ["look-room", "entity-5", "object-6"]
  );
  assert.deepEqual(items[0].payload, { room: true });
  assert.deepEqual(items[1].payload, { target_id: 5 });
  assert.deepEqual(items[2].payload, { target_id: 6 });
});

test("the wait rows are dawn, sleep, and the rest form, then the back row", () => {
  // exploration-room-actions design D5: the wait card's rows (the card drops
  // the builder's back row and draws its own `✕ 返回`).
  const items = ExplorationMenu.waitItems();
  assert.deepEqual(
    items.map((item) => item.key),
    ["wait-dawn", "wait-sleep", "wait-rest", "back"]
  );
  assert.deepEqual(items[0].payload, { daypart: "dawn" });
  assert.equal(items[0].actionId, "explore.wait");
  assert.deepEqual(items[1].payload, { sleep: true }, "the dream flag is the question's, never the row's");
  assert.equal(items[2].actionId, null, "the rest row opens the form and submits nothing");
  assert.equal(items[2].openRestForm, true);
  const back = items[items.length - 1];
  assert.equal(back.goBack, true);
  assert.equal(back.actionId, null, "the back row never submits an action");
  // Dynamic menus (a target's affordances) and the suggestions rows end with
  // the same back cell.
  const model = ExplorationMenu.buildMenus(validPanel(), { currentNode: "room:3" });
  const target = ExplorationMenu.targetById(model, 5);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  assert.equal(targetMenu.items[targetMenu.items.length - 1].key, "back");
  const suggestions = ExplorationMenu.suggestionsMenu({ status: "generating" });
  assert.equal(suggestions.items[suggestions.items.length - 1].key, "back");
});

test("the menu model carries no router frame any more", () => {
  // exploration-room-actions: the wait and suggestions frames are retired;
  // the model keeps the panel and the current node the verb card reads.
  const panel = validPanel();
  const model = ExplorationMenu.buildMenus(panel, { currentNode: "room:3" });
  assert.deepEqual(model.menus, {});
  assert.equal(model.panel, panel);
  assert.equal(model.currentNode, "room:3");
  assert.equal(ExplorationMenu.overviewMenu, undefined, "the scene overview builder is retired");
});

test("rail target entries name their server-authored affordances", () => {
  const entries = ExplorationMenu.presenceEntries(validPanel());
  const person = entries.find((entry) => entry.key === "target-5");
  assert.equal(person.presence, "target");
  assert.equal(person.identity, 5);
  assert.equal(person.enabled, true);
  assert.equal(person.actionId, null, "a target entry opens the verb card and submits nothing");
  assert.equal(person.summary, "交談／公會服務");
  assert.equal(person.openTarget, undefined, "the openTarget item kind is retired");
});

test("a target with no affordances still opens its card, and its affordance frame keeps the empty placeholder", () => {
  const panel = validPanel({
    interact: [{ identity: 8, display_name: "路人", portrait_ref: null, affordances: [] }],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  // The rail entry is always enabled and reads 查看: its verb card has at
  // least 查看.
  const person = ExplorationMenu.presenceEntries(panel).find((entry) => entry.key === "target-8");
  assert.equal(person.enabled, true);
  assert.equal(person.summary, "查看");
  // The card's own source frame carries the disabled empty row.
  const targetMenu = ExplorationMenu.targetMenuFor(model, ExplorationMenu.targetById(model, 8));
  const empty = targetMenu.items.find((item) => item.key === "target-empty");
  assert.equal(empty.enabled, false);
  assert.equal(empty.actionId, null);
});

test("the navigate-kind service affordance is dock-navigation only, never an action", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), {});
  const target = ExplorationMenu.targetById(model, 5);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const service = targetMenu.items.find((item) => item.key === "service-guild");
  assert.ok(service);
  assert.equal(service.enabled, true);
  assert.equal(service.actionId, null);
  assert.equal(service.payload, null);
  assert.equal(service.openDrawer, "quest");
   assert.equal(service.openServiceSubmenu, undefined);
});

test("shop navigate affordance carries openDrawer: 'shop' and no openServiceSubmenu", () => {
   const panel = validPanel({
     interact: [
       {
         identity: 7,
         display_name: "雜貨店老闆",
         portrait_ref: null,
         affordances: [
           {
             kind: "navigate",
             surface: "shop",
             label: "商店",
             enabled: true,
             disabled_reason: null,
           },
           {
             kind: "navigate",
             surface: "shop",
             label: "打烊的商店",
             enabled: false,
             disabled_reason: "店家已打烊",
           },
         ],
       },
     ],
});
   const model = ExplorationMenu.buildMenus(panel, {});
   const target = ExplorationMenu.targetById(model, 7);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);

   const shopOpen = targetMenu.items[0];
   assert.equal(shopOpen.key, "service-shop");
   assert.equal(shopOpen.label, "商店");
   assert.equal(shopOpen.enabled, true);
   assert.equal(shopOpen.actionId, null);
   assert.equal(shopOpen.payload, null);
   assert.equal(shopOpen.openDrawer, "shop");
   assert.equal(shopOpen.openServiceSubmenu, undefined);
   assert.equal(shopOpen.description, null);
   assert.equal(shopOpen.disabledReason, null);

   const shopClosed = targetMenu.items[1];
   assert.equal(shopClosed.enabled, false);
   assert.equal(shopClosed.openDrawer, "shop");
   assert.equal(shopClosed.openServiceSubmenu, undefined);
   assert.equal(shopClosed.disabledReason, "店家已打烊");
});

test("guild navigate affordance carries openDrawer: 'quest', no openServiceSubmenu, and disabled reason preserved", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 9,
        display_name: "公會執事",
        portrait_ref: null,
        affordances: [
          {
            kind: "navigate",
            surface: "guild",
            label: "公會服務",
            enabled: false,
            disabled_reason: "公會整修中",
          },
        ],
      },
    ],
});
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 9);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const row = targetMenu.items[0];
  assert.equal(row.key, "service-guild");
  assert.equal(row.label, "公會服務");
  assert.equal(row.enabled, false);
  assert.equal(row.actionId, null);
  assert.equal(row.payload, null);
  assert.equal(row.openDrawer, "quest");
  assert.equal(row.openServiceSubmenu, undefined);
  assert.equal(row.description, null);
  assert.equal(row.disabledReason, "公會整修中");
});

test("no exploration menu item carries openServiceSubmenu", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), {});
  for (const [menuKey, menu] of Object.entries(model.menus)) {
    for (const item of menu.items) {
      assert.equal(
        item.openServiceSubmenu,
        undefined,
        `item ${item.key} in menu ${menuKey} carried openServiceSubmenu`
      );
    }
  }
});

test("the conversation row submits explore.talk_open with the host identity", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 9,
        display_name: "吟遊詩人",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.talk_open",
            label: "交談",
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 9);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const talk = targetMenu.items.find((item) => item.key === "talk-open");
  assert.ok(talk);
  assert.equal(talk.enabled, true);
  assert.equal(talk.label, "交談");
  assert.equal(talk.actionId, "explore.talk_open");
  assert.deepEqual(talk.payload, { npc_id: 9 });
  assert.deepEqual(talk.commandDisplay, { npcLabel: "吟遊詩人" });
});

test("a disabled conversation row keeps its reason and submits nothing", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 9,
        display_name: "吟遊詩人",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.talk_open",
            label: "交談",
            enabled: false,
            disabled_reason: {
              code: "possessed_talk",
              message: "附身狀態下無法與他人開啟對話。",
            },
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 9);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const talk = targetMenu.items.find((item) => item.key === "talk-open");
  assert.ok(talk);
  assert.equal(talk.enabled, false);
  assert.equal(talk.actionId, null);
  assert.equal(talk.payload, null);
  assert.equal(talk.description, "附身狀態下無法與他人開啟對話。");
  assert.deepEqual(talk.disabledReason, {
    code: "possessed_talk",
    message: "附身狀態下無法與他人開啟對話。",
  });
});

test("engage submits explore.engage only when enabled", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 10,
        display_name: "哥布林",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.engage",
            label: "戰鬥",
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 10);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const engage = targetMenu.items.find((item) => item.key === "engage");
  assert.equal(engage.actionId, "explore.engage");
  assert.deepEqual(engage.payload, { monster_id: 10 });
});

test("party invite submits explore.party_invite with the server NPC id", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 11,
        display_name: "艾洛希雅",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.party_invite",
            label: "邀請",
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 11);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const invite = targetMenu.items.find((item) => item.key === "party-invite");
  assert.equal(invite.actionId, "explore.party_invite");
  assert.deepEqual(invite.payload, { npc_id: 11, message: "" });
});

test("a disabled party invite keeps its reason and never submits", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 11,
        display_name: "艾洛希雅",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.party_invite",
            label: "邀請",
            enabled: false,
            disabled_reason: { code: "party_full", message: "你的隊伍已經滿了（最多 4 人）。" },
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 11);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const invite = targetMenu.items.find((item) => item.key === "party-invite");
  assert.equal(invite.enabled, false);
  assert.equal(invite.actionId, null);
  assert.equal(invite.payload, null);
  assert.match(invite.description, /滿/);
});

test("party leave submits explore.party_leave with the server NPC id", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 12,
        display_name: "艾洛希雅",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.party_leave",
            label: "解散",
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 12);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const leave = targetMenu.items.find((item) => item.key === "party-leave");
  assert.equal(leave.actionId, "explore.party_leave");
  assert.deepEqual(leave.payload, { npc_id: 12 });
});

test("deliver forwards the server-normalized params and echoes the server label", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 13,
        display_name: "灰婆婆",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.deliver",
            label: `交付 ${SYNTH_ITEM.display} 給 灰婆婆`,
            params: { npc_id: 13, item_key: SYNTH_ITEM.id },
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
  });
  // End-to-end mirror assertion (quest-deliver-action): the production panel
  // validator accepts the row the menu model is about to consume.
  assert.doesNotThrow(() => Protocol.validateExplorationPanel(panel));
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 13);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const deliver = targetMenu.items.find((item) => item.key === "deliver");
  assert.ok(deliver);
  assert.equal(deliver.actionId, "explore.deliver");
  // The menu forwards the server-normalized payload, never a reconstruction.
  assert.deepEqual(deliver.payload, { npc_id: 13, item_key: SYNTH_ITEM.id });
  assert.deepEqual(deliver.commandDisplay, {
    actionLabel: `交付 ${SYNTH_ITEM.display} 給 灰婆婆`,
  });
});

test("a disabled delivery keeps its reason and never submits", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 13,
        display_name: "灰婆婆",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.deliver",
            label: `交付 ${SYNTH_ITEM.display} 給 灰婆婆`,
            params: { npc_id: 13, item_key: SYNTH_ITEM.id },
            enabled: false,
            disabled_reason: {
              code: "item_not_held",
              message: "你沒有帶著足夠的任務物品。",
            },
          },
        ],
      },
    ],
  });
  assert.doesNotThrow(() => Protocol.validateExplorationPanel(panel));
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 13);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const deliver = targetMenu.items.find((item) => item.key === "deliver");
  assert.ok(deliver);
  assert.equal(deliver.enabled, false);
  assert.equal(deliver.actionId, null);
  assert.equal(deliver.payload, null);
  assert.match(deliver.description, /沒有帶著/);
});

// ---------------------------------------------------------------------------
// webclient-scene-overview-component (task 2.3): the scene overview and the
// verb popover menus. Synthesized fixtures only.
// ---------------------------------------------------------------------------

function overviewPanel() {
  return validPanel({
    move: [
      { exit_ref: "e1", label: "北", destination: "room:1", enabled: true, disabled_reason: null },
      {
        exit_ref: "e2",
        label: "櫃檯門",
        destination: "room:2",
        enabled: false,
        disabled_reason: { code: "locked", message: "門鎖著。" },
      },
    ],
    look: {
      room: { identity: 3, display_name: "試驗大廳", room: true },
      entities: [
        { identity: 5, display_name: "試驗守衛", kind: "npc", portrait_ref: null },
        { identity: 8, display_name: "旅人甲", kind: "character", portrait_ref: null },
      ],
      objects: [
        { identity: 6, display_name: "試驗箱" },
        { identity: 7, display_name: "告示板" },
      ],
    },
    interact: [
      {
        identity: 5,
        display_name: "試驗守衛",
        portrait_ref: null,
        affordances: [],
      },
    ],
  });
}

test("the room's 查看房間 row is the look builder's room row", () => {
  // exploration-room-actions design D3: the place card's 查看房間 submits the
  // retired footer chip's payload.
  const room = ExplorationMenu.lookItems(overviewPanel()).find((item) => item.key === "look-room");
  assert.equal(room.label, "查看房間");
  assert.equal(room.actionId, "explore.look");
  assert.deepEqual(room.payload, { room: true });
  assert.deepEqual(room.commandDisplay, { room: true });
});

test("a disabled exit target keeps its reason and the plain exit label", () => {
  const rows = ExplorationMenu.exitTargets(overviewPanel(), { currentNode: "room:3" });
  const locked = rows.find((item) => item.key === "exit-e2");
  assert.equal(locked.enabled, false);
  assert.equal(locked.actionId, null);
  assert.equal(locked.payload, null);
  assert.equal(locked.label, "櫃檯門", "no （無法通行） suffix is baked in");
  assert.equal(locked.description, "門鎖著。");
  assert.deepEqual(locked.disabledReason, { code: "locked", message: "門鎖著。" });
});

test("exit targets are exactly the move rows and carry the payload with current_node", () => {
  const rows = ExplorationMenu.exitTargets(overviewPanel(), { currentNode: "room:3" });
  assert.deepEqual(rows, ExplorationMenu.moveItems(overviewPanel(), "room:3"));
  assert.deepEqual(rows.map((item) => item.key), ["exit-e1", "exit-e2"]);
  const north = rows.find((item) => item.key === "exit-e1");
  assert.equal(north.actionId, "explore.move");
  assert.deepEqual(north.payload, { exit_ref: "e1", current_node: "room:3" });
  assert.equal(north.direction, "north");
  assert.equal(north.destination, "room:1");
  const unsynced = ExplorationMenu.exitTargets(overviewPanel(), {})[0];
  assert.equal(unsynced.enabled, false);
  assert.equal(unsynced.label, "北");
  assert.equal(unsynced.actionId, null, "an exit without the local-map current_node never submits");
});

test("rail entries follow the retired rows' order: targets, bystanders, then objects", () => {
  const entries = ExplorationMenu.presenceEntries(overviewPanel());
  assert.deepEqual(
    entries.map((entry) => [entry.key, entry.presence]),
    [
      ["target-5", "target"],
      ["entity-8", "bystander"],
      ["object-6", "object"],
      ["object-7", "object"],
    ]
  );
});

test("bystander entries appear only for identities without an interact descriptor and carry the look row verbatim", () => {
  const panel = overviewPanel();
  const entries = ExplorationMenu.presenceEntries(panel);
  assert.ok(!entries.some((entry) => entry.key === "entity-5"));
  const traveller = entries.find((entry) => entry.key === "entity-8");
  const lookRow = ExplorationMenu.lookItems(panel).find((item) => item.key === "entity-8");
  for (const field of ["key", "label", "enabled", "actionId", "payload", "commandDisplay"]) {
    assert.deepEqual(traveller[field], lookRow[field], field);
  }
  assert.deepEqual(traveller.payload, { target_id: 8 });
  assert.equal(traveller.summary, "查看");
  const chest = entries.find((entry) => entry.key === "object-6");
  assert.deepEqual(chest.payload, { target_id: 6 });
  assert.equal(chest.actionId, "explore.look");
  assert.deepEqual(chest.commandDisplay, { targetLabel: "試驗箱" });
});

test("rail target entries carry their portrait ref, falling back to the entity's", () => {
  const panel = overviewPanel();
  panel.look.entities[0].portrait_ref = "npc_5";
  panel.look.entities[1].portrait_ref = "char_8";
  const entries = ExplorationMenu.presenceEntries(panel);
  assert.equal(entries.find((entry) => entry.key === "target-5").portraitRef, "npc_5");
  assert.equal(entries.find((entry) => entry.key === "entity-8").portraitRef, "char_8");
  panel.interact[0].portrait_ref = "own_5";
  assert.equal(
    ExplorationMenu.presenceEntries(panel).find((entry) => entry.key === "target-5").portraitRef,
    "own_5"
  );
});

test("an empty room has no rail entries", () => {
  const panel = overviewPanel();
  panel.interact = [];
  panel.look.entities = [];
  panel.look.objects = [];
  assert.deepEqual(ExplorationMenu.presenceEntries(panel), []);
  assert.deepEqual(ExplorationMenu.presenceEntries(null), []);
});

test("every available panel carries the room row the place card reads", () => {
  // The OOB v2 schema guarantees a non-null `look.room` on every available
  // panel (`validateExplorationLook` requires the exact room fields), so the
  // place card's 查看房間 always has its row.
  const panel = overviewPanel();
  assert.doesNotThrow(() => Protocol.validateExplorationPanel(panel));
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      Object.assign({}, panel, {
        look: Object.assign({}, panel.look, { room: null }),
      })
    )
  );
  assert.ok(ExplorationMenu.lookItems(panel).some((item) => item.key === "look-room"));
});

test("verbMenuFor keeps payload order and appends 查看 then back", () => {
  const panel = validPanel();
  const model = ExplorationMenu.buildMenus(panel, { currentNode: "room:3" });
  const menu = ExplorationMenu.verbMenuFor(model, panel.interact[0]);
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["talk-open", "service-guild", "look-target", "back"]
  );
  const look = menu.items[2];
  assert.equal(look.label, "查看");
  assert.equal(look.actionId, "explore.look");
  assert.deepEqual(look.payload, { target_id: 5 });
  assert.equal(menu.title, "南門守衛");
  assert.equal(menu.target, panel.interact[0]);
  assert.equal(menu.grid, undefined, "the popover is a vertical list");
});

test("verbMenuFor yields 查看 and back for a target with no mapped affordance", () => {
  const panel = overviewPanel();
  const model = ExplorationMenu.buildMenus(panel, { currentNode: "room:3" });
  const menu = ExplorationMenu.verbMenuFor(model, panel.interact[0]);
  assert.deepEqual(menu.items.map((item) => item.key), ["look-target", "back"]);
});

// npc-persona-editor-window D1: the 編輯人物設定 navigate row opens the author
// editor bound by value to the target identity; a disabled row opens nothing
// and explains itself with the server-authored reason.
test("verbMenuFor maps the npc_persona affordance to a bound editor row", () => {
  const panel = validPanel();
  const target = Object.assign({}, panel.interact[0], {
    affordances: [
      { kind: "navigate", surface: "npc_persona", label: "編輯人物設定", enabled: true, disabled_reason: null },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, { currentNode: "room:3" });
  const menu = ExplorationMenu.verbMenuFor(model, target);
  const row = menu.items.find((item) => item.key === "service-npc_persona");
  assert.equal(row.label, "編輯人物設定");
  assert.equal(row.enabled, true);
  assert.equal(row.openNpcPersona, target.identity);
  assert.equal(row.actionId, null, "opening the editor dispatches nothing itself");
  assert.equal(row.openDrawer, undefined);

  const reason = { code: "npc_persona.unavailable", message: "此角色的設定目前無法編輯或尚未初始化。" };
  const disabledTarget = Object.assign({}, target, {
    affordances: [{ kind: "navigate", surface: "npc_persona", label: "", enabled: false, disabled_reason: reason }],
  });
  const disabled = ExplorationMenu.verbMenuFor(model, disabledTarget).items.find(
    (item) => item.key === "service-npc_persona"
  );
  assert.equal(disabled.label, "編輯人物設定", "an empty label falls back to the editor name");
  assert.equal(disabled.enabled, false);
  assert.equal(disabled.openNpcPersona, null);
  assert.equal(disabled.description, reason.message);
  assert.deepEqual(disabled.disabledReason, reason);
});
