// Pure response segmentation and token-stream pagination for the AVG message
// window (docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md
// §6.1–§6.2; OpenSpec change webclient-message-pages, design D2–D4).
//
// No Vue or DOM imports; depends only on ./narrative_markup.js and ./box_drawing.js.
import NarrativeMarkup from "./narrative_markup.js";
import { isBoxDrawing } from "./box_drawing.js";

const CJK_SENTENCE_END = new Set(["。", "！", "？", "…"]);
const ASCII_SENTENCE_END = new Set([".", "!", "?"]);
const CJK_CLAUSE_END = new Set(["，", "、", "；", "："]);
const ASCII_CLAUSE_END = new Set([",", ";", ":"]);
const CLOSING_QUOTES = new Set(["」", "』", "）", '"', "'"]);
const WHITESPACE_RE = /^\s$/;

function lineText(line) {
  return !line || line.text == null ? "" : String(line.text);
}

function lineTokens(line) {
  if (line && Array.isArray(line.tokens)) {
    return line.tokens;
  }
  return NarrativeMarkup.tokenize(lineText(line));
}

function toBlock(line) {
  const text = lineText(line);
  const kind = (line && line.kind) || "out";
  return {
    kind,
    seq: line && typeof line.seq === "number" ? line.seq : null,
    text,
    tokens: lineTokens(line),
    mapArt: isBoxDrawing(text),
  };
}

// D2: Convert a segmented response (or raw line list) into pageable blocks.
// Player input (`in`) lines are headers, never blocks.
export function responseBlocks(response) {
  if (!response) {
    return [];
  }
  if (Array.isArray(response)) {
    const blocks = [];
    for (let i = 0; i < response.length; i += 1) {
      const item = response[i];
      if (!item || item.kind === "in") {
        continue;
      }
      if (Array.isArray(item.tokens) && typeof item.mapArt === "boolean") {
        blocks.push(item);
      } else {
        blocks.push(toBlock(item));
      }
    }
    return blocks;
  }
  if (Array.isArray(response.lines)) {
    const blocks = [];
    for (let i = 0; i < response.lines.length; i += 1) {
      const line = response.lines[i];
      if (!line || line.kind === "in") {
        continue;
      }
      blocks.push(toBlock(line));
    }
    return blocks;
  }
  if (Array.isArray(response.blocks)) {
    return response.blocks.filter((b) => b && b.kind !== "in");
  }
  return [];
}

// D2: Walk retained narrative lines once and segment into responses at each
// `in` line and at each response mark.
export function segmentResponses(lines, marks = []) {
  const safeLines = Array.isArray(lines) ? lines : [];
  const markSet = new Set();
  if (Array.isArray(marks)) {
    for (let i = 0; i < marks.length; i += 1) {
      if (typeof marks[i] === "number") {
        markSet.add(marks[i]);
      }
    }
  }

  const responses = [];
  let current = null;

  for (let i = 0; i < safeLines.length; i += 1) {
    const line = safeLines[i];
    if (!line) {
      continue;
    }
    const seq = typeof line.seq === "number" ? line.seq : null;
    const isIn = line.kind === "in";
    const isMarked = seq !== null && markSet.has(seq);

    if (isIn) {
      current = {
        startSeq: seq,
        header: line,
        lines: [],
        blocks: [],
      };
      responses.push(current);
    } else if (isMarked) {
      const block = toBlock(line);
      current = {
        startSeq: seq,
        header: null,
        lines: [line],
        blocks: [block],
      };
      responses.push(current);
    } else {
      if (!current) {
        current = {
          startSeq: null,
          header: null,
          lines: [],
          blocks: [],
        };
        responses.push(current);
      }
      current.lines.push(line);
      current.blocks.push(toBlock(line));
    }
  }

  return responses;
}

// Flatten a token stream into code-point units for measurement/cutting.
// Each unit is either `{ kind: "char", ch }` or `{ kind: "break", ch: "\n" }`.
function extractUnits(tokens) {
  const units = [];
  if (!Array.isArray(tokens)) {
    return units;
  }
  for (let i = 0; i < tokens.length; i += 1) {
    const tok = tokens[i];
    if (!tok || typeof tok.kind !== "string") {
      continue;
    }
    if (tok.kind === "text") {
      const cps = Array.from(tok.value == null ? "" : String(tok.value));
      for (let j = 0; j < cps.length; j += 1) {
        units.push({ kind: "char", ch: cps[j] });
      }
    } else if (tok.kind === "break") {
      units.push({ kind: "break", ch: "\n" });
    }
  }
  return units;
}

function isHardBreakUnit(unit) {
  return Boolean(unit) && (unit.kind === "break" || unit.ch === "\n");
}

