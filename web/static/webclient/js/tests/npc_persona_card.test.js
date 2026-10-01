const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const NpcPersonaCard = require("../elosern/npc_persona_card.js");

const FIXTURES_PATH = path.resolve(
  __dirname,
  "../../../../../world/lore/tests/fixtures/npc_card_boundary_cases.json"
);

test("NpcPersonaCard fixture cases match server contract exactly", () => {
  const cases = JSON.parse(fs.readFileSync(FIXTURES_PATH, "utf-8"));

  for (const c of cases) {
    const raw = JSON.parse(JSON.stringify(c.card));

    if (c.use_astral_600_field) {
      raw[c.use_astral_600_field] = "😀".repeat(600);
    } else if (c.use_leaf_601_field) {
      raw[c.use_leaf_601_field] = "A".repeat(601);
    } else if (c.override_identity_overflow) {
      raw.identity = {
        public: "公".repeat(300),
        hidden: "隱".repeat(300),
      };
    } else if (c.override_total_overflow) {
      raw.identity = { public: "公開", hidden: "隱秘" };
      for (const fKey of [
        "appearance",
        "personality",
        "speech_style",
        "life_story",
        "habit",
        "social_connection",
      ]) {
        raw[fKey] = "字".repeat(330);
      }
    } else if (c.override_all_leaves_600) {
      raw.identity = { public: "公".repeat(600), hidden: "隱".repeat(600) };
      for (const fKey of [
        "appearance",
        "personality",
        "speech_style",
        "life_story",
        "habit",
        "social_connection",
      ]) {
        raw[fKey] = "字".repeat(600);
      }
    }

    if (c.expected_valid) {
      const normalized = NpcPersonaCard.normalizeCard(raw);
      assert.ok(normalized, `Case ${c.name} should be valid`);
      if (c.expected_public !== undefined) {
        assert.equal(normalized.identity.public, c.expected_public);
      }
      if (c.expected_hidden !== undefined) {
        assert.equal(normalized.identity.hidden, c.expected_hidden);
      }
      if (c.expected_appearance !== undefined) {
        assert.equal(normalized.appearance, c.expected_appearance);
      }
      if (c.expected_social_connection !== undefined) {
        assert.equal(normalized.social_connection, c.expected_social_connection);
      }
    } else {
      let threw = false;
      try {
        NpcPersonaCard.normalizeCard(raw);
      } catch (err) {
        threw = true;
        assert.equal(
          err.code,
          c.expected_code,
          `Case ${c.name} code mismatch: expected ${c.expected_code}, got ${err.code}`
        );
        assert.equal(
          err.field,
          c.expected_field,
          `Case ${c.name} field mismatch: expected ${c.expected_field}, got ${err.field}`
        );
      }
      assert.ok(threw, `Case ${c.name} should have thrown`);
    }
  }
});
