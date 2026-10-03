import { createApp, h, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { createPinia, disposePinia } from "pinia";
import AppShell from "../../components/AppShell.vue";
import AppClient from "../../AppClient.vue";
import { useElosernStore } from "../../stores/elosern.js";
import { createWindowBridge } from "../../bridge.js";
import CombatMenu from "../../lib/combat_menu.js";
import * as protocolFixtures from "../../tests/store/protocol_fixtures.js";
import {
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
  COMMAND_HISTORY_SAMPLE,
  FOE_PORTRAIT_CATALOG,
  PARTY_PARTICIPANTS,
  combatSkills,
  foeParticipants,
  NARRATIVE_SAMPLE,
  OBJECTIVES_PANEL_SAMPLE,
  PARTY_PANEL_SAMPLE,
  PROMPT_SAMPLE,
  STATUS_SLICE_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  STAGE_JOURNEY_STOPS,
  stageJourneyLocalMap,
  stageJourneyScene,
} from "../fixtures.js";

// AppShell (root/layout). Passive B1 contract: renders the slices it is
// given and emits user intent; the primary states are the transport
// connection states the shell is rendered in offline.
//
// Props: mode (contextual mode slice, rendered as data-elosern-mode),
// connected / locationLabel / timeLabel (TopBar slice), narrative (log
// slice), connectionStatus ("connecting" | "waiting" | "offline" | "ready"),
// offline (offline-overlay slice), prompt, commandHistory (drawer slices).
// Events: submit-command(text) — one deliberate send from the drawer.
//
// Shell key contract: `/` or the ⌨ toggle expands the collapsed command line
// and focuses `#inputfield` (slash stays literal text inside editables);
// Escape or an accepted send collapses the line and returns focus to
// `#action-dock`. The mount retires the replaced text fallback
// (hidden, not removed).

let mountedShell = null;
const renderShell = (args) => ({
  setup() {
    const shell = ref(null);
    onMounted(() => {
      mountedShell = shell.value;
      if (shell.value?.$el) {
        shell.value.$el.__elosernShell = shell.value;
      }
    });
    return () => h(AppShell, { ...args, ref: shell });
  },
});

export default {
  title: "Core/AppShell",
  component: AppShell,
  parameters: {
    docs: {
      description: {
        component:
          "The offline desktop shell composing TopBar, MessageWindow, " +
          "the 日誌 log control, the ⌨ command-line toggle, " +
          "the collapsible CommandLine, ConnectOverlay, " +
          "the preserved `#elosern-action-live` live region and the " +
          "`#elosern-offline-overlay` hook.",
      },
    },
  },
};

export const CommandLineExpanded = {
  render: renderShell,
  args: {
    ...STATUS_SLICE_SAMPLE,
    connectionStatus: "ready",
    mode: "exploration",
    narrative: NARRATIVE_SAMPLE,
    prompt: PROMPT_SAMPLE,
    commandHistory: COMMAND_HISTORY_SAMPLE,
  },
  play: async ({ canvasElement }) => {
    const root = canvasElement?.querySelector('[data-testid="elosern-vue-root"]');
    await (root?.__elosernShell || mountedShell)?.focusCommandField();
  },
};

export const PreConnection = {
  render: renderShell,
  args: {
    connectionStatus: "connecting",
    connected: false,
    narrative: [],
    prompt: "",
    commandHistory: [],
  },
};

export const ReadyOfflinePreview = {
  render: renderShell,
  args: {
    ...STATUS_SLICE_SAMPLE,
    connectionStatus: "ready",
    mode: "exploration",
    narrative: NARRATIVE_SAMPLE,
    prompt: PROMPT_SAMPLE,
    commandHistory: COMMAND_HISTORY_SAMPLE,
  },
};

export const DisconnectedSession = {
  render: renderShell,
  args: {
    ...STATUS_SLICE_SAMPLE,
    connectionStatus: "offline",
    offline: true,
    narrative: NARRATIVE_SAMPLE,
    prompt: PROMPT_SAMPLE,
    commandHistory: COMMAND_HISTORY_SAMPLE,
  },
};

// Exercise the real composed shell: isolated component stories cannot expose
// overlap between the dock, the wrapped overview chips, the verb popover,
// the narrative and the command-line anchors.
// The stage-transition journey's panels for one stop
// (webclient-scene-transitions): the scene, the current map node, and the
// vitals, all full except the stop's hp, so the vitals island shows only on
// the stops that lower it.
function journeyPanels(stop) {
  const cell = stageJourneyLocalMap(stop.node).nodes.find((node) => node.current);
  return {
    art: { ...ART_PANEL_SAMPLE, scene: stageJourneyScene(stop) },
    local_map: stageJourneyLocalMap(stop.node),
    status: protocolFixtures.statusPanel({
      actor: { location: { label: cell.label, identity: cell.id } },
      resources: {
        hp: { current: stop.hp, maximum: 100 },
        mp: { current: 50, maximum: 50 },
        sp: { current: 40, maximum: 40 },
      },
    }),
  };
}

// The mode-transition journey's host (webclient-mode-transitions): the
// tavern keeper with a finished portrait, a greeting, and four picks.
const MODE_JOURNEY_CATALOG = {
  "7": {
    subject_key: "npc_7", status: "done", url: "/art/defaults/elder.webp", aspect_ratio: "3:4",
    alt: "店長的肖像", placeholder: null,
    face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 }, context: { name: "店長", role: "對話對象" },
    stage: { scale: 1, x: 0, y: 0 },
  },
};
const MODE_JOURNEY_DIALOGUE = {
  schema_version: 2, available: true, kind: "dialogue",
  host: { identity: 7, display_name: "店長", portrait_ref: "7" },
  bond_stage: "熟識",
  line: "又見面了。今晚爐火正旺，要喝點什麼，還是想打聽些消息？",
  choices: [
    { keyword_id: "news", label: "最近有什麼消息？" },
    { keyword_id: "town", label: "關於這座城鎮" },
    { keyword_id: "guild", label: "冒險者公會在哪裡？" },
    { keyword_id: "rest", label: "我想稍作休息" },
  ],
};
const MODE_JOURNEY_DIALOGUE_CLOSED = {
  schema_version: 2, available: false, reason: { code: "dialogue_unavailable", message: "對話已結束" },
};

