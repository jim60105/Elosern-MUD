<script>
// FullLogOverlay (H1, webclient-hud-01-shell-and-scene, design D4): the
// scrollable view of the complete retained narrative. It renders the same
// line stream through the preserved `narrative-renderer.js` — never a second
// markup path.
//
// Frame (webclient-full-log-frame): the log sits in the shared reference
// workspace — an opaque panel under the shared `DrawerHeader` — over a scrim
// that covers the whole viewport and absorbs pointer input without closing.
// The header only borrows markup: the log keeps its own focus trap, Escape
// close and opener restore, and nests no second modal host. The lines read
// as one centred 42em column; each retained input echo is styled in place
// as the heading of the response it begins.
//
// Open-at-latest-line rule (design D6): the log's scroll region opens
// scrolled to its end. Lines that arrive while open never move the reader.
// While the reader is above the end, the footer strip — outside the text,
// so it never covers a line or a selection — offers 回到最新, marked 新內容
// once a line has arrived; activating it scrolls the region only.
//
// focus contract: focus-trapped while open (initial focus on the scroll
// region, so the reading keys scroll at once), Escape closes, and focus is
// restored to the control that opened it.
import { h, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { narrativeLineNodes } from "../lib/narrative_line_nodes.js";
import DrawerHeader from "./DrawerHeader.vue";
import { createFocusTrap } from "./focus-trap.js";

// The scroll region counts as "at the end" within this many pixels.
const END_SLACK_PX = 4;
// Reading keys the log routes to its scroll region when focus sits on one of
// its controls (the header close, 回到最新), so the footer legend holds in
// every focus state.
const LINE_STEP_PX = 48;
const READING_KEYS = new Set(["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End"]);

// The newest retained line's identity: its monotonic `seq`, which survives
// the store's retention trimming (the line count stops growing at the
// retention cap), or the count for a bare line stream.
function lastLineKey(lines) {
  const last = lines[lines.length - 1];
  if (!last) {
    return 0;
  }
  return typeof last.seq === "number" ? `seq:${last.seq}` : `n:${lines.length}`;
}

export default {
  name: "FullLogOverlay",
  props: {
    // The retained narrative line stream (the store's `narrative` slice,
    // trimmed at the head past its retention cap).
    lines: { type: Array, default: () => [] },
  },
  emits: ["close"],
  setup(props, { emit, expose }) {
    const rootEl = ref(null);
    const scrollEl = ref(null);
    const columnEl = ref(null);
    const latestEl = ref(null);
    // The opener (the active element before the overlay took focus). When the
    // overlay closes, focus is restored to this element (design D4).
    const preFocus = ref(null);
    // Whether the scroll region shows its end, and whether a line arrived
    // since the reader last saw it.
    const atEnd = ref(true);
    const fresh = ref(false);
    // H4 (task 2.2): the shared focusable-query trap (design D5).
    let trap = null;
    let resizeObserver = null;

    function measure() {
      const el = scrollEl.value;
      if (!el) {
        return;
      }
      atEnd.value = el.scrollTop + el.clientHeight >= el.scrollHeight - END_SLACK_PX;
      if (atEnd.value) {
        // The end is in view: nothing is unseen.
        fresh.value = false;
      }
    }

    function focusSelf() {
      preFocus.value = document.activeElement;
      trap = createFocusTrap(rootEl.value, {
        initialFocusEl: scrollEl.value,
        openerEl: preFocus.value,
      });
      trap.enter();
      if (scrollEl.value) {
        scrollEl.value.scrollTop = scrollEl.value.scrollHeight;
      }
      fresh.value = false;
      measure();
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

    function close() {
      restoreOpenerFocus();
      emit("close");
    }

    function scrollToLatest() {
      const el = scrollEl.value;
      if (!el) {
        return;
      }
      // Focus moves to the region first: the control leaves once the end is
      // in view, and focus must never fall out of the trapped surface.
      el.focus();
      const smooth = document.documentElement.dataset.motion === "full";
      if (typeof el.scrollTo === "function") {
        el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
      } else {
        el.scrollTop = el.scrollHeight;
      }
      measure();
    }

    // A reading key pressed on one of the log's controls scrolls the region
    // as it would with the region focused, and hands focus to the region.
    function routeReadingKey(event) {
      const el = scrollEl.value;
      if (
        !el ||
        event.target === el ||
        !READING_KEYS.has(event.key) ||
        event.ctrlKey ||
        event.metaKey ||
        event.altKey
      ) {
        return;
      }
      event.preventDefault();
      el.focus();
      const page = Math.max(LINE_STEP_PX, el.clientHeight * 0.9);
      const deltas = {
        ArrowUp: -LINE_STEP_PX,
        ArrowDown: LINE_STEP_PX,
        PageUp: -page,
        PageDown: page,
      };
      if (event.key === "Home") {
        el.scrollTop = 0;
      } else if (event.key === "End") {
        el.scrollTop = el.scrollHeight;
      } else {
        el.scrollTop += deltas[event.key];
      }
      measure();
    }

    function onKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        close();
        return;
      }
      if (event.key !== "Tab") {
        // A focus-trapped surface owns every key it receives
        // (webclient-pointer-activation): stop propagation so the
        // document-level keyboard bridge (and the router behind the overlay)
        // never consumes navigation keys while the overlay holds trapped
        // focus — "the router consumes nothing behind it".
        event.stopPropagation();
        routeReadingKey(event);
        return;
      }
      if (trap) {
        // The shared trap cycles Tab across every focusable control in the
        // overlay, never into the recessed background (design D5).
        trap.onKeydown(event);
      }
    }

    // Arrivals never touch the scroll offset; once rendered, an arrival the
    // reader cannot see (the end is out of view) marks new content. A shrink
    // (a cleared log) re-measures too.
    watch(
      () => lastLineKey(props.lines),
      (key, previous) => {
        void nextTick(() => {
          measure();
          if (key !== previous && key !== 0 && !atEnd.value) {
            fresh.value = true;
          }
        });
      },
    );
    watch(
      () => props.lines.length,
      () => void nextTick(measure),
    );

    // Runs before the DOM update that removes 回到最新 at the end, so a
    // focused control hands focus to the region first.
    watch(
      atEnd,
      (value) => {
        if (!value) {
          return;
        }
        if (latestEl.value && document.activeElement === latestEl.value) {
          scrollEl.value?.focus();
        }
      },
      { flush: "pre" },
    );

    onMounted(() => {
      // Late layout (a web-font swap, a resize) changes the content height
      // without a scroll event.
      if (typeof ResizeObserver === "function") {
        resizeObserver = new ResizeObserver(() => measure());
        if (scrollEl.value) resizeObserver.observe(scrollEl.value);
        if (columnEl.value) resizeObserver.observe(columnEl.value);
      }
    });

    onBeforeUnmount(() => {
      resizeObserver?.disconnect();
      resizeObserver = null;
    });

    expose({ focusSelf });

    const titleId = "fulllog-title";

    return () =>
      h(
        "div",
        {
          ref: rootEl,
          class: "fulllog-overlay",
          "data-testid": "fulllog-overlay",
          // A click on the scrim or the frame's chrome keeps focus inside
          // the surface (on this root), under its own key handling.
          tabindex: "-1",
          onKeydown: onKeyDown,
        },
        [
          h("div", {
            class: "fulllog-overlay__scrim",
            "data-testid": "fulllog-scrim",
            "aria-hidden": "true",
          }),
          h(
            "section",
            {
              class: "fulllog-overlay__panel",
              role: "dialog",
              "aria-modal": "true",
              "aria-labelledby": titleId,
            },
            [
              h(DrawerHeader, {
                surface: "fulllog",
                icon: "log",
                title: "日誌",
                subtitle: "完整紀錄 ‧ 由舊到新",
                titleId,
                onClose: close,
              }),
              h(
                "div",
                {
                  ref: scrollEl,
                  class: "fulllog-overlay__scroll",
                  "data-testid": "fulllog-scroll",
                  tabindex: "0",
                  role: "region",
                  "aria-label": "日誌內容",
                  onScroll: measure,
                },
                [
                  // The same line mapping as the message window's source
                  // stream: a divider plus a literal `.inp` line for player
                  // input, a pipeline-rendered line for everything else, and
                  // the monospace stack for box-drawing lines. One renderer,
                  // no second markup path (design D4) — shared
                  // lib/narrative_line_nodes.js.
                  h(
                    "div",
                    { ref: columnEl, class: "fulllog-overlay__column" },
                    props.lines.flatMap((line, index) => narrativeLineNodes(line, index)),
                  ),
                ],
              ),
              h("footer", { class: "fulllog-overlay__foot" }, [
                h(
                  "span",
                  { class: "fulllog-overlay__legend", "aria-hidden": "true" },
                  "↑↓ 捲動 ‧ End 最新 ‧ Esc 關閉",
                ),
                atEnd.value
                  ? null
                  : h(
                      "button",
                      {
                        ref: latestEl,
                        type: "button",
                        class: "fulllog-overlay__latest",
                        "data-testid": "fulllog-latest",
                        "data-fresh": fresh.value ? "true" : "false",
                        onClick: scrollToLatest,
                      },
                      [
                        fresh.value
                          ? h("span", { class: "fulllog-overlay__fresh" }, [
                              h("span", { class: "fulllog-overlay__pip", "aria-hidden": "true" }),
                              "新內容",
                            ])
                          : null,
                        h("span", null, "回到最新"),
                        h(
                          "svg",
                          { viewBox: "0 0 16 16", width: "14", height: "14", "aria-hidden": "true" },
                          [
                            h("path", {
                              d: "M8 2.5v10M3.5 8.5 8 13l4.5-4.5",
                              fill: "none",
                              stroke: "currentColor",
                              "stroke-width": "1.5",
                              "stroke-linecap": "round",
                              "stroke-linejoin": "round",
                            }),
                          ],
                        ),
                      ],
                    ),
              ]),
            ],
          ),
        ],
      );
  },
};
</script>

