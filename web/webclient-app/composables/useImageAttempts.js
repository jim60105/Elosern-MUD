// useImageAttempts — the local resource driver for one image surface.
//
// It owns the *local* half of the shared load lifecycle: it binds the active
// subject/epoch/attempt, feeds actual DOM load/decode observations into the
// pure reducer in `lib/image-attempts.js`, keeps only the reachable local
// result, and disposes on replacement or unmount. It never parses a panel wire
// shape, never selects a business subject, and never schedules a retry or a
// global cache.
//
// The caller passes the normalized internal load request (see
// `lib/image-attempts.js`) and the shared availability input. Loading is
// element-driven: the caller binds the returned `attempt` to one `<img>`
// (`:key="attempt.token"`, `:src="attempt.url"` and
// `:data-attempt-token="attempt.token"`), so each attempt owns its own element
// exactly once and the driver reads the natural dimensions off that same
// element — no probe double-fetch, no source crossfade, and no late event from
// a retired element can settle a newer attempt.
//
// Restart identity is the ordered *resolution* facts plus subject/epoch and
// availability, so:
//   * a geometry-only revision keeps the facts and only refreshes the selected
//     resource's geometry — no request, no source-key change;
//   * a new resource version/key restarts and recomputes;
//   * an unchanged revision re-renders with no request and its reached failure
//     intact.
//
// `options.provisional` optionally supplies a caller-held provisional outcome
// map (resource key -> { epoch, phase, dimensions?, reason? }) for a source
// whose outcome is already known. A provisional success is a one-shot handoff
// consumed when the cursor reaches it; a provisional failure stays latent until
// that source is reached; a provisional `loading` parks resolution on a `wait`
// until the map changes.

import { computed, ref, toValue, watch } from "vue";
import {
  IMAGE_DECODE_FAILED,
  IMAGE_LOAD_FAILED,
  LOAD_PHASE,
  canonicalOrder,
  createLoadState,
  observeFailure,
  observeSuccess,
  resolutionFacts,
  resolve,
  withKnown,
  withProvisional,
} from "../lib/image-attempts.js";

function provisionalMap(value) {
  if (value instanceof Map) {
    return value;
  }
  return new Map(Object.entries(value ?? {}));
}

function provisionalSignature(store) {
  return JSON.stringify(
    [...provisionalMap(store).entries()].map(([key, outcome]) => [
      key,
      outcome?.epoch ?? null,
      outcome?.phase ?? null,
      outcome?.reason ?? null,
      outcome?.dimensions ?? null,
    ]),
  );
}

