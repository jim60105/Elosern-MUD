<script>
import { computed, h, nextTick, onMounted, ref, watch } from "vue";
import NarrativeMarkup from "../lib/narrative_markup.js";
import UnreadIndicator from "./UnreadIndicator.vue";
import { renderNarrativeTokens } from "./narrative-renderer.js";

// Bounded narrative caption card (H1, design D4): the narrative is a
// bounded caption at the visual centre of the stage — `width:min(880px,90vw)`,
// `max-height:30vh` (set by the `feed` anchor), blurred panel chrome. The
// card carries a head row naming the mode and a single labelled control
// (`完整日誌 ↑`) that opens the full-log surface presenting the complete
// retained narrative through the same markup renderer (never a second markup
// path). The `#narrative-unread` indicator, its polite live region, and the
// jump-to-latest behaviour remain on the card beside the mode label.

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
    mode: { type: String, default: "exploration" },
  },
  emits: ["open-full-log"],
  setup(props, { expose, emit }) {
    const feedRoot = ref(null);
    const unread = ref(0);

    const modeLabel = computed(() => (props.mode === "combat" ? "戰鬥日誌" : "敘述"));

    const BOX_DRAWING = /[─-╿]/;
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
    watch(
      () => props.lines.length,
      (newLen, oldLen) => {
        const added = Math.max(0, newLen - (oldLen ?? 0));
        const wasAtBottom = atBottom();
        void nextTick().then(() => {
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
          class: "elosern elosern-narrative feed-inner",
          role: "log",
          "aria-label": "敘事紀錄",
          tabindex: "-1",
          "data-testid": "narrative-feed",
          onScroll,
        },
        [
          h(
            "div",
            { class: "narrative-head head", "data-testid": "narrative-head" },
            [
              h(
                "span",
                {
                  class: "narrative-mode-label",
                  "data-testid": "narrative-mode-label",
                },
                modeLabel.value,
              ),
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
                  class: "narrative-fulllog-control more",
                  "data-testid": "narrative-fulllog-control",
                  "data-openlog": "",
                  onClick: () => emit("open-full-log"),
                },
                "完整日誌 ↑",
              ),
            ],
          ),
          ...props.lines.flatMap((line, index) => lineNodes(line, index)),
        ],
      );
  },
};
</script>

<style>
/* Bounded caption card (design D4, draft .feed-inner): panel fill with
   backdrop blur, hairline border, shared radius and shadow, and the left
   hairline gradient rule. Internal scrolling within bounded height. */
.elosern-narrative {
  position: relative;
  box-sizing: border-box;
  max-height: 32vh;
  overflow-y: auto;
  padding: 14px 20px 15px;
  scroll-behavior: smooth;
  background: var(--panel);
  backdrop-filter: blur(7px);
  -webkit-backdrop-filter: blur(7px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.elosern-narrative::before {
  content: "";
  position: absolute;
  left: -16px;
  top: 10px;
  bottom: 10px;
  width: 2px;
  background: linear-gradient(180deg, transparent, var(--ink-600) 12%, var(--ink-600) 88%, transparent);
}

/* The caption's head row: mode label, unread indicator, and the `完整日誌 ↑`
   capsule control. */
.elosern-narrative .narrative-head {
  position: sticky;
  top: 0;
  z-index: 1;
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

.elosern-narrative .narrative-head .narrative-mode-label {
  font-family: var(--f-sans);
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

.elosern-narrative .narrative-line em,
.elosern-narrative .narrative-line .em {
  font-style: normal;
  color: var(--gold-400);
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

.elosern-narrative .narrative-line.sys {
  font-family: var(--f-sans);
  font-size: calc(13px * var(--prose-scale));
  color: var(--paper-500);
  font-style: normal;
}

.elosern-narrative .narrative-line.sys::before {
  content: "◈ ";
  color: var(--seal-500);
}

.elosern-narrative .narrative-line.err {
  color: var(--seal-400);
  font-style: italic;
}

.elosern-narrative .narrative-divider {
  max-width: 72ch;
  margin: var(--sp-3) auto 0;
  height: 1px;
  background: var(--line);
}
</style>
