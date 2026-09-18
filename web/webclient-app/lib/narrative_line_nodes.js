// The ONE line→vnode renderer for the narrative surfaces
// (webclient-frontend-utils): a divider plus a literal `.inp` line for
// player input, a pipeline-rendered line for everything else
// (NarrativeMarkup tokens → vnodes through the preserved renderer, the
// degrade-to-literal-text path included), and the monospace stack (`.map-art`)
// for box-drawing lines. The full-log overlay and the narrative feed share
// this module — one renderer, no second markup path.
//
// A box-drawing line is one whose text carries any U+2500..U+257F code
// point (the `─`..`╿` range); the escaped form is the single copy.
import { h } from "vue";
import NarrativeMarkup from "./narrative_markup.js";
import { renderNarrativeTokens } from "../components/narrative-renderer.js";

const BOX_DRAWING = /[\u2500-\u257f]/;

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
  if (BOX_DRAWING.test(text)) {
    classes.push("map-art");
  }
  nodes.push(
    h(
      "div",
      { key: index, class: classes.join(" "), "data-line-kind": lineClass },
      renderNarrativeTokens(NarrativeMarkup.tokenize(text)),
    ),
  );
  return nodes;
}
