// webclient-scene-transitions (design D1): the one inert rule for every
// leaving copy. Each hook's effect on `inert`, element by element.
import { describe, expect, it } from "vitest";
import { inertWhileLeaving } from "../lib/transition_hooks.js";

describe("inertWhileLeaving", () => {
  it("makes a leaving element inert in the patch that removes it", () => {
    const el = document.createElement("div");
    inertWhileLeaving.onBeforeLeave(el);
    expect(el.inert).toBe(true);
  });

  it("clears inert once the leave finishes", () => {
    const el = document.createElement("div");
    inertWhileLeaving.onBeforeLeave(el);
    inertWhileLeaving.onAfterLeave(el);
    expect(el.inert).toBe(false);
  });

  it("clears inert when a v-show element re-enters mid-leave", () => {
    const el = document.createElement("div");
    inertWhileLeaving.onBeforeLeave(el);
    inertWhileLeaving.onLeaveCancelled(el);
    expect(el.inert).toBe(false);
  });

  it("an entering element is in reach from its first frame", () => {
    const el = document.createElement("div");
    el.inert = true;
    inertWhileLeaving.onBeforeEnter(el);
    expect(el.inert).toBe(false);
  });

  it("binds exactly the four Transition hook props and cannot be mutated", () => {
    expect(Object.keys(inertWhileLeaving).sort()).toEqual(
      ["onAfterLeave", "onBeforeEnter", "onBeforeLeave", "onLeaveCancelled"],
    );
    expect(Object.isFrozen(inertWhileLeaving)).toBe(true);
  });
});
