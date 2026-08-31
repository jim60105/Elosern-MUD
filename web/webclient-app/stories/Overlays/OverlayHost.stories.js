import { h } from "vue";
import OverlayHost from "../../components/OverlayHost.vue";
import MapOverlay from "../../components/MapOverlay.vue";
import SettingsOverlay from "../../components/SettingsOverlay.vue";
import HelpOverlay from "../../components/HelpOverlay.vue";
import { LOCAL_MAP_SAMPLE, localMapModelFor } from "../fixtures.js";

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
            mapModel: args.mapModel,
            locationLabel: "灰河帶",
            onClose: () => {},
            onMove: () => {},
          },
          {
            default: (slotProps) => {
              const { overlay, mapModel } = slotProps;
              if (overlay === "map") {
                // Wave 0: the map family binds through the shared
                // derived-shape helper, so even this fallback is the exact
                // store model shape.
                return h(MapOverlay, {
                  localMap: mapModel || localMapModelFor(LOCAL_MAP_SAMPLE),
                  onMove: () => {},
                  onOpenMap: () => {},
                });
              }
              if (overlay === "settings") {
                return h(SettingsOverlay, {
                  fontScale: 1,
                  textToHtml: true,
                  reducedMotion: null,
                  colorblind: false,
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
  args: { overlay: "map", mapModel: localMapModelFor(LOCAL_MAP_SAMPLE) },
};

export const SettingsSurface = {
  render: renderHost,
  args: { overlay: "settings", mapModel: null },
};

export const HelpSurface = {
  render: renderHost,
  args: { overlay: "help", mapModel: null },
};
