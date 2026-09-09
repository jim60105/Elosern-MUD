import { createApp, h, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { createPinia, disposePinia } from "pinia";
import AppShell from "../../components/AppShell.vue";
import AppClient from "../../AppClient.vue";
import { useElosernStore } from "../../stores/elosern.js";
import { createWindowBridge } from "../../bridge.js";
import * as protocolFixtures from "../../tests/store/protocol_fixtures.js";
import {
  CHARACTER_PANEL_SAMPLE,
  COMMAND_HISTORY_SAMPLE,
  NARRATIVE_SAMPLE,
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
// Shell key contract: `/` toggles the drawer and focuses the field (slash
// stays literal text inside editables); Escape releases an open drawer back
// to the narrative pane. The mount retires the replaced text fallback
// (hidden, not removed).

const renderShell = (args) => ({ render: () => h(AppShell, args) });

export default {
  title: "Core/AppShell",
  component: AppShell,
  parameters: {
    docs: {
      description: {
        component:
          "The offline desktop shell composing TopBar, NarrativeFeed, " +
          "UnreadIndicator (inside the feed), CommandDrawer, ConnectOverlay, " +
          "the preserved `#elosern-action-live` live region and the " +
          "`#elosern-offline-overlay` hook.",
      },
    },
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
// overlap between the dock, wrapped tabs, narrative and command-line anchors.
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
        mode: args.dialogue ? "dialogue" : "exploration",
        panels: {
          status: protocolFixtures.statusPanel(),
          exploration: protocolFixtures.explorationPanel({
            interact: [
              { identity: 7, display_name: "店長", portrait_ref: null, affordances: [
                { kind: "action", action_id: "explore.talk_scripted", label: "交談", enabled: true, disabled_reason: null },
                { kind: "action", action_id: "explore.talk_freeform", label: "自由對話", enabled: true, disabled_reason: null },
              ] },
              { identity: 8, display_name: "守衛", portrait_ref: null, affordances: [
                { kind: "action", action_id: "explore.talk_scripted", label: "詢問城門", enabled: true, disabled_reason: null },
              ] },
            ],
          }),
          context_actions: protocolFixtures.explorationActions({
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
          ...(args.dialogue ? { dialogue: {
            schema_version: 1, available: true, kind: "dialogue",
            host: { identity: 7, display_name: "店長", portrait_ref: null },
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
      if (!result.accepted || store.lastPanelRejection) throw new Error("Player layout fixture was rejected");
      if (args.pane) store.tabToRootAndConfirm(args.pane, "pointer");
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
export const InteractionSelector = { render: renderPlayer, args: { pane: "interact" } };
export const DialogueSelector = { render: renderPlayer, args: { dialogue: true } };
export const WaitingSelector = { render: renderPlayer, args: { pane: "wait" } };
export const PracticeScreen = { render: renderPlayer, args: { practice: true } };