<style>
/* The stacking root: every part of the log rides the shared modal tier. */
.fulllog-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-surface-modal);
  outline: none;
}

/* The scrim covers the whole viewport, the top navigation included — the
   log is modal over everything — and absorbs pointer input without closing
   (the utility-overlay convention: a stray click never drops the reader's
   place). */
.fulllog-overlay__scrim {
  position: absolute;
  inset: 0;
  background: var(--surface-scrim);
}
@supports (backdrop-filter: blur(1px)) {
  .fulllog-overlay__scrim { backdrop-filter: blur(2px) saturate(.8); }
}

/* The shared reference workspace (drawers and utility overlays): 12px under
   the top navigation, 16px side insets, `--workspace-bottom` above the
   viewport bottom, a fully opaque ink panel with the fine gold frame. */
.fulllog-overlay__panel {
  position: absolute;
  top: calc(var(--header-h) + 12px * var(--ui-scale));
  left: calc(16px * var(--ui-scale));
  right: calc(16px * var(--ui-scale));
  bottom: var(--workspace-bottom);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #bca57966;
  border-radius: var(--radius);
  background: var(--surface-panel);
  box-shadow: 0 calc(16px * var(--ui-scale)) calc(64px * var(--ui-scale)) #000a, inset 0 1px 0 #e8d8aa14;
}

