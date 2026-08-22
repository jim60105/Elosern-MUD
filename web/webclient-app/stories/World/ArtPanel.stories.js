import { h } from "vue";
import ArtPanel from "../../components/ArtPanel.vue";
import {
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
  ART_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// ArtPanel: the world art surface (B4). Prop: art — the committed `art` v1
// panel payload (a 16:9 scene + 3:4 portrait catalog with contextual
// name/role overlays) or the registry-owned unavailable form. Read-only: no
// events.

const renderPanel = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(ArtPanel, args),
    ]),
});

export default {
  title: "World/ArtPanel",
  component: ArtPanel,
};

export const FullPayload = {
  render: renderPanel,
  args: { art: ART_PANEL_SAMPLE },
};

export const Pending = {
  render: renderPanel,
  args: { art: ART_PANEL_PENDING_SAMPLE },
};

export const Unavailable = {
  render: renderPanel,
  args: { art: ART_PANEL_UNAVAILABLE_SAMPLE },
};
