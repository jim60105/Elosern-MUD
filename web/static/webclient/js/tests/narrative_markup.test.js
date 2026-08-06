/*
 * DOM-independent tests for the narrative markup allowlist tokenizer
 * (webclient-narrative-markup). Runs with Node 24's built-in test runner.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");

const Markup = require("../elosern/narrative_markup.js");

function kinds(source) {
  return Markup.tokenize(source).map((token) => token.kind);
}

function texts(source) {
  return Markup.tokenize(source)
    .filter((token) => token.kind === "text")
    .map((token) => token.value);
}

test("plain text and entities decode to a single text token", () => {
  const tokens = Markup.tokenize("南大道 &amp; 公會 &lt;tag&gt; &quot;q&quot; &#x27;x&#39; &nbsp;");
  assert.equal(tokens.length, 1);
  assert.equal(tokens[0].kind, "text");
  assert.equal(tokens[0].value, "南大道 & 公會 <tag> \"q\" 'x' \u00a0");
});

test("unknown entities stay literal", () => {
  assert.equal(texts("&amp;lt;")[0], "&lt;");
  assert.equal(texts("&bogus; &amp;bogus;")[0], "&bogus; &bogus;");
});

test("every br spelling produces a break token", () => {
  for (const spelling of ["<br>", "<br/>", "<br />"]) {
    const tokens = Markup.tokenize("a" + spelling + "b");
    assert.deepEqual(
      tokens.map((t) => t.kind),
      ["text", "break", "text"]
    );
  }
});

test("nested and adjacent spans keep their classes", () => {
  const tokens = Markup.tokenize(
    '<span class="color-009">a</span><span class="underline color-012">b</span><span class="bgcolor-021">c</span>'
  );
  const opens = tokens.filter((t) => t.kind === "open");
  assert.equal(opens.length, 3);
  assert.deepEqual(opens[0].classes, ["color-009"]);
  assert.deepEqual(opens[1].classes, ["underline", "color-012"]);
  assert.deepEqual(opens[2].classes, ["bgcolor-021"]);
  assert.deepEqual(kinds("x"), ["text"]);
});

test("class filtering keeps text while dropping the disallowed class", () => {
  const tokens = Markup.tokenize('<span class="color-014 evil color-9999">南大道</span>');
  const open = tokens.find((t) => t.kind === "open");
  assert.deepEqual(open.classes, ["color-014"]);
  const text = tokens.filter((t) => t.kind === "text").map((t) => t.value);
  assert.deepEqual(text, ["南大道"]);
});

test("truecolor style is accepted exactly for the two color declarations", () => {
  const tokens = Markup.tokenize(
    '<span class="" style="color: #ff0000;background-color: #00ff00;">x</span>'
  );
  const open = tokens.find((t) => t.kind === "open");
  assert.equal(open.style.color, "#ff0000");
  assert.equal(open.style.backgroundColor, "#00ff00");
});

test("truecolor style with only background-color is accepted", () => {
  const open = Markup.tokenize(
    '<span class="" style="background-color: #0a141e;">x</span>'
  ).find((t) => t.kind === "open");
  assert.equal(open.style.backgroundColor, "#0a141e");
  assert.equal(open.style.color, undefined);
});

test("non-hex, shorthand, extra-property, and malformed styles drop the whole attribute", () => {
  const badStyles = [
    'style="color: red;"',
    'style="color: #ff00;"',
    'style="color: #ff0000;font-size: 12px;"',
    'style="color: #ff0000; color: #00ff00;"',
    'style="border: 1px;"',
  ];
  for (const style of badStyles) {
    const open = Markup.tokenize('<span class="color-001" ' + style + ">x</span>").find(
      (t) => t.kind === "open"
    );
    assert.equal(open.style, null, "style must be dropped for " + style);
    assert.deepEqual(open.classes, ["color-001"], "classes must survive for " + style);
  }
});

test("unknown attribute degrades the whole tag to literal text", () => {
  const tokens = Markup.tokenize('<span class="color-009" onclick="x()">hi</span>');
  assert.deepEqual(
    tokens.map((t) => t.kind),
    ["text", "text", "text"]
  );
  assert.equal(tokens[0].value, '<span class="color-009" onclick="x()">');
  assert.equal(tokens[1].value, "hi");
  assert.equal(tokens[2].value, "</span>");
});

test("anchors degrade to their text content with no anchor token", () => {
  const mxpCommand =
    '<a id="mxplink" href="#" onclick="Evennia.msg(&quot;text&quot;,[&quot;click me&quot;],{});return false;">MXP cmd</a>';
  const mxpUrl = '<a id="mxplink" href="http://example.com" target="_blank">MXP url</a>';
  const autoUrl = '<a href="http://example.com/x?y=1" target="_blank">http://example.com/x?y=1</a>';
  for (const source of [mxpCommand, mxpUrl, autoUrl]) {
    const tokens = Markup.tokenize(source);
    assert.equal(tokens.some((t) => t.kind === "open" || t.kind === "close"), false);
    assert.equal(tokens.some((t) => t.tag === "a"), false);
    const text = tokens.filter((t) => t.kind === "text").map((t) => t.value).join("");
    assert.equal(text.includes("Evennia.msg"), false);
    assert.equal(tokens.some((t) => t.value && t.value.includes("Evennia.msg")), false);
    assert.equal(text.includes("<a"), false);
    assert.equal(text.includes("</a>"), false);
  }
  // The label text survives, and the command is never reconstructed.
  const label = Markup.tokenize(mxpCommand)
    .filter((t) => t.kind === "text")
    .map((t) => t.value)
    .join("");
  assert.equal(label, "MXP cmd");
});

test("hostile markup degrades to visible literal text", () => {
  const sources = [
    "<script>alert(1)</script>",
    '<img src="x" onerror="alert(1)">',
    '<a href="javascript:alert(1)">click</a>',
    '<span class="color-009" style="color: #ff0000;evil: 1" onclick="x">t</span>',
    'quote "soup" &amp; &quot; &#39;',
    '<span class="color-009"', // unterminated span tag
    "<span",
    "<br",
    "</span>",
    "<SPAN class=\"color-009\">upper</SPAN>",
    '<span class="color-009" onmouseover="x()">hover</span>',
  ];
  for (const source of sources) {
    const tokens = Markup.tokenize(source);
    const degraded = tokens.filter((t) => t.kind === "text");
    assert.ok(
      degraded.length >= 1,
      "hostile input must degrade to text tokens for " + JSON.stringify(source)
    );
    for (const token of tokens) {
      assert.equal(token.kind, "text", "only text tokens for " + JSON.stringify(source));
    }
  }
});

test("a well-formed unclosed span keeps its opening token", () => {
  const tokens = Markup.tokenize('<span class="color-009">unbalanced');
  assert.deepEqual(
    tokens.map((t) => t.kind),
    ["open", "text"]
  );
});

test("hostile markup text is preserved verbatim and flagged as degraded", () => {
  const tokens = Markup.tokenize("<script>alert(1)</script>");
  assert.deepEqual(
    tokens.map((t) => t.value),
    ["<script>", "alert(1)", "</script>"]
  );
  assert.equal(tokens[0].degraded, true);
  assert.equal(tokens[1].degraded, undefined);
  assert.equal(tokens[2].degraded, true);
});

test("normal entity-decoded text is never flagged as degraded", () => {
  const tokens = Markup.tokenize("&lt;script&gt; &amp; text");
  assert.equal(tokens.length, 1);
  assert.equal(tokens[0].value, "<script> & text");
  assert.equal(tokens[0].degraded, undefined);
});

test("depth bound degrades the offending opening tag", () => {
  const source = '<span class="color-001">'.repeat(Markup.MAX_DEPTH + 1) + "x" + "</span>".repeat(Markup.MAX_DEPTH + 1);
  const tokens = Markup.tokenize(source);
  const opens = tokens.filter((t) => t.kind === "open");
  assert.equal(opens.length, Markup.MAX_DEPTH);
  const closes = tokens.filter((t) => t.kind === "close");
  assert.equal(closes.length, Markup.MAX_DEPTH);
  const degraded = tokens.filter((t) => t.kind === "text" && t.value.indexOf("<span") === 0);
  assert.equal(degraded.length, 1);
});

test("degraded deep spans stay balanced so later legitimate spans survive", () => {
  // MAX_DEPTH + 1 nested spans, fully closed, followed by a fresh span that
  // must render normally. The renderer's element stack must stay balanced:
  // the degraded open's matching close degrades too, and the legitimate
  // closes pop exactly the accepted spans.
  const source =
    '<span class="color-001">'.repeat(Markup.MAX_DEPTH + 1) +
    "deep" +
    "</span>".repeat(Markup.MAX_DEPTH + 1) +
    '<span class="color-002">after</span>';
  const tokens = Markup.tokenize(source);
  const opens = tokens.filter((t) => t.kind === "open");
  const closes = tokens.filter((t) => t.kind === "close");
  assert.equal(opens.length, Markup.MAX_DEPTH + 1);
  assert.equal(closes.length, opens.length);
  // The final span survived intact.
  const lastOpen = opens[opens.length - 1];
  assert.deepEqual(lastOpen.classes, ["color-002"]);
  // The deep content and the final text both render.
  const text = tokens.filter((t) => t.kind === "text").map((t) => t.value).join("");
  assert.equal(text.includes("deep"), true);
  assert.equal(text.includes("after"), true);
  // Exactly one degraded open tag and one degraded close tag (the bound pair).
  const degraded = tokens.filter((t) => t.kind === "text" && t.degraded === true);
  assert.equal(degraded.length, 2);
});

test("token bound emits the remainder as one literal text token and stops", () => {
  let source = "";
  for (let i = 0; i < Markup.MAX_TOKENS; i += 1) {
    source += "<br>";
  }
  source += "tail &amp; content";
  const tokens = Markup.tokenize(source);
  assert.equal(tokens.length, Markup.MAX_TOKENS + 1);
  const last = tokens[tokens.length - 1];
  assert.equal(last.kind, "text");
  assert.equal(last.value, "tail &amp; content");
});

test("empty and whitespace-only messages tokenize to text", () => {
  assert.deepEqual(Markup.tokenize(""), []);
  assert.deepEqual(Markup.tokenize("   ").map((t) => t.value), ["   "]);
  assert.deepEqual(Markup.tokenize(null), []);
});

test("mixed real parse_html output renders without degradation", () => {
  // Mirrors what `parse_html` actually emits for styled prose.
  const source =
    '<span class="color-009">南大道</span><br>' +
    '<span class="bgcolor-021">bluebg</span> ' +
    '<span class="underline color-012">under</span><br>' +
    '<span class="" style="color: #ff0000;background-color: #00ff00;">true</span>' +
    " escaped &lt;script&gt; &amp; more";
  const tokens = Markup.tokenize(source);
  assert.equal(tokens.some((t) => t.kind === "open" || t.kind === "close"), true);
  assert.equal(tokens.some((t) => t.kind === "break"), true);
  const text = tokens.filter((t) => t.kind === "text").map((t) => t.value).join("");
  assert.equal(text.includes("南大道"), true);
  assert.equal(text.includes("&lt;script&gt;"), false);
  assert.equal(text.includes("<script>"), true);
  assert.equal(text.includes("&amp;"), false);
  assert.equal(text.includes("&"), true);
});

test("exports the bounds and allowlist constants as one source of truth", () => {
  assert.equal(Markup.MAX_TOKENS, 4096);
  assert.equal(Markup.MAX_DEPTH, 32);
  assert.ok(Markup.CLASS_ALLOWLIST.test("color-014"));
  assert.ok(Markup.CLASS_ALLOWLIST.test("bgcolor-255"));
  assert.ok(Markup.CLASS_ALLOWLIST.test("underline"));
  assert.ok(Markup.CLASS_ALLOWLIST.test("blink"));
  assert.equal(Markup.CLASS_ALLOWLIST.test("color-9999"), false);
  assert.equal(Markup.CLASS_ALLOWLIST.test("onclick"), false);
  assert.equal(Markup.ENTITY_DECODE["&amp;"], "&");
});
