const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const Protocol = require("../elosern/protocol.js");

test("exploration accepts npc_persona navigation surface", () => {
  assert.ok(Protocol.EXPLORATION_SURFACES.includes("npc_persona"));
  const panel = {
    schema_version: 3,
    available: true,
    kind: "exploration",
    move: [],
    look: {
      room: { identity: 1, display_name: "大廳", room: true },
      entities: [],
      objects: [],
    },
    interact: [
      {
        identity: 10,
        display_name: "接待員",
        portrait_ref: null,
        affordances: [
          {
            kind: "navigate",
            surface: "npc_persona",
            label: "編輯人物設定",
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
    character: { available: true },
    quests: { available: true },
    inventory: { available: true },
  };

  const validated = Protocol.validateExplorationPanel(panel);
  assert.equal(validated.interact[0].affordances[0].surface, "npc_persona");

  // Rejects extra fields on navigation affordance
  const badPanel = JSON.parse(JSON.stringify(panel));
  badPanel.interact[0].affordances[0].extra = "forbidden";
  assert.throws(() => Protocol.validateExplorationPanel(badPanel));
});

test("maximal-card success envelope passes Node protocol mirror", () => {
  const envelope = {
    protocol_version: 1,
    presentation_epoch: "valid-epoch-1234567890",
    request_id: "req-cjk",
    outcome: "success",
    code: "updated",
    message: "角色設定更新成功。",
    presentation_revision: 5,
    data: {
      npc_id: 10,
      display_name: "接待員",
      npc_title: "資深接待員",
      persona_version: 2,
      persona: {
        identity: {
          public: "公會侍者",
          hidden: "秘密情報員",
        },
        appearance: "金".repeat(300),
        personality: "善".repeat(300),
        speech_style: "客".repeat(300),
        life_story: "生".repeat(300),
        habit: "讀".repeat(300),
        social_connection: "交".repeat(300),
      },
    },
  };

  const validated = Protocol.validateActionResult(envelope);
  assert.equal(validated.outcome, "success");
  assert.equal(validated.data.npc_id, 10);
});
