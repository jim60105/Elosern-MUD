<script>
import {
  computed,
  h,
  nextTick,
  onMounted,
  onUpdated,
  ref,
  shallowRef,
  useId,
  vShow,
  watch,
  withDirectives,
} from "vue";
import {
  pageIndexForOffset,
  paginate,
  responseBlocks,
  responseLength,
  segmentResponses,
} from "../lib/message_pages.js";
import { lineText, narrativeBlockNodes } from "../lib/narrative_line_nodes.js";
import { useMessageMeasure } from "../composables/use-message-measure.js";
import { portraitFor, portraitGlyph } from "./party-helpers.js";
import { faceObjectPosition } from "./face-rect.js";

// The AVG message window (docs/superpowers/specs/2026-09-23-webclient-avg-
// stage-redesign-design.md §6; OpenSpec change
// webclient-message-window-component). It fills the band's message region
// and shows the current response one page at a time: a text area above a
// fixed 36px control strip that holds the page marker (`▼` while more pages
// follow, `■` on the last one) and leaves its right end to 日誌 and ⌨.
//
// Pages come from the pure C6a lib (`segmentResponses` → `paginate`); the
// fit test is the hidden DOM measurer of `use-message-measure.js`. The
// `pageFit` prop is a TEST SEAM ONLY: Vitest injects a deterministic
// `fits(fragments)` because jsdom has no layout; the live wiring passes none.
//
// Key scope rule: Enter / Space advance only while focus is on the page
// surface itself, and the handler stops propagation, so the document
// keyboard bridge (`bridge.js` → `store.focusPress`) never turns the key
// into a dock confirm or multi-select toggle. With focus anywhere else the
// keys keep their dock meaning. A click advances unless it lands on a
// control or text is selected (so players can copy text).
//
// Reader state (design D3): mount opens the last response on its last page;
// a new response opens on page 1; an action whose reply has not arrived yet
// (a pending mark, or an echo line with no reply) flushes the shown response
// to its last page; appended lines keep the page; a re-page keeps the page
// holding the first character that was on screen.
//
// While mode is `dialogue` and the dialogue panel is available, the window
// renders the dialogue variant (design D6): unpaged, scrolling
// inside the text area, with the pick, free-dialogue, and exit rows.
export default {
  name: "MessageWindow",
  props: {
    // The narrative log (`store.narrative`): lines with `kind`, `text`,
    // `tokens`, and `seq`.
    lines: { type: Array, default: () => [] },
    // The store's dispatch-time response marks (`store.responseMarks`).
    marks: { type: Array, default: () => [] },
    mode: { type: String, default: "exploration" },
    // The dialogue view model (`dialogueViewModel`), null unless available.
    dialogue: { type: Object, default: null },
    // The committed `art` panel: the host portrait's catalog source.
    artPanel: { type: Object, default: null },
    // The prose scale; a change re-pages (a CSS variable change is invisible
    // to the ResizeObserver).
    fontScale: { type: Number, default: 1 },
    // Test seam: an injected `fits(fragments) -> boolean`.
    pageFit: { type: Function, default: null },
  },
  emits: ["dialogue-pick", "dialogue-freeform", "dialogue-leave", "open-full-log"],
  setup(props, { emit, expose }) {
    const rootRef = ref(null);
    const surfaceRef = ref(null);
    const dialogueScrollRef = ref(null);
    // Registered first so its onMounted creates the measurer before the
    // window's own first paging pass.
    const measure = useMessageMeasure(surfaceRef);
    const pageLabelId = useId();

    const dialogueVariant = computed(() => props.mode === "dialogue" && !!props.dialogue);
    const responses = computed(() => segmentResponses(props.lines, props.marks));

    // A dispatch is out and no line has taken its ordinal yet.
    const pending = computed(() => {
      const marks = Array.isArray(props.marks) ? props.marks : [];
      const lastMark = marks.length > 0 ? marks[marks.length - 1] : null;
      if (typeof lastMark !== "number") {
        return false;
      }
      const lines = Array.isArray(props.lines) ? props.lines : [];
      for (let i = lines.length - 1; i >= 0; i -= 1) {
        const seq = lines[i] && lines[i].seq;
        if (typeof seq === "number") {
          return lastMark > seq;
        }
      }
      return true;
    });

    // The response the window presents. While the reader's action awaits its
    // reply — a pending mark, or a newest response holding only its echo
    // header — the latest response WITH text stays on screen, flushed to its
    // last page, so the window never blanks between an action and its reply.
    const display = computed(() => {
      const list = responses.value;
      let index = list.length - 1;
      let awaiting = pending.value;
      while (index >= 0 && list[index].blocks.length === 0) {
        index -= 1;
        awaiting = true;
      }
      if (index < 0) {
        return { key: null, blocks: [], awaiting: false };
      }
      const response = list[index];
      const key = typeof response.startSeq === "number" ? `s${response.startSeq}` : `i${index}`;
      return { key, blocks: response.blocks, awaiting };
    });

    const pages = shallowRef([]);
    const pageIndex = ref(0);
    const provisional = ref(false);
    const liveText = ref("");
    // The response offset of the first character on screen: the re-page
    // anchor (C7 moves it to the typing position).
    let anchorOffset = 0;
    // The response offset up to which the live region has spoken.
    let announcedEnd = 0;
    let shownKey = null;
    let shownBlocks = null;
    let shownLength = 0;
    let initialized = false;
    let generation = 0;

    function fragmentText(fragment) {
      let text = "";
      for (const token of fragment.tokens || []) {
        if (token && token.kind === "text") {
          text += token.value == null ? "" : String(token.value);
        } else if (token && token.kind === "break") {
          text += "\n";
        }
      }
      return text;
    }

    function announce(text) {
      if (!text) {
        return;
      }
      if (liveText.value === text) {
        // A repeat of identical text must still be heard: clear, then set.
        liveText.value = "";
        void nextTick(() => {
          liveText.value = text;
        });
      } else {
        liveText.value = text;
      }
    }

    // Speak the current page's fragments that begin at or after the
    // watermark (a new page: all of it; lines appended to the page on
    // screen: only their own fragments). Paging is greedy, so an append
    // never re-cuts a fragment that was already on screen.
    function announceCurrentPage({ whole }) {
      const page = pages.value[pageIndex.value];
      if (!page) {
        return;
      }
      const fresh = whole ? page.blocks : page.blocks.filter((f) => f.start >= announcedEnd);
      const text = fresh.map(fragmentText).filter(Boolean).join("\n");
      const pageEnd = page.blocks[page.blocks.length - 1].end;
      announcedEnd = Math.max(announcedEnd, pageEnd);
      announce(text);
    }

    function setPage(index) {
      pageIndex.value = index;
      const page = pages.value[index];
      anchorOffset = page && page.blocks.length > 0 ? page.blocks[0].start : 0;
    }

    function measurePages(blocks) {
      if (blocks.length === 0) {
        return [];
      }
      if (props.pageFit) {
        return paginate(blocks, props.pageFit);
      }
      try {
        return paginate(blocks, measure.fits);
      } finally {
        measure.clear();
      }
    }

    function repage() {
      generation += 1;
      if (dialogueVariant.value) {
        // Leaving the variant reopens like a mount: on the last page.
        initialized = false;
        pages.value = [];
        return;
      }
      const shown = display.value;
      if (!measure.ready.value) {
        // Fonts not ready: the first block, unpaged, scrolling inside.
        provisional.value = true;
        const first = shown.blocks[0];
        pages.value = first
          ? [
              {
                blocks: [
                  {
                    kind: first.kind,
                    seq: first.seq,
                    mapArt: first.mapArt,
                    first: true,
                    tokens: first.tokens,
                    start: 0,
                    end: responseLength([first]),
                  },
                ],
                oversize: true,
              },
            ]
          : [];
        pageIndex.value = 0;
        return;
      }
      provisional.value = false;
      const next = measurePages(shown.blocks);
      const blocksChanged = shown.blocks !== shownBlocks;
      shownBlocks = shown.blocks;
      pages.value = next;
      if (next.length === 0) {
        pageIndex.value = 0;
        return;
      }
      const last = next.length - 1;
      const length = responseLength(shown.blocks);
      const shrank = shown.key === shownKey && length < shownLength;
      shownLength = length;
      // A trim of the log's oldest lines can cut into the shown (leading)
      // response and renumber its offsets; the anchor and watermark are then
      // meaningless, so it settles like a mount.
      if (!initialized || shown.awaiting || shrank) {
        // Mount, resync, or the reader acted: the last page, already read.
        initialized = true;
        shownKey = shown.key;
        announcedEnd = length;
        setPage(last);
        return;
      }
      if (shown.key !== shownKey) {
        // A new response opens on page 1.
        shownKey = shown.key;
        announcedEnd = 0;
        setPage(0);
        announceCurrentPage({ whole: true });
        return;
      }
      // Same response: appended lines or a new box / scale / font. The page
      // holding the anchor stays; only appended text is announced.
      pageIndex.value = Math.min(pageIndexForOffset(next, anchorOffset), last);
      if (blocksChanged) {
        announceCurrentPage({ whole: false });
      }
    }

    function advance() {
      if (dialogueVariant.value || provisional.value) {
        return false;
      }
      if (pageIndex.value >= pages.value.length - 1) {
        return false;
      }
      setPage(pageIndex.value + 1);
      announceCurrentPage({ whole: true });
      return true;
    }

    watch(
      () => [
        display.value.key,
        display.value.blocks,
        display.value.awaiting,
        measure.boxKey.value,
        measure.ready.value,
        dialogueVariant.value,
      ],
      () => repage(),
      { flush: "post" },
    );
    // `--prose-scale` lands on <html> with the preference; re-measure on the
    // next tick unless a newer paging pass already ran.
    watch(
      () => props.fontScale,
      () => {
        const ticket = generation;
        void nextTick(() => {
          if (ticket === generation) {
            repage();
          }
        });
      },
    );

    onMounted(() => {
      repage();
      if (dialogueVariant.value) {
        dialoguePin.value = true;
        void nextTick(pinDialogueBox);
      }
    });

    // ---- reading controls (design D4) ----

    function selectionInside() {
      const selection = typeof window.getSelection === "function" ? window.getSelection() : null;
      if (!selection || selection.isCollapsed || !selection.anchorNode) {
        return false;
      }
      return !!rootRef.value && rootRef.value.contains(selection.anchorNode);
    }

    function onClick(event) {
      if (dialogueVariant.value) {
        return;
      }
      const target = event.target;
      if (target && typeof target.closest === "function" && target.closest("button, a, [role=button]")) {
        return;
      }
      if (selectionInside()) {
        return;
      }
      advance();
      surfaceRef.value?.focus({ preventScroll: true });
    }

    function onSurfaceKeydown(event) {
      if (event.target !== surfaceRef.value) {
        return;
      }
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }
      if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) {
        return;
      }
      // Claimed even on a repeat: a held key must never leak to the dock.
      event.preventDefault();
      event.stopPropagation();
      if (!event.repeat) {
        advance();
      }
    }

    function onWheel(event) {
      if (dialogueVariant.value || !(event.deltaY < 0)) {
        return;
      }
      const surface = surfaceRef.value;
      if (!surface) {
        return;
      }
      const scrollable = surface.scrollHeight > surface.clientHeight + 1;
      if (!scrollable || surface.scrollTop <= 0) {
        emit("open-full-log");
      }
    }

    // ---- dialogue variant (design D6) ----

    // Announce-once: the `.dlg` box renders the same committed line the
    // narrative stream carries, so the stream's record of that exchange is
    // dropped, but ONLY through an anchored match on the final `out` line:
    // the verbatim reply or the adapters' `<host>說：<reply>` echo form. A
    // daily-affinity hint glued to the echo survives as the residual line.
    function suppressDialogueEcho(lines, reply) {
      if (lines.length === 0) {
        return lines;
      }
      const last = lines[lines.length - 1];
      if (!last || (last.kind || "out") !== "out") {
        return lines;
      }
      const text = lineText(last)
        .replace(/<br\s*\/?>/gi, "\n")
        .replace(/<\/?(?:span|a)(?: [^>]*)?>/gi, "");
      const prefixCut = text.lastIndexOf("說：");
      const suffix = prefixCut > 0 ? text.slice(prefixCut + 2) : "";
      const exactEcho =
        prefixCut > 0 &&
        prefixCut <= 48 &&
        !text.slice(0, prefixCut).includes("說：") &&
        suffix.startsWith(reply);
      const remainder = exactEcho
        ? suffix.slice(reply.length).replace(/^(\n|<br\s*\/?>)+/i, "")
        : "";
      const matches =
        text === reply ||
        (exactEcho &&
          (suffix === reply || suffix[reply.length] === "\n" || suffix[reply.length] === "（"));
      if (!matches) {
        return lines;
      }
      // The residual is re-tokenized from its own text (never the stored
      // tokens of the whole echo).
      return remainder === ""
        ? lines.slice(0, -1)
        : [...lines.slice(0, -1), { ...last, text: remainder, tokens: null }];
    }

    const dialogueBlocks = computed(() => {
      if (!dialogueVariant.value) {
        return [];
      }
      const list = responses.value;
      const current = list.length > 0 ? list[list.length - 1] : null;
      const lines = current ? current.lines : [];
      return responseBlocks(suppressDialogueEcho(lines, props.dialogue.line));
    });

    const dialoguePin = ref(false);

    function pinDialogueBox() {
      const el = dialogueScrollRef.value;
      const box = el?.querySelector(".dlg");
      if (!el || !box) {
        return;
      }
      el.scrollTop = Math.max(0, box.offsetTop - 8);
    }

    onUpdated(() => {
      if (dialoguePin.value && dialogueVariant.value) {
        pinDialogueBox();
      }
    });

    watch(
      () => (dialogueVariant.value ? props.dialogue.line : null),
      (line, previous) => {
        if (!dialogueVariant.value) {
          dialoguePin.value = false;
          return;
        }
        if (line !== previous) {
          dialoguePin.value = true;
          void nextTick(pinDialogueBox);
          announce(line);
        }
      },
    );

    function onDialogueScroll() {
      if (!dialoguePin.value) {
        return;
      }
      const el = dialogueScrollRef.value;
      const box = el?.querySelector(".dlg");
      if (box && el) {
        const drift = Math.abs(box.getBoundingClientRect().top - el.getBoundingClientRect().top - 8);
        dialoguePin.value = drift < 64;
      }
    }

    function dialogueNodes(vm) {
      const portrait = portraitFor(props.artPanel, vm.host.portraitRef);
      const nodes = [
        h("div", { key: "dlg-box", class: "dlg", "data-testid": "dialogue-box" }, [
          portrait
            ? h("img", {
                class: "av",
                src: portrait.url,
                alt: vm.host.displayName,
                style: { objectPosition: faceObjectPosition(portrait.face_rect) },
              })
            : h("div", { class: "av" }, [portraitGlyph(vm.host.displayName)]),
          h("div", { class: "body" }, [
            h("div", { class: "who", "data-testid": "dialogue-who" }, [
              vm.host.displayName,
              vm.bondStage == null
                ? null
                : h(
                    "span",
                    { class: "who-bond", "data-testid": "dialogue-bond" },
                    `  ·  羈絆 ${vm.bondStage}`,
                  ),
            ]),
            h("div", { class: "say", "data-testid": "dialogue-say" }, [vm.line]),
          ]),
        ]),
      ];
      if (vm.picks.length > 0 || vm.freeRow) {
        nodes.push(
          h("div", { key: "dlg-choices", class: "choices", "data-testid": "dialogue-choices" }, [
            ...vm.picks.map((pick, index) =>
              h(
                "button",
                {
                  key: pick.key,
                  type: "button",
                  class: "pick",
                  "data-testid": "dialogue-pick",
                  "data-keyword-id": pick.payload.keyword_id,
                  onClick: () => emit("dialogue-pick", pick),
                },
                [h("span", { class: "k" }, String(index + 1)), h("span", { class: "t" }, pick.label)],
              ),
            ),
            vm.freeRow
              ? h(
                  "button",
                  {
                    key: vm.freeRow.key,
                    type: "button",
                    class: "pick",
                    "data-testid": "dialogue-freeform",
                    onClick: () => emit("dialogue-freeform"),
                  },
                  [
                    h("span", { class: "k" }, "⌨"),
                    h("span", { class: "t" }, "自由對話（輸入任意話語）→ 指令列"),
                  ],
                )
              : null,
            h(
              "button",
              {
                key: "dlg-exit",
                type: "button",
                class: "pick pick-exit",
                "data-testid": "dialogue-exit",
                onClick: () => emit("dialogue-leave"),
              },
              [h("span", { class: "k" }, "✕"), h("span", { class: "t" }, "結束對話")],
            ),
          ]),
        );
      }
      return nodes;
    }

    function focus() {
      const target = dialogueVariant.value ? dialogueScrollRef.value : surfaceRef.value;
      target?.focus({ preventScroll: true });
    }

    expose({ focus, advance });

    return () => {
      const variant = dialogueVariant.value ? "dialogue" : "paged";
      const page = pages.value[pageIndex.value] || null;
      const total = pages.value.length;
      const onLast = pageIndex.value >= total - 1;
      const showMarker = variant === "paged" && !provisional.value && total > 0;
      return h(
        "section",
        {
          ref: rootRef,
          class: "message-window",
          "data-testid": "message-window",
          "data-mode": props.mode,
          "data-variant": variant,
          onClick,
          onWheel,
        },
        [
          // Exactly two vnode slots (the dialogue region or its placeholder,
          // then the page surface): the measurer is an untracked DOM node
          // appended after them by use-message-measure.js and must stay the
          // last child, so never add a slot or key a fragment here without
          // moving the measurer into the vnode tree.
          h("div", { class: "message-window__text" }, [
            variant === "dialogue"
              ? h(
                  "div",
                  {
                    ref: dialogueScrollRef,
                    class: "message-window__dialogue",
                    "data-testid": "message-dialogue",
                    tabindex: "-1",
                    onScroll: onDialogueScroll,
                  },
                  [
                    ...dialogueBlocks.value.map((block, index) =>
                      narrativeBlockNodes({ ...block, first: true }, `b${index}`),
                    ),
                    ...dialogueNodes(props.dialogue),
                  ],
                )
              : null,
            // The page surface stays mounted in the dialogue variant (hidden)
            // so the measurer and its observer keep one stable host.
            withDirectives(
              h(
                "div",
                {
                  ref: surfaceRef,
                  class: "message-window__page",
                  "data-testid": "message-page",
                  "data-oversize": page && page.oversize ? "true" : "false",
                  "data-page": total > 0 ? String(pageIndex.value + 1) : "0",
                  "data-pages": String(total),
                  tabindex: "0",
                  "aria-label": "訊息",
                  "aria-describedby": pageLabelId,
                  onKeydown: onSurfaceKeydown,
                },
                page ? page.blocks.map((fragment, index) => narrativeBlockNodes(fragment, `f${index}`)) : [],
              ),
              [[vShow, variant === "paged"]],
            ),
          ]),
          h("div", { class: "message-window__controls" }, [
            showMarker
              ? h(
                  "span",
                  {
                    class: "message-window__marker",
                    "data-testid": "message-page-marker",
                    "data-state": onLast ? "end" : "more",
                    "aria-hidden": "true",
                  },
                  onLast ? "■" : "▼",
                )
              : null,
          ]),
          h(
            "span",
            { id: pageLabelId, class: "message-window__sr" },
            total > 0 ? `第 ${pageIndex.value + 1}／${total} 頁` : "",
          ),
          h(
            "div",
            {
              class: "message-window__sr",
              role: "status",
              "aria-live": "polite",
              "aria-atomic": "true",
              "data-testid": "message-live",
            },
            liveText.value,
          ),
        ],
      );
    };
  },
};
</script>

