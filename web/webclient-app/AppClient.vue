<script setup>
// C3 (webclient-vue-09-wire-transport-mount): the store-bound live renderers
// (design D3: passive, emit only user-intent dispatches). Every surface
// reads the C1 store's committed slices; panels render only when their
// backing OOB read model is present (the truthful-data scope, roadmap §7 —
// no surface is invented for a panel without a backing model). The behavior
// groups live in ./composables/ (each watch stays with the state it mutates).
import { computed, nextTick, provide, ref, watch } from "vue";
import { useElosernStore } from "./stores/elosern.js";
import { useAppClient } from "./composables/use-app-client.js";
import AppShell from "./components/AppShell.vue";
import ActionDock from "./components/ActionDock.vue";
import CreationOverlay from "./components/CreationOverlay.vue";
import DockMenu from "./components/DockMenu.vue";
import SkillDetailPane from "./components/SkillDetailPane.vue";
import ExitCompass from "./components/ExitCompass.vue";
import ExplorationReadout from "./components/ExplorationReadout.vue";
import FullLogOverlay from "./components/FullLogOverlay.vue";
import CharacterStatusDrawer from "./components/CharacterStatusDrawer.vue";
import HudDrawer from "./components/HudDrawer.vue";
import InventoryPanel from "./components/InventoryPanel.vue";
import LocalMap from "./components/LocalMap.vue";
import LoreCodexDrawer from "./components/LoreCodexDrawer.vue";
import MapOverlay from "./components/MapOverlay.vue";
import RestForm from "./components/RestForm.vue";
import QuestDrawer from "./components/QuestDrawer.vue";
import SceneBackdrop from "./components/SceneBackdrop.vue";
import SettingsOverlay from "./components/SettingsOverlay.vue";
import ShopPanel from "./components/ShopPanel.vue";
import TitleBallotMenu from "./components/TitleBallotMenu.vue";
import SkillBook from "./components/SkillBook.vue";
import SkillUseDock from "./components/SkillUseDock.vue";
import StatusPanel from "./components/StatusPanel.vue";
import OverlayHost from "./components/OverlayHost.vue";
import HelpOverlay from "./components/HelpOverlay.vue";
import LineagePanel from "./components/LineagePanel.vue";
import TitleCodexPanel from "./components/TitleCodexPanel.vue";
import GalleryPanel from "./components/GalleryPanel.vue";
import NpcPersonaEditor from "./components/NpcPersonaEditor.vue";
import LettersPanel from "./components/LettersPanel.vue";
import DreamPanel from "./components/DreamPanel.vue";
import ToastQueue from "./components/ToastQueue.vue";
import CompanionLineup from "./components/CompanionLineup.vue";
import { companionFigures, displayedLineup, lineupSlotByIdentity } from "./components/companion-lineup.js";
import { portraitFor } from "./components/party-helpers.js";
import PartyDrawer from "./components/PartyDrawer.vue";
import ObjectiveTracker from "./components/ObjectiveTracker.vue";
import DesktopNavigation from "./components/DesktopNavigation.vue";
import ReferenceArtwork from "./components/ReferenceArtwork.vue";
import StageActor from "./components/StageActor.vue";
import FoeLineup from "./components/FoeLineup.vue";
import { drawnFoes, fallenLook, foeStageLimit } from "./components/foe-lineup.js";
import FigurePlate from "./components/FigurePlate.vue";
import { plateHpCurrent, repeatedNames } from "./components/figure-plate.js";
import { formationOrderFor, markersFor, onStage, positionKeyFor, targetingFor } from "./components/stage-targeting.js";
import { useCombatFormation } from "./composables/use-combat-formation.js";
import { useFormationGlide } from "./composables/use-formation-glide.js";
import DialogueChoices from "./components/DialogueChoices.vue";
import ChoiceCard from "./components/ChoiceCard.vue";
import QuestionCard from "./components/QuestionCard.vue";
import PresenceRail from "./components/PresenceRail.vue";
import { inertWhileLeaving } from "./lib/transition_hooks.js";