// The combat panel with `foes` active foes (webclient-combat-foes-on-stage):
// the player's side, then the foes in presenter order, each with a catalog
// portrait; `overrides` edits a foe by identity (a defeat, a missing ref).
const combatPanelWith = (foes, overrides = {}) =>
  protocolFixtures.combatActions({ ...combatRoster([...PARTY_PARTICIPANTS, ...foeParticipants(foes, overrides)]) });
const combatRoster = (participants) => ({ participants, skills: combatSkills(participants) });
const combatArt = (art) => ({ ...art, portrait_catalog: { ...(art.portrait_catalog || {}), ...FOE_PORTRAIT_CATALOG } });

const renderPlayer = (args) => ({
  setup() {
    const host = ref(null);
    const pinia = createPinia();
    const store = useElosernStore(pinia);
    let app;
    let bridge;
    let journeyTimer = null;
    onMounted(async () => {
      app = createApp(AppClient);
      app.use(pinia);
      bridge = createWindowBridge(store);
      app.mount(host.value);
      store.beginTransport(1);
      store.setConnected(true);
      store.setLoggedIn(true);
      const snapshot = protocolFixtures.snapshot({
        mode: args.dialogue ? "dialogue" : args.combat ? "combat" : "exploration",
        panels: {
          status: protocolFixtures.statusPanel(args.populated || args.combat ? {
            conditions: [
              { code: "poisoned", label: "中毒", severity: "harmful", remaining_seconds: 40 },
              { code: "blessed", label: "祝福", severity: "beneficial" },
            ],
          } : undefined),
          // The populated island stacks (webclient-avg-stage-hud-anchors):
          // a two-slot party under the vitals and three tracked objectives,
          // so the `map` anchor shows the objective line with `+2`.
          ...(args.populated || args.combat ? {
            // party v1 carries no bound portrait (`portrait_ref` null).
            party: { ...PARTY_PANEL_SAMPLE, slots: PARTY_PANEL_SAMPLE.slots.map((s) => ({ ...s, portrait_ref: null })) },
            objectives: OBJECTIVES_PANEL_SAMPLE,
            art: args.combat ? combatArt(ART_PANEL_SAMPLE) : ART_PANEL_SAMPLE,
          } : {}),
          exploration: protocolFixtures.explorationPanel({
            // Exits labelled by direction, as the server labels them: the
            // choice list's `↦ 移動…` rows then show each direction's glyph
            // and the destination's name.
            ...(args.dialogue ? { move: [
              { exit_ref: "east", label: "東", destination: "room:43", enabled: true, disabled_reason: null },
              { exit_ref: "north", label: "北", destination: "room:44", enabled: false, disabled_reason: { code: "blocked", message: "門被鎖住了" } },
            ] } : {}),
            interact: [
              { identity: 7, display_name: "店長", portrait_ref: null, affordances: [
                { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
              ] },
              { identity: 8, display_name: "守衛", portrait_ref: null, affordances: [
                { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
              ] },
            ],
          }),
          context_actions: args.combat ? combatPanelWith(args.combat === true ? 3 : args.combat) : protocolFixtures.explorationActions({
            suggestions: { status: "ready", cards: [
              { kind: "known_action", action_code: "explore.look", label: "查看房間", params: { room: true } },
              { kind: "known_action", action_code: "explore.wait", label: "等到黃昏", params: { daypart: "dusk" } },
              { kind: "known_action", action_code: "explore.look", label: "查看木箱", params: { target_id: 3 } },
            ] },
          }),
          local_map: protocolFixtures.localMapPanel(),
          ...(args.journey ? journeyPanels(STAGE_JOURNEY_STOPS[0]) : {}),
          services: SERVICES_PANEL_SAMPLE,
          character: CHARACTER_PANEL_SAMPLE,
          roster: {
            schema_version: 2,
            available: true,
            characters: [
              {
                identity: 1,
                name: "艾莉亞",
                current: true,
                pending: false,
                portrait: args.grounding ? {
                  subject_key: "char_1", status: args.grounding,
                  url: null, aspect_ratio: null, alt: "艾莉亞的肖像",
                  placeholder: { kind: "missing", label: "無肖像" }, face_rect: null,
                  stage: null,
                } : {
                  subject_key: "char_1",
                  status: "done",
                  url: "/art/defaults/man.webp",
                  aspect_ratio: "3:4",
                  alt: "艾莉亞的肖像",
                  placeholder: null,
                  face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
                  stage: { scale: 1, x: 0, y: 0 },
                },
              },
            ],
            max_characters: 5,
            can_create: true,
            switch_locked: false,
            lock_reason: null,
          },
          // The dialogue host's catalog entry (webclient-dialogue-stage-
          // actors): an image, a pending placeholder card, or no entry at all
          // (`portrait_ref` null → the name's initial and the name).
          ...(args.dialogue && args.dialogue !== "missing" ? { art: {
            ...ART_PANEL_PENDING_SAMPLE,
            // A local scene image for layout review (optional arg).
            ...(args.sceneUrl ? { scene: { ...ART_PANEL_SAMPLE.scene, url: args.sceneUrl } } : {}),
            portrait_catalog: {
              "7": args.dialogue === "pending" ? {
                subject_key: "npc_7", status: "pending", url: null, aspect_ratio: null,
                alt: "店長的肖像", placeholder: { kind: "missing", label: "肖像生成中" },
                face_rect: null, context: { name: "店長", role: "對話對象" },
                stage: null,
              } : {
                subject_key: "npc_7", status: "done", url: "/art/defaults/elder.webp", aspect_ratio: "3:4",
                alt: "店長的肖像", placeholder: null,
                face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 }, context: { name: "店長", role: "對話對象" },
                stage: { scale: 1, x: 0, y: 0 },
              },
            },
          } } : {}),
          ...(args.dialogue ? { dialogue: {
            schema_version: 2, available: true, kind: "dialogue",
            host: { identity: 7, display_name: args.dialogue === "missing" ? "合成‧旅人" : "店長", portrait_ref: args.dialogue === "missing" ? null : "7" },
            bond_stage: "熟識",
            line: "歡迎來到西風酒館。你可以在這裡打聽消息，也可以稍作休息再出發。",
            choices: [
              { keyword_id: "news", label: "最近有什麼消息？" },
              { keyword_id: "town", label: "關於這座城鎮" },
              { keyword_id: "guild", label: "冒險者公會在哪裡？" },
              { keyword_id: "rest", label: "我想稍作休息" },
            ],
          } } : {}),
        },
      });
      if (args.participantPolish) {
        const participants = [...PARTY_PARTICIPANTS, ...foeParticipants(4, {
          31: { display_name: "灰袍盜賊與北境巡防隊長的漫長稱號" },
          34: { state: "defeated", hp_current: 0 },
        })];
        snapshot.panels.context_actions = protocolFixtures.combatActions({
          participants, session: { round: 0 },
          skills: [{ category: "martial_arts", label: "武技", groups: [{ group: "basic", label: "基本", skills: [{
            key: CombatMenu.BASIC_ATTACK_KEY, label: "基本攻擊", description: "選擇一名敵人。",
            cost: {}, target_spec: "single", element: null, enabled: true, disabled_reason: null,
            targets: [31, 32, 33], shorthands: [],
          }] }] }],
        });
        snapshot.panels.status = protocolFixtures.statusPanel({ combat: { mode: "hostile", round: 0 } });
        snapshot.panels.art.portrait_catalog["32"] = {
          ...FOE_PORTRAIT_CATALOG["32"], url: null, status: "pending", face_rect: null, aspect_ratio: null,
          placeholder: { kind: "missing", label: "肖像生成中" },
          stage: null,
        };
      }
      const result = store.receive(1, "ui_snapshot", [snapshot], {});
      if (!result.accepted || store.lastPanelRejection) throw new Error(`Player layout fixture was rejected: ${JSON.stringify(store.lastPanelRejection || result)}`);
      if (args.pane) store.tabToRootAndConfirm(args.pane, "pointer");
      if (args.participantPolish) {
        let revision = 1;
        const sender = protocolFixtures.createFakeSender();
        store.setSender(sender);
        const round = (terminal = false) => {
          const request = store.dispatchAction("combat.cast", { skill_key: CombatMenu.BASIC_ATTACK_KEY, target_ids: [31] });
          const beats = [
            { seq: 0, action: 0, kind: "roll", actor: "32", target: "31", amount: null, hp_after: null, text: "敵人舉起武器。" },
            { seq: 1, action: 1, kind: "damage", actor: "32", target: "31", amount: 20, hp_after: 10, text: "武器命中，生命值下降。" },
          ];
          beats.forEach((beat) => store.appendText("out", beat.text));
          const panels = {
            context_actions: terminal ? protocolFixtures.explorationActions() : protocolFixtures.combatActions({
              skills: snapshot.panels.context_actions.skills,
              session: { round: revision },
              participants: snapshot.panels.context_actions.participants.map((p) => p.identity === 31 ? { ...p, hp_current: 10 } : p),
            }),
            status: protocolFixtures.statusPanel({ combat: terminal ? null : { mode: "hostile", round: revision } }),
            combat_beats: { schema_version: 1, available: true, round: `polish/${revision}`, beats },
          };
          const received = store.receive(1, "ui_update", [protocolFixtures.update({
            revision: ++revision, mode: terminal ? "exploration" : "combat", panels,
          })], {});
          if (!received.accepted || store.lastPanelRejection) throw new Error(JSON.stringify(store.lastPanelRejection || received));
          store.receive(1, "ui_action_result", [protocolFixtures.actionResult({ request_id: request, presentation_revision: revision })], {});
        };
        window.__participantPolish = { store, sent: sender.sent, round };
        host.value.__participantPolish = window.__participantPolish;
      }
      // The session line as the narrative delivers it (webclient-dialogue-
      // choices-overlay D2): paged verbatim under the name plate. On mount
      // the window shows the last page complete, so the choice list shows at
      // once; `lateGreeting` delivers it after mount, so it types first.
      if (args.dialogue) {
        const hostName = args.dialogue === "missing" ? "合成‧旅人" : "店長";
        const deliver = () =>
          store.appendText("out", `${hostName}說：「${args.greeting || "歡迎來到西風酒館。你可以在這裡打聽消息，也可以稍作休息再出發。"}」`);
        if (args.lateGreeting) setTimeout(deliver, 400);
        else deliver();
      }
      // The player speaking: a pick in flight (no transport is attached, so
      // the request stays open and the player stays lit).
      if (args.playerSpeaking) store.dispatchAction("explore.talk_scripted", { npc_id: 7, keyword_id: "news" }, null);
      // The `↦ 移動…` swap: the list shows the committed overview's exits.
      if (args.moveExits) {
        // The list renders once the fonts are ready and the line is read.
        for (let tries = 0; tries < 60; tries += 1) {
          const row = host.value?.querySelector('[data-testid="dialogue-move"]');
          if (row) {
            row.click();
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 50));
        }
      }
      // The stage-transition journey (webclient-scene-transitions): each
      // step acts, commits the next stop's scene, location, map node, and
      // vitals, then delivers its line, exactly as a move does live. The
      // host exposes `step()` so a reviewer (or a browser driving the story)
      // can take one step at a time; `autoplay` walks on its own.
      if (args.journey) {
        store.appendText("out", STAGE_JOURNEY_STOPS[0].line);
        let index = 0;
        let revision = 1;
        const step = () => {
          index = (index + 1) % STAGE_JOURNEY_STOPS.length;
          const stop = STAGE_JOURNEY_STOPS[index];
          revision += 1;
          store.appendText("in", stop.command);
          store.receive(1, "ui_update", [protocolFixtures.update({ revision, panels: journeyPanels(stop) })], {});
          store.appendText("out", stop.line);
          return index;
        };
        const journey = { step, store };
        host.value.__stageJourney = journey;
        window.__stageJourney = journey;
        if (args.autoplay) {
          journeyTimer = setInterval(step, 3600);
        }
      }
      // The mode-transition journey (webclient-mode-transitions): the real
      // client walks exploration -> dialogue -> exploration -> combat ->
      // exploration, one committed revision per step, exactly as the server
      // commits them. The host exposes `__modeJourney.go(step)` so a
      // reviewer (or a browser driving the story) takes one step at a time;
      // `autoplay` walks on its own.
      if (args.modeJourney) {
        let revision = 1;
        const art = { ...ART_PANEL_SAMPLE, scene: stageJourneyScene(STAGE_JOURNEY_STOPS[2]), portrait_catalog: { ...MODE_JOURNEY_CATALOG, ...FOE_PORTRAIT_CATALOG } };
        const foes = args.modeJourneyFoes || 3;
        const commit = (mode, panels, line) => {
          revision += 1;
          store.receive(1, "ui_update", [protocolFixtures.update({ revision, mode, panels })], {});
          if (line) store.appendText("out", line);
        };
        const steps = {
          talk: () => {
            store.appendText("in", "與店長交談");
            commit("dialogue", { art, dialogue: MODE_JOURNEY_DIALOGUE }, `店長說：「${MODE_JOURNEY_DIALOGUE.line}」`);
          },
          leave: () => {
            store.appendText("in", "結束對話");
            commit("exploration", { dialogue: MODE_JOURNEY_DIALOGUE_CLOSED }, "你向店長點頭致意，轉身離開吧檯。爐火在身後劈啪作響。");
          },
          fight: () => {
            store.appendText("in", "攻擊灰袍盜賊");
            commit("combat", { context_actions: combatPanelWith(foes) }, "灰袍盜賊猛然掀翻木桌，短刀在火光中一閃！");
          },
          // Inside combat (webclient-combat-foes-on-stage): the front foe is
          // defeated, fades where it stands, and the others step forward.
          defeat: () => {
            store.appendText("in", "攻擊灰袍盜賊");
            commit("combat", { context_actions: combatPanelWith(foes, { 31: { state: "defeated", hp_current: 0 } }) }, "灰袍盜賊踉蹌倒地，再也沒有起來。");
          },
          flee: () => {
            store.appendText("in", "逃跑");
            commit("exploration", { context_actions: protocolFixtures.explorationActions() }, "你撞開後門衝進夜色，身後的叫罵聲漸漸遠去。");
          },
        };
        const order = ["talk", "leave", "fight", "defeat", "flee"];
        let next = 0;
        const go = (name) => {
          const key = name || order[next];
          next = (order.indexOf(key) + 1) % order.length;
          steps[key]();
          return key;
        };
        store.receive(1, "ui_update", [protocolFixtures.update({ revision: (revision += 1), mode: "exploration", panels: { art } })], {});
        store.appendText("out", STAGE_JOURNEY_STOPS[2].line);
        const journey = { go, store };
        host.value.__modeJourney = journey;
        window.__modeJourney = journey;
        if (args.autoplay) {
          journeyTimer = setInterval(() => go(), 3200);
        }
      }
      if (args.practice) {
        store.openHudDrawer("skill");
        await nextTick();
        host.value?.querySelector('button[aria-label^="修煉"]')?.click();
      }
    });
    onBeforeUnmount(() => {
      if (journeyTimer !== null) clearInterval(journeyTimer);
      if (window.__stageJourney && host.value?.__stageJourney === window.__stageJourney) delete window.__stageJourney;
      if (window.__modeJourney && host.value?.__modeJourney === window.__modeJourney) delete window.__modeJourney;
      if (window.__participantPolish && host.value?.__participantPolish === window.__participantPolish) delete window.__participantPolish;
      bridge?.uninstall();
      app?.unmount();
      disposePinia(pinia);
    });
    return () => h("div", { ref: host, style: "height:100vh;min-height:0" });
  },
});

