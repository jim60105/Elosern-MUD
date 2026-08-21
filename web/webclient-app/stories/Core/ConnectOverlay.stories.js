import { h } from "vue";
import ConnectOverlay from "../../components/ConnectOverlay.vue";

// ConnectOverlay: the full-viewport connection state screen (a non-
// dismissible polite live region). Props: status — "connecting" |
// "waiting" | "offline" (shown) or "ready" (not rendered). No emitted
// events: the transport/store owns reconnection (C3). The status line pairs
// a glyph with a text label, never color alone.

const renderOverlay = (args) => ({ render: () => h(ConnectOverlay, args) });

export default {
  title: "Core/ConnectOverlay",
  component: ConnectOverlay,
};

export const Connecting = {
  render: renderOverlay,
  args: { status: "connecting" },
};

export const WaitingForLogin = {
  render: renderOverlay,
  args: { status: "waiting" },
};

export const Disconnected = {
  render: renderOverlay,
  args: { status: "offline" },
};

export const ReadyHidden = {
  render: renderOverlay,
  args: { status: "ready" },
};