function isWhitespaceUnit(unit) {
  return Boolean(unit) && (unit.kind === "break" || WHITESPACE_RE.test(unit.ch));
}

function isSentenceEndChar(ch) {
  return CJK_SENTENCE_END.has(ch) || ASCII_SENTENCE_END.has(ch);
}

// Precompute strong and clause cut positions in [1..units.length].
// A cut position `p` means the prefix takes the first `p` units (indices 0..p-1).
function computeBoundaries(units) {
  const n = units.length;
  const strong = new Set();
  const clause = new Set();

  // 1. Hard breaks: cutting at a hard break means ending the prefix right
  // before the break (at index i, where i > 0) and stripping the leading break
  // run from the remainder so the break is consumed at the split point.
  for (let i = 0; i < n; i += 1) {
    if (isHardBreakUnit(units[i]) && i > 0 && !isHardBreakUnit(units[i - 1])) {
      strong.add(i);
    }
  }

  // 2. Sentence ends: a maximal run of [。！？….!?]+ followed by any run of
  // closing quotes/brackets [」』）"']*.
  let i = 0;
  while (i < n) {
    const u = units[i];
    if (u.kind === "char" && isSentenceEndChar(u.ch)) {
      let hasCjkEnd = CJK_SENTENCE_END.has(u.ch);
      let j = i + 1;
      while (j < n && units[j].kind === "char" && isSentenceEndChar(units[j].ch)) {
        if (CJK_SENTENCE_END.has(units[j].ch)) {
          hasCjkEnd = true;
        }
        j += 1;
      }
      let k = j;
      while (k < n && units[k].kind === "char" && CLOSING_QUOTES.has(units[k].ch)) {
        k += 1;
      }
      // Valid sentence end if it contains any CJK end mark OR is followed by
      // whitespace/break after the end-mark + closing-quote run.
      const followedBySpace = k < n && isWhitespaceUnit(units[k]);
      if (hasCjkEnd || followedBySpace) {
        strong.add(k);
      }
      i = k;
    } else {
      i += 1;
    }
  }

  // 3. Clause marks: CJK ，、；： cut immediately (including any directly
  // following closing quotes); ASCII ,;: cut when followed by whitespace/break.
  for (let idx = 0; idx < n; idx += 1) {
    const u = units[idx];
    if (u.kind !== "char") {
      continue;
    }
    if (CJK_CLAUSE_END.has(u.ch)) {
      let k = idx + 1;
      while (k < n && units[k].kind === "char" && CLOSING_QUOTES.has(units[k].ch)) {
        k += 1;
      }
      clause.add(k);
    } else if (ASCII_CLAUSE_END.has(u.ch)) {
      let k = idx + 1;
      while (k < n && units[k].kind === "char" && CLOSING_QUOTES.has(units[k].ch)) {
        k += 1;
      }
      if (k < n && isWhitespaceUnit(units[k])) {
        clause.add(k);
      }
    }
  }

  return { strong, clause };
}

function cloneOpenToken(token) {
  const copy = {
    kind: "open",
    tag: token.tag || "span",
    classes: Array.isArray(token.classes) ? token.classes.slice() : [],
  };
  if (token.style) {
    copy.style = { ...token.style };
  }
  return copy;
}

function makeTextToken(value, degraded) {
  const tok = { kind: "text", value };
  if (degraded) {
    tok.degraded = true;
  }
  return tok;
}

