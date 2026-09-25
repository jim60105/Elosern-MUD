// webclient-typewriter-reading-prefs (task 5.3): the reading preferences of
// the presentation-preferences slice — the text speed and the opt-in
// auto-advance. Client-local, published on the view, persisted through the
// versioned layout store (version 2), and reset with it.

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import LayoutStore from "../../lib/layout_store.js";

const KEY = LayoutStore.STORAGE_KEY;

function stored() {
  return JSON.parse(window.localStorage.getItem(KEY));
}

function freshStore() {
  setActivePinia(createPinia());
  return useElosernStore();
}

describe("reading preferences", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("defaults to the normal speed with auto-advance off", () => {
    const store = freshStore();
    expect(store.view.textSpeed).toBe("normal");
    expect(store.view.autoAdvance).toBe(false);
  });

  it("applies, persists, and reloads both preferences", () => {
    const store = freshStore();
    store.setTextSpeed("fast");
    store.setAutoAdvance(true);
    expect(store.view.textSpeed).toBe("fast");
    expect(store.view.autoAdvance).toBe(true);
    const wrapper = stored();
    expect(wrapper.layout_version).toBe(2);
    expect(wrapper.preferences.textSpeed).toBe("fast");
    expect(wrapper.preferences.autoAdvance).toBe(true);

    const reloaded = freshStore();
    expect(reloaded.view.textSpeed).toBe("fast");
    expect(reloaded.view.autoAdvance).toBe(true);
  });

  it("ignores a speed outside the four steps", () => {
    const store = freshStore();
    store.setTextSpeed("slow");
    store.setTextSpeed("warp");
    store.setTextSpeed(null);
    expect(store.view.textSpeed).toBe("slow");
    expect(stored().preferences.textSpeed).toBe("slow");
  });

  it("drops an invalid stored speed and keeps the other stored preferences", () => {
    window.localStorage.setItem(
      KEY,
      JSON.stringify({
        layout_version: 2,
        dimensions: {},
        tabs: {},
        preferences: { fontScale: 1.12, textSpeed: "warp", autoAdvance: true },
      }),
    );
    const store = freshStore();
    expect(store.view.textSpeed).toBe("normal");
    expect(store.view.autoAdvance).toBe(true);
    expect(store.view.fontScale).toBe(1.12);
  });

  it("resets a version-1 wrapper to every default", () => {
    window.localStorage.setItem(
      KEY,
      JSON.stringify({
        layout_version: 1,
        dimensions: {},
        tabs: {},
        preferences: { fontScale: 1.12, colorblind: true },
      }),
    );
    const store = freshStore();
    expect(store.view.fontScale).toBe(1);
    expect(store.view.colorblind).toBe(false);
    expect(store.view.textSpeed).toBe("normal");
    expect(store.view.autoAdvance).toBe(false);
    const wrapper = stored();
    expect(wrapper.layout_version).toBe(2);
    expect(wrapper.preferences.textSpeed).toBe("normal");
  });
});
