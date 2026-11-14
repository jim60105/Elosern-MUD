// The landmark rite stage's shell binding (OpenSpec change landmark-rite-stage
// design D2; landmark rites design §12.2). The rite store group
// (`stores/elosern/rite.js`) owns the local phase and the one request; this
// composable only projects `view.rite` into what the shell mounts:
//
// - the arrival card (`cardOpen`), which waits while the dream or a
//   sleep-handoff card owns the choices anchor (`blocked`);
// - the stage (`onStage`): local presentation over the committed exploration
//   mode, with the guardian's form as the message window's line under the
//   guardian's name plate, and the rite panel while nothing is pending or
//   playing (`panelShown`);
// - the delivery's playback through the shared authored-scene player, whose
//   single finish returns the panel;
// - the return entry under the place card (`entryShown`).
//
// It sends nothing itself: `perform` is the store's one
// `explore.landmark_rite`, always for the controlled character here.
import { computed, onScopeDispose, watch } from "vue";
import { ritePerformers } from "../components/rite/rite-model.js";
import { useAuthoredScene } from "./use-authored-scene.js";

export function useRiteStage({ store, blocked }) {
  const view = computed(() => store.view?.rite ?? null);
  const rite = computed(() => view.value?.panel ?? null);
  const phase = computed(() => view.value?.phase ?? "closed");
  const playing = computed(() => view.value?.playing === true);
  const pending = computed(() => view.value?.pending === true);

  const cardOpen = computed(() => !!rite.value && phase.value === "card" && !blocked.value);
  const onStage = computed(() => !!rite.value && phase.value === "stage");
  const panelShown = computed(() => onStage.value && !playing.value && !pending.value);
  const entryShown = computed(
    () => !!rite.value && phase.value === "closed" && store.view?.mode === "exploration",
  );
  const performer = computed(() => (rite.value ? ritePerformers(rite.value)[0] ?? null : null));
  const lines = computed(() =>
    rite.value ? [{ kind: "out", text: rite.value.guardian.form, seq: 1 }] : [],
  );
  const dialogueModel = computed(() => ({
    host: { displayName: rite.value?.guardian?.name ?? "" },
    bondStage: null,
  }));

  const source = computed(() => {
    const delivery = view.value?.delivery ?? null;
    return {
      playable: onStage.value && playing.value,
      generation: store.view?.generation ?? null,
      contextId: rite.value ? `rite:${rite.value.district.key}` : null,
      // A rite delivery has no phase: nothing under it can retire it.
      delivery: delivery ? { ...delivery, phase_revision: null } : null,
      npcId: null,
      actorName: delivery?.actor_name ?? "",
      hostName: delivery?.guardian_name ?? "",
      bondStage: null,
    };
  });
  const scene = useAuthoredScene(source);
  const stopFinished = scene.onSceneFinished(() => store.finishRiteScene());
  onScopeDispose(stopFinished);

  // A delivery the shared player does not present (no lines, an unknown
  // kind, or a key already retired in this session) would never finish and
  // would hold the stage without its panel and without a way out: it plays
  // nothing and returns the panel at once.
  watch(
    () => onStage.value && playing.value && !scene.active.value,
    (stranded) => {
      if (stranded) store.finishRiteScene();
    },
    { immediate: true },
  );

  const sceneHold = computed(() => pending.value);

  function approach() {
    return store.approachRite() === true;
  }
  function leave() {
    return store.leaveRite() === true;
  }
  function openEntry() {
    return store.openRiteCard() === true;
  }
  function perform(key) {
    return store.performRite(key, null) === true;
  }
  function advance() {
    return scene.advance();
  }

  return {
    rite,
    cardOpen,
    onStage,
    panelShown,
    entryShown,
    performer,
    lines,
    dialogueModel,
    scene,
    sceneHold,
    approach,
    leave,
    perform,
    openEntry,
    advance,
  };
}

export default { useRiteStage };
