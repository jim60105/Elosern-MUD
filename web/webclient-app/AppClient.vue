<script setup>
// C3 (webclient-vue-09-wire-transport-mount): the store-bound live renderers
// (design D3: passive, emit only user-intent dispatches). Every surface
// reads the C1 store's committed slices; panels render only when their
// backing OOB read model is present (the truthful-data scope, roadmap §7 —
// no surface is invented for a panel without a backing model). The behavior
// groups live in ./composables/ (each watch stays with the state it mutates).
import { computed, ref } from "vue";
import { useElosernStore } from "./stores/elosern.js";
import { useAppClient } from "./composables/use-app-client.js";
import AppShell from "./components/AppShell.vue";
import ActionDock from "./components/ActionDock.vue";
import CreationOverlay from "./components/CreationOverlay.vue";
import DockMenu from "./components/DockMenu.vue";
import ParticipantFrame from "./components/ParticipantFrame.vue";
import SkillDetailPane from "./components/SkillDetailPane.vue";
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
import ToastQueue from "./components/ToastQueue.vue";
import PartyStrip from "./components/PartyStrip.vue";
import PartyDrawer from "./components/PartyDrawer.vue";
import ObjectiveTracker from "./components/ObjectiveTracker.vue";
import DesktopNavigation from "./components/DesktopNavigation.vue";
import ReferenceArtwork from "./components/ReferenceArtwork.vue";
import { portraitGlyph } from "./components/party-helpers.js";
import { faceObjectPosition } from "./components/face-rect.js";

const store = useElosernStore();
const currentPortrait = computed(
  () => store.view.rosterCharacters?.find((character) => character.current)?.portrait ?? null,
);
// The shell handle (H5, design D1/D6) and the SceneBackdrop harness hook
// (the __-prefixed pending-scene journey seeds the prior-image memory
// through this handle — SceneBackdrop's exposed setPriorImage).
const shellRef = ref(null);
const sceneBackdropRef = ref(null);
// The behavior groups composed in use-app-client.js: every binding below is
// a group's verbatim state/handler, destructured so the template is unchanged.
const {
  panel, panelAvailable, dispatchIntent,
  dialogueVM, onDialoguePick, onDialogueFreeform, onDialogueLeave,
  completionCandidates, possessionBanner, contextAffordances, releaseAffordance,
  titleBallotPanel, titleBallotCandidates, onMapMove, showObjectiveTracker,
  restFormOpen, restFormError, onRestFormSubmit, onRestFormClose, onRestFormError,
  waitOpen, skipDisabled, activateWait, practiceOpen, practiceFeedback, onPractice,
  fullLogOpen, fullLogRef, openFullLog, closeFullLog, openSurfaces,
  openOverlayByName, onOpenOverlay, onMapExpand, onOverlayClose,
  drawerTitle, onOpenDrawer, onHudDrawerClose, questServicesPanel,
  questGuildAvailable, questServicesUnavailable, skillBookSubtitle,
  inventoryWalletCopper, inventoryWalletSubtitle, partyReason, SKILL_CAST_HINT,
  rootItems, navigationItems, dockItems, dockPaneKind, interactionOpen,
  interactionTarget, interactionChoices, onInteractionTarget, onTabClick,
  onDockBack, contextActionsPanel, rowPrefix, detailTestId,
  showDetail, focusedRowDisabled,
  onAction, onDockActivate, onDockFocusChange,
  onShopBuy, onShopSell, onInventoryItemAction, onTitleBallotAction, onTitleCodexAction,
  onCreationAction, onCreationDispatch, onCreationRequestReset, onCreationCancelConfirm,
  onQuestAction, onPersonaEdit, onSubmitCommand, onSwitchCharacter, onCreateCharacter,
} = useAppClient(store, shellRef, sceneBackdropRef);
</script>