// Split `tokens` after `cutCount` code-point/break units (D4).
// Also strips leading `break` tokens and leading `\n` characters from the
// remainder, returning `{ prefixTokens, remainderTokens, droppedBreaks }`.
function splitTokenStream(tokens, cutCount) {
  const prefixTokens = [];
  const remainderTokens = [];
  const openStack = [];
  let remaining = cutCount;
  let inRemainder = remaining <= 0;
  let strippingLeadingBreaks = inRemainder;
  let droppedBreaks = 0;

  function openRemainderSpans() {
    for (let i = 0; i < openStack.length; i += 1) {
      remainderTokens.push(cloneOpenToken(openStack[i]));
    }
  }

  function closePrefixSpans() {
    for (let i = openStack.length - 1; i >= 0; i -= 1) {
      prefixTokens.push({ kind: "close", tag: openStack[i].tag || "span" });
    }
  }

  if (inRemainder) {
    // Cut at 0: prefix is empty, remainder gets everything.
  }

  for (let i = 0; i < tokens.length; i += 1) {
    const tok = tokens[i];
    if (!tok || typeof tok.kind !== "string") {
      continue;
    }

    if (!inRemainder) {
      if (tok.kind === "open") {
        const openCopy = cloneOpenToken(tok);
        prefixTokens.push(openCopy);
        openStack.push(openCopy);
      } else if (tok.kind === "close") {
        if (openStack.length > 0) {
          openStack.pop();
        }
        prefixTokens.push({ kind: "close", tag: tok.tag || "span" });
      } else if (tok.kind === "break") {
        if (remaining > 1) {
          prefixTokens.push({ kind: "break" });
          remaining -= 1;
        } else {
          // remaining === 1: this break ends the prefix.
          prefixTokens.push({ kind: "break" });
          remaining = 0;
          closePrefixSpans();
          openRemainderSpans();
          inRemainder = true;
          strippingLeadingBreaks = true;
        }
      } else if (tok.kind === "text") {
        const cps = Array.from(tok.value == null ? "" : String(tok.value));
        if (cps.length === 0) {
          continue;
        }
        if (cps.length < remaining) {
          prefixTokens.push(makeTextToken(cps.join(""), tok.degraded));
          remaining -= cps.length;
        } else if (cps.length === remaining) {
          prefixTokens.push(makeTextToken(cps.join(""), tok.degraded));
          remaining = 0;
          closePrefixSpans();
          openRemainderSpans();
          inRemainder = true;
          strippingLeadingBreaks = true;
        } else {
          // Split inside this text token.
          const head = cps.slice(0, remaining).join("");
          if (head.length > 0) {
            prefixTokens.push(makeTextToken(head, tok.degraded));
          }
          let tailCps = cps.slice(remaining);
          remaining = 0;
          closePrefixSpans();
          openRemainderSpans();
          inRemainder = true;
          strippingLeadingBreaks = true;

          while (strippingLeadingBreaks && tailCps.length > 0 && tailCps[0] === "\n") {
            tailCps.shift();
            droppedBreaks += 1;
          }
          if (tailCps.length > 0) {
            strippingLeadingBreaks = false;
            remainderTokens.push(makeTextToken(tailCps.join(""), tok.degraded));
          }
        }
      }
    } else {
      // Already in remainder.
      if (tok.kind === "open") {
        const openCopy = cloneOpenToken(tok);
        remainderTokens.push(openCopy);
        openStack.push(openCopy);
      } else if (tok.kind === "close") {
        if (openStack.length > 0) {
          openStack.pop();
        }
        remainderTokens.push({ kind: "close", tag: tok.tag || "span" });
      } else if (tok.kind === "break") {
        if (strippingLeadingBreaks) {
          droppedBreaks += 1;
        } else {
          remainderTokens.push({ kind: "break" });
        }
      } else if (tok.kind === "text") {
        const cps = Array.from(tok.value == null ? "" : String(tok.value));
        if (strippingLeadingBreaks) {
          while (cps.length > 0 && cps[0] === "\n") {
            cps.shift();
            droppedBreaks += 1;
          }
        }
        if (cps.length > 0) {
          strippingLeadingBreaks = false;
          remainderTokens.push(makeTextToken(cps.join(""), tok.degraded));
        }
      }
    }
  }

  return {
    prefixTokens: pruneEmptySpans(prefixTokens),
    remainderTokens: pruneEmptySpans(remainderTokens),
    droppedBreaks,
  };
}

// Drop `<span ...></span>` pairs that hold no text or break tokens so cutting
// at a span boundary never emits an empty span wrapper.
function pruneEmptySpans(tokens) {
  const out = [];
  for (let i = 0; i < tokens.length; i += 1) {
    const tok = tokens[i];
    if (tok.kind === "close" && out.length > 0 && out[out.length - 1].kind === "open") {
      out.pop();
    } else {
      out.push(tok);
    }
  }
  return out;
}

function chooseCut(maxFit, boundaries) {
  for (let p = maxFit; p >= 1; p -= 1) {
    if (boundaries.strong.has(p)) {
      return p;
    }
  }
  for (let p = maxFit; p >= 1; p -= 1) {
    if (boundaries.clause.has(p)) {
      return p;
    }
  }
  return maxFit;
}

export function responseLength(blocks) {
  if (!Array.isArray(blocks)) {
    return 0;
  }
  let total = 0;
  for (let i = 0; i < blocks.length; i += 1) {
    const block = blocks[i];
    if (!block || block.kind === "in") {
      continue;
    }
    const tokens = Array.isArray(block.tokens) ? block.tokens : lineTokens(block);
    total += extractUnits(tokens).length;
  }
  return total;
}

