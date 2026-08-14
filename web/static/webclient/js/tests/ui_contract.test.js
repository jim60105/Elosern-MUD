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
  // The drawer component (goldenlayout.js) owns the single send path.
  const drawer = read("web/static/webclient/js/plugins/goldenlayout.js");
  // The drawer is explicitly an ordinary-text path.
  assert.match(drawer, /plugin_handler\.onSend/);
  assert.match(drawer, /Evennia\.msg\("text"/);
  // No ui_action envelope is ever built or sent by the drawer path.
  assert.strictEqual(
    /Evennia\.msg\(\s*["']ui_action["']/.test(drawer),
    false,
    "drawer must not send ui_action"
  );
  assert.strictEqual(
    /msg\(\s*["']ui_action["']/.test(drawer),
    false,
    "drawer must never construct a ui_action message"
  );
});

test("elosern_ui no longer binds a bare document keydown listener", () => {
  const source = read("web/static/webclient/js/plugins/elosern_ui.js");
  // Key routing runs through the plugin `onKeydown` contract, not a direct
  // document listener; the only document-level listeners that remain are the
  // stock plugins' capture-phase modal-capture exceptions (services quantity,
  // exploration rest, creation form), which live in the docks, not here.
  assert.strictEqual(
    /document\.addEventListener\(\s*["']keydown["']/.test(source),
    false,
    "elosern_ui must route keydown through the plugin contract"
  );
  // The plugin exposes the hook and claims exactly what the router consumed.
  assert.match(source, /onKeydown:\s*routeKeyboard/);
  // The drawer owns the send path; no duplicate send implementation remains.
  assert.strictEqual(
    /sendDrawerText/.test(source),
    false,
    "the duplicated send path must be gone"
  );
  // The delegated pointer bridge is installed once at init.
  assert.match(source, /installPointerBridge\(\)/);
});

test("goldenlayout inserts text through text APIs, not HTML", () => {
  const source = read("web/static/webclient/js/plugins/goldenlayout.js");
  assert.ok(/createTextNode/.test(source));
  assert.ok(/innerHTML/.test(source) === false, "no innerHTML interpolation");
});

test("the narrative markup pipeline never parses HTML strings", () => {
  const plugins = [
    "web/static/webclient/js/plugins/goldenlayout.js",
    "web/static/webclient/js/plugins/elosern_ui.js",
  ];
  const markup = "web/static/webclient/js/elosern/narrative_markup.js";
  const forbidden = [
    "DOMParser",
    "insertAdjacentHTML",
    "outerHTML",
    "createContextualFragment",
    "document.write",
    "eval",
  ];
  for (const rel of plugins) {
    const source = read(rel);
    for (const api of forbidden) {
      assert.strictEqual(
        source.includes(api),
        false,
        `${rel} must never use ${api}`
      );
    }
  }
  const tokenizer = read(markup);
  for (const api of forbidden) {
    assert.strictEqual(
      tokenizer.includes(api),
      false,
      `${markup} must never use ${api}`
    );
  }
  // The tokenizer is DOM-independent: no document reference at all.
  assert.strictEqual(
    /document\./.test(tokenizer),
    false,
    "narrative_markup.js stays DOM-independent"
  );
  // No innerHTML on the narrative path either (goldenlayout already asserted;
  // the tokenizer must be clean too).
  assert.strictEqual(
    tokenizer.includes("innerHTML"),
    false,
    "narrative_markup.js must never use innerHTML"
  );
});

test("narrative preserves scrollback position with an unread count", () => {
  const source = read("web/static/webclient/js/plugins/goldenlayout.js");
  assert.match(source, /narrativeUnread/);
  assert.match(source, /wasAtBottom/);
});

test("drawer field Enter routes through the plugin onKeydown contract", () => {
  const source = read("web/static/webclient/js/plugins/elosern_ui.js");
  // The routing gate treats the drawer's own field as the open drawer
  // (pointer-focused field: Enter sends, Escape restores dock focus).
  assert.match(source, /isDrawerField\(event\.target\)/);
  assert.match(source, /drawer\.isOpen\(\) \|\| isDrawerField\(/);
  // No direct listener is bound on the field: exactly one send path exists,
  // owned by the drawer component and dispatched through the plugin handler.
  assert.strictEqual(
    /document\.addEventListener\(\s*["']keydown["']/.test(source),
    false,
    "keydown must keep flowing through the plugin contract"
  );
  const drawer = read("web/static/webclient/js/plugins/goldenlayout.js");
  const sendOccurrences = (drawer.match(/plugin_handler\.onSend\(text\)/g) || []).length;
  assert.strictEqual(
    sendOccurrences,
    1,
    "the drawer must own exactly one send implementation"
  );
});

test("the rest-duration form never swallows keys typed in the drawer field", () => {
  const source = read("web/static/webclient/js/plugins/exploration_dock.js");
  assert.match(source, /closest\(\s*["']\.inputfieldwrapper["']\s*\)/);
});

test("seal-red small text is never used on dark surfaces", () => {
  // The deep seal-red token (≈2.9:1 on ink) is restricted to fills, borders,
  // and large/bold text and symbols. A dark-surface `color:` declaration that
  // uses the token -- or its raw hex -- would fail the contrast floor, so the
  // repository contract rejects it. The only deep seal-red *text* uses are
  // the current map node (large/bold with a shape companion) and the offline
  // overlay title (1.4rem bold).
  const files = [
    "web/static/webclient/css/elosern.css",
    "web/static/webclient/css/goldenlayout.css",
  ];
  // The project CSS is hand-written and unminified: rules end at the first
  // `}` that closes the opening `{`, and no declaration string contains a
  // literal `{` or `}`.
  function selectorsWithRedTextColor(css) {
    const selectors = [];
    const pattern = /([^{}]*)\{([^{}]*)\}/g;
    let match;
    while ((match = pattern.exec(css)) !== null) {
      const selector = match[1].trim();
      const body = match[2];
      // A declaration-boundary match so `border-left-color:
      // var(--elm-vermilion)` (an approved border role) is not mistaken for
      // a text color.
      if (/(?:^|[;\n])\s*color:\s*var\(--elm-vermilion/.test(body)) {
        selectors.push(selector);
      }
    }
    return selectors;
  }
  for (const rel of files) {
    const css = read(rel);
    for (const selector of selectorsWithRedTextColor(css)) {
      assert.match(
        selector,
        /node-current|offline-title/,
        `${rel}: deep seal-red text is allowed only on the current map node and the offline title (large/bold roles); offending rule selector: ${selector}`
      );
    }
    assert.strictEqual(
      /(?:^|[;\n])\s*color:\s*#a9322a/.test(css),
      false,
      `${rel}: the raw deep seal-red hex must never be used as text color`
    );
  }
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

test("creation form claims its keydowns without breaking native input", () => {
  const source = read("web/static/webclient/js/plugins/creation_dock.js");
  // The capture-phase form handler claims every keydown while the form owns
  // focus (design D6) so no unclaimed keydown reaches the stock handler...
  assert.match(source, /_formKeyBound/);
  assert.match(source, /stopPropagation/);
  // ...while never preventing Tab, modifier keys, or IME composition, so
  // native focus movement, text input, and Chinese IME keep working.
  assert.match(source, /event\.key === "Tab"/);
  assert.match(source, /event\.isComposing/);
  assert.match(source, /\.inputfieldwrapper/);
  // The form action buttons are pointer-operable through the shared
  // in-flight / awaiting-revision gate and the exact-once click detail check.
  assert.match(source, /form\.addEventListener\("click"/);
  assert.match(source, /isMutationInFlight/);
  assert.match(source, /isAwaitingRevision/);
  assert.match(source, /event\.detail !== 1/);
});

test("creation form requires a subrace and shows the allocation briefing", () => {
  const menu = read("web/static/webclient/js/elosern/creation_menu.js");
  const dock = read("web/static/webclient/js/plugins/creation_dock.js");
  // The "無子種族" radio is gone and a missing subrace is an advisory error.
  assert.strictEqual(/subrace-none/.test(menu), false, "no subrace-none item");
  assert.strictEqual(/無子種族/.test(dock), false, "no 無子種族 radio");
  assert.match(menu, /errors\.subrace/);
  // The allocation briefing facts are derived from the server profile.
  assert.match(menu, /briefingFor/);
  assert.match(menu, /六項配點總和必須恰好等於/);
  assert.match(dock, /配點說明：共 /);
  assert.match(dock, /briefing\.rule/);
  // The bounded background field is part of the custom form.
  assert.match(dock, /背景設定（風味文字）/);
  assert.match(menu, /background: ""/);
});
