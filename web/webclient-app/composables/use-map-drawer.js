// The map drawer's session workflow (OpenSpec change redesign-map-drawer;
// approved design docs/superpowers/specs/2026-10-22-world-map-drawer-design.md
// §5.1/§6.4). It owns, for the AppClient host:
//
// - the active scope tab (區域 / 世界), chosen by the current layer every
//   time the drawer opens (world in the wilderness, area everywhere else);
// - the per-tab session memory (`view` and `selected` for each tab), scoped
//   to the transport generation and presentation epoch, so a reconnect or a
//   puppet change never shows the previous character's views;
// - the area memory key (`map_id|frame.key|frame.unit`): an area body of
//   another map or coordinate frame clears the area view and selection
//   synchronously, before the view renders the new body;
// - the on-demand `map.view` requests: one for the active scope when the
//   drawer opens or switches tab, and one after each committed move while it
//   is open — never on input, on a rejected move or while closed.
//
// A request rides the store's single in-flight lock and its admission
// rules. No queue exists: one coalesced pending scope is sent when the lock
// frees, and it is dropped on close or when the session scope changes.
// The server never learns whether the drawer is open.
import { computed, reactive, ref, watch } from "vue";

export const MAP_SCOPES = Object.freeze(["area", "world"]);

/** The scope the drawer opens on for a `local_map` layer. */
export function scopeForLayer(layer) {
  return layer === "wilderness" ? "world" : "area";
}

/** The area memory key of an available `area_map` body, else null. */
export function areaMemoryKey(area) {
  if (!area || area.available !== true || !area.frame) return null;
  return `${area.map_id}|${area.frame.key}|${area.frame.unit}`;
}

function blankMemory() {
  return {
    area: { key: null, view: undefined, selected: undefined },
    world: { view: undefined, selected: undefined },
  };
}

