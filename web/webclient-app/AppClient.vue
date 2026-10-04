<script setup>
// C3 (webclient-vue-09-wire-transport-mount): the store-bound live renderers
// (design D3: passive, emit only user-intent dispatches). Every surface
// reads the C1 store's committed slices; panels render only when their
// backing OOB read model is present (the truthful-data scope, roadmap §7 —
// no surface is invented for a panel without a backing model). The behavior
// groups live in ./composables/ (each watch stays with the state it mutates).
import { computed, ref, watch } from "vue";
import { useElosernStore } from "./stores/elosern.js";
import { useAppClient } from "./composables/use-app-client.js";
import AppShell from "./components/AppShell.vue";
import ActionDock from "./components/ActionDock.vue";
import CreationOverlay from "./components/CreationOverlay.vue";
import DockMenu from "./components/DockMenu.vue";
import DockVerbPopover from "./components/DockVerbPopover.vue";
import ParticipantFrame from "./components/ParticipantFrame.vue";
import SkillDetailPane from "./components/SkillDetailPane.vue";
import SceneOverview from "./components/SceneOverview.vue";
import FullLogOverlay from "./components/FullLogOverlay.vue";
import CharacterStatusDrawer from "./components/CharacterStatusDrawer.vue";
import HudDrawer from "./components/HudDrawer.vue";
import InventoryPanel from "./components/InventoryPanel.vue";
import LocalMap from "./components/LocalMap.vue";
import LoreCodexDrawer from "./components/LoreCodexDrawer.vue";
import MapOverlay from "./components/MapOverlay.vue";
import RestForm from "./components/RestForm.vue";
import GuildCounter from "./components/GuildCounter.vue";
import QuestLog from "./components/QuestLog.vue";
import SceneBackdrop from "./components/SceneBackdrop.vue";
import SettingsOverlay from "./components/SettingsOverlay.vue";
import ShopPanel from "./components/ShopPanel.vue";
import TitleBallotMenu from "./components/TitleBallotMenu.vue";
import SkillBook from "./components/SkillBook.vue";
import StatusPanel from "./components/StatusPanel.vue";
import OverlayHost from "./components/OverlayHost.vue";
import HelpOverlay from "./components/HelpOverlay.vue";
import LineagePanel from "./components/LineagePanel.vue";
import TitleCodexPanel from "./components/TitleCodexPanel.vue";
import GalleryPanel from "./components/GalleryPanel.vue";
import NpcPersonaEditor from "./components/NpcPersonaEditor.vue";
import LettersPanel from "./components/LettersPanel.vue";
import ToastQueue from "./components/ToastQueue.vue";
import CompanionLineup from "./components/CompanionLineup.vue";
import { companionFigures } from "./components/companion-lineup.js";
import { portraitFor } from "./components/party-helpers.js";
import PartyDrawer from "./components/PartyDrawer.vue";
import ObjectiveTracker from "./components/ObjectiveTracker.vue";
import DesktopNavigation from "./components/DesktopNavigation.vue";
import ReferenceArtwork from "./components/ReferenceArtwork.vue";
import StageActor from "./components/StageActor.vue";
import FoeLineup from "./components/FoeLineup.vue";
import { FOE_LINEUP_MAX, activeFoes, foeLineupSpan, foeSlots } from "./components/foe-lineup.js";
import DialogueChoices from "./components/DialogueChoices.vue";
import { inertWhileLeaving } from "./lib/transition_hooks.js";

