const { test } = require("node:test");
const assert = require("node:assert/strict");
const TextConsole = require("../text_console.js");

test("createModel buffers output and input lines in order", () => {
  const model = TextConsole.createModel();
  model.appendOut("room line 1");
  model.appendIn("look");
  model.appendOut("room line 2");
  assert.deepEqual(model.lines(), [
    { kind: "out", body: "room line 1" },
    { kind: "in", body: "look" },
    { kind: "out", body: "room line 2" },
  ]);
});

test("createModel trims to the line cap keeping the tail", () => {
  const model = TextConsole.createModel(3);
  for (let i = 0; i < 5; i += 1) model.appendOut(`line ${i}`);
  model.appendIn("cmd");
  const lines = model.lines();
  assert.equal(lines.length, 3);
  assert.deepEqual(
    lines.map((l) => l.body),
    ["line 3", "line 4", "cmd"],
  );
});

test("createModel tracks transport status transitions", () => {
  const model = TextConsole.createModel();
  assert.equal(model.status(), "offline");
  model.setConnected(true);
  assert.equal(model.status(), "waiting");
  model.setLoggedIn(true);
  assert.equal(model.status(), "ready");
  model.setConnected(false);
  assert.equal(model.status(), "offline");
  model.appendOut("before");
  model.reset();
  assert.deepEqual(model.lines(), []);
});

test("setPrompt stores the latest prompt only", () => {
  const model = TextConsole.createModel();
  model.setPrompt("甲> ");
  model.setPrompt("乙> ");
  assert.equal(model.prompt(), "乙> ");
});

test("MAX_LINES is the documented default cap", () => {
  assert.equal(TextConsole.MAX_LINES, 500);
});
