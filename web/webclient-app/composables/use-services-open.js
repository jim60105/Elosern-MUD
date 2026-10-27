// services-open (npc-targeted-service-flows): the selected provider's private,
// correlated services read.
//
// A service drawer opened from a provider dispatches one `services.open
// {npc_id}` and renders only that read's own result (`{npc_id, services}`),
// never the room-wide summary as if it were the selection. Adopting a result
// requires the exact two-field wrapper, the provider the slot asked for, and
// every shipped section naming that same provider; anything else is discarded
// so a stale, foreign or substituted response never reopens UI.
//
// Refresh ownership: while a slot is open, a committed presentation revision
// (a purchase, a registration, a quest write) repeats the read for the same
// provider once nothing is in flight. `services.open` publishes no panel of
// its own, so a read cannot trigger another read. The selection is never
// persisted on the actor or the NPC.
import { computed, ref, watch } from "vue";
import Protocol from "../../static/webclient/js/elosern/protocol.js";

const ACTION_ID = "services.open";
const REQUIRED_SECTIONS = ["guild", "rank", "shop"];

function isProviderId(value) {
  return Number.isSafeInteger(value) && value > 0;
}

// Exactly `{npc_id, services}` with every shipped section naming the same
// provider, and the panel conforming to schema 8.
function admissible(data, providerId) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return false;
  if (Object.keys(data).sort().join(",") !== "npc_id,services") return false;
  if (data.npc_id !== providerId) return false;
  const services = data.services;
  if (!services || services.available !== true) return false;
  for (const key of REQUIRED_SECTIONS) {
    const section = services[key];
    if (section !== null && section !== undefined && section.provider_id !== providerId) return false;
  }
  try {
    Protocol.validateServicesPanel(services);
  } catch {
    return false;
  }
  return true;
}

export function useServicesOpen(store, { dispatchIntent }) {
  // slot -> { providerId, requestId, epoch, generation, snapshot }
  const bindings = ref({});
  // slot -> { providerId, requestId, epoch, generation }
  const pending = ref({});

  function forget(slot) {
    if (!(slot in bindings.value) && !(slot in pending.value)) return;
    const nextBindings = { ...bindings.value };
    const nextPending = { ...pending.value };
    delete nextBindings[slot];
    delete nextPending[slot];
    bindings.value = nextBindings;
    pending.value = nextPending;
  }

  function dispatchRead(slot, providerId) {
    const requestId = dispatchIntent(ACTION_ID, { npc_id: providerId });
    if (!requestId) return null;
    pending.value = {
      ...pending.value,
      [slot]: {
        providerId,
        requestId,
        epoch: store.view.epoch,
        generation: store.view.generation,
      },
    };
    return requestId;
  }

  // Open (or re-target) one slot. Re-opening the already-bound provider is a
  // no-op: the committed snapshot is what its drawer renders.
  function openServices(slot, providerId) {
    if (!isProviderId(providerId)) {
      forget(slot);
      return null;
    }
    const current = bindings.value[slot];
    const waiting = pending.value[slot];
    if (current && current.providerId === providerId) return null;
    if (waiting && waiting.providerId === providerId) return null;
    return dispatchRead(slot, providerId);
  }

  function closeServices(slot) {
    forget(slot);
  }

  // Re-read every adopted slot whose committed revision moved on, once no
  // request is in flight. A read that has not settled yet keeps its slot.
  function refreshBindings() {
    if (store.view.dispatch?.inFlight) return;
    for (const [slot, binding] of Object.entries(bindings.value)) {
      if (pending.value[slot]) continue;
      if (binding.revision === store.view.revision) continue;
      dispatchRead(slot, binding.providerId);
    }
  }

  // The committed snapshot of one slot, or null while it is not adopted.
  const snapshots = computed(() => {
    const result = {};
    for (const [slot, binding] of Object.entries(bindings.value)) {
      result[slot] = binding.snapshot;
    }
    return result;
  });

  // A transport or puppet change makes every pending and adopted read stale.
  watch([() => store.view.epoch, () => store.view.generation], () => {
    bindings.value = {};
    pending.value = {};
  });

  // Adopt only this read's own result. A rejection drops the slot's snapshot:
  // the provider left, lost its capability or failed its gates.
  watch(
    () => store.view.lastActionResult,
    (result) => {
      if (!result || typeof result.requestId !== "string") return;
      const ownRead = Object.values(pending.value).some(
        (entry) => entry.requestId === result.requestId,
      );
      for (const [slot, entry] of Object.entries(pending.value)) {
        if (entry.requestId !== result.requestId) continue;
        const nextPending = { ...pending.value };
        delete nextPending[slot];
        pending.value = nextPending;
        if (result.epoch !== undefined && result.epoch !== entry.epoch) return;
        if (store.view.epoch !== entry.epoch || store.view.generation !== entry.generation) return;
        if (result.outcome !== "success" || !admissible(result.data, entry.providerId)) {
          forget(slot);
          return;
        }
        bindings.value = {
          ...bindings.value,
          [slot]: {
            providerId: entry.providerId,
            requestId: entry.requestId,
            epoch: entry.epoch,
            generation: entry.generation,
            revision: store.view.revision,
            snapshot: result.data.services,
          },
        };
        return;
      }
      // Another action settled: a committed revision waits for its own read.
      if (!ownRead) refreshBindings();
    },
  );

  // Committed-state refresh: the same provider is read again once the in-flight
  // request settles, so a purchase, registration or quest write is reflected
  // without ever falling back to the room summary. A read itself publishes no
  // panel, so this cannot loop.
  watch(
    () => store.view.revision,
    () => refreshBindings(),
  );

  return { openServices, closeServices, snapshots };
}