<style>
/* The message window (design D1). The band behind it is the frame (its
   gradient and top hairline run under both regions), so the window adds no
   card of its own: only a quiet ink rule at its left edge that turns gold
   while the page surface holds keyboard focus. Every selector is prefixed
   and unscoped: page fragments are render-function vnodes and the measurer
   is filled through Vue's `render()`, neither of which carries scope ids.
   No child combinators: the measurer nests the fragments one level deeper
   than the live page. */
.message-window {
  position: relative;
  box-sizing: border-box;
  height: 100%;
  display: flex;
  flex-direction: column;
  color: var(--paper-100);
}

.message-window::before {
  content: "";
  position: absolute;
  left: 0;
  top: 12px;
  bottom: calc(var(--message-controls-h) + 4px);
  width: 1px;
  background: linear-gradient(180deg, transparent, var(--ink-600) 18%, var(--ink-600) 82%, transparent);
  transition: background var(--motion-fast) var(--ease-standard);
  pointer-events: none;
}

.message-window:has(.message-window__page:focus-visible)::before {
  width: 2px;
  background: linear-gradient(180deg, transparent, var(--gold-400) 18%, var(--gold-400) 82%, transparent);
}

.message-window__text {
  position: relative;
  flex: 1;
  min-height: 0;
}