<template>
  <div class="elosern-root" data-testid="elosern-client-root">
      <AppShell
        ref="shellRef"
        :mode="store.view.mode || 'exploration'"
        :connected="store.view.connected"
        :location-label="store.view.statusSlice.locationLabel"
        :time-label="store.view.statusSlice.timeLabel"
        :narrative="store.narrative"
        :response-marks="store.responseMarks"
        :dialogue="dialogueVM"
        :art-panel="panel('art')"
        :font-scale="store.view.fontScale"
        :text-speed="store.view.textSpeed"
        :auto-advance="store.view.autoAdvance"
        :reduced-motion="store.view.reducedMotion"
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
        :in-flight="store.view.dispatch.inFlight !== null"
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
        @dialogue-pick="onDialoguePick"
        @dialogue-freeform="onDialogueFreeform"
        @dialogue-leave="onDialogueLeave"
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
          <SceneBackdrop ref="sceneBackdropRef" :art="panel('art') || {}" :mode="store.view.mode || 'exploration'" />
        </template>
        <!-- The player's standing portrait (webclient-avg-stage-shell D4):
             the current roster character's portrait stands on the bottom
             band's top edge in the `actor-left` anchor, outside creation. -->
        <template #actor-left>
          <ReferenceArtwork v-if="store.view.mode !== 'creation'" :portrait="currentPortrait" />
        </template>
        <!-- The `vitals` anchor (webclient-avg-stage-hud-anchors design D1),
             under the place card: the vitals and conditions islands, then
             the compact party quickbar. -->
        <template #vitals>
        <StatusPanel
          v-if="panelAvailable('status')"
          :status="panel('status') || {}"
          :low-hp="store.view.vitals.lowHp"
          :visible="store.view.vitals.visible"
          :revision="store.view.revision"
          :epoch="store.view.epoch"
        />
        <PartyStrip
          v-if="store.partyAvailable && store.view.mode !== 'creation'"
          :slots="store.partySlots"
          :combat-participants="store.combatParticipants"
          :art-panel="panel('art')"
          @open-drawer="() => store.openHudDrawer('party')"
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
          :focused-key="store.view.focus.key"
          :view="store.view"
            @action="onAction"
          @tab-click="onTabClick"
          @back="onDockBack"
        >
          <div
            class="dock-pane-host"
            :class="{ 'interaction-workspace': interactionOpen, 'interaction-workspace--selected': !!interactionTarget }"
          >
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
            <section v-if="interactionTarget" class="interaction-targets" aria-label="互動對象">
              <h3 class="interaction-heading"><span>1</span>選擇互動對象</h3>
              <div class="interaction-target-grid">
                <button
                  v-for="target in interactionChoices"
                  :key="target.identity"
                  type="button"
                  class="interaction-target"
                  :aria-pressed="target.identity === interactionTarget.identity"
                  :disabled="!target.affordances.length"
                  @keydown.enter.stop
                  @keydown.space.stop
                  @click="onInteractionTarget(target.identity)"
                >
                  <span class="interaction-avatar" aria-hidden="true">
                    <img v-if="target.portrait" :src="target.portrait.url" :style="{ objectPosition: faceObjectPosition(target.portrait.face_rect) }" alt="" />
                    <span v-else>{{ portraitGlyph(target.display_name) }}</span>
                  </span>
                  <span>{{ target.display_name }}</span>
                </button>
              </div>
            </section>
            <h3 v-if="interactionOpen" class="interaction-heading interaction-heading--active">
              <span>{{ interactionTarget ? "2" : "1" }}</span>
              {{ interactionTarget ? "選擇對話或行動" : "選擇互動對象" }}
            </h3>
            <section v-if="interactionOpen && !interactionTarget" class="interaction-prompt">
              <h3 class="interaction-heading"><span>2</span>選擇對話或行動</h3>
              <p>先選擇左側的對象，即可查看可用的互動。</p>
            </section>
             <DockMenu
               v-if="!waitOpen && dockItems.length && !(store.view.dockDepth === 1 && dockPaneKind === 'plain' && !store.view.degradedRoot)"
               :items="dockItems"
              :focused-key="store.view.focus.key"
              :id-prefix="rowPrefix"
              :detail-test-id="detailTestId"
              :show-detail="showDetail && (!interactionOpen || focusedRowDisabled)"
              :detail-message="restFormError"
              :grid-cols="store.view.combatMenu ? store.view.combatMenu.gridCols : null"
              :depth="store.view.dockDepth"
              :view="store.view"
              :art-panel="panel('art')"
              :target-name="store.view.combatMenu ? store.view.combatMenu.title : null"
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
        </ActionDock>
      </template>
    </AppShell>

    <!-- H4 (task 7.4): the reference-drawer layer, mounted above the
         stage. A single `HudDrawer` chrome hosts the drawer body for the
         store's single open-drawer name; only the open drawer's surface is
         in the DOM (task 7.7: no reference surface while closed). -->
    <HudDrawer
      v-if="store.view.hudDrawer"
      :open="true"
      :title="practiceOpen && store.view.hudDrawer === 'skill' ? '修煉' : drawerTitle"
      :subtitle="store.view.hudDrawer === 'inventory' ? inventoryWalletSubtitle : (store.view.hudDrawer === 'skill' ? skillBookSubtitle : (store.view.hudDrawer === 'party' ? `${(store.partySlots || []).length} / 4` : ''))"
      :icon="store.view.hudDrawer === 'inventory' ? 'inventory' : (store.view.hudDrawer === 'skill' ? 'skills' : (store.view.hudDrawer === 'party' ? 'party' : null))"
      :drawer-key="store.view.hudDrawer"
      @close="onHudDrawerClose"
    >
      <template #art>
        <ReferenceArtwork
          :portrait="store.view.hudDrawer === 'quest' ? null : currentPortrait"
        />
      </template>
      <SkillBook v-if="store.view.hudDrawer === 'skill'" :skills="panel('character') || {}" :practice-disabled="skipDisabled" :practice-feedback="practiceFeedback" @practice="onPractice" @practice-view="(open) => practiceOpen = open" />
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
          :reduced-motion="store.view.reducedMotion"
          :colorblind="store.view.colorblind"
          :text-speed="store.view.textSpeed"
          :auto-advance="store.view.autoAdvance"
          @scale-change="store.setFontScale"
          @text-html-change="store.setTextToHtml"
          @reduced-motion-change="store.setReducedMotion"
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
  gap: 12px;
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
  font-size: 0.85em;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}
</style>
