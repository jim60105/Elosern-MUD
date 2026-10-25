<script>
import {
  Transition,
  computed,
  h,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  useId,
  watch,
} from "vue";
import {
  pageIndexForOffset,
  paginate,
  responseLength,
  segmentResponses,
} from "../lib/message_pages.js";
import { beatBlocks, beatPages, tailBlocks } from "../lib/beat_queue.js";
import { readMotionMs } from "../lib/motion_tokens.js";
import { narrativeBlockNodes } from "../lib/narrative_line_nodes.js";
import {
  TEXT_SPEEDS,
  autoAdvanceAllowed,
  autoAdvanceDelayMs,
  effectiveCps,
  fragmentReveal,
  offsetAtUnits,
  pageUnits,
  snapUnits,
  unitsAtOffset,
} from "../lib/message_reveal.js";
import { useMessageMeasure } from "../composables/use-message-measure.js";
import { useTypewriter } from "../composables/use-typewriter.js";
import { MOTION_LEVELS } from "../lib/motion_level.js";
import { inertWhileLeaving } from "../lib/transition_hooks.js";
import { PROSE_SCALE_DEFAULT } from "../lib/prose_scale.js";

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
// holding the reader's typing position.
//
// Typewriter (OpenSpec change webclient-typewriter-reading-prefs): each page
// the window starts to show types in at the reader's `textSpeed`, driven by
// the rAF clock of `use-typewriter.js`. The page is always rendered in full
// and the unrevealed tail is hidden with `visibility: hidden` and
// `aria-hidden` (`narrativeBlockNodes`' `reveal`), so nothing re-wraps while
// typing. The typing position is the re-page anchor: the next character to
// reveal while typing, the last character shown once complete. A click or
// Enter / Space while typing completes the page instead of advancing; the
// marker renders only on a fully shown page. Mount and a flush show the page
// complete; the live region still announces a page once, when it starts.
// An effective motion level other than `full` makes every page instant
// (webclient-motion-level, design D5): the window reads the level the store
// resolved — never `matchMedia` itself — so the stylesheet and the typewriter
// cannot disagree. Opt-in auto-advance arms on a fully shown page with a next
// page (never past the last page, never on an oversize or map page) and
// pauses while `held` (an open drawer, overlay, or the full log).
//
// Dialogue (webclient-dialogue-choices-overlay D1/D3): the window pages and
// types the session line exactly like any response. While mode is
// `dialogue` and the dialogue panel is available, the host's name plate
// heads the text area (webclient-dialogue-stage-actors D7), and the text
// column starts under the player portrait's anchor edge. The window holds no
// choice row: the centred `DialogueChoices` list over the stage does. The
// window reports `reading-change` — true exactly while the current
// response's last page is on screen, fully shown, with no pending action
// mark — so the shell knows when the list may appear. `focusHome()` focuses
// the page surface.
//
// Combat beats (webclient-combat-beat-queue, design D6): while a published
// round is bound to the response on screen, that response's pages are the
// round's beat pages — each beat paginated alone — followed by the response's
// remaining lines. At `full` and `reduced` the queue paces itself: each beat
// page is revealed at the reader's speed, its last page's completion reports
// `beat-shown`, and a further page of the same beat waits the beat pause read
// from `--motion-beat`. A pointer activation, or Enter / Space on the page
// surface, emits `beat-skip` instead of completing or advancing; the marker is
// hidden and auto-advance is disarmed, because the queue paces the pages. At
// `off` the beat pages and the following pages are ordinary reader pages.
//
// Authored scenes (authored-dialogue-playback; `use-authored-scene.js` owns
// the line cursor): while the `scene` prop is set the window presents the
// scene's CURRENT LINE instead of the narrative response — the server also
// logs every line as transcript, which stays in the full log and is never
// re-typed here. Each line is paginated and typed like a response; the
// window owns pages and the composable owns lines. An activation while a
// page types completes it; on a fully shown page with a further page it
// turns the page; on the line's last fully shown page it emits
// `scene-advance` (next line, or the explicit finish on the final line).
// The scene mode never arms auto-advance and never binds a combat round.
// Line changes patch the page in place (no clear layer between lines, so
// text, plate and stage emphasis change in one frame); the clear layer plays
// only when a new delivery replaces what was on screen. The plate row is
// reserved for the whole scene — narration renders an invisible spacer in
// its place — so the text area never re-measures between speakers. Leaving
// a scene settles the narrative it covered on its last page, already read.
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
    // The person in focus in exploration (exploration-presence-rail): the
    // name plate names them while their verb card is open, so the plate is
    // already up when 交談 hands the standee to the dialogue screen.
    speaker: { type: String, default: null },
    // The prose scale; a change re-pages (a CSS variable change is invisible
    // to the ResizeObserver).
    fontScale: { type: Number, default: PROSE_SCALE_DEFAULT },
    // Test seam: an injected `fits(fragments) -> boolean`.
    pageFit: { type: Function, default: null },
    // The reader's typing speed (`store.view.textSpeed`).
    textSpeed: {
      type: String,
      default: "normal",
      validator: (value) => TEXT_SPEEDS.includes(value),
    },
    // Opt-in auto-advance (`store.view.autoAdvance`).
    autoAdvance: { type: Boolean, default: false },
    // The EFFECTIVE motion level (`store.view.motionLevel`).
    motionLevel: {
      type: String,
      default: "full",
      validator: (value) => MOTION_LEVELS.includes(value),
    },
    // True while a drawer, overlay, or the full log is open: the
    // auto-advance wait pauses.
    held: { type: Boolean, default: false },
    // True across a reconnect's null mode edges (webclient-mode-transitions
    // D2): the name plate then appears and goes with no fade.
    modeHydrating: { type: Boolean, default: false },
    // The playing combat round (`store.view.beatPlayback`,
    // webclient-combat-beat-queue D5/D6): null, or the published slice whose
    // `startSeq` names the response it belongs to. Its `texts` are the beat
    // pages and `coveredLines` the response lines they replace.
    beatPlayback: { type: Object, default: null },
    // The authored scene's current line (`useAuthoredScene().presentation`):
    // null, or `{key, lineIndex, lineCount, kind, text, speaker, speakerName,
    // bondStage, last, finished}`.
    scene: { type: Object, default: null },
    // True while a scripted topic pick awaits its reply in dialogue: the
    // window keeps what it shows until the reply commits, so a transcript
    // line arriving before its scene delivery never types on its own.
    sceneHold: { type: Boolean, default: false },
  },
  emits: ["open-full-log", "reading-change", "beat-shown", "beat-skip", "scene-advance"],
  setup(props, { emit, expose }) {
    const rootRef = ref(null);
    const surfaceRef = ref(null);
    // Registered first so its onMounted creates the measurer before the
    // window's own first paging pass.
    const measure = useMessageMeasure(surfaceRef);
    const pageLabelId = useId();

    // The name plate renders while the dialogue panel is available, and in
    // exploration while a person is in focus.
    const dialoguePlated = computed(() => props.mode === "dialogue" && !!props.dialogue);
    // An authored scene reserves the plate row: its speaker's plate, or an
    // invisible spacer for narration.
    const scenePlated = computed(() => !!props.scene);
    const plated = computed(() => scenePlated.value || dialoguePlated.value || (props.mode === "exploration" && !!props.speaker));
    const plateName = computed(() => {
      if (scenePlated.value) return props.scene.speakerName || null;
      return dialoguePlated.value ? props.dialogue.host.displayName : props.speaker;
    });
    const plateBond = computed(() => {
      if (scenePlated.value) return props.scene.bondStage ?? null;
      return dialoguePlated.value ? props.dialogue.bondStage ?? null : null;
    });
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
    const narrativeDisplay = computed(() => {
      const list = responses.value;
      let index = list.length - 1;
      let awaiting = pending.value;
      while (index >= 0 && list[index].blocks.length === 0) {
        index -= 1;
        awaiting = true;
      }
      if (index < 0) {
        return { key: null, blocks: [], awaiting: false, startSeq: null };
      }
      const response = list[index];
      const key = typeof response.startSeq === "number" ? `s${response.startSeq}` : `i${index}`;
      return {
        key,
        blocks: response.blocks,
        awaiting,
        startSeq: typeof response.startSeq === "number" ? response.startSeq : null,
      };
    });

    // A scene line as one pageable block, memoized per line so a same-line
    // re-render (an availability refresh) keeps the block identity and the
    // reader's page.
    let sceneBlockCache = null;
    function sceneBlocks(scene) {
      const id = `${scene.key}:${scene.lineIndex}`;
      if (!sceneBlockCache || sceneBlockCache.id !== id || sceneBlockCache.text !== scene.text) {
        sceneBlockCache = {
          id,
          text: scene.text,
          blocks: [
            {
              kind: scene.kind === "narration" ? "narration" : "out",
              seq: null,
              text: scene.text,
              tokens: [{ kind: "text", value: scene.text }],
              mapArt: false,
            },
          ],
        };
      }
      return sceneBlockCache.blocks;
    }

    // Scene bookkeeping: the clear group on screen, whether a scene line is
    // on screen, and the narrative response the scene covered (settled, not
    // re-typed, when the scene retires).
    let shownGroup = null;
    let shownScene = false;
    let sceneCoveredKey = null;

    // The display a pick froze while it awaits its reply. While held, the
    // transcript arriving for the reply is not counted as read; when the
    // hold releases onto a (new) scene, that transcript is the scene's own.
    const heldDisplay = shallowRef(null);
    watch(
      () => props.sceneHold,
      (hold, before) => {
        heldDisplay.value = hold ? (props.scene ? null : narrativeDisplay.value) : null;
        if (!hold && before && props.scene && shownScene) {
          sceneCoveredKey = narrativeDisplay.value.key;
        }
      },
      { flush: "sync", immediate: true },
    );

    const display = computed(() => {
      const scene = props.scene;
      if (scene) {
        return {
          key: `scene:${scene.key}:${scene.lineIndex}`,
          group: `scene:${scene.key}`,
          scene: true,
          blocks: sceneBlocks(scene),
          awaiting: false,
          startSeq: null,
        };
      }
      return heldDisplay.value || narrativeDisplay.value;
    });

    // The round bound to the response on screen (design D6): the published
    // slice whose `startSeq` is this response's own start. A round attached to
    // any other response leaves the window alone.
    const boundBeats = computed(() => {
      const bound = props.beatPlayback;
      if (props.scene || !bound || typeof bound.startSeq !== "number") {
        return null;
      }
      return bound.startSeq === display.value.startSeq ? bound : null;
    });
    // The page list's identity: the response the round belongs to and the
    // beats it replaces. A rebuild happens only when this changes.
    const beatBinding = computed(() => {
      const bound = boundBeats.value;
      if (!bound) {
        return null;
      }
      const texts = Array.isArray(bound.texts) ? bound.texts : [];
      return `${bound.startSeq}:${bound.coveredLines}:${texts.join("\u0000")}`;
    });
    // A round the queue paces by itself: `off` never plays, and a round that
    // has ended is read like any other response.
    const beatPlaying = computed(() => {
      const bound = boundBeats.value;
      return !!bound && bound.auto && bound.phase !== "done";
    });
    // The playback's identity: the binding, the level, the current beat, and
    // the phase. The pacing watcher re-evaluates on any of them.
    const beatSignature = computed(() => {
      const bound = boundBeats.value;
      return bound ? `${bound.startSeq}:${bound.auto}:${bound.index}:${bound.phase}` : null;
    });

    const pages = shallowRef([]);
    // The bound round's page layout: each beat's first page, and the first
    // tail page (-1 when the response has no line after the beats). `layoutSeq`
    // counts bound re-pages, so the queue repositions itself after one.
    const beatStarts = shallowRef([]);
    const beatTailStart = shallowRef(-1);
    let layoutSeq = 0;
    let followedLayout = -1;
    let followedBeat = null;
    // The beats already reported to the store, and whether the end-of-round
    // move to the first tail page has run; both belong to one binding.
    let reportedBeats = new Set();
    let tailMoved = false;
    let laidOutFor = null;
    let wasBeatPlaying = false;
    // The queue's own in-beat page timer. It is deliberately NOT the
    // typewriter's armed wait: that one counts only unheld frame time, so an
    // open drawer or the full log would freeze a multi-page beat and hold the
    // command panel with it. The queue's pause is held-agnostic, exactly like
    // the store's inter-beat one.
    let beatPageTimer = null;
    // The response the pages were cut from (design D3): a new or appended
    // response dirties `display` at once, before the post-flush re-page, so
    // completeness is never read off the previous response's stale pages.
    const pagedBlocks = shallowRef(null);
    const layoutKey = ref(null);
    const layoutBinding = ref(null);
    const layoutCurrent = computed(() => measure.ready.value &&
      layoutKey.value === display.value.key && layoutBinding.value === beatBinding.value);
    const pageIndex = ref(0);
    const provisional = ref(false);
    const liveText = ref("");
    // The clear (webclient-scene-transitions, design D4): the page's content
    // is keyed by this counter, which only a NEW response bumps. Mount,
    // resync, a flush, and appended lines patch the content in place, so
    // nothing replays; a new response leaves the previous page behind as a
    // fading, inert layer while the new page mounts and types at once.
    const clearKey = ref(0);

    const currentPage = () => pages.value[pageIndex.value] || null;
    const typingCps = computed(() => effectiveCps(props.motionLevel, props.textSpeed));
    const typewriter = useTypewriter({
      units: () => pageUnits(currentPage()),
      snap: (n) => snapUnits(currentPage(), n),
      cps: () => typingCps.value,
      held: () => props.held,
    });
    const typing = typewriter.typing;

    // The response offset up to which the live region has spoken.
    let announcedEnd = 0;
    let shownKey = null;
    let shownBlocks = null;
    let shownLength = 0;
    let initialized = false;
    // The response on screen when a fonts-not-ready pass first ran before
    // the mount pass; `undefined` when no such pass ran.
    let provisionalKey;
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
      let text = fresh.map(fragmentText).filter(Boolean).join("\n");
      // A scene line names its speaker once, on its first page; narration
      // and later pages carry the text alone.
      if (props.scene && pageIndex.value === 0 && props.scene.speakerName && text) {
        text = `${props.scene.speakerName}：${text}`;
      }
      const pageEnd = page.blocks[page.blocks.length - 1].end;
      announcedEnd = Math.max(announcedEnd, pageEnd);
      announce(text);
    }

    function setPage(index) {
      pageIndex.value = index;
    }

    // The reader's typing position on the page on screen (design D6): the
    // next character to reveal while typing, else the last character shown.
    function readerAnchor() {
      const page = currentPage();
      if (!page) {
        return { offset: 0, complete: true };
      }
      if (typing.value) {
        return { offset: offsetAtUnits(page, typewriter.typed.value), complete: false };
      }
      return { offset: Math.max(0, offsetAtUnits(page, pageUnits(page)) - 1), complete: true };
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

    // D6: the bound round's page list. Each beat is paginated alone (a short
    // beat never shares a page with the next), the response's remaining lines
    // follow as ordinary pages, and every beat page carries the beat it
    // belongs to. Before the fonts are measurable each beat is one page: the
    // provisional presentation stays unpaged, and the queue still steps.
    function measureBeatPages(blocks, bound) {
      const ready = measure.ready.value;
      const fits = ready ? props.pageFit || measure.fits : () => true;
      const texts = Array.isArray(bound.texts) ? bound.texts : [];
      try {
        return beatPages(texts, tailBlocks(blocks, bound.coveredLines), fits);
      } finally {
        if (ready && !props.pageFit) {
          measure.clear();
        }
      }
    }

    // The first page of a bound beat: the layout's own record, clamped so a
    // stale index can never address a page that is not there.
    function firstBeatPage(index) {
      const starts = beatStarts.value;
      if (starts.length === 0) {
        return 0;
      }
      return starts[Math.max(0, Math.min(index, starts.length - 1))];
    }

    function clearBeatPageTimer() {
      if (beatPageTimer !== null) {
        clearTimeout(beatPageTimer);
        beatPageTimer = null;
      }
    }

    // Arm the wait between two pages of the same beat. Re-arming restarts it.
    function armBeatPage(ms, onDue) {
      clearBeatPageTimer();
      beatPageTimer = setTimeout(() => {
        beatPageTimer = null;
        onDue();
      }, ms);
    }

    // Reveal a page the queue picked: announce it, then type it (instantly
    // when nothing can be measured).
    function showBeatPage(index) {
      setPage(index);
      announceCurrentPage({ whole: true });
      typewriter.start(0);
      if (!measure.ready.value) {
        typewriter.complete();
      }
    }

    // The bound round's own re-page (design D6): the beat layout owns the page
    // list, because a beat page's offsets are its own — the ordinary path's
    // response-space anchor cannot address it. A binding that changes under a
    // reader on the same response re-announces the page (the beat pages
    // replaced the response's own lines) and starts the reported-beat record
    // afresh; later appends to the same response keep the page. The queue then
    // repositions itself on the new layout's next tick.
    function repageBeats(shown, bound) {
      const ready = measure.ready.value;
      provisional.value = !ready;
      const layout = measureBeatPages(shown.blocks, bound);
      pages.value = layout.pages;
      beatStarts.value = layout.beatStarts;
      beatTailStart.value = layout.tailStart;
      layoutSeq += 1;
      const bindingChanged = shown.key !== laidOutFor;
      const isNew = shown.key !== shownKey;
      if (bindingChanged) {
        laidOutFor = shown.key;
        reportedBeats = new Set();
        tailMoved = false;
        followedBeat = null;
        followedLayout = -1;
        announcedEnd = 0;
        clearBeatPageTimer();
      }
      shownBlocks = shown.blocks;
      shownKey = shown.key;
      shownLength = responseLength(shown.blocks);
      const last = Math.max(0, layout.pages.length - 1);
      let announce = false;
      if (!initialized) {
        // A mount opens the last page of the last response, fully read.
        initialized = true;
        announcedEnd = shownLength;
        setPage(last);
        typewriter.complete();
        typewriter.disarmAdvance();
      } else if (isNew && !shown.awaiting) {
        clearKey.value += 1;
        announcedEnd = 0;
        setPage(beatPlaying.value ? firstBeatPage(bound.index) : 0);
        announce = true;
        typewriter.start(0);
      } else {
        const held = Math.min(pageIndex.value, last);
        if (held !== pageIndex.value) {
          setPage(held);
          typewriter.start(0);
        } else if (bindingChanged) {
          announce = true;
        }
      }
      if (!ready) {
        typewriter.complete();
      }
      if (announce) {
        announceCurrentPage({ whole: true });
      }
    }

    // A scene line's page list. A new line (or delivery, or the scene's
    // first line) opens on page 1 and types; the clear layer plays only for
    // a new group. The same line re-measured (box, scale, font, a same-
    // delivery refresh) keeps the page holding the reader's position.
    function repageScene(shown) {
      const anchor = readerAnchor();
      const ready = measure.ready.value;
      provisional.value = !ready;
      const length = responseLength(shown.blocks);
      const next = ready
        ? measurePages(shown.blocks)
        : [{ blocks: [{ ...shown.blocks[0], first: true, start: 0, end: length }], oversize: true }];
      pages.value = next;
      shownBlocks = shown.blocks;
      shownLength = length;
      initialized = true;
      if (!shownScene) {
        shownScene = true;
        sceneCoveredKey = narrativeDisplay.value.key;
      }
      if (shown.key !== shownKey) {
        if (shown.group !== shownGroup) {
          clearKey.value += 1;
        }
        shownKey = shown.key;
        shownGroup = shown.group;
        announcedEnd = 0;
        setPage(0);
        announceCurrentPage({ whole: true });
        typewriter.start(0);
        if (!ready) {
          typewriter.complete();
        }
        return;
      }
      const index = Math.min(pageIndexForOffset(next, anchor.offset), Math.max(0, next.length - 1));
      setPage(index);
      typewriter.start(unitsAtOffset(next[index], anchor.complete ? anchor.offset + 1 : anchor.offset));
      if (!ready) {
        typewriter.complete();
      }
    }

    function repage() {
      generation += 1;
      const shown = display.value;
      pagedBlocks.value = shown.blocks;
      if (shown.scene) {
        repageScene(shown);
        return;
      }
      // Leaving a scene: the narrative it covered (its own transcript, or a
      // reconnect's) was already read through the scene, so it settles on
      // its last page; a response that arrived with the retirement types.
      let settle = false;
      if (shownScene) {
        shownScene = false;
        shownGroup = null;
        liveText.value = "";
        settle = shown.key === sceneCoveredKey || props.modeHydrating;
        if (!settle) {
          shownKey = null;
        }
      }
      if (boundBeats.value) {
        repageBeats(shown, boundBeats.value);
        return;
      }
      // Read before the pages are replaced: the anchor is on the old page.
      const anchor = readerAnchor();
      if (!measure.ready.value) {
        // Fonts not ready: the first block, unpaged, scrolling inside.
        provisional.value = true;
        if (!initialized && provisionalKey === undefined) {
          provisionalKey = shown.key;
        }
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
        typewriter.complete();
        return;
      }
      provisional.value = false;
      const next = measurePages(shown.blocks);
      const blocksChanged = shown.blocks !== shownBlocks;
      shownBlocks = shown.blocks;
      pages.value = next;
      if (next.length === 0) {
        pageIndex.value = 0;
        typewriter.complete();
        return;
      }
      const last = next.length - 1;
      const length = responseLength(shown.blocks);
      const shrank = shown.key === shownKey && length < shownLength;
      shownLength = length;
      // A response that arrived while the fonts were loading was never read:
      // the first paging pass opens it on page 1 and types it (design D5),
      // instead of settling it like the mount's retained log.
      const arrivedWhileProvisional =
        !initialized && provisionalKey !== undefined && shown.key !== provisionalKey;
      if (arrivedWhileProvisional && !shown.awaiting && !shrank) {
        initialized = true;
        shownKey = null;
      }
      // A trim of the log's oldest lines can cut into the shown (leading)
      // response and renumber its offsets; the anchor and watermark are then
      // meaningless, so it settles like a mount.
      if (!initialized || shown.awaiting || shrank || settle) {
        // Mount, resync, or the reader acted: the last page, already read.
        // A flush stops typing and shows the page complete.
        initialized = true;
        shownKey = shown.key;
        announcedEnd = length;
        setPage(last);
        typewriter.complete();
        typewriter.disarmAdvance();
        return;
      }
      if (shown.key !== shownKey) {
        // A new response opens on page 1 and types from its start.
        shownKey = shown.key;
        clearKey.value += 1;
        announcedEnd = 0;
        setPage(0);
        announceCurrentPage({ whole: true });
        typewriter.start(0);
        return;
      }
      // Same response: appended lines or a new box / scale / font. The page
      // holding the typing position stays; the text before it shows at once
      // and the rest types (design D6). On a complete page the resume point
      // is just past the last character shown, which also resumes typing
      // into lines appended to that page. Only appended text is announced.
      const index = Math.min(pageIndexForOffset(next, anchor.offset), last);
      setPage(index);
      typewriter.start(unitsAtOffset(next[index], anchor.complete ? anchor.offset + 1 : anchor.offset));
      if (blocksChanged) {
        announceCurrentPage({ whole: false });
      }
    }

    function advance() {
      if (beatPlaying.value) {
        // A playing round: this activation ends it at once and changes no
        // page (design D6).
        emit("beat-skip");
        return true;
      }
      if (provisional.value) {
        return false;
      }
      if (typing.value) {
        // A press while typing shows the page in full.
        typewriter.complete();
        return true;
      }
      if (pageIndex.value >= pages.value.length - 1) {
        // The line's last page, fully shown: the scene's next line or its
        // explicit finish belongs to the line owner.
        if (props.scene && !props.scene.finished) {
          emit("scene-advance");
          return true;
        }
        return false;
      }
      setPage(pageIndex.value + 1);
      announceCurrentPage({ whole: true });
      typewriter.start(0);
      return true;
    }

    // A switch to `instant`, or away from the `full` motion level, completes
    // the typing page; any other speed change applies from the next page.
    watch(typingCps, (cps) => {
      if (cps === Infinity) {
        typewriter.complete();
      }
    });

    // Auto-advance (design D7): armed on a fully shown page with a next page
    // that is neither oversize nor a map; any change re-evaluates it, so the
    // wait counts from the later of "fully shown" and "a next page exists".
    // While a combat round plays by itself the queue paces the pages and this
    // watcher neither arms nor disarms: the queue's own watcher below is the
    // sole owner of the armed wait then (webclient-combat-beat-queue D6).
    watch(
      () => [
        props.autoAdvance && !props.scene,
        beatPlaying.value,
        provisional.value,
        typing.value,
        pageIndex.value,
        pages.value,
        layoutCurrent.value,
      ],
      // An awaiting flush always parks on the last page, so `index` then
      // fails the next-page test and nothing arms.
      ([auto, playing, unpaged, isTyping, index, list, current]) => {
        if (!current) {
          typewriter.disarmAdvance();
          return;
        }
        if (playing) {
          return;
        }
        const page = list[index];
        if (auto && !unpaged && !isTyping && index < list.length - 1 && autoAdvanceAllowed(page)) {
          typewriter.armAdvance(autoAdvanceDelayMs(page), () => advance());
        } else {
          typewriter.disarmAdvance();
        }
      },
      { flush: "post" },
    );

    // The beat queue's pacing (webclient-combat-beat-queue D6). While a round
    // plays, the store's `index` picks the beat: the page follows it, and once
    // it is fully shown the next beat follows after the beat pause. A beat
    // that runs over more than one page waits that same pause between its own
    // pages, and its last page reports `beat-shown` — once per beat. When the
    // round ends, the window moves to the page after the beats, or stays on
    // the last beat page when none follows.
    watch(
      () => [beatSignature.value, typing.value, pageIndex.value, pages.value, layoutCurrent.value],
      () => {
        const bound = boundBeats.value;
        const playing = !!bound && bound.auto && bound.phase !== "done";
        // Every pass re-decides the pause; only the same-beat branch re-arms.
        clearBeatPageTimer();
        if (!layoutCurrent.value) {
          typewriter.disarmAdvance();
          return;
        }
        if (playing && !wasBeatPlaying) {
          // A wait armed before the round bound would end it with no player
          // action; the queue owns the channel from here.
          typewriter.disarmAdvance();
        }
        wasBeatPlaying = playing;
        if (!bound || !bound.auto) {
          return;
        }
        if (bound.phase === "done") {
          if (!tailMoved) {
            tailMoved = true;
            const last = Math.max(0, pages.value.length - 1);
            // With no line after the beats the tail holds no page: stay on
            // the last beat page, fully shown.
            const tail = beatTailStart.value;
            const target = tail >= 0 && tail <= last ? tail : last;
            if (target !== pageIndex.value) {
              showBeatPage(target);
            }
          }
          return;
        }
        // Follow the store's beat, and reposition after a re-page. When the
        // page is already the one this beat starts at, pacing continues in
        // the same pass.
        if (followedLayout !== layoutSeq || followedBeat !== bound.index) {
          followedLayout = layoutSeq;
          followedBeat = bound.index;
          const start = firstBeatPage(bound.index);
          if (start !== pageIndex.value) {
            showBeatPage(start);
            return;
          }
        }
        if (typing.value) {
          return;
        }
        const page = pages.value[pageIndex.value];
        const beat = page && typeof page.beat === "number" ? page.beat : bound.index;
        const next = pages.value[pageIndex.value + 1];
        if (next && typeof next.beat === "number" && next.beat === beat) {
          armBeatPage(readMotionMs("--motion-beat"), () => {
            const current = boundBeats.value;
            // The round may have ended (or been replaced) while the page
            // waited: never advance a page the queue no longer owns.
            if (!current || !current.auto || current.phase === "done") {
              return;
            }
            showBeatPage(pageIndex.value + 1);
          });
          return;
        }
        typewriter.disarmAdvance();
        if (!reportedBeats.has(beat)) {
          reportedBeats.add(beat);
          emit("beat-shown", beat);
        }
      },
      { flush: "post" },
    );

    let fontRequest = 0;
    function requestRepage() {
      const ticket = ++fontRequest;
      if (!layoutCurrent.value) {
        typewriter.disarmAdvance();
        clearBeatPageTimer();
      }
      const commit = () => {
        if (ticket !== fontRequest) return;
        repage();
        if (measure.ready.value) {
          layoutKey.value = display.value.key;
          layoutBinding.value = beatBinding.value;
        }
      };
      if (props.pageFit || !measure.ready.value) {
        commit();
        return;
      }
      const bound = boundBeats.value;
      const blocks = bound
        ? [...beatBlocks(bound.texts), ...tailBlocks(display.value.blocks, bound.coveredLines)]
        : display.value.blocks;
      const prepared = measure.prepareFonts(blocks);
      if (prepared) {
        void prepared.then(commit);
      } else {
        commit();
      }
    }
    onBeforeUnmount(() => {
      fontRequest += 1;
      clearBeatPageTimer();
    });

    // The transcript a scene covers: every narrative response that arrives
    // while a scene line is on screen (registered before the paging watcher,
    // so a retirement in the same flush is judged against the last response
    // seen during the scene).
    watch(
      () => narrativeDisplay.value.key,
      (key) => {
        if (shownScene && props.scene && !props.sceneHold) {
          sceneCoveredKey = key;
        }
      },
      { flush: "post" },
    );

    watch(
      () => [
        display.value.key,
        display.value.blocks,
        display.value.awaiting,
        // A round binding to (or leaving) the response on screen re-pages it
        // (webclient-combat-beat-queue D6).
        beatBinding.value,
        measure.boxKey.value,
        measure.ready.value,
      ],
      () => requestRepage(),
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
            requestRepage();
          }
        });
      },
    );

    onMounted(() => {
      requestRepage();
    });

    // Reading complete (design D3): the current response's last page is on
    // screen and fully shown, with no pending action mark. Pure reader
    // state, never prose. A response with no text has nothing to read.
    const readingComplete = computed(() => {
      // A playing round is not read yet: the shell's dialogue list waits for
      // the playback to end (webclient-combat-beat-queue D6).
      if (props.scene) {
        // An authored scene is read only once its final page received the
        // further, explicit finish activation.
        return props.scene.finished === true;
      }
      if (!measure.ready.value || provisional.value || display.value.awaiting || beatPlaying.value) {
        return false;
      }
      if (pagedBlocks.value !== display.value.blocks || typing.value) {
        return false;
      }
      const total = pages.value.length;
      return total === 0 || pageIndex.value === total - 1;
    });
    watch(readingComplete, (complete) => emit("reading-change", complete), { immediate: true });

    // ---- reading controls (design D4) ----

    function selectionInside() {
      const selection = typeof window.getSelection === "function" ? window.getSelection() : null;
      if (!selection || selection.isCollapsed || !selection.anchorNode) {
        return false;
      }
      return !!rootRef.value && rootRef.value.contains(selection.anchorNode);
    }

    function onClick(event) {
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
      if (!(event.deltaY < 0)) {
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

    function focus() {
      surfaceRef.value?.focus({ preventScroll: true });
    }

    // Dialogue mode's focus home while no choice list is shown
    // (webclient-dialogue-choices-overlay D7): the page surface.
    function focusHome() {
      surfaceRef.value?.focus({ preventScroll: true });
    }

    expose({ focus, focusHome, advance });

    return () => {
      const page = pages.value[pageIndex.value] || null;
      const total = pages.value.length;
      const onLastPage = pageIndex.value >= total - 1;
      const scene = props.scene;
      // A scene's ■ belongs to the final line's last page; every earlier
      // line's last page still promises more (▼).
      const onLast = onLastPage && (!scene || scene.last);
      // The final page before its explicit finish activation.
      const awaitingFinish = !!scene && onLast && !scene.finished;
      const isTyping = typing.value;
      // The queue paces a playing round, so it shows no marker of its own
      // (webclient-combat-beat-queue D6).
      const showMarker = !provisional.value && total > 0 && !isTyping && !beatPlaying.value;
      const reveals = isTyping && page ? fragmentReveal(page, typewriter.typed.value) : null;
      return h(
        "section",
        {
          ref: rootRef,
          class: "message-window",
          "data-testid": "message-window",
          "data-mode": props.mode,
          "data-variant": "paged",
          "data-reading-complete": readingComplete.value ? "true" : "false",
          "data-typing": isTyping ? "true" : "false",
          "data-scene": scene ? "true" : null,
          "data-scene-speaker": scene ? scene.speaker || "narration" : null,
          onClick,
          onWheel,
        },
        [
          // The name plate (webclient-dialogue-stage-actors D7): a header row
          // above the text area while the dialogue panel is available. It
          // fades in and out on a live mode change (webclient-mode-
          // transitions D4); the Transition stays in the tree either way, so
          // the text area below keeps its vnode position.
          h(
            Transition,
            {
              name: "plate",
              // Between the lines of a scene the plate swaps in the commit's
              // frame: a fading name must never outlive its line.
              css: props.motionLevel !== "off" && !props.modeHydrating && !scene,
              ...inertWhileLeaving,
            },
            () => {
              if (!plated.value) {
                return null;
              }
              if (scene && !plateName.value) {
                // Narration: no speaker plate, but the row keeps its box so
                // the page below never re-measures between lines.
                return h(
                  "div",
                  {
                    class: "message-window__plate message-window__plate--spacer",
                    "data-testid": "message-plate-spacer",
                    "aria-hidden": "true",
                  },
                  [h("span", { class: "message-window__plate-line" }, [h("span", { class: "message-window__plate-name" }, "\u00a0")])],
                );
              }
              return h(
                "div",
                {
                  class: "message-window__plate",
                  "data-testid": "message-name-plate",
                  "data-speaker": scene ? scene.speaker : null,
                },
                [
                  // The underline runs under this line only, from the
                  // name's own left edge (webclient-message-typesetting).
                  h("span", { class: "message-window__plate-line" }, [
                    h("span", { class: "message-window__plate-name" }, plateName.value),
                    plateBond.value == null
                      ? null
                      : h(
                          "span",
                          { class: "message-window__plate-bond", "data-testid": "dialogue-bond" },
                          ` ‧ 羈絆 ${plateBond.value}`,
                        ),
                  ]),
                ],
              );
            },
          ),
          // The measurer is an untracked DOM node appended after the page
          // surface by use-message-measure.js and must stay the text area's
          // last child, so never add a sibling slot or key a fragment here
          // without moving the measurer into the vnode tree.
          h("div", { class: "message-window__text" }, [
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
              [
                h(
                  Transition,
                  {
                    name: "message-clear",
                    // At `off` the previous page goes in the commit's frame
                    // (a CSS phase would linger a double frame even at 0s).
                    css: props.motionLevel !== "off",
                    ...inertWhileLeaving,
                  },
                  () =>
                    h(
                      "div",
                      { key: clearKey.value, class: "message-window__content", "data-testid": "message-content" },
                      page
                        ? page.blocks.map((fragment, index) =>
                            narrativeBlockNodes(fragment, `f${index}`, reveals ? reveals[index] : undefined),
                          )
                        : [],
                    ),
                ),
              ],
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
                    "data-await-finish": awaitingFinish ? "true" : null,
                    "aria-hidden": "true",
                  },
                  onLast ? "■" : "▼",
                )
              : null,
          ]),
          h(
            "span",
            { id: pageLabelId, class: "message-window__sr" },
            total === 0
              ? ""
              : scene
                ? `第 ${scene.lineIndex + 1}／${scene.lineCount} 句，第 ${pageIndex.value + 1}／${total} 頁`
                : `第 ${pageIndex.value + 1}／${total} 頁`,
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
   card of its own: only a gold reading rule at its left edge while the page
   surface holds keyboard focus. Every selector is prefixed
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
  /* The clear layer's opaque fill (webclient-scene-transitions D4): the
     band's own gradient (HudFrame's `.stage-band`) as it falls behind the
     text area, so the fading page never reads as a card. */
  --message-clear-fill: linear-gradient(180deg, #0e0f15 0%, #13101a 32%, #110e17 64%, #0e0b12 100%);
  /* The page's type size and the prose column's outer width
     (webclient-message-typesetting). The page's max-width and the marker's
     placement both read these, so the marker always tracks the measure. */
  --message-page-font: calc(var(--message-text) * var(--prose-scale));
  --message-measure: calc(var(--message-page-font) * 42 + 48px * var(--ui-scale));
}

.message-window::before {
  content: "";
  position: absolute;
  left: 0;
  top: calc(12px * var(--ui-scale));
  bottom: calc(var(--message-controls-h) + 4px * var(--ui-scale));
  width: 2px;
  background: linear-gradient(180deg, transparent, var(--gold-400) 18%, var(--gold-400) 82%, transparent);
  opacity: 0;
  transition: opacity var(--motion-fast) var(--ease-standard);
  pointer-events: none;
}

/* The reading rule (webclient-message-typesetting) shows only while the
   page surface holds keyboard focus; at rest the text sits straight on the
   band's ink with no line of the window's own. */
.message-window:has(.message-window__page:focus-visible)::before {
  opacity: 1;
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
  max-width: var(--message-measure);
  height: 100%;
  margin: 0 auto;
  padding: 0 calc(24px * var(--ui-scale));
  overflow: hidden;
  /* The page text's face (retarget-desktop-viewport-contract D5): the bundled
     Jim Mono TC reading face, whose CJK is exactly two cells wide — what the
     42-cell measure below was always counting in. */
  font-family: var(--f-mono);
  font-size: var(--message-page-font);
  line-height: var(--message-line-height);
  color: var(--paper-100);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.55);
  outline: none;
  /* CJK prose spacing (webclient-message-typesetting), progressive: a
     browser without a property keeps its default spacing. A small gap
     between CJK and Latin letters or digits, trimmed opening brackets at a
     line start, strict line-break rules for small kana and iteration marks.
     Spacing only — the narrative text is never rewritten, no `halt` is set,
     and the hidden measurer carries this class too, so paging measures the
     spacing it shows. Maps opt out below. */
  text-autospace: normal;
  text-spacing-trim: trim-start;
  line-break: strict;
}

.message-window__page:focus-visible {
  box-shadow: none;
}

/* The clear (webclient-scene-transitions, design D4). The page surface is
   the positioning box of the leaving layer; the layer keeps the page's own
   padding, so its text stays exactly where it was read. */
.message-window__page {
  position: relative;
}

.message-window .message-clear-leave-active {
  position: absolute;
  inset: 0;
  z-index: 1;
  padding: inherit;
  pointer-events: none;
  background: var(--message-clear-fill);
  /* Feathered side edges, inside the page's text-free side padding. */
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 calc(16px * var(--ui-scale)), #000 calc(100% - 16px * var(--ui-scale)), transparent);
  mask-image: linear-gradient(90deg, transparent, #000 calc(16px * var(--ui-scale)), #000 calc(100% - 16px * var(--ui-scale)), transparent);
  transition: opacity var(--motion-clear) var(--ease-standard);
}

.message-window .message-clear-leave-to {
  opacity: 0;
}

/* The two pages hand over rather than overlap: the previous page drops
   away on a fast-falling curve, and the new page — already mounted and
   typing — surfaces beneath it only in the clear's last stretch, when the
   old text is nearly gone. (At the reduced level the page is typed at once,
   so this is what keeps two whole pages from showing through each other.) */
.message-window .message-clear-enter-active {
  transition: opacity calc(var(--motion-clear) * 0.6) var(--ease-standard) calc(var(--motion-clear) * 0.4);
}

.message-window .message-clear-enter-from {
  opacity: 0;
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
  margin-top: var(--message-paragraph-gap);
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
  /* An absolute reference token, not an `em` fraction
     (retarget-desktop-viewport-contract D6): at the page's 16px floor a
     `0.75em` aside would render at 12px, below the legibility floor, so the
     aside reads at `--text-sm` (17px at the reference) whatever the reader's
     prose scale. */
  font-size: var(--text-sm);
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

/* The typewriter reveal (webclient-typewriter-reading-prefs design D1): the
   unrevealed tail keeps its place invisibly, so nothing re-wraps while a
   page types. A `sys` line's ◈ marker is a ::before, so it stays hidden
   with its unrevealed line. */
.message-window .narrative-unrevealed,
.message-window .narrative-line.unrevealed {
  visibility: hidden;
}

/* Box-drawing maps: atomic mono blocks with a tight leading so vertical
   strokes join. */
.message-window .narrative-line.map-art {
  font-family: var(--f-mono);
  /* The same floor rule as `.sys`: the box-drawing art path is an absolute
     token, `--text-xs` (16px at the reference), never a sub-em fraction
     (retarget-desktop-viewport-contract D6). */
  font-size: var(--text-xs);
  line-height: 1.15;
  white-space: pre;
  color: var(--paper-300);
  text-shadow: none;
  /* A map is a grid: no inserted spacing, trimming, or rule-based breaks. */
  text-autospace: no-autospace;
  text-spacing-trim: space-all;
  line-break: auto;
}

/* The control strip: the marker ends at the prose column's right edge
   (webclient-message-typesetting) — the centred column in exploration and
   combat, the left-aligned column in dialogue — and never closer to the
   region's right edge than the 日誌 / ⌨ controls the shell places there. */
.message-window__controls {
  position: relative;
  flex: none;
  height: var(--message-controls-h);
}

.message-window__marker {
  position: absolute;
  right: max(
    var(--band-strip-actions-w),
    calc((100% - min(100%, var(--message-measure))) / 2 + 24px * var(--ui-scale))
  );
  bottom: calc(12px * var(--ui-scale));
  font-size: var(--text-md);
  line-height: 1;
  color: var(--gold-400);
  text-shadow: 0 0 calc(8px * var(--ui-scale)) var(--gold-glow);
  pointer-events: none;
}

.message-window__marker[data-state="more"] {
  animation: message-window-marker-bob var(--motion-marker-bob) var(--ease-standard) infinite;
}

.message-window__marker[data-state="end"] {
  font-size: var(--text-xs);
  bottom: calc(14px * var(--ui-scale));
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
    transform: translateY(calc(var(--motion-marker-travel) * var(--motion-travel)));
    opacity: 0.55;
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

/* Dialogue (webclient-dialogue-stage-actors D7; webclient-dialogue-choices-
   overlay D1): the window spans the whole band. The name plate heads it and
   the page below it keeps the 42em measure, but in one left-aligned column
   whose left edge lines up with the player portrait's anchor, so the line
   reads down from the figure standing above it and the right part of the
   band stays open under the host. The measurer shares the page's classes,
   so it measures the same column. */
/* The player portrait's left inset, less the band region's 18px left
   padding: the text column starts under the figure's anchor edge. Declared
   in every mode, so a name plate leaving after the commit back to
   exploration keeps its geometry while it fades. */
.message-window {
  --dialogue-inset: max(24px * var(--ui-scale), calc(var(--actor-left-inset, 6vw) - 18px * var(--ui-scale)));
}

.message-window[data-mode="dialogue"] .message-window__page {
  max-width: var(--message-measure);
  margin: 0;
  padding-left: var(--dialogue-inset);
}

.message-window[data-mode="dialogue"] {
  --message-measure: calc(var(--message-page-font) * 42 + var(--dialogue-inset) + 24px * var(--ui-scale));
}

.message-window[data-mode="dialogue"] .message-window__marker {
  right: max(var(--band-strip-actions-w), calc(100% - min(100%, var(--message-measure)) + 24px * var(--ui-scale)));
}

/* The focus rule follows the column: just left of the text, below the
   plate. */
.message-window[data-mode="dialogue"]::before {
  left: calc(var(--dialogue-inset) - 14px * var(--ui-scale));
  top: calc(var(--message-text) * 2);
}

.message-window__plate {
  flex: none;
  display: flex;
  align-items: baseline;
  min-width: 0;
  box-sizing: border-box;
  max-width: var(--message-measure);
  margin: calc(4px * var(--ui-scale)) 0 calc(6px * var(--ui-scale));
  padding: 2px calc(24px * var(--ui-scale)) calc(3px * var(--ui-scale)) var(--dialogue-inset);
  font-size: var(--message-page-font);
  white-space: nowrap;
  overflow: hidden;
}

/* In exploration the plate names the person in focus (exploration-presence-
   rail) above the centred reading column, so it takes the page's own
   geometry: the same centred measure and side padding, its name starting
   where the text starts. */
.message-window[data-mode="exploration"] .message-window__plate {
  width: 100%;
  margin-left: auto;
  margin-right: auto;
  padding-left: calc(24px * var(--ui-scale));
}

/* The name's underline (webclient-message-typesetting): it starts exactly
   at the name's left edge, where the text column starts, holds gold under
   the name, and fades out a little past the bond stage, so the rule belongs
   to the name rather than to the window. A small lozenge seats its start. */
.message-window__plate-line {
  position: relative;
  display: flex;
  align-items: baseline;
  min-width: 0;
  padding: 0 2.4em calc(7px * var(--ui-scale)) 0;
  background:
    linear-gradient(90deg, var(--gold-400), var(--gold-500) 45%, rgba(185, 154, 96, 0.3) 78%, transparent)
    left bottom / 100% 1px no-repeat;
}

.message-window__plate-line::before {
  content: "";
  position: absolute;
  left: 0;
  bottom: -2px;
  width: calc(5px * var(--ui-scale));
  height: calc(5px * var(--ui-scale));
  transform: rotate(45deg);
  background: var(--gold-400);
  box-shadow: 0 0 calc(6px * var(--ui-scale)) var(--gold-glow);
}

/* The plate's entrance (webclient-mode-transitions D4): it takes its row at
   the commit, so the page re-measures once, and its content fades in a beat
   after the host starts to walk on, drifting the last few pixels in from
   the text column's side. Leaving, it is lifted out of flow onto the
   window's top edge (the text below takes its row at once) and drops away
   on a fast-falling curve, gone before the new page surfaces under it. */
.message-window .plate-enter-active {
  transition:
    opacity var(--motion-reveal) var(--ease-standard) calc(var(--motion-panel) * 0.4 * var(--motion-travel)),
    transform var(--motion-reveal) var(--ease-enter) calc(var(--motion-panel) * 0.4 * var(--motion-travel));
}
.message-window .plate-enter-from {
  opacity: 0;
  transform: translateX(calc(-1 * var(--motion-shift-sm) * var(--motion-travel)));
}
.message-window .plate-leave-active {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  pointer-events: none;
  transition: opacity calc(var(--motion-reveal) * 0.4) var(--ease-standard);
}
.message-window .plate-leave-to {
  opacity: 0;
}

/* `text-overflow` does not apply to the flex row itself, so the name
   truncates inside its own box and the bond segment always stays readable. */
.message-window__plate-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--gold-300);
  font-family: var(--f-display);
  /* An absolute floor token, not a fraction of the plate line
     (retarget-desktop-viewport-contract D6): at 0.86em of the 18px base the
     name rendered at 15.48px, below the 16px reference floor. */
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  text-shadow: 0 0 calc(14px * var(--ui-scale)) var(--gold-glow), 0 1px 2px rgba(0, 0, 0, 0.7);
}

/* Authored scenes (authored-dialogue-playback). Narration keeps the plate
   row's box with nothing in it, so the page never moves between speakers. */
.message-window__plate--spacer {
  visibility: hidden;
}

/* The acting body's plate seats its underline on an open lozenge, the
   host's on the filled one: a shape cue for the side that speaks, beside
   the name itself and the stage emphasis. */
.message-window__plate[data-speaker="actor"] .message-window__plate-line::before {
  background: transparent;
  box-shadow: inset 0 0 0 1px var(--gold-400), 0 0 calc(6px * var(--ui-scale)) var(--gold-glow);
}

/* Narration reads as the scene's own voice: the quieter paper tone and a
   touch more tracking, the same face and size as speech. */
.message-window .narrative-line.narration {
  color: var(--paper-300);
  letter-spacing: 0.04em;
}

/* The final page waiting for its finish activation breathes on the motion
   tokens (still at `reduced` / `off`, where the duration is 0); after the
   finish the ■ is at rest. */
.message-window__marker[data-await-finish="true"] {
  animation: message-window-marker-breathe var(--motion-marker-bob) var(--ease-standard) infinite;
}

@keyframes message-window-marker-breathe {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.45;
  }
}

.message-window__plate-bond {
  flex: none;
  white-space: pre;
  color: var(--paper-500);
  font-family: var(--f-sans);
  font-size: max(var(--text-xs), 0.46em);
  /* The sans suffix sits inside the name's line box, so a host plate is
     exactly as tall as the acting body's plate and the narration spacer:
     the page below never re-measures between speakers. */
  line-height: 1;
  letter-spacing: 0.12em;
}
</style>
