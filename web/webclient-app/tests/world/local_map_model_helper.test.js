import { describe, expect, it } from "vitest";
import LocalMapModel from "../../lib/local_map.js";
import {
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";

// Wave 0 (webclient-map-00-story-fidelity, design D1): the shared story
// helper must stay byte-identical to the store's `localMapModel` construction
// (`stores/elosern.js`): `{ ...reducePanel(panel), available: panel.available
// !== false, reason: panel.reason }`. The store inlines that expression, so
// this test restates it verbatim as the parity reference — any drift between
// the helper and the production shape fails here, and the unavailable form
// must keep the registry-owned reason (the rebind must not blank it).
function storeShape(panel) {
  return {
    ...LocalMapModel.reducePanel(panel),
    available: panel.available !== false,
    reason: panel.reason,
  };
}

describe("localMapModelFor — the exact store-side conversion", () => {
  it("matches the store construction field-for-field for an available fixture", () => {
    expect(localMapModelFor(LOCAL_MAP_SAMPLE)).toEqual(storeShape(LOCAL_MAP_SAMPLE));
    // Spot-check the fields the components read.
    const model = localMapModelFor(LOCAL_MAP_SAMPLE);
    expect(model.available).toBe(true);
    expect(model.reason).toBeUndefined();
    expect(model.currentNode).toBe(LOCAL_MAP_SAMPLE.current_node);
    expect(model.cols).toBeGreaterThan(0);
    expect(model.rows).toBeGreaterThan(0);
    expect(model.nodes.every((n) => Number.isInteger(n.col) && Number.isInteger(n.row))).toBe(true);
  });

  it("preserves the registry-owned reason for the unavailable fixture", () => {
    const model = localMapModelFor(LOCAL_MAP_UNAVAILABLE_SAMPLE);
    expect(model).toEqual(storeShape(LOCAL_MAP_UNAVAILABLE_SAMPLE));
    expect(model.available).toBe(false);
    expect(model.reason).toEqual(LOCAL_MAP_UNAVAILABLE_SAMPLE.reason);
    expect(model.reason.message).toBe("區域地圖目前無法顯示");
  });

  it("never mutates the fixture it converts", () => {
    const snapshot = JSON.stringify(LOCAL_MAP_SAMPLE);
    localMapModelFor(LOCAL_MAP_SAMPLE);
    expect(JSON.stringify(LOCAL_MAP_SAMPLE)).toBe(snapshot);
  });
});
