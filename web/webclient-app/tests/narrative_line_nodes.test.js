// webclient-frontend-utils: the shared line→vnode renderer extracted from
// FullLogOverlay.vue and MessageWindow.vue. Pins the contract the two
// components share: a divider plus a literal `.inp` line for player input
// (divider only for a non-first line), a pipeline-rendered line for
// everything else, and the `.map-art` monospace class for box-drawing
// lines — plus the design D2 equivalence: the util's escaped
// `BOX_DRAWING` form (`/[\u2500-\u257f]/`) classifies exactly the same
// text as the feed's literal-glyph spelling `/[─-╿]/`.

import { describe, expect, it, vi } from "vitest";
import { render } from "vue";
import { BOX_DRAWING, isBoxDrawing } from "../lib/box_drawing.js";
import NarrativeMarkup from "../lib/narrative_markup.js";
import {
  lineText,
  narrativeBlockNodes,
  narrativeLineNodes,
} from "../lib/narrative_line_nodes.js";

// The feed's literal-glyph spelling of the U+2500..U+257F box-drawing range.
const LITERAL_BOX_DRAWING = /[─-╿]/;

function faceOf(line, index = 0) {
  return narrativeLineNodes(line, index).map((node) => node.props);
}

describe("narrativeLineNodes", () => {
  it("renders an in line at index 0 as a literal .inp line with no divider", () => {
    const nodes = narrativeLineNodes({ kind: "in", text: "<b>look</b>" }, 0);
    expect(nodes).toHaveLength(1);
    expect(nodes[0].props.class).toBe("narrative-line inp");
    expect(nodes[0].props["data-line-kind"]).toBe("in");
    // Player input is literal text — never through the markup pipeline.
    expect(nodes[0].children).toEqual(["<b>look</b>"]);
  });

  it("renders the narrative-divider before an in line at index > 0", () => {
    const nodes = narrativeLineNodes({ kind: "in", text: "look" }, 3);
    expect(nodes).toHaveLength(2);
    expect(nodes[0].props.class).toBe("narrative-divider");
    expect(nodes[0].props.key).toBe("3-divider");
    expect(nodes[0].props["data-testid"]).toBe("narrative-divider");
    expect(nodes[1].props.class).toBe("narrative-line inp");
    expect(nodes[1].props.key).toBe(3);
    expect(nodes[1].props["data-line-kind"]).toBe("in");
  });

  it("tags box-drawing lines with the map-art monospace class", () => {
    const classes = faceOf({ kind: "out", text: "│  北面出口  │" })[0].class;
    expect(classes).toBe("narrative-line out map-art");
  });

  it("escaped BOX_DRAWING agrees with the literal-glyph form on a ─ and a CJK sample", () => {
    // A `─` (U+2500) classifies as box-drawing under both spellings; a CJK
    // sample classifies as prose under both.
    expect(lineText({ text: "─" })).toBe("─");
    expect(LITERAL_BOX_DRAWING.test("─")).toBe(true);
    expect(BOX_DRAWING.test("─")).toBe(true);
    expect(isBoxDrawing("─")).toBe(true);
    expect(faceOf({ kind: "out", text: "─" })[0].class).toContain("map-art");

    expect(LITERAL_BOX_DRAWING.test("標題")).toBe(false);
    expect(BOX_DRAWING.test("標題")).toBe(false);
    expect(isBoxDrawing("標題")).toBe(false);
    expect(faceOf({ kind: "out", text: "標題" })[0].class).not.toContain("map-art");
  });

  it("normalizes a null text to an empty string for both forms", () => {
    expect(lineText({})).toBe("");
    expect(lineText({ text: null })).toBe("");
    expect(narrativeLineNodes({ kind: "out", text: null }, 0)[0].children).toEqual([]);
  });
});

describe("narrativeLineNodes pipeline path", () => {
  it("renders an out line's markup through the preserved allowlist pipeline", () => {
    const children = narrativeLineNodes(
      { kind: "out", text: '<span class="color-203">石板</span> 廣場' },
      0,
    )[0].children;
    const spans = children.filter((child) => child && typeof child === "object" && child.type === "span");
    expect(spans).toHaveLength(1);
    expect(spans[0].props.class).toBe("color-203");
    expect(children).toContain(" 廣場");
  });

  it("renders stored line.tokens identically to the fallback without re-tokenizing", () => {
    const text = '<span class="color-203">石板</span> 廣場';
    const tokens = NarrativeMarkup.tokenize(text);
    const spy = vi.spyOn(NarrativeMarkup, "tokenize");
    try {
      const fromStored = narrativeLineNodes({ kind: "out", text, tokens }, 0);
      expect(spy).not.toHaveBeenCalled();
      const fromFallback = narrativeLineNodes({ kind: "out", text }, 0);
      expect(spy).toHaveBeenCalledTimes(1);
      expect(fromStored).toEqual(fromFallback);
    } finally {
      spy.mockRestore();
    }
  });
});

