import { h } from "vue";
import LocalMap from "../../components/LocalMap.vue";
import {
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// LocalMap (B4 world family): renders the committed `local_map` v1 panel —
// an SVG lattice whose node markers encode visibility by non-color shape
// (square / open circle / filled circle / diamond), the legend with state
// glyphs, and the detail line. Nodes carrying the payload's own exact
// `move` action are actionable: activating one emits `move` with its
// exit_ref and destination. Nothing is invented; unavailable payloads render
// only the registry-owned reason message.

const renderMap = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(LocalMap, args),
    ]),
});

export default {
  title: "World/LocalMap",
  component: LocalMap,
};

export const FullLattice = {
  render: renderMap,
  args: {
    localMap: LOCAL_MAP_SAMPLE,
  },
};

export const Minimal = {
  render: renderMap,
  args: {
    localMap: LOCAL_MAP_MINIMAL_SAMPLE,
  },
};

export const Unavailable = {
  render: renderMap,
  args: {
    localMap: LOCAL_MAP_UNAVAILABLE_SAMPLE,
  },
};
