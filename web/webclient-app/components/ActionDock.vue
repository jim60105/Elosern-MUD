<script setup>
// ActionDock (H3 webclient-hud-03-action-dock, task 4.1/4.8): the
// non-closable action surface: the content column inside the bottom band's
// command region (HudFrame `data-anchor="band-command"`, the band's right
// third; webclient-avg-stage-shell). The band chrome (the draft's upward
// gradient, the `--line` top border, the upward shadow) is owned by the
// band element itself (`.stage-band`); this container keeps only
// `max-width:1180px` centering and the fixed-chrome / scrolling-body layout
// (the draft's `.dock`). The preserved `#action-dock` element keeps its
// `tabindex`, `data-mode`, and its role as the surface's documented focus
// target. The row container carrying `data-testid="dock-menu"` is always in
// the pane: the combat root renders there as a vertical command list
// (webclient-combat-command-window), and a deeper frame replaces it.
//
// The chrome is, top to bottom: the optional guidance line, the breadcrumb,
// the scrolling body, and the shortcut-legend strip. The legend is the
// single element carrying the `action-dock-description` hook; the
// exploration panel carries none (exploration-exit-compass: its keys live in
// the help overlay, and the compass needs the height).
//
// While a combat round plays by itself and locks the commands (`playback`),
// the body carries a waiting cue over its top edge: a label, the existing
// skip (the same `store.skipBeats` a click on the message window runs), and a
// decorative sweep that states no progress and stands still at reduced/off.
//
// The body is `position: relative`, so an `overlay` child positioned
// `absolute; inset: 0` covers exactly the visible pane box (the retired
// verb popover used it; a person's verbs are now the stage's verb card,
// exploration-presence-rail).
//
// The exploration root holds no row of its own (exploration-room-actions):
// its pane is the exit compass, the 建議 pill, and the readout, each its own
// tab stop, so the container leaves the tab order there (`tabStop` false)
// while staying the programmatic focus target. The `context_actions.
// suggestions` envelope is the centred suggestions card's, opened by the
// pill; the dock renders no suggestions element.
//
// The combat card (webclient-combat-command-card-centred D5, `card`): in
// combat HudFrame moves this same element into the stage's `choices` anchor,
// and the dock presents as the narrow centred card — the shared ChoiceCard
// frame (gold-edged ink panel, crest, corner brackets), a one-line
// breadcrumb, the row region, the detail strip below it (its frames read the
// provided `"strip"` variant), and the shortcut legend wrapping at its
// separators. The playback cue still veils the body inside the card.
//
// The stage target step (webclient-combat-stage-target-picking D3,
// `stageTarget`): while the current frame's targets are picked on the stage
// figures, the card collapses to a target prompt — the action with 選擇目標
// and `Esc 返回`, the focused position's summary, and (AREA) one chip per
// group and the confirm chip. The row region stays mounted but `hidden`, so
// the router's state and the rows' focus bookkeeping are unchanged; DOM focus
// that was inside it moves to `#action-dock`. A polite live region inside the
// card, mounted in every card state, announces the focused target.
import { computed, nextTick, provide, ref, watch } from "vue";
import DockBreadcrumb from "./DockBreadcrumb.vue";
import { DOCK_DETAIL_VARIANT } from "./dock-panes.js";
// The card frame's rules are ChoiceCard's global (unscoped) styles; importing
// the component registers them wherever the dock renders, Storybook included.
import "./ChoiceCard.vue";

const props = defineProps({
  // The contextual dock mode slice (exploration/combat/...), rendered as the
  // preserved `#action-dock` data-mode attribute.
  mode: { type: String, default: "exploration" },
  // The root frame's items; the chrome renders only while a root exists.
  rootItems: { type: Array, default: () => [] },
  // The committed view slice: the crumb reads `dockTrail`/`dockDepth`
  // (task 3.1/3.2).
  view: { type: Object, default: null },
  // The per-surface guidance prefix (legacy dock chrome), shown beside the
  // crumb trail.
  guidancePrefix: { type: String, default: null },
  // True while a combat round plays by itself and locks the commands
  // (`store.view.dispatch.beatLocked`, webclient-combat-beat-queue D5).
  playback: { type: Boolean, default: false },
  // Whether the container itself is a tab stop (false at the exploration
  // root, whose zones are the tab stops).
  tabStop: { type: Boolean, default: true },
  // The narrow combat command card presentation (design D5): AppClient
  // passes `store.view.mode === 'combat'`.
  card: { type: Boolean, default: false },
  // The stage target step (`store.view.stageTarget`), or null.
  stageTarget: { type: Object, default: null },
});

