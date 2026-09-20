/*
 * lineage panel: JS validator mirror boundary tests.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_FIREARROW, T_FIRE_LABEL, T_SKILL_LABEL } = require("./protocol_support.js");


function validLineageNode(key, overrides) {
  return Object.assign(
    {
      skill_key: key,
      display_name_zh: T_SKILL_LABEL,
      owned: true,
      usable: true,
      level: 1,
      xp_into_level: 23,
      xp_to_next_level: 27,
      capped: false,
      prereq_text_zh: "",
    },
    overrides || {}
  );
}

function validLineageChain(root, nodeCount, overrides) {
  const count = nodeCount === undefined ? 2 : nodeCount;
  const nodes = count >= 1 ? [validLineageNode(root)] : [];
  for (let index = 1; index < count; index += 1) {
    nodes.push(validLineageNode(`${root}_n${index}`));
  }
  return Object.assign(
    {
      root_skill_key: root,
      element_or_style_zh: T_FIRE_LABEL,
      consumed: false,
      meter: 0.5,
      nodes: nodes,
    },
    overrides || {}
  );
}

function validLineagePanel(chains, completed, total) {
  const list = chains === undefined ? [validLineageChain(T_FIREARROW)] : chains;
  return {
    schema_version: 1,
    available: true,
    kind: "lineage",
    completed_count: completed === undefined ? 0 : completed,
    total_count: total === undefined ? list.length : total,
    chains: list,
  };
}

test("lineage validates the minimal available payload and pins its caps", () => {
  assert.equal(Protocol.LINEAGE_MAX_CHAINS, 16);
  assert.equal(Protocol.LINEAGE_MAX_NODES_PER_CHAIN, 32);
  assert.equal(Protocol.LINEAGE_MAX_TEXT, 128);
  const normalized = Protocol.validatePanel(
    "lineage",
    Protocol.PANEL_ALLOWLIST.lineage,
    validLineagePanel()
  );
  assert.equal(normalized.kind, "lineage");
  assert.equal(normalized.chains[0].root_skill_key, T_FIREARROW);
});

test("lineage rejects a wrong kind or schema_version", () => {
  assert.throws(() =>
    Protocol.validateLineagePanel(Object.assign(validLineagePanel(), { kind: "character" }))
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(Object.assign(validLineagePanel(), { schema_version: 2 }))
  );
  assert.throws(() =>
    Protocol.validateLineagePanel({ ...validLineagePanel(), extra: true })
  );
});

test("lineage rejects completed_count above total_count", () => {
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel(undefined, 2, 1)));
});

test("lineage available form rejects a false or non-boolean discriminator", () => {
  // Rubber-duck R2-2: the exported validator must mirror Python's
  // validate_lineage, which requires available === true in this form.
  assert.throws(() =>
    Protocol.validateLineagePanel(Object.assign(validLineagePanel(), { available: false }))
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(Object.assign(validLineagePanel(), { available: "true" }))
  );
});

test("lineage caps chain and node counts at the mirrored bounds", () => {
  const atCap = [];
  for (let index = 0; index < Protocol.LINEAGE_MAX_CHAINS; index += 1) {
    atCap.push(validLineageChain(`root_${index}`, 1));
  }
  assert.doesNotThrow(() => Protocol.validateLineagePanel(validLineagePanel(atCap)));
  atCap.push(validLineageChain("root_over", 1));
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel(atCap)));

  assert.doesNotThrow(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([
        validLineageChain("root_a", Protocol.LINEAGE_MAX_NODES_PER_CHAIN),
      ])
    )
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([
        validLineageChain("root_a", Protocol.LINEAGE_MAX_NODES_PER_CHAIN + 1),
      ])
    )
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(validLineagePanel([validLineageChain("root_a", 0)]))
  );
});

test("lineage bounds text lengths and the meter range", () => {
  const tooLong = "測".repeat(Protocol.LINEAGE_MAX_TEXT + 1);
  assert.throws(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([
        validLineageChain("root_a", 1, {
          nodes: [validLineageNode("root_a", { display_name_zh: tooLong })],
        }),
      ])
    )
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([
        validLineageChain("root_a", 1, {
          nodes: [validLineageNode("root_a", { prereq_text_zh: tooLong })],
        }),
      ])
    )
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(
      validLineagePanel([validLineageChain("root_a", 1, { element_or_style_zh: tooLong })])
    )
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(validLineagePanel([validLineageChain("root_a", 2, { meter: 1.1 })]))
  );
  assert.throws(() =>
    Protocol.validateLineagePanel(validLineagePanel([validLineageChain("root_a", 2, { meter: -0.1 })]))
  );
});

test("lineage truncated chains keep their root head", () => {
  const chain = validLineageChain("root_a", 2);
  chain.nodes = chain.nodes.slice(1);
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel([chain])));
});

test("lineage byte budget fails closed on the theoretical worst case", () => {
  // All ceilings at once serialize past the 65,536-byte envelope; the
  // validator enforces serialized size (the presenter truncates instead).
  const chains = [];
  for (let index = 0; index < Protocol.LINEAGE_MAX_CHAINS; index += 1) {
    const root = `root_${index}`;
    const nodes = [];
    for (let nodeIndex = 0; nodeIndex < Protocol.LINEAGE_MAX_NODES_PER_CHAIN; nodeIndex += 1) {
      nodes.push(
        validLineageNode(nodeIndex === 0 ? root : `n${index}_${nodeIndex}`, {
          display_name_zh: "測".repeat(Protocol.LINEAGE_MAX_TEXT),
        })
      );
    }
    chains.push(validLineageChain(root, 1, { nodes: nodes }));
  }
  assert.throws(() => Protocol.validateLineagePanel(validLineagePanel(chains)));
});

test("lineage unavailable form validates through the common discriminator", () => {
  const unavailable = {
    schema_version: 1,
    available: false,
    reason: { code: "lineage_unavailable", message: "技能系譜目前無法顯示" },
  };
  assert.deepEqual(
    Protocol.validatePanel("lineage", Protocol.PANEL_ALLOWLIST.lineage, unavailable),
    unavailable
  );
});

