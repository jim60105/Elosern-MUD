import { h } from "vue";
import MapLattice from "../../components/MapLattice.vue";
import {
  LOCAL_MAP_GEOMETRY_STRESS_SAMPLE,
  LOCAL_MAP_INSTANCE_SAMPLE,
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_SINGLE_NODE_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  localMapModelFor,
} from "../fixtures.js";

// MapLattice: the minimap island's `local_map` renderer (the full map is
// the map drawer's area and world views since redesign-map-drawer). The
// stories feed the reduced render model (exactly what the store builds in
// production) through the shared `localMapModelFor` helper.

// The minimap island's fixed 240px canvas (the island sits at the top of the
// stage's `map` anchor). Island-scale stories fill it the way the island
// does, so a story shows the same canvas the minimap draws rather than a
// natural-size one.
const renderLattice = (args) => ({
  render: () =>
    h("div", { style: "width: 240px;" }, [h(MapLattice, args)]),
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
    canvasSize: 240,
    labelFont: 16,
    showAxis: true,
    fogVignette: true,
    markerNames: true,
  };
};

// Island (minimap) scale: the fixed 240-unit square, 4-char radial label
// truncation, markerScale 1 and the shared 16-unit label steps.
// IslandScaleSample carries an outside-extent remembered place, so the
// lattice variant draws its edge direction marker on the island's rim.
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

// Task 3.6: Draft lattice fidelity stories (webclient-minimap-06-draft-lattice-fidelity)

// Sparse payload: one marker centered in roughly three and a half coordinate cells of dot field (pitch 60)
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