export const ActionNavigation = { render: renderPlayer, args: {} };
// A person chip's verb popover (webclient-scene-overview-swap): the overview
// stays rendered beneath it while the popover's card covers the pane.
export const VerbPopoverSelector = { render: renderPlayer, args: { pane: "target-7" } };
// Dialogue (webclient-dialogue-stage-actors; webclient-dialogue-choices-
// overlay): the command region collapses, the message window pages the
// session line under the host's name plate, the host stands opposite the
// player — lit while speaking, the player dimmed — and the choice list sits
// centred over the stage once the line is read.
export const DialogueSelector = { render: renderPlayer, args: { dialogue: true } };
// The choice list's `↦ 移動…` swap (webclient-dialogue-choices-overlay):
// the committed overview's exits with their glyphs, a locked exit with its
// reason, and the back row.
export const DialogueMoveExits = { render: renderPlayer, args: { dialogue: true, moveExits: true } };
// The greeting arrives after mount, so it types under the name plate with no
// choice list; the list appears centred over the stage and takes focus once
// the last page is fully shown.
export const DialogueGreetingTypes = { render: renderPlayer, args: { dialogue: true, lateGreeting: true } };
// The player's pick is in flight: the player is lit and the host dimmed.
export const DialoguePlayerSpeaking = { render: renderPlayer, args: { dialogue: true, playerSpeaking: true } };
// The host's catalog entry is still generating: its own placeholder card.
export const DialogueHostPending = { render: renderPlayer, args: { dialogue: "pending" } };
// The host is not in the catalog: the name's initial and the name.
export const DialogueHostMissing = { render: renderPlayer, args: { dialogue: "missing" } };
export const WaitingSelector = { render: renderPlayer, args: { pane: "wait" } };
export const PracticeScreen = { render: renderPlayer, args: { practice: true } };
// The island anchors populated (webclient-avg-stage-hud-anchors): vitals,
// a harmful condition, and the compact party at the top-left; the place
// card, the minimap, and the one-line objective at the top-right.
export const PopulatedHud = { render: renderPlayer, args: { populated: true } };
// Combat: the minimap and the objective line are hidden, and the participant
// frame takes the `map` anchor.
export const CombatHud = { render: renderPlayer, args: { combat: true } };
// Six rows, three standing foes, long identity and pending thumbnail. The
// offline journey exposes round()/round(true) for normal/terminal playback.
export const CombatParticipantPolish = { render: renderPlayer, args: { combat: 4, participantPolish: true } };
// The foe line-up (webclient-combat-foes-on-stage) with one foe, and with
// five, of whom three stand on the stage while the frame lists all five.
export const CombatOneFoe = { render: renderPlayer, args: { combat: 1 } };
export const GroundedOneFoe = { render: renderPlayer, args: { combat: 1, grounding: "missing" } };
export const GroundedTwoFoes = { render: renderPlayer, args: { combat: 2, grounding: "pending" } };
export const GroundedThreeFoes = { render: renderPlayer, args: { combat: 3, grounding: "failed" } };
export const CombatFiveFoes = { render: renderPlayer, args: { combat: 5 } };
// The stage transitions (webclient-scene-transitions): a walk down a short
// street. Each step crossfades the scene once the next painting is decoded,
// slides the place card's new heading in, pans the minimap from the node the
// player left, clears the message window for the new line, and reveals or
// hides the vitals island as hp drops and recovers. It walks on its own
// every few seconds; the host element's `__stageJourney.step()` takes one
// step on demand.
export const StageJourney = { render: renderPlayer, args: { journey: true, autoplay: true } };
// The mode transitions (webclient-mode-transitions): the real client opens a
// conversation (the command panel slides out over the widened message
// window, the host walks on from the right, the name plate fades in, and
// the choices stagger in once the greeting is read), ends it (the reverse),
// then enters combat (the flash, the veil, the panel flip, and the foes
// stepping in as the flash releases), defeats the front foe (it fades and
// the others step forward), and leaves combat (the foes fade out).
// It walks on its own every few seconds; the host element's
// `__modeJourney.go(step)` takes one step on demand
// (`talk`, `leave`, `fight`, `defeat`, `flee`).
export const ModeJourney = { render: renderPlayer, args: { modeJourney: true, autoplay: true } };