/* The page surface: a centred reading column of at most 42em of text (one
   CJK character is one em) plus its side padding. Its height is the text
   area's; capacity is decided by the measurer, never by a line count. */
.message-window__page {
  box-sizing: border-box;
  width: 100%;
  max-width: calc(42em + 48px);
  height: 100%;
  margin: 0 auto;
  padding: 0 24px;
  overflow: hidden;
  font-family: var(--f-serif);
  font-size: calc(var(--message-text) * var(--prose-scale));
  line-height: var(--message-line-height);
  color: var(--paper-100);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.55);
  outline: none;
}

.message-window__page:focus-visible {
  box-shadow: none;
}

.message-window__page[data-oversize="true"] {
  overflow-y: auto;
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-width: thin;
}

/* The hidden twin (design D2): the page's own classes, content height. */
.message-window__page.message-window__measure {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: auto;
  overflow: visible;
  visibility: hidden;
  pointer-events: none;
}

.message-window .narrative-line {
  margin: 0;
  padding: 0;
  white-space: pre-wrap;
  overflow-wrap: break-word;
}

.message-window .narrative-line + .narrative-line {
  margin-top: 0.2em;
}

.message-window .narrative-line em,
.message-window .narrative-line .em {
  font-style: normal;
  color: var(--gold-400);
}