const store = useElosernStore();
const currentCharacter = computed(
  () => store.view.rosterCharacters?.find((character) => character.current) ?? null,
);
// The current character's own figure position (design D4/D10): its complete
// roster descriptor, judged against the committed roster panel that admitted
// it — the owner's row stays the roster's current row even while a bound
// companion is possessed.
const currentArtwork = computed(() => currentCharacter.value?.portrait ?? null);
// The shell handle (H5, design D1/D6) and the SceneBackdrop harness hook
// (the __-prefixed pending-scene journey seeds the prior-image memory
// through this handle — SceneBackdrop's exposed setPriorImage).
const shellRef = ref(null);
const sceneBackdropRef = ref(null);
// The behavior groups composed in use-app-client.js: every binding below is
// a group's verbatim state/handler, destructured so the template is unchanged.
const {
  panel, panelAvailable, dispatchIntent, modeChange, modeHydrating,
  dialogueVM, onDialoguePick, onDialogueFreeform, onDialogueLeave,
  onReadingChange, choicesShown, dialogueExits, onDialogueMove, beforeChoiceActivate,
  completionCandidates, possessionBanner, contextAffordances, releaseAffordance,
  titleBallotPanel, titleBallotCandidates, onMapMove, showObjectiveTracker,
  skipDisabled, practiceOpen, practiceFeedback, onPractice,
  fullLogOpen, fullLogRef, openFullLog, closeFullLog, openSurfaces,
  openOverlayByName, onOpenOverlay, onMapExpand, onOverlayClose,
  drawerTitle, drawerIcon, drawerHasArt, onOpenDrawer, onHudDrawerClose, skillBookSubtitle,
  inventoryWalletCopper, inventoryWalletSubtitle, partyReason, SKILL_BOOK_KEY_HINT,
  rootItems, navigationItems, dockItems, dockPaneKind,
  explorationRootShown,
  onTabClick, onDockBack, contextActionsPanel, rowPrefix, detailTestId,
  showDetail,
  onAction, onDockActivate, onDockFocusChange,
  onShopBuy, onShopSell, onInventoryItemAction, onTitleBallotAction, onTitleCodexAction,
  onCreationAction, onCreationDispatch, onCreationRequestReset, onCreationCancelConfirm,
  onQuestAction, onPersonaEdit, onSubmitCommand, onSwitchCharacter, onCreateCharacter,
  npcPersonaEditor, npcPersonaSetField, npcPersonaSave, npcPersonaReload, npcPersonaDiscard,
  npcPersonaRetry, npcPersonaClose,
  onSkillUse, skillUseDockShown, skillUseLocked,
  compassRef, compassTargets, compassArrivalKey, compassBusy, compassActive,
  readoutContent, aimedNode, onCompassMove, onCompassAim, onCompassBlocked, onRailHover,
  railRef, railMounted, railShown, presenceCardOpen, personFocus, focusTarget, focusPortrait,
  cardRows, cardKey, cardCaption, cardLabel, speaker,
  onRailActivate, onCardPick, onCardBack,
  roomCardRef, roomCard, roomCardOpen, roomCardShown, roomCardRows, roomCardNotes, roomCardTrailing,
  roomCardCaption, roomCardLabel, dreamOpen, restOpen, placeActions, pillShown, pillCount, pillLabel,
  onPlaceLook, onPlaceWait, onPill, onRoomCardPick, onRoomCardBack, onDreamAnswer, onDreamClose,
  onRestSubmit, onRestClose, onPlaceHover, onPillHoverChange,
  onCompassTab, onRailTab, onPlaceTab, onPillTab,
} = useAppClient(store, shellRef, sceneBackdropRef);
// The dialogue host's standing figure (webclient-dialogue-stage-actors D2):
// the canonical descriptor the committed `dialogue` panel's
// `host.portrait_ref` names in the committed `art` panel's catalog — so a
// pending host shows its own truthful state and an admitted silhouette-only
// host keeps its reference; a null reference is expected absence and a
// dangling one a local failure. The client never builds a catalog key.
const hostPortrait = computed(() => {
  const key = dialogueVM.value?.host.portraitRef;
  return key == null ? null : (panel("art")?.portrait_catalog?.[key]?.artwork ?? null);
});
// The speaking state (design D3): only a conversation with its host on the
// stage dims anyone (a transiently unavailable panel leaves the player lit).
const inDialogue = computed(() => store.view.mode === "dialogue");
// The host's entrance and exit (webclient-mode-transitions D3) animate only
// on a live mode change: at `off` there is no CSS phase (a CSS phase would
// outlive the commit by a double frame even at 0s), and across a reconnect
// (`modeHydrating`) the host appears and goes in the commit's frame.
const hostTransitionCss = computed(
  () => store.view.motionLevel !== "off" && !modeHydrating.value,
);
// The figures `actor-left` really draws (reuse-lineup-person-focus D1): the
// bounded list `CompanionLineup` displays, so the actor-right join below
// decides membership on what is rendered — never on raw `party.slots`, a
// display name, a portrait key or art availability.
const renderedLineup = computed(() => displayedLineup(companionLineupSlots.value));
// The one figure in `actor-right` outside combat (exploration-presence-rail
// design D3): the dialogue host while the conversation is on, else the
// person in focus behind the verb card. Both are keyed by the same
// server-authored identity, so the commit that turns 交談 into the dialogue
// screen keeps the very same StageActor element on the stage — no leave,
// no re-entry.
const actorRightTarget = computed(() => {
  if (inDialogue.value && dialogueVM.value) {
    return {
      identity: dialogueVM.value.host.identity,
      name: dialogueVM.value.host.displayName,
      artwork: hostPortrait.value,
      panel: panel("art"),
      hasReference: dialogueVM.value.host.portraitRef != null,
    };
  }
  if (store.view.mode === "exploration" && personFocus.value && focusTarget.value) {
    return {
      identity: focusTarget.value.identity,
      name: focusTarget.value.display_name,
      artwork: focusPortrait.value,
      panel: panel("art"),
      hasReference: focusTarget.value.portrait_ref != null,
    };
  }
  return null;
});
// The exploration card target's rendered figure, or null (D1): exploration
// mode, an open verbs card, and a target still committed to the room. All
// three are committed state, so a target that leaves the room clears the
// emphasis in that commit even while a locked settlement still holds the card
// open (D3). The join normalizes identity only for the comparison and carries
// no other evidence — a null portrait still matches, equal names never do.
const explorationFocusFigure = computed(() =>
  store.view.mode === "exploration" && personFocus.value && focusTarget.value
    ? lineupSlotByIdentity(renderedLineup.value, focusTarget.value.identity)
    : null,
);
// The actor-right identity's rendered figure, or null (D1): a person the
// actor-left row already draws is represented once and gets no actor-right
// copy. The dialogue host and the focused person share this one rule.
const actorRightFigure = computed(() => {
  if (inDialogue.value && dialogueVM.value) {
    return lineupSlotByIdentity(renderedLineup.value, dialogueVM.value.host.identity);
  }
  return explorationFocusFigure.value;
});
const standee = computed(() => (actorRightFigure.value ? null : actorRightTarget.value));
// The representation transfer must not leave a right-side copy behind (D1):
// when the standee disappears because its identity is now drawn in the
// actor-left lineup, that leave phase is skipped. Every other entrance and
// exit — a non-lineup target's card closing, a departure — keeps the ordinary
// CSS phase, and `off`/hydrating keep it off as before.
const standeeTransitionCss = computed(() => hostTransitionCss.value && !actorRightFigure.value);
// The exploration emphasis identity (D2): the selected rendered NON-controlled
// slot's own identity, handed to the existing companion speaking signal so that
// one figure goes lit with z above every baseline. The controlled front is
// never a listener, so it never supplies this value and keeps its baseline z,
// its independent dim and its beat gestures.
const explorationSpeakingIdentity = computed(() => {
  const figure = explorationFocusFigure.value;
  return figure && !figure.isControlled ? figure.identity : null;
});
// The dialogue emphasis is unchanged (design D3): the committed host while the
// conversation is on and the host is the one speaking. Dialogue and
// exploration are exclusive modes, so one prop carries both.
const dialogueSpeakingIdentity = computed(() =>
  inDialogue.value && dialogueVM.value && store.view.dialogueSpeaker === "host"
    ? panel("dialogue")?.host?.identity ?? null
    : null,
);
const companionSpeakingIdentity = computed(() => dialogueSpeakingIdentity.value ?? explorationSpeakingIdentity.value);
const isControllingCompanion = computed(() => !!possessionBanner.value?.available);
const companionLineupSlots = computed(() => companionFigures({
  player: {
    identity: currentCharacter.value?.identity,
    // The player's own figure is the ROSTER position: its complete roster
    // descriptor, judged against the committed roster panel that admitted it.
    artwork: currentArtwork.value,
    panel: panel("roster"),
    hasReference: true,
    displayName: currentCharacter.value?.name || panel("status")?.actor?.name || "",
  },
  companions: store.partyAvailable ? store.partySlots : [],
  actorIdentity: panel("status")?.actor?.identity,
  possessing: isControllingCompanion.value,
  controlledName: possessionBanner.value?.host_name || "",
  artPanel: panel("art"), portraitFor,
}));
// Vue keeps a leaving stage actor until its CSS phase ends and cannot cancel a
// started leave without a re-entering child, and the lineup's own slots use no
// transition, so a copy still leaving when its identity becomes drawn in the
// lineup would paint a second figure of the represented person (D1). Every
// committed membership change therefore finishes exactly the copies it
// overtakes: the stage actor carries the identity it was drawn for, and a
// stage actor still in `actor-right` whose identity is now drawn on the left
// is by construction such a copy. Vue's own leave completion stays a no-op on
// the detached element, and a leave of an unrepresented identity is untouched.
// The trigger is the rendered identities, not the current focus, so a leave
// that started before the transfer (an earlier card close) is finished too.
const renderedIdentities = computed(() =>
  renderedLineup.value.map((slot) => String(slot.identity)).join(","),
);
watch(
  renderedIdentities,
  (key) => {
    if (!key) {
      return;
    }
    const drawn = new Set(key.split(","));
    document
      .querySelectorAll('[data-testid="anchor-actor-right"] [data-testid="stage-actor"][data-identity]')
      .forEach((el) => {
        if (drawn.has(el.getAttribute("data-identity"))) {
          el.remove();
        }
      });
  },
  { flush: "post" },
);
// The player's displayed hit points while a combat round plays
// (webclient-combat-beat-queue D7): the published playback value keyed by the
// committed actor identity, else null, so the vitals island reads the
// committed `status` whenever nothing plays.
const playerDisplayHp = computed(() => {
  const displayed = store.view.displayHp;
  const identity = panel("status")?.actor?.identity;
  if (!displayed || identity == null) {
    return null;
  }
  const value = displayed[identity];
  return typeof value === "number" ? value : null;
});
// The foe line-up (webclient-combat-foes-on-stage D1/D3): the committed
// combat panel's foes that have not fled (webclient-combat-defeated-foes D5:
// a knocked-out or defeated foe keeps its slot), in presenter order, stand in
// `actor-right` while the mode is combat. It enters and leaves on the same
// live-only rule as the host (`hostTransitionCss`).
const combatFoes = computed(() =>
  contextActionsPanel.value?.kind === "combat" ? drawnFoes(contextActionsPanel.value.participants) : [],
);
// While a combat round plays by itself (webclient-combat-beat-choreography
// D5/D6), the line-up stands the round's pre-round foes until each one's own
// defeat beat; the round that ended the fight keeps them on the stage
// (`beatHold`, inert) after the committed mode has already left combat.
const beatStage = computed(() => store.view.beatStage || null);
// Direct target choices live in `combat.skill`; staged choices live in
// `combat.target`. Resolve the focused item's action payload instead of
// parsing its key or assuming either source. AREA submit/shorthands carry no
// single target.
const focusedCombatTarget = computed(() => {
  if (store.view.dispatch.beatLocked) return null;
  const item = store.view.combatMenu?.items?.find((row) => row.key === store.view.focus.key);
  if (item?.actionId === "toggle-target") return item.payload?.identity ?? null;
  return item?.actionId === "combat.cast" && item.payload?.target_ids?.length === 1
    ? item.payload.target_ids[0] : null;
});
const beatHold = computed(() => !!store.view.beatHold);
const lineupFoes = computed(() => (beatStage.value ? beatStage.value.foes : combatFoes.value));
const foesOnStage = computed(
  () => (store.view.mode === "combat" || beatHold.value) && lineupFoes.value.length > 0,
);
const stageMode = computed(() =>
  beatHold.value && (store.view.mode === "exploration" || store.view.mode === "combat")
    ? "combat"
    : store.view.mode || "exploration",
);
// The player's own beat gesture, keyed by the committed actor identity.
const playerGesture = computed(() => {
  const identity = panel("status")?.actor?.identity;
  const entry = identity == null ? null : beatStage.value?.gestures?.[identity];
  return entry || null;
});
// The combat formation (webclient-combat-formation D1): while the stage is in
// combat (the committed mode, or a held round that ended the fight), the
// controlled figure, every drawn companion and every active foe up to
// `16 - party` stand at the engine's boxes for the measured stage. The
// counts, the mode and the measurements are all inputs of one computed, so a
// roster change re-forms both sides in the same tick.
const rootRef = ref(null);
const formationActive = computed(() => stageMode.value === "combat");
const partyFigureCount = computed(() => Math.max(1, renderedLineup.value.length));
const foeLimit = computed(() => foeStageLimit(partyFigureCount.value));
const formationCounts = computed(() => ({
  party: partyFigureCount.value,
  foes: foesOnStage.value ? Math.min(lineupFoes.value.length, foeLimit.value) : 0,
}));
const { formation, metrics: stageMetrics, instant: formationInstant } = useCombatFormation({
  rootRef,
  active: formationActive,
  counts: formationCounts,
});
// A re-formed line glides at `full`, never across a reconnect or a resize.
const formationGlide = computed(
  () => store.view.motionLevel === "full" && !modeHydrating.value && !formationInstant.value,
);
useFormationGlide({ rootRef, formation, enabled: () => formationGlide.value });