export function useMapDrawer(store, { onMapMove }) {
  const open = computed(() => store.view.hudOverlay === "map");
  const sessionScope = computed(() => `${store.view.generation}|${store.view.epoch}`);
  const tab = ref("area");
  const memory = reactive(blankMemory());

  // The scope waiting for the lock, the map.view request in flight, and the
  // drawer's own move whose committed result triggers a refresh.
  const pendingScope = ref(null);
  const awaiting = ref(null);
  const trackedMove = ref(null);
  // Results observed before this opening never trigger a refresh.
  let baselineResultId = null;

  function resetMemory() {
    const fresh = blankMemory();
    memory.area = fresh.area;
    memory.world = fresh.world;
  }

  function resultOf() {
    return store.view.lastActionResult ?? null;
  }

  function lockFree() {
    return !store.view.dispatch?.inFlight;
  }

  function flush() {
    if (!open.value || pendingScope.value === null || !lockFree()) return;
    const scope = pendingScope.value;
    const requestId = store.dispatchAction("map.view", { scope }, null);
    if (requestId) {
      pendingScope.value = null;
      awaiting.value = { requestId, scope, epoch: store.view.epoch };
    }
  }

  function request(scope) {
    // The scope already on its way needs no second request.
    if (pendingScope.value === null && awaiting.value?.scope === scope) return;
    pendingScope.value = scope;
    flush();
  }

  // Opening chooses the scope from the current layer and requests it;
  // closing drops anything still pending (a response that lands later only
  // refreshes the stored map, which the next opening re-requests anyway).
  watch(
    open,
    (isOpen) => {
      if (isOpen) {
        baselineResultId = resultOf()?.requestId ?? null;
        trackedMove.value = null;
        awaiting.value = null;
        tab.value = scopeForLayer(store.view.localMapModel?.layer ?? null);
        request(tab.value);
      } else {
        pendingScope.value = null;
        awaiting.value = null;
        trackedMove.value = null;
      }
    },
    // Synchronous, so the baseline is the result standing at the moment the
    // drawer opens, before any queued result watcher looks at it.
    { immediate: true, flush: "sync" },
  );

  watch(tab, (scope) => {
    if (open.value) request(scope);
  });

  // A new transport generation or presentation epoch retires every view,
  // selection and pending request of the previous session; an open drawer
  // asks the new session for its active scope.
  watch(sessionScope, () => {
    resetMemory();
    pendingScope.value = null;
    awaiting.value = null;
    trackedMove.value = null;
    baselineResultId = resultOf()?.requestId ?? null;
    if (open.value) request(tab.value);
  });

  // A disconnect drops the pending slot: nothing is sent into a session the
  // drawer has not seen yet (the reconnect's new scope re-requests).
  watch(
    () => store.view.connected,
    (connected) => {
      if (!connected) {
        pendingScope.value = null;
        awaiting.value = null;
      }
    },
  );

  // The area memory belongs to one map and coordinate frame. The reset is
  // synchronous so the view never renders the new body with the previous
  // frame's pan, zoom or selection.
  watch(
    () => areaMemoryKey(store.view.maps?.area_map),
    (key) => {
      if (key !== null && key !== memory.area.key) {
        memory.area = { key, view: undefined, selected: undefined };
      }
    },
    { flush: "sync", immediate: true },
  );

  // Result settlement. A move is committed when its own result (request id
  // and epoch) is a success and the in-flight lock has released, which the
  // store does only once the committed revision reached the result's
  // declared presentation revision. A move dispatched elsewhere while the
  // drawer is open (none is reachable behind the modal today) is recognised
  // by its committed `moved` result code.
  watch(
    () => [resultOf(), store.view.dispatch?.inFlight ?? null, store.view.revision],
    () => {
      const result = resultOf();
      if (!open.value) return;
      if (awaiting.value && result && result.requestId === awaiting.value.requestId && lockFree()) {
        awaiting.value = null;
      }
      if (!result || result.requestId === baselineResultId || result.epoch !== store.view.epoch) {
        flush();
        return;
      }
      const ours = trackedMove.value && result.requestId === trackedMove.value.requestId && result.epoch === trackedMove.value.epoch;
      const foreignMove = !trackedMove.value && result.code === "moved";
      if ((ours || foreignMove) && lockFree()) {
        baselineResultId = result.requestId;
        trackedMove.value = null;
        if (result.outcome === "success") {
          pendingScope.value = tab.value;
        }
      } else if (ours && result.outcome !== "success") {
        // A rejected move refreshes nothing; the lock may still be held
        // until its recovery commits, but no refresh will follow.
        baselineResultId = result.requestId;
        trackedMove.value = null;
      }
      flush();
    },
  );

  // Any change of the store's admission inputs retries the one pending slot.
  watch(
    () => [
      store.view.connected,
      store.view.phase,
      store.view.mutationsLocked,
      store.view.dispatch?.beatLocked ?? false,
    ],
    flush,
  );

  // True while the drawer shows a body older than the committed state, or
  // the lock would refuse a move anyway: 前往 waits instead of being
  // refused, and a stale current node is never forwarded.
  const busy = computed(
    () =>
      pendingScope.value !== null ||
      awaiting.value !== null ||
      trackedMove.value !== null ||
      !lockFree() ||
      !store.view.connected ||
      store.view.mutationsLocked === true ||
      store.view.phase !== "active" ||
      store.view.dispatch?.beatLocked === true,
  );

  // The drawer's 前往: the exact area-view descriptor with that body's
  // canonical current node, through the shared minimap move seam.
  function onDrawerMove(payload) {
    if (busy.value || !payload) return null;
    const requestId = onMapMove(payload);
    if (requestId) {
      trackedMove.value = { requestId, epoch: store.view.epoch };
    }
    return requestId;
  }

  // Opening the world tab on a commission the area tab cannot place.
  function showOnWorld(questId) {
    memory.world.selected = `quest:${questId}`;
    tab.value = "world";
  }

  return {
    mapDrawerOpen: open,
    mapTab: tab,
    mapMemory: memory,
    mapEpoch: sessionScope,
    mapBusy: busy,
    onMapDrawerMove: onDrawerMove,
    onMapShowOnWorld: showOnWorld,
  };
}
