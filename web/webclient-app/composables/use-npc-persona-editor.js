// The NPC author editor's state machine (npc-persona-editor-window D1-D6).
//
// The editor binds BY VALUE to the target identity, presentation epoch,
// transport generation, and current character captured when 編輯人物設定 is
// activated; it never follows a later selection. Every `npc.persona.read` /
// `npc.persona.update` it dispatches is recorded as the single pending
// request, and a result is applied only when its request id, epoch, and
// transport generation match that record and the editor is still bound to
// the same NPC — so a late result for a closed editor, another target, or a
// superseded request can neither seed nor close the current one.
//
// States (the `state` computed): closed, loading, ready_clean, ready_dirty,
// saving, conflict, rejected, unavailable. Only a confirmed server save
// replaces the baseline; a rejection keeps the draft; a transport loss makes
// no claim and re-reads after reconnecting the same character; a departure
// keeps the draft visible with save disabled. Logout (detach), a
// same-transport epoch replacement, or a reconnect onto another character
// closes the editor and drops every piece of editor state. Nothing here ever
// touches localStorage/sessionStorage.
import { computed, nextTick, reactive, ref, watch } from "vue";
import {
  changedFields,
  draftFromData,
  emptyDraft,
  fieldLabel,
  personaFromDraft,
  rejectionField,
  sameDraft,
  validateDraft,
} from "../components/npc-persona-editor-model.js";

const READ = "npc.persona.read";
const UPDATE = "npc.persona.update";
const EDITABLE_MODES = new Set(["exploration", "dialogue"]);

