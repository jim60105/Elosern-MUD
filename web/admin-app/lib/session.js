import { reactive } from "vue";

// The operator session as fetched from /gm/api/session, loaded once and
// shared by the shell header and the overview. Plain reactive state: S1 has
// no domain store, so Pinia is not needed.
export function createSessionState(api) {
  const state = reactive({ status: "idle", data: null, error: null });
  let pending = null;
  // Only the latest request may write the state; a slower, older response
  // (e.g. before a forced reload) is ignored.
  let latest = 0;

  async function load({ force = false } = {}) {
    if (pending && !force) return pending;
    const token = ++latest;
    state.status = "loading";
    state.error = null;
    const request = api
      .get("/session")
      .then((data) => {
        if (token !== latest) return data;
        state.data = data;
        state.status = "ready";
        return data;
      })
      .catch((error) => {
        if (token !== latest) return null;
        state.error = error;
        state.status = "error";
        pending = null;
        return null;
      });
    pending = request;
    return request;
  }

  return { state, load };
}
