// The travel group of the composed Elosern store (OpenSpec change
// wilderness-travel-interface): the committed travel selection and the active
// stage's map state, published as `view.travel`.
//
// - The selection (`mode`, `layout`, `room`) is a pure projection of the
//   committed state (components/travel/travel-model.js); nothing selects it
//   from prose, a click or a cached scene.
// - The map state is written by the one refresh owner
//   (composables/use-travel-map.js) through `setTravelMap`: its status
//   (ready | refreshing | unavailable | invalid | retired) and the area body
//   it last adopted from a correlated complete response. `map` is that body's
//   decoded grid and `mapReady` is true only at `ready`.
// - The recovery signal records every accepted full snapshot (an external
//   server snapshot or an explicit sync's completion) at the transport
//   acceptance seam, so the refresh owner can ask for the area once even
//   when position and time did not change. On-demand maps always arrive on
//   `ui_update`, so the owner's own map completions never raise it.

import { ref } from "vue";
import { travelSelection } from "../../components/travel/travel-model.js";
import { decodeTravelGrid } from "../../lib/travel-grid.js";

export const TRAVEL_MAP_STATUSES = Object.freeze(["ready", "refreshing", "unavailable", "invalid", "retired"]);

export function applyTravel(ctx) {
  ctx.travelMap = { status: "refreshing", area: null, grid: null };
  ctx.travelRecovery = ref(null);

  ctx.setTravelMap = function setTravelMap({ status, area }) {
    if (!TRAVEL_MAP_STATUSES.includes(status)) return;
    const body = area ?? null;
    if (ctx.travelMap.status === status && ctx.travelMap.area === body) return;
    // The grid is decoded once per adopted body, not once per publication.
    const grid = body === ctx.travelMap.area ? ctx.travelMap.grid : decodeTravelGrid(body);
    ctx.travelMap = { status, area: body, grid };
    ctx.publishView();
  };

  ctx.noteRecoveryPublication = function noteRecoveryPublication(generation, epoch, revision) {
    ctx.travelRecovery.value = Object.freeze({ generation, epoch, revision });
  };

  ctx.travelView = function travelView(rs) {
    const selection = travelSelection({
      mode: rs.mode,
      panels: rs.panels || {},
      creation: ctx.creation != null,
    });
    return Object.freeze({
      ...selection,
      map: ctx.travelMap.grid,
      mapReady: ctx.travelMap.status === "ready",
      mapStatus: ctx.travelMap.status,
      area: ctx.travelMap.area,
    });
  };
}
