// The dream stage's farewell hold (dream-farewell-beat): which committed
// transitions keep a closed dream on stage, and what ends the hold.
import { describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, reactive } from "vue";
import { useDreamFarewell } from "../composables/use-dream-farewell.js";

function dream(overrides = {}) {
  return { session_id: "synthetic-dream", revision: 2, open: true, confirmed: false, ending: "", ...overrides };
}
const closed = (overrides = {}) => dream({ revision: 3, open: false, ending: "合成的告別", ...overrides });

function harness(first = dream()) {
  const store = reactive({
    view: { connected: true, panels: { dream: first === null ? null : { state: first } } },
    setDreamFarewellActive: vi.fn(),
  });
  const scope = effectScope();
  const stage = scope.run(() => useDreamFarewell(store));
  // Each publication replaces the panel, as the store's view projection does.
  const publish = (state) => { store.view = { ...store.view, panels: { dream: state === null ? null : { state } } }; };
  return { store, scope, stage, publish };
}

describe("dream farewell hold", () => {
  it("holds a live departure of the same session that carries an ending", () => {
    const { stage, publish } = harness();
    expect(stage.state.value.open).toBe(true);
    publish(closed());
    expect(stage.active.value).toBe(true);
    expect(stage.held.value).toEqual(closed());
    expect(stage.state.value.ending).toBe("合成的告別");
    // A copy: a later publication cannot change the presented farewell.
    publish(closed({ ending: "合成的另一句" }));
    expect(stage.state.value.ending).toBe("合成的告別");
    publish(null);
    expect(stage.active.value).toBe(true);
  });

  it("does not hold a state that is already closed when first seen", () => {
    const { stage, publish } = harness(closed());
    expect(stage.active.value).toBe(false);
    publish(closed({ revision: 4 }));
    expect(stage.active.value).toBe(false);
    expect(stage.state.value).toBeNull();
  });

  it("does not hold a closed state of a different session", () => {
    const { stage, publish } = harness();
    publish(closed({ session_id: "synthetic-other" }));
    expect(stage.active.value).toBe(false);
  });

  it("does not hold a departure without ending text", () => {
    const { stage, publish } = harness();
    publish(closed({ ending: "" }));
    expect(stage.active.value).toBe(false);
  });

  it("keeps the hold unchanged when the same closed state republishes", () => {
    const { stage, publish } = harness();
    publish(closed());
    const first = stage.held.value;
    publish(closed());
    expect(stage.held.value).toBe(first);
    expect(stage.generation.value).toBe(0);
  });

  it("drops a held farewell on disconnect", () => {
    const { store, stage, publish } = harness();
    publish(closed());
    store.view = { ...store.view, connected: false };
    expect(stage.active.value).toBe(false);
    // The reconnect's closed state is not replayed.
    store.view = { ...store.view, connected: true };
    publish(closed({ revision: 5 }));
    expect(stage.active.value).toBe(false);
  });

  it("discards a held farewell when a new open dream is committed", () => {
    const { stage, publish } = harness();
    publish(closed());
    publish(dream({ revision: 4 }));
    expect(stage.held.value).toBeNull();
    expect(stage.state.value).toEqual(dream({ revision: 4 }));
    expect(stage.generation.value).toBe(1);
  });

  it("releases the stage on release()", () => {
    const { stage, publish } = harness();
    publish(closed());
    stage.release();
    expect(stage.active.value).toBe(false);
    expect(stage.state.value).toBeNull();
  });

  it("raises the store flag while a farewell is held and lowers it on release", async () => {
    const { store, scope, stage, publish } = harness();
    await nextTick();
    // An open dream is not a farewell; the flag follows the whole stage.
    expect(store.setDreamFarewellActive).toHaveBeenLastCalledWith(true);
    publish(closed());
    await nextTick();
    expect(store.setDreamFarewellActive).toHaveBeenLastCalledWith(true);
    stage.release();
    await nextTick();
    expect(store.setDreamFarewellActive).toHaveBeenLastCalledWith(false);
    scope.stop();
    expect(store.setDreamFarewellActive).toHaveBeenLastCalledWith(false);
  });
});
