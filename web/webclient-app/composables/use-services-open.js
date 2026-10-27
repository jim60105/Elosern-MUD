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
// A slot that has been targeted keeps its identity until the drawer closes or
// reselects: while its first read is in flight, and after a refusal, it has no
// snapshot and the drawer shows an unavailable surface rather than the room
// summary, so a flow opened for one NPC can never be completed against
// another. A dispatch the store refuses (one action is already in flight) is
// remembered and replayed once the store is free, so an opening that races a
// mutation still reads its provider.
//
// Refresh ownership: while a slot holds a snapshot, a committed presentation
// revision (a purchase, a registration, a quest write) repeats the read for
// the same provider once nothing is in flight. `services.open` publishes no
// panel of its own, so a read cannot trigger another read. The selection is
// never persisted on the actor or the NPC.
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
  // slot -> { providerId, requestId, epoch, generation, revision, snapshot, refusal }
  const slots = ref({});
  // slot -> providerId the drawer asked for but the store would not dispatch yet
  const wanted = ref({});

  function clearSlot(slot) {
    if (!(slot in slots.value) && !(slot in wanted.value)) return;
    const nextSlots = { ...slots.value };
    const nextWanted = { ...wanted.value };
    delete nextSlots[slot];
    delete nextWanted[slot];
    slots.value = nextSlots;
    wanted.value = nextWanted;
  }

  function dispatchRead(slot, providerId) {
    const previous = slots.value[slot];
    const sameProvider = previous && previous.providerId === providerId;
    const requestId = dispatchIntent(ACTION_ID, { npc_id: providerId });
    if (!requestId) return null;
    slots.value = {
      ...slots.value,
      [slot]: {
        providerId,
        requestId,
        epoch: store.view.epoch,
        generation: store.view.generation,
        // A refresh keeps the committed snapshot on screen; a re-target or a
        // first read starts from nothing.
        revision: sameProvider ? previous.revision : null,
        snapshot: sameProvider ? previous.snapshot : null,
        refusal: null,
      },
    };
    return requestId;
  }

  // Open (or re-target) one slot. Re-opening the provider of a slot that holds
  // a snapshot or a pending read is a no-op; a slate that only recorded a
  // refusal reads again, because selecting the provider is what retries it.
  function openServices(slot, providerId) {
    if (!isProviderId(providerId)) {
      clearSlot(slot);
      return null;
    }
    const current = slots.value[slot];
    if (
      current &&
      current.providerId === providerId &&
      (current.snapshot || current.requestId)
    ) {
      return null;
    }
    if (!dispatchRead(slot, providerId)) {
      // The store holds one action at a time: remember the opening instead of
      // losing it, and replay it when the store is free.
      wanted.value = { ...wanted.value, [slot]: providerId };
    }
    return null;
  }

  function closeServices(slot) {
    clearSlot(slot);
  }

  // Replay every remembered opening, then re-read every adopted slot whose
  // committed revision moved on, once no request is in flight. A read that
  // has not settled yet keeps its slot.
  function advance() {
    const queued = wanted.value;
    if (Object.keys(queued).length > 0) {
      wanted.value = {};
      for (const [slot, providerId] of Object.entries(queued)) {
        const current = slots.value[slot];
        if (current && current.providerId === providerId) continue;
        if (!dispatchRead(slot, providerId)) {
          wanted.value = { ...wanted.value, [slot]: providerId };
        }
      }
    }
    if (store.view.dispatch?.inFlight) return;
    for (const [slot, state] of Object.entries(slots.value)) {
      if (state.requestId || !state.snapshot) continue;
      if (state.revision === store.view.revision) continue;
      dispatchRead(slot, state.providerId);
    }
  }

  // The state of every open slot, for the drawer that owns it.
  const slotStates = computed(() => slots.value);

  // A transport or puppet change makes every pending and adopted read stale.
  watch([() => store.view.epoch, () => store.view.generation], () => {
    slots.value = {};
    wanted.value = {};
  });

  // Adopt only this read's own result. A rejection keeps the slot's provider
  // but drops any snapshot, so the drawer states the refusal instead of
  // falling back to the room summary.
  watch(
    () => store.view.lastActionResult,
    (result) => {
      if (!result || typeof result.requestId !== "string") return;
      const slot = Object.keys(slots.value).find(
        (key) => slots.value[key].requestId === result.requestId,
      );
      if (slot === undefined) {
        // Another action settled: a committed revision waits for its own read.
        advance();
        return;
      }
      const entry = slots.value[slot];
      const settled = { ...entry, requestId: null };
      const stale =
        (result.epoch !== undefined && result.epoch !== entry.epoch) ||
        store.view.epoch !== entry.epoch ||
        store.view.generation !== entry.generation;
      if (stale || result.outcome !== "success" || !admissible(result.data, entry.providerId)) {
        slots.value = {
          ...slots.value,
          [slot]: {
            ...settled,
            revision: null,
            snapshot: null,
            refusal: {
              code: typeof result.code === "string" ? result.code : "service_rejected",
              message: typeof result.message === "string" ? result.message : "",
            },
          },
        };
        return;
      }
      slots.value = {
        ...slots.value,
        [slot]: {
          ...settled,
          revision: store.view.revision,
          snapshot: result.data.services,
          refusal: null,
        },
      };
    },
  );

  // An opening that lost the single-action race reads its provider as soon as
  // the store settles, and a committed revision re-reads the open slots.
  watch(
    () => store.view.dispatch?.inFlight ?? null,
    () => advance(),
  );

  watch(
    () => store.view.revision,
    () => advance(),
  );

  return { openServices, closeServices, slots: slotStates };
}