describe("narrativeBlockNodes", () => {
  it("renders a fragment with its kind and map-art classes", () => {
    const tokens = NarrativeMarkup.tokenize("│  北面出口  │");
    const node = narrativeBlockNodes(
      {
        kind: "out",
        seq: 1,
        mapArt: true,
        first: true,
        tokens,
        start: 0,
        end: 10,
      },
      "frag-0",
    );
    expect(node.props.key).toBe("frag-0");
    expect(node.props.class).toBe("narrative-line out map-art");
    expect(node.props["data-line-kind"]).toBe("out");
    expect(node.children).toEqual(["│  北面出口  │"]);
  });

  it("marks a sys continuation fragment with cont while keeping sys and emphasis classes", () => {
    const firstSys = narrativeBlockNodes(
      {
        kind: "sys",
        seq: 2,
        mapArt: false,
        first: true,
        tokens: NarrativeMarkup.tokenize("系統前段"),
        start: 0,
        end: 4,
      },
      "sys-0",
    );
    const contSys = narrativeBlockNodes(
      {
        kind: "sys",
        seq: 2,
        mapArt: false,
        first: false,
        tokens: NarrativeMarkup.tokenize("系統後段"),
        start: 4,
        end: 8,
      },
      "sys-1",
    );
    expect(firstSys.props.class).toBe("narrative-line sys");
    expect(contSys.props.class).toBe("narrative-line sys cont");
    expect(contSys.props["data-line-kind"]).toBe("sys");

    const contProse = narrativeBlockNodes(
      {
        kind: "out",
        seq: 3,
        mapArt: false,
        first: false,
        tokens: NarrativeMarkup.tokenize('<span class="color-220">重點</span>續句'),
        start: 4,
        end: 8,
      },
      "out-1",
    );
    expect(contProse.props.class).toBe("narrative-line out cont");
    const spans = contProse.children.filter(
      (c) => c && typeof c === "object" && c.type === "span",
    );
    expect(spans).toHaveLength(1);
    expect(spans[0].props.class).toBe("color-220");
  });
});

// webclient-typewriter-reading-prefs (task 2.4): the typewriter reveal.
describe("narrativeBlockNodes reveal", () => {
  const SOURCE =
    '甲乙<span class="color-203" style="color: #ff5555;">丙丁<span class="underline">戊己</span>庚</span>辛<badtag>';

  function fragmentOf(text, extra = {}) {
    const tokens = NarrativeMarkup.tokenize(text);
    let units = 0;
    for (const token of tokens) {
      if (token.kind === "text") units += Array.from(token.value).length;
      if (token.kind === "break") units += 1;
    }
    return { kind: "out", seq: 1, mapArt: false, first: true, tokens, start: 0, end: units, ...extra };
  }

  function mountNode(vnode) {
    const host = document.createElement("div");
    render(vnode, host);
    return host.firstElementChild;
  }

  // Each character with the class/style chain of its ancestors inside the
  // line, skipping the reveal wrapper: equal chains mean equal markup.
  function charChains(line) {
    const out = [];
    const walker = document.createTreeWalker(line, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const chain = [];
      for (let el = node.parentElement; el && el !== line; el = el.parentElement) {
        if (!el.classList.contains("narrative-unrevealed")) {
          chain.unshift(`${el.tagName}.${el.className}|${el.getAttribute("style") || ""}`);
        }
      }
      for (const ch of Array.from(node.textContent)) out.push(`${ch}@${chain.join(">")}`);
    }
    return out;
  }

  function revealedText(line) {
    const clone = line.cloneNode(true);
    clone.querySelectorAll(".narrative-unrevealed").forEach((el) => el.remove());
    return clone.textContent;
  }

  it("leaves the output unchanged with no reveal or a complete reveal", () => {
    const fragment = fragmentOf(SOURCE);
    const plain = mountNode(narrativeBlockNodes(fragment, "k")).outerHTML;
    expect(mountNode(narrativeBlockNodes(fragment, "k", fragment.end)).outerHTML).toBe(plain);
    expect(mountNode(narrativeBlockNodes(fragment, "k", fragment.end + 5)).outerHTML).toBe(plain);
    expect(plain).not.toContain("unrevealed");
  });

  it("hides a fragment with nothing revealed as a whole unrevealed line", () => {
    const line = mountNode(narrativeBlockNodes(fragmentOf(SOURCE, { kind: "sys" }), "k", 0));
    expect(line.classList.contains("unrevealed")).toBe(true);
    expect(line.classList.contains("sys")).toBe(true);
    expect(line.getAttribute("aria-hidden")).toBe("true");
    expect(line.querySelector(".narrative-unrevealed")).toBeNull();
  });

  it("splits at every typing position with head + tail markup equal to the unsplit markup", () => {
    const fragment = fragmentOf(SOURCE);
    const whole = mountNode(narrativeBlockNodes(fragment, "k"));
    const expected = charChains(whole);
    const text = whole.textContent;
    for (let n = 1; n < fragment.end; n += 1) {
      const line = mountNode(narrativeBlockNodes(fragment, "k", n));
      expect(line.classList.contains("unrevealed")).toBe(false);
      const wrapper = line.querySelector(":scope > .narrative-unrevealed");
      expect(wrapper).not.toBeNull();
      expect(wrapper.getAttribute("aria-hidden")).toBe("true");
      expect(line.textContent).toBe(text);
      expect(charChains(line)).toEqual(expected);
      expect(revealedText(line)).toBe(Array.from(text).slice(0, n).join(""));
    }
  });

  it("keeps the degraded literal text and hard breaks through a split", () => {
    const fragment = fragmentOf("甲<br>乙<nope>");
    const whole = mountNode(narrativeBlockNodes(fragment, "k"));
    const line = mountNode(narrativeBlockNodes(fragment, "k", 1));
    expect(line.querySelectorAll("br")).toHaveLength(whole.querySelectorAll("br").length);
    expect(line.querySelector(".narrative-unrevealed br")).not.toBeNull();
    expect(line.textContent).toBe(whole.textContent);
    expect(line.textContent).toContain("<nope>");
  });
});
