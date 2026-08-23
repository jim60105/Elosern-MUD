<script>
import { h, nextTick, onMounted, ref, watch } from "vue";
import NarrativeMarkup from "../lib/narrative_markup.js";
import UnreadIndicator from "./UnreadIndicator.vue";
import ChoicePointBlock from "./ChoicePointBlock.vue";
import { renderNarrativeTokens } from "./narrative-renderer.js";

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
  emits: ["choice-action"],
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
        el.scrollTop = el.scrollHeight;
      }
    }

    let previousLength = props.lines.length;

    // The at-bottom decision is taken against the old DOM (pre-render),
    // exactly like the legacy single-owner check around each insertion.
    watch(
      () => props.lines,
      () => {
        const added = Math.max(0, props.lines.length - previousLength);
        previousLength = props.lines.length;
        if (added === 0) {
          return;
        }
        const wasAtBottom = atBottom();
        void nextTick().then(() => {
          if (wasAtBottom) {
            scrollToBottom();
          } else {
            unread.value += added;
          }
        });
      },
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
          h(UnreadIndicator, {
            count: unread.value,
            onJump: () => {
              jumpToLatest();
            },
          }),
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
.elosern-narrative {
  position: relative;
  box-sizing: border-box;
  overflow-y: auto;
  padding: var(--sp-4) 0 calc(var(--sp-4) + env(safe-area-inset-bottom, 0px));
  scroll-behavior: smooth;
}

.elosern-narrative .narrative-line {
  max-width: 72ch;
  margin: 0 auto;
  padding: 2px var(--sp-6);
  font-family: var(--f-serif);
  font-size: var(--text-narrative);
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
