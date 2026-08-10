/*
 * command_echo.js DOM-independent tests: every catalog mapping is pinned
 * against the canonical typed command spellings in `commands/*.py`, the
 * no-typed-command fallbacks emit server labels only, and null cases stay
 * silent. The bounds are asserted so a hostile label can never flood the log.
 */
const test = require("node:test");
const assert = require("node:assert");

const Echo = require("../elosern/command_echo.js");

test("explore.look resolves the room to the bare look command", () => {
  assert.strictEqual(
    Echo.commandLine("explore.look", { room: true }, { room: true }),
    "look"
  );
});

test("explore.look resolves an entity to look <name>", () => {
  assert.strictEqual(
    Echo.commandLine(
      "explore.look",
      { target_id: "goblin_1" },
      { targetLabel: "哥布林" }
    ),
    "look 哥布林"
  );
});

test("explore.talk_scripted resolves to talk <NPC> <keyword>", () => {
  assert.strictEqual(
    Echo.commandLine(
      "explore.talk_scripted",
      { npc_id: "innkeeper", keyword_id: "guild" },
      { npcLabel: "旅店老闆", keywordLabel: "公會" }
    ),
    "talk 旅店老闆 公會"
  );
});

test("explore.talk_freeform resolves to talk <NPC> <speech>", () => {
  assert.strictEqual(
    Echo.commandLine(
      "explore.talk_freeform",
      { npc_id: "innkeeper", speech: "你好嗎" },
      { npcLabel: "旅店老闆" }
    ),
    "talk 旅店老闆 你好嗎"
  );
});

test("explore.party_invite without a message resolves to invite <NPC>", () => {
  assert.strictEqual(
    Echo.commandLine(
      "explore.party_invite",
      { npc_id: "innkeeper", message: "" },
      { npcLabel: "艾洛希雅" }
    ),
    "invite 艾洛希雅"
  );
});

test("explore.party_invite with a message resolves to invite <NPC> <message>", () => {
  assert.strictEqual(
    Echo.commandLine(
      "explore.party_invite",
      { npc_id: "innkeeper", message: "你願意嗎" },
      { npcLabel: "艾洛希雅" }
    ),
    "invite 艾洛希雅 你願意嗎"
  );
});

test("explore.party_leave resolves to leave <NPC>", () => {
  assert.strictEqual(
    Echo.commandLine(
      "explore.party_leave",
      { npc_id: "innkeeper" },
      { npcLabel: "艾洛希雅" }
    ),
    "leave 艾洛希雅"
  );
});

test("explore.engage resolves to engage <target>", () => {
  assert.strictEqual(
    Echo.commandLine(
      "explore.engage",
      { monster_id: "goblin_1" },
      { targetLabel: "哥布林" }
    ),
    "engage 哥布林"
  );
});

test("explore.wait daypart resolves to wait until <daypart>", () => {
  assert.strictEqual(
    Echo.commandLine("explore.wait", { daypart: "dawn" }, {}),
    "wait until dawn"
  );
});

test("explore.wait seconds resolves to rest <n>s", () => {
  assert.strictEqual(
    Echo.commandLine("explore.wait", { seconds: 3600 }, {}),
    "rest 3600s"
  );
});

test("explore.wait sleep resolves to sleep", () => {
  assert.strictEqual(Echo.commandLine("explore.wait", { sleep: true }, {}), "sleep");
});

test("explore.move has no typed command and emits the exit label", () => {
  assert.strictEqual(
    Echo.commandLine(
      "explore.move",
      { exit_ref: "42", current_node: "grid:capital_altoria:2:0" },
      { exitLabel: "南大道" }
    ),
    "南大道"
  );
});

test("combat.cast without a target resolves to cast <skill>", () => {
  assert.strictEqual(
    Echo.commandLine("combat.cast", { skill_key: "body_strengthen" }, { skillLabel: "身體強化" }),
    "cast 身體強化"
  );
});

test("combat.cast with a target token resolves to cast <skill>=<target>", () => {
  assert.strictEqual(
    Echo.commandLine(
      "combat.cast",
      { skill_key: "fire_ball", target_ids: ["goblin_1"] },
      { skillLabel: "火球術", targetLabel: "哥布林" }
    ),
    "cast 火球術=哥布林"
  );
});

test("combat.cast with an AREA shorthand resolves to cast <skill>=<shorthand>", () => {
  assert.strictEqual(
    Echo.commandLine(
      "combat.cast",
      { skill_key: "fire_ball", target_shorthand: "all-enemies" },
      { skillLabel: "火球術" }
    ),
    "cast 火球術=all-enemies"
  );
});

test("combat.forfeit resolves to combat forfeit", () => {
  assert.strictEqual(Echo.commandLine("combat.forfeit", {}, {}), "combat forfeit");
});

test("combat.flee has no typed command and emits its button label", () => {
  assert.strictEqual(
    Echo.commandLine("combat.flee", {}, { actionLabel: "逃跑" }),
    "逃跑"
  );
});

test("guild.register resolves to guild register", () => {
  assert.strictEqual(Echo.commandLine("guild.register", {}, {}), "guild register");
});

test("guild.quest_accept resolves to guild accept <definition_key>", () => {
  assert.strictEqual(
    Echo.commandLine("guild.quest_accept", { definition_key: "gq_bandit_clear" }, {}),
    "guild accept gq_bandit_clear"
  );
});

