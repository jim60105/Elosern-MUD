// Shared harness for the travel suites (wilderness-travel-interface): the real
// composed store behind a fake sender, synthetic committed panels and the
// mounted AppClient. Every body passes the real wire validators.

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../../AppClient.vue";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";
import { ART_PANEL_SAMPLE, sceneBlock, sceneDescriptor } from "../../stories/fixtures/art_panels.js";
import { LOCAL_MAP_WILDERNESS_METRIC_SAMPLE } from "../../stories/fixtures.js";
import { wildernessArea } from "../../stories/fixtures/area_map.js";

export { fx, wildernessArea };

export const WILD_SUBJECT = "wilderness:合成荒原:100,200";
export const TOWN_SUBJECT = "grid:t_synth_map:2,0";

/** A committed `art` panel whose scene names `subject`. */
export function artFor(subject) {
  return { ...ART_PANEL_SAMPLE, scene: sceneBlock({}, sceneDescriptor({ subject_id: subject })) };
}

export const tick = async () => {
  await nextTick();
  await nextTick();
};

/** The eager panels of one exploration publication at `subject`. */
export function panelsAt(subject, extra = {}) {
  return {
    status: fx.statusPanel(),
    context_actions: fx.explorationActions(),
    exploration: fx.explorationPanel(),
    local_map: LOCAL_MAP_WILDERNESS_METRIC_SAMPLE,
    art: artFor(subject),
    ...extra,
  };
}

/**
 * The live harness: a store established at `subject` and, unless `mounted`
 * is false, the AppClient attached to the document.
 */
export function liveTravel({ subject = WILD_SUBJECT, panels = null, mounted = true, wrappers = [] } = {}) {
  setActivePinia(createPinia());
  const store = useElosernStore();
  const sender = fx.createFakeSender();
  store.setSender(sender);
  store.beginTransport(1);
  store.setConnected(true);
  const accept = (name, body) => {
    const outcome = store.receive(store.view.generation, name, [body], {});
    if (!outcome.accepted) throw new Error(`${name} rejected: ${JSON.stringify(outcome)}`);
    return outcome;
  };
  accept("ui_snapshot", fx.snapshot({ panels: panels ?? panelsAt(subject) }));
  let w = null;
  if (mounted) {
    w = mount(AppClient, { attachTo: document.body });
    wrappers.push(w);
  }
  const mapViews = () => sender.sent.actions.filter((a) => a.action_id === "map.view");
  /** The next consecutive revision. */
  const next = () => store.view.revision + 1;
  /** An update of `panels` at the next revision. */
  const publish = (bodyPanels, overrides = {}) => {
    const revision = next();
    accept("ui_update", fx.update({ revision, panels: bodyPanels, ...overrides }));
    return revision;
  };
  /** The result of `request` declaring `revision`. */
  const result = (request, revision, outcome = "success", code = "completed") =>
    accept("ui_action_result", fx.actionResult({
      request_id: request.request_id, presentation_revision: revision, outcome, code,
      ...(outcome === "success" ? {} : { message: "無法讀取地圖" }),
    }));
  /** Answer the last map.view with `area` in the given order. */
  const answerMap = async (area, order = "body-first") => {
    const request = mapViews().at(-1);
    const revision = next();
    if (order === "result-first") {
      result(request, revision);
      await tick();
    }
    accept("ui_update", fx.update({ revision, panels: { area_map: area } }));
    await tick();
    if (order === "body-first") {
      result(request, revision);
      await tick();
    }
    return revision;
  };
  return { store, sender, w, accept, publish, result, answerMap, mapViews, next };
}
