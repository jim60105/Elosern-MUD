// Creation portrait publications and the store's creation navigation
// (creation-draft-portrait-panel). The navigation signature is preset keys,
// race keys and draft only: a freshly decoded panel whose portrait changed but
// whose draft contents are equal must not re-run the dock rebuild (which would
// reopen a dismissed confirmation or reset the creation frame), while a real
// draft change still does.

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import {
  CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
  CREATION_PANEL_PRESET_DRAFT_SAMPLE,
  CREATION_PANEL_SAMPLE,
  CREATION_PORTRAIT_STATES,
} from "../../stories/fixtures.js";
import * as fx from "./protocol_fixtures.js";

const PORTRAIT_ONLY_STATES = ["pending", "ready", "failed", "unavailable", "empty"];

// A wire-valid saved custom draft on the sample's subraced race (the wire
// requires a concrete subrace key and the race's affinity bound).
const SUBRACED = CREATION_PANEL_SAMPLE.custom.races.find((race) => (race.subraces ?? []).length > 0);
const CUSTOM_DRAFT_PANEL = {
  ...CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
  draft: {
    ...CREATION_PANEL_CUSTOM_DRAFT_SAMPLE.draft,
    race: SUBRACED.key,
    subrace: SUBRACED.subraces[0],
    affinity_elements: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE.draft.affinity_elements.slice(0, 1),
  },
};

describe("creation portrait publications keep the store navigation", () => {
  let store;
  let revision;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    store.setSender(fx.createFakeSender());
    revision = 1;
  });

  afterEach(() => {
    store.$dispose();
  });

  function open(panel) {
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    const result = store.receive(
      1,
      "ui_snapshot",
      [fx.snapshot({ mode: "creation", revision, panels: { creation: structuredClone(panel) } })],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  function publish(panel) {
    revision += 1;
    const result = store.receive(
      1,
      "ui_update",
      [fx.update({ mode: "creation", revision, panels: { creation: structuredClone(panel) } })],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  it("a dismissed preset confirmation stays dismissed across portrait-only updates", () => {
    open(CREATION_PANEL_PRESET_DRAFT_SAMPLE);
    expect(store.view.creationView.stage).toBe("confirm");
    store.focusEscape();
    expect(store.view.creationView.stage).toBe("presets");

    for (const state of PORTRAIT_ONLY_STATES) {
      publish({ ...CREATION_PANEL_PRESET_DRAFT_SAMPLE, portrait: CREATION_PORTRAIT_STATES[state] });
      expect(store.view.panels.creation.portrait.status).toBe(state);
      expect(store.view.creationView.stage).toBe("presets");
    }

    // Control: a genuinely changed draft reruns the rebuild and reopens it.
    const otherKey = CREATION_PANEL_SAMPLE.presets.find(
      (card) => card.key !== CREATION_PANEL_PRESET_DRAFT_SAMPLE.draft.preset_key,
    ).key;
    publish({
      ...CREATION_PANEL_PRESET_DRAFT_SAMPLE,
      draft: { ...CREATION_PANEL_PRESET_DRAFT_SAMPLE.draft, preset_key: otherKey },
    });
    expect(store.view.creationView.stage).toBe("confirm");
  });

  it("a custom draft's restored root survives portrait-only updates", () => {
    open(CUSTOM_DRAFT_PANEL);
    expect(store.view.creationView.stage).toBe("custom");
    store.focusEscape();
    expect(store.view.creationView.stage).toBe("root");

    for (const state of PORTRAIT_ONLY_STATES) {
      publish({ ...CUSTOM_DRAFT_PANEL, portrait: CREATION_PORTRAIT_STATES[state] });
      expect(store.view.panels.creation.portrait.status).toBe(state);
      expect(store.view.creationView.stage).toBe("root");
    }

    publish({
      ...CUSTOM_DRAFT_PANEL,
      draft: { ...CUSTOM_DRAFT_PANEL.draft, display_name: "改過的名字" },
    });
    expect(store.view.creationView.stage).toBe("custom");
  });
});
