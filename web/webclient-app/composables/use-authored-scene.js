// The shared manual authored-scene player (authored-dialogue-playback; Shared
// contract v2 "Delivery, replay and wire"). One player renders every complete
// static or generated scene delivery: the source never selects a renderer.
//
// Event ownership:
// - MessageWindow owns PAGES: pagination, the typewriter, and the reader's
//   activations (a click on the message surface, or an unmodified,
//   non-repeated Space/Enter on the focused page surface). While a page
//   types an activation completes it; on a fully shown page with a further
//   page it turns the page. Only an activation on the LAST fully shown page
//   of the current line leaves the window, as its `scene-advance` event.
// - This composable owns LINES: `advance()` (bound to `scene-advance`) moves
//   to the next line, or — on the final line — finishes the scene and emits
//   the single `scene-finished` event. Nothing here arms a timer: an
//   authored scene never auto-advances a page, a line, or its finish,
//   whatever the stored auto-advance preference says.
// - The shell owns choices and focus (`use-dialogue-choices.js`): the
//   choice list stays hidden until `readingComplete` (the explicit finish).
//
// Presentation only: this module imports no store, dispatches nothing,
// settles no effect and never touches the server clock. The cursor lives in
// memory and is DERIVED from the playback key, so a new key renders line one
// in the same tick that commits it (text, plate and stage emphasis change
// together) with no watcher reset to race the render:
// - a new delivery_id, a changed context/phase, or a new transport
//   generation (a reconnect, even of the same delivery) starts at line one;
// - an availability-only refresh of the same delivery keeps the local line
//   and the window keeps its page (the window's display key is unchanged);
// - a key that disappears (mode change, unavailable panel, a native
//   delivery) or a phase revision that changes under the same delivery
//   retires the player without a finished event; a retired key stays
//   retired if the same delivery is committed again in that generation (a
//   reconnect is a new generation, so it replays from line one).
import { computed, shallowRef, watch } from "vue";

// Deliveries the player presents. Opening/service lines (and freeform
// replies, which the presenter ships as one native host line) keep the
// window's native response presentation.
export const AUTHORED_SCENE_KINDS = Object.freeze(["formal", "refusal"]);

export function isAuthoredDelivery(delivery) {
  return (
    !!delivery &&
    AUTHORED_SCENE_KINDS.includes(delivery.kind) &&
    Array.isArray(delivery.lines) &&
    delivery.lines.length > 0
  );
}

// The playback identity: generation | context | delivery. Delivery and
// generated topic/scene IDs are opaque; they are joined, never parsed. The
// phase revision is not part of the key: a phase change under the same
// delivery retires the player (see `useAuthoredScene`), it never replays.
export function authoredSceneKey({ playable, generation, contextId, delivery }) {
  if (!playable || !isAuthoredDelivery(delivery)) {
    return null;
  }
  return `${generation ?? ""}|${contextId ?? ""}|${delivery.delivery_id}`;
}

// A line's explicit attribution: "actor" or "host" for speech, null for
// narration (no plate, neither participant emphasized).
export function lineSpeaker(line) {
  if (!line || line.kind !== "speech") {
    return null;
  }
  return line.speaker === "actor" || line.speaker === "host" ? line.speaker : null;
}

/**
 * @param {import("vue").Ref<{playable: boolean, generation: *, contextId: *,
 *   delivery: object|null, npcId: number|null, actorName: string, hostName: string,
 *   bondStage: string|null}>} source — a computed over committed state.
 */