/* sys: the quieter sans aside with the seal ◈ marker; a continuation
   fragment after a page cut drops the marker (webclient-message-pages D5:
   each consuming surface owns this rule). */
.message-window .narrative-line.sys {
  font-family: var(--f-sans);
  font-size: 0.75em;
  line-height: 1.6;
  letter-spacing: 0.02em;
  color: var(--paper-500);
}

.message-window .narrative-line.sys::before {
  content: "◈ ";
  color: var(--seal-500);
}

.message-window .narrative-line.sys.cont::before {
  content: none;
}

.message-window .narrative-line.err {
  color: var(--seal-400);
  font-style: italic;
}

/* Box-drawing maps: atomic mono blocks with a tight leading so vertical
   strokes join. */
.message-window .narrative-line.map-art {
  font-family: var(--f-mono);
  font-size: 0.6em;
  line-height: 1.15;
  white-space: pre;
  color: var(--paper-300);
  text-shadow: none;
}

/* The control strip: the marker sits left of the 日誌 / ⌨ controls the
   shell places at the region's bottom-right. */
.message-window__controls {
  position: relative;
  flex: none;
  height: var(--message-controls-h);
}

.message-window__marker {
  position: absolute;
  right: 104px;
  bottom: 12px;
  font-size: 14px;
  line-height: 1;
  color: var(--gold-400);
  text-shadow: 0 0 8px var(--gold-glow);
  pointer-events: none;
}