// The glance plates (design D4): one per drawn figure other than the
// controlled one, in its formation plate slot. Numbers come from the combat
// panel's participant row joined by identity (the displayed playback value
// while a round plays); the session token is shown only while two drawn
// figures share a name.
const combatParticipants = computed(() =>
  contextActionsPanel.value?.kind === "combat" && Array.isArray(contextActionsPanel.value.participants)
    ? contextActionsPanel.value.participants
    : [],
);
function participantFor(identity) {
  if (identity === null || identity === undefined) return null;
  const key = String(identity);
  return combatParticipants.value.find((p) => String(p.identity) === key) ?? null;
}
// The fallen looks the stage shows (webclient-combat-defeated-foes D1/D4),
// identity -> "defeated" | "down", only while the formation stands: the
// playing round's own looks (a foe falls on its defeat beat), else the
// committed participants' states. The line-ups, the controlled figure and
// the plates all read this one map.
const fallenMap = computed(() => {
  if (!formationActive.value) return {};
  if (beatStage.value) return beatStage.value.fallen || {};
  const map = {};
  for (const row of combatParticipants.value) {
    const look = row && row.identity != null ? fallenLook(row.team, row.state) : null;
    if (look) map[String(row.identity)] = look;
  }
  return map;
});
function fallenOf(identity) {
  return identity == null ? null : fallenMap.value[String(identity)] ?? null;
}
const actingIdentity = computed(() => {
  const gestures = beatStage.value?.gestures;
  if (!gestures) return null;
  const ref = Object.keys(gestures).find((key) => gestures[key]?.gesture === "lunge");
  return ref ?? null;
});
const plateEntries = computed(() => {
  const shape = formation.value;
  if (!shape) return [];
  const party = renderedLineup.value.slice(0, shape.party.figures.length);
  const foes = lineupFoes.value.slice(0, shape.foes.figures.length);
  const repeated = repeatedNames([...party.map((slot) => slot.displayName), ...foes.map((p) => p.display_name)]);
  const displayHp = store.view.displayHp;
  const entries = [];
  party.forEach((slot, index) => {
    if (slot.isControlled) return;
    const row = participantFor(slot.identity);
    entries.push({
      key: `party:${slot.identity}`,
      identity: slot.identity,
      side: "party",
      name: slot.displayName || row?.display_name || "",
      token: row?.token ?? "",
      showToken: repeated.has(slot.displayName),
      hpCurrent: row ? plateHpCurrent(row, displayHp) : null,
      hpMaximum: row?.hp_maximum ?? null,
      conditions: row?.conditions ?? [],
      plate: shape.party.figures[index].plate,
      fallen: fallenOf(slot.identity),
      target: false,
      acting: false,
    });
  });
  foes.forEach((p, index) => {
    // The committed row carries the current numbers; while a round plays a
    // pre-round foe the committed roster has lost keeps its pre-round row.
    const row = participantFor(p.identity) ?? p;
    entries.push({
      key: `foe:${p.identity}`,
      identity: p.identity,
      side: "foes",
      name: p.display_name,
      token: p.token ?? "",
      showToken: repeated.has(p.display_name),
      hpCurrent: plateHpCurrent(row, displayHp),
      hpMaximum: row.hp_maximum ?? null,
      conditions: row.conditions ?? [],
      plate: shape.foes.figures[index].plate,
      fallen: fallenOf(p.identity),
      target: focusedCombatTarget.value != null && String(focusedCombatTarget.value) === String(p.identity),
      acting: actingIdentity.value != null && p.portrait_ref != null && String(p.portrait_ref) === actingIdentity.value,
    });
  });
  return entries;
});

// The plates' condition tooltips (webclient-combat-figure-plates, design
// D3) close when a round starts playing and when the committed mode
// changes; a resize and a scroll close them inside ConditionChips. The
// counter is provided, not passed, so a plate already fading out of the
// stage (no longer patched) still sees it.
const plateTooltipClose = ref(0);
provide("plateTooltipClose", plateTooltipClose);
watch(
  () => !!store.view.dispatch.beatLocked,
  (locked) => {
    if (locked) plateTooltipClose.value += 1;
  },
);
watch(
  () => store.view.mode,
  () => {
    plateTooltipClose.value += 1;
  },
);

// The stage target step (webclient-combat-stage-target-picking D1/D4): the
// store's model of the current target frame (null outside it), the stage
// order it reads (published from the very formation the stage draws), the
// line-ups' lit/selectable sets, and the arrow markers in the plates layer.
const controlledFigureId = computed(() => renderedLineup.value.find((slot) => slot.isControlled)?.identity ?? null);
const stageTarget = computed(() => onStage(store.view.stageTarget || null, controlledFigureId.value));
const drawnParty = computed(() => {
  const shape = formation.value;
  return shape ? renderedLineup.value.slice(0, shape.party.figures.length).map((slot) => slot.identity) : [];
});
const drawnFoeIds = computed(() => {
  const shape = formation.value;
  return shape ? lineupFoes.value.slice(0, shape.foes.figures.length).map((p) => p.identity) : [];
});
const stageOrder = computed(() => formationOrderFor(formation.value, drawnParty.value, drawnFoeIds.value));
watch(stageOrder, (order) => store.setStageFormation(order), { immediate: true });
const targeting = computed(() => targetingFor(stageTarget.value));
const targetMarkers = computed(() =>
  markersFor(stageTarget.value, formation.value, drawnParty.value, drawnFoeIds.value),
);
function onTargetFigure(identity, action) {
  const key = positionKeyFor(stageTarget.value, identity);
  if (key) store.stageTargetPointer(key, action);
}
function onTargetPosition(key, action) {
  store.stageTargetPointer(key, action);
}

// The cross-side question (webclient-combat-cross-side-confirm D2/D3): a
// held cast's yes/no card over the stage target step. 是 waits for the same
// submission gate every combat command does (a mutation in flight, a
// declared revision not yet committed, a locked or inactive session); 否 and
// the close control always answer.
const crossSideQuestion = computed(() =>
  store.view.mode === "combat" ? store.view.crossSideConfirm?.question ?? null : null,
);
const crossSideOpen = computed(() => crossSideQuestion.value !== null);
const crossSideLocked = computed(
  () =>
    !store.view.connected ||
    store.view.phase !== "active" ||
    !!store.view.mutationsLocked ||
    !!store.view.dispatch?.inFlight ||
    !!store.view.submitLocked,
);
// Every close path requests DOM focus on the dock through the store; a
// close the store does not route there (the mode left combat), or a focus
// the still-inert dock refused, falls back to the mode's focus home, so the
// question never leaves focus on the document body.
watch(crossSideOpen, async (open, was) => {
  if (open || !was) return;
  await nextTick();
  await nextTick();
  const active = typeof document === "undefined" ? null : document.activeElement;
  if (!active || active === document.body) {
    shellRef.value?.restoreFocusHome?.();
  }
});
// Starting a step closes any open plate tooltip (webclient-combat-figure-
// plates D3) and moves keyboard focus out of the plates group to the card,
// so the step's arrow keys and the group's never compete.
watch(
  () => !!stageTarget.value,
  (active, was) => {
    if (!active || was) return;
    plateTooltipClose.value += 1;
    const focused = typeof document === "undefined" ? null : document.activeElement;
    if (focused && focused.closest && focused.closest('[data-anchor="plates"]')) {
      document.getElementById("action-dock")?.focus({ preventScroll: true });
    }
  },
);

