import { h } from "vue";
import MapLattice from "../../components/MapLattice.vue";
import {
  LOCAL_MAP_GEOMETRY_STRESS_SAMPLE,
  LOCAL_MAP_INSTANCE_SAMPLE,
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_SINGLE_NODE_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  localMapModelFor,
} from "../fixtures.js";

// MapLattice (improve-webclient-map-overlay-scale): the shared `local_map`
// lattice renderer, parameterized by scale. The stories feed the reduced
// render model (exactly what the store builds in production) through the
// shared `localMapModelFor` helper (wave 0, design D1: one shared binding,
// the old private copy deleted), reusing the existing `local_map` fixtures
// so both surfaces render the identical committed payload.

// The island column's CONTENT box: the 230px hud-right anchor less the
// island's 9px padding and 1px border on each side. Island-scale stories fill
// it the way the island does, so a story shows the same canvas the minimap
// draws rather than a natural-size one.
const renderLattice = (args) => ({
  render: () =>
    h("div", { style: "width: 210px;" }, [h(MapLattice, args)]),
});

const renderOverlayScale = (args) => ({
  render: () =>
    h("div", { style: "width: 848px;" }, [
      h(MapLattice, {
        colPitch: 280,
        rowPitch: 212,
        labelMax: 10,
        markerScale: 4.83,
        maxWidth: 848,
        maxHeight: null,
        fillWidth: true,
        ...args,
      }),
    ]),
});
export default {
  title: "World/MapLattice",
  component: MapLattice,
};

// Layout variants (webclient-map-02-layout-variants D2): the surfaces pass
// the model's resolved `layoutVariant` — lattice for grid/wilderness
// payloads (rank-compressed grid placement + edge direction markers), graph
// for instance/interior payloads (radial placement, no markers). Stories
// pass it explicitly, mirroring what the surfaces wire.
const latticeOf = (fixture) => {
  const model = localMapModelFor(fixture);
  return {
    localMap: model,
    variant: model.layoutVariant,
    showLegend: false,
    fillWidth: true,
    colPitch: 40,
    rowPitch: 40,
    labelFont: 9,
    fieldFill: true,
    showAxis: true,
    fogVignette: true,
    markerNames: true,
  };
};

// Island (minimap) scale: the crowding fix's decoupled pitches (58px
// column / 44px row), 4-char label truncation, markerScale 1.
// IslandScaleSample carries an outside-extent remembered place, so the
// lattice variant draws its edge direction marker in the gutter (name-free
// on the island — the remembered list stays the canonical reading path).
export const IslandScaleSample = {
  render: renderLattice,
  args: latticeOf(LOCAL_MAP_SAMPLE),
};

export const IslandScaleWilderness = {
  render: renderLattice,
  args: latticeOf(LOCAL_MAP_WILDERNESS_SAMPLE),
};

export const IslandScaleMinimal = {
  render: renderLattice,
  args: latticeOf(LOCAL_MAP_MINIMAL_SAMPLE),
};

// Graph variant at island scale: the instance payload's radial placement —
// current at the centre, BFS rings around it, no edge direction markers.
export const IslandScaleRadial = {
  render: renderLattice,
  args: latticeOf(LOCAL_MAP_INSTANCE_SAMPLE),
};

// Overlay scale: the full-map overlay's larger pitches (280px column /
// 212px row), 10-char labels, 4.83x markers, fill-width layout at the
// 848px body content width. The overlay chrome mirrors MapOverlay.vue: it
// turns on the mapcanvas framing, the pin, and the marker NAME boxes.
const overlayOf = (fixture) => {
  const model = localMapModelFor(fixture);
  return {
    localMap: model,
    variant: model.layoutVariant,
    overlayChrome: true,
    showLegend: true,
    fillWidth: true,
    markerNames: true,
  };
};

export const OverlayScaleSample = {
  render: renderOverlayScale,
  args: overlayOf(LOCAL_MAP_SAMPLE),
};

export const OverlayScaleWilderness = {
  render: renderOverlayScale,
  args: overlayOf(LOCAL_MAP_WILDERNESS_SAMPLE),
};

export const OverlayScaleMinimal = {
  render: renderOverlayScale,
  args: overlayOf(LOCAL_MAP_MINIMAL_SAMPLE),
};

// Graph variant at the overlay's scale: the interior payload's radial
// placement with the mapcanvas chrome and the pin over the current node.
export const OverlayScaleRadial = {
  render: renderOverlayScale,
  args: overlayOf(LOCAL_MAP_INTERIOR_SAMPLE),
};

// Task 3.6: Draft lattice fidelity stories (webclient-minimap-06-draft-lattice-fidelity)

// Sparse payload: one marker centered in a five-cell coordinate dot field
export const IslandScaleSparse = {
  render: renderLattice,
  args: latticeOf(LOCAL_MAP_SINGLE_NODE_SAMPLE),
};

// Reported three-by-three wilderness payload
export const IslandScaleReportedWilderness = {
  render: renderLattice,
  args: latticeOf(LOCAL_MAP_WILDERNESS_SAMPLE),
};

// Adjacent-labelled-pair payload at 48-unit pitch
export const IslandScaleAdjacentLabelledPair = {
  render: renderLattice,
  args: latticeOf(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE),
};

// Overlay scale with coordinate dot field
export const OverlayScaleReportedWilderness = {
  render: renderOverlayScale,
  args: overlayOf(LOCAL_MAP_WILDERNESS_SAMPLE),
};
