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

test("combat.cast echoes the chosen freeform magnitude label", () => {
  assert.strictEqual(
    Echo.commandLine(
      "combat.cast",
      { skill_key: "wind_blade", scale: 2, target_ids: [2] },
      { skillLabel: "風刃術", scaleLabel: "2", targetLabel: "哥布林" }
    ),
    "cast 風刃術（威力×2）=哥布林"
  );
  assert.strictEqual(
    Echo.commandLine(
      "combat.cast",
      { skill_key: "wind_blade", scale: 0.5, target_shorthand: "all-enemies" },
      { skillLabel: "風刃術", scaleLabel: "1/2" }
    ),
    "cast 風刃術（威力×1/2）=all-enemies"
  );
});

test("combat.cast without a scale label stays byte-identical", () => {
  assert.strictEqual(
    Echo.commandLine(
      "combat.cast",
      { skill_key: "wind_blade", target_shorthand: "all-enemies" },
      { skillLabel: "風刃術" }
    ),
    "cast 風刃術=all-enemies"
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

test("inventory.use resolves to the typed use command", () => {
  assert.strictEqual(
    Echo.commandLine("inventory.use", { item_key: "healing_potion" }, null),
    "use healing_potion"
  );
});

test("inventory.use stays silent on a missing, empty, or non-string item_key", () => {
  assert.strictEqual(Echo.commandLine("inventory.use", {}, null), null);
  assert.strictEqual(
    Echo.commandLine("inventory.use", { item_key: "  " }, null),
    null
  );
  assert.strictEqual(
    Echo.commandLine("inventory.use", { item_key: 7 }, null),
    null
  );
});

test("inventory.toggle_equip echoes the typed equip command in both directions", () => {
  // The typed 裝備/equip command IS the toggle: the unequip click echoes the
  // same replayable line, and no `unequip` command is ever invented.
  assert.strictEqual(
    Echo.commandLine("inventory.toggle_equip", { item_key: "leather_vest" }, null),
    "equip leather_vest"
  );
  assert.strictEqual(
    Echo.commandLine("inventory.toggle_equip", { item_key: "leather_vest" }, { equipped: true }),
    "equip leather_vest"
  );
});

test("title.accept resolves to the typed ballot answer", () => {
  for (const index of [1, 2, 3]) {
    assert.strictEqual(
      Echo.commandLine("title.accept", { index }, null),
      "title accept " + index
    );
  }
});

test("title.accept stays silent on a missing or out-of-cap index", () => {
  assert.strictEqual(Echo.commandLine("title.accept", {}, null), null);
  assert.strictEqual(Echo.commandLine("title.accept", { index: 0 }, null), null);
  assert.strictEqual(Echo.commandLine("title.accept", { index: 4 }, null), null);
  assert.strictEqual(
    Echo.commandLine("title.accept", { index: "1" }, null),
    null
  );
});

test("title.decline resolves to the typed decline command", () => {
  assert.strictEqual(Echo.commandLine("title.decline", {}, null), "title decline");
});

test("character.persona.update echoes the typed persona command per field", () => {
  const fields = {
    background: "設定背景",
    personality: "設定個性",
    life_story: "設定生平",
    habit: "設定習慣",
  };
  for (const [field, command] of Object.entries(fields)) {
    assert.strictEqual(
      Echo.commandLine("character.persona.update", { field, text: "清晨練劍" }, {}),
      command + " 清晨練劍"
    );
    // A null or blank text is the clear: a display-only （清除） notation,
    // never the bare command key (which is the READ spelling).
    assert.strictEqual(
      Echo.commandLine("character.persona.update", { field, text: null }, {}),
      command + "（清除）"
    );
    assert.strictEqual(
      Echo.commandLine("character.persona.update", { field, text: "   " }, {}),
      command + "（清除）"
    );
  }
});

test("character.persona.update stays silent on an unknown field or bad text", () => {
  assert.strictEqual(
    Echo.commandLine("character.persona.update", { field: "identity", text: "結構鍵" }, {}),
    null
  );
  assert.strictEqual(
    Echo.commandLine("character.persona.update", { field: "habit", text: 42 }, {}),
    null
  );
  assert.strictEqual(Echo.commandLine("character.persona.update", {}, {}), null);
});

test("title.equip resolves both kinds from the payload identifier", () => {
  assert.strictEqual(
    Echo.commandLine("title.equip", { kind: "fixed", identifier: "g_f_rank" }, null),
    "title equip fixed g_f_rank"
  );
  assert.strictEqual(
    Echo.commandLine(
      "title.equip",
      { kind: "epithet", identifier: "夜襲之人" },
      null
    ),
    "title equip epithet 夜襲之人"
  );
  assert.strictEqual(
    Echo.commandLine("title.equip", { kind: "widget", identifier: "x" }, null),
    null
  );
  assert.strictEqual(
    Echo.commandLine("title.equip", { kind: "fixed", identifier: "" }, null),
    null
  );
});

test("title.remove echoes the confirmed removal, quoting a confirm-tailed display", () => {
  assert.strictEqual(
    Echo.commandLine("title.remove", { display: "夜襲之人" }, null),
    "title remove epithet 夜襲之人 confirm"
  );
  // A display whose tail would eat the literal confirm token is echoed
  // quoted so the echoed line re-parses to the same target (the server's
  // parse strips one matching quote pair before the gate match).
  assert.strictEqual(
    Echo.commandLine("title.remove", { display: "破門 confirm" }, null),
    'title remove epithet "破門 confirm" confirm'
  );
  assert.strictEqual(
    Echo.commandLine("title.remove", { display: "confirm" }, null),
    'title remove epithet "confirm" confirm'
  );
  assert.strictEqual(Echo.commandLine("title.remove", {}, null), null);
  assert.strictEqual(Echo.commandLine("title.remove", { display: 7 }, null), null);
});

test("title echoes keep the full 64-code-point contract cap, never 60", () => {
  // The title view/validator contract admits identifiers up to 64 code
  // points; the echo must dispatch exactly what the payload carries, so
  // the generic 60-char label bound must not truncate a 61-64 display.
  const display = "名".repeat(Echo.MAX_TITLE_IDENTIFIER_LENGTH);
  assert.strictEqual(
    Echo.commandLine("title.remove", { display }, null),
    `title remove epithet ${display} confirm`
  );
  assert.strictEqual(
    Echo.commandLine("title.equip", { kind: "epithet", identifier: display }, null),
    `title equip epithet ${display}`
  );
  // Anything past the contract cap degrades to the cap, and the worst-case
  // quoted remove line still fits the global line bound.
  const over = "名".repeat(Echo.MAX_TITLE_IDENTIFIER_LENGTH + 8);
  const line = Echo.commandLine("title.remove", { display: over }, null);
  assert.strictEqual(
    line,
    `title remove epithet ${"名".repeat(64)} confirm`
  );
  assert.ok(line.length <= Echo.MAX_LINE_LENGTH);
});

test("combat.cast echoes explicit multi-target labels in payload order (D3b)", () => {
  const line = Echo.commandLine(
    "combat.cast",
    { skill_key: "wind_blade", target_ids: ["goblin_1", "orc_2"] },
    { skillLabel: "風刃術", targetLabels: ["哥布林", "獸人"] }
  );
  assert.strictEqual(line, "cast 風刃術=哥布林、獸人");
});

test("combat.cast bounds multi-target labels and prefers shorthand over them", () => {
  const huge = "太".repeat(Echo.MAX_LABEL_LENGTH + 10);
  const line = Echo.commandLine(
    "combat.cast",
    { skill_key: "wind_blade", target_ids: ["a", "b"] },
    { skillLabel: "風", targetLabels: [huge, "乙"] }
  );
  assert.ok(line !== null);
  assert.ok(line.length <= Echo.MAX_LINE_LENGTH);
  const shorthand = Echo.commandLine(
    "combat.cast",
    { skill_key: "wind_blade", target_shorthand: "all-enemies", target_ids: ["a"] },
    { skillLabel: "風", targetLabels: ["甲", "乙"] }
  );
  assert.strictEqual(shorthand, "cast 風=all-enemies");
});

test("combat.cast with empty or non-array targetLabels falls back like before", () => {
  assert.strictEqual(
    Echo.commandLine("combat.cast", { skill_key: "k" }, { skillLabel: "風", targetLabels: [] }),
    "cast 風"
  );
  assert.strictEqual(
    Echo.commandLine("combat.cast", { skill_key: "k" }, { skillLabel: "風", targetLabels: "甲" }),
    "cast 風"
  );
});

test("options.dismiss is a declared silent presentation control", () => {
  assert.ok(Echo.SILENT_PRESENTATION_CONTROLS.indexOf("options.dismiss") !== -1);
  assert.ok(Echo.SILENT_PRESENTATION_CONTROLS.indexOf("creation.roll_name") !== -1);
  assert.strictEqual(Echo.isSilentPresentationControl("options.dismiss"), true);
  assert.strictEqual(
    Echo.commandLine("options.dismiss", {}, { npcLabel: "老闆" }),
    null,
    "the silence is by declaration, not an accidental missing resolver"
  );
});

// Coverage invariant (webclient-input-narrative, design D5): every action id
// registered in `web/webclient/actions/registry.py` resolves to a bounded
// line from this pinned fixture or appears on the declared silent list. The
// shared manifest `command_echo_coverage_manifest.json` is the single id
// source for this suite, the Vitest per-surface table
// (web/webclient-app/tests/store/command_echo_surfaces.test.js), and the
// Python registry pin (web/webclient/actions/tests/
// test_action_catalog_coverage.py), so a newly registered action cannot ship
// with a silent catalog gap.
const COVERAGE_MANIFEST = require("./command_echo_coverage_manifest.json");

const REGISTERED_MUTATION_ACTIONS = {
  "combat.cast": { payload: { skill_key: "wind_blade" }, display: { skillLabel: "風刃術" } },
  "character.persona.update": { payload: { field: "habit", text: "清晨練劍" }, display: {} },
  "combat.flee": { payload: {}, display: { actionLabel: "逃跑" } },
  "combat.forfeit": { payload: {}, display: {} },
  "creation.activate": { payload: {}, display: { presetKey: "elf_mage" } },
  "creation.concept": { payload: { concept: "流浪學者" }, display: {} },
  "creation.custom": { payload: {}, display: {} },
  "creation.preset": { payload: { preset_key: "elf_mage" }, display: {} },
  "creation.reset": { payload: {}, display: { actionLabel: "清除草稿" } },
  "creation.roll_name": null,
  "explore.engage": { payload: {}, display: { targetLabel: "哥布林" } },
  "explore.look": { payload: { room: true }, display: { room: true } },
  "explore.move": { payload: { exit_ref: "e1", current_node: "n1" }, display: { exitLabel: "北門" } },
  "explore.party_invite": { payload: { npc_id: "bard" }, display: { npcLabel: "吟遊詩人" } },
  "explore.party_leave": { payload: { npc_id: "bard" }, display: { npcLabel: "吟遊詩人" } },
  "explore.talk_freeform": { payload: { npc_id: "bard", speech: "你好" }, display: { npcLabel: "吟遊詩人" } },
  "explore.talk_scripted": { payload: { npc_id: "bard", keyword_id: "guild" }, display: { npcLabel: "吟遊詩人", keywordLabel: "公會" } },
  "explore.wait": { payload: { daypart: "dusk" }, display: {} },
  "guild.exam_start": { payload: { target_rank: "正式會員" }, display: {} },
  "guild.quest_abandon": { payload: { quest_id: "quest_1" }, display: {} },
  "guild.quest_accept": { payload: { definition_key: "escort" }, display: {} },
  "guild.quest_track": { payload: { quest_id: "quest_1", tracked: true }, display: {} },
  "guild.quest_turnin": { payload: { quest_id: "quest_1" }, display: {} },
  "guild.register": { payload: {}, display: {} },
  "inventory.toggle_equip": { payload: { item_key: "leather_vest" }, display: {} },
  "inventory.use": { payload: { item_key: "healing_potion" }, display: {} },
  "options.dismiss": null,
  "shop.buy": { payload: { item_key: "healing_potion", quantity: 2 }, display: { itemLabel: "治療藥水" } },
  "shop.sell": { payload: { item_key: "healing_potion", quantity: 1 }, display: { itemLabel: "治療藥水" } },
  "title.accept": { payload: { index: 2 }, display: {} },
  "title.decline": { payload: {}, display: {} },
  "title.equip": { payload: { kind: "fixed", identifier: "g_f_rank" }, display: {} },
  "title.remove": { payload: { display: "夜襲之人" }, display: {} },
};

test("every registered mutation action resolves non-null or is declared silent", () => {
  const manifestIds = COVERAGE_MANIFEST.registeredMutationActionIds.slice().sort();
  const fixtureIds = Object.keys(REGISTERED_MUTATION_ACTIONS).sort();
  assert.deepStrictEqual(
    fixtureIds,
    manifestIds,
    "the catalog coverage fixture must cover exactly the manifest's registered ids"
  );
  for (const actionId of fixtureIds) {
    const fixture = REGISTERED_MUTATION_ACTIONS[actionId];
    if (fixture === null) {
      assert.ok(
        COVERAGE_MANIFEST.silentPresentationControlIds.indexOf(actionId) !== -1,
        `${actionId} must appear on the manifest's silent list`
      );
      assert.ok(
        Echo.isSilentPresentationControl(actionId),
        `${actionId} must be on the catalog's declared silent list`
      );
      assert.strictEqual(Echo.commandLine(actionId, {}, {}), null);
      continue;
    }
    assert.ok(
      !Echo.isSilentPresentationControl(actionId),
      `${actionId} must not be declared silent`
    );
    const line = Echo.commandLine(actionId, fixture.payload, fixture.display);
    assert.ok(
      typeof line === "string" && line.trim() !== "",
      `${actionId} must resolve to a non-empty display line`
    );
    assert.ok(line.length <= Echo.MAX_LINE_LENGTH);
  }
});

test("the silent list contains only registered presentation controls", () => {
  assert.deepStrictEqual(
    Echo.SILENT_PRESENTATION_CONTROLS,
    COVERAGE_MANIFEST.silentPresentationControlIds,
    "adding a silent control is a spec-reviewed decision (manifest + catalog together)"
  );
});
