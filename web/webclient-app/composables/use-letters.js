// Personal correspondence uses the existing correlated result-data channel.
// No list or mount opens a letter: only an explicit read establishes knowledge.
import { computed, onMounted, ref, watch } from "vue";

export function useLetters(store) {
  const page = ref(null);
  const opened = ref(null);
  const message = ref("");
  const pending = ref(null);
  const recipient = ref("");
  const body = ref("");
  let sendId = null;
  let sendFingerprint = null;
  const locked = computed(() => !!pending.value || !store.view.connected || !!store.view.dispatch?.inFlight);

  function dispatch(action, payload) {
    if (locked.value) return false;
    const requestId = store.dispatchAction(action, payload, null);
    if (requestId == null) { message.value = "目前無法操作信件，請稍後再試。"; return false; }
    pending.value = { requestId, action, epoch: store.view.epoch, generation: store.view.generation };
    message.value = "處理中。";
    return true;
  }
  const refresh = (after = 0) => dispatch("letters.list", { after });
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
  watch(() => store.view.lastActionResult, (result) => {
    const request = pending.value;
    if (!request || !result || result.requestId !== request.requestId || result.epoch !== request.epoch ||
        store.view.generation !== request.generation) return;
    pending.value = null;
    if (result.outcome !== "success") { message.value = result.message || "信件操作未完成。"; return; }
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
  });
  watch(() => [store.view.epoch, store.view.generation, store.view.connected], () => {
    pending.value = null;
    page.value = null;
    opened.value = null;
    // Never carry another character's private prose across a session boundary.
    recipient.value = "";
    body.value = "";
    sendId = null;
    sendFingerprint = null;
    message.value = "連線或角色已變更，請重新載入信件。";
  });
  onMounted(() => refresh());
  return { page, opened, message, recipient, body, locked, refresh, collect, read, send };
}
