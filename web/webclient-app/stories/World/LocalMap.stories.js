import { h } from "vue";
import LocalMap from "../../components/LocalMap.vue";
import {
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_INSTANCE_SAMPLE,
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
} from "../fixtures.js";

// LocalMap (H2, webclient-hud-02-status-islands, design D9/D10): the
// minimap renders as the stage's right-anchor island — bounded, the
// renderer-axis orientation legend on the coordinate-bearing `grid` /
// `wilderness` layers only, no bearing, no distance, and no full-map
// control (MapOverlay is H5's). The stories below cover the island chrome
// across all four layers (grid / wilderness / instance / interior) plus the
// minimal and unavailable forms.

const renderMap = (args) => ({
  render: () =>
    h("div", { style: "width: 230px;" }, [h(LocalMap, args)]),
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

export const Wilderness = {
  render: renderMap,
  args: {
    localMap: LOCAL_MAP_WILDERNESS_SAMPLE,
  },
};

export const Instance = {
  render: renderMap,
  args: {
    localMap: LOCAL_MAP_INSTANCE_SAMPLE,
  },
};

export const Interior = {
  render: renderMap,
  args: {
    localMap: LOCAL_MAP_INTERIOR_SAMPLE,
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