test("guild.quest_abandon resolves to guild abandon <quest_id>", () => {
  assert.strictEqual(
    Echo.commandLine("guild.quest_abandon", { quest_id: "q_7" }, {}),
    "guild abandon q_7"
  );
});

test("guild.quest_turnin resolves to guild turnin <quest_id>", () => {
  assert.strictEqual(
    Echo.commandLine("guild.quest_turnin", { quest_id: "q_7" }, {}),
    "guild turnin q_7"
  );
});

test("guild.exam_start resolves to guild exam <target_rank>", () => {
  assert.strictEqual(
    Echo.commandLine("guild.exam_start", { target_rank: "E" }, {}),
    "guild exam E"
  );
});

test("shop.buy resolves to buy <item> <quantity>", () => {
  assert.strictEqual(
    Echo.commandLine("shop.buy", { item_key: "healing_potion", quantity: 3 }, { itemLabel: "治療藥水" }),
    "buy 治療藥水 3"
  );
});

test("shop.sell resolves to sell <item> <quantity>", () => {
  assert.strictEqual(
    Echo.commandLine("shop.sell", { item_key: "healing_potion", quantity: 2 }, { itemLabel: "治療藥水" }),
    "sell 治療藥水 2"
  );
});

test("creation.preset resolves to character preset <key>", () => {
  assert.strictEqual(
    Echo.commandLine("creation.preset", { preset_key: "elf_mage" }, {}),
    "character preset elf_mage"
  );
});

test("creation.custom resolves to character create", () => {
  assert.strictEqual(Echo.commandLine("creation.custom", {}, {}), "character create");
});

test("creation.concept resolves to the character concept command", () => {
  assert.strictEqual(
    Echo.commandLine("creation.concept", { concept: "流浪的精靈劍士" }, {}),
    "character concept 流浪的精靈劍士"
  );
  assert.strictEqual(Echo.commandLine("creation.concept", { concept: "" }, {}), null);
});

test("creation.activate resolves through the draft path", () => {
  assert.strictEqual(
    Echo.commandLine("creation.activate", {}, { presetKey: "elf_mage" }),
    "character preset elf_mage"
  );
  assert.strictEqual(Echo.commandLine("creation.activate", {}, {}), "character create");
});

test("creation.reset has no typed command and emits its button label", () => {
  assert.strictEqual(
    Echo.commandLine("creation.reset", {}, { actionLabel: "清除草稿" }),
    "清除草稿"
  );
});

test("an unknown action id stays silent", () => {
  assert.strictEqual(Echo.commandLine("proof.noop", {}, {}), null);
});

test("a missing descriptor label stays silent rather than fabricating a name", () => {
  assert.strictEqual(
    Echo.commandLine("explore.talk_scripted", { npc_id: "x", keyword_id: "y" }, {}),
    null
  );
  assert.strictEqual(Echo.commandLine("explore.engage", {}, {}), null);
  assert.strictEqual(
    Echo.commandLine("combat.flee", {}, {}),
    null,
    "a flee echo without a server label must not invent one"
  );
});

test("non-string and empty payload values stay silent", () => {
  assert.strictEqual(Echo.commandLine("shop.buy", { quantity: "3" }, { itemLabel: "藥水" }), null);
  assert.strictEqual(
    Echo.commandLine("explore.talk_freeform", { speech: "   " }, { npcLabel: "老闆" }),
    null
  );
});

test("oversized labels are truncated to the bounded length", () => {
  const huge = "太".repeat(Echo.MAX_LABEL_LENGTH + 40);
  const line = Echo.commandLine("explore.engage", {}, { targetLabel: huge });
  assert.ok(line !== null);
  assert.strictEqual(
    line,
    "engage " + "太".repeat(Echo.MAX_LABEL_LENGTH),
    "the embedded label is truncated to the label bound"
  );
  assert.strictEqual(line.length, "engage ".length + Echo.MAX_LABEL_LENGTH);
});

test("the emitted line itself is bounded to MAX_LINE_LENGTH", () => {
  // Two MAX_LABEL_LENGTH descriptors plus the command prefix push the line
  // over the line bound; the line is truncated, never longer.
  const npc = "名".repeat(Echo.MAX_LABEL_LENGTH);
  const keyword = "題".repeat(Echo.MAX_LABEL_LENGTH);
  const line = Echo.commandLine(
    "explore.talk_scripted",
    { npc_id: "n", keyword_id: "k" },
    { npcLabel: npc, keywordLabel: keyword }
  );
  assert.ok(line !== null);
  assert.strictEqual(line.length, Echo.MAX_LINE_LENGTH);
  assert.ok(line.length <= Echo.MAX_LINE_LENGTH);
});

test("label-derived lines containing markup-like characters stay literal text", () => {
  const line = Echo.commandLine(
    "explore.engage",
    {},
    { targetLabel: "<script>alert(1)</script>" }
  );
  assert.strictEqual(line, "engage <script>alert(1)</script>");
});

test("line separators in speech are collapsed, never echoed as raw newlines", () => {
  const line = Echo.commandLine(
    "explore.talk_freeform",
    { npc_id: "n", speech: "第一行\n第二行\t結尾" },
    { npcLabel: "老闆" }
  );
  assert.strictEqual(line, "talk 老闆 第一行 第二行 結尾");
});