// The scene caption stays centred in the open stage between the party's
// innermost figure and the leftmost foe (app-shell.css reads
// `--caption-left`/`--caption-right`). The foe edge keeps the room of a line
// that shrinks until its leaving foe has faded, and of a line that leaves the
// stage until it has faded, so the caption never slides under a fading
// figure; a line that grows takes its room at once.
const captionGap = computed(() => 16 * (stageMetrics.value?.uiScale ?? 1));
const partyEdge = computed(() => {
  const figures = formation.value?.party.figures ?? [];
  return figures.length ? Math.max(...figures.map((f) => f.box.left + f.box.width)) : null;
});
const foeEdgeNow = computed(() => {
  const shape = formation.value;
  const figures = shape?.foes.figures ?? [];
  // The stage's width is twice its centre (the engine's frame).
  return figures.length ? shape.centre * 2 - Math.min(...figures.map((f) => f.box.left)) : null;
});
const foeEdge = ref(null);
watch(
  foeEdgeNow,
  (edge) => {
    // A resize re-forms in place (`formationInstant`), so the edge follows the
    // new stage at once even when it shrinks; only a roster change holds it.
    if (edge !== null && (foeEdge.value === null || edge >= foeEdge.value || formationInstant.value)) {
      foeEdge.value = edge;
    }
  },
  { immediate: true },
);
function onFoeLineupSettled() {
  foeEdge.value = foeEdgeNow.value;
}
function onFoeLineupGone() {
  if (!foesOnStage.value) {
    foeEdge.value = null;
  }
}
const rootStyle = computed(() => {
  const style = {};
  // The shared figure scale, for the figures' placeholder glyphs and labels.
  if (formation.value) style["--formation-scale"] = formation.value.scale;
  if (partyEdge.value !== null) style["--caption-left"] = `${partyEdge.value + captionGap.value}px`;
  if (foeEdge.value !== null) style["--caption-right"] = `${foeEdge.value + captionGap.value}px`;
  return style;
});
</script>

