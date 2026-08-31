import { h } from "vue";
import MapLattice from "../../components/MapLattice.vue";
import {
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  localMapModelFor,
} from "../fixtures.js";

// MapLattice (improve-webclient-map-overlay-scale): the shared `local_map`
// lattice renderer, parameterized by scale. The stories feed the reduced
// render model (exactly what the store builds in production) through the
// shared `localMapModelFor` helper (wave 0, design D1: one shared binding,
// the old private copy deleted), reusing the existing `local_map` fixtures
// so both surfaces render the identical committed payload.

const renderLattice = (args) => ({
  render: () =>
    h("div", { style: "width: 230px;" }, [h(MapLattice, args)]),
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

// Island (minimap) scale: the crowding fix's decoupled pitches (58px
// column / 44px row), 4-char label truncation, markerScale 1.
export const IslandScaleSample = {
  render: renderLattice,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
  },
};

export const IslandScaleWilderness = {
  render: renderLattice,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE),
  },
};

export const IslandScaleMinimal = {
  render: renderLattice,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_MINIMAL_SAMPLE),
  },
};

// Overlay scale: the full-map overlay's larger pitches (280px column /
// 212px row), 10-char labels, 4.83x markers, fill-width layout at the
// 848px body content width.
export const OverlayScaleSample = {
  render: renderOverlayScale,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
  },
};

export const OverlayScaleWilderness = {
  render: renderOverlayScale,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE),
  },
};

export const OverlayScaleMinimal = {
  render: renderOverlayScale,
  args: {
    localMap: localMapModelFor(LOCAL_MAP_MINIMAL_SAMPLE),
  },
};
