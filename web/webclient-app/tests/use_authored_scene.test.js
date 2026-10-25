// authored-dialogue-playback: the shared manual scene player's line cursor
// (`use-authored-scene.js`). Pure state over a committed source: no store,
// no timers. One player serves static and generated deliveries alike
// (including canonical generated IDs far longer than a static ID).
import { describe, expect, it } from "vitest";
import { nextTick, ref } from "vue";
import {
  authoredSceneKey,
  isAuthoredDelivery,
  lineSpeaker,
  useAuthoredScene,
} from "../composables/use-authored-scene.js";
import { narration, nativeDelivery, sceneDelivery, speech } from "./support/dialogue_panel.js";

const LINES = [
  speech("actor", "最近有什麼消息？"),
  speech("host", "北岸大道最近不太平。"),
  speech("host", "夜裡別走那條路。"),
  narration("店長壓低了聲音。"),
];

// A canonical generated identity: "g:" + unpadded URL-safe base64, opaque.
const GENERATED_TOPIC = "g:" + "WyJwa2dfYWIxMiIsIm1vdGhlciIsInBoYXNlXzEiLCJ0b3BpY19hIl0".repeat(30);

function setup(overrides = {}) {
  const source = ref({
    playable: true,
    generation: 1,
    contextId: "ctx-1",
    delivery: sceneDelivery(LINES),
    actorName: "旅人",
    hostName: "店長",
    bondStage: "熟識",
    ...overrides,
  });
  const scene = useAuthoredScene(source);
  const finished = [];
  scene.onSceneFinished((detail) => finished.push(detail));
  return { source, scene, finished };
}

const attribution = (scene) => ({
  index: scene.lineIndex.value,
  speaker: scene.speaker.value,
  name: scene.speakerName.value,
  bond: scene.presentation.value?.bondStage ?? null,
  text: scene.presentation.value?.text ?? null,
});

describe("useAuthoredScene", () => {
  it("presents formal and refusal scenes, never native opening/service lines", () => {
    expect(isAuthoredDelivery(sceneDelivery(LINES))).toBe(true);
    expect(isAuthoredDelivery(sceneDelivery(LINES, { kind: "refusal" }))).toBe(true);
    expect(isAuthoredDelivery(nativeDelivery("歡迎。"))).toBe(false);
    expect(isAuthoredDelivery(sceneDelivery(LINES, { kind: "service" }))).toBe(false);
    expect(isAuthoredDelivery(null)).toBe(false);
    expect(lineSpeaker(narration("風聲。"))).toBe(null);
    expect(lineSpeaker(speech("actor", "嗯。"))).toBe("actor");
  });

  it("walks lines one reading step at a time, with explicit attribution", () => {
    const { scene } = setup();
    const steps = [attribution(scene)];
    while (scene.lineIndex.value < scene.lineCount.value - 1) {
      expect(scene.advance()).toBe(true);
      steps.push(attribution(scene));
    }
    expect(steps).toEqual([
      { index: 0, speaker: "actor", name: "旅人", bond: null, text: "最近有什麼消息？" },
      { index: 1, speaker: "host", name: "店長", bond: "熟識", text: "北岸大道最近不太平。" },
      { index: 2, speaker: "host", name: "店長", bond: "熟識", text: "夜裡別走那條路。" },
      { index: 3, speaker: null, name: null, bond: null, text: "店長壓低了聲音。" },
    ]);
    expect(scene.presentation.value.last).toBe(true);
    expect(scene.readingComplete.value).toBe(false);
  });

  it("finishes only on the final line's further activation, emitting one event", () => {
    const { scene, finished } = setup({ delivery: sceneDelivery(LINES.slice(0, 2)) });
    scene.advance();
    expect(scene.readingComplete.value).toBe(false);
    expect(finished).toHaveLength(0);
    expect(scene.advance()).toBe(true);
    expect(scene.readingComplete.value).toBe(true);
    expect(scene.presentation.value.finished).toBe(true);
    // A double activation in the same tick finishes nothing twice.
    expect(scene.advance()).toBe(false);
    expect(finished).toEqual([
      {
        delivery_id: "dlv-1",
        context_id: "ctx-1",
        topic_id: "host.fare",
        scene_id: "host.fare_scene",
        scene_revision: "r1",
        kind: "formal",
      },
    ]);
  });

  it("starts a new delivery at line one and keeps the line on a same-delivery refresh", () => {
    const { source, scene } = setup();
    scene.advance();
    scene.advance();
    // Availability-only refresh: a new panel object, the same delivery.
    source.value = { ...source.value, delivery: sceneDelivery(LINES), bondStage: "親睦" };
    expect(scene.lineIndex.value).toBe(2);
    expect(scene.presentation.value.bondStage).toBe("親睦");
    // A new delivery_id restarts.
    source.value = { ...source.value, delivery: sceneDelivery(LINES, { deliveryId: "dlv-2" }) };
    expect(scene.lineIndex.value).toBe(0);
    expect(scene.readingComplete.value).toBe(false);
  });

  it("replays the same delivery from line one in a new transport generation", () => {
    const { source, scene, finished } = setup();
    scene.advance();
    scene.advance();
    source.value = { ...source.value, playable: false };
    source.value = { ...source.value, playable: true, generation: 2 };
    expect(scene.active.value).toBe(true);
    expect(scene.lineIndex.value).toBe(0);
    expect(finished).toHaveLength(0);
  });

  it("retires without a finished event on invalidation, and a retired delivery stays retired", async () => {
    const { source, scene, finished } = setup();
    scene.advance();
    // Combat (or an unavailable panel): not playable.
    source.value = { ...source.value, playable: false };
    expect(scene.active.value).toBe(false);
    expect(scene.presentation.value).toBe(null);
    // The same delivery returns in the same generation: still retired.
    source.value = { ...source.value, playable: true };
    await nextTick();
    expect(scene.active.value).toBe(false);
    expect(finished).toHaveLength(0);
  });

  it("retires when the phase changes under the same delivery, and on an explicit retire()", () => {
    const { source, scene, finished } = setup({ delivery: sceneDelivery(LINES) });
    source.value = { ...source.value, delivery: { ...sceneDelivery(LINES), phase_revision: "p2" } };
    expect(scene.active.value).toBe(false);
    const second = setup();
    second.scene.retire();
    expect(second.scene.active.value).toBe(false);
    expect(second.scene.advance()).toBe(false);
    expect(finished).toHaveLength(0);
    expect(second.finished).toHaveLength(0);
  });

  it("keys opaque generated identities without truncation", () => {
    const delivery = sceneDelivery(LINES, { topicId: GENERATED_TOPIC, sceneId: `${GENERATED_TOPIC}s` });
    expect(GENERATED_TOPIC.length).toBeGreaterThan(1500);
    const { scene, finished } = setup({ delivery });
    while (scene.advance());
    expect(finished[0].topic_id).toBe(GENERATED_TOPIC);
    expect(authoredSceneKey({ playable: true, generation: 1, contextId: "c", delivery })).toBe("1|c|dlv-1");
  });
});
