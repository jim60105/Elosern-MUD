// Unit tests for pure response segmentation and token-stream pagination
// (OpenSpec change webclient-message-pages, tasks 2.2–2.3).
import { describe, expect, it } from "vitest";
import NarrativeMarkup from "../lib/narrative_markup.js";
import {
  pageIndexForOffset,
  paginate,
  responseBlocks,
  responseLength,
  segmentResponses,
  splitTokensAt,
} from "../lib/message_pages.js";

function makeLine(kind, text, seq) {
  const normalized = String(text == null ? "" : text);
  const line = {
    kind,
    text: normalized,
    tokens: kind === "in" ? null : NarrativeMarkup.tokenize(normalized),
  };
  if (typeof seq === "number") {
    line.seq = seq;
  }
  return line;
}

// Fake fit predicate: counts code points per wrapped line (`cols` chars/line,
// `maxLines` lines/page), with each `break` token or `\n` ending a line and
// each fragment starting on a new line.
function makeCodePointFits(cols = 10, maxLines = 3) {
  return function fits(fragments) {
    if (cols <= 0 || maxLines <= 0) {
      return false;
    }
    let totalLines = 0;
    for (const frag of fragments) {
      let lineChars = 0;
      let fragLines = 1;
      for (const tok of frag.tokens || []) {
        if (tok.kind === "break") {
          fragLines += 1;
          lineChars = 0;
        } else if (tok.kind === "text") {
          const cps = Array.from(tok.value || "");
          for (const ch of cps) {
            if (ch === "\n") {
              fragLines += 1;
              lineChars = 0;
            } else {
              if (lineChars >= cols) {
                fragLines += 1;
                lineChars = 0;
              }
              lineChars += 1;
            }
          }
        }
      }
      totalLines += fragLines;
      if (totalLines > maxLines) {
        return false;
      }
    }
    return totalLines <= maxLines;
  };
}

function fragmentPlainText(fragment) {
  let out = "";
  for (const tok of fragment.tokens || []) {
    if (tok.kind === "text") {
      out += tok.value;
    } else if (tok.kind === "break") {
      out += "\n";
    }
  }
  return out;
}

function blockPlainText(block) {
  let out = "";
  const tokens = Array.isArray(block.tokens)
    ? block.tokens
    : NarrativeMarkup.tokenize(block.text || "");
  for (const tok of tokens) {
    if (tok.kind === "text") {
      out += tok.value;
    } else if (tok.kind === "break") {
      out += "\n";
    }
  }
  return out;
}