export function useAuthoredScene(source) {
  const key = computed(() => authoredSceneKey(source.value || {}));
  // {key, lineIndex, finished, retired}; meaningful only while its key is
  // the current one.
  const cursor = shallowRef({ key: null, lineIndex: 0, finished: false, retired: false });
  // Keys retired in this session, and the phase revision each key started
  // with (both bounded by the deliveries one tab sees).
  const retiredKeys = shallowRef(new Set());
  const startPhase = new Map();
  const state = computed(() => {
    const current = key.value;
    const held = cursor.value;
    if (current === null) {
      return null;
    }
    if (retiredKeys.value.has(current)) {
      return { key: current, lineIndex: 0, finished: false, retired: true };
    }
    return held.key === current ? held : { key: current, lineIndex: 0, finished: false, retired: false };
  });
  function retireKey(retiring) {
    if (retiring === null || retiredKeys.value.has(retiring)) {
      return;
    }
    const next = new Set(retiredKeys.value);
    next.add(retiring);
    retiredKeys.value = next;
  }
  // Committed invalidation (sync, so no render sees a stale line): a key
  // that goes away retires; a phase change under a live key retires it.
  watch(
    () => [key.value, source.value?.delivery?.phase_revision ?? null],
    ([current, phase], previous) => {
      const [before] = previous || [null];
      if (before !== null && before !== current) {
        retireKey(before);
      }
      if (current === null) {
        return;
      }
      if (!startPhase.has(current)) {
        startPhase.set(current, phase);
      } else if (startPhase.get(current) !== phase) {
        retireKey(current);
      }
    },
    { flush: "sync", immediate: true },
  );
  const active = computed(() => !!state.value && !state.value.retired);
  const delivery = computed(() => (active.value ? source.value.delivery : null));
  const lines = computed(() => (delivery.value ? delivery.value.lines : []));
  const lineCount = computed(() => lines.value.length);
  const lineIndex = computed(() => (active.value ? Math.min(state.value.lineIndex, lineCount.value - 1) : 0));
  const line = computed(() => (active.value ? lines.value[lineIndex.value] : null));
  const speaker = computed(() => lineSpeaker(line.value));
  const speakerName = computed(() => {
    if (speaker.value === "actor") return source.value.actorName || null;
    if (speaker.value === "host") return source.value.hostName || null;
    return null;
  });
  const readingComplete = computed(() => active.value && state.value.finished);

  // The window's input: everything one line's presentation needs, so the
  // text, the plate and the marker change together.
  const presentation = computed(() => {
    if (!active.value || !line.value) {
      return null;
    }
    return {
      key: key.value,
      lineIndex: lineIndex.value,
      lineCount: lineCount.value,
      kind: line.value.kind === "speech" ? "speech" : "narration",
      text: String(line.value.text ?? ""),
      speaker: speaker.value,
      speakerName: speakerName.value,
      // The bond suffix belongs to host speech only.
      bondStage: speaker.value === "host" ? source.value.bondStage ?? null : null,
      last: lineIndex.value === lineCount.value - 1,
      finished: state.value.finished,
    };
  });

  const finishedHandlers = new Set();
  function onSceneFinished(handler) {
    finishedHandlers.add(handler);
    return () => finishedHandlers.delete(handler);
  }

  // The window reports an activation on the current line's last fully
  // shown page. Returns true when it moved the scene.
  function advance() {
    const held = state.value;
    if (!active.value || held.finished) {
      return false;
    }
    if (lineIndex.value < lineCount.value - 1) {
      cursor.value = { key: held.key, lineIndex: lineIndex.value + 1, finished: false, retired: false };
      return true;
    }
    cursor.value = { key: held.key, lineIndex: lineIndex.value, finished: true, retired: false };
    const shown = delivery.value;
    // The single finish event: locally usable now; the reading-client
    // slice wires it to persistence.
    const detail = {
      // The host identity follows the committed conversation so the reading
      // client can compose the exact five-field acknowledgement payload
      // without re-deriving it (authored-dialogue-reading-client).
      npc_id: source.value?.npcId ?? null,
      delivery_id: shown.delivery_id,
      context_id: shown.context_id,
      topic_id: shown.topic_id,
      scene_id: shown.scene_id,
      scene_revision: shown.scene_revision,
      kind: shown.kind,
    };
    for (const handler of [...finishedHandlers]) {
      try {
        handler(detail);
      } catch (error) {
        // One failing listener never starves the others or the reader's
        // key handler; the error still surfaces, outside this activation.
        queueMicrotask(() => {
          throw error;
        });
      }
    }
    return true;
  }

  // Stop presenting the current delivery without a finished event (an
  // explicit invalidation; committed key changes retire implicitly).
  function retire() {
    if (state.value) {
      retireKey(state.value.key);
    }
  }

  return {
    key,
    active,
    lineIndex,
    lineCount,
    line,
    speaker,
    speakerName,
    readingComplete,
    presentation,
    advance,
    retire,
    onSceneFinished,
  };
}

export default { useAuthoredScene, isAuthoredDelivery, authoredSceneKey, lineSpeaker, AUTHORED_SCENE_KINDS };