<template>
  <div
    ref="rootRef"
    class="elosern-root"
    data-testid="elosern-client-root"
    :data-cross-side-open="crossSideOpen ? 'true' : null"
    :style="rootStyle"
  >
      <AppShell
        ref="shellRef"
        :mode="store.view.mode || 'exploration'"
        :connected="store.view.connected"
        :location-label="store.view.statusSlice.locationLabel"
        :time-label="store.view.statusSlice.timeLabel"
        :narrative="store.narrative"
        :response-marks="store.responseMarks"
        :dialogue="dialogueVM"
        :font-scale="store.view.fontScale"
        :text-speed="store.view.textSpeed"
        :auto-advance="store.view.autoAdvance"
        :motion-level="store.view.motionLevel"
        :beat-playback="store.view.beatPlayback"
        :mode-change="modeChange"
        :beat-hold="beatHold"
        :card-open="presenceCardOpen || roomCardOpen"
        :person-focus="personFocus"
        :formation="!!formation"
        :speaker="speaker"
        :mode-hydrating="modeHydrating"
        :connection-status="store.view.connectionStatus"
        :offline="!store.view.connected"
        :uncertain="store.view.dispatch.uncertain"
        :prompt="store.view.prompt"
        :command-history="store.commandHistory"
        :mutations-locked="store.view.mutationsLocked"
        :open-surfaces="openSurfaces"
        :low-hp="store.view.vitals.lowHp"
        :vitals-visible="store.view.vitals.visible"
        :text-to-html="store.view.textToHtml"
        :command-accepts="store.view.commandAccepts"
        :completion-candidates="completionCandidates"
        :roster-available="store.rosterAvailable"
        :roster-characters="store.rosterCharacters"
        :roster-can-create="store.rosterCanCreate"
        :roster-switch-locked="store.rosterSwitchLocked"
        :roster-lock-reason="store.rosterLockReason"
        :roster-panel="panel('roster')"
        :epoch="store.view.epoch"
        :possession-banner="possessionBanner"
        :place-actions="placeActions"
        @submit-command="onSubmitCommand"
        @focus-lost="store.clearFreeformTarget()"
        @open-full-log="openFullLog"
        @reading-change="onReadingChange"
        @beat-shown="store.beatShown"
        @beat-skip="store.skipBeats"
        @switch-character="onSwitchCharacter"
        @create-character="onCreateCharacter"
        @place-look="onPlaceLook"
        @place-wait="onPlaceWait"
        @place-hover="onPlaceHover"
        @place-tab="onPlaceTab"
      >
        <template #navigation>
          <DesktopNavigation
            :mode="store.view.mode"
            :items="navigationItems"
            :drawer="store.view.hudDrawer"
            :gallery-available="panelAvailable('gallery')"
            @navigate="onTabClick"
            @overlay="onOpenOverlay"
            @drawer="onOpenDrawer"
          />
        </template>
        <!-- The scene backdrop is the lowest stage layer (design D3/D8):
             it renders the committed `art` panel's scene truthfully — the
             done image, the dimmed prior image, or the mode gradient with a
             truthful placeholder. -->
        <template #backdrop>
          <SceneBackdrop
            ref="sceneBackdropRef"
            :art="panel('art') || {}"
            :mode="stageMode"
            :motion-level="store.view.motionLevel"
          />
        </template>
        <!-- The player's standing portrait (webclient-avg-stage-shell D4):
             the current roster character's portrait stands on the bottom
             band's top edge in the `actor-left` anchor, outside creation,
             dimmed while the dialogue host speaks. -->
        <template #actor-left>
          <CompanionLineup
            v-if="store.view.mode !== 'creation'"
            :slots="companionLineupSlots"
            :compact="inDialogue"
            :speaking-identity="companionSpeakingIdentity"
            :dimmed="inDialogue && !!dialogueVM && store.view.dialogueSpeaker === 'host'"
            :motion-level="store.view.motionLevel"
            :gesture="playerGesture?.gesture ?? null"
            :gesture-key="beatStage?.key ?? null"
            :float-amount="playerGesture?.amount ?? null"
            :formation="formation?.party ?? null"
            :glide="formationGlide"
            :fallen="fallenMap"
            :fall-instant="modeHydrating"
            :targeting="targeting"
            @target-pointer="onTargetFigure"
          />
        </template>
        <!-- The opposite side of the stage (webclient-dialogue-stage-actors
             D2 stands the dialogue host here; exploration-presence-rail D3
             the person in focus). -->
        <template #actor-right>
          <!-- The one non-combat standee (the dialogue host, else the person
               in focus) enters from the right and leaves to it
               (webclient-mode-transitions D3), keyed by identity so a new
               host during a session hands over; a new portrait for the same
               host is StageActor's own crossfade. A person the actor-left
               lineup already draws stands there instead, so this anchor is
               empty and the transfer skips its leave phase rather than
               leaving a right-side copy behind (reuse-lineup-person-focus
               D1) — the inert rule below still covers every other leaving
               copy. -->
          <Transition name="actor-enter" :css="standeeTransitionCss" v-bind="inertWhileLeaving">
            <StageActor
              v-if="standee"
              :key="standee.identity"
              :data-identity="standee.identity"
              side="right"
              :artwork="standee.artwork"
              :panel="standee.panel"
              :has-reference="standee.hasReference"
              :name="standee.name"
              :dimmed="inDialogue && store.view.dialogueSpeaker === 'player'"
              :motion-level="store.view.motionLevel"
            />
          </Transition>
          <!-- The foe line-up (webclient-combat-foes-on-stage D1/D3): the
               active foes stand opposite the player in combat. It slides in
               as the combat flash releases on a live entry, fades on leaving
               (inert), and mounts in place on a reload or reconnect. -->
          <!-- While the round that ended the fight is held
               (webclient-combat-beat-choreography D6) the line-up is inert.
               It is already mounted from combat when the hold begins; a
               fresh mount would run `inertWhileLeaving`'s enter hook, which
               clears `inert`, so the hold relies on that ordering. -->
          <Transition
            name="foes-enter"
            :css="hostTransitionCss"
            v-bind="inertWhileLeaving"
            @after-leave="onFoeLineupGone"
          >
            <FoeLineup
              v-if="foesOnStage"
              :foes="combatFoes"
              :stage="beatStage"
              :max="foeLimit"
              :formation="formation?.foes ?? null"
              :glide="formationGlide"
              :fallen="fallenMap"
              :fall-instant="modeHydrating"
              :inert="beatHold || null"
              :art-panel="panel('art')"
              :motion-level="store.view.motionLevel"
              :targeting="targeting"
              @settled="onFoeLineupSettled"
              @target-pointer="onTargetFigure"
            />
          </Transition>
        </template>
        <!-- The glance plates (webclient-combat-formation D4): one per drawn
             figure other than the controlled one, at its formation plate
             slot. They rise in once their figures have landed, glide with
             them on a re-formed line, and fade where they stand on leaving. -->
        <template #plates>
          <TransitionGroup
            tag="div"
            class="figure-plates"
            name="figure-plate"
            :data-glide="formationGlide ? 'true' : 'false'"
            :css="hostTransitionCss"
            v-bind="inertWhileLeaving"
          >
            <FigurePlate
              v-for="entry in plateEntries"
              :key="entry.key"
              :identity="entry.identity"
              :name="entry.name"
              :token="entry.token"
              :show-token="entry.showToken"
              :side="entry.side"
              :hp-current="entry.hpCurrent"
              :hp-maximum="entry.hpMaximum"
              :form="entry.plate.form"
              :box="entry.plate"
              :target="entry.target"
              :acting="entry.acting"
              :conditions="entry.conditions"
              :stage-x="entry.plate.left + entry.plate.width / 2"
              :fallen="entry.fallen"
            />
          </TransitionGroup>
          <!-- The stage target step's arrow markers (webclient-combat-stage-
               target-picking D4): one per selectable drawn figure at its
               formation marker slot, directly above its plate; filled and
               larger on a lit figure, outlined otherwise, with the item's
               digit (server order) and a check for a selected AREA member.
               They appear without an entrance and take a pointer like the
               figure's hit area; the card's live region is their reading. -->
          <div v-if="targetMarkers.length" class="stage-target-markers" aria-hidden="true">
            <span
              v-for="marker in targetMarkers"
              :key="marker.key"
              class="stage-target__marker"
              data-testid="stage-target-marker"
              :data-identity="marker.identity"
              :data-state="marker.state"
              :data-selected="marker.selected ? 'true' : null"
              :data-target-motion="store.view.motionLevel === 'full' ? 'full' : 'static'"
              :style="{
                left: `${marker.box.left}px`,
                top: `${marker.box.top}px`,
                width: `${marker.box.width}px`,
                height: `${marker.box.height}px`,
              }"
              @pointerenter="onTargetPosition(marker.positionKey, 'hover')"
              @click="onTargetPosition(marker.positionKey, 'activate')"
            >
              <svg class="stage-target__arrow" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3.5 2.5h17v10.2L12 21.5 3.5 12.7z" />
              </svg>
              <b v-if="marker.digit !== null" class="stage-target__digit">{{ marker.digit }}</b>
              <i v-if="marker.selected" class="stage-target__check" data-testid="stage-target-check">✓</i>
            </span>
          </div>
        </template>
        <!-- The dialogue choice list (webclient-dialogue-choices-overlay
             D4/D5), centred over the stage: only in dialogue with the panel
             available, once the line is fully read, and never while an
             action is in flight. -->
        <template #choices>
          <!-- The room cards (exploration-room-actions design D1/D4/D5): the
               wait card the place card's 等待 opens and the suggestions card
               the 建議 pill opens, through the one card shell, trapping focus
               until they close. The wait card stays mounted (hidden) under
               its 進入夢境協作？ question and its rest form, so it keeps its
               active row for the return. -->
          <template v-if="roomCardOpen">
            <ChoiceCard
              v-show="roomCardShown"
              ref="roomCardRef"
              :key="roomCard.kind"
              :test-id="`${roomCard.kind}-card`"
              :data-card-kind="roomCard.kind"
              :rows="roomCardRows"
              :notes="roomCardNotes"
              :trailing-index="roomCardTrailing"
              :caption="roomCardCaption"
              :aria-label="roomCardLabel"
              :entrance="!modeHydrating"
              trap-focus
              autofocus
              @pick="onRoomCardPick"
              @back="onRoomCardBack"
            />
            <QuestionCard
              v-if="dreamOpen"
              test-id="dream-question"
              question="進入夢境協作？"
              close-label="取消睡眠"
              :locked="skipDisabled"
              reason="上一個行動尚未完成，請稍候。"
              :entrance="!modeHydrating"
              @yes="onDreamAnswer(true)"
              @no="onDreamAnswer(false)"
              @close="onDreamClose"
            />
            <section
              v-if="restOpen"
              class="choice-card rest-card"
              role="dialog"
              aria-label="休息 N 小時"
              data-testid="rest-card"
            >
              <span class="choice-card__corners" aria-hidden="true"></span>
              <div class="choice-card__caption" aria-hidden="true">休息 N 小時</div>
              <RestForm :disabled="skipDisabled" @submit="onRestSubmit" @close="onRestClose" />
            </section>
          </template>
          <!-- The exploration cards (exploration-presence-rail design D4):
               a person's verb card or the overflow card, through the one
               card shell, trapping focus until it closes. -->
          <ChoiceCard
            v-else-if="presenceCardOpen"
            :key="cardKey"
            test-id="presence-card"
            :data-card-kind="store.view.presenceCard?.kind"
            :rows="cardRows"
            :trailing-index="cardRows.length - 1"
            :caption="cardCaption"
            :aria-label="cardLabel"
            :entrance="!modeHydrating"
            trap-focus
            autofocus
            @pick="onCardPick"
            @back="onCardBack"
          />
          <!-- The cross-side question (webclient-combat-cross-side-confirm
               D3): over the collapsed command card, centred in the anchor,
               focus starting on its safe answer 否. The card host (the
               teleported dock) stays where it is, inert beneath it. -->
          <QuestionCard
            v-else-if="crossSideOpen"
            class="cross-side-question"
            test-id="cross-side-question"
            :question="crossSideQuestion"
            caption="跨陣營施展"
            tone="caution"
            initial-focus="no"
            no-while-locked
            close-label="返回選擇目標"
            :locked="crossSideLocked"
            reason="上一個行動尚未完成，請稍候。"
            :entrance="!modeHydrating"
            @yes="store.confirmCrossSide()"
            @no="store.cancelCrossSide()"
            @close="store.cancelCrossSide()"
          />
          <DialogueChoices
            v-else-if="choicesShown"
            :entrance="!modeHydrating"
            :picks="dialogueVM.picks"
            :exits="dialogueExits"
            :local-map="store.view.localMapModel"
            :locked="store.view.dispatch.inFlight !== null"
            :before-activate="beforeChoiceActivate"
            @pick="onDialoguePick"
            @freeform="onDialogueFreeform"
            @move="onDialogueMove"
            @leave="onDialogueLeave"
          />
        </template>
        <!-- The presence rail (exploration-presence-rail design D4): the
             room's people and objects on the stage floor. It stays mounted
             (hidden, inert) under a card, so the opener takes focus back the
             moment the card closes. -->
        <template #presence>
          <Transition name="presence-rail-fade" :css="store.view.motionLevel !== 'off'">
            <PresenceRail
              v-if="railMounted"
              v-show="railShown"
              ref="railRef"
              :entries="store.view.presenceEntries"
              :art-panel="panel('art')"
              :motion-level="store.view.motionLevel"
              :inert="!railShown || null"
              @activate="onRailActivate"
              @hover="onRailHover"
              @tab="onRailTab"
            />
          </Transition>
        </template>
        <!-- The lower-left dock carries conditions and vitals only. -->
        <template #vitals>
        <StatusPanel
          v-if="panelAvailable('status')"
          :status="panel('status') || {}"
          :low-hp="store.view.vitals.lowHp"
          :visible="store.view.mode !== 'dialogue' && store.view.vitals.visible"
          :motion-level="store.view.motionLevel"
          :revision="store.view.revision"
          :epoch="store.view.epoch"
          :display-hp="playerDisplayHp"
        />
      </template>
      <!-- The `map` anchor (webclient-avg-stage-hud-anchors design D1/D4),
           at the stage's top-right, in this order: the minimap island, the
           one-line objective (exploration only), and the title ballot. It is
           not rendered in combat, where the formation stands in the right
           column (webclient-combat-formation D2). No reference panel lives
           here; they are drawers. -->
      <template #map>
        <!-- The minimap island (H2, design D9); hidden in combat. The
             `@move` wiring and `explore.move` submission are untouched. -->
        <LocalMap
          v-if="store.view.localMapModel"
          :local-map="store.view.localMapModel"
          :aimed-node="aimedNode"
          :motion-level="store.view.motionLevel"
          @move="onMapMove"
          @open-map="onMapExpand"
        />
        <!-- The objective line (design D2): the first tracked objective and
             a `+N` count, directly under the minimap. -->
        <ObjectiveTracker
          v-if="showObjectiveTracker"
          :rows="store.objectivesRows"
        />
        <!-- The epithet nomination ballot menu (title-epithet-nomination):
             mounted only while the committed `title_ballot` panel carries
             candidates; answering consumes the ballot and the targeted
             panel update unmounts it. -->
        <TitleBallotMenu
          v-if="titleBallotCandidates.length > 0"
          :ballot="titleBallotPanel"
          @accept="onTitleBallotAction"
          @decline="onTitleBallotAction"
        />
      </template>
      <template #action-dock>
        <ActionDock
          v-if="rootItems.length > 0 || !!store.view.degradedRoot || (store.view.mode !== 'creation' && !!store.view.dockSource) || (store.view.mode === 'creation' && panelAvailable('creation'))"
          :mode="store.view.mode || 'exploration'"
          :root-items="rootItems"
          :tab-stop="!(store.view.mode === 'exploration' && explorationRootShown)"
          :view="store.view"
          :playback="store.view.mode === 'combat' && !!store.view.dispatch.beatLocked"
          :card="store.view.mode === 'combat'"
          :stage-target="store.view.mode === 'combat' ? stageTarget : null"
          :inert="crossSideOpen || null"
          @action="onAction"
          @target-pointer="onTargetPosition"
          @back="onDockBack"
          @skip="store.skipBeats"
        >
          <div
            class="dock-pane-host"
            :class="{
              'dock-pane-host--bounded': contextActionsPanel?.kind === 'combat' || skillUseDockShown,
              'dock-pane-host--exploration': explorationRootShown,
            }"
          >
            <!-- The exploration dock's root pane (exploration-exit-compass
                 design D5; exploration-room-actions design D2): the exit
                 compass on the left, filling the panel height, and a right
                 column holding the 建議 pill at its top and the shared
                 readout at its bottom. The room actions are the place
                 card's, and the people and objects the presence rail's; the
                 panel holds no chip row, footer, or key hint. -->
            <div
              v-if="explorationRootShown"
              class="exploration-root"
              data-testid="exploration-root"
            >
              <div class="exploration-root__compass" @keydown="onCompassTab">
                <ExitCompass
                  ref="compassRef"
                  :targets="compassTargets"
                  :busy="compassBusy"
                  :arrival-key="compassArrivalKey"
                  :active="compassActive"
                  :motion-level="store.view.motionLevel"
                  @aim="onCompassAim"
                  @blocked="onCompassBlocked"
                  @move="onCompassMove"
                />
              </div>
              <div class="exploration-root__side">
                <button
                  v-if="pillShown"
                  type="button"
                  class="exploration-pill"
                  data-testid="suggestions-pill"
                  :aria-label="pillLabel"
                  :data-count="pillCount > 0 ? pillCount : null"
                  @click="onPill"
                  @keydown.enter.stop
                  @keydown.space.stop
                  @keydown="onPillTab"
                  @mouseenter="onPillHoverChange(true)"
                  @mouseleave="onPillHoverChange(false)"
                  @focus="onPillHoverChange(true)"
                  @blur="onPillHoverChange(false)"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z" />
                  </svg>
                  <span class="exploration-pill__label">建議</span>
                  <b v-if="pillCount > 0" class="exploration-pill__count">{{ ` ${pillCount}` }}</b>
                </button>
                <ExplorationReadout
                  class="exploration-root__readout"
                  :lead="readoutContent.lead"
                  :text="readoutContent.text"
                  :tone="readoutContent.tone"
                  :flash="readoutContent.flash"
                  :motion-level="store.view.motionLevel"
                />
              </div>
            </div>
            <!-- The SkillBook casting flow (skillbook-authoritative-casting):
                 the book handed casting to the dock; its frames render here
                 with their own detail card. -->
            <SkillUseDock
              v-else-if="skillUseDockShown"
              :menu="store.view.combatMenu"
              :focused-key="store.view.focus.key"
              :detail="store.view.skillUse"
              :locked="!!store.view.dispatch.inFlight"
              @focus-change="onDockFocusChange"
              @activate="onDockActivate"
            />
            <DockMenu
              v-else-if="dockItems.length && !(store.view.dockDepth === 1 && dockPaneKind === 'plain' && !store.view.degradedRoot)"
              :items="dockItems"
              :focused-key="store.view.focus.key"
              :id-prefix="rowPrefix"
              :detail-test-id="detailTestId"
              :show-detail="showDetail"
              :grid-cols="store.view.combatMenu ? store.view.combatMenu.gridCols : null"
              :depth="store.view.dockDepth"
              :hide-generic-detail="!!store.view.focusedSkill"
              @focus-change="onDockFocusChange"
              @activate="onDockActivate"
            />
            <SkillDetailPane
              v-if="store.view.focusedSkill"
              :skill="store.view.focusedSkill"
              :selected="store.view.combatSelected"
              :scales="store.view.focusedSkill.freeformScales || []"
              :scale="store.view.focusedSkill.scale || 1"
              :focus-key="store.view.focus.key"
              @choose-scale="(p) => store.chooseScale(p.scale)"
              @choose-shorthand="(p) => store.chooseShorthand(p.shorthand)"
            />
          </div>
        </ActionDock>
      </template>
    </AppShell>

    <!-- H4 (task 7.4): the reference-drawer layer, mounted above the
         stage. A single `HudDrawer` chrome hosts the drawer body for the
         store's single open-drawer name; only the open drawer's surface is
         in the DOM (task 7.7: no reference surface while closed). -->
    <!-- The NPC author editor (npc-persona-editor-window) owns its drawer
         chrome: it binds to the target captured at 編輯人物設定 and guards a
         dirty close. -->
    <DreamPanel v-if="panel('dream')?.state?.open" :state="panel('dream').state" :store="store" />
    <NpcPersonaEditor
      v-if="store.view.hudDrawer === 'npc_persona' && npcPersonaEditor.open"
      :editor="npcPersonaEditor"
      @input="npcPersonaSetField"
      @save="npcPersonaSave"
      @reload="npcPersonaReload"
      @discard="npcPersonaDiscard"
      @retry="npcPersonaRetry"
      @close="npcPersonaClose"
    />
    <HudDrawer
      v-if="store.view.hudDrawer && store.view.hudDrawer !== 'npc_persona'"
      :open="true"
      :title="practiceOpen && store.view.hudDrawer === 'skill' ? '修煉' : drawerTitle"
      :subtitle="store.view.hudDrawer === 'inventory' ? inventoryWalletSubtitle : (store.view.hudDrawer === 'skill' ? skillBookSubtitle : (store.view.hudDrawer === 'party' ? `${(store.partySlots || []).length} / 4` : ''))"
      :icon="drawerIcon"
      :drawer-key="store.view.hudDrawer"
      :body-flush="store.view.hudDrawer === 'quest'"
      @close="onHudDrawerClose"
    >
      <!-- Only a drawer about the current character stands its portrait
           beside the content (webclient-drawer-content-polish); the other
           drawers provide no art slot and take the whole workspace. -->
      <template v-if="drawerHasArt" #art>
        <ReferenceArtwork
          :artwork="currentArtwork"
          :panel="panel('roster')"
          :name="currentCharacter?.name || ''"
          :initial-of="currentCharacter?.name || ''"
          stage
        />
      </template>
      <LettersPanel v-if="store.view.hudDrawer === 'letters'" :store="store" />
      <SkillBook
        v-else-if="store.view.hudDrawer === 'skill'"
        :skills="panel('character') || {}"
        :practice-disabled="skipDisabled"
        :practice-feedback="practiceFeedback"
        :mode="store.view.mode || 'exploration'"
        :use-locked="skillUseLocked"
        :use-pending-key="store.view.skillUsePendingKey"
        :use-notice="store.view.skillUseNotice"
        :return-target="store.view.bookReturn"
        @practice="onPractice"
        @practice-view="(open) => practiceOpen = open"
        @use="onSkillUse"
      />
      <InventoryPanel
        v-else-if="store.view.hudDrawer === 'inventory'"
        :services="panel('services') || {}"
        :character="panel('character')"
        :wallet="inventoryWalletCopper"
        @use="onInventoryItemAction"
        @toggle-equip="onInventoryItemAction"
      />
      <ShopPanel
        v-else-if="store.view.hudDrawer === 'shop'"
        :services="panel('services') || {}"
        @buy="onShopBuy"
        @sell="onShopSell"
      />
      <QuestDrawer
        v-else-if="store.view.hudDrawer === 'quest'"
        :quest-log="panel('quest_log')"
        :services="panel('services')"
        :memory-scope="`${store.view.generation}|${store.view.epoch}`"
        @action="onQuestAction"
      />
      <LoreCodexDrawer v-else-if="store.view.hudDrawer === 'lore'" :codex="panel('lore_codex')" />
      <CharacterStatusDrawer
        v-else-if="store.view.hudDrawer === 'status'"
        :status="panel('status') || {}"
        :character="panel('character') || {}"
        :low-hp="store.view.vitals.lowHp"
        :party-available="store.partyAvailable"
        @open-party="() => store.openHudDrawer('party')"
        @open-skill="() => store.openHudDrawer('skill')"
        @persona-edit="onPersonaEdit"
      />
      <PartyDrawer
        v-else-if="store.view.hudDrawer === 'party'"
        :slots="store.partySlots"
        :combat-participants="store.combatParticipants"
        :art-panel="panel('art')"
        :interact-targets="store.explorationInteract"
        :mode="store.view.mode || 'exploration'"
        :available="store.partyAvailable"
        :reason="partyReason"
        :release-affordance="releaseAffordance"
        :affordances="contextAffordances"
        @action="onAction"
        @close="onHudDrawerClose"
      />
      <!-- The book's keyboard guidance is skill-drawer-only and absent while
           the practice sub-screen replaces the book: a conditional named slot,
           so the other drawers provide no `foot` slot and render no footer. -->
      <template v-if="store.view.hudDrawer === 'skill' && !practiceOpen" #foot>
        <p class="hud-drawer__key-hint" data-testid="skill-book-key-hint">{{ SKILL_BOOK_KEY_HINT }}</p>
      </template>
    </HudDrawer>

    <!-- H5 (tasks 5.4/6.4): the single shared full-screen overlay surface.
         The host owns the geometry, the focus trap, the Escape handling and
         the labelled close control; the three stripped overlay bodies mount
         inside its body slot. An open overlay registers into `openSurfaces`
         so the stage recession applies without a second mechanism. The
         creation overlay is mode-driven and stays outside this single-open
         stack (task 5.5). -->
    <OverlayHost
      v-if="store.view.hudOverlay"
      :overlay="store.view.hudOverlay"
      :opener="store.view.hudOverlayOpener"
      :map-model="store.view.localMapModel"
      :location-label="store.view.statusSlice.locationLabel"
      @close="onOverlayClose"
      @move="onMapMove"
    >
      <template #default="{ overlay: openName, mapModel }">
        <MapOverlay
          v-if="openName === 'map'"
          :local-map="mapModel || store.view.localMapModel || {}"
          @move="onMapMove"
          @open-map="onMapExpand"
        />
        <SettingsOverlay
          v-else-if="openName === 'settings'"
          :font-scale="store.view.fontScale"
          :text-to-html="store.view.textToHtml"
          :motion-level="store.view.motionLevel"
          :colorblind="store.view.colorblind"
          :text-speed="store.view.textSpeed"
          :auto-advance="store.view.autoAdvance"
          @scale-change="store.setFontScale"
          @text-html-change="store.setTextToHtml"
          @motion-level-change="store.setMotionLevel"
          @colorblind-change="store.setColorblind"
          @text-speed-change="store.setTextSpeed"
          @auto-advance-change="store.setAutoAdvance"
        />
        <!-- skill-lineage-panel (task 2.3): the big-window ledger renders the
             committed `lineage` panel verbatim — expanded chains carry per-node
             meters, collapsed chains their aggregate meter; the client
             computes no growth rules. -->
        <LineagePanel v-else-if="openName === 'lineage'" :lineage="panel('lineage')" />
        <!-- title-codex-removal: the big-window codex renders the committed
             `title_codex` panel verbatim — the server's `can_remove` flag
             alone decides whether a 移除 control exists; the client owns no
             gate rule and no 卸裝 control. -->
        <TitleCodexPanel
          v-else-if="openName === 'codex'"
          :codex="panel('title_codex')"
          @action="onTitleCodexAction"
        />
        <GalleryPanel
          v-else-if="openName === 'gallery'"
          :model="panel('gallery')"
          :disabled="!store.view.connected || store.view.mutationsLocked || store.view.dispatch.inFlight !== null"
          :dispatch="dispatchIntent"
          :result="store.view.lastActionResult"
          :revision="store.view.revision"
          @character="store.openHudDrawer('status')"
          @log="openFullLog"
        />
        <!-- The help surface renders the client-owned control reference and
             the statement of how the game's own `help` output is reached —
             no invented copy. -->
        <HelpOverlay v-else />
      </template>
    </OverlayHost>

    <CreationOverlay
      v-if="panelAvailable('creation')"
      :creation="panel('creation')"
      :result="store.view.lastActionResult"
      :stage="store.view.creationView"
      :dispatch="onCreationDispatch"
      :dispatch-state="store.view.dispatch"
      :push-toast="store.pushToast"
      @action="onCreationAction"
      @request-reset="onCreationRequestReset"
      @cancel-confirm="onCreationCancelConfirm"
    />

    <!-- The full-log surface (design D4): the complete retained narrative,
         reachable in one action from the caption card's control; focus-
         trapped, Escape-closing, with focus restored to the opener. -->
    <FullLogOverlay
      v-if="fullLogOpen"
      ref="fullLogRef"
      :lines="store.narrative"
      :style="store.view.hudOverlay === 'gallery' ? { zIndex: 3100 } : null"
      @close="closeFullLog(true)"
    />

    <!-- The action-feedback toast queue (webclient-action-feedback D2): the
         LAST child of the client root so equal-tier surfaces stack above the
         overlays; the component owns its fixed modal-tier z-index. Always
         mounted — it renders nothing while the store's queue is empty. -->
    <ToastQueue :toasts="store.view.toasts" @dismiss="store.dismissToast" />
  </div>
