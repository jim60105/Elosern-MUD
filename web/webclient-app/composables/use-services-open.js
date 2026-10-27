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
// A slot records its selected provider the moment the drawer asks for it —
// before the dispatch, while the read is in flight, and after a refusal. The
// drawer therefore never renders the room summary for a targeted slot: until
// a snapshot is adopted it states an unavailable surface, so a flow opened for
// one NPC can never be completed against another.
//
// The store runs one action at a time. An opening it refuses (because another
// action is in flight) is remembered as scheduling information and replayed
// once the store settles; an explicit opening always supersedes the previous
// selection and any queued intent, so a late replay can never override the
// latest choice.
//
// Refresh ownership: while a slot holds a snapshot, a committed presentation
// revision (a purchase, a registration, a quest write) repeats the read for
// the same provider once nothing is in flight; a snapshot older than the
// committed revision is re-read too, because the result's own presentation
// revision — not the arrival time — says what it shows. `services.open`
// publishes no panel of its own, so a read cannot trigger another read. The
// selection is never persisted on the actor or the NPC.
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

  function forgetWanted(slot) {
    if (!(slot in wanted.value)) return;
    const next = { ...wanted.value };
    delete next[slot];
    wanted.value = next;
  }

  // Record the slot's selection and try to dispatch it. The selection is
  // recorded whether or not the dispatch succeeds, so the drawer is targeted
  // from this moment on. A same-provider read keeps its snapshot and refusal
  // on screen; a different provider starts from nothing and stops owning the
  // previous read.
  function dispatchRead(slot, providerId) {
    const previous = slots.value[slot];
    const sameProvider = previous !== undefined && previous.providerId === providerId;
    const requestId = dispatchIntent(ACTION_ID, { npc_id: providerId });
    slots.value = {
      ...slots.value,
      [slot]: {
        providerId,
        requestId,
        epoch: store.view.epoch,
        generation: store.view.generation,
        revision: sameProvider ? previous.revision : null,
        snapshot: sameProvider ? previous.snapshot : null,
        refusal: requestId === null && sameProvider ? previous.refusal : null,
      },
    };
    return requestId;
  }

  // Open (or re-target) one slot. Re-opening the provider of a slot that holds
  // a snapshot or a pending read is a no-op for that provider; a slot that only
  // recorded a refusal reads again, because selecting the provider is what
  // retries it. Either way the call supersedes any queued intent.
  function openServices(slot, providerId) {
    if (!isProviderId(providerId)) {
      clearSlot(slot);
      return null;
    }
    forgetWanted(slot);
    const current = slots.value[slot];
    if (
      current &&
      current.providerId === providerId &&
      (current.snapshot || current.requestId)
    ) {
      return null;
    }
    if (!dispatchRead(slot, providerId)) {
      wanted.value = { ...wanted.value, [slot]: providerId };
    }
    return null;
  }

  function closeServices(slot) {
    clearSlot(slot);
  }

  // Replay every remembered opening, then re-read every adopted slot whose
  // snapshot trails the committed revision, once no request is in flight. A
  // read that has not settled yet keeps its slot.
  function advance() {
    const queued = wanted.value;
    if (Object.keys(queued).length > 0) {
      wanted.value = {};
      for (const [slot, providerId] of Object.entries(queued)) {
        const current = slots.value[slot];
        if (
          current &&
          current.providerId === providerId &&
          (current.snapshot || current.requestId)
        ) {
          continue;
        }
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
      // The result's own presentation revision says what the rows show; a
      // result that already trails the committed state is re-read below
      // instead of being recorded as current.
      const revision =
        typeof result.presentationRevision === "number"
          ? result.presentationRevision
          : store.view.revision;
      slots.value = {
        ...slots.value,
        [slot]: {
          ...settled,
          revision,
          snapshot: result.data.services,
          refusal: null,
        },
      };
      if (revision < store.view.revision) advance();
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
