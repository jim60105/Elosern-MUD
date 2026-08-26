/*
 * Repository contract tests for the WebClient drawer and narrative text path
 * (foundation section 5.4/5.5).
 *
 * These verify source-level contracts that are hard to exercise in a browser
 * here: the command drawer sends only ordinary text, never a `ui_action`
 * envelope, and server-authored labels are inserted as text, never as HTML.
 *
 * After the Vue migration (D1), the legacy `js/plugins/*` view files are
 * deleted; the contracts now point at the Vue SPA sources (webclient-app) and
 * the preserved DOM-independent `js/elosern/*` logic.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..", "..", "..", "..", "..");

function read(rel) {
  return fs.readFileSync(path.join(ROOT, rel), "utf8");
}

test("the command line sends ordinary text, never a ui_action envelope", () => {
  // H5 (webclient-hud-05-overlays-and-command-line): the command drawer was
  // retired for the permanently-present command line; its single send intent
  // (`submit(text)`) still routes through the store's text transport
  // (Evennia.msg("text", ...)), never a ui_action envelope.
  const line = read("web/webclient-app/components/CommandLine.vue");
  assert.match(line, /defineEmits\(\["submit", "focus-parent", "open-overlay", "focus-lost"\]\)/);
  assert.match(line, /emit\("submit", text\)/);
  assert.strictEqual(
    /ui_action/.test(line),
    false,
    "the command line must not construct or reference a ui_action envelope"
  );
  const store = read("web/webclient-app/stores/elosern.js");
  assert.match(store, /function dispatchAction\(/);
  assert.match(store, /function sendText\(/);
});

test("the Vue keyboard router wraps the preserved DOM-independent router", () => {
  // The C2 bridge installs a managed document listener; the actual key
  // routing lives in the preserved `js/elosern/keyboard_router.js`, re-exposed
  // through the Vite CommonJS-interop ESM wrapper (design D1).
  const wrapper = read("web/webclient-app/lib/keyboard_router.js");
  assert.match(wrapper, /import KeyboardRouter from "..\/..\/static\/webclient\/js\/elosern\/keyboard_router\.js"/);
  assert.match(wrapper, /export default KeyboardRouter;/);
});

test("narrative feed keeps scrollback position with an unread count", () => {
  const source = read("web/webclient-app/components/NarrativeFeed.vue");
  assert.match(source, /wasAtBottom/);
  assert.match(source, /scrollToBottom/);
  assert.match(source, /unread/);
  // Server-authored narrative text is rendered through Vue bindings, not HTML.
  assert.strictEqual(/innerHTML/.test(source), false, "no innerHTML on the narrative path");
});

test("the narrative markup pipeline never parses HTML strings", () => {
  const markup = "web/static/webclient/js/elosern/narrative_markup.js";
  const forbidden = [
    "DOMParser",
    "insertAdjacentHTML",
    "outerHTML",
    "createContextualFragment",
    "document.write",
    "eval",
  ];
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
  // No innerHTML on the narrative path either (the tokenizer must be clean too).
  assert.strictEqual(
    tokenizer.includes("innerHTML"),
    false,
    "narrative_markup.js must never use innerHTML"
  );
});

test("the rest-duration form claims its keydowns without breaking native input", () => {
  const source = read("web/webclient-app/components/RestForm.vue");
  // The capture-phase form handler claims the form's keys so the global
  // keyboard router does not swallow them (the legacy isEditingRestForm gate).
  assert.match(source, /@keydown="onKeyDown"/);
  assert.match(source, /event\.stopPropagation\(\)/);
  // Digits, Backspace, Escape, Enter and the slash gate are all claimed and
  // prevented, so the value is collected in the browser and validated server-side.
  assert.match(source, /key >= "0" && key <= "9"/);
  assert.match(source, /key === "Escape"/);
  assert.match(source, /key === "\/"/);
});

test("suggestion cards and the dismiss control keep native activation", () => {
  // The routing gate defers to the browser default for Enter/Space pressed on
  // a focused suggestion card or dismiss button: the card click path is a
  // direct listener, never the KeyboardRouter, so the router must not claim
  // those keys (webclient-options-surface D4).
  const card = read("web/webclient-app/components/OptionCard.vue");
  assert.match(card, /class="option-card"/);
  assert.match(card, /@click="activate"/);
  const dock = read("web/webclient-app/components/ActionDock.vue");
  assert.match(dock, /suggestions-dismiss/);
  assert.match(dock, /✕ 清除建議/);
});

test("seal-red small text is never used on dark surfaces", () => {
  // The deep seal-red token (≈2.9:1 on ink) is restricted to fills, borders,
  // and large/bold text and symbols. A dark-surface `color:` declaration that
  // uses the token -- or its raw hex -- would fail the contrast floor, so the
  // repository contract rejects it.
  const files = [
    "web/webclient-app/styles/tokens.css",
    "web/webclient-app/styles/app-shell.css",
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
      // A declaration-boundary match so `border-color: var(--seal-600)` (an
      // approved border role) is not mistaken for a text color.
      if (/(?:^|[;\n])\s*color:\s*var\(--seal-600/.test(body)) {
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
        /offline-title|node-current/,
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

test("the creation overlay and preserved menu model insert text via text APIs", () => {
  const overlay = read("web/webclient-app/components/CreationOverlay.vue");
  const menu = read("web/static/webclient/js/elosern/creation_menu.js");
  for (const source of [overlay, menu]) {
    assert.strictEqual(/innerHTML/.test(source), false, "no innerHTML interpolation");
  }
  // The DOM-independent menu model never touches the document at load time.
  assert.strictEqual(/document\./.test(menu), false, "menu stays DOM-independent");
});

test("the creation form adult fields enforce the 18 minimum on both age fields", () => {
  const source = read("web/webclient-app/components/CreationOverlay.vue");
  assert.match(source, /const age = ref\(18\)/);
  assert.match(source, /const apparentAge = ref\(18\)/);
  assert.match(source, /Number\(age\.value\) >= minimumAge\.value && Number\(apparentAge\.value\) >= minimumApparentAge\.value/);
});

test("the scene backdrop reuses an in-flight scene image instead of refetching", () => {
  // The browser image-load-failure requirement forbids repeatedly fetching
  // the same scene URL. H1 moved the scene frame out of ArtPanel into
  // SceneBackdrop (the stage backdrop), so the no-refetch contract lives
  // there: a failed URL is remembered in `failedUrls` and not re-fetched;
  // a new scene URL resets the load-failure flag.
  const source = read("web/webclient-app/components/SceneBackdrop.vue");
  assert.match(source, /imageLoadFailed = ref\(false\)/);
  assert.match(source, /const failedUrls = new Set\(\)/);
  assert.match(source, /failedUrls\.add\(url\)/);
  // A failed URL resolves to null so the image element is not re-requested.
  assert.match(source, /if \(url && failedUrls\.has\(url\)/);
  // A new scene resets the load-failure flag (the generating prior image).
  assert.match(source, /imageLoadFailed\.value = false/);
  assert.match(source, /目前場景圖片生成中/);
});
