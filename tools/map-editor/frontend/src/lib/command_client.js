// Named document commands, undo and redo over the authenticated service API.
//
// Commands run strictly one at a time. Each queued operation is built only
// when its turn comes, against the workspace snapshot the service returned
// after the previous one, so its expected document fingerprint and snapshot
// revision are current. A rejected or failed command is reported and the
// rest of the queue is dropped: nothing is retried, replayed or restored
// from browser storage. The launch token lives in memory only.

export function newSegment(cryptoImpl = globalThis.crypto) {
  if (cryptoImpl?.randomUUID) return cryptoImpl.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function createCommandClient({
  fetchImpl,
  getWorkspace,
  refetch,
  onChange = () => {},
  segment = newSegment(),
  sessionUrl = "/api/session",
}) {
  const state = { inFlight: 0, failure: null, savedAt: null, lastDocument: null };
  let token = null;
  let tokenSession = null;
  let tail = Promise.resolve();
  let generation = 0;

  const emit = () => onChange({ ...state });

  async function currentToken(workspace) {
    if (!token || tokenSession !== workspace.session_generation) {
      const response = await fetchImpl(sessionUrl, { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error(`session request failed: ${response.status}`);
      const body = await response.json();
      token = body.token;
      tokenSession = body.session_generation;
    }
    return token;
  }

  async function post(url, body, workspace) {
    const response = await fetchImpl(url, {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: { "Content-Type": "application/json", "X-Map-Editor-Token": await currentToken(workspace) },
      body: JSON.stringify(body),
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    return { ok: response.ok, status: response.status, payload };
  }

  async function run(build) {
    const workspace = getWorkspace();
    const command = workspace ? build(workspace) : null;
    if (!command) return null;
    const body = {
      session_generation: workspace.session_generation,
      snapshot_revision: workspace.snapshot_revision,
      segment,
      document_id: command.documentId,
      expected_document_fingerprint: command.expected,
      arguments: command.arguments,
    };
    const result = await post(`/api/commands/${command.name}`, body, workspace);
    if (!result.ok) {
      const error = result.payload?.error ?? {};
      throw Object.assign(new Error(error.message ?? `HTTP ${result.status}`), {
        failure: {
          command: command.name,
          code: error.code ?? `http_${result.status}`,
          message: error.message ?? `HTTP ${result.status}`,
          documentId: error.document_id ?? command.documentId,
          details: error,
        },
      });
    }
    if (result.payload?.changed) {
      state.savedAt = new Date().toISOString();
      state.lastDocument = result.payload.document_id;
    }
    return result.payload;
  }

  // Queue one operation; `build(workspace)` returns the command or null.
  function enqueue(build) {
    const ticket = generation;
    state.inFlight += 1;
    emit();
    const task = tail.then(async () => {
      try {
        if (ticket !== generation) return null; // dropped after an earlier failure
        const payload = await run(build);
        await refetch();
        return payload;
      } catch (error) {
        generation += 1;
        state.failure = error.failure ?? {
          command: "unknown",
          code: "network_error",
          message: String(error?.message ?? error),
          documentId: null,
        };
        await refetch();
        return null;
      } finally {
        state.inFlight -= 1;
        emit();
      }
    });
    tail = task;
    return task;
  }

  function history(direction) {
    return enqueue((workspace) => {
      const history = workspace.history;
      const head = history?.segment === segment ? history[direction] : null;
      if (!head) return null;
      return {
        name: direction,
        documentId: head.document_id,
        expected: head.expected_document_fingerprint,
        arguments: {},
      };
    });
  }

  // Save: wait until every accepted operation has an answer. Drafts are never
  // submitted from here.
  function flush() {
    return tail;
  }

  async function reload() {
    await tail;
    const workspace = getWorkspace();
    if (!workspace) return;
    const result = await post("/api/reload", { session_generation: workspace.session_generation }, workspace);
    if (result.ok) {
      state.failure = null;
      emit();
    }
    await refetch();
  }

  function canUndo(workspace) {
    return workspace?.history?.segment === segment && Boolean(workspace.history.undo);
  }

  function canRedo(workspace) {
    return workspace?.history?.segment === segment && Boolean(workspace.history.redo);
  }

  return {
    segment,
    submit: enqueue,
    undo: () => history("undo"),
    redo: () => history("redo"),
    flush,
    reload,
    canUndo,
    canRedo,
    state: () => ({ ...state }),
  };
}