describe("segmentResponses and responseBlocks", () => {
  it("segments at in lines and response marks, excluding in lines from blocks", () => {
    const lines = [
      makeLine("in", "look", 1),
      makeLine("out", "石板廣場。", 2),
      makeLine("out", "遠處有微光。", 3),
    ];
    const responses = segmentResponses(lines, []);
    expect(responses).toHaveLength(1);
    expect(responses[0].header).toEqual(lines[0]);
    expect(responses[0].startSeq).toBe(1);
    const blocks = responseBlocks(responses[0]);
    expect(blocks.map((b) => b.text)).toEqual(["石板廣場。", "遠處有微光。"]);
    expect(blocks.every((b) => b.kind !== "in")).toBe(true);
  });

  it("starts a headerless response at a silent action's response mark", () => {
    const lines = [
      makeLine("in", "talk host", 1),
      makeLine("out", "「歡迎。」", 2),
      makeLine("out", "你結束了對話。", 3),
    ];
    // Mark at seq 3 (silent explore.dialogue_leave)
    const responses = segmentResponses(lines, [1, 3]);
    expect(responses).toHaveLength(2);
    expect(responses[0].header.text).toBe("talk host");
    expect(responseBlocks(responses[0]).map((b) => b.text)).toEqual(["「歡迎。」"]);
    expect(responses[1].header).toBe(null);
    expect(responses[1].startSeq).toBe(3);
    expect(responseBlocks(responses[1]).map((b) => b.text)).toEqual(["你結束了對話。"]);
  });

  it("counts a mark-plus-echo at the same seq as a single response", () => {
    const lines = [
      makeLine("out", "起始房間。", 1),
      makeLine("in", "north", 2),
      makeLine("out", "北側長廊。", 3),
    ];
    // Dispatch recorded mark 2, and echo appended `in` line with seq 2.
    const responses = segmentResponses(lines, [2]);
    expect(responses).toHaveLength(2);
    expect(responses[0].header).toBe(null);
    expect(responseBlocks(responses[0]).map((b) => b.text)).toEqual(["起始房間。"]);
    expect(responses[1].header.text).toBe("north");
    expect(responses[1].startSeq).toBe(2);
    expect(responseBlocks(responses[1]).map((b) => b.text)).toEqual(["北側長廊。"]);
  });

  it("ignores a pending mark that has no retained line yet", () => {
    const lines = [
      makeLine("in", "look", 1),
      makeLine("out", "石板廣場。", 2),
    ];
    // Pending mark 3 has no line yet.
    const responses = segmentResponses(lines, [1, 3]);
    expect(responses).toHaveLength(1);
    expect(responseBlocks(responses[0]).map((b) => b.text)).toEqual(["石板廣場。"]);
  });

  it("forms a leading headerless response for lines before any action", () => {
    const lines = [
      makeLine("sys", "已連線至伺服器。", 1),
      makeLine("out", "清晨的霧氣籠罩廣場。", 2),
    ];
    const responses = segmentResponses(lines, []);
    expect(responses).toHaveLength(1);
    expect(responses[0].header).toBe(null);
    expect(responses[0].startSeq).toBe(null);
    expect(responseBlocks(responses[0]).map((b) => b.text)).toEqual([
      "已連線至伺服器。",
      "清晨的霧氣籠罩廣場。",
    ]);
  });

  it("appends late asynchronous lines to the current response", () => {
    const lines = [
      makeLine("in", "talk bard 你好", 1),
      makeLine("out", "詩人微微笑了笑。", 2),
      makeLine("out", "「願風指引你的道路。」", 3),
    ];
    const responses = segmentResponses(lines, [1]);
    expect(responses).toHaveLength(1);
    expect(responseBlocks(responses[0]).map((b) => b.text)).toEqual([
      "詩人微微笑了笑。",
      "「願風指引你的道路。」",
    ]);
  });

  it("segments seq-less fixture lines by in lines alone and never leaks in lines into blocks", () => {
    const fixtures = [
      { kind: "out", text: "序幕。" },
      { kind: "in", text: "look" },
      { kind: "out", text: "第一段。" },
      { kind: "sys", text: "系統提示。" },
    ];
    const responses = segmentResponses(fixtures, [1, 2]);
    expect(responses).toHaveLength(2);
    expect(responses[0].header).toBe(null);
    expect(responseBlocks(responses[0]).map((b) => b.text)).toEqual(["序幕。"]);
    expect(responses[1].header.text).toBe("look");
    expect(responseBlocks(responses[1]).map((b) => b.text)).toEqual(["第一段。", "系統提示。"]);
    // Passing a raw fixture array to responseBlocks also filters out `in` lines.
    expect(responseBlocks(fixtures).every((b) => b.kind !== "in")).toBe(true);
  });
});