</template>

<style>
/* The dialogue host's entrance (webclient-mode-transitions D3; AVG stage
   design §9.3): the figure walks in from the right edge of the stage. It
   starts a beat after the command panel begins to leave, so the eye reads
   the band clearing first and the host arriving second; it decelerates into
   place while its opacity rises a little faster than it moves, so no
   half-transparent body hangs in the air. Leaving mirrors it: an
   accelerating slide back out while it thins. Every distance is multiplied
   by the travel token and the beat scales with it, so the reduced level is
   a plain fade and the off level has no CSS phase at all. The leaving copy
   is lifted onto the anchor's box, so a host handing over to another never
   stacks two figures in flow. */
[data-anchor="actor-right"] > .actor-enter-enter-active {
  transition:
    opacity calc(var(--motion-actor) * 0.8) var(--ease-standard) calc(var(--motion-panel) * 0.24 * var(--motion-travel)),
    transform var(--motion-actor) var(--ease-enter) calc(var(--motion-panel) * 0.24 * var(--motion-travel)),
    filter var(--motion-base) var(--ease-standard);
}
[data-anchor="actor-right"] > .actor-enter-leave-active {
  position: absolute;
  inset: 0;
  transition:
    opacity var(--motion-actor) var(--ease-standard),
    transform var(--motion-actor) var(--ease-exit),
    filter var(--motion-base) var(--ease-standard);
}
[data-anchor="actor-right"] > .actor-enter-enter-from,
[data-anchor="actor-right"] > .actor-enter-leave-to {
  opacity: 0;
  transform: translateX(calc(var(--motion-shift-lg) * 1.5 * var(--motion-travel)));
}

