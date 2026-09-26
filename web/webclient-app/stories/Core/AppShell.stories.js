import { createApp, h, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { createPinia, disposePinia } from "pinia";
import AppShell from "../../components/AppShell.vue";
import AppClient from "../../AppClient.vue";
import { useElosernStore } from "../../stores/elosern.js";
import { createWindowBridge } from "../../bridge.js";
import * as protocolFixtures from "../../tests/store/protocol_fixtures.js";
import {
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
  COMMAND_HISTORY_SAMPLE,
  NARRATIVE_SAMPLE,
  OBJECTIVES_PANEL_SAMPLE,
  PARTY_PANEL_SAMPLE,
  PROMPT_SAMPLE,
  STATUS_SLICE_SAMPLE,
  SERVICES_PANEL_SAMPLE,
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
const renderPlayer = (args) => ({
  setup() {
    const host = ref(null);
    const pinia = createPinia();
    const store = useElosernStore(pinia);
    let app;
    let bridge;
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
            art: ART_PANEL_SAMPLE,
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
          context_actions: args.combat ? protocolFixtures.combatActions() : protocolFixtures.explorationActions({
            suggestions: { status: "ready", cards: [
              { kind: "known_action", action_code: "explore.look", label: "查看房間", params: { room: true } },
              { kind: "known_action", action_code: "explore.wait", label: "等到黃昏", params: { daypart: "dusk" } },
              { kind: "known_action", action_code: "explore.look", label: "查看木箱", params: { target_id: 3 } },
            ] },
          }),
          local_map: protocolFixtures.localMapPanel(),
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
                portrait: {
                  subject_key: "char_1",
                  status: "done",
                  url: "/art/defaults/man.webp",
                  aspect_ratio: "3:4",
                  alt: "艾莉亞的肖像",
                  placeholder: null,
                  face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
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
              } : {
                subject_key: "npc_7", status: "done", url: "/art/defaults/elder.webp", aspect_ratio: "3:4",
                alt: "店長的肖像", placeholder: null,
                face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 }, context: { name: "店長", role: "對話對象" },
              },
            },
          } } : {}),
          ...(args.dialogue ? { dialogue: {
            schema_version: 2, available: true, kind: "dialogue",
            host: { identity: 7, display_name: args.dialogue === "missing" ? "合成·旅人" : "店長", portrait_ref: args.dialogue === "missing" ? null : "7" },
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
      const result = store.receive(1, "ui_snapshot", [snapshot], {});
      if (!result.accepted || store.lastPanelRejection) throw new Error(`Player layout fixture was rejected: ${JSON.stringify(store.lastPanelRejection || result)}`);
      if (args.pane) store.tabToRootAndConfirm(args.pane, "pointer");
      // The session line as the narrative delivers it (webclient-dialogue-
      // choices-overlay D2): paged verbatim under the name plate. On mount
      // the window shows the last page complete, so the choice list shows at
      // once; `lateGreeting` delivers it after mount, so it types first.
      if (args.dialogue) {
        const hostName = args.dialogue === "missing" ? "合成·旅人" : "店長";
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
      if (args.practice) {
        store.openHudDrawer("skill");
        await nextTick();
        host.value?.querySelector('button[aria-label^="修煉"]')?.click();
      }
    });
    onBeforeUnmount(() => {
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
// a harmful condition, and the compact party under the place card; the
// minimap and the one-line objective at the top-right.
export const PopulatedHud = { render: renderPlayer, args: { populated: true } };
// Combat: the minimap and the objective line are hidden, and the participant
// frame takes the `map` anchor.
export const CombatHud = { render: renderPlayer, args: { combat: true } };