describe("paginate", () => {
  it("packs whole blocks onto a single page when they fit together", () => {
    const fits = makeCodePointFits(10, 3);
    const blocks = responseBlocks([
      makeLine("out", "短句一。", 1),
      makeLine("out", "短句二。", 2),
      makeLine("out", "短句三。", 3),
    ]);
    const pages = paginate(blocks, fits);
    expect(pages).toHaveLength(1);
    expect(pages[0].oversize).toBe(false);
    expect(pages[0].blocks.map(fragmentPlainText)).toEqual(["短句一。", "短句二。", "短句三。"]);
    expect(pages[0].blocks.every((b) => b.first === true)).toBe(true);
  });

  it("always begins a new page for sys and err blocks", () => {
    const fits = makeCodePointFits(10, 3);
    const blocks = responseBlocks([
      makeLine("out", "普通敘述。", 1),
      makeLine("err", "操作失敗。", 2),
      makeLine("sys", "系統通知。", 3),
    ]);
    const pages = paginate(blocks, fits);
    expect(pages).toHaveLength(3);
    expect(pages[0].blocks.map((b) => b.kind)).toEqual(["out"]);
    expect(pages[1].blocks.map((b) => b.kind)).toEqual(["err"]);
    expect(pages[2].blocks.map((b) => b.kind)).toEqual(["sys"]);
  });

  it("cuts at hard breaks (<br> and \\n) and drops the consumed break at the split point", () => {
    const fits = makeCodePointFits(10, 2);
    const blocks = responseBlocks([
      makeLine("out", "第一行文字<br>第二行文字<br>第三行文字", 1),
    ]);
    const pages = paginate(blocks, fits);
    expect(pages).toHaveLength(2);
    expect(fragmentPlainText(pages[0].blocks[0])).toBe("第一行文字\n第二行文字");
    expect(pages[0].blocks[0].first).toBe(true);
    expect(fragmentPlainText(pages[1].blocks[0])).toBe("第三行文字");
    expect(pages[1].blocks[0].first).toBe(false);
    // Continuation must not start with a break token.
    expect(pages[1].blocks[0].tokens[0].kind).not.toBe("break");

    // Also verify `\n` inside a text token.
    const nlBlocks = responseBlocks([makeLine("out", "甲乙丙丁戊\n己庚辛壬癸\n子丑寅卯辰", 2)]);
    const nlPages = paginate(nlBlocks, fits);
    expect(nlPages).toHaveLength(2);
    expect(fragmentPlainText(nlPages[0].blocks[0])).toBe("甲乙丙丁戊\n己庚辛壬癸");
    expect(fragmentPlainText(nlPages[1].blocks[0])).toBe("子丑寅卯辰");
  });

  it("cuts at sentence ends including closing quotes and keeps …… and ！？ runs whole", () => {
    // 10 chars/line, 1 line/page -> maxFit = 10 code points per page.
    const fits = makeCodePointFits(10, 1);

    // Sentence end with closing quote `。」` within 10 chars:
    const quoted = responseBlocks([makeLine("out", "「你好！」她微笑著說道。", 1)]);
    const quotedPages = paginate(quoted, fits);
    expect(fragmentPlainText(quotedPages[0].blocks[0])).toBe("「你好！」");
    expect(fragmentPlainText(quotedPages[1].blocks[0])).toBe("她微笑著說道。");

    // `……` run kept whole when both fit:
    const ellipsis = responseBlocks([makeLine("out", "風停了……遠方傳來鐘聲。", 2)]);
    const ellipsisPages = paginate(ellipsis, fits);
    expect(fragmentPlainText(ellipsisPages[0].blocks[0])).toBe("風停了……");
    expect(fragmentPlainText(ellipsisPages[1].blocks[0])).toBe("遠方傳來鐘聲。");

    // `！？` run kept whole:
    const bangQ = responseBlocks([makeLine("out", "什麼！？你竟然在這裡。", 3)]);
    const bangQPages = paginate(bangQ, fits);
    expect(fragmentPlainText(bangQPages[0].blocks[0])).toBe("什麼！？");
    expect(fragmentPlainText(bangQPages[1].blocks[0])).toBe("你竟然在這裡。");

    // ASCII sentence end with closing quote followed by space vs decimal/version dots:
    const asciiFits = makeCodePointFits(14, 1);
    const ascii = responseBlocks([makeLine("out", 'v1.2.3 "Hi!" Next words', 4)]);
    const asciiPages = paginate(ascii, asciiFits);
    // Must cut after `"Hi!"` (12 chars), never at `1.` or `2.`.
    expect(fragmentPlainText(asciiPages[0].blocks[0])).toBe('v1.2.3 "Hi!"');
    expect(fragmentPlainText(asciiPages[1].blocks[0])).toBe(" Next words");
  });

  it("falls back to clause marks, then character boundaries without splitting surrogate pairs", () => {
    const fits = makeCodePointFits(10, 1);

    // No sentence end within 10 chars, but a clause mark `，` at index 5:
    const clauseBlocks = responseBlocks([makeLine("out", "微風吹過廣場，帶起一片落葉。", 1)]);
    const clausePages = paginate(clauseBlocks, fits);
    expect(fragmentPlainText(clausePages[0].blocks[0])).toBe("微風吹過廣場，");
    expect(fragmentPlainText(clausePages[1].blocks[0])).toBe("帶起一片落葉。");

    // No sentence end or clause mark within 10 code points -> character cut at 10 code points.
    // Include surrogate pairs (𠮷 = U+20BB7, 2 UTF-16 code units, 1 code point) around the cut.
    const astral = "一二三四五六七八九𠮷甲乙丙";
    const charBlocks = responseBlocks([makeLine("out", astral, 2)]);
    const charPages = paginate(charBlocks, fits);
    expect(Array.from(fragmentPlainText(charPages[0].blocks[0]))).toHaveLength(10);
    expect(fragmentPlainText(charPages[0].blocks[0])).toBe("一二三四五六七八九𠮷");
    expect(fragmentPlainText(charPages[1].blocks[0])).toBe("甲乙丙");
    // Verify no lone surrogates exist in either page.
    for (const p of charPages) {
      const text = fragmentPlainText(p.blocks[0]);
      expect(/[\uD800-\uDFFF]/.test(text.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, ""))).toBe(
        false,
      );
    }
  });

  it("closes and re-opens nested styled spans across a cut and preserves degraded text flags", () => {
    const fits = makeCodePointFits(6, 1);
    const source =
      '<span class="color-203" style="color: #ff5555;"><span class="underline">紅底線前段，紅底線後段</span></span>';
    const blocks = responseBlocks([makeLine("out", source, 1)]);
    const pages = paginate(blocks, fits);
    expect(pages).toHaveLength(2);

    const firstTokens = pages[0].blocks[0].tokens;
    const secondTokens = pages[1].blocks[0].tokens;
    expect(firstTokens).toEqual([
      { kind: "open", tag: "span", classes: ["color-203"], style: { color: "#ff5555" } },
      { kind: "open", tag: "span", classes: ["underline"] },
      { kind: "text", value: "紅底線前段，" },
      { kind: "close", tag: "span" },
      { kind: "close", tag: "span" },
    ]);
    expect(secondTokens).toEqual([
      { kind: "open", tag: "span", classes: ["color-203"], style: { color: "#ff5555" } },
      { kind: "open", tag: "span", classes: ["underline"] },
      { kind: "text", value: "紅底線後段" },
      { kind: "close", tag: "span" },
      { kind: "close", tag: "span" },
    ]);

    // Unaccepted markup degrades to `{ kind: "text", value, degraded: true }` and keeps `degraded: true` across cuts.
    const degradedBlocks = responseBlocks([makeLine("out", "<badtag_12345>", 2)]);
    const degradedPages = paginate(degradedBlocks, fits);
    expect(degradedPages.length).toBeGreaterThanOrEqual(2);
    for (const page of degradedPages) {
      for (const tok of page.blocks[0].tokens) {
        expect(tok.kind).toBe("text");
        expect(tok.degraded).toBe(true);
      }
    }
  });

  it("keeps box-drawing blocks atomic and marks an oversize map page when taller than the box", () => {
    const fits = makeCodePointFits(10, 3);
    const tallMap = ["┌────┐", "│ 一 │", "│ 二 │", "│ 三 │", "└────┘"].join("<br>");
    const blocks = responseBlocks([
      makeLine("out", "地圖標題。", 1),
      makeLine("out", tallMap, 2),
      makeLine("out", "地圖說明。", 3),
    ]);
    const pages = paginate(blocks, fits);
    expect(pages).toHaveLength(3);
    expect(pages[0].oversize).toBe(false);
    expect(fragmentPlainText(pages[0].blocks[0])).toBe("地圖標題。");

    // The 5-line map sits alone on page 1, unsplit, marked oversize.
    expect(pages[1].oversize).toBe(true);
    expect(pages[1].blocks).toHaveLength(1);
    expect(pages[1].blocks[0].mapArt).toBe(true);
    expect(fragmentPlainText(pages[1].blocks[0])).toBe(tallMap.replace(/<br>/g, "\n"));

    expect(pages[2].oversize).toBe(false);
    expect(fragmentPlainText(pages[2].blocks[0])).toBe("地圖說明。");
  });

  it("marks a page oversize when the box is too small for even a single character", () => {
    const zeroFits = () => false;
    const blocks = responseBlocks([makeLine("out", "無法容納的文字", 1)]);
    const pages = paginate(blocks, zeroFits);
    expect(pages).toHaveLength(1);
    expect(pages[0].oversize).toBe(true);
    expect(fragmentPlainText(pages[0].blocks[0])).toBe("無法容納的文字");
  });

  it("is lossless over a seeded randomized corpus and deterministic across repeated calls", () => {
    // Mulberry32 PRNG with fixed seed.
    let seed = 0x20260925;
    function rand() {
      seed |= 0;
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    }

    const alphabet = [
      "石",
      "板",
      "廣",
      "場",
      "霧",
      "燈",
      "。",
      "！",
      "？",
      "…",
      "，",
      "、",
      "；",
      "：",
      "「",
      "」",
      "𠮷",
      "a",
      ".",
      " ",
      "\n",
    ];
    const kinds = ["out", "sys", "err"];

    for (let trial = 0; trial < 40; trial += 1) {
      const rawLines = [];
      const lineCount = 1 + Math.floor(rand() * 5);
      for (let l = 0; l < lineCount; l += 1) {
        const kind = kinds[Math.floor(rand() * kinds.length)];
        const len = 1 + Math.floor(rand() * 45);
        let text = "";
        for (let c = 0; c < len; c += 1) {
          if (rand() < 0.08) {
            text += "<br>";
          } else if (rand() < 0.08) {
            text += '<span class="color-203">彩</span>';
          } else {
            text += alphabet[Math.floor(rand() * alphabet.length)];
          }
        }
        rawLines.push(makeLine(kind, text, l + 1));
      }

      const blocks = responseBlocks(rawLines);
      const cols = 4 + Math.floor(rand() * 10);
      const maxLines = 1 + Math.floor(rand() * 4);
      const fits = makeCodePointFits(cols, maxLines);

      const pages1 = paginate(blocks, fits);
      const pages2 = paginate(blocks, fits);
      // Determinism: identical inputs and fit results yield identical pages.
      expect(pages2).toEqual(pages1);

      // Losslessness: per block, concatenating its fragments reproduces the
      // block's plain text minus only the dropped breaks at fragment cuts.
      const byBlock = new Map();
      let idx = -1;
      for (const page of pages1) {
        for (const frag of page.blocks) {
          if (frag.first) {
            idx += 1;
            byBlock.set(idx, []);
          }
          byBlock.get(idx).push(frag);
        }
      }
      expect(byBlock.size).toBe(blocks.length);
      let blockBase = 0;
      for (let b = 0; b < blocks.length; b += 1) {
        const frags = byBlock.get(b);
        const cps = Array.from(blockPlainText(blocks[b]));
        let cursor = 0;
        for (let f = 0; f < frags.length; f += 1) {
          const relStart = frags[f].start - blockBase;
          const relEnd = frags[f].end - blockBase;
          expect(relStart).toBeGreaterThanOrEqual(cursor);
          // Any code points skipped at a cut before this fragment must be `\n`.
          for (let k = cursor; k < relStart; k += 1) {
            expect(cps[k]).toBe("\n");
          }
          expect(fragmentPlainText(frags[f])).toBe(cps.slice(relStart, relEnd).join(""));
          cursor = relEnd;
        }
        // Any trailing code points skipped at a final cut must also be `\n`.
        for (let k = cursor; k < cps.length; k += 1) {
          expect(cps[k]).toBe("\n");
        }
        blockBase += cps.length;
      }
    }
  });

  it("tracks character offsets and locates the page containing an anchor offset across re-paging", () => {
    const blocks = responseBlocks([
      makeLine("out", "第一句話結束。第二句話比較長一點。第三句話在最後面。", 1),
    ]);
    const totalLen = responseLength(blocks);
    expect(totalLen).toBe(26);

    const widePages = paginate(blocks, makeCodePointFits(15, 1));
    const narrowPages = paginate(blocks, makeCodePointFits(8, 1));
    expect(widePages.length).toBeLessThan(narrowPages.length);

    // Pick the offset of '第' in '第三句話' (code point index 17).
    const anchorOffset = 17;
    const wideIdx = pageIndexForOffset(widePages, anchorOffset);
    const narrowIdx = pageIndexForOffset(narrowPages, anchorOffset);

    const widePageText = widePages[wideIdx].blocks.map(fragmentPlainText).join("");
    const narrowPageText = narrowPages[narrowIdx].blocks.map(fragmentPlainText).join("");
    expect(widePageText).toContain("第三");
    expect(narrowPageText).toContain("第三");

    // Out-of-range offsets clamp to first / last page.
    expect(pageIndexForOffset(narrowPages, -5)).toBe(0);
    expect(pageIndexForOffset(narrowPages, 9999)).toBe(narrowPages.length - 1);
    expect(pageIndexForOffset([], 0)).toBe(0);
  });

  it("still produces a valid, lossless paging when given a non-monotonic fit function", () => {
    // Non-monotonic fake: claims prefix lengths 5 and 6 do not fit even though 7 fits,
    // and anything > 8 does not fit.
    const nonMonotonicFits = (fragments) => {
      const len = fragments.reduce(
        (sum, f) => sum + Array.from(fragmentPlainText(f)).length,
        0,
      );
      if (len === 5 || len === 6) {
        return false;
      }
      return len <= 8;
    };
    const text = "一二三四五六七八九十甲乙丙丁戊己";
    const blocks = responseBlocks([makeLine("out", text, 1)]);
    const pages = paginate(blocks, nonMonotonicFits);
    const joined = pages.flatMap((p) => p.blocks.map(fragmentPlainText)).join("");
    expect(joined).toBe(text);
  });
});