const SIDE_LABELS = { foes: "敵方", party: "我方" };
const dockRef = ref(null);
const step = computed(() => (props.card ? props.stageTarget : null));
// The focused position's summary (line 2 of the prompt), as parts so the
// side and the state read as small tags beside the name.
const summary = computed(() => {
  const s = step.value;
  const p = s && s.focused;
  if (!p) return { name: "以方向鍵選擇目標", tags: [] };
  if (p.kind === "self") return { name: "自己", tags: [{ text: "我方", tone: "party" }] };
  if (p.kind === "member") {
    const tags = [{ text: SIDE_LABELS[p.side], tone: p.side }];
    if (p.offStage) tags.push({ text: "場外", tone: "muted" });
    if (s.selectedIds.includes(p.identities[0])) tags.push({ text: "已選", tone: "chosen" });
    return { name: p.label, tags };
  }
  if (p.kind === "group") return { name: p.label, tags: [{ text: `共 ${p.identities.length} 名`, tone: p.side || "muted" }] };
  if (s.selectedIds.length > 0) return { name: "施展", tags: [{ text: `已選 ${s.selectedIds.length} 名`, tone: "chosen" }] };
  if (s.shorthand) {
    const group = s.positions.find((q) => q.kind === "group" && q.key === `shorthand-${s.shorthand}`);
    return { name: "施展", tags: [{ text: `${group ? group.label : s.shorthand}，共 ${s.choiceCount} 名`, tone: "chosen" }] };
  }
  return { name: "施展", tags: [{ text: "尚未選擇目標", tone: "muted" }] };
});
// The AREA chips: one per group position, then the confirm chip.
const chips = computed(() => {
  const s = step.value;
  if (!s || s.form !== "area") return [];
  return s.positions
    .filter((p) => p.kind === "group" || p.kind === "confirm")
    .map((p) => ({
      key: p.key,
      kind: p.kind,
      label: p.kind === "confirm" ? `施展（${s.choiceCount}）` : p.label,
      focused: s.focusKey === p.key,
      chosen: p.kind === "group" ? s.shorthand === p.key.slice("shorthand-".length) : false,
      empty: p.kind === "confirm" && s.choiceCount === 0,
    }));
});
// The live region's text: only the focus and the selection change it.
const announce = computed(() => (step.value ? step.value.announce : ""));

function onChip(key) {
  emit("target-pointer", key, "activate");
  // A chip never keeps DOM focus: `bridge.js` leaves Enter on a focused
  // button to the button, so the next Enter must reach the router.
  dockRef.value?.focus({ preventScroll: true });
}

// Entering the step hides the row region; DOM focus inside it would fall to
// the document body, so it moves to the card itself.
watch(
  () => !!step.value,
  async (active) => {
    if (!active || !dockRef.value) return;
    const focused = typeof document === "undefined" ? null : document.activeElement;
    if (focused && focused !== dockRef.value && dockRef.value.contains(focused)) {
      dockRef.value.focus({ preventScroll: true });
    }
    await nextTick();
    const after = typeof document === "undefined" ? null : document.activeElement;
    if (after === document.body && focused && dockRef.value && dockRef.value.contains(focused)) {
      dockRef.value.focus({ preventScroll: true });
    }
  },
);

provide(
  DOCK_DETAIL_VARIANT,
  computed(() => (props.card ? "strip" : "pane")),
);

const emit = defineEmits(["action", "back", "skip", "target-pointer"]);

// Creation mode renders the panel with no bar and no crumb (task 4.8):
// exactly one `#action-dock` persists across every mode change. Every other
// mode keeps the crumb, even over the exploration root, whose router menu is
// empty (exploration-room-actions): a pushed child frame there (the
// SkillBook casting flow) still names its trail.
const showChrome = computed(() => props.mode !== "creation");
const trail = computed(() => (props.view && props.view.dockTrail) || []);
const depth = computed(() => (props.view && props.view.dockDepth) || 1);
// Every submenu frame keeps the breadcrumb; a person's verbs are the stage's
// verb card (exploration-presence-rail), never a dock frame.
const showCrumb = computed(() => showChrome.value && !step.value);


