// webclient-motion-level (design D1/D2/D10): the motion level of the
// presentation-preferences slice.
//
// The store is the only resolver. It holds `prefs.motionLevel` (`null` or one
// of `MOTION_LEVELS`), follows the operating system's
// `prefers-reduced-motion: reduce` preference live while nothing is stored,
// writes the EFFECTIVE level to `<html data-motion>`, and persists the stored
// level through the versioned layout store (version 3).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import LayoutStore from "../../lib/layout_store.js";

const KEY = LayoutStore.STORAGE_KEY;
const ROOT = document.documentElement;

// A `matchMedia` stub the test can drive, mirroring the shape the store reads
// (`matches` plus an `addEventListener("change", …)`).
function stubMatchMedia(matches) {
  const listeners = new Set();
  const media = {
    matches,
    media: "(prefers-reduced-motion: reduce)",
    addEventListener: (_type, fn) => listeners.add(fn),
    removeEventListener: (_type, fn) => listeners.delete(fn),
  };
  window.matchMedia = () => media;
  return {
    listeners,
    set(value) {
      media.matches = value;
      for (const fn of listeners) fn({ matches: value });
    },
  };
}

// Count the `data-motion` writes so "the listener did not re-apply" is an
// observable, not a tautology.
function recordDataMotionWrites() {
  const original = ROOT.setAttribute;
  const writes = [];
  ROOT.setAttribute = function setAttribute(name, value) {
    if (name === "data-motion") {
      writes.push(value);
    }
    return original.call(this, name, value);
  };
  return {
    writes,
    restore() {
      ROOT.setAttribute = original;
    },
  };
}

function stored() {
  return JSON.parse(window.localStorage.getItem(KEY));
}

function seed(wrapper) {
  window.localStorage.setItem(KEY, JSON.stringify(wrapper));
}

function freshStore() {
  setActivePinia(createPinia());
  return useElosernStore();
}

describe("motion level preference", () => {
  const originalMatchMedia = window.matchMedia;

  beforeEach(() => {
    window.localStorage.clear();
    ROOT.removeAttribute("data-motion");
  });

  afterEach(() => {
    window.localStorage.clear();
    ROOT.removeAttribute("data-motion");
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
  });

  it("follows the operating system while nothing is stored, and stores nothing", () => {
    stubMatchMedia(true);
    const store = freshStore();
    expect(store.view.motionLevel).toBe("reduced");
    expect(ROOT.getAttribute("data-motion")).toBe("reduced");
    expect(window.localStorage.getItem(KEY)).toBeNull();

    stubMatchMedia(false);
    const plain = freshStore();
    expect(plain.view.motionLevel).toBe("full");
    expect(ROOT.getAttribute("data-motion")).toBe("full");
    expect(window.localStorage.getItem(KEY)).toBeNull();
  });

  it("re-applies on a live OS change while nothing is stored, and never persists it", () => {
    const media = stubMatchMedia(false);
    const store = freshStore();
    expect(store.view.motionLevel).toBe("full");
    expect(media.listeners.size).toBeGreaterThan(0);

    const writes = recordDataMotionWrites();
    try {
      media.set(true);
      expect(ROOT.getAttribute("data-motion")).toBe("reduced");
      expect(store.view.motionLevel).toBe("reduced");
      expect(writes.writes).toEqual(["reduced"]);

      media.set(false);
      expect(ROOT.getAttribute("data-motion")).toBe("full");
      expect(store.view.motionLevel).toBe("full");
    } finally {
      writes.restore();
    }
    expect(window.localStorage.getItem(KEY)).toBeNull();
  });

  it("ignores a live OS change once a level is stored", () => {
    const media = stubMatchMedia(true);
    const store = freshStore();
    store.setMotionLevel("full");
    expect(ROOT.getAttribute("data-motion")).toBe("full");

    const before = window.localStorage.getItem(KEY);
    const writes = recordDataMotionWrites();
    try {
      media.set(false);
      expect(writes.writes).toEqual([]);
    } finally {
      writes.restore();
    }
    expect(ROOT.getAttribute("data-motion")).toBe("full");
    expect(store.view.motionLevel).toBe("full");
    expect(window.localStorage.getItem(KEY)).toBe(before);
  });

  it("applies and persists a selected level, which beats the OS preference", () => {
    stubMatchMedia(true);
    const store = freshStore();
    expect(store.view.motionLevel).toBe("reduced");

    store.setMotionLevel("full");
    expect(ROOT.getAttribute("data-motion")).toBe("full");
    expect(store.view.motionLevel).toBe("full");
    expect(stored().layout_version).toBe(3);
    expect(stored().preferences.motionLevel).toBe("full");

    store.setMotionLevel("off");
    expect(ROOT.getAttribute("data-motion")).toBe("off");
    expect(stored().preferences.motionLevel).toBe("off");

    // The stored level survives a reload, still beating the OS preference.
    const reloaded = freshStore();
    expect(reloaded.view.motionLevel).toBe("off");
    expect(ROOT.getAttribute("data-motion")).toBe("off");
  });

  it("ignores a value outside the three levels", () => {
    stubMatchMedia(false);
    const store = freshStore();
    store.setMotionLevel("reduced");
    for (const invalid of ["dim", "FULL", "on", null, undefined, 1, true, {}]) {
      store.setMotionLevel(invalid);
    }
    expect(store.view.motionLevel).toBe("reduced");
    expect(stored().preferences.motionLevel).toBe("reduced");
  });

  it("discards an invalid stored level, as if nothing were stored", () => {
    stubMatchMedia(true);
    seed({
      layout_version: 3,
      dimensions: {},
      tabs: {},
      preferences: { fontScale: 1.12, motionLevel: "warp" },
    });
    const store = freshStore();
    expect(store.view.motionLevel).toBe("reduced");
    expect(store.view.fontScale).toBe(1.12);
  });

  it("resets a version-2 wrapper to the version-3 default", () => {
    stubMatchMedia(false);
    seed({
      layout_version: 2,
      dimensions: {},
      tabs: {},
      preferences: { fontScale: 1.12, reducedMotion: true, motionLevel: "off" },
    });
    const store = freshStore();
    expect(store.view.motionLevel).toBe("full");
    expect(store.view.fontScale).toBe(1);
    expect(ROOT.getAttribute("data-motion")).toBe("full");
    expect(stored().layout_version).toBe(3);
  });
});
