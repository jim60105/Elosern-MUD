<script>
// FullLogOverlay (H1, webclient-hud-01-shell-and-scene, design D4): the
// full-screen, scrollable view of the complete retained narrative. It
// renders the same line stream through the preserved
// `narrative-renderer.js` — never a second markup path — and carries the
// focus contract: focus-trapped while open, Escape closes, and focus is
// restored to the control that opened it. The caption card's `完整日誌`
// control is the single one-action escape hatch (MODIFIED
// webclient-desktop-shell: the complete log is reachable in one action).
import { h, ref } from "vue";
import NarrativeMarkup from "../lib/narrative_markup.js";
import ChoicePointBlock from "./ChoicePointBlock.vue";
import { renderNarrativeTokens } from "./narrative-renderer.js";
import { createFocusTrap } from "./focus-trap.js";

export default {
  name: "FullLogOverlay",
  props: {
    // The full retained narrative line stream (the store's `narrative`
    // slice, unbounded).
    lines: { type: Array, default: () => [] },
    // The committed `context_actions.suggestions` envelope: the stream-end
    // choice-point block renders after the lines, exactly like the feed.
    suggestions: { type: Object, default: null },
  },
  emits: ["close", "choice-action"],
  setup(props, { emit, expose }) {
    const overlayEl = ref(null);
    // The opener (the active element before the overlay took focus). When the
    // overlay closes, focus is restored to this element (design D4).
    const preFocus = ref(null);
    // H4 (task 2.2): the shared focusable-query trap (design D5) replaces the
    // hard-coded two-element cycle; the overlay's existing Escape and
    // focus-restore behaviour is unchanged.
    let trap = null;

    function focusSelf() {
      preFocus.value = document.activeElement;
      trap = createFocusTrap(overlayEl.value, {
        initialFocusEl: overlayEl.value,
        openerEl: preFocus.value,
      });
      trap.enter();
    }

    function restoreOpenerFocus() {
      if (trap) {
        trap.restore();
        return;
      }
      if (preFocus.value instanceof HTMLElement && document.contains(preFocus.value)) {
        preFocus.value.focus();
      }
    }

    function onKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        restoreOpenerFocus();
        emit("close");
        return;
      }
      if (event.key !== "Tab") {
        // A focus-trapped surface owns every key it receives
        // (webclient-pointer-activation): stop propagation so the
        // document-level keyboard bridge (and the router behind the overlay)
        // never consumes navigation keys while the overlay holds trapped
        // focus — "the router consumes nothing behind it".
        event.stopPropagation();
      }
      if (event.key === "Tab" && trap) {
        // The shared trap cycles Tab across every focusable control in the
        // overlay (the close button, the choice-point cards), never into the
        // recessed background (design D5).
        trap.onKeydown(event);
      }
    }

    function onChoiceAction(intent) {
      // The stream-end choice-point card/dismiss intents route through the
      // same single dispatch entry as the dock (store is the sole writer).
      emit("choice-action", intent);
    }

    expose({ focusSelf });

    // The same line mapping as the feed: a divider plus a literal `.inp`
    // line for player input, a pipeline-rendered line for everything else,
    // and the monospace stack for box-drawing lines. One renderer, no
    // second markup path (design D4).
    const BOX_DRAWING = /[\u2500-\u257f]/;

    function lineText(line) {
      return line && line.text == null ? "" : String(line.text);
    }

    function lineNodes(line, index) {
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

    return () =>
      h(
        "div",
        {
          ref: overlayEl,
          class: "fulllog-overlay",
          "data-testid": "fulllog-overlay",
          tabindex: "-1",
          role: "dialog",
          "aria-modal": "true",
          onKeydown: onKeyDown,
        },
        [
          h(
            "button",
            {
              type: "button",
              class: "fulllog-close",
              "data-testid": "fulllog-close",
              onClick: () => {
                restoreOpenerFocus();
                emit("close");
              },
            },
            "關閉",
          ),
          ...props.lines.flatMap((line, index) => lineNodes(line, index)),
          h(ChoicePointBlock, {
            suggestions: props.suggestions,
            onAction: onChoiceAction,
          }),
        ],
      );
  },
};
</script>

<style>
/* The full-screen scrollable log view: the complete retained narrative,
   rendered through the same renderer as the caption card. H5 (design D13):
   the full-log surface's lines are a prose-scale target. */
.fulllog-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  overflow-y: auto;
  background: var(--ink-950);
  color: var(--paper-100);
  font-family: var(--f-serif);
  font-size: calc(var(--text-narrative) * var(--prose-scale));
  line-height: var(--lh-narrative);
  padding: var(--sp-6);
  outline: none;
}

.fulllog-overlay .fulllog-close {
  position: sticky;
  top: 0;
  float: right;
  margin: calc(-1 * var(--sp-6)) calc(-1 * var(--sp-6)) var(--sp-3) var(--sp-3);
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: var(--text-sm);
  padding: 2px var(--sp-3);
  cursor: pointer;
}

.fulllog-overlay .fulllog-close:hover {
  border-color: var(--gold-500);
  color: var(--paper-50);
}

/* The same line styles as the feed (one markup path). */
.fulllog-overlay .narrative-line {
  max-width: 72ch;
  margin: 0 auto;
  padding: 2px var(--sp-6);
  white-space: pre-wrap;
  overflow-wrap: break-word;
}

.fulllog-overlay .narrative-line.map-art {
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  line-height: 1.4;
  white-space: pre;
}

.fulllog-overlay .narrative-line.inp {
  color: var(--gold-400);
}

.fulllog-overlay .narrative-line.inp::before {
  content: "> ";
  color: var(--paper-500);
}

.fulllog-overlay .narrative-line.sys,
.fulllog-overlay .narrative-line.err {
  color: var(--paper-500);
  font-style: italic;
}

.fulllog-overlay .narrative-line.err {
  color: var(--seal-400);
}

.fulllog-overlay .narrative-divider {
  max-width: 72ch;
  margin: var(--sp-3) auto 0;
  height: 1px;
  background: var(--line);
}
</style>
