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
//
// `options.provisionalSource` optionally names ONE resource — a scene's own
// bundled/terminal background — this driver fetches OUTSIDE the ordered walk,
// so a higher-priority source that is still loading never leaves the surface
// blank. It is the same element-driven mechanism, never a second loader: the
// resource's `loading` ownership is registered before its element is exposed,
// so the ordered walk parks on that source instead of issuing a duplicate
// request, and its settled outcome is handed over at the source's own
// precedence position with no duplicate attempt. The element is exposed as
// `provisionalAttempt` (bind `token`/`url` exactly like `attempt`) and its
// successful resource as `provisionalSelected`.

import { computed, ref, toValue, watch } from "vue";
import {
  IMAGE_DECODE_FAILED,
  IMAGE_LOAD_FAILED,
  LOAD_PHASE,
  canonicalOrder,
  createLoadState,
  observeFailure,
  observeSuccess,
  resourceKey,
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
  // The out-of-band provisional element this driver owns (the surface's own
  // bundled/terminal background) and the resource it successfully decoded.
  const provisionalAttempt = ref(null);
  const provisionalSelected = ref(null);
  // The driver's OWN provisional outcomes, merged with the caller's map. They
  // are epoch-scoped and keyed by resource identity/version exactly like the
  // shared reducer's own store, so the ordered walk reuses the outcome at the
  // source's precedence position.
  const provisionalOutcomes = ref(new Map());

  let machine = null;
  // One immutable token per concrete attempt. The caller keys its `<img>` on
  // `attempt.token`, so every attempt owns its own element and any late
  // load/error from a retired element is rejected by the attribute it carries.
  let attemptToken = 0;
  let provisionalToken = 0;
  let disposed = false;
  let knownEpoch;
  const knownOutcomes = new Map();

  const requestValue = () => toValue(request) ?? null;
  const availabilityValue = () => {
    const value = toValue(availability);
    return value && typeof value === "object" ? value : { state: "ready" };
  };
  const provisionalSourceValue = () =>
    options.provisionalSource === undefined ? null : toValue(options.provisionalSource) ?? null;
  const provisionalValue = () => {
    const merged = provisionalMap(
      options.provisional === undefined ? undefined : toValue(options.provisional),
    );
    for (const [key, outcome] of provisionalOutcomes.value.entries()) {
      merged.set(key, outcome);
    }
    return merged;
  };

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
  const provisionalSourceKey = computed(() => {
    const source = provisionalSourceValue();
    return JSON.stringify([resourceKey(source), source?.url ?? null]);
  });

  function clearProvisional() {
    provisionalAttempt.value = null;
    provisionalSelected.value = null;
    provisionalOutcomes.value = new Map();
  }

  // Start or retire the out-of-band provisional element.
  //
  // It is started ONLY for a resource the ordered walk does not currently own:
  // once the walk's own in-flight attempt IS that resource, or its outcome is
  // already durable, or it is already provisional-loaded, there is nothing
  // left to fetch outside the walk — which is what keeps the resource
  // requested exactly once. The `loading` ownership is recorded before the
  // element exists, so a walk that reaches the resource meanwhile parks on it
  // instead of issuing a second request.
  function syncProvisional() {
    if (disposed) {
      return;
    }
    const req = requestValue();
    const source = provisionalSourceValue();
    const key = resourceKey(source);
    if (!req || !source || !key || availabilityValue().state !== "ready") {
      provisionalAttempt.value = null;
      return;
    }
    if (phase.value !== LOAD_PHASE.loading) {
      // Resolution already settled (or exhausted): an out-of-band background
      // has nothing left to stand in for, so its element is retired rather
      // than left fetching a resource that will not be displayed.
      provisionalAttempt.value = null;
      return;
    }
    const settledProvisional = provisionalOutcomes.value.get(key);
    if (settledProvisional && settledProvisional.phase !== LOAD_PHASE.loading) {
      provisionalAttempt.value = null;
      return;
    }
    if (knownOutcomes.has(key) || attempt.value?.key === key) {
      // The ordered walk already owns (or already observed) this exact
      // resource: a second fetching element would be a duplicate attempt.
      provisionalAttempt.value = null;
      return;
    }
    if (provisionalAttempt.value?.key === key) {
      return;
    }
    provisionalToken += 1;
    const entry = machine?.order.find((item) => item.kind === "image" && item.key === key);
    provisionalOutcomes.value = new Map(provisionalOutcomes.value).set(key, {
      epoch: machine?.epoch ?? req?.epoch ?? null,
      phase: LOAD_PHASE.loading,
    });
    provisionalAttempt.value = {
      key,
      sourceId: entry?.sourceId ?? null,
      rank: entry?.rank ?? null,
      resource: source,
      url: source.url,
      token: provisionalToken,
    };
  }

  function settleProvisional(outcome) {
    const current = provisionalAttempt.value;
    if (disposed || !current) {
      return;
    }
    provisionalOutcomes.value = new Map(provisionalOutcomes.value).set(current.key, {
      epoch: machine?.epoch ?? null,
      ...outcome,
    });
    if (outcome.phase === LOAD_PHASE.success) {
      provisionalSelected.value = {
        key: current.key,
        sourceId: current.sourceId,
        rank: current.rank,
        resourceId: current.resource?.resource_id ?? null,
        version: current.resource?.version ?? null,
        url: current.url,
        geometry: current.resource?.geometry ?? null,
        dimensions: outcome.dimensions ?? null,
      };
    }
    provisionalAttempt.value = null;
  }

  function onProvisionalLoad(event) {
    const target = event?.target;
    const current = provisionalAttempt.value;
    if (!current?.url || !target || typeof target.getAttribute !== "function") {
      return;
    }
    if (target.getAttribute("data-provisional-token") !== String(current.token)) {
      return;
    }
    const width = Number(target.naturalWidth) || 0;
    const height = Number(target.naturalHeight) || 0;
    if (width > 0 && height > 0) {
      settleProvisional({ phase: LOAD_PHASE.success, dimensions: { width, height } });
    } else {
      settleProvisional({ phase: "failed", reason: IMAGE_DECODE_FAILED });
    }
  }

  function onProvisionalError(event) {
    const target = event?.target;
    const current = provisionalAttempt.value;
    if (!current?.url || !target || typeof target.getAttribute !== "function") {
      return;
    }
    if (target.getAttribute("data-provisional-token") !== String(current.token)) {
      return;
    }
    settleProvisional({ phase: "failed", reason: IMAGE_LOAD_FAILED });
  }

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
    clearProvisional();
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
    // The out-of-band provisional element is started AFTER the walk's own
    // first step, so it can never claim a resource the walk is already
    // fetching.
    syncProvisional();
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
    clearProvisional();
    clearResult();
    panelUnavailable.value = false;
  }

  // The resolution facts are the commit boundary of this surface, so the
  // restart runs SYNCHRONOUSLY with them: any other watcher of the same commit
  // (a consumer keeping its own display content) then reads a cleared
  // selection rather than a stale one, and no surface can pair this commit's
  // facts with the previous commit's result.
  watch(factsKey, restart, { immediate: true, flush: "sync" });
  watch(geometryKey, refreshGeometry);
  watch(provisionalKey, resume);
  // A settled resolution retires the out-of-band element too: the provisional
  // background exists to stand in WHILE a higher-priority source loads.
  watch([provisionalSourceKey, () => phase.value], syncProvisional);

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
    provisionalAttempt,
    provisionalSelected,
    onProvisionalLoad,
    onProvisionalError,
    dispose,
  };
}
