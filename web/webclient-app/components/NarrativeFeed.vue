<script>
import { computed, h, nextTick, onMounted, onUpdated, ref, watch } from "vue";
import NarrativeMarkup from "../lib/narrative_markup.js";
import UnreadIndicator from "./UnreadIndicator.vue";
import { renderNarrativeTokens } from "./narrative-renderer.js";
import { portraitFor, portraitGlyph } from "./party-helpers.js";

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
    // The dialogue view model (webclient-align-08-dialogue-surface): the ONE
    // derived shape over the committed `dialogue` panel (null when the panel
    // is unavailable/absent or the mode is not dialogue). The variant renders
    // only while mode is `dialogue` AND this is non-null; the plain fallback
    // (mode dialogue, panel transiently unavailable) keeps the `對話` head
    // label with no dialogue box.
    dialogue: { type: Object, default: null },
    // The committed `art` panel (the portrait catalog source; the same seam
    // the party rows use — schema ships `portrait_ref: null` today, so the
    // gold initial fallback is the exercised path).
    artPanel: { type: Object, default: null },
  },
  emits: ["open-full-log", "dialogue-pick", "dialogue-freeform", "dialogue-leave"],
  setup(props, { expose, emit }) {
    const feedRoot = ref(null);
    // The dedicated scroll viewport (webclient-align-11-dialogue-ux, design
    // D5): the ONLY scrollable element. The head row is a static sibling
    // ABOVE it (inside the card), so narrative content can never render
    // between the card edge and the head. The scroll-keep, unread, and pin
    // owners all live on this element.
    const scrollRoot = ref(null);
    const unread = ref(0);

    const modeLabel = computed(() =>
      props.mode === "combat" ? "戰鬥日誌" : props.mode === "dialogue" ? "對話" : "敘述",
    );
    // The dialogue variant (draft `.feed.m-dialogue`): the box renders while
    // mode is dialogue AND the committed panel is available. The `完整日誌`
    // capsule suppression is scoped to the same available-window (the draft
    // renders no log control in the dialogue variant).
    const dialogueVariant = computed(() => props.mode === "dialogue" && !!props.dialogue);

    const BOX_DRAWING = /[─-╿]/;
    const AT_BOTTOM_SLACK = 8;

    function lineText(line) {
      return line && line.text == null ? "" : String(line.text);
    }

    // Announce-once invariant (design risk §): the `.dlg` box renders the
    // SAME committed line the narrative stream already carries. The variant
    // owns presentation of that exchange, so the exchange's stream record is
    // dropped — but ONLY through an anchored match on the FINAL output line:
    // either the verbatim reply or the deterministic echo form
    // `<host>說：<reply>` the scripted/freeform adapters emit for it. A player
    // input echo (`kind: "in"`) is never suppressed even when its text
    // coincides with the reply, and an older line is never searched
    // backwards. The polite live region keeps announcing each new committed
    // line exactly once.
    const renderedLines = computed(() => {
      const lines = props.lines;
      if (!dialogueVariant.value || lines.length === 0) {
        return lines;
      }
      const last = lines[lines.length - 1];
      // Only outgoing narrative records are echo candidates: player input
      // echoes keep their literal line, and a sys/err record that coincides
      // with the reply is a distinct event the feed must not swallow.
      if (!last || (last.kind || "out") !== "out") {
        return lines;
      }
      // Stored stream text carries the markup pipeline's inline tags; the
      // committed reply is plain server-authored prose. The match runs on text
      // normalized like the renderer sees it: `<br>` becomes a newline and
      // only the pipeline's own recognized tags are removed, so any literal
      // `<...>` prose a hint carries survives verbatim into the residual
      // (where the strict tokenizer renders it as literal text).
      const text = lineText(last)
        .replace(/<br\s*\/?>/gi, "\n")
        .replace(/<\/?(?:span|a)(?: [^>]*)?>/gi, "");
      const reply = props.dialogue.line;
      // The anchored echo form is `<npc key>說：<reply>` (the scripted and
      // freeform adapters' message shape). The key differs from the panel's
      // display_name (no title), so the match anchors on the speech-marker
      // seam and a bounded speaker prefix. A settled exchange may carry the
      // server's daily-affinity hint as a newline-delimited suffix on the
      // same message. The exchange's reply is presentation-duplicated by the
      // box, so the stream keeps ONLY the residual (the hint) after the
      // anchored reply is cut — never the reply twice, never the hint lost.
      const prefixCut = text.lastIndexOf("說：");
      const suffix = prefixCut > 0 ? text.slice(prefixCut + 2) : "";
      const exactEcho =
        prefixCut > 0 &&
        prefixCut <= 48 &&
        !text.slice(0, prefixCut).includes("說：") &&
        suffix.startsWith(reply);
      // The residual is the markup-free remainder AFTER the anchored reply.
      // A null/empty residual means the whole line was the exchange: it drops.
      const remainder = exactEcho ? suffix.slice(reply.length).replace(/^(\n|<br\s*\/?>)+/i, "") : "";
      const matches =
        text === reply ||
        (exactEcho &&
          (suffix === reply ||
            suffix[reply.length] === "\n" ||
            // Belt-and-braces: some markup forms glue the parenthetical hint
            // directly after the reply, so the hint glyph itself is accepted
            // as the seam alongside the newline form.
            suffix[reply.length] === "（"));
      if (!matches) {
        return lines;
      }
      return remainder === ""
        ? lines.slice(0, -1)
        : [...lines.slice(0, -1), { ...last, text: remainder }];
    });

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
      const el = scrollRoot.value;
      if (!el) {
        return true;
      }
      return el.scrollHeight - el.scrollTop - el.clientHeight < AT_BOTTOM_SLACK;
    }

    function scrollToBottom() {
      const el = scrollRoot.value;
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

    // The dialogue variant's focus pin: align the `.dlg` box with the head
    // (the head is a static sibling ABOVE the scroll viewport, so the box
    // pins to the viewport top). A reply + its picks can exceed the bounded
    // caption (the panel caps the exchange at four picks + the trailing
    // free/exit row pair); the box is the newest exchange and keeps its top
    // visible, and the player scrolls the remaining rows within the viewport.
    // The pin holds across renders (a panel commit and its stream push land
    // in separate ticks) until the player scrolls the box away by hand.
    const dialoguePin = ref(false);

    function pinDialogueBox() {
      const el = scrollRoot.value;
      const box = el?.querySelector(".dlg");
      if (!el || !box) {
        scrollToBottom();
        return;
      }
      const prevBehavior = el.style.scrollBehavior;
      el.style.scrollBehavior = "auto";
      // The scroll viewport is positioned, so the box's offsetTop measures its
      // distance from the viewport top; pinning puts the exchange exactly
      // there (a hair of context above costs nothing but reads smoother).
      el.scrollTop = Math.max(0, box.offsetTop - 8);
      el.style.scrollBehavior = prevBehavior;
    }

    // Re-pin on every render while held: the committed panel and the stream
    // push land in separate updates, and each one moves the box.
    onUpdated(() => {
      if (dialoguePin.value && dialogueVariant.value) {
        pinDialogueBox();
      }
    });

    // The at-bottom decision is taken against the old DOM (pre-render),
    // exactly like the legacy single-owner check around each insertion.
    // Watch the array length (not the array reference) so a push or a trim
    // both trigger the auto-scroll / unread logic. The dialogue variant's
    // committed line joins the signature: the box sits at the stream tail, so
    // a panel commit that changes the reply must re-pin the view even when the
    // stream length itself did not move (the duplicate tail is suppressed).
    watch(
      () => [props.lines.length, dialogueVariant.value ? props.dialogue.line : null],
      ([newLen, newLine], [oldLen, oldLine] = []) => {
        const added = Math.max(0, newLen - (oldLen ?? 0));
        const variant = dialogueVariant.value;
        // A reply change only owns the focus while the variant is presented;
        // the null→line transition on ENTERING the variant counts as a new
        // reply, and the line→null transition on EXITING it must not be
        // mistaken for one (it would pin and scroll a box that no longer
        // exists).
        const replyChanged = variant && newLine !== oldLine;
        const wasAtBottom = atBottom();
        if (!variant && dialoguePin.value) {
          // Exiting the variant releases the pin — the box is gone and the
          // pin must not survive to leak into a later dialogue mount.
          dialoguePin.value = false;
        }
        void nextTick().then(() => {
          if (added === 0 && !replyChanged) {
            return;
          }
          if (replyChanged) {
            // A committed dialogue reply owns the caption's focus: the box is
            // pinned into view even when the player had scrolled the stream
            // away (the exchange it carries is the newest line).
            // The box IS the newest exchange, so the commit clears unread.
            dialoguePin.value = true;
            unread.value = 0;
            pinDialogueBox();
          } else if (wasAtBottom) {
            scrollToBottom();
          } else if (added > 0 && !dialoguePin.value) {
            // While the dialogue variant pins, the newest exchange stays
            // visible in the box — nothing arrived unread.
            unread.value += added;
          }
        });
      },
    );

    function onScroll() {
      if (dialoguePin.value) {
        // Manual scrolling that moves the box away from its pin releases the
        // pin; the pin's own scroll assignments keep it.
        const el = scrollRoot.value;
        const box = el?.querySelector(".dlg");
        if (box && el) {
          const drift = Math.abs(
            box.getBoundingClientRect().top -
              el.getBoundingClientRect().top -
              8,
          );
          dialoguePin.value = drift < 64;
        }
      }
      if (atBottom() && unread.value > 0) {
        unread.value = 0;
      }
    }

    function jumpToLatest() {
      const el = scrollRoot.value;
      if (el) {
        el.focus({ preventScroll: true });
      }
      if (dialogueVariant.value) {
        pinDialogueBox();
      } else {
        scrollToBottom();
      }
      unread.value = 0;
    }

    function focusFeed() {
      scrollRoot.value?.focus({ preventScroll: true });
    }

    onMounted(() => {
      if (dialogueVariant.value) {
        // Mounting INTO the dialogue variant: the box is the newest exchange
        // from the first render, so nothing is unread and the card opens
        // pinned to it instead of the stream history's top.
        unread.value = 0;
        dialoguePin.value = true;
        void nextTick().then(pinDialogueBox);
      } else {
        scrollToBottom();
      }
    });

    expose({ focus: focusFeed });

    // The draft's `.dlg` box (JRPG dialogue): the host avatar (the bound
    // portrait through the art catalog when `portrait_ref` resolves, else the
    // display name's initial letter in the gold display face), the gold
    // speaker line (display_name plus ` · 羈絆 <stage>` only when bond_stage
    // is non-null), and the serif reply line verbatim. The numbered picks and
    // the trailing free-dialogue row follow under the draft's `.choices`
    // markup — activation emits through the same single dispatch entry the
    // dock rows use (AppClient maps the emits to the store).
    function dialogueNodes(vm) {
      const portrait = portraitFor(props.artPanel, vm.host.portraitRef);
      const nodes = [];
      nodes.push(
        h("div", { key: "dlg-box", class: "dlg", "data-testid": "dialogue-box" }, [
          portrait
            ? h("img", { class: "av", src: portrait.url, alt: vm.host.displayName })
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
      );
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
                [
                  h("span", { class: "k" }, String(index + 1)),
                  h("span", { class: "t" }, pick.label),
                ],
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
            // The exit row (webclient-align-11-dialogue-ux, design D6): the
            // caption's own way out — dispatches the deterministic
            // `explore.dialogue_leave` seam through the parent wiring (no
            // confirm: the clear is consequence-free, races reject
            // idempotently). Takes no digit slot, like the free row.
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

    return () =>
      h(
        "div",
        {
          ref: feedRoot,
          class: ["elosern elosern-narrative feed-inner", dialogueVariant.value ? "m-dialogue" : null],
        },
        [
          // The head is a STATIC sibling above the scroll viewport (design
          // D5): nothing can ever render between the card edge and the head.
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
              // The reference's dialogue variant renders no log control — the
              // capsule is suppressed only inside the available window (the
              // transient-unavailable fallback keeps its plain presentation,
              // capsule included).
              dialogueVariant.value
                ? null
                : h(
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
          // The dedicated scroll viewport: the ONLY scrollable surface, and
          // the `role="log"` live region (the scroll-keep/unread/pin owners
          // all address this element).
          h(
            "div",
            {
              ref: scrollRoot,
              class: "narrative-scroll",
              role: "log",
              "aria-label": "敘事紀錄",
              tabindex: "-1",
              // The feed test id lives on the scroll viewport: the managed
              // browser suites drive `scrollTop`/`scrollHeight` against this
              // element, and the id keeps its "the scrollable feed" meaning
              // (webclient-align-11 DOM contract: the outer card carries no
              // overflow, tabindex, role, or test id).
              "data-testid": "narrative-feed",
              onScroll,
            },
            [
              ...renderedLines.value.flatMap((line, index) => lineNodes(line, index)),
              // The dialogue variant sits at the stream tail: the box REPLACES
              // the caption's duplicate stream tail for that exchange, so the
              // auto-scroll that keeps the latest exchange in view keeps the
              // box and its picks in view too (draft dialogue mode shows no
              // history stream at all).
              ...(dialogueVariant.value ? dialogueNodes(props.dialogue) : []),
            ],
          ),
        ],
      );
  },
};
</script>

<style>
/* Bounded caption card (design D4, draft .feed-inner): panel fill with
   backdrop blur, hairline border, shared radius and shadow, and the left
   hairline gradient rule. webclient-align-11-dialogue-ux (design D5): the
   card itself never scrolls — the head is a static sibling and the bounded
   scrolling lives in `.narrative-scroll`, so content can never appear
   between the card edge and the head. */
.elosern-narrative {
  position: relative;
  box-sizing: border-box;
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
   capsule control. Static (never sticky): it lives ABOVE the scroll viewport. */
.elosern-narrative .narrative-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px 0;
  background: var(--panel-solid);
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--paper-500);
  text-transform: uppercase;
}

/* The dedicated scroll viewport: the bounded region (the 32vh caption bound
   moved here), positioned so the dialogue pin can measure the box's offsetTop
   against the viewport itself. */
.elosern-narrative .narrative-scroll {
  position: relative;
  box-sizing: border-box;
  max-height: 32vh;
  overflow-y: auto;
  padding: 8px 20px 15px;
  scroll-behavior: smooth;
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

/* The dialogue variant (webclient-align-08-dialogue-surface, draft index.html
   .dlg/.choices/.pick rules): the JRPG box — 64px rounded avatar tile with the
   radial gold-initial ground, the gold speaker line, the serif reply — and
   the numbered pick rows with mono digit badges. */
.elosern-narrative .dlg {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.elosern-narrative .dlg .av {
  width: 64px;
  height: 64px;
  flex: none;
  border-radius: 12px;
  background: radial-gradient(60% 70% at 50% 38%, #4a3a2a, #1a150e 82%);
  display: grid;
  place-items: center;
  font-family: var(--f-display);
  font-size: 30px;
  color: var(--gold-400);
  border: 1px solid var(--ink-600);
  box-shadow: 0 0 0 1px rgba(203, 161, 53, 0.28);
  overflow: hidden;
  object-fit: cover;
}

.elosern-narrative .dlg .av img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.elosern-narrative .dlg .body {
  flex: 1;
  min-width: 0;
}

.elosern-narrative .dlg .who {
  font-size: 13px;
  letter-spacing: 0.06em;
  color: var(--gold-400);
  margin-bottom: 5px;
  font-weight: 600;
}

.elosern-narrative .dlg .who .who-bond {
  color: var(--paper-500);
  font-weight: 400;
  font-size: 11px;
}

.elosern-narrative .dlg .say {
  font-family: var(--f-serif);
  font-size: calc(16px * var(--prose-scale));
  line-height: 1.78;
  color: var(--paper-50);
}

.elosern-narrative .choices {
  /* Two-column pick grid (design D5): with the four-choice panel cap the
     exchange unit fits the bounded caption; the trailing free + exit rows
     form one spanning row pair below the grid. Narrow viewports collapse to
     one column. */
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  margin-top: 13px;
}

@media (max-width: 640px) {
  .elosern-narrative .choices {
    grid-template-columns: minmax(0, 1fr);
  }
}

.elosern-narrative .choices .pick {
  display: flex;
  align-items: center;
  gap: 11px;
  text-align: left;
  width: 100%;
  background: linear-gradient(180deg, var(--panel-hi), var(--panel));
  border: 1px solid var(--ink-600);
  border-radius: 9px;
  padding: 9px 12px;
  cursor: pointer;
  transition: border-color 0.12s, background 0.12s, transform 0.12s;
}

/* The free + exit rows span the full grid width as the trailing pair. */
.elosern-narrative .choices .pick[data-testid="dialogue-freeform"],
.elosern-narrative .choices .pick[data-testid="dialogue-exit"] {
  grid-column: 1 / -1;
}

/* The exit row reads as an exit, not another reply: the seal accent stays the
   one deliberate red on the caption. */
.elosern-narrative .choices .pick-exit .k {
  color: var(--seal-400);
}

.elosern-narrative .choices .pick-exit:hover,
.elosern-narrative .choices .pick-exit:focus-visible {
  border-color: var(--seal-500);
}

.elosern-narrative .choices .pick:hover,
.elosern-narrative .choices .pick:focus-visible {
  border-color: var(--gold-500);
  background: var(--panel-hi);
  transform: translateX(3px);
}

.elosern-narrative .choices .pick .k {
  font-family: var(--f-mono);
  font-size: 11px;
  color: var(--paper-500);
  border: 1px solid var(--ink-600);
  border-radius: 5px;
  padding: 1px 6px;
  flex: none;
  width: 20px;
  text-align: center;
}

.elosern-narrative .choices .pick .t {
  font-size: 14.5px;
  color: var(--paper-100);
}
</style>
