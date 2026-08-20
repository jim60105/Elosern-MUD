// Vue renderer for the preserved narrative markup token stream (design D3).
// The tokenizer (web/static/webclient/js/elosern/narrative_markup.js, imported
// through the A2 lib wrapper) already enforces the strict server-side
// allowlist: accepted spans/breaks become element tokens, and everything
// unrecognized degrades to a literal text token, so no element is ever built
// from markup the pipeline did not accept. This module only maps the token
// stream to vnodes; degraded text renders as plain text vnodes.
import { h } from "vue";

export function renderNarrativeTokens(tokens) {
  const root = [];
  const stack = [root];
  const top = () => stack[stack.length - 1];
  for (const token of tokens) {
    if (!token || typeof token.kind !== "string") {
      continue;
    }
    if (token.kind === "text") {
      top().push(token.value);
    } else if (token.kind === "break") {
      top().push(h("br"));
    } else if (token.kind === "open") {
      const props = {};
      const classes = Array.isArray(token.classes) ? token.classes : [];
      if (classes.length) {
        props.class = classes.join(" ");
      }
      if (token.style) {
        const style = {};
        if (token.style.color) {
          style.color = token.style.color;
        }
        if (token.style.backgroundColor) {
          style.backgroundColor = token.style.backgroundColor;
        }
        if (Object.keys(style).length) {
          props.style = style;
        }
      }
      // The children array is referenced by the span vnode and filled as the
      // remaining tokens of the same span are processed; Vue reads it only at
      // mount, after the whole stream has been consumed.
      const children = [];
      top().push(h("span", props, children));
      stack.push(children);
    } else if (token.kind === "close") {
      // The tokenizer balances opens/closes (an unbalanced close degrades to
      // text there), so this never pops below the line root.
      if (stack.length > 1) {
        stack.pop();
      }
    }
  }
  return root;
}
