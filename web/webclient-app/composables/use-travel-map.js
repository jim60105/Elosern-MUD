// The active travel stage's area refresh owner (OpenSpec change
// wilderness-travel-interface, design "Current-protocol adapter and refresh
// owner"). It is the one requester of `map.view {scope: "area"}` while the
// travel layout is shown; the map drawer keeps its own requests and never
// asks for the area in travel.
//
// Refresh causes, and only these, while the layout is shown:
//   - entering the layout;
//   - a committed change of the canonical current node or the world time;
//   - a completed `explore.look`;
//   - an accepted full snapshot (an external one or an explicit sync's
//     completion), once per publication identity, even at unchanged
//     position and time;
//   - the player's own retry after a failed read (an explicit input, never a
//     timer).
// Aim, hover, resize, render and a failed move change none of these inputs,
// so they never refresh. Causes coalesce into one pending slot that is sent
// through the store's single dispatch gate when it is free; nothing polls.
//
// A request is adopted exactly like the drawer's world baseline
// (use-map-drawer.js): its own result (request id, epoch) declares the
// presentation revision, and only the `area_map` publication at exactly that
// revision, newer than the mark taken at send time, is its body. Result and
// body may arrive in either order; a partial transfer never advances the
// revision, and an older or foreign-epoch response never matches.
//
// Status: `refreshing` while a cause waits (the last adopted map stays,
// dimmed; a first load has no map and shows fog), `ready` once a correlated
// complete available body is adopted with no cause pending, `unavailable`
// for a refused read or an unavailable body, `invalid` for a body the stage
// cannot read, `retired` after a transport generation or epoch change. A
// failed state stays until another cause. The state is published through the
// store (`view.travel`), the single source every surface reads.
import { computed, watch } from "vue";
import { decodeTravelGrid } from "../lib/travel-grid.js";

const FAILED = new Set(["unavailable", "invalid", "retired"]);

export function useTravelMap(store) {
  const layout = computed(() => !!store.view.travel?.layout);
  // A drawer or a full-screen overlay owns input: refreshes wait for it.
  const owned = computed(() => layout.value && !store.view.hudOverlay && !store.view.hudDrawer);
  const session = computed(() => `${store.view.generation}|${store.view.epoch}`);

  let status = "refreshing";
  let adopted = null;
  let pending = false;
  let awaiting = null;
  let lookRequest = null;
  const seenRecovery = new Set();

  function publish() {
    store.setTravelMap({ status, area: adopted });
  }

  function setStatus(next) {
    status = next;
    publish();
  }

  // Every cause one publication raises (entry, a changed node or time, a
  // recovery snapshot) runs in the same watcher pass; the send waits for the
  // pass to end, so they all leave as one request.
  let flushQueued = false;
  // The canonical place and time a request was sent at, and the recovery
  // publications it already covers: a cause observed later for the same
  // publication is answered by that request and asks nothing more.
  let sentKey = null;
  function placeKey() {
    return `${store.view.panels?.local_map?.current_node ?? ""}|${JSON.stringify(store.view.serverTime ?? null)}`;
  }
  function recoveryKey(signal) {
    return signal ? `${signal.generation}|${signal.epoch}|${signal.revision}` : null;
  }

  function want() {
    if (!layout.value) return;
    pending = true;
    if (status !== "refreshing") setStatus("refreshing");
    if (flushQueued) return;
    flushQueued = true;
    Promise.resolve().then(() => {
      flushQueued = false;
      flush();
    });
  }

  function admitted() {
    const v = store.view;
    return v.connected && v.phase === "active" && !v.mutationsLocked && !v.dispatch?.inFlight && !v.dispatch?.beatLocked;
  }

  function flush() {
    if (!owned.value || !pending || awaiting || !admitted()) return;
    const mark = store.view.mapPublications?.area_map ?? -1;
    const requestId = store.dispatchAction("map.view", { scope: "area" }, null);
    if (!requestId) return;
    pending = false;
    awaiting = { requestId, session: session.value, mark, revision: null };
    sentKey = placeKey();
    const covered = recoveryKey(store.travelRecovery);
    if (covered) seenRecovery.add(covered);
  }

  function adopt(body) {
    if (!body || body.available === false) {
      setStatus("unavailable");
    } else if (decodeTravelGrid(body) === null) {
      setStatus("invalid");
    } else {
      adopted = body;
      // A cause that arrived meanwhile still owes a fresher map.
      setStatus(pending ? "refreshing" : "ready");
    }
  }

  function settle() {
    const v = store.view;
    const result = v.lastActionResult ?? null;
    if (awaiting && awaiting.session !== session.value) awaiting = null;
    if (awaiting && awaiting.revision === null && result &&
        result.requestId === awaiting.requestId && result.epoch === v.epoch) {
      if (result.outcome === "success") {
        awaiting.revision = result.presentationRevision;
      } else {
        awaiting = null;
        setStatus("unavailable");
      }
    }
    if (awaiting && awaiting.revision !== null && v.revision !== null && v.revision >= awaiting.revision) {
      const publication = v.mapPublications?.area_map;
      const own = publication === awaiting.revision && publication > awaiting.mark;
      awaiting = null;
      if (own) adopt(v.maps?.area_map ?? null);
      else setStatus("unavailable");
    }
    // A completed room look owes the stage a fresh map.
    if (lookRequest && result && result.requestId === lookRequest.requestId && result.epoch === lookRequest.epoch) {
      const success = result.outcome === "success";
      lookRequest = null;
      if (success) want();
    }
    flush();
  }

  // A new transport generation or epoch retires the adopted map and every
  // pending request; that session's own snapshot is the next cause.
  watch(session, () => {
    adopted = null;
    awaiting = null;
    pending = false;
    lookRequest = null;
    setStatus("retired");
  });

  watch(
    layout,
    (shown) => {
      if (shown) {
        want();
        return;
      }
      // Leaving drops the slot and the map: a late response is ignored, and
      // a later entry starts from the first-load fog, never from a map of
      // another place.
      pending = false;
      awaiting = null;
      adopted = null;
      setStatus("refreshing");
    },
    { immediate: true },
  );

  watch(placeKey, (now, before) => {
    if (before !== undefined && now !== before && now !== sentKey) want();
  });

  // A room look: remember the request while it is the one in flight.
  watch(
    () => store.view.dispatch?.inFlight?.requestId ?? null,
    (requestId) => {
      if (requestId && store.view.dispatch?.inFlightActionId === "explore.look") {
        lookRequest = { requestId, epoch: store.view.epoch };
      }
    },
  );

  watch(
    // Pinia unwraps the store's ref, so this reads the signal itself.
    () => store.travelRecovery ?? null,
    (signal) => {
      const identity = recoveryKey(signal);
      if (!identity) return;
      if (seenRecovery.has(identity)) return;
      seenRecovery.add(identity);
      want();
    },
  );

  watch(
    () => [store.view.lastActionResult, store.view.revision, store.view.mapPublications?.area_map, store.view.dispatch?.inFlight ?? null],
    settle,
  );

  watch(
    () => [owned.value, store.view.connected, store.view.phase, store.view.mutationsLocked, store.view.dispatch?.beatLocked ?? false],
    () => {
      if (!store.view.connected) {
        awaiting = null;
      }
      flush();
    },
  );

  /** The player's explicit retry of a failed read. */
  function retry() {
    if (layout.value && FAILED.has(status)) want();
  }

  return { retryTravelMap: retry };
}