function onBack() {
  // The crumb's back chevron pops exactly one router level (task 4.6/8.6).
  emit("back");
}

function onPaneActivate(payload) {
  // The pane's (DockMenu) `activate` intent routes through the single
  // dispatch entry (the store is the sole writer).
  const intent = payload && payload.intent;
  if (intent) {
    emit("action", intent);
  }
}

</script>

<template>
  <section
    id="action-dock"
    ref="dockRef"
    class="action-dock"
    :class="{ 'action-dock--card choice-card choice-card--still': card, 'action-dock--target': !!step }"
    :data-target-step="step ? step.form : null"
    :tabindex="tabStop ? 0 : -1"
    :data-mode="mode"
    data-testid="action-dock"
  >
    <!-- The card frame's corner brackets (decorative; the crest is the
         frame's own pseudo-elements). -->
    <span v-if="card" class="choice-card__corners" aria-hidden="true"></span>
    <!-- The per-surface guidance line (the B2 Node-contract hook
         `action-dock-guidance`), rendered from the committed `guidancePrefix`. -->
    <div v-if="guidancePrefix" class="action-dock__guidance" data-testid="action-dock-guidance">
      {{ guidancePrefix }}
    </div>
    <DockBreadcrumb
      v-if="showCrumb"
      :trail="trail"
      :depth="depth"
      :guidance-prefix="guidancePrefix"
      @back="onBack"
    />
    <!-- The body: the scrolling pane plus the overlay layer. The pane holds
         the active menu frame (the exploration root pane, a combat or
         skill-use frame, or a confirm frame); the named `overlay` slot renders after
         it and covers exactly the pane's visible box. -->
    <!-- The target prompt (stage target step, design D3). -->
    <div v-if="step" class="target-prompt" data-testid="target-prompt" :data-form="step.form">
      <p class="target-prompt__head">
        <span class="target-prompt__action" data-testid="target-prompt-action">
          <span class="target-prompt__skill">{{ step.label }}</span>
          <span v-if="step.scaleLabel" class="target-prompt__scale">{{ step.scaleLabel }}</span>
          <span class="target-prompt__verb">‧ 選擇目標</span>
        </span>
        <span class="target-prompt__esc"><kbd>Esc</kbd> 返回</span>
      </p>
      <p class="target-prompt__focus" data-testid="target-prompt-focus">
        <span class="target-prompt__glyph" aria-hidden="true">▸</span>
        <span class="target-prompt__name">{{ summary.name }}</span>
        <span
          v-for="tag in summary.tags"
          :key="tag.text"
          class="target-prompt__tag"
          :data-tone="tag.tone"
        >{{ tag.text }}</span>
      </p>
      <div v-if="chips.length" class="target-prompt__chips" data-testid="target-prompt-chips">
        <button
          v-for="chip in chips"
          :key="chip.key"
          type="button"
          tabindex="-1"
          class="target-prompt__chip"
          data-testid="target-prompt-chip"
          :data-key="chip.key"
          :data-kind="chip.kind"
          :data-focused="chip.focused ? 'true' : null"
          :data-chosen="chip.chosen ? 'true' : null"
          :data-empty="chip.empty ? 'true' : null"
          @mousedown.prevent
          @click="onChip(chip.key)"
        >{{ chip.label }}</button>
      </div>
    </div>
    <!-- The step's live region: mounted in every card state so the first
         focus is announced; it changes only with the focus or the selection. -->
    <p v-if="card" class="action-dock__announce" role="status" aria-live="polite" data-testid="target-announce">{{ announce }}</p>
    <div class="action-dock__body" :class="{ 'action-dock__body--playback': playback }" :hidden="!!step || null">
      <!-- The waiting cue (webclient-combat-command-window): it veils the
           body, so the rows never move when playback starts or ends. The button is a real control, so its own Enter / Space never
           reach the dock's key routing. -->
      <div v-if="playback" class="action-dock__playback" data-testid="action-dock-playback">
        <!-- Only the words are the live region; the button stays outside it,
             so the mount announces the wait, not the control's label. -->
        <span class="action-dock__playback-label" role="status">回合演出中</span>
        <span class="action-dock__playback-hint">點擊訊息視窗亦可跳過</span>
        <button
          type="button"
          class="action-dock__playback-skip"
          data-testid="action-dock-playback-skip"
          @keydown.enter.stop
          @keydown.space.stop
          @click="emit('skip')"
        >跳過演出</button>
        <span class="action-dock__playback-line" aria-hidden="true"></span>
      </div>
      <div class="action-dock__pane">
        <slot />
      </div>
      <slot name="overlay" />
    </div>
    <!-- The shortcut legend (webclient-align-01-dock-chrome, re-homed by
         webclient-scene-overview-swap D3 and widened by
         webclient-retire-exploration-submenus): the draft's `.dock .hint`
         markup — `數字鍵 1–9 ‧ <kbd>Enter</kbd> 執行 ‧ <kbd>Esc</kbd> 返回`
         with styled `<kbd>` elements. It is the single visible legend and the
         only element carrying the `action-dock-description` hook; it renders
         in dialogue and combat mode (never in creation mode, and never in
         exploration, whose bindings the help overlay lists:
         exploration-exit-compass). -->
    <p
      v-if="mode !== 'creation' && mode !== 'exploration' && !step"
      class="action-dock__legend"
      data-testid="action-dock-description"
    >
      <!-- Three unbreakable segments: in the narrow card the legend wraps
           only at the space after a separator; the text is unchanged. -->
      <span class="action-dock__legend-text"><span class="action-dock__legend-seg">數字鍵 1–9 ‧</span> <span class="action-dock__legend-seg"><kbd>Enter</kbd> 執行 ‧</span> <span class="action-dock__legend-seg"><kbd>Esc</kbd> 返回</span></span>
    </p>

  </section>
