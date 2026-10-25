// Memory-only dialogue reading client (authored-dialogue-reading-client;
// Shared contract v2 "Reading and completion" + "Availability and
// notifications").
//
// One formal scene finish becomes one acknowledgement of the exact delivered
// receipt through `explore.dialogue_complete`. The acknowledgement and its
// retry live ONLY in this module's memory: there is no localStorage,
// IndexedDB, service-worker retry or durable queue, and a fresh app mount
// therefore has no pending state (the server's saved reading wins and the
// latest valid delivery replays from line one).
//
// The module owns five things (see design.md):
// - `finishDialogueDelivery(delivery)`: admit exactly one bounded entry for a
//   formal delivery, deduplicated by `context_id + delivery_id`. Refusals,
//   openings, service lines and freeform text never queue.
// - The acknowledgement queue: entries are acknowledged in insertion order
//   and a pure-chain successor waits until every predecessor is saved
//   (predecessor-first serialization). One acknowledgement is on the wire at
//   a time; the store's single-mutation dispatch entry refuses to overlap it,
//   so the server's one-action-per-session admission is never challenged.
// - `retryDialogueReading()`: the explicit retry for an unsaved entry
//   (transport error, retryable rejection). A same-context transport
//   restoration retries by itself.
// - The transient pure-chain reveal: after a root finish whose acknowledgement
//   is still pending, an already pre-delivered public successor (the panel's
//   `pure_chain`) may play immediately. Only that delivered successor is
//   revealed; the server's `choices` stay the sole source of qualified topic
//   rows and nothing is unlocked locally.
// - Discarding: leaving dialogue, a changed context/control/phase, a changed
//   acting character or a logical rejection drops the pending memory and the
//   reveal; a transport generation change only suspends the queue for a
//   same-context retry.
import { ref } from "vue";

// Matches the server's per-topic completion receipt bound (Shared contract v2:
// at most 32 retained formal receipts).
export const MAX_PENDING_COMPLETIONS = 32;
// Bound on locally finished topics remembered for chain gating; the server
// retains at most 16 topics per host and 32 receipts, so this is generous.
const MAX_FINISHED_TOPICS = 64;
// How long one acknowledgement may stay on the wire before it is presented as
// an unsaved entry with an explicit retry. A live transport answers in one
// round trip; this only bounds a silently lost send.
export const DIALOGUE_ACK_TIMEOUT_MS = 5000;

// Stable rejection codes that make the acknowledgement itself meaningless
// (Shared contract v2): the receipt is gone, foreign, retired or was never a
// formal delivery. The entry is discarded and the canonical presentation is
// re-requested — never retried against a receipt the server already refused.
const DISCARD_CODES = new Set([
  "dialogue_context_closed",
  "stale_context",
  "dialogue_receipt_unknown",
  "dialogue_receipt_foreign",
  "dialogue_receipt_stale",
  "dialogue_receipt_kind",
  "no_npc",
  "no_puppet",
  "malformed_payload",
]);
// Operational rejections: nothing was committed, so the exact same payload
// may be attempted again later (explicit retry or a same-context restore).
const RETRYABLE_CODES = new Set([
  "busy",
  "stale",
  "dialogue_completion_failed",
  "internal_error",
]);
// A public successor whose predecessor is not saved yet stays queued.
const WAITING_CODE = "dialogue_predecessor_unread";

function deliveryKey(contextId, deliveryId) {
  // Ids are opaque; JSON keeps the pair unambiguous without parsing either.
  return JSON.stringify([contextId, deliveryId]);
}

/**
 * Install the memory-only reading client over the composed store context.
 *
 * @param {object} ctx — the shared store context (see stores/elosern.js).
 */
