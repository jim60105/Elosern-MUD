// Node self-test for the synthetic data JS mirror
// (add-test-synthetic-data-kit). Proves the mirror loads, its exports
// deep-equal the canonical block embedded in the same file, and the two
// byte-identical mirror copies (vitest + node --test) carry the same
// canonical text — so drift in either copy goes red here, and the Python
// kit is checked against the same text by world/tests/test_synthetic_data.py.
// The support/ directory is deliberately excluded from the node --test glob.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  SYNTH_CANONICAL,
  SYNTH_CANONICAL_JSON,
  SYNTH_ITEM,
  SYNTH_PRESET,
  SYNTH_QUEST,
  SYNTH_SKILL,
  SYNTH_TITLE,
} from "./support/synthetic-data.js";

// web/static/webclient/js/tests/ -> web/webclient-app/tests/support/ (four up).
const SIBLING_MIRROR = "../../../../webclient-app/tests/support/synthetic-data.mjs";
// Assembled from fragments so this file's own source never matches it.
const CANON_PATTERN = new RegExp(
  ["export const SYNTH_", "CANONICAL", "_JSON = `([^`]*)`;"].join("")
);

function canonicalTextOf(source) {
  const matched = CANON_PATTERN.exec(source);
  assert.ok(matched, "mirror must embed the delimited canonical JSON block");
  return matched[1];
}

test("mirror exports deep-equal its own canonical block", () => {
  const parsed = JSON.parse(SYNTH_CANONICAL_JSON);
  assert.deepEqual(SYNTH_CANONICAL, parsed);
  assert.deepEqual(SYNTH_ITEM, parsed.SYNTH_ITEM);
  assert.deepEqual(SYNTH_SKILL, parsed.SYNTH_SKILL);
  assert.deepEqual(SYNTH_PRESET, parsed.SYNTH_PRESET);
  assert.deepEqual(SYNTH_QUEST, parsed.SYNTH_QUEST);
  assert.deepEqual(SYNTH_TITLE, parsed.SYNTH_TITLE);
});

test("the two mirror copies carry byte-identical canonical text", () => {
  const here = canonicalTextOf(
    readFileSync(new URL("./support/synthetic-data.js", import.meta.url), "utf8")
  );
  const sibling = canonicalTextOf(
    readFileSync(new URL(SIBLING_MIRROR, import.meta.url), "utf8")
  );
  assert.equal(here, sibling);
});

test("every mirrored identifier is a t_-keyed synthetic stand-in", () => {
  for (const [name, payload] of Object.entries(SYNTH_CANONICAL)) {
    const keys = ["id", "rank", "race", "subrace", "price_table"];
    for (const field of keys) {
      if (typeof payload[field] === "string") {
        assert.ok(
          payload[field].startsWith("t_"),
          `${name}.${field} must carry the reserved t_ prefix`
        );
      }
    }
  }
});