</template>

<style scoped>
/* The visually hidden live region (the card's step announcement). */
.action-dock__announce {
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

/* The content column (the draft's `.dock`): centred, bounded width, and the
   vertical layout only. The band chrome (gradient, top border, shadow) lives
   on HudFrame's `.stage-band`, which spans the whole stage; this column
   fills the band's command region and paints nothing. */
.action-dock {
  position: relative;
  max-width: calc(1180px * var(--ui-scale));
  margin: 0 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  font-family: var(--f-sans);
}

/* The container's focus (webclient-band-material-pass): the dock keeps DOM
   focus while the router moves a row's focused state, so the strong
   treatment belongs to that row. The container itself carries a quiet but
   clearly visible mark — a thin gold frame with brighter corner brackets —
   drawn by a pseudo layer so the base rule paints nothing. */
.action-dock:focus,
.action-dock:focus-visible {
  outline: none;
}
/* The card keeps its frame's drop shadow under focus. */
.action-dock:not(.action-dock--card):focus,
.action-dock:not(.action-dock--card):focus-visible {
  box-shadow: none;
}

/* Its right edge sits on the column's own edge: an outset there would count
   as horizontal overflow of the dock (webclient-combat-command-window). The
   card presentation has no such mark: its `::after` is the frame's crest. */
.action-dock:not(.action-dock--card)::after {
  content: "";
  position: absolute;
  inset: calc(-4px * var(--ui-scale)) 0 calc(-4px * var(--ui-scale)) -2px;
  border-radius: var(--radius-sm);
  pointer-events: none;
  opacity: 0;
  border: 1px solid var(--dock-focus-rule);
  background:
    linear-gradient(var(--gold-400), var(--gold-400)) top left / calc(12px * var(--ui-scale)) 2px no-repeat,
    linear-gradient(var(--gold-400), var(--gold-400)) top left / 2px calc(12px * var(--ui-scale)) no-repeat,
    linear-gradient(var(--gold-400), var(--gold-400)) bottom right / calc(12px * var(--ui-scale)) 2px no-repeat,
    linear-gradient(var(--gold-400), var(--gold-400)) bottom right / 2px calc(12px * var(--ui-scale)) no-repeat;
  transition: opacity var(--motion-fast) var(--ease-standard);
}

/* A pointer focus keeps a fainter mark, so the container never loses its
   indication when no row carries the focused state. */
.action-dock:not(.action-dock--card):focus::after {
  opacity: 0.45;
}

.action-dock:not(.action-dock--card):focus-visible::after {
  opacity: 1;
}

/* The body (task 4.1): the dock's one remaining region, holding the scrolling
   pane and the overlay layer. It is the flex child that takes the column's
   remaining height; the overlay child is positioned against it, so it covers
   exactly the pane's visible box whatever the pane's scroll position. */
.action-dock__body {
  position: relative;
  flex: 1;
  min-height: 0;
}

/* The waiting cue: a veil over the whole body while a round plays, so the
   rows never move and the wait reads at once. The decorative sweep is a
   gold hairline whose highlight travels on `--motion-playback-sweep`; at
   reduced and off that token is 0ms, so the line stands still and never
   implies progress. */
.action-dock__playback {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  grid-template-columns: auto auto;
  grid-template-rows: auto auto auto;
  align-content: center;
  justify-content: center;
  align-items: center;
  column-gap: calc(16px * var(--ui-scale));
  row-gap: calc(10px * var(--ui-scale));
  background: radial-gradient(70% 90% at 50% 50%, rgba(10, 11, 14, 0.9), rgba(10, 11, 14, 0.62));
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
}
.action-dock__playback-label {
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  letter-spacing: 0.24em;
  color: var(--gold-400);
}
.action-dock__playback-hint {
  grid-column: 1 / -1;
  grid-row: 3;
  justify-self: center;
  font-size: var(--text-xs);
  color: var(--paper-500);
}
.action-dock__playback-skip {
  padding: calc(5px * var(--ui-scale)) calc(14px * var(--ui-scale));
  background: var(--gold-glow);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  color: var(--gold-400);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  letter-spacing: 0.06em;
  cursor: pointer;
}
.action-dock__playback-skip:hover {
  color: var(--paper-50);
  border-color: var(--gold-400);
}
.action-dock__playback-skip:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}
.action-dock__playback-line {
  grid-column: 1 / -1;
  grid-row: 2;
  justify-self: stretch;
  height: 1px;
  background:
    linear-gradient(90deg, transparent, var(--gold-400), transparent) 0 0 / 35% 100% no-repeat,
    linear-gradient(90deg, transparent, rgba(185, 154, 96, 0.45), transparent);
  animation: action-dock-playback-sweep var(--motion-playback-sweep) linear infinite;
}
@keyframes action-dock-playback-sweep {
  from {
    background-position: -55% 0, 0 0;
  }
  to {
    background-position: 155% 0, 0 0;
  }
}
/* The locked rows stay readable but recede under the cue. */
.action-dock__body--playback .action-dock__pane {
  opacity: 0.5;
  transition: opacity var(--motion-fast) var(--ease-standard);
}