.message-window__marker[data-state="more"] {
  animation: message-window-marker-bob calc(var(--motion-pulse) / 3) var(--ease-standard) infinite;
}

.message-window__marker[data-state="end"] {
  font-size: 10px;
  bottom: 14px;
  color: var(--gold-500);
  text-shadow: none;
}

@keyframes message-window-marker-bob {
  0%,
  100% {
    transform: translateY(0);
    opacity: 1;
  }
  50% {
    transform: translateY(3px);
    opacity: 0.45;
  }
}

.message-window__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}

/* The dialogue variant (design D6): the JRPG box and its pick rows, ported
   from the narrative feed and scaled to the window's text size. Unpaged:
   the exchange scrolls inside the text area. */
.message-window__dialogue {
  --message-dialogue-text: calc(var(--message-text) * 0.72 * var(--prose-scale));
  position: relative;
  box-sizing: border-box;
  height: 100%;
  overflow-y: auto;
  padding: 6px 24px 8px;
  outline: none;
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-width: thin;
}

.message-window__dialogue .narrative-line {
  max-width: 42em;
  margin-bottom: 10px;
  font-family: var(--f-serif);
  font-size: var(--message-dialogue-text);
  line-height: 1.6;
  color: var(--paper-300);
}

.message-window__dialogue .narrative-line.sys {
  font-size: calc(var(--message-dialogue-text) * 0.8);
}