export function applyDialogueReading(ctx) {
  // The published snapshot (`view.dialogueReading`); every write replaces the
  // whole object, so no subscriber observes a half-applied state.
  const published = ref(emptySnapshot());
  ctx.dialogueReading = published;

  const memory = {
    ownerId: null,
    contextId: null,
    npcId: null,
    phaseRevision: undefined,
    serverDeliveryId: null,
    readingRevision: 0,
    canonicalCompleted: [],
    // Admission order == acknowledgement order.
    pending: [],
    // Exact request id -> entry key for the attempt currently on the wire.
    requests: new Map(),
    sending: null,
    // Topics finished locally this context (chain gating; insertion bounded).
    finished: new Set(),
    // Topics the server answered saved/already_saved for this context.
    saved: new Set(),
    // The one transient reveal: {entryKey, delivery, predecessors}.
    reveal: null,
    // The newest presentation revision an acknowledged attempt settled at;
    // the next acknowledgement waits until the committed view reaches it.
    settleRevision: 0,
    // Monotonic local save counter: a `dialogue_predecessor_unread` answer is
    // only re-evaluated after a NEW save/canonical completion, so a defensive
    // refusal never loops on the same knowledge.
    saveEpoch: 0,
    attempts: 0,
    timer: null,
  };

  function emptySnapshot() {
    return {
      contextId: null,
      npcId: null,
      readingRevision: 0,
      completedTopicIds: [],
      savedTopicIds: [],
      pendingCount: 0,
      pending: [],
      sending: false,
      retryable: false,
      revealed: null,
    };
  }

  function snapshot() {
    return {
      contextId: memory.contextId,
      npcId: memory.npcId,
      readingRevision: memory.readingRevision,
      completedTopicIds: memory.canonicalCompleted.slice(),
      savedTopicIds: [...memory.saved],
      pending: memory.pending.map((entry) => ({
        deliveryId: entry.deliveryId,
        topicId: entry.topicId,
        contextId: entry.contextId,
        status: entry.status,
      })),
      pendingCount: memory.pending.length,
      sending: memory.sending !== null,
      retryable: memory.pending.some((entry) => entry.status === "failed"),
      revealed: memory.reveal
        ? {
            deliveryId: memory.reveal.delivery.delivery_id,
            topicId: memory.reveal.delivery.topic_id,
            predecessors: memory.reveal.predecessors.slice(),
            delivery: memory.reveal.delivery,
          }
        : null,
    };
  }

  function publishSnapshot() {
    published.value = snapshot();
  }

  function clearTimer() {
    if (memory.timer !== null) {
      clearTimeout(memory.timer);
      memory.timer = null;
    }
  }

  function entryByKey(key) {
    return memory.pending.find((entry) => entry.key === key) || null;
  }

  function savedTopics() {
    // Server-canonical completions and locally acknowledged saves both satisfy
    // a predecessor gate; nothing else does.
    return new Set([...memory.canonicalCompleted, ...memory.saved]);
  }

  function clearReveal(exceptDeliveryId = null) {
    if (memory.reveal && memory.reveal.delivery.delivery_id !== exceptDeliveryId) {
      memory.reveal = null;
    }
  }

  function releaseWire(entry) {
    if (entry && entry.requestId) {
      // Only retire the mapping this attempt owns (a newer attempt may have
      // replaced it after a restoration).
      if (memory.requests.get(entry.requestId) === entry.key) {
        memory.requests.delete(entry.requestId);
      }
      entry.requestId = null;
    }
    if (memory.sending === entry) {
      memory.sending = null;
      clearTimer();
    }
  }

  function discardEntry(entry) {
    releaseWire(entry);
    const index = memory.pending.indexOf(entry);
    if (index !== -1) {
      memory.pending.splice(index, 1);
    }
    if (memory.reveal && memory.reveal.entryKey === entry.key) {
      memory.reveal = null;
    }
  }

  function discardAll() {
    for (const entry of memory.pending) {
      if (entry.requestId) {
        memory.requests.delete(entry.requestId);
      }
    }
    memory.pending = [];
    memory.requests.clear();
    memory.sending = null;
    clearTimer();
    memory.finished.clear();
    memory.saved.clear();
    memory.canonicalCompleted = [];
    memory.reveal = null;
    memory.serverDeliveryId = null;
    memory.readingRevision = 0;
    memory.contextId = null;
    memory.npcId = null;
    memory.phaseRevision = undefined;
    memory.settleRevision = 0;
    memory.saveEpoch = 0;
  }

  function evictOne() {
    if (memory.pending.length === 0) {
      return;
    }
    // Never evict the attempt on the wire; prefer an entry no queued successor
    // still needs as a predecessor.
    const needed = new Set(
      memory.pending.flatMap((entry) => entry.predecessors || []),
    );
    // Prefer a never-sent entry, then any non-sending one: an entry that
    // already failed still holds the player's unsaved progress and its
    // explicit retry.
    let index = memory.pending.findIndex(
      (entry) => entry.status === "queued" && !needed.has(entry.topicId),
    );
    if (index === -1) {
      index = memory.pending.findIndex(
        (entry) => entry.status !== "sending" && !needed.has(entry.topicId),
      );
    }
    if (index === -1) {
      index = memory.pending.findIndex((entry) => entry.status !== "sending");
    }
    if (index === -1) {
      index = 0;
    }
    const [dropped] = memory.pending.splice(index, 1);
    if (dropped) {
      releaseWire(dropped);
      if (memory.reveal && memory.reveal.entryKey === dropped.key) {
        memory.reveal = null;
      }
    }
  }

  function rememberFinished(topicId) {
    if (typeof topicId !== "string" || topicId === "") {
      return;
    }
    memory.finished.add(topicId);
    while (memory.finished.size > MAX_FINISHED_TOPICS) {
      const oldest = memory.finished.values().next().value;
      memory.finished.delete(oldest);
    }
  }

  function refreshCanonicalState() {
    const sender = ctx.sender;
    if (sender && typeof sender.sendSync === "function") {
      sender.sendSync();
    }
  }

  function buildPayload(entry) {
    // Exactly the five server-issued fields (Shared contract v2), each
    // verbatim: generated topic ids are opaque and never truncated.
    return {
      npc_id: entry.npcId,
      delivery_id: entry.deliveryId,
      context_id: entry.contextId,
      topic_id: entry.topicId,
      scene_revision: entry.sceneRevision,
    };
  }

  function sendEntry(entry, rs) {
    const sender = ctx.sender;
    if (!sender || typeof sender.sendAction !== "function") {
      return false;
    }
    const requestId = `reading:${++memory.attempts}`;
    const envelope = {
      protocol_version: 1,
      presentation_epoch: rs.activeEpoch,
      request_id: requestId,
      base_revision: rs.revision,
      action_id: "explore.dialogue_complete",
      payload: buildPayload(entry),
    };
    // The attempt is recorded BEFORE the send: a synchronous sender failure
    // (or a fake that answers inline) must never leave an unowned attempt.
    entry.status = "sending";
    entry.requestId = requestId;
    memory.requests.set(requestId, entry.key);
    memory.sending = entry;
    clearTimer();
    memory.timer = setTimeout(() => {
      // A lost acknowledgement is an unsaved entry, never a durable claim.
      if (memory.sending === entry && entry.requestId === requestId) {
        releaseWire(entry);
        entry.status = "failed";
        publishSnapshot();
        ctx.publishView();
      }
    }, DIALOGUE_ACK_TIMEOUT_MS);
    try {
      sender.sendAction(envelope);
      return true;
    } catch (error) {
      releaseWire(entry);
      entry.status = "failed";
      return false;
    }
  }

  function eligibleEntry(rs) {
    const saved = savedTopics();
    for (const entry of memory.pending) {
      if (entry.status === "sending" || entry.status === "failed" || entry.status === "waiting") {
        continue;
      }
      const predecessors = entry.predecessors || [];
      if (predecessors.length > 0 && !predecessors.every((id) => saved.has(id))) {
        // A queued successor waits for saved predecessors (predecessor-first).
        entry.status = "waiting";
        continue;
      }
      if (rs.revision < memory.settleRevision) {
        // The previous acknowledgement's presentation has not committed yet;
        // sending now would name an outdated base revision.
        return null;
      }
      return entry;
    }
    return null;
  }

  function flush() {
    if (memory.sending !== null || memory.pending.length === 0) {
      return;
    }
    const rs = ctx.reducer.getState();
    if (
      !rs.connected ||
      rs.phase !== "active" ||
      rs.mode == null ||
      rs.mutationsLocked ||
      rs.protocolError?.reloadRequired === true
    ) {
      return;
    }
    // Never challenge the store's single in-flight mutation (the server admits
    // one action per session and answers the loser `busy`).
    if (ctx.inFlight) {
      return;
    }
    const entry = eligibleEntry(rs);
    if (!entry) {
      return;
    }
    sendEntry(entry, rs);
  }

  function markPredecessorsResolved() {
    const saved = savedTopics();
    for (const entry of memory.pending) {
      if (
        entry.status === "waiting" &&
        (entry.waitingEpoch ?? 0) < memory.saveEpoch &&
        (entry.predecessors || []).every((id) => saved.has(id))
      ) {
        entry.status = "queued";
      }
    }
  }

  function save(entry) {
    releaseWire(entry);
    const index = memory.pending.indexOf(entry);
    if (index !== -1) {
      memory.pending.splice(index, 1);
    }
    memory.saved.add(entry.topicId);
    memory.saveEpoch += 1;
    rememberFinished(entry.topicId);
    markPredecessorsResolved();
  }

  function revealSuccessor(panel, delivery) {
    const finishedTopic = delivery.topic_id;
    if (!panel || !Array.isArray(panel.pure_chain)) {
      return;
    }
    const saved = savedTopics();
    if (saved.has(finishedTopic)) {
      // The canonical save already drives the server's rows; no optimistic
      // reveal is allowed to compete with them.
      return;
    }
    const chain = panel.pure_chain;
    // A reveal that is NOT the delivery just finished is still the presented
    // scene (or a later node): never replace it from this finish.
    if (memory.reveal !== null && memory.reveal.delivery.delivery_id !== delivery.delivery_id) {
      return;
    }
    // The finished node's bit is kept below unless a further node is eligible:
    // the panel still replays the session root, so dropping the reveal would
    // restart the root scene the player already read.
    const finishedReveal = memory.reveal;
    for (const node of chain) {
      const nodeDelivery = node && node.delivery;
      const predecessors = node && Array.isArray(node.predecessors) ? node.predecessors : [];
      if (!nodeDelivery || nodeDelivery.kind !== "formal" || !nodeDelivery.topic_id) {
        continue;
      }
      if (nodeDelivery.context_id !== panel.context_id) {
        continue;
      }
      if (predecessors.length === 0) {
        continue;
      }
      // Only nodes the player has actually read in order, and only while at
      // least one predecessor is still unsaved: the reveal is the optimistic
      // bridge until the server's saved reading publishes the real row.
      if (!predecessors.every((id) => memory.finished.has(id))) {
        continue;
      }
      if (predecessors.every((id) => saved.has(id))) {
        continue;
      }
      if (memory.finished.has(nodeDelivery.topic_id)) {
        continue;
      }
      memory.reveal = {
        entryKey: deliveryKey(nodeDelivery.context_id, nodeDelivery.delivery_id),
        delivery: nodeDelivery,
        predecessors: predecessors.slice(),
      };
      return;
    }
    memory.reveal = finishedReveal;
  }

  function admit(delivery) {
    const contextId = delivery.context_id;
    const deliveryId = delivery.delivery_id;
    const key = deliveryKey(contextId, deliveryId);
    const existing = entryByKey(key);
    if (existing) {
      // Deduplicate repeated finish events: one exact acknowledgement.
      return existing;
    }
    while (memory.pending.length >= MAX_PENDING_COMPLETIONS) {
      evictOne();
    }
    const entry = {
      key,
      contextId,
      deliveryId,
      topicId: delivery.topic_id,
      sceneRevision: delivery.scene_revision,
      npcId: delivery.npc_id,
      predecessors:
        memory.reveal && memory.reveal.entryKey === key
          ? memory.reveal.predecessors.slice()
          : [],
      status: "queued",
      requestId: null,
    };
    memory.pending.push(entry);
    return entry;
  }

  function resolveNpcId(delivery) {
    if (Number.isInteger(delivery.npc_id) && delivery.npc_id > 0) {
      return delivery.npc_id;
    }
    const rs = ctx.reducer.getState();
    const panel = rs.panels && rs.panels.dialogue;
    if (panel && panel.available === true && panel.context_id === delivery.context_id) {
      const identity = panel.host && panel.host.identity;
      if (Number.isInteger(identity) && identity > 0) {
        return identity;
      }
    }
    return null;
  }

  /**
   * Queue the exact completion acknowledgement for one finished delivery.
   *
   * Only a formal delivery delivered inside the committed conversation queues;
   * a refusal, the opening greeting, a service line or freeform text never
   * does. Returns the queued entry key, or null when nothing was admitted.
   */
  ctx.finishDialogueDelivery = function finishDialogueDelivery(delivery) {
    if (!delivery || delivery.kind !== "formal") {
      return null;
    }
    if (
      typeof delivery.delivery_id !== "string" ||
      delivery.delivery_id === "" ||
      typeof delivery.context_id !== "string" ||
      delivery.context_id === "" ||
      typeof delivery.topic_id !== "string" ||
      delivery.topic_id === "" ||
      typeof delivery.scene_revision !== "string" ||
      delivery.scene_revision === ""
    ) {
      return null;
    }
    const rs = ctx.reducer.getState();
    if (rs.mode !== "dialogue") {
      return null;
    }
    const panel = rs.panels && rs.panels.dialogue;
    if (!panel || panel.available !== true || panel.context_id !== delivery.context_id) {
      return null;
    }
    const npcId = resolveNpcId(delivery);
    if (npcId === null) {
      return null;
    }
    rememberFinished(delivery.topic_id);
    const entry = admit({
      npc_id: npcId,
      delivery_id: delivery.delivery_id,
      context_id: delivery.context_id,
      topic_id: delivery.topic_id,
      scene_revision: delivery.scene_revision,
    });
    revealSuccessor(panel, delivery);
    flush();
    publishSnapshot();
    ctx.publishView();
    return entry.key;
  };

  /** Explicit retry for every unsaved entry (the visible 重試 affordance). */
  ctx.retryDialogueReading = function retryDialogueReading() {
    let changed = false;
    for (const entry of memory.pending) {
      if (entry.status === "failed" || entry.status === "waiting") {
        entry.status = "queued";
        changed = true;
      }
    }
    if (changed) {
      flush();
      publishSnapshot();
      ctx.publishView();
    }
    return changed;
  };


  /**
   * Reconcile the memory with one committed state (the publish entry point).
   *
   * Suspended states (a transport reset's pre-snapshot null mode, the
   * awaiting-initial-snapshot phase, a reconnect's null epoch) keep the queue
   * for a same-context retry. An authoritative state that leaves dialogue,
   * changes host/context/phase/acting character or retires the panel discards
   * it.
   */
  ctx.syncDialogueReading = function syncDialogueReading(prev, rs) {
    if (!rs) {
      return;
    }
    if (prev && prev.generation !== rs.generation) {
      // A new transport generation: the old attempt can never answer (the
      // reducer discards old-generation messages). Keep the exact payloads
      // and retry on the same-context restoration.
      for (const entry of memory.pending) {
        if (entry.status === "sending") {
          entry.status = "queued";
        }
      }
      memory.requests.clear();
      memory.sending = null;
      clearTimer();
      memory.settleRevision = 0;
    }
    if (rs.phase !== "active" || rs.mode == null) {
      // Suspended (reset/bootstrap): never discard on the reset itself.
      publishSnapshot();
      return;
    }
    const statusPanel = rs.panels && rs.panels.status;
    const owner = statusPanel && statusPanel.actor && statusPanel.actor.identity;
    if (owner !== undefined && owner !== null) {
      const ownerId = String(owner);
      if (memory.ownerId !== null && memory.ownerId !== ownerId) {
        // A different acting character: nothing queued may outlive it.
        discardAll();
      }
      memory.ownerId = ownerId;
    }
    if (rs.mode !== "dialogue") {
      if (memory.pending.length > 0 || memory.saved.size > 0 || memory.reveal) {
        discardAll();
      }
      publishSnapshot();
      return;
    }
    const panel = rs.panels && rs.panels.dialogue;
    if (!panel || panel.available !== true) {
      if (memory.pending.length > 0 || memory.saved.size > 0 || memory.reveal) {
        discardAll();
      }
      publishSnapshot();
      return;
    }
    const contextId = panel.context_id;
    const npcId = (panel.host && panel.host.identity) ?? null;
    const phase = (panel.delivery && panel.delivery.phase_revision) ?? null;
    if (
      memory.contextId !== null &&
      (memory.contextId !== contextId ||
        memory.npcId !== npcId ||
        (memory.phaseRevision !== undefined && memory.phaseRevision !== phase))
    ) {
      // Changed context, control/host or phase: retired receipts.
      discardAll();
    }
    memory.contextId = contextId;
    memory.npcId = npcId;
    memory.phaseRevision = phase;
    memory.readingRevision = Number.isInteger(panel.reading_revision)
      ? panel.reading_revision
      : 0;
    const completed = Array.isArray(panel.completed_topic_ids)
      ? panel.completed_topic_ids.slice(0, 16)
      : [];
    if (
      completed.length !== memory.canonicalCompleted.length ||
      completed.some((id, index) => id !== memory.canonicalCompleted[index])
    ) {
      // A newer canonical save (another connection or a pushed refresh)
      // releases queued successors that were waiting on it.
      memory.canonicalCompleted = completed;
      memory.saveEpoch += 1;
    }
    const serverDeliveryId = (panel.delivery && panel.delivery.delivery_id) ?? null;
    if (memory.serverDeliveryId !== serverDeliveryId) {
      if (memory.serverDeliveryId !== null) {
        // The server committed a different playback: the optimistic reveal is
        // retired and the canonical delivery plays (a reading-revision-only
        // update keeps the same id and therefore neither restarts nor
        // advances the current delivery).
        clearReveal();
      }
      memory.serverDeliveryId = serverDeliveryId;
    }
    markPredecessorsResolved();
    flush();
    publishSnapshot();
  };

  /**
   * Settle one acknowledgement result (called from the transport receive seam
   * after the reducer accepted it). Matching is by the exact request id this
   * module allocated; nothing else can clear an entry.
   */
  ctx.onDialogueReadingResult = function onDialogueReadingResult(result) {
    // The reducer's committed `lastActionResult` normalizes the wire snake_case
    // to camelCase; accept the committed form (and the raw form) without
    // duplicating the protocol mapping.
    const requestId = result && (result.requestId ?? result.request_id);
    if (typeof requestId !== "string") {
      return false;
    }
    const key = memory.requests.get(requestId);
    if (key === undefined) {
      // A foreign, superseded or already-settled attempt.
      return false;
    }
    memory.requests.delete(requestId);
    const entry = entryByKey(key);
    if (memory.sending !== null && memory.sending.key === key) {
      memory.sending = null;
      clearTimer();
    }
    if (!entry) {
      publishSnapshot();
      return true;
    }
    entry.requestId = null;
    const wireRevision = result.presentationRevision ?? result.presentation_revision;
    const revision = Number.isInteger(wireRevision)
      ? wireRevision
      : ctx.reducer.getState().revision;
    if (typeof revision === "number" && revision > memory.settleRevision) {
      memory.settleRevision = revision;
    }
    if (result.outcome === "success" && result.code === "dialogue_completed") {
      save(entry);
    } else if (result.outcome === "rejected" && result.code === WAITING_CODE) {
      // The predecessor is not saved yet: keep the entry queued behind it.
      entry.status = "waiting";
      entry.waitingEpoch = memory.saveEpoch;
    } else if (result.outcome === "rejected" && DISCARD_CODES.has(result.code)) {
      discardEntry(entry);
      // The server wins after a discarded entry: re-read the canonical
      // reading/availability instead of showing optimistic progress.
      refreshCanonicalState();
    } else if (result.outcome === "rejected" && RETRYABLE_CODES.has(result.code)) {
      entry.status = "failed";
    } else if (result.outcome === "stale" || result.outcome === "error") {
      entry.status = "failed";
    } else {
      // Every matched terminal result settles the attempt; an unknown
      // rejection is an unsaved entry with an explicit retry, never a stuck
      // queue.
      entry.status = "failed";
    }
    publishSnapshot();
    ctx.publishView();
    return true;
  };
}

export default { applyDialogueReading, MAX_PENDING_COMPLETIONS, DIALOGUE_ACK_TIMEOUT_MS };