const store = useElosernStore();
const currentCharacter = computed(
  () => store.view.rosterCharacters?.find((character) => character.current) ?? null,
);
const currentPortrait = computed(() => currentCharacter.value?.portrait ?? null);
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
  restFormOpen, restFormError, onRestFormSubmit, onRestFormClose, onRestFormError,
  waitOpen, skipDisabled, activateWait, practiceOpen, practiceFeedback, onPractice,
  fullLogOpen, fullLogRef, openFullLog, closeFullLog, openSurfaces,
  openOverlayByName, onOpenOverlay, onMapExpand, onOverlayClose,
  drawerTitle, drawerIcon, drawerHasArt, onOpenDrawer, onHudDrawerClose, questServicesPanel,
  questGuildAvailable, questServicesUnavailable, skillBookSubtitle,
  inventoryWalletCopper, inventoryWalletSubtitle, partyReason, SKILL_CAST_HINT,
  rootItems, navigationItems, dockItems, dockPaneKind,
  overviewShown, overviewActive, overviewMenu, overviewFocusKey,
  onTabClick, onDockBack, contextActionsPanel, rowPrefix, detailTestId,
  showDetail,
  onAction, onDockActivate, onDockFocusChange,
  onShopBuy, onShopSell, onInventoryItemAction, onTitleBallotAction, onTitleCodexAction,
  onCreationAction, onCreationDispatch, onCreationRequestReset, onCreationCancelConfirm,
  onQuestAction, onPersonaEdit, onSubmitCommand, onSwitchCharacter, onCreateCharacter,
  npcPersonaEditor, npcPersonaSetField, npcPersonaSave, npcPersonaReload, npcPersonaDiscard,
  npcPersonaRetry, npcPersonaClose,
} = useAppClient(store, shellRef, sceneBackdropRef);
// The dialogue host's standing portrait (webclient-dialogue-stage-actors
// D2): the committed `art` panel's raw catalog entry named by the committed
// `dialogue` panel's `host.portrait_ref` — the raw entry, so a pending entry
// shows its own placeholder card; a null or unknown key falls to the
// StageActor's name placeholder. The client never builds a catalog key.
const hostPortrait = computed(() => {
  const key = dialogueVM.value?.host.portraitRef;
  return key == null ? null : (panel("art")?.portrait_catalog?.[key] ?? null);
});
const hostAlreadyInLineup = computed(() =>
  !!dialogueVM.value && companionLineupSlots.value.some((slot) => String(slot.identity) === String(dialogueVM.value.host.identity)),
);
const isControllingCompanion = computed(() => !!possessionBanner.value?.available);
const companionLineupSlots = computed(() => companionFigures({
  player: {
    identity: currentCharacter.value?.identity,
    portrait: currentPortrait.value,
    displayName: currentCharacter.value?.name || panel("status")?.actor?.name || "",
  },
  companions: store.partyAvailable ? store.partySlots : [],
  actorIdentity: panel("status")?.actor?.identity,
  possessing: isControllingCompanion.value,
  controlledName: possessionBanner.value?.host_name || "",
  artPanel: panel("art"), portraitFor,
}));
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
// The foe line-up (webclient-combat-foes-on-stage D1/D3): the committed
// combat panel's active foes, in presenter order, stand in `actor-right`
// while the mode is combat. It enters and leaves on the same live-only rule
// as the host (`hostTransitionCss`).
const combatFoes = computed(() =>
  contextActionsPanel.value?.kind === "combat" ? activeFoes(contextActionsPanel.value.participants) : [],
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
// How far the row reaches left of the anchor, in anchor widths, and its
// front foe's scale (which sets the row's inset), exposed on the client root
// as `--foe-lineup-span` and `--foe-front-scale` so the scene caption stays
// clear of it (styles/app-shell.css). A row that grows takes its room at
// once; a row that shrinks (a foe fell or fled) keeps its room until the
// leaving foe has faded; and a row that leaves the stage keeps it until the
// whole row has faded, so the caption never slides under a fading figure.
const foeLineupCount = computed(() => (foesOnStage.value ? Math.min(lineupFoes.value.length, FOE_LINEUP_MAX) : 0));
const foeLineupReach = ref({ span: 0, front: 1 });
function reachFor(count) {
  return count > 0 ? { span: foeLineupSpan(count), front: foeSlots(count)[0].scale } : { span: 0, front: 1 };
}
watch(
  foeLineupCount,
  (count) => {
    const next = reachFor(count);
    if (count > 0 && next.span >= foeLineupReach.value.span) {
      foeLineupReach.value = next;
    }
  },
  { immediate: true },
);
function onFoeLineupSettled() {
  foeLineupReach.value = reachFor(foeLineupCount.value);
}
function onFoeLineupGone() {
  if (!foesOnStage.value) {
    foeLineupReach.value = reachFor(0);
  }
}
</script>

<template>
  <div
    class="elosern-root"
    data-testid="elosern-client-root"
    :style="{ '--foe-lineup-span': foeLineupReach.span, '--foe-front-scale': foeLineupReach.front }"
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
        :epoch="store.view.epoch"
        :possession-banner="possessionBanner"
        @submit-command="onSubmitCommand"
        @focus-lost="store.clearFreeformTarget()"
        @open-full-log="openFullLog"
        @reading-change="onReadingChange"
        @beat-shown="store.beatShown"
        @beat-skip="store.skipBeats"
        @switch-character="onSwitchCharacter"
        @create-character="onCreateCharacter"
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
            :speaking-identity="inDialogue && dialogueVM && store.view.dialogueSpeaker === 'host' ? panel('dialogue')?.host?.identity : null"
            :dimmed="inDialogue && !!dialogueVM && store.view.dialogueSpeaker === 'host'"
            :motion-level="store.view.motionLevel"
            :gesture="playerGesture?.gesture ?? null"
            :gesture-key="beatStage?.key ?? null"
            :float-amount="playerGesture?.amount ?? null"
          />
        </template>
        <!-- The dialogue host's standing portrait (webclient-dialogue-stage-
             actors D2): only while the mode is dialogue and the committed
             panel is available; empty in every other state. -->
        <template #actor-right>
          <!-- The host enters from the right and leaves to it
               (webclient-mode-transitions D3), keyed by identity so a new
               host during a session hands over; a new portrait for the same
               host is StageActor's own crossfade. -->
          <Transition name="actor-enter" :css="hostTransitionCss" v-bind="inertWhileLeaving">
            <StageActor
              v-if="inDialogue && dialogueVM && !hostAlreadyInLineup"
              :key="dialogueVM.host.identity"
              side="right"
              :portrait="hostPortrait"
              :name="dialogueVM.host.displayName"
              :dimmed="store.view.dialogueSpeaker === 'player'"
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
              :display-hp="store.view.displayHp"
              :focused-target="focusedCombatTarget"
              :inert="beatHold || null"
              :art-panel="panel('art')"
              :motion-level="store.view.motionLevel"
              @settled="onFoeLineupSettled"
            />
          </Transition>
        </template>
        <!-- The dialogue choice list (webclient-dialogue-choices-overlay
             D4/D5), centred over the stage: only in dialogue with the panel
             available, once the line is fully read, and never while an
             action is in flight. -->
        <template #choices>
          <DialogueChoices
            v-if="choicesShown"
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
           one-line objective (exploration only), the combat participant
           frame, and the title ballot. No reference panel lives here; they
           are drawers. -->
      <template #map>
        <!-- The minimap island (H2, design D9); hidden in combat. The
             `@move` wiring and `explore.move` submission are untouched. -->
        <LocalMap
          v-if="store.view.localMapModel"
          :local-map="store.view.localMapModel"
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
        <!-- The combat participant frame (H3, design D4): the minimap is
             hidden in combat, so the frame takes the top-right; it never
             stands on a portrait anchor. -->
        <ParticipantFrame
          v-if="contextActionsPanel && contextActionsPanel.kind === 'combat' && Array.isArray(contextActionsPanel.participants)"
          :participants="contextActionsPanel.participants"
          :art-panel="panel('art')"
          :display-hp="store.view.displayHp"
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
          v-if="rootItems.length > 0 || !!store.view.degradedRoot || !!store.view.suggestions || (store.view.mode === 'creation' && panelAvailable('creation'))"
          :mode="store.view.mode || 'exploration'"
          :root-items="rootItems"
          :view="store.view"
          :playback="store.view.mode === 'combat' && !!store.view.dispatch.beatLocked"
          @action="onAction"
          @back="onDockBack"
          @skip="store.skipBeats"
        >
          <div class="dock-pane-host" :class="{ 'dock-pane-host--bounded': contextActionsPanel?.kind === 'combat' }">
            <section v-if="waitOpen" class="waiting-screen" aria-label="等待與休息">
              <article class="waiting-card" :class="{ 'waiting-card--focused': store.view.focus.key === 'wait-dawn' }">
                <h3>等待直到黎明</h3>
                <p>等待下一次天亮，再展開旅程。</p>
                <button type="button" :disabled="skipDisabled" @keydown.enter.stop @keydown.space.stop @click="activateWait('wait-dawn')">等待直到黎明</button>
              </article>
              <article class="waiting-card" :class="{ 'waiting-card--focused': store.view.focus.key === 'wait-sleep' }">
                <h3>睡眠至完全恢復</h3>
                <p>依目前恢復速度睡眠，實際時長由伺服器決定，受睡眠上限限制。</p>
                <button type="button" :disabled="skipDisabled" @keydown.enter.stop @keydown.space.stop @click="activateWait('wait-sleep')">開始睡眠</button>
              </article>
              <article class="waiting-card" :class="{ 'waiting-card--focused': store.view.focus.key === 'wait-rest' }">
                <h3>休息 N 小時</h3>
                <RestForm :autofocus="restFormOpen" :disabled="skipDisabled" @submit="onRestFormSubmit" @close="onRestFormClose" @error="onRestFormError" />
              </article>
              <button type="button" class="waiting-back" @keydown.enter.stop @keydown.space.stop @click="onDockBack">返回上一層</button>
            </section>
            <!-- The exploration dock's root frame (webclient-scene-overview-
                 swap D4): one scene overview — chip rows for exits, people,
                 and objects, plus the footer. Under a target's verb popover
                 it stays rendered as inert ancestor chrome. -->
            <SceneOverview
              v-if="overviewShown"
              :menu="overviewMenu"
              :focused-key="overviewActive ? store.view.focus.key : overviewFocusKey"
              :local-map="store.view.localMapModel"
              :active="overviewActive"
              @focus-change="onDockFocusChange"
              @activate="onDockActivate"
            />
             <DockMenu
               v-else-if="!waitOpen && dockItems.length && !(store.view.dockDepth === 1 && dockPaneKind === 'plain' && !store.view.degradedRoot)"
               :items="dockItems"
              :focused-key="store.view.focus.key"
              :id-prefix="rowPrefix"
              :detail-test-id="detailTestId"
              :show-detail="showDetail"
              :detail-message="restFormError"
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
              @choose-scale="(p) => store.chooseScale(p.scale)"
              @choose-shorthand="(p) => store.chooseShorthand(p.shorthand)"
            />
          </div>
          <RestForm v-if="restFormOpen && !waitOpen" :disabled="skipDisabled" @submit="onRestFormSubmit" @close="onRestFormClose" @error="onRestFormError" />
          <!-- The target's verb popover (webclient-scene-overview-swap D4):
               a card inside the command region over the inert overview. -->
          <template #overlay>
            <DockVerbPopover
              v-if="store.view.dockSource === 'exploration.target'"
              :menu="store.view.combatMenu"
              :focused-key="store.view.focus.key"
              @focus-change="onDockFocusChange"
              @activate="onDockActivate"
              @back="onDockBack"
            />
          </template>
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
      @close="onHudDrawerClose"
    >
      <!-- Only a drawer about the current character stands its portrait
           beside the content (webclient-drawer-content-polish); the other
           drawers provide no art slot and take the whole workspace. -->
      <template v-if="drawerHasArt" #art>
        <ReferenceArtwork
          :portrait="currentPortrait"
          :initial-of="currentCharacter?.name || ''"
          stage
        />
      </template>
      <LettersPanel v-if="store.view.hudDrawer === 'letters'" :store="store" />
      <SkillBook v-else-if="store.view.hudDrawer === 'skill'" :skills="panel('character') || {}" :practice-disabled="skipDisabled" :practice-feedback="practiceFeedback" @practice="onPractice" @practice-view="(open) => practiceOpen = open" />
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
      <div
        v-else-if="store.view.hudDrawer === 'quest'"
        class="quest-drawer"
        data-testid="quest-drawer"
      >
        <QuestLog
          :quest-log="panel('quest_log')"
          :services="panel('services') || {}"
          @quest_track="onQuestAction"
          @quest_abandon="onQuestAction"
          @quest_turnin="onQuestAction"
        />
        <GuildCounter
          v-if="questGuildAvailable"
          :services="panel('services') || {}"
          @quest_register="onQuestAction"
          @quest_accept="onQuestAction"
          @exam_start="onQuestAction"
        />
        <!-- The counter's two honest absence forms: the services panel's own
             registry reason when the panel degraded, otherwise the explicit
             no-clerk marker. -->
        <p
          v-else-if="questServicesUnavailable"
          class="quest-drawer__counter-unavailable"
          data-testid="quest-drawer__counter-unavailable"
          :data-reason-code="questServicesPanel?.reason?.code"
        >
          {{ questServicesPanel?.reason?.message }}
        </p>
        <p
          v-else
          class="quest-drawer__counter-absent"
          data-testid="quest-drawer__counter-absent"
        >
          公會櫃台需在公會職員面前才能辦理。
        </p>
      </div>
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
      <!-- The cast-syntax footer hint is skill-drawer-only: a conditional
           named slot means the other five drawers provide no `foot` slot, so
           `HudDrawer` renders no footer for them. -->
      <template v-if="store.view.hudDrawer === 'skill' && !practiceOpen" #foot>
        <p class="hud-drawer__cast-hint" data-testid="skill-book-cast-hint">{{ SKILL_CAST_HINT }}</p>
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

/* quest-drawer-split: the drawer body's wrapper for the two quest surfaces.
   It stacks the quest book above the guild counter (or the counter's honest
   absence marker). */
.quest-drawer {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 0;
}

.quest-drawer__counter-absent,
.quest-drawer__counter-unavailable {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: max(var(--text-xs), 0.85em);
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}
</style>
