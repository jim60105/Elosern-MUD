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

test("creation dock and menu insert text via text APIs and never trust HTML", () => {
  const dock = read("web/static/webclient/js/plugins/creation_dock.js");
  const menu = read("web/static/webclient/js/elosern/creation_menu.js");
  assert.ok(/createTextNode/.test(dock), "dock inserts text through text APIs");
  for (const source of [dock, menu]) {
    assert.strictEqual(/innerHTML/.test(source), false, "no innerHTML interpolation");
  }
  // The DOM-independent menu model never touches the document at load time.
  assert.strictEqual(/document\./.test(menu), false, "menu stays DOM-independent");
});

test("creation dock and menu never write canonical or draft state to localStorage", () => {
  const dock = read("web/static/webclient/js/plugins/creation_dock.js");
  const menu = read("web/static/webclient/js/elosern/creation_menu.js");
  for (const source of [dock, menu]) {
    assert.strictEqual(
      /localStorage/.test(source),
      false,
      "creation state must never be stored client-side"
    );
  }
});

test("creation dock adult fields advertise the 18 minimum", () => {
  const source = read("web/static/webclient/js/plugins/creation_dock.js");
  assert.match(source, /實際年齡（至少 18）/);
  assert.match(source, /外表年齡（至少 18）/);
});
