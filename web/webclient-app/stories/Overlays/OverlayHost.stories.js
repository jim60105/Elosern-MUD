import { h } from "vue";
import OverlayHost from "../../components/OverlayHost.vue";
import MapDrawer from "../../components/MapDrawer.vue";
import SettingsOverlay from "../../components/SettingsOverlay.vue";
import HelpOverlay from "../../components/HelpOverlay.vue";
import { townArea } from "../fixtures/area_map.js";

// OverlayHost (H5, task 5.6): the shared full-screen overlay surface. The
// stories below cover the three overlay names with their real stripped
// bodies, so the showcase gate sees a mounted, reachable surface — not a
// manifest-listed orphan.

const renderHost = (args) => ({
  render: () =>
    h(
      "div",
      { style: "position: relative; height: 420px; background: var(--ink-950); overflow: hidden;" },
      [
        h(
          OverlayHost,
          {
            overlay: args.overlay,
            opener: null,
            locationLabel: "灰河帶",
            // The map drawer draws its own header (redesign-map-drawer).
            ownHeader: args.overlay === "map",
            onClose: () => {},
          },
          {
            default: (slotProps) => {
              const { overlay, close } = slotProps;
              if (overlay === "map") {
                return h(MapDrawer, {
                  area: townArea(),
                  world: null,
                  tab: "area",
                  memory: { area: {}, world: {} },
                  locationLabel: "灰河帶",
                  onClose: close,
                });
              }
              if (overlay === "settings") {
                return h(SettingsOverlay, {
                  fontScale: 1,
                  textToHtml: true,
                  motionLevel: "full",
                  colorblind: false,
                  textSpeed: "normal",
                  autoAdvance: false,
                });
              }
              return h(HelpOverlay, { guide: {} });
            },
          }
        ),
      ]
    ),
});

export default {
  title: "Overlays/OverlayHost",
  component: OverlayHost,
};

export const MapSurface = {
  render: renderHost,
  args: { overlay: "map" },
};

export const SettingsSurface = {
  render: renderHost,
  args: { overlay: "settings" },
};

export const HelpSurface = {
  render: renderHost,
  args: { overlay: "help" },
};
