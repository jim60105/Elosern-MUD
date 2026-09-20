/*
 * title_ballot panel v1 mirror: ballots, voting payloads, rejections.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { VALID_EPOCH, serverTime } = require("./protocol_support.js");


function validTitleBallotCandidate(index, overrides) {
  return Object.assign(
    { index: index, display: "破城先鋒", basis: "率先破門。" },
    overrides || {}
  );
}

function validTitleBallotPanel(count) {
  var candidates = [];
  for (var i = 1; i <= (count === undefined ? 3 : count); i++) {
    candidates.push(validTitleBallotCandidate(i));
  }
  return {
    schema_version: 1,
    available: true,
    kind: "title_ballot",
    candidates: candidates,
  };
}

test("title_ballot accepts the idle zero-candidate and full three-candidate forms", () => {
  for (const count of [0, 1, 2, 3]) {
    const panel = validTitleBallotPanel(count);
    assert.deepEqual(Protocol.validateTitleBallotPanel(panel), panel);
    assert.doesNotThrow(() =>
      Protocol.validatePanel("title_ballot", Protocol.PANEL_ALLOWLIST.title_ballot, panel)
    );
  }
});

test("title_ballot accepts the common unavailable form at its registered version", () => {
  const unavailable = {
    schema_version: 1,
    available: false,
    reason: { code: "ballot_unavailable", message: "異名提名目前無法顯示" },
  };
  assert.deepEqual(
    Protocol.validatePanel("title_ballot", Protocol.PANEL_ALLOWLIST.title_ballot, unavailable),
    unavailable
  );
  assert.throws(() =>
    Protocol.validatePanel("title_ballot", Protocol.PANEL_ALLOWLIST.title_ballot, {
      schema_version: 2,
      available: false,
      reason: { code: "ballot_unavailable", message: "異名提名目前無法顯示" },
    })
  );
});

test("title_ballot enforces the exact field sets, version, and kind", () => {
  assert.throws(() => Protocol.validateTitleBallotPanel("not-a-panel"));
  assert.throws(() =>
    Protocol.validateTitleBallotPanel({ ...validTitleBallotPanel(), extra: 1 })
  );
  const missing = validTitleBallotPanel();
  delete missing.candidates;
  assert.throws(() => Protocol.validateTitleBallotPanel(missing));
  assert.throws(() =>
    Protocol.validateTitleBallotPanel({ ...validTitleBallotPanel(), kind: "services" })
  );
  assert.throws(() =>
    Protocol.validateTitleBallotPanel({ ...validTitleBallotPanel(), schema_version: 2 })
  );
  assert.throws(() =>
    Protocol.validateTitleBallotPanel(
      { ...validTitleBallotPanel(), candidates: [validTitleBallotCandidate(1, { extra: 1 })] }
    )
  );
  assert.throws(() =>
    Protocol.validateTitleBallotPanel(
      { ...validTitleBallotPanel(), candidates: [{ index: 1, display: "破城先鋒" }] }
    )
  );
});

test("title_ballot candidate indices must be strictly one-based ascending", () => {
  for (const candidates of [
    [validTitleBallotCandidate(0)],
    [validTitleBallotCandidate(2)],
    [validTitleBallotCandidate(1), validTitleBallotCandidate(1)],
    [validTitleBallotCandidate(2), validTitleBallotCandidate(1)],
    [validTitleBallotCandidate(1), validTitleBallotCandidate(3)],
    [{ index: "1", display: "破城先鋒", basis: "率先破門。" }],
    [{ index: true, display: "破城先鋒", basis: "率先破門。" }],
  ]) {
    assert.throws(() =>
      Protocol.validateTitleBallotPanel({ ...validTitleBallotPanel(), candidates })
    );
  }
  const tooMany = [];
  for (let i = 1; i <= Protocol.TITLE_BALLOT_MAX_CANDIDATES + 1; i++) {
    tooMany.push(validTitleBallotCandidate(i));
  }
  assert.throws(() =>
    Protocol.validateTitleBallotPanel({ ...validTitleBallotPanel(), candidates: tooMany })
  );
});

test("title_ballot enforces the display and basis code-point ceilings", () => {
  const atCaps = validTitleBallotPanel();
  atCaps.candidates = [
    validTitleBallotCandidate(1, {
      display: "長".repeat(Protocol.TITLE_BALLOT_MAX_DISPLAY),
      basis: "援".repeat(Protocol.TITLE_BALLOT_MAX_BASIS),
    }),
  ];
  assert.doesNotThrow(() => Protocol.validateTitleBallotPanel(atCaps));
  for (const bad of [
    validTitleBallotCandidate(1, {
      display: "長".repeat(Protocol.TITLE_BALLOT_MAX_DISPLAY + 1),
    }),
    validTitleBallotCandidate(1, { basis: "援".repeat(Protocol.TITLE_BALLOT_MAX_BASIS + 1) }),
    validTitleBallotCandidate(1, { display: "" }),
    validTitleBallotCandidate(1, { basis: "" }),
    validTitleBallotCandidate(1, { display: 7 }),
    validTitleBallotCandidate(1, { basis: null }),
  ]) {
    assert.throws(() =>
      Protocol.validateTitleBallotPanel({
        ...validTitleBallotPanel(),
        candidates: [bad],
      })
    );
  }
});

test("title_ballot is in the production panel allowlist and a bad panel rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.title_ballot, 1);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "exploration",
    panels: {
      title_ballot: { ...validTitleBallotPanel(), kind: "bogus" },
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.validateSnapshot(envelope));
  envelope.panels.title_ballot = validTitleBallotPanel();
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
  envelope.panels = {
    title_ballot: {
      schema_version: 1,
      available: true,
      kind: "title_ballot",
      candidates: [validTitleBallotCandidate(1)],
    },
  };
  envelope.revision = 6;
  assert.doesNotThrow(() => Protocol.validateUpdate(envelope));
});