.message-window__dialogue .dlg {
  display: flex;
  gap: 18px;
  align-items: flex-start;
}

.message-window__dialogue .dlg .av {
  width: 82px;
  height: 96px;
  flex: none;
  box-sizing: border-box;
  border-radius: var(--radius-sm);
  background: radial-gradient(60% 70% at 50% 38%, #4a3a2a, #1a150e 82%);
  display: grid;
  place-items: center;
  font-family: var(--f-display);
  font-size: 36px;
  color: var(--gold-400);
  border: 1px solid var(--ink-600);
  box-shadow: 0 0 0 1px rgba(203, 161, 53, 0.28);
  overflow: hidden;
  object-fit: cover;
}

.message-window__dialogue .dlg .body {
  flex: 1;
  min-width: 0;
}

.message-window__dialogue .dlg .who {
  font: 19px var(--f-serif);
  letter-spacing: 0.06em;
  color: var(--gold-400);
  margin-bottom: 8px;
  overflow-wrap: anywhere;
}

.message-window__dialogue .dlg .who .who-bond {
  color: var(--paper-500);
  font-family: var(--f-sans);
  font-size: 12px;
  letter-spacing: 0.04em;
}

.message-window__dialogue .dlg .say {
  max-width: 42em;
  font-family: var(--f-serif);
  font-size: var(--message-dialogue-text);
  line-height: 1.6;
  color: var(--paper-50);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.55);
}