/* The presence rail fades as a whole when it leaves or returns to the stage
   (a card opens or closes, the mode changes); its entries fade on their own
   (PresenceRail). */
.presence-rail-fade-enter-active,
.presence-rail-fade-leave-active {
  transition: opacity var(--motion-reveal) var(--ease-standard);
}
.presence-rail-fade-enter-from,
.presence-rail-fade-leave-to {
  opacity: 0;
}

/* The foe line-up's entrance (webclient-combat-foes-on-stage D3; AVG stage
   design §9.3 "foes enter"): the row emerges as the combat flash releases —
   it waits half the flash, then fades in while each foe decelerates in from
   the right, the front foe travelling furthest (parallax). The row and its
   foes share one duration and delay, so Vue, which times the transition on
   the row alone, never ends a foe's slide early. Leaving combat, the row
   fades while the foes drift a step back out. Every distance and the delay
   scale with the travel and flash tokens, so `reduced` is a plain fade and
   `off` has no CSS phase at all. */
[data-anchor="actor-right"] > .foes-enter-enter-active {
  transition: opacity var(--motion-actor) var(--ease-standard) calc(var(--motion-flash) * 0.5);
}
[data-anchor="actor-right"] > .foes-enter-enter-active > .foe-lineup__slot {
  transition: transform var(--motion-actor) var(--ease-enter) calc(var(--motion-flash) * 0.5);
}
[data-anchor="actor-right"] > .foes-enter-enter-from > .foe-lineup__slot {
  transform: translateX(calc(var(--motion-shift-lg) * (1.5 - 0.25 * var(--foe-index, 0)) * var(--motion-travel)));
}
[data-anchor="actor-right"] > .foes-enter-leave-active {
  transition: opacity var(--motion-actor) var(--ease-exit);
}
[data-anchor="actor-right"] > .foes-enter-leave-active > .foe-lineup__slot {
  transition: transform var(--motion-actor) var(--ease-exit);
}
[data-anchor="actor-right"] > .foes-enter-leave-to > .foe-lineup__slot {
  transform: translateX(calc(var(--motion-shift-sm) * var(--motion-travel)));
}
[data-anchor="actor-right"] > .foes-enter-enter-from,
[data-anchor="actor-right"] > .foes-enter-leave-to {
  opacity: 0;
}

/* The glance plates (webclient-combat-formation D4). The group spans the
   plates layer, so each plate's slot is in stage pixels. A re-formed line
   glides each plate with its figure (the slots' own duration and easing);
   on a resize, a reconnect and below `full` it moves in place. A plate rises
   out of its anchored foot and fades in once its figure has landed (after
   the travel duration), and fades where it stands when its figure leaves;
   `reduced` keeps only the fade and `off` has no CSS phase at all. */
