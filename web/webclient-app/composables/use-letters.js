// Personal correspondence uses the existing correlated result-data channel.
// No list or mount opens a letter: only an explicit read establishes knowledge.
//
// D1 (correspondence-panel-open-once): one component lifetime IS one opening.
// The panel's conditional mount in AppClient is the lifecycle boundary, so an
// ordinary presentation that replaces `store.view` wholesale never resets this
// local state. The array-returning boundary watcher is deleted: the drawer
// teardown owns disconnect, detach, and epoch/generation replacement.
// D2: the first collected page is a component-scoped *unsent* intent, consumed
// before dispatch and disposed on close. Once a request id exists the attempt is
// consumed permanently for this opening; nothing re-arms on a result or lock
// release, so a submitted failure needs an explicit close-and-reopen.
import { computed, onUnmounted, ref, watch } from "vue";

// Player-facing notices (zh-TW, full-width punctuation).
const WAITING_MESSAGE = "正在載入信件。";
const REFUSED_MESSAGE = "目前無法操作信件，請稍後再試。";
const SYNC_FAILURE_MESSAGE = "信件操作未完成，請關閉信件面板後重新開啟。";
const LIST_FAILURE_SUFFIX = "請關閉信件面板後重新開啟，以重新載入信件。";

export function useLetters(store) {
  const page = ref(null);
  const opened = ref(null);
  const message = ref(WAITING_MESSAGE);
  const pending = ref(null);
  const recipient = ref("");
  const body = ref("");
  let sendId = null;
  let sendFingerprint = null;

  // The identity this opening belongs to (D2/D3). A publication that changes
  // either has already left this opening — the drawer teardown is about to
  // unmount it — so no submission, result, or private state may cross that
  // boundary even if the component is still mounted for the current tick.
  const openingEpoch = store.view.epoch;
  const openingGeneration = store.view.generation;
  const sameOpening = () =>
    store.view.epoch === openingEpoch && store.view.generation === openingGeneration;

  // The unsent initial-load intent: true only while this opening still owes its
  // one first-page request.
  const initialIntent = ref(true);

  // Dispatch readiness, mirroring `dispatchAction`'s gates (D2): connected,
  // active phase, no mutation lock, no in-flight/global request, no local
  // pending action, and no combat beat lock. Expressed as primitives/one
  // computed so the readiness watcher never observes a freshly allocated
  // array (whose identity changes on every wholesale view replacement).
  const ready = computed(() => {
    const view = store.view;
    return (
      !!view.connected &&
      view.phase === "active" &&
      !view.mutationsLocked &&
      !view.dispatch?.inFlight &&
      !view.dispatch?.beatLocked &&
      pending.value === null
    );
  });
  const locked = computed(() => !ready.value);

  function handleResult(result) {
    const request = pending.value;
    if (!request || !result || result.requestId !== request.requestId ||
        result.epoch !== request.epoch || store.view.generation !== request.generation) {
      return;
    }
    pending.value = null;
    if (result.outcome !== "success") {
      const failure = result.message || "信件操作未完成。";
      // A failed list load never retries; the player recovers by closing and
      // reopening the folio (the only refresh boundary, D1/D2).
      message.value = request.action === "letters.list" ? `${failure}${LIST_FAILURE_SUFFIX}` : failure;
      return;
    }
    const data = result.data;
    if (request.action === "letters.read") {
      if (!data || !Array.isArray(data.body_parts)) { message.value = "信件資料無法讀取。"; return; }
      opened.value = { sourceId: data.source_id, senderId: data.sender_id, body: data.body_parts.join("") };
      const row = page.value?.letters.find((letter) => letter.source_id === data.source_id);
      if (row && Number.isSafeInteger(data.read_tick)) row.read_tick = data.read_tick;
      message.value = "信件已開啟。";
    } else {
      page.value = data;
      message.value = request.action === "letters.collect" ? `已領取 ${data.count} 封信件。` :
        request.action === "letters.send" ? "信件已寄出。" : "";
      if (request.action === "letters.send") { body.value = ""; sendId = null; sendFingerprint = null; }
    }
  }

  // Returns true when a request was submitted (a request id exists), false when
  // nothing was submitted.
  function dispatch(action, payload) {
    if (!sameOpening()) return false;
    if (!ready.value) { message.value = REFUSED_MESSAGE; return false; }
    const epoch = store.view.epoch;
    const generation = store.view.generation;
    const requestId = store.dispatchAction(action, payload, null);
    if (requestId == null) return false;
    // The send can synchronously cross the opening boundary; never install
    // local state for a request that now belongs to another identity.
    if (!sameOpening()) return false;
    pending.value = { requestId, action, epoch, generation };
    message.value = "處理中。";
    // The synchronous transport-failure contract (transport.js): a thrown
    // sender clears the in-flight record, sets uncertainty, publishes, and
    // still returns this request id with no `ui_action_result`. Correlate it
    // immediately — a cleared in-flight record alone could belong to an
    // unrelated earlier failure, and a completed result for this request means
    // the send did reach the server.
    const d = store.view.dispatch;
    if (d?.submittedRequestId === requestId && !d.inFlight && d.uncertain &&
        store.view.lastActionResult?.requestId !== requestId) {
      pending.value = null;
      message.value = SYNC_FAILURE_MESSAGE;
      return true;
    }
    // A transport that delivers the result synchronously settles the request
    // before the observer below can run; consume it here so the one attempt is
    // never left pending.
    const settled = store.view.lastActionResult;
    if (settled && settled.requestId === requestId && settled.epoch === epoch &&
        store.view.generation === generation) {
      handleResult(settled);
    }
    return true;
  }

  const listPage = (after = 0) => dispatch("letters.list", { after });
  const collect = () => dispatch("letters.collect", {});
  const read = (sourceId) => dispatch("letters.read", { source_id: sourceId });
  function send() {
    const units = Array.from(body.value);
    if (!recipient.value.trim() || !body.value.trim() || units.length > 8000) {
      message.value = "請填寫收件人與 1 至 8000 字的內容。"; return false;
    }
    const fingerprint = JSON.stringify([recipient.value, body.value]);
    if (fingerprint !== sendFingerprint) {
      sendFingerprint = fingerprint;
      sendId = crypto.randomUUID();
    }
    const parts = [];
    for (let offset = 0; offset < units.length; offset += 2000) parts.push(units.slice(offset, offset + 2000).join(""));
    return dispatch("letters.send", { recipient: recipient.value, body_parts: parts, source_id: sendId });
  }

  // The one initial first-page request per opening (D2). The intent is consumed
  // BEFORE the dispatch so the synchronous `publishView` re-entry cannot
  // schedule a second one; it is re-armed only when no request id was produced
  // and this opening is still live. A readiness refusal submits nothing and is
  // simply re-evaluated on the next readiness transition (never a timer).
  function attemptInitialLoad() {
    if (!initialIntent.value) return;
    if (!sameOpening()) { initialIntent.value = false; return; }
    if (!ready.value) return;
    initialIntent.value = false;
    if (!listPage(0) && sameOpening()) initialIntent.value = true;
  }

  // The result observer is installed before the immediate initial-load watcher
  // so a synchronous completion during that first dispatch is still observed.
  watch(() => store.view.lastActionResult, (result) => {
    if (!sameOpening()) return;
    handleResult(result);
  });
  watch(ready, attemptInitialLoad, { immediate: true });
  // Closing disposes the unsent intent (Vue also stops both watchers).
  onUnmounted(() => { initialIntent.value = false; });

  return { page, opened, message, recipient, body, locked, listPage, collect, read, send };
}
