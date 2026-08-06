/*
 * Elosern narrative markup tokenizer.
 *
 * DOM-independent strict allowlist parser for Evennia's ANSI-to-HTML
 * narrative stream. The portal runs `parse_html` on narrative text before it
 * leaves the server, so the client receives a small closed grammar:
 * `<span class="color-NNN bgcolor-NNN underline blink">` with an optional
 * truecolor `style`, `<br>`, and `<a>` links. Everything else degrades to a
 * literal text token so no element is ever created from unrecognized markup.
 *
 * The module touches no `document` or `window` at load time, so the Node suite
 * exercises the complete grammar directly.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.NarrativeMarkup = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var MAX_TOKENS = 4096;
  var MAX_DEPTH = 32;

  // The exact class allowlist `parse_html` can emit. Three decimal digits for
  // color/bgcolor; anything else is dropped, never applied.
  var CLASS_ALLOWLIST = /^(?:color-\d{3}|bgcolor-\d{3}|underline|blink)$/;

  // The only entities the converted stream can carry (player content is
  // `html.escape`d by `parse_html`); everything else stays literal.
  var ENTITY_DECODE = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#x27;": "'",
    "&#39;": "'",
    "&nbsp;": "\u00a0",
  };
  var ENTITY_RE = /&(?:amp|lt|gt|quot|#x27|#39|nbsp);/g;

  function decodeEntities(text) {
    if (text.indexOf("&") === -1) {
      return text;
    }
    return text.replace(ENTITY_RE, function (entity) {
      return ENTITY_DECODE[entity];
    });
  }

  // Parse a `style="color: #rrggbb;background-color: #rrggbb;"` value strictly.
  // Returns `{ color?, backgroundColor? }` or null when any declaration or
  // value falls outside the two permitted color properties (the whole
  // attribute is then dropped, never partially applied).
  function parseStyle(value) {
    var style = {};
    var seen = {};
    var parts = value.split(";");
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i].trim();
      if (part === "") {
        continue;
      }
      var match = /^(color|background-color)\s*:\s*#([0-9a-fA-F]{6})$/.exec(part);
      if (!match || seen[match[1]]) {
        return null;
      }
      seen[match[1]] = true;
      if (match[1] === "color") {
        style.color = "#" + match[2].toLowerCase();
      } else {
        style.backgroundColor = "#" + match[2].toLowerCase();
      }
    }
    return style;
  }

  // Parse the attribute list of a `<span>` tag. Only `class` and `style` are
  // allowed; any other attribute name (including any `on*` handler) rejects
  // the whole tag. Returns `{ classes, style }` or null.
  function parseSpanAttrs(raw) {
    var classes = [];
    var style = null;
    var sawClass = false;
    var sawStyle = false;
    var pos = 0;
    var re = /\s*([A-Za-z][A-Za-z0-9-]*)\s*=\s*"([^"]*)"/g;
    var match;
    while ((match = re.exec(raw)) !== null) {
      if (match.index !== pos) {
        return null;
      }
      pos = re.lastIndex;
      var name = match[1];
      var value = match[2];
      if (name === "class") {
        if (sawClass) {
          return null;
        }
        sawClass = true;
        classes = value.split(/\s+/).filter(function (cls) {
          return cls.length > 0 && CLASS_ALLOWLIST.test(cls);
        });
      } else if (name === "style") {
        if (sawStyle) {
          return null;
        }
        sawStyle = true;
        style = parseStyle(value);
        if (style === null) {
          style = undefined;
        }
      } else {
        return null;
      }
    }
    if (pos !== raw.length) {
      return null;
    }
    return {
      classes: classes,
      style: style === undefined ? null : style,
    };
  }

  function tokenize(source) {
    var text = source == null ? "" : String(source);
    var tokens = [];
    // Syntax stack of open spans; each entry records whether the opening tag
    // was accepted (emitted an `open` token) or degraded (emitted as literal
    // text, e.g. past MAX_DEPTH). The matching close then takes the same
    // path, so the renderer's element stack stays perfectly balanced.
    var spanStack = [];
    var depth = 0;
    var index = 0;
    var length = text.length;
    var textStart = 0;

    // Find the `>` that terminates the tag starting at `start`, skipping any
    // `>` inside a double-quoted attribute value. Returns -1 when unterminated.
    function scanTagEnd(start) {
      var inQuote = false;
      var pos = start + 1;
      while (pos < length) {
        var ch = text.charAt(pos);
        if (inQuote) {
          if (ch === '"') {
            inQuote = false;
          }
        } else if (ch === '"') {
          inQuote = true;
        } else if (ch === ">") {
          return pos;
        }
        pos += 1;
      }
      return -1;
    }

    // Consume a tag beginning at `index` (which points at `<`). Returns a
    // descriptor: `{ end, token }` for an accepted production, `{ end,
    // anchor: true }` for a silently consumed anchor, or `{ end, text }` for
    // degraded markup emitted as a literal text token.
    function parseTag(start) {
      var rest = text.slice(start);
      // `</span>` close, exact.
      if (rest.indexOf("</span>") === 0) {
        if (spanStack.length === 0) {
          return { end: start + 7, text: "</span>" };
        }
        var closed = spanStack.pop();
        if (!closed.accepted) {
          // Matches a degraded opening tag (nesting bound): the close
          // degrades to literal text too, keeping the accepted spans'
          // stack balanced.
          return { end: start + 7, text: "</span>" };
        }
        depth -= 1;
        return { end: start + 7, token: { kind: "close", tag: "span" } };
      }
      // The three accepted `<br>` spellings, exact.
      var br = /^<br(?:>|\/>|\s\/>)/.exec(rest);
      if (br) {
        return { end: start + br[0].length, token: { kind: "break" } };
      }
      // `</a>` close, exact.
      if (rest.indexOf("</a>") === 0) {
        return { end: start + 4, anchor: true };
      }
      // `<a ...>` open; every attribute is discarded.
      if (rest.indexOf("<a") === 0 && (rest.length === 2 || /[\s>]/.test(rest.charAt(2)))) {
        var anchorEnd = scanTagEnd(start);
        if (anchorEnd < 0) {
          return { end: length, text: rest };
        }
        return { end: anchorEnd + 1, anchor: true };
      }
      // `<span ...>` open.
      if (rest.indexOf("<span") === 0 && (rest.length === 5 || /[\s>]/.test(rest.charAt(5)))) {
        var spanEnd = scanTagEnd(start);
        if (spanEnd < 0) {
          return { end: length, text: rest };
        }
        var tagText = text.slice(start, spanEnd + 1);
        var parsed = parseSpanAttrs(text.slice(start + 5, spanEnd));
        if (parsed === null) {
          return { end: spanEnd + 1, text: tagText };
        }
        if (depth >= MAX_DEPTH) {
          // Nesting bound: the offending opening tag degrades to literal
          // text; a degraded entry is pushed so its matching close degrades
          // too and never closes a legitimate span early.
          spanStack.push({ accepted: false });
          return { end: spanEnd + 1, text: tagText };
        }
        depth += 1;
        spanStack.push({ accepted: true });
        return {
          end: spanEnd + 1,
          token: {
            kind: "open",
            tag: "span",
            classes: parsed.classes,
            style: parsed.style,
          },
        };
      }
      // Everything else degrades to literal text: an unknown tag, a malformed
      // or unterminated tag. Verbatim source characters, never an element.
      var unknownEnd = scanTagEnd(start);
      if (unknownEnd < 0) {
        return { end: length, text: rest };
      }
      return { end: unknownEnd + 1, text: text.slice(start, unknownEnd + 1) };
    }

    while (index < length) {
      if (tokens.length >= MAX_TOKENS) {
        // Bound: emit the entire remainder as one literal text token and stop.
        var remainderStart = textStart < index ? textStart : index;
        tokens.push({ kind: "text", value: text.slice(remainderStart), degraded: true });
        textStart = length;
        break;
      }
      if (text.charAt(index) !== "<") {
        index += 1;
        continue;
      }
      var tag = parseTag(index);
      if (index > textStart) {
        tokens.push({
          kind: "text",
          value: decodeEntities(text.slice(textStart, index)),
        });
      }
      if (tag.token) {
        tokens.push(tag.token);
      } else if (tag.text !== undefined) {
        // Literal-text fallback: the offending markup as verbatim characters.
        tokens.push({ kind: "text", value: tag.text, degraded: true });
      }
      textStart = tag.end;
      index = tag.end;
    }
    if (length > textStart) {
      tokens.push({
        kind: "text",
        value: decodeEntities(text.slice(textStart, length)),
      });
    }
    return tokens;
  }

  return {
    MAX_TOKENS: MAX_TOKENS,
    MAX_DEPTH: MAX_DEPTH,
    CLASS_ALLOWLIST: CLASS_ALLOWLIST,
    ENTITY_DECODE: Object.assign({}, ENTITY_DECODE),
    decodeEntities: decodeEntities,
    tokenize: tokenize,
  };
});