/* The scrolling pane (task 4.1): bounded height with internal scroll. Its
   padding counts inside that height (webclient-band-material-pass), so the
   pane ends exactly at the legend strip and no row ever paints over it. */
.action-dock__pane {
  box-sizing: border-box;
  height: 100%;
  overflow-y: auto;
  padding: calc(6px * var(--ui-scale)) calc(8px * var(--ui-scale)) calc(8px * var(--ui-scale));
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}


.action-dock__pane::-webkit-scrollbar {
  width: calc(6px * var(--ui-scale));
}
.action-dock__pane::-webkit-scrollbar-thumb {
  background: var(--ink-700);
  border-radius: var(--radius-sm);
}

/* The shortcut-legend strip: one line pinned below the scrolling body, so it
   stays visible while the frame's rows scroll. It is exactly the band's
   shared strip height (`--band-strip-h`), so its text shares one baseline
   with the message window's marker and 日誌 / ⌨ controls. */
.action-dock__legend {
  flex: none;
  display: flex;
  align-items: center;
  box-sizing: border-box;
  height: var(--band-strip-h);
  margin: 0;
  padding: 0 calc(8px * var(--ui-scale));
  border-top: 1px solid rgba(85, 82, 75, 0.45);
  font-size: var(--text-xs);
  color: var(--paper-500);
  font-family: var(--f-sans);
  white-space: nowrap;
  overflow: hidden;
}

/* The legend's one inline run, centred in the strip by the flex parent. */
.action-dock__legend-text {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.6;
}

