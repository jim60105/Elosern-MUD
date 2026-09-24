/**
 * Shared fixtures for the split map_lattice.test.js siblings.
 *
 * Not a test file: the vitest gate collects `*.test.js` only, so this module
 * is imported, never collected. The payload literals and the overlay prop set
 * moved verbatim from the original map_lattice.test.js; the shared lattice
 * mount helper existed twice there byte-identically and now lives once here,
 * parameterised with a setter so each sibling keeps its closure-local
 * `wrapper` and `afterEach` unmount exactly as before.
 */

import { mount } from "@vue/test-utils";
import MapLattice from "../../components/MapLattice.vue";
import { LOCAL_MAP_SAMPLE, localMapModelFor } from "../../stories/fixtures.js";

// Wave 0 & 1 (webclient-minimap-05-edge-markers-replace-list):
  // Named edge markers on the island and overlay.
  const REPORTED_WILDERNESS_PAYLOAD = {
    schema_version: 1,
    available: true,
    layer: "wilderness",
    title: "西部荒野",
    current_node: "w:1:1",
    nodes: [
      { id: "w:0:0", label: "0,0", x: 0, y: 0, visibility: "visible_visited", current: false },
      { id: "w:1:0", label: "1,0", x: 1, y: 0, visibility: "visible_visited", current: false },
      { id: "w:2:0", label: "2,0", x: 2, y: 0, visibility: "visible_visited", current: false },
      { id: "w:0:1", label: "0,1", x: 0, y: 1, visibility: "visible_visited", current: false },
      { id: "w:1:1", label: "1,1", x: 1, y: 1, visibility: "current", current: true },
      { id: "w:2:1", label: "2,1", x: 2, y: 1, visibility: "visible_visited", current: false },
      { id: "w:0:2", label: "0,2", x: 0, y: 2, visibility: "visible_visited", current: false },
      { id: "w:1:2", label: "1,2", x: 1, y: 2, visibility: "visible_visited", current: false },
      { id: "w:2:2", label: "2,2", x: 2, y: 2, visibility: "visible_visited", current: false },
      { id: "r:west", label: "西部丘陵與谷地（南門）", x: -10, y: 1, visibility: "remembered", landmark: true },
      { id: "r:east", label: "聖潔王都", x: 10, y: 1, visibility: "remembered", landmark: true },
    ],
    edges: [],
  };

  const UNIFORM_WILDERNESS_PAYLOAD = {
    schema_version: 1,
    available: true,
    layer: "wilderness",
    title: "西部荒野",
    current_node: "w:1:1",
    nodes: [
      { id: "w:0:0", label: "西部荒野", x: 0, y: 0, visibility: "visible_visited" },
      { id: "w:1:0", label: "西部荒野", x: 1, y: 0, visibility: "visible_visited" },
      { id: "w:2:0", label: "西部荒野", x: 2, y: 0, visibility: "visible_visited" },
      { id: "w:0:1", label: "西部荒野", x: 0, y: 1, visibility: "visible_visited" },
      { id: "w:1:1", label: "西部荒野", x: 1, y: 1, visibility: "current", current: true },
      { id: "w:2:1", label: "西部荒野", x: 2, y: 1, visibility: "visible_visited" },
      { id: "w:0:2", label: "西部荒野", x: 0, y: 2, visibility: "visible_visited" },
      { id: "w:1:2", label: "西部荒野", x: 1, y: 2, visibility: "visible_visited" },
      { id: "w:2:2", label: "西部荒野", x: 2, y: 2, visibility: "visible_visited" },
      { id: "r:west", label: "西部丘陵與谷地（南門）", x: -10, y: 1, visibility: "remembered", landmark: true },
      { id: "r:east", label: "聖潔王都", x: 10, y: 1, visibility: "remembered", landmark: true },
    ],
    edges: [],
  };

  export const OVERLAY_PROPS = {
    colPitch: 280,
    rowPitch: 212,
    labelMax: 10,
    markerScale: 4.83,
    overlayChrome: true,
    markerNames: true,
    markerNameFont: 11,
  };

export function mountLattice(setWrapper, props = {}) {
  const wrapper = mount(MapLattice, {
    props: {
      localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
      ...props,
    },
  });
  setWrapper(wrapper);
  return wrapper;
}

export { REPORTED_WILDERNESS_PAYLOAD, UNIFORM_WILDERNESS_PAYLOAD };
