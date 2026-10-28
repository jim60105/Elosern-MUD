// The browser's only transport to the editor service.
//
// HTTP returns the complete authoritative workspace state; the SSE stream
// carries status/invalidation only. On every `status` or `invalidate` that
// names another session or revision than the snapshot on screen -- including
// the first `status` after a reconnect -- the client fetches
// GET /api/workspace again and replaces its whole state. Nothing is patched,
// merged or replayed, and nothing is restored from browser storage.
//
// `fetchImpl` and `EventSourceImpl` are injected so the state machine is
// testable without a browser.

export const CONNECTING = "connecting";
export const CONNECTED = "connected";
export const DISCONNECTED = "disconnected";

export function needsRefetch(snapshot, status) {
  if (!status) return false;
  if (!snapshot) return true;
  return (
    status.session_generation !== snapshot.session_generation ||
    status.snapshot_revision !== snapshot.snapshot_revision
  );
}

export function createWorkspaceClient({
  fetchImpl,
  EventSourceImpl,
  onChange,
  workspaceUrl = "/api/workspace",
  eventsUrl = "/api/events",
}) {
  const state = {
    connection: CONNECTING,
    workspace: null,
    // When the snapshot on screen was last confirmed by the service.
    confirmedAt: null,
    error: null,
  };
  let source = null;
  let requestSeq = 0;
  let appliedSeq = 0;

  const emit = () => onChange({ ...state });

  async function refetch() {
    const seq = ++requestSeq;
    try {
      const response = await fetchImpl(workspaceUrl, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`workspace request failed: ${response.status}`);
      const workspace = await response.json();
      // A slower, older response never overwrites a newer one.
      if (seq < appliedSeq) return;
      appliedSeq = seq;
      state.workspace = workspace;
      state.confirmedAt = workspace.checked_at ?? null;
      state.error = null;
      emit();
    } catch (error) {
      state.error = String(error?.message ?? error);
      emit();
    }
  }

  function handleStatus(event) {
    let status = null;
    try {
      status = JSON.parse(event.data);
    } catch {
      return;
    }
    state.connection = CONNECTED;
    if (needsRefetch(state.workspace, status) || event.type === "invalidate") {
      emit();
      refetch();
    } else {
      emit();
    }
  }

  function start() {
    source = new EventSourceImpl(eventsUrl);
    source.addEventListener("status", handleStatus);
    source.addEventListener("invalidate", handleStatus);
    source.onerror = () => {
      // The browser keeps retrying; the last snapshot stays on screen and is
      // presented as disconnected until the next status refetches it.
      state.connection = DISCONNECTED;
      emit();
    };
    emit();
  }

  function stop() {
    if (source) source.close();
    source = null;
  }

  return { start, stop, refetch, state: () => ({ ...state }) };
}