/* The legend's `<kbd>` treatment, verbatim from the reference draft's
   `.dock .hint kbd` rule. */
.action-dock__legend kbd {
  font-family: var(--f-mono);
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: var(--radius-sm);
  padding: 0 calc(4px * var(--ui-scale));
  color: var(--paper-300);
}

/* The combat command card (webclient-combat-command-card-centred D5). The
   frame itself (ground, gold edge, shadow, crest, brackets) is ChoiceCard's;
   here the card fills the host the stage sizes (264px·S by min(400px·S, the
   anchor's span)) and lays its chrome out for the narrow column. */
.action-dock.action-dock--card {
  width: 100%;
  height: 100%;
  max-width: none;
  margin: 0;
  padding: calc(12px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(8px * var(--ui-scale));
  gap: calc(4px * var(--ui-scale));
}
/* Keyboard focus within the card brightens its frame, as the dialogue
   card's does (the base rule above clears the global ring). */
.action-dock.action-dock--card:focus-visible,
.action-dock.action-dock--card:has(:focus-visible) {
  border-color: rgba(228, 200, 142, 0.72);
  box-shadow:
    var(--shadow-lg),
    0 0 0 1px rgba(228, 200, 142, 0.18),
    0 0 calc(22px * var(--ui-scale)) calc(-6px * var(--ui-scale)) var(--gold-glow),
    inset 0 0 0 1px rgba(0, 0, 0, 0.55),
    inset 0 1px 0 1px rgba(238, 221, 180, 0.06);
}
.action-dock--card:focus-visible > .choice-card__corners,
.action-dock--card:has(:focus-visible) > .choice-card__corners {
  opacity: 1;
}
/* The pane never scrolls in the card: the row region inside it does. */
.action-dock--card .action-dock__pane {
  overflow: hidden;
  padding: 0;
}
/* The breadcrumb is one line: the back control and the current frame never
   shrink; earlier crumbs share what is left and ellipsize. */
.action-dock--card :deep(.dock-crumb) {
  flex-wrap: nowrap;
  white-space: nowrap;
  gap: calc(4px * var(--ui-scale));
  margin: calc(-4px * var(--ui-scale)) 0 0 calc(-4px * var(--ui-scale));
  border-bottom: 1px solid rgba(185, 154, 96, 0.16);
}
.action-dock--card :deep(.dock-crumb__back) {
  flex: none;
  min-width: calc(30px * var(--ui-scale));
  min-height: calc(30px * var(--ui-scale));
  padding: 0;
}
.action-dock--card :deep(.dock-crumb__trail) {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
  column-gap: 0.35em;
}
.action-dock--card :deep(.dock-crumb__parents) {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.action-dock--card :deep(.dock-crumb__current) {
  flex: none;
  letter-spacing: 0.06em;
}
/* The stage target step (design D3): the card collapses to the prompt at
   the same centre, width and top (HudFrame lets the host shrink to it, at
   most 136px·S). Every line is --text-sm on a 22px·S line; long text
   ellipsizes; AREA chips are 28px·S tall and wrap onto at most two rows. */
.action-dock.action-dock--card.action-dock--target {
  height: auto;
  gap: calc(4px * var(--ui-scale));
  padding-bottom: calc(10px * var(--ui-scale));
}
.action-dock__body[hidden] {
  display: none;
}
.target-prompt {
  display: flex;
  flex-direction: column;
  gap: calc(4px * var(--ui-scale));
  min-width: 0;
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  line-height: calc(22px * var(--ui-scale));
}
.target-prompt p {
  margin: 0;
}
.target-prompt__head {
  display: flex;
  align-items: baseline;
  gap: calc(4px * var(--ui-scale));
  min-width: 0;
  white-space: nowrap;
  border-bottom: 1px solid rgba(185, 154, 96, 0.18);
  padding-bottom: calc(2px * var(--ui-scale));
}
.target-prompt__action {
  display: flex;
  align-items: baseline;
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  color: var(--paper-500);
}
.target-prompt__verb,
.target-prompt__scale {
  flex: none;
}
.target-prompt__verb {
  font-size: var(--text-xs);
}
.target-prompt__skill {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--f-serif);
  color: var(--gold-300);
}
.target-prompt__scale {
  margin-left: 0.4em;
  color: var(--gold-400);
  font-size: var(--text-xs);
}
.target-prompt__esc {
  flex: none;
  color: var(--paper-500);
  font-size: var(--text-xs);
}
.target-prompt__esc kbd {
  font-family: var(--f-mono);
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: var(--radius-sm);
  padding: 0 calc(4px * var(--ui-scale));
  color: var(--paper-300);
}
.target-prompt__focus {
  display: flex;
  align-items: center;
  gap: calc(6px * var(--ui-scale));
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
}
.target-prompt__glyph {
  flex: none;
  color: var(--gold-400);
}
.target-prompt__name {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--paper-50);
  font-weight: 500;
}
.target-prompt__tag {
  flex: none;
  padding: 0 calc(6px * var(--ui-scale));
  border-radius: var(--radius-pill);
  border: 1px solid currentColor;
  font-size: var(--text-xs);
  line-height: calc(18px * var(--ui-scale));
  color: var(--paper-500);
}
.target-prompt__tag[data-tone="foes"] {
  color: #f0a59a;
  background: rgba(150, 40, 36, 0.22);
}
.target-prompt__tag[data-tone="party"] {
  color: #a9c8f0;
  background: rgba(46, 82, 140, 0.22);
}
.target-prompt__tag[data-tone="chosen"] {
  color: #bfe7c9;
  background: rgba(47, 107, 70, 0.28);
}
.target-prompt__chips {
  display: flex;
  flex-wrap: wrap;
  gap: calc(4px * var(--ui-scale));
  max-height: calc(60px * var(--ui-scale));
  overflow: hidden;
}
.target-prompt__chip {
  flex: 1 1 auto;
  box-sizing: border-box;
  height: calc(28px * var(--ui-scale));
  padding: 0 calc(8px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.45);
  border-radius: var(--radius-sm);
  background: rgba(16, 12, 9, 0.55);
  color: var(--paper-200);
  font: var(--text-xs) / 1 var(--f-sans);
  letter-spacing: 0.04em;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.target-prompt__chip:hover {
  border-color: var(--gold-400);
  color: var(--paper-50);
}
.target-prompt__chip[data-chosen="true"] {
  border-color: #8fd1a2;
  color: #dff5e5;
}
.target-prompt__chip[data-chosen="true"]::before {
  content: "✓ ";
}
.target-prompt__chip[data-kind="confirm"] {
  border-color: var(--gold-500);
  color: var(--gold-300);
  background: rgba(185, 154, 96, 0.12);
}
.target-prompt__chip[data-kind="confirm"][data-empty="true"] {
  border-style: dashed;
  color: var(--paper-500);
  background: transparent;
}
.target-prompt__chip[data-focused="true"] {
  border-color: var(--gold-300);
  background: linear-gradient(180deg, rgba(240, 212, 142, 0.32), rgba(185, 154, 96, 0.18));
  color: var(--paper-50);
  box-shadow: 0 0 0 1px rgba(238, 221, 180, 0.35), 0 0 calc(10px * var(--ui-scale)) rgba(228, 200, 142, 0.35);
}
.target-prompt__chip[data-focused="true"]::after {
  content: " ◂";
  color: var(--gold-300);
}

/* The waiting cue stacks into one centred column in the narrow card. */
.action-dock--card .action-dock__playback {
  grid-template-columns: auto;
  grid-template-rows: auto auto auto auto;
  justify-items: center;
  row-gap: calc(8px * var(--ui-scale));
}
.action-dock--card .action-dock__playback-hint {
  grid-row: 4;
}
.action-dock--card .action-dock__playback-line {
  grid-row: 2;
}
.action-dock--card .action-dock__playback-skip {
  grid-row: 3;
}
/* The legend keeps its text and wraps at its separators onto at most two
   centred lines. */
.action-dock--card .action-dock__legend {
  height: auto;
  min-height: var(--band-strip-h);
  justify-content: center;
  padding: calc(4px * var(--ui-scale)) 0 0;
  border-top-color: rgba(185, 154, 96, 0.18);
  white-space: normal;
  text-align: center;
}
.action-dock--card .action-dock__legend-text {
  overflow: visible;
  line-height: 1.55;
}
.action-dock__legend-seg {
  white-space: nowrap;
}
</style>