.fulllog-overlay__scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: var(--gold-500) transparent;
  scrollbar-width: thin;
  outline: none;
}

/* The reading rule the message window's page shows under keyboard focus. */
.fulllog-overlay__scroll:focus-visible {
  box-shadow: inset 2px 0 0 var(--gold-500);
}

/* Forced colours drop box shadows: a system outline marks the focus. */
@media (forced-colors: active) {
  .fulllog-overlay__scroll:focus-visible {
    outline: 2px solid CanvasText;
    outline-offset: -2px;
  }
}

/* The reading column: the message window's prose at the log's reading size
   (a prose-scale target), on a 42em measure. The measure lives on the
   column, so smaller `sys` asides and maps share its left edge. */
.fulllog-overlay__column {
  box-sizing: content-box;
  max-width: 42em;
  margin: 0 auto;
  padding: calc(28px * var(--ui-scale)) calc(32px * var(--ui-scale)) calc(48px * var(--ui-scale));
  color: var(--paper-100);
  font-family: var(--f-serif);
  font-size: calc(var(--log-text) * var(--prose-scale));
  line-height: 1.75;
}

.fulllog-overlay .narrative-line {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  /* The message window's progressive CJK prose spacing
     (webclient-message-typesetting); maps and echoed commands opt out. */
  text-autospace: normal;
  text-spacing-trim: trim-start;
  line-break: strict;
}

