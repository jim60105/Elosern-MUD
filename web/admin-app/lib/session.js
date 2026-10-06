import { reactive } from "vue";

// The operator session as fetched from /gm/api/session, loaded once and
// shared by the shell header and the overview. Plain reactive state: S1 has
// no domain store, so Pinia is not needed.
export function createSessionState(api) {
  const state = reactive({ status: "idle", data: null, error: null });
  let pending = null;

  async function load({ force = false } = {}) {
    if (pending && !force) return pending;
    state.status = "loading";
    state.error = null;
    pending = api
      .get("/session")
      .then((data) => {
        state.data = data;
        state.status = "ready";
        return data;
      })
      .catch((error) => {
        state.error = error;
        state.status = "error";
        pending = null;
        return null;
      });
    return pending;
  }

  return { state, load };
}
