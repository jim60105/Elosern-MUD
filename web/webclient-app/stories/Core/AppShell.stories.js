import { h } from "vue";
import AppShell from "../../components/AppShell.vue";
import {
  COMMAND_HISTORY_SAMPLE,
  NARRATIVE_SAMPLE,
  PROMPT_SAMPLE,
  STATUS_SLICE_SAMPLE,
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
