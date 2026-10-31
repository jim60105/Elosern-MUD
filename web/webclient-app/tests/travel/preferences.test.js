// The travel preferences (wilderness-travel-leg-ui, task 2.1): the leg
// panel's pace and nightfall stop persist in the versioned presentation
// wrapper, reload with it, fall back to their defaults on a missing or
// malformed stored value, and are frozen while a walk (or the hold that
// arms one) is active.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import LayoutStore from "../../lib/layout_store.js";
import { fx, walkArea, walkPanels } from "./support.js";

const KEY = LayoutStore.STORAGE_KEY;
const CX = 60;
const CY = 80;

function stored() {
  return JSON.parse(window.localStorage.getItem(KEY));
}

function freshStore() {
  setActivePinia(createPinia());
  return useElosernStore();
}

function seed(preferences) {
  window.localStorage.setItem(KEY, JSON.stringify({ layout_version: 3, dimensions: {}, tabs: {}, preferences }));
}

function travelling() {
  const store = freshStore();
  store.setSender(fx.createFakeSender());
  store.beginTransport(1);
  store.setConnected(true);
  store.receive(store.view.generation, "ui_snapshot", [fx.snapshot({ panels: walkPanels(CX, CY) })], {});
  store.setTravelMap({ status: "ready", area: walkArea(CX, CY) });
  return store;
}

describe("travel preferences", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => {
    window.localStorage.clear();
    vi.useRealTimers();
  });

  it("defaults to the standard pace with the nightfall stop on", () => {
    expect(freshStore().view.travel.preferences).toEqual({ pace: "standard", stopAtNight: true });
  });

  it("persists the chosen pair and restores it on reload", () => {
    const store = freshStore();
    expect(store.setTravelPace("cautious")).toBe(true);
    expect(store.setTravelStopAtNight(false)).toBe(true);
    expect(store.view.travel.preferences).toEqual({ pace: "cautious", stopAtNight: false });
    const wrapper = stored();
    expect(wrapper.layout_version).toBe(3);
    expect(wrapper.preferences.travelPace).toBe("cautious");
    expect(wrapper.preferences.travelStopAtNight).toBe(false);

    expect(freshStore().view.travel.preferences).toEqual({ pace: "cautious", stopAtNight: false });
  });

  it("keeps the other presentation preferences when saving the travel pair", () => {
    const store = freshStore();
    store.setTextSpeed("fast");
    store.setTravelPace("forced");
    const reloaded = freshStore();
    expect(reloaded.view.textSpeed).toBe("fast");
    expect(reloaded.view.travel.preferences.pace).toBe("forced");
  });

  it("loads the defaults for missing or malformed stored values", () => {
    seed({ textSpeed: "slow" });
    expect(freshStore().view.travel.preferences).toEqual({ pace: "standard", stopAtNight: true });
    seed({ travelPace: "sprint", travelStopAtNight: "yes" });
    expect(freshStore().view.travel.preferences).toEqual({ pace: "standard", stopAtNight: true });
    // One valid key survives beside one malformed key.
    seed({ travelPace: "forced", travelStopAtNight: 0 });
    expect(freshStore().view.travel.preferences).toEqual({ pace: "forced", stopAtNight: true });
  });

  it("refuses invalid values without writing", () => {
    const store = freshStore();
    for (const value of ["sprint", "", null, undefined, 1]) {
      expect(store.setTravelPace(value)).toBe(false);
    }
    for (const value of ["true", 1, null, undefined]) {
      expect(store.setTravelStopAtNight(value)).toBe(false);
    }
    expect(window.localStorage.getItem(KEY)).toBeNull();
    expect(store.view.travel.preferences).toEqual({ pace: "standard", stopAtNight: true });
  });

  it("freezes both preferences while a walk or its arming hold is active", () => {
    vi.useFakeTimers();
    const store = travelling();
    store.setTravelPace("cautious");
    // The hold that arms a walk already freezes the pair.
    store.holdTravel("east");
    expect(store.view.travel.holding).toBe(true);
    expect(store.setTravelPace("forced")).toBe(false);
    expect(store.setTravelStopAtNight(false)).toBe(false);
    // The 400 ms hold starts the walk; still frozen.
    vi.advanceTimersByTime(400);
    expect(store.view.travel.walking).not.toBeNull();
    expect(store.setTravelPace("forced")).toBe(false);
    expect(store.setTravelStopAtNight(false)).toBe(false);
    expect(store.view.travel.preferences).toEqual({ pace: "cautious", stopAtNight: true });
    expect(stored().preferences.travelPace).toBe("cautious");
    // Stopped: changes apply again.
    store.stopTravel("stop");
    expect(store.view.travel.walking).toBeNull();
    expect(store.setTravelPace("forced")).toBe(true);
    expect(store.setTravelStopAtNight(false)).toBe(true);
    expect(store.view.travel.preferences).toEqual({ pace: "forced", stopAtNight: false });
  });
});