export function useImageAttempts(request, availability, options = {}) {
  const attempt = ref(null);
  const phase = ref(LOAD_PHASE.exhausted);
  const selected = ref(null);
  const reachedFaults = ref([]);
  const exhausted = ref(true);
  const panelUnavailable = ref(false);

  let machine = null;
  // One immutable token per concrete attempt. The caller keys its `<img>` on
  // `attempt.token`, so every attempt owns its own element and any late
  // load/error from a retired element is rejected by the attribute it carries.
  let attemptToken = 0;
  let disposed = false;
  let knownEpoch;
  const knownOutcomes = new Map();

  const requestValue = () => toValue(request) ?? null;
  const availabilityValue = () => {
    const value = toValue(availability);
    return value && typeof value === "object" ? value : { state: "ready" };
  };
  const provisionalValue = () => (options.provisional === undefined ? new Map() : provisionalMap(toValue(options.provisional)));

  const dimensions = computed(() => selected.value?.dimensions ?? null);
  const saveEligible = computed(
    () => phase.value === LOAD_PHASE.success && !!dimensions.value && !panelUnavailable.value,
  );

  const factsKey = computed(() => {
    const req = requestValue();
    const avail = availabilityValue();
    return JSON.stringify([
      avail.state ?? "ready",
      avail.view_subject_id ?? null,
      req?.subjectId ?? null,
      req?.epoch ?? null,
      resolutionFacts(req),
    ]);
  });
  const geometryKey = computed(() => {
    const req = requestValue();
    const rows = Array.isArray(req?.attempts) ? req.attempts : [];
    return JSON.stringify([
      ...rows.map((row) => row?.resource?.geometry ?? null),
      req?.terminal?.resource?.geometry ?? null,
    ]);
  });
  const provisionalKey = computed(() => provisionalSignature(provisionalValue()));

  function clearResult() {
    attempt.value = null;
    phase.value = LOAD_PHASE.exhausted;
    selected.value = null;
    reachedFaults.value = [];
    exhausted.value = true;
  }

  function resourceFor(key) {
    const entry = machine?.order.find((item) => item.kind === "image" && item.key === key);
    return entry?.resource ?? null;
  }

  function step(state) {
    machine = state;
    const next = resolve(state);
    machine = next.state;
    reachedFaults.value = next.state.reachedFaults;
    const { action } = next;
    if (action.type !== "done") {
      attemptToken += 1;
    }
    if (action.type === "load") {
      attempt.value = {
        key: action.key,
        sourceId: action.sourceId,
        rank: action.rank,
        resource: action.resource,
        url: action.resource.url,
        token: attemptToken,
      };
      phase.value = LOAD_PHASE.loading;
      selected.value = null;
      exhausted.value = false;
    } else if (action.type === "wait") {
      attempt.value = {
        key: action.key,
        sourceId: action.sourceId,
        rank: action.rank,
        resource: null,
        url: null,
        token: attemptToken,
      };
      phase.value = LOAD_PHASE.loading;
      selected.value = null;
      exhausted.value = false;
    } else if (action.type === "reuse") {
      selected.value = next.state.selected;
      attempt.value = {
        key: action.key,
        sourceId: action.sourceId,
        rank: action.rank,
        resource: resourceFor(action.key),
        url: next.state.selected?.url ?? null,
        token: attemptToken,
      };
      phase.value = LOAD_PHASE.success;
      exhausted.value = false;
    } else {
      // Exhaustion keeps the faults it accumulated: the local failure marker
      // persists after every permitted source is spent.
      attempt.value = null;
      selected.value = null;
      phase.value = LOAD_PHASE.exhausted;
      exhausted.value = true;
      reachedFaults.value = next.state.reachedFaults;
    }
  }

  function restart() {
    if (disposed) {
      return;
    }
    const req = requestValue();
    const avail = availabilityValue();
    const epoch = req?.epoch ?? null;
    if (knownEpoch !== epoch) {
      knownOutcomes.clear();
      knownEpoch = epoch;
    }
    clearResult();
    if (avail.state === "failed") {
      panelUnavailable.value = true;
      return;
    }
    panelUnavailable.value = false;
    if (!req || avail.state === "expected_absent") {
      return;
    }
    step(createLoadState(req, { known: knownOutcomes, provisional: provisionalValue() }));
  }

  function refreshGeometry() {
    if (disposed || !selected.value) {
      return;
    }
    const req = requestValue();
    const entry = canonicalOrder(req).find((item) => item.kind === "image" && item.key === selected.value.key);
    if (!entry) {
      return;
    }
    selected.value = { ...selected.value, geometry: entry.resource?.geometry ?? null };
  }

  function resume() {
    if (disposed || !machine || phase.value !== LOAD_PHASE.loading) {
      return;
    }
    // Always take the newest provisional snapshot: an outcome that changed
    // while a real request was in flight must be visible to the resolution
    // that follows that request's failure. Only a parked `wait` advances now;
    // an in-flight real load is never re-issued by a provisional update.
    machine = withProvisional(machine, provisionalValue());
    if (!attempt.value || attempt.value.resource !== null) {
      return;
    }
    step(machine);
  }

  function settle(current, outcome) {
    if (disposed || !machine || current.token !== attemptToken) {
      return;
    }
    const advanced = outcome.phase === LOAD_PHASE.success
      ? observeSuccess(machine, { epoch: machine.epoch, key: current.key, dimensions: outcome.dimensions })
      : observeFailure(machine, { epoch: machine.epoch, key: current.key, reason: outcome.reason });
    if (advanced === machine) {
      return;
    }
    machine = withKnown(advanced, current.key, outcome);
    knownOutcomes.set(current.key, { epoch: machine.epoch, ...outcome });
    if (outcome.phase === LOAD_PHASE.success) {
      selected.value = machine.selected;
      reachedFaults.value = machine.reachedFaults;
      phase.value = LOAD_PHASE.success;
      exhausted.value = false;
      attempt.value = { ...current };
    } else {
      reachedFaults.value = machine.reachedFaults;
      step(machine);
    }
  }

  function onImageLoad(event) {
    const target = event?.target;
    const current = attempt.value;
    if (!current?.url || !target || typeof target.getAttribute !== "function") {
      return;
    }
    if (target.getAttribute("data-attempt-token") !== String(current.token)) {
      return;
    }
    const width = Number(target.naturalWidth) || 0;
    const height = Number(target.naturalHeight) || 0;
    if (width > 0 && height > 0) {
      settle(current, { phase: LOAD_PHASE.success, dimensions: { width, height } });
    } else {
      settle(current, { phase: "failed", reason: IMAGE_DECODE_FAILED });
    }
  }

  function onImageError(event) {
    const target = event?.target;
    const current = attempt.value;
    if (!current?.url) {
      return;
    }
    if (!target || typeof target.getAttribute !== "function") {
      return;
    }
    if (target.getAttribute("data-attempt-token") !== String(current.token)) {
      return;
    }
    settle(current, { phase: "failed", reason: IMAGE_LOAD_FAILED });
  }

  function dispose() {
    disposed = true;
    knownOutcomes.clear();
    machine = null;
    clearResult();
    panelUnavailable.value = false;
  }

  watch(factsKey, restart, { immediate: true });
  watch(geometryKey, refreshGeometry);
  watch(provisionalKey, resume);

  return {
    attempt,
    phase,
    selected,
    reachedFaults,
    exhausted,
    dimensions,
    panelUnavailable,
    saveEligible,
    onImageLoad,
    onImageError,
    dispose,
  };
}
