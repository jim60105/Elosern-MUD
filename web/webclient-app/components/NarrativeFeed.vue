<script>
import { h, nextTick, onMounted, ref, watch } from "vue";
import NarrativeMarkup from "../lib/narrative_markup.js";
import UnreadIndicator from "./UnreadIndicator.vue";
import ChoicePointBlock from "./ChoicePointBlock.vue";
import { renderNarrativeTokens } from "./narrative-renderer.js";

// Bounded narrative caption card (H1, design D4): the narrative is a
// bounded caption at the visual centre of the stage — `width:min(880px,90vw)`,
// `max-height:30vh` (set by the `feed` anchor), blurred panel chrome. The
// card carries a single labelled control (`完整日誌`) that opens the
// full-log surface presenting the complete retained narrative through the
// same markup renderer (never a second markup path). The `#narrative-unread`
// indicator, its polite live region, and the jump-to-latest behaviour
// remain on the card, unchanged.

// Narrative feed (the story centerpiece): renders the narrative log slice.
// Server-transformed lines (out/sys/err) render through the preserved
// NarrativeMarkup allowlist pipeline (tokens → vnodes, the
// degrade-to-literal-text path included); player input lines (`.inp`) are
// literal text nodes that never enter the pipeline, each preceded by a
// `.narrative-divider` hairline unless the log has no prior line (Phase-0
// audit §2.3 `.inp`/`.narrative-divider` contract). Box-drawing lines keep
// the monospace stack (`.map-art`).
//
// Scroll-keep and the unread marker are one owner here, like the legacy
// shell: lines landing while the reader is at the bottom auto-scroll; lines
// landing while away count into the UnreadIndicator instead. Jumping to the
// latest line moves focus to the narrative pane first so focus never drops
// into a hidden element. Line contents are dynamic vnodes, so the component
// renders vnodes directly (setup returns the render function).
export default {
  name: "NarrativeFeed",
  props: {
    lines: { type: Array, default: () => [] },
    // The committed `context_actions.suggestions` envelope (or null). The
    // stream-end choice-point block renders from this slice (the AI-only
    // surface — generating and ready only).
    suggestions: { type: Object, default: null },
  },
  emits: ["choice-action", "open-full-log"],
  setup(props, { expose, emit }) {
    const feedRoot = ref(null);
    const unread = ref(0);

    const BOX_DRAWING = /[\u2500-\u257f]/;
    const AT_BOTTOM_SLACK = 8;

    function lineText(line) {
      return line && line.text == null ? "" : String(line.text);
    }

    // One line → the vnodes that render it: a divider plus a literal `.inp`
    // line for player input, a pipeline-rendered line for everything else.
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

    function atBottom() {
      const el = feedRoot.value;
      if (!el) {
        return true;
      }
      return el.scrollHeight - el.scrollTop - el.clientHeight < AT_BOTTOM_SLACK;
    }

    function scrollToBottom() {
      const el = feedRoot.value;
      if (el) {
        // The feed's stylesheet sets `scroll-behavior: smooth` for user
        // programmatic scrolls; the deterministic auto-scroll must be instant,
        // so override the behavior for this single assignment.
        const prevBehavior = el.style.scrollBehavior;
        el.style.scrollBehavior = "auto";
        el.scrollTop = el.scrollHeight;
        el.style.scrollBehavior = prevBehavior;
      }
    }

    // The at-bottom decision is taken against the old DOM (pre-render),
    // exactly like the legacy single-owner check around each insertion.
    // Watch the array length (not the array reference) so a push or a trim
    // both trigger the auto-scroll / unread logic.
    //
    // `lastSettledSh` tracks the content height of the last settled render.
    // The stream-end choice-point block (webclient-action-choicepoints) swaps
    // its generating line / ready group in place, and that in-place re-render
    // can complete before a watcher callback reads the DOM, so the
    // "reader was tracking the stream end" decision for a block swap is made
    // against the last settled geometry, never the live mid-swap DOM.
    const lastSettledSh = ref(0);

    watch(
      () => props.lines.length,
      (newLen, oldLen) => {
        const added = Math.max(0, newLen - (oldLen ?? 0));
        const wasAtBottom = atBottom();
        void nextTick().then(() => {
          const el = feedRoot.value;
          if (el) {
            lastSettledSh.value = el.scrollHeight;
          }
          if (added === 0) {
            return;
          }
          if (wasAtBottom) {
            scrollToBottom();
          } else {
            unread.value += added;
          }
        });
      },
    );

    // The stream-end choice-point block (webclient-action-choicepoints): the
    // generating line and the taller ready group are the SAME DOM node swapping
    // content in place, so the `lines.length` watcher alone would not keep the
    // stream end visible across the swap. Watch the suggestions status (sync
    // flush, at the store commit) and auto-scroll for a reader pinned at the
    // bottom, deciding "was at the stream end" from the settled height that
    // preceded the current block content (`preBlockSh`), never the mid-swap DOM.
    const preBlockSh = ref(0);

    watch(
      () => (props.suggestions && props.suggestions.status) || "none",
      (status) => {
        const el = feedRoot.value;
        const wasAtBottom =
          !el || preBlockSh.value - el.scrollTop - el.clientHeight < AT_BOTTOM_SLACK;
        void nextTick().then(() => {
          const el2 = feedRoot.value;
          if (el2) {
            // `lastSettledSh` still holds the pre-swap height here; hand it to
            // `preBlockSh` as the reference for the next in-place swap.
            preBlockSh.value = lastSettledSh.value;
            lastSettledSh.value = el2.scrollHeight;
          }
          if (wasAtBottom) {
            scrollToBottom();
          }
        });
      },
      { flush: "sync" },
    );

    function onScroll() {
      if (atBottom() && unread.value > 0) {
        unread.value = 0;
      }
    }

    function jumpToLatest() {
      const el = feedRoot.value;
      if (el) {
        el.focus({ preventScroll: true });
      }
      scrollToBottom();
      unread.value = 0;
    }

    function focusFeed() {
      feedRoot.value?.focus({ preventScroll: true });
    }

    onMounted(() => {
      scrollToBottom();
    });

    expose({ focus: focusFeed });

    return () =>
      h(
        "div",
        {
          ref: feedRoot,
          class: "elosern elosern-narrative",
          role: "log",
          "aria-label": "敘事紀錄",
          tabindex: "-1",
          "data-testid": "narrative-feed",
          onScroll,
        },
        [
          h(
            "div",
            { class: "narrative-head", "data-testid": "narrative-head" },
            [
              h(UnreadIndicator, {
                count: unread.value,
                onJump: () => {
                  jumpToLatest();
                },
              }),
              h(
                "button",
                {
                  type: "button",
                  class: "narrative-fulllog-control",
                  "data-testid": "narrative-fulllog-control",
                  onClick: () => emit("open-full-log"),
                },
                "完整日誌",
              ),
            ],
          ),
          ...props.lines.flatMap((line, index) => lineNodes(line, index)),
          // The stream-end choice-point block (webclient-action-choicepoints):
          // rendered after the lines so it stays at the stream end and is
          // re-parented (moved down) when newer narrative text lands, exactly
          // like the legacy `appendNode` insertBefore-the-block semantics.
          h(ChoicePointBlock, {
            suggestions: props.suggestions,
            onAction: (intent) => emit("choice-action", intent),
          }),
        ],
      );
  },
};
</script>