export function useNpcPersonaEditor(store, { shellRef = null } = {}) {
  const binding = ref(null);
  const pending = ref(null);
  const header = ref({ displayName: "", npcTitle: "" });
  const version = ref(null);
  const baseline = ref(null);
  const draft = reactive(emptyDraft());
  const defaultGreeting = ref("");
  const rejection = ref(null);
  const conflict = ref(null);
  const readFailure = ref(null);
  const needsResync = ref(false);
  const discardAfterReload = ref(false);
  const announcement = ref("");
  const focusRequest = ref(null);
  let handledResult = null;
  let announceSeq = 0;

  function announce(message) {
    // A trailing zero-width variation keeps an identical repeated message
    // re-announced by the polite live region.
    announceSeq += 1;
    announcement.value = announceSeq % 2 ? message : `${message}​`;
  }

  function currentCharacterId() {
    const row = (store.view.rosterCharacters || []).find((character) => character.current);
    return row && row.identity != null ? row.identity : null;
  }

  function resetState() {
    binding.value = null;
    pending.value = null;
    header.value = { displayName: "", npcTitle: "" };
    version.value = null;
    baseline.value = null;
    Object.assign(draft, emptyDraft());
    defaultGreeting.value = "";
    rejection.value = null;
    conflict.value = null;
    readFailure.value = null;
    needsResync.value = false;
    discardAfterReload.value = false;
    announcement.value = "";
    focusRequest.value = null;
    handledResult = null;
  }

  function dispatch(actionId, payload, kind) {
    const requestId = store.dispatchAction(actionId, payload, null);
    if (requestId === null) {
      return false;
    }
    pending.value = {
      requestId,
      kind,
      npcId: binding.value.npcId,
      epoch: store.view.epoch,
      generation: store.view.generation,
    };
    return true;
  }

  function read(kind) {
    if (!binding.value || pending.value) {
      return false;
    }
    const sent = dispatch(READ, { npc_id: binding.value.npcId }, kind);
    if (!sent && kind !== "resync") {
      // A refused dispatch (another mutation in flight, a locked phase) is
      // explicit, never a silent drop; the player can retry.
      if (baseline.value === null) {
        readFailure.value = { message: "目前無法讀取人物設定，請稍後再試。", retryable: true };
      }
      announce("目前無法讀取人物設定，請稍後再試。");
    }
    return sent;
  }

  // ------------------------------------------------------ departure / mode

  // Present: the committed exploration panel still lists the bound NPC as an
  // interact target in an editable mode. Unknown (no committed panel yet
  // while reconnecting) reads as null so it never flips the state alone.
  const present = computed(() => {
    const bound = binding.value;
    if (!bound) {
      return null;
    }
    const panel = store.view.panels && store.view.panels.exploration;
    if (!store.view.connected || !panel) {
      return null;
    }
    if (!EDITABLE_MODES.has(store.view.mode) || panel.available !== true) {
      return false;
    }
    return (panel.interact || []).some((target) => target.identity === bound.npcId);
  });

  // ---------------------------------------------------------------- binding

  watch(
    () => store.view.npcPersonaRequest && store.view.npcPersonaRequest.seq,
    (seq) => {
      const request = store.view.npcPersonaRequest;
      if (!seq || !request) {
        return;
      }
      resetState();
      binding.value = {
        npcId: request.npcId,
        epoch: store.view.epoch,
        generation: store.view.generation,
        characterId: currentCharacterId(),
        openerEl: typeof document !== "undefined" ? document.activeElement : null,
      };
      read("initial");
    },
  );

  // The drawer closed by another route (an overlay replaced it, a teardown):
  // drop every piece of editor state.
  watch(
    () => store.view.hudDrawer,
    (name) => {
      if (name !== "npc_persona" && binding.value) {
        resetState();
      } else if (name === "npc_persona" && !binding.value) {
        // Opened without a bound target (not through 編輯人物設定): nothing
        // to edit, so the empty drawer name never lingers.
        store.closeHudDrawer();
      }
    },
  );

  // ------------------------------------------------------------ correlation

  function applyRead(result, kind) {
    const data = result.data;
    if (!data || data.npc_id !== binding.value.npcId) {
      return;
    }
    const fresh = draftFromData(data);
    header.value = { displayName: data.display_name || "", npcTitle: data.npc_title || "" };
    defaultGreeting.value = typeof data.default_greeting === "string" ? data.default_greeting : "";
    readFailure.value = null;
    if (kind === "initial" || baseline.value === null) {
      needsResync.value = false;
      baseline.value = fresh;
      version.value = data.persona_version;
      Object.assign(draft, fresh);
      announce(`已載入${header.value.displayName}的人物設定（第 ${data.persona_version} 版）。`);
      return;
    }
    if (kind === "resync") {
      needsResync.value = false;
      if (data.persona_version === version.value) {
        announce("連線已恢復，草稿仍保留。");
        return;
      }
      if (sameDraft(draft, fresh)) {
        // The version moved to exactly what the draft holds (typically this
        // editor's own save whose result was lost): adopt it as saved.
        baseline.value = fresh;
        version.value = data.persona_version;
        conflict.value = null;
        announce(`連線已恢復，人物設定目前為第 ${data.persona_version} 版。`);
        return;
      }
      conflict.value = { version: data.persona_version, message: null };
      announce(`連線期間人物設定已更新為第 ${data.persona_version} 版，你的草稿仍保留。`);
      return;
    }
    // kind === "reload": replace the baseline and version, keep the draft
    // unless the player chose to discard.
    baseline.value = fresh;
    version.value = data.persona_version;
    conflict.value = null;
    rejection.value = null;
    if (discardAfterReload.value) {
      discardAfterReload.value = false;
      Object.assign(draft, fresh);
      announce(`已放棄修改，顯示第 ${data.persona_version} 版的設定。`);
    } else {
      announce(`已重新載入第 ${data.persona_version} 版；你的修改仍保留，確認後可再儲存。`);
    }
  }

  function applySave(result) {
    if (result.outcome === "success") {
      const data = result.data;
      if (!data || data.npc_id !== binding.value.npcId) {
        return;
      }
      const saved = draftFromData(data);
      baseline.value = saved;
      version.value = data.persona_version;
      Object.assign(draft, saved);
      defaultGreeting.value = typeof data.default_greeting === "string" ? data.default_greeting : "";
      rejection.value = null;
      conflict.value = null;
      announce(
        result.code === "unchanged"
          ? "內容與已儲存的設定相同，沒有變更。"
          : `已儲存為第 ${data.persona_version} 版。`,
      );
      return;
    }
    const message = typeof result.message === "string" && result.message ? result.message : "儲存未完成，草稿已保留。";
    if (result.code === "npc_persona.version_conflict") {
      conflict.value = { version: null, message };
      announce(message);
      return;
    }
    const field = rejectionField(result.code);
    rejection.value = { code: result.code, message, field };
    if (field) {
      focusRequest.value = { field, seq: (focusRequest.value?.seq || 0) + 1 };
    }
    announce(field ? `${fieldLabel(field)}：${message}` : message);
  }

  function applyReadFailure(result, kind) {
    const message = typeof result.message === "string" && result.message ? result.message : "目前無法讀取人物設定。";
    if (kind === "resync") {
      // The re-read after a reconnect was refused (the NPC left, the mode
      // changed): stay unavailable with the draft until it is present again.
      needsResync.value = true;
      announce(message);
      return;
    }
    if (baseline.value === null) {
      readFailure.value = { message, retryable: true };
    }
    discardAfterReload.value = false;
    announce(message);
  }

  watch(
    () => store.view.lastActionResult,
    (result) => {
      const request = pending.value;
      if (!result || !request || !binding.value) {
        return;
      }
      if (
        result.requestId !== request.requestId ||
        result.epoch !== request.epoch ||
        store.view.generation !== request.generation ||
        request.npcId !== binding.value.npcId
      ) {
        return;
      }
      const fingerprint = `${request.generation}|${request.epoch}|${request.requestId}`;
      if (handledResult === fingerprint) {
        return;
      }
      handledResult = fingerprint;
      pending.value = null;
      if (request.kind === "save") {
        applySave(result);
      } else if (result.outcome === "success") {
        applyRead(result, request.kind);
      } else {
        applyReadFailure(result, request.kind);
      }
    },
  );

  // ------------------------------------------------- transport and session

  watch(
    () => store.view.connected,
    (connected, wasConnected) => {
      if (!binding.value || connected || !wasConnected) {
        return;
      }
      // No claim either way: the pending request's outcome is unknown.
      const lostSave = pending.value && pending.value.kind === "save";
      pending.value = null;
      needsResync.value = true;
      announce(
        lostSave
          ? "連線中斷，無法確認是否已儲存；恢復連線後會重新讀取，你的草稿會保留。"
          : "連線中斷；恢復連線後會重新讀取，你的草稿會保留。",
      );
    },
  );

  watch(
    () => store.view.phase,
    (phase) => {
      if (binding.value && phase === "detached") {
        close({ restoreFocus: true });
      }
    },
  );

  function tryResync() {
    const bound = binding.value;
    const v = store.view;
    if (!bound || !needsResync.value || pending.value) {
      return;
    }
    if (!v.connected || v.phase !== "active" || v.epoch == null || v.mutationsLocked || v.dispatch?.inFlight) {
      return;
    }
    if (v.generation !== bound.generation) {
      const current = currentCharacterId();
      if (bound.characterId != null) {
        if (current == null) {
          // The roster has not committed yet: hold the re-read (and save)
          // until the character is known.
          return;
        }
        if (current !== bound.characterId) {
          close({ restoreFocus: true });
          return;
        }
      }
      bound.epoch = v.epoch;
      bound.generation = v.generation;
    }
    if (v.epoch !== bound.epoch) {
      return;
    }
    read("resync");
  }

  watch(
    () => [
      store.view.connected,
      store.view.phase,
      store.view.epoch,
      store.view.generation,
      store.view.mutationsLocked,
      !!store.view.dispatch?.inFlight,
      currentCharacterId(),
      needsResync.value,
      present.value,
    ],
    () => {
      const bound = binding.value;
      if (!bound) {
        return;
      }
      const v = store.view;
      const characterId = currentCharacterId();
      if (bound.characterId != null && characterId != null && characterId !== bound.characterId) {
        close({ restoreFocus: true });
        return;
      }
      // A new epoch inside the SAME transport generation is a session or
      // puppet replacement: close and drop everything.
      if (v.epoch != null && v.epoch !== bound.epoch && v.generation === bound.generation) {
        close({ restoreFocus: true });
        return;
      }
      if (needsResync.value && present.value !== false) {
        tryResync();
      }
    },
  );

  // ------------------------------------------------------------- derived

  const validation = computed(() => validateDraft(draft));
  const dirty = computed(() => baseline.value !== null && !sameDraft(draft, baseline.value));
  const dirtyFields = computed(() => changedFields(draft, baseline.value));

  const unavailableReason = computed(() => {
    if (!binding.value) {
      return null;
    }
    if (readFailure.value && baseline.value === null) {
      return { kind: "read_failed", message: readFailure.value.message };
    }
    if (baseline.value === null) {
      return null;
    }
    if (!store.view.connected) {
      return { kind: "offline", message: "連線中斷。恢復連線後會重新讀取，草稿會保留。" };
    }
    if (needsResync.value) {
      if (present.value === false) {
        return { kind: "departed", message: "對方已不在這裡，或目前的狀態無法編輯。草稿會保留；回到對方身邊後即可儲存。" };
      }
      return { kind: "resyncing", message: pending.value ? "正在重新讀取人物設定……" : "等待連線與操作狀態恢復後，將重新讀取人物設定。" };
    }
    if (present.value === false) {
      return EDITABLE_MODES.has(store.view.mode)
        ? { kind: "departed", message: "對方已不在這裡。草稿會保留，但目前無法儲存。" }
        : { kind: "mode", message: "目前的狀態無法編輯人物設定。草稿會保留，但目前無法儲存。" };
    }
    return null;
  });

  const state = computed(() => {
    if (!binding.value) return "closed";
    if (baseline.value === null) return readFailure.value ? "unavailable" : "loading";
    if (pending.value && pending.value.kind === "save") return "saving";
    if (unavailableReason.value) return "unavailable";
    if (conflict.value) return "conflict";
    if (rejection.value) return "rejected";
    return dirty.value ? "ready_dirty" : "ready_clean";
  });

  const busy = computed(() => !!pending.value);
  const canSave = computed(
    () =>
      (state.value === "ready_dirty" || state.value === "rejected") &&
      dirty.value &&
      validation.value.valid &&
      !pending.value,
  );

  // --------------------------------------------------------------- intents

  function setField(key, value) {
    if (!binding.value || baseline.value === null || !(key in draft)) {
      return;
    }
    draft[key] = String(value ?? "");
    if (rejection.value && (rejection.value.field === key || rejection.value.field === null || (rejection.value.field === "identity" && key.startsWith("identity.")))) {
      rejection.value = null;
    }
  }

  function save() {
    if (!canSave.value || !binding.value) {
      return false;
    }
    const payload = {
      npc_id: binding.value.npcId,
      expected_persona_version: version.value,
      persona: personaFromDraft(draft),
      offline_greeting: draft.offline_greeting,
    };
    if (!dispatch(UPDATE, payload, "save")) {
      announce("目前無法儲存，請稍後再試。草稿已保留。");
      return false;
    }
    rejection.value = null;
    announce("儲存中……");
    return true;
  }

  function reload() {
    if (!binding.value || pending.value) return false;
    return read("reload");
  }

  function discard() {
    if (!binding.value || pending.value) return false;
    if (conflict.value) {
      // Discarding during a conflict shows the latest saved card: re-read
      // first, then replace the draft with it.
      discardAfterReload.value = true;
      if (!read("reload")) {
        discardAfterReload.value = false;
        return false;
      }
      return true;
    }
    if (baseline.value) {
      Object.assign(draft, baseline.value);
      rejection.value = null;
      announce("已放棄修改。");
    }
    return true;
  }

  function retry() {
    if (!binding.value || pending.value) return false;
    readFailure.value = null;
    return read("initial");
  }

  function close({ restoreFocus = true } = {}) {
    const opener = binding.value ? binding.value.openerEl : null;
    const wasOpen = store.view.hudDrawer === "npc_persona";
    resetState();
    if (wasOpen) {
      store.closeHudDrawer();
    }
    if (!restoreFocus || typeof document === "undefined") {
      return;
    }
    void nextTick().then(() => {
      const active = document.activeElement;
      if (active && active !== document.body && document.contains(active)) {
        return;
      }
      if (opener && document.contains(opener) && typeof opener.focus === "function") {
        opener.focus();
        return;
      }
      shellRef?.value?.restoreFocusHome?.();
    });
  }

  const view = computed(() => ({
    open: !!binding.value,
    state: state.value,
    npcId: binding.value ? binding.value.npcId : null,
    displayName: header.value.displayName,
    npcTitle: header.value.npcTitle,
    version: version.value,
    draft: { ...draft },
    baseline: baseline.value,
    defaultGreeting: defaultGreeting.value,
    validation: validation.value,
    dirty: dirty.value,
    dirtyFields: dirtyFields.value,
    busy: busy.value,
    canSave: canSave.value,
    rejection: rejection.value,
    conflict: conflict.value,
    unavailable: unavailableReason.value,
    announcement: announcement.value,
    focusRequest: focusRequest.value,
  }));

  return {
    npcPersonaEditor: view,
    npcPersonaSetField: setField,
    npcPersonaSave: save,
    npcPersonaReload: reload,
    npcPersonaDiscard: discard,
    npcPersonaRetry: retry,
    npcPersonaClose: close,
  };
}