.figure-plates {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.figure-plates[data-glide="true"] > .figure-plate {
  transition:
    left calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    top calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    width calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    height calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard);
}
.figure-plates > .figure-plate-enter-active {
  transition:
    opacity var(--motion-actor) var(--ease-standard) calc(var(--motion-actor) * var(--motion-travel)),
    transform var(--motion-actor) var(--ease-enter) calc(var(--motion-actor) * var(--motion-travel));
}
.figure-plates > .figure-plate-leave-active {
  transition: opacity var(--motion-actor) var(--ease-exit);
}
.figure-plates > .figure-plate-enter-from {
  opacity: 0;
  transform: translateY(calc(var(--motion-shift-sm) * 0.5 * var(--motion-travel)));
}
.figure-plates > .figure-plate-leave-to {
  opacity: 0;
}

/* The stage target step's arrow markers (webclient-combat-stage-target-
   picking D4). The layer spans the plates anchor and takes no pointer; each
   marker is a 24px·S pointer target at its figure's marker slot. The arrow
   is a gold shield pointing down at the figure: outlined while selectable,
   filled, larger and glowing on a lit figure, its digit inside. At `full`
   the focused arrow bobs on the page marker's loop; below it stands still
   and an underline bar marks it. */
/* The cross-side question (webclient-combat-cross-side-confirm D3): the card
   stands in the choices anchor's column below the collapsed command card
   (`order` places it after the card host whatever the DOM order), centred on
   the stage and vertically centred in the span the prompt leaves free, so it
   never covers the prompt that names the skill and the focused target. It is
   a little wider than the column (a centred flex item overflows both sides
   equally), so the question sets on one or two balanced lines. While it is
   open no figure's hit area, arrow marker or prompt chip takes a pointer, so
   no click or hover behind it moves the step. */
.elosern-stage[data-elosern-mode="combat"] [data-anchor="choices"] > .cross-side-question {
  order: 1;
  position: relative;
  z-index: 2;
  flex: none;
  align-self: center;
  width: calc(336px * var(--ui-scale));
  max-height: none;
  margin: auto 0;
  box-shadow:
    var(--shadow-lg),
    0 0 0 calc(1px * var(--ui-scale)) rgba(0, 0, 0, 0.5),
    0 calc(18px * var(--ui-scale)) calc(48px * var(--ui-scale)) calc(-8px * var(--ui-scale)) rgba(0, 0, 0, 0.85),
    inset 0 0 0 1px rgba(0, 0, 0, 0.55);
}
/* The inert card beneath recedes, so the question is the one surface that
   reads as live. */
.elosern-root[data-cross-side-open="true"] #action-dock {
  opacity: 0.45;
  filter: saturate(0.6);
  transition: opacity var(--motion-fast) var(--ease-standard), filter var(--motion-fast) var(--ease-standard);
}
.elosern-root[data-cross-side-open="true"] .stage-target__hit,
.elosern-root[data-cross-side-open="true"] .stage-target__marker,
.elosern-root[data-cross-side-open="true"] .target-prompt__chip {
  pointer-events: none;
}
.stage-target-markers {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.stage-target__marker {
  position: absolute;
  box-sizing: border-box;
  display: grid;
  place-items: center;
  pointer-events: auto;
  cursor: pointer;
  color: var(--gold-300);
  transform-origin: 50% 100%;
}
.stage-target__arrow {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  fill: rgba(16, 12, 9, 0.62);
  stroke: var(--gold-400);
  stroke-width: 1.6;
  stroke-linejoin: round;
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.7));
}
.stage-target__digit {
  position: relative;
  margin-top: -18%;
  font: 600 calc(11px * var(--ui-scale)) / 1 var(--f-mono);
  letter-spacing: 0;
  color: var(--gold-300);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8);
}
.stage-target__marker[data-state="focus"] {
  z-index: 1;
  transform: scale(1.3);
  animation: elosern-target-marker-bob var(--motion-marker-bob) ease-in-out infinite alternate;
}
.stage-target__marker[data-state="focus"] .stage-target__arrow {
  fill: #e9c97f;
  stroke: #fff4d6;
  stroke-width: 1.2;
  filter:
    drop-shadow(0 0 calc(4px * var(--ui-scale)) rgba(255, 226, 150, 0.9))
    drop-shadow(0 1px 1px rgba(0, 0, 0, 0.6));
}
.stage-target__marker[data-state="focus"] .stage-target__digit {
  color: var(--target-marker-ink);
  text-shadow: none;
}
.stage-target__check {
  position: absolute;
  right: -34%;
  top: -30%;
  display: grid;
  place-items: center;
  width: 62%;
  height: 62%;
  border-radius: 50%;
  background: #2f6b46;
  border: 1px solid #b9e6c4;
  color: #f3fff6;
  font: 700 calc(10px * var(--ui-scale)) / 1 var(--f-sans);
  font-style: normal;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
}
.stage-target__marker[data-target-motion="static"][data-state="focus"] {
  animation: none;
}
.stage-target__marker[data-target-motion="static"][data-state="focus"]::after {
  content: "";
  position: absolute;
  left: 14%;
  right: 14%;
  bottom: -22%;
  height: 2px;
  border-radius: 1px;
  background: #fff1cc;
  box-shadow: 0 0 calc(4px * var(--ui-scale)) rgba(255, 226, 150, 0.9);
}
@keyframes elosern-target-marker-bob {
  from { transform: scale(1.3) translateY(calc(-1 * var(--motion-marker-travel) * var(--motion-travel))); }
  to { transform: scale(1.3) translateY(calc(var(--motion-marker-travel) * var(--motion-travel))); }
}
@media (prefers-reduced-motion: reduce) {
  :root:not([data-motion]) .stage-target__marker[data-state="focus"] {
    animation: none;
  }
  :root:not([data-motion]) .stage-target__marker[data-state="focus"]::after {
    content: "";
    position: absolute;
    left: 14%;
    right: 14%;
    bottom: -22%;
    height: 2px;
    background: #fff1cc;
  }
}

/* Carry the mount container's viewport height down to the shell so the
   shell grid's 1fr row clamps to the available space (the root div broke
   the 100% height chain, letting the shell grow to its content height). */
.elosern-root {
  height: 100%;
  width: 100%;
}

/* H3 (task 6.4): the skill master-detail layout — the skill list and the
   detail pane sit side by side inside the dock pane (the draft's `.skwrap`
   two-column grid, adapted to a flex row that fits the bounded pane). */
.dock-pane-host {
  display: flex;
  gap: calc(12px * var(--ui-scale));
  flex: 1;
  min-height: 0;
  align-items: flex-start;
}

/* The exploration root pane (exploration-exit-compass design D5;
   exploration-room-actions design D2): the compass fills the pane's height on
   the left; the right column holds the 建議 pill at its top right and the
   shared readout at its bottom, so the pane (and the command panel's box)
   never grows. */
.dock-pane-host.dock-pane-host--exploration {
  align-items: stretch;
  height: 100%;
}
.exploration-root {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: calc(10px * var(--ui-scale));
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
}
/* The compass column is as wide as the pane is tall: the pad is a square
   sized to the band height minus the pane's padding (about 198 px at
   1451x790). */
.exploration-root__compass {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 0;
  aspect-ratio: 1 / 1;
}
.exploration-root__side {
  display: flex;
  flex-direction: column;
  gap: calc(8px * var(--ui-scale));
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.exploration-root__readout {
  margin-top: auto;
}

/* The 建議 pill (redesign §5.2): a quiet outlined pill at the column's top
   right; the count in the gold numeral tone. */
.exploration-pill {
  align-self: flex-end;
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: calc(6px * var(--ui-scale));
  box-sizing: border-box;
  height: calc(34px * var(--ui-scale));
  padding: 0 calc(12px * var(--ui-scale)) 0 calc(10px * var(--ui-scale));
  background: transparent;
  border: 1px solid #736b5c;
  border-radius: var(--radius-pill);
  color: var(--paper-200);
  font: var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.06em;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.exploration-pill svg {
  flex: none;
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
}
.exploration-pill__count {
  font-weight: 500;
  color: var(--gold-300);
}
.exploration-pill:hover,
.exploration-pill:focus-visible {
  border-color: var(--gold-500);
  background: var(--gold-glow);
  color: var(--paper-50);
  outline: none;
}
.exploration-pill:focus-visible {
  box-shadow: 0 0 0 1px var(--gold-400);
}

/* The wait card's rest form (exploration-room-actions design D5): the
   bounded RestForm in the centred card frame. */
.rest-card {
  align-self: center;
  width: min(100%, calc(360px * var(--ui-scale)));
  padding: 0 calc(14px * var(--ui-scale)) calc(14px * var(--ui-scale));
  gap: calc(8px * var(--ui-scale));
}
.rest-card .exploration-rest-form {
  background: transparent;
  border: 0;
  padding: calc(4px * var(--ui-scale)) calc(6px * var(--ui-scale)) 0;
}
</style>