// D3: Cut pageable blocks into pages using an injected fit predicate
// `fits(candidateFragments) -> boolean`.
export function paginate(blocks, fits) {
  const safeBlocks = Array.isArray(blocks) ? blocks.filter((b) => b && b.kind !== "in") : [];
  if (safeBlocks.length === 0) {
    return [];
  }
  const fitFn = typeof fits === "function" ? fits : () => true;

  const pages = [];
  let currentPage = [];

  function flushPage(oversize = false) {
    if (currentPage.length > 0) {
      pages.push({ blocks: currentPage, oversize });
      currentPage = [];
    }
  }

  let responseOffset = 0;

  for (let bIndex = 0; bIndex < safeBlocks.length; bIndex += 1) {
    const raw = safeBlocks[bIndex];
    const kind = raw.kind || "out";
    const seq = typeof raw.seq === "number" ? raw.seq : null;
    const text = lineText(raw);
    const initialTokens = Array.isArray(raw.tokens) ? raw.tokens : NarrativeMarkup.tokenize(text);
    const mapArt = typeof raw.mapArt === "boolean" ? raw.mapArt : isBoxDrawing(text);

    // Rule 1: If the block is `sys` or `err` and the current page is non-empty,
    // close the page first.
    if ((kind === "sys" || kind === "err") && currentPage.length > 0) {
      flushPage(false);
    }

    let tokens = initialTokens;
    let units = extractUnits(tokens);
    let first = true;
    let startOffset = responseOffset;
    const blockEndOffset = responseOffset + units.length;
    responseOffset = blockEndOffset;

    // Empty block (e.g. empty string line): emit one empty fragment.
    if (units.length === 0) {
      const emptyFrag = {
        kind,
        seq,
        mapArt,
        first: true,
        tokens: [],
        start: startOffset,
        end: startOffset,
      };
      if (fitFn(currentPage.concat([emptyFrag]))) {
        currentPage.push(emptyFrag);
      } else {
        if (currentPage.length > 0) {
          flushPage(false);
        }
        if (fitFn([emptyFrag])) {
          currentPage.push(emptyFrag);
        } else {
          pages.push({ blocks: [emptyFrag], oversize: true });
        }
      }
      continue;
    }

    while (units.length > 0) {
      const wholeFrag = {
        kind,
        seq,
        mapArt,
        first,
        tokens,
        start: startOffset,
        end: startOffset + units.length,
      };

      // Rule 2: If `fits(page + block)`, append the whole remaining block and continue.
      if (fitFn(currentPage.concat([wholeFrag]))) {
        currentPage.push(wholeFrag);
        break;
      }

      // Rule 3: Box-drawing blocks are atomic.
      if (mapArt) {
        if (currentPage.length > 0) {
          flushPage(false);
          continue;
        }
        pages.push({ blocks: [wholeFrag], oversize: true });
        break;
      }

      // Rule 4: Binary search over code-point prefix lengths [1..units.length - 1]
      // for the largest L whose prefix fragment fits on `currentPage`.
      let lo = 1;
      let hi = units.length - 1;
      let bestL = 0;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const { prefixTokens } = splitTokenStream(tokens, mid);
        const candidateFrag = {
          kind,
          seq,
          mapArt: false,
          first,
          tokens: prefixTokens,
          start: startOffset,
          end: startOffset + mid,
        };
        if (fitFn(currentPage.concat([candidateFrag]))) {
          bestL = mid;
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }

      // Rule 5: If no prefix fits (bestL === 0):
      // - On a non-empty page, close the page and retry the whole block.
      // - On an empty page, emit the whole remaining block as an oversize page.
      if (bestL === 0) {
        if (currentPage.length > 0) {
          flushPage(false);
          continue;
        }
        pages.push({ blocks: [wholeFrag], oversize: true });
        break;
      }

      const boundaries = computeBoundaries(units);
      const cut = chooseCut(bestL, boundaries);
      const { prefixTokens, remainderTokens, droppedBreaks } = splitTokenStream(tokens, cut);
      const prefixFrag = {
        kind,
        seq,
        mapArt: false,
        first,
        tokens: prefixTokens,
        start: startOffset,
        end: startOffset + cut,
      };
      currentPage.push(prefixFrag);
      flushPage(false);

      startOffset = startOffset + cut + droppedBreaks;
      tokens = remainderTokens;
      units = extractUnits(tokens);
      first = false;
    }
  }

  flushPage(false);
  return pages;
}

// D3: Return the 0-based page index containing the response character offset.
export function pageIndexForOffset(pages, offset) {
  if (!Array.isArray(pages) || pages.length === 0) {
    return 0;
  }
  const target = typeof offset === "number" && offset > 0 ? offset : 0;
  for (let i = 0; i < pages.length; i += 1) {
    const page = pages[i];
    const blocks = page && Array.isArray(page.blocks) ? page.blocks : [];
    if (blocks.length === 0) {
      continue;
    }
    const pageEnd = blocks[blocks.length - 1].end;
    if (target < pageEnd) {
      return i;
    }
  }
  return pages.length - 1;
}
