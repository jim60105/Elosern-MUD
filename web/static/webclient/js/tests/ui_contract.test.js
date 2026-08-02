/*
 * Repository contract tests for the WebClient drawer and narrative text path
 * (foundation section 5.4/5.5).
 *
 * These verify source-level contracts that are hard to exercise in a browser
 * here: the command drawer sends only ordinary text, never a `ui_action`
 * envelope, and server-authored labels are inserted as text, never as HTML.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..", "..", "..", "..", "..");

function read(rel) {
  return fs.readFileSync(path.join(ROOT, rel), "utf8");
}

test("drawer plugin never constructs ui_action", () => {
  const source = read("web/static/webclient/js/plugins/elosern_ui.js");
  // The drawer is explicitly an ordinary-text path.
  assert.match(source, /plugin_handler\.onSend/);
  assert.match(source, /Evennia\.msg\("text"/);
  // No ui_action envelope is ever built or sent by the drawer plugin.
  assert.strictEqual(
    /\bui_action\b/.test(source),
    true,
    "drawer plugin mentions ui_action only in its explanatory comment"
  );
  assert.strictEqual(
    /Evennia\.msg\(\s*["']ui_action["']/.test(source),
    false,
    "drawer must not send ui_action"
  );
  assert.strictEqual(
    /msg\(\s*["']ui_action["']/.test(source),
    false,
    "drawer must never construct a ui_action message"
  );
});

test("goldenlayout inserts text through text APIs, not HTML", () => {
  const source = read("web/static/webclient/js/plugins/goldenlayout.js");
  assert.ok(/createTextNode/.test(source));
  assert.ok(/innerHTML/.test(source) === false, "no innerHTML interpolation");
});

test("narrative preserves scrollback position with an unread count", () => {
  const source = read("web/static/webclient/js/plugins/goldenlayout.js");
  assert.match(source, /narrativeUnread/);
  assert.match(source, /wasAtBottom/);
});
