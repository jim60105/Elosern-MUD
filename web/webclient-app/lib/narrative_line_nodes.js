// The ONE line→vnode renderer for the narrative surfaces
// (webclient-frontend-utils): a divider plus a literal `.inp` line for
// player input, a pipeline-rendered line for everything else
// (NarrativeMarkup tokens → vnodes through the preserved renderer, the
// degrade-to-literal-text path included), and the monospace stack (`.map-art`)
// for box-drawing lines. The full-log overlay and the narrative feed share
// this module — one renderer, no second markup path.
//
// A box-drawing line is one whose text carries any U+2500..U+257F code
// point (the `─`..`╿` range); `lib/box_drawing.js` owns the single copy.
import { h } from "vue";
import { isBoxDrawing } from "./box_drawing.js";
import NarrativeMarkup from "./narrative_markup.js";
import { renderNarrativeTokens } from "../components/narrative-renderer.js";

export function lineText(line) {
  return line && line.text == null ? "" : String(line.text);
}

// One line → the vnodes that render it, keyed by its position in the
// caller's line stream (the divider carries `${index}-divider` so an input
// line and its hairline are distinct keys).
export function narrativeLineNodes(line, index) {
  const kind = line && line.kind;
  const text = lineText(line);
  const nodes = [];
  if (kind === "in") {
    if (index > 0) {
      nodes.push(
        h("div", {
          key: `${index}-divider`,
          class: "narrative-divider",
          "data-testid": "narrative-divider",
        }),
      );
    }
    nodes.push(
      h("div", { key: index, class: "narrative-line inp", "data-line-kind": "in" }, [text]),
    );
    return nodes;
  }
  const lineClass = kind || "out";
  const classes = ["narrative-line", lineClass];
  if (isBoxDrawing(text)) {
    classes.push("map-art");
  }
  const tokens =
    line && Array.isArray(line.tokens) ? line.tokens : NarrativeMarkup.tokenize(text);
  nodes.push(
    h(
      "div",
      { key: index, class: classes.join(" "), "data-line-kind": lineClass },
      renderNarrativeTokens(tokens),
    ),
  );
  return nodes;
}

// One page fragment → its `.narrative-line.<kind>` vnode (design D5,
// webclient-message-pages). Carries `map-art` when the fragment's line is
// box-drawing and `cont` when the fragment is a continuation after a page cut.
export function narrativeBlockNodes(fragment, key) {
  const lineClass = (fragment && fragment.kind) || "out";
  const classes = ["narrative-line", lineClass];
  if (fragment && fragment.mapArt) {
    classes.push("map-art");
  }
  if (fragment && fragment.first === false) {
    classes.push("cont");
  }
  const tokens = fragment && Array.isArray(fragment.tokens) ? fragment.tokens : [];
  return h(
    "div",
    { key, class: classes.join(" "), "data-line-kind": lineClass },
    renderNarrativeTokens(tokens),
  );
}