<style>
/* Bounded caption card (design D4): the card takes the `feed` anchor's
   geometry (`width:min(880px,90vw)`, `max-height:30vh`), carries the
   draft's blurred panel chrome, and never grows to fill the stage. The
   card scrolls internally when the narrative outgrows its bounded height. */
.elosern-narrative {
  position: relative;
  box-sizing: border-box;
  max-height: 30vh;
  overflow-y: auto;
  padding: 14px 20px 15px;
  scroll-behavior: smooth;
  background: var(--panel);
  backdrop-filter: blur(7px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

/* The caption's head row: the unread indicator and the `完整日誌` control
   (the one-action escape hatch to the complete log). */
.elosern-narrative .narrative-head {
  position: sticky;
  top: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  padding: 4px 0;
  background: var(--panel-solid);
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--paper-500);
  text-transform: uppercase;
}

.elosern-narrative .narrative-head .narrative-fulllog-control {
  margin-left: auto;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: 99px;
  color: var(--paper-300);
  cursor: pointer;
  font-family: var(--f-sans);
  font-size: 11px;
  letter-spacing: 0;
  padding: 3px 10px;
  text-transform: none;
}

.elosern-narrative .narrative-head .narrative-fulllog-control:hover {
  border-color: var(--gold-500);
  color: var(--paper-50);
}

.elosern-narrative .narrative-line {
  max-width: 72ch;
  margin: 0 auto;
  padding: 2px var(--sp-6);
  font-family: var(--f-serif);
  /* H5 (design D13): the caption card's lines are a prose-scale target. */
  font-size: calc(var(--text-narrative) * var(--prose-scale));
  line-height: var(--lh-narrative);
  color: var(--paper-100);
  white-space: pre-wrap;
  overflow-wrap: break-word;
}

.elosern-narrative .narrative-line.map-art {
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  line-height: 1.4;
  white-space: pre;
}

.elosern-narrative .narrative-line.inp {
  color: var(--gold-400);
}

.elosern-narrative .narrative-line.inp::before {
  content: "> ";
  color: var(--paper-500);
}

.elosern-narrative .narrative-line.sys,
.elosern-narrative .narrative-line.err {
  color: var(--paper-500);
  font-style: italic;
}

.elosern-narrative .narrative-line.err {
  color: var(--seal-400);
}

.elosern-narrative .narrative-divider {
  max-width: 72ch;
  margin: var(--sp-3) auto 0;
  height: 1px;
  background: var(--line);
}
</style>