// webclient-typewriter-reading-prefs (task 2.1): the span-preserving cut
// exposed for the typewriter reveal.
describe("splitTokensAt", () => {
  it("closes nested spans on the head and re-opens shallow copies on the tail", () => {
    const tokens = NarrativeMarkup.tokenize(
      '<span class="color-203" style="color: #ff5555;"><span class="underline">紅底線前段</span></span>',
    );
    const { head, tail } = splitTokensAt(tokens, 2);
    expect(head).toEqual([
      { kind: "open", tag: "span", classes: ["color-203"], style: { color: "#ff5555" } },
      { kind: "open", tag: "span", classes: ["underline"] },
      { kind: "text", value: "紅底" },
      { kind: "close", tag: "span" },
      { kind: "close", tag: "span" },
    ]);
    expect(tail).toEqual([
      { kind: "open", tag: "span", classes: ["color-203"], style: { color: "#ff5555" } },
      { kind: "open", tag: "span", classes: ["underline"] },
      { kind: "text", value: "線前段" },
      { kind: "close", tag: "span" },
      { kind: "close", tag: "span" },
    ]);
    // Shallow copies: mutating the tail never touches the source tokens.
    tail[0].classes.push("x");
    expect(tokens[0].classes).toEqual(["color-203"]);
  });

  it("cuts at a break and keeps every break on the tail", () => {
    const tokens = [
      { kind: "text", value: "甲乙" },
      { kind: "break" },
      { kind: "break" },
      { kind: "text", value: "丙" },
    ];
    // The first break is unit 3: it ends the head; the second stays on the tail.
    expect(splitTokensAt(tokens, 3)).toEqual({
      head: [{ kind: "text", value: "甲乙" }, { kind: "break" }],
      tail: [{ kind: "break" }, { kind: "text", value: "丙" }],
    });
    // A cut before the breaks keeps both on the tail (a page cut would drop them).
    expect(splitTokensAt(tokens, 2).tail).toEqual([
      { kind: "break" },
      { kind: "break" },
      { kind: "text", value: "丙" },
    ]);
    // Leading newline characters inside a text token are kept too.
    expect(splitTokensAt([{ kind: "text", value: "甲\n\n乙" }], 1).tail).toEqual([
      { kind: "text", value: "\n\n乙" },
    ]);
  });

  it("never splits a surrogate pair and keeps the degraded flag on both halves", () => {
    const { head, tail } = splitTokensAt([{ kind: "text", value: "𠀀𠀁𠀂", degraded: true }], 2);
    expect(head).toEqual([{ kind: "text", value: "𠀀𠀁", degraded: true }]);
    expect(tail).toEqual([{ kind: "text", value: "𠀂", degraded: true }]);
  });

  it("puts everything on the tail at 0 and on the head past the end", () => {
    const tokens = [{ kind: "text", value: "甲乙" }];
    expect(splitTokensAt(tokens, 0)).toEqual({ head: [], tail: tokens });
    // A cut at 0 keeps a leading break on the tail.
    const leading = [{ kind: "break" }, { kind: "text", value: "甲" }];
    expect(splitTokensAt(leading, 0)).toEqual({ head: [], tail: leading });
    expect(splitTokensAt(tokens, 9)).toEqual({ head: tokens, tail: [] });
  });
});
