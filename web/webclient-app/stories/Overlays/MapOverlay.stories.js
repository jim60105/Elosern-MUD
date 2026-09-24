import { h } from "vue";
import MapOverlay from "../../components/MapOverlay.vue";
import {
  LOCAL_MAP_GEOMETRY_STRESS_SAMPLE,
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
  localMapModelFor,
} from "../fixtures.js";

// MapOverlay (webclient-full-map-fit-view D1/D7): the full-map body content.
// Each story stages one committed payload form — the full lattice, the
// minimal lattice, a tall street, and the registry-owned unavailable reason —
// inside a dark 900x600 stage with a bordered container, so the overlay's
// fitted view opens the WHOLE drawing inside the stage (no body scrollbar)
// and the reader zooms instead of scrolling. Nothing is invented: the
// unavailable story shows only the payload's reason.message.
//
// Wave 0 (webclient-map-00-story-fidelity): every `localMap` arg binds
// through the shared `localMapModelFor` helper — the EXACT derived shape the
// store passes in production — never the raw payload.
const renderOverlay = (args) => ({
  render: () =>
    h(
      "div",
      {
        style:
          "position: relative; width: 900px; height: 600px; overflow: hidden; " +
          "border: 1px solid var(--ink-700); border-radius: 12px; " +
          "background: var(--ink-950);",
      },
      [h(MapOverlay, args)]
    ),
});

export default {
  title: "Overlays/MapOverlay",
  component: MapOverlay,
};

export const FullLattice = {
  render: renderOverlay,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
  },
};

export const InteriorWithRemembered = {
  render: renderOverlay,
  args: {
    // Remembered rooms travel in the payload's `nodes` list with
    // `visibility: "remembered"`; the model splits them into `remembered`.
    localMap: localMapModelFor({
      ...LOCAL_MAP_INTERIOR_SAMPLE,
      nodes: [
        ...LOCAL_MAP_INTERIOR_SAMPLE.nodes,
        { id: "room:rem1", label: "公會倉庫", x: 0, y: 5, visibility: "remembered", landmark: false },
        { id: "room:rem2", label: "檔案室", x: 2, y: 5, visibility: "remembered", landmark: true },
      ],
    }),
  },
};

export const Minimal = {
  render: renderOverlay,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_MINIMAL_SAMPLE),
  },
};

export const Unavailable = {
  render: renderOverlay,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_UNAVAILABLE_SAMPLE),
  },
};

// Graph variant (webclient-map-02): the overlay passes the model's resolved
// `layoutVariant` through to the shared renderer — the interior payload's
// radial placement fills the mapcanvas, with the pin over the current node
// and no lattice axis legend.
export const RadialGraph = {
  render: renderOverlay,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE),
  },
};

// The fitted view's reason to exist (webclient-full-map-fit-view): the tall
// geometry-stress street payload opens wholly inside the stage at its fitted
// scale instead of running down a scrolling body.
export const TallLattice = {
  render: renderOverlay,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE),
  },
};