.fulllog-overlay .narrative-line + .narrative-line {
  margin-top: var(--message-paragraph-gap);
}

/* A response's section rule: the hairline before each input echo, gold at
   the heading's side and fading out across the column. */
.fulllog-overlay .narrative-divider {
  height: 1px;
  margin: 1.6em 0 0.75em;
  background: linear-gradient(90deg, #cfb3787a, #cfb37826 40%, transparent 85%);
}

/* The input echo, styled in place as the heading of the response it
   begins: the quiet sans label seated on a small lozenge. */
.fulllog-overlay .narrative-line.inp {
  position: relative;
  padding-left: calc(20px * var(--ui-scale));
  font-family: var(--f-sans);
  font-size: calc(var(--text-md) * var(--prose-scale));
  line-height: 1.5;
  letter-spacing: 0.06em;
  color: var(--gold-400);
}

.fulllog-overlay .narrative-line.inp::before {
  content: "";
  position: absolute;
  left: calc(3px * var(--ui-scale));
  top: calc(0.75em - 4px * var(--ui-scale));
  width: calc(7px * var(--ui-scale));
  height: calc(7px * var(--ui-scale));
  box-sizing: border-box;
  border: 1px solid var(--gold-400);
  background: var(--ink-900);
  transform: rotate(45deg);
}

.fulllog-overlay .narrative-line.inp + .narrative-line {
  margin-top: 0.6em;
}

.fulllog-overlay .narrative-line.map-art,
.fulllog-overlay .narrative-line.inp {
  text-autospace: no-autospace;
  text-spacing-trim: space-all;
  line-break: auto;
}

.fulllog-overlay .narrative-line em,
.fulllog-overlay .narrative-line .em {
  font-style: normal;
  color: var(--gold-400);
}

.fulllog-overlay .narrative-line.sys {
  font-family: var(--f-sans);
  font-size: 0.75em;
  line-height: 1.6;
  letter-spacing: 0.02em;
  color: var(--paper-500);
}

.fulllog-overlay .narrative-line.sys::before {
  content: "◈ ";
  color: var(--seal-500);
}

.fulllog-overlay .narrative-line.err {
  color: var(--seal-400);
  font-style: italic;
}

/* Box-drawing maps: a mono grid with a tight leading so strokes join; a
   map wider than the column scrolls inside its own block. */
.fulllog-overlay .narrative-line.map-art {
  max-width: 100%;
  overflow-x: auto;
  font-family: var(--f-mono);
  font-size: 0.8em;
  line-height: 1.15;
  white-space: pre;
  color: var(--paper-300);
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-width: thin;
}

/* The footer strip: outside the scroll region, so nothing in it ever covers
   a line or a selection. Its height never changes with its content. */
.fulllog-overlay__foot {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: calc(16px * var(--ui-scale));
  height: calc(44px * var(--ui-scale));
  box-sizing: border-box;
  padding: 0 calc(12px * var(--ui-scale)) 0 calc(20px * var(--ui-scale));
  border-top: 1px solid var(--ink-700);
  background: linear-gradient(180deg, #121418, #0e1013);
}

.fulllog-overlay__legend {
  color: var(--paper-500);
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.fulllog-overlay__latest {
  display: inline-flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  padding: 0 calc(12px * var(--ui-scale)) 0 calc(14px * var(--ui-scale));
  color: var(--paper-100);
  background: var(--ink-780);
  border: 1px solid #cfb37866;
  border-radius: var(--radius-sm);
  font: var(--text-sm) var(--f-sans);
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: color var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}

.fulllog-overlay__latest:hover {
  color: var(--gold-400);
  border-color: var(--gold-500);
}

.fulllog-overlay__latest:focus-visible {
  outline: none;
  color: var(--gold-400);
  border-color: var(--gold-400);
  box-shadow: var(--focus);
}

.fulllog-overlay__fresh {
  display: inline-flex;
  align-items: center;
  gap: calc(6px * var(--ui-scale));
  padding-right: calc(8px * var(--ui-scale));
  border-right: 1px solid var(--ink-600);
  color: var(--gold-400);
}

.fulllog-overlay__pip {
  width: calc(6px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  border-radius: 50%;
  background: var(--gold-400);
  box-shadow: 0 0 calc(6px * var(--ui-scale)) var(--gold-glow);
}
</style>