.message-window__dialogue .choices {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
  margin-top: 16px;
}

.message-window__dialogue .choices .pick {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
  min-height: 44px;
  width: 100%;
  box-sizing: border-box;
  text-align: left;
  background: linear-gradient(180deg, var(--panel-hi), var(--panel));
  border: 1px solid #625c50;
  border-radius: var(--radius-sm);
  padding: 9px 12px;
  cursor: pointer;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    background var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}

.message-window__dialogue .choices .pick[data-testid="dialogue-freeform"],
.message-window__dialogue .choices .pick[data-testid="dialogue-exit"] {
  grid-column: 1 / -1;
}

.message-window__dialogue .choices .pick:hover,
.message-window__dialogue .choices .pick:focus-visible {
  border-color: var(--gold-500);
  background: var(--panel-hi);
  transform: translateX(3px);
}

.message-window__dialogue .choices .pick .k {
  flex: none;
  width: 20px;
  padding: 1px 6px;
  font-family: var(--f-mono);
  font-size: 11px;
  text-align: center;
  color: var(--gold-400);
  border: 1px solid var(--gold-500);
  border-radius: 5px;
}

.message-window__dialogue .choices .pick .t {
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 15px;
  color: var(--paper-100);
}

/* The exit row reads as an exit, not another reply. */
.message-window__dialogue .choices .pick-exit .k {
  color: var(--seal-400);
  border-color: var(--seal-600);
}

.message-window__dialogue .choices .pick-exit:hover,
.message-window__dialogue .choices .pick-exit:focus-visible {
  border-color: var(--seal-500);
}
</style>
