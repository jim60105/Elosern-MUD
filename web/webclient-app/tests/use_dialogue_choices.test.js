// authored-dialogue-locked-ui: the choice wiring keeps refusal completion
// local. A refusal (the scene a visibly locked topic plays) and a formal
// scene share one player and both return the choices on their explicit
// finish, but only a delivered `formal` kind reaches the formal-completion
// hook the reading client wires to persistence.
import { describe, expect, it } from "vitest";
import { computed, effectScope, reactive, ref } from "vue";
import { useDialogueChoices } from "../composables/use-dialogue-choices.js";
import { dialogueViewModel } from "../stores/dialogue-view.js";
import { dialoguePanel, sceneDelivery, speech } from "./support/dialogue_panel.js";

function harness() {
  const store = {
    view: reactive({
      mode: "dialogue",
      generation: 1,
      dispatch: { inFlight: null, inFlightActionId: null },
      dialogueSpeaker: null,
      explorationExits: [],
    }),
  };
  const panel = ref(null);
  const scope = effectScope();
  const choices = scope.run(() =>
    useDialogueChoices(store, ref(null), computed(() => dialogueViewModel(panel.value))),
  );
  return { store, panel, scope, choices };
}

function play(choices) {
  // Every line's last page was read; each advance moves one line, and the
  // final one finishes the scene.
  for (let index = 0; index < 4 && !choices.scene.readingComplete.value; index += 1) {
    choices.onSceneAdvance();
  }
}

const LINES = [speech("actor", "可以說嗎？"), speech("host", "還不行。")];

describe("useDialogueChoices formal completion", () => {
  it("a refusal finish returns the choices without a formal completion", () => {
    const { panel, scope, choices } = harness();
    const formal = [];
    const all = [];
    choices.onFormalSceneFinished((detail) => formal.push(detail));
    choices.onSceneFinished((detail) => all.push(detail));
    panel.value = dialoguePanel({
      delivery: sceneDelivery(LINES, { kind: "refusal", topicId: "host.gate", deliveryId: "dlv-refusal" }),
    });
    expect(choices.choicesShown.value).toBe(false);
    play(choices);
    expect(choices.choicesShown.value).toBe(true);
    expect(all.map((detail) => detail.kind)).toEqual(["refusal"]);
    expect(formal).toEqual([]);
    scope.stop();
  });

  it("a formal finish reaches the hook once, and the unsubscribe stops it", () => {
    const { panel, scope, choices } = harness();
    const formal = [];
    const stop = choices.onFormalSceneFinished((detail) => formal.push(detail));
    panel.value = dialoguePanel({ delivery: sceneDelivery(LINES, { kind: "formal", topicId: "host.fare" }) });
    play(choices);
    choices.onSceneAdvance();
    expect(formal).toHaveLength(1);
    expect(formal[0]).toMatchObject({ kind: "formal", topic_id: "host.fare", delivery_id: "dlv-1" });
    stop();
    panel.value = dialoguePanel({ delivery: sceneDelivery(LINES, { kind: "formal", topicId: "host.fare", deliveryId: "dlv-2" }) });
    play(choices);
    expect(choices.choicesShown.value).toBe(true);
    expect(formal).toHaveLength(1);
    scope.stop();
  });
});
