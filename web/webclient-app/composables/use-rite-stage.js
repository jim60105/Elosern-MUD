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
// After the scene of a district's first completion finishes, the message
// window names the newly lit district under the guardian's form
// (landmark-rite-discovery-notice D2) until the player leaves or performs
// again.
//
// It sends nothing itself: `perform` is the store's one
// `explore.landmark_rite`, for the performer the store holds.
//
// Performer picking (landmark-rite-performer-picking D2) reuses the party
// line-up's targeting input: while picking is offered the listed performers'
// figures are hit areas, the picked one lit and selected, a hovered one lit,
// the rest dimmed; during a request or a scene only the performer is lit.
import { computed, onScopeDispose, ref, watch } from "vue";
import { ritePerformers } from "../components/rite/rite-model.js";
import { useAuthoredScene } from "./use-authored-scene.js";

// The line-up identity of one performer row. The first row is the controlled
// body, whose figure is the line-up's controlled slot (a possessed companion
// in that row included); every other row is a party member, whose figure
// carries its member id (the owner's figure too, while a companion is
// possessed: the roster identity is the same database id).
export function riteFigureId(row, controlledId) {
  if (row.id !== "self") return row.id;
  return controlledId === null || controlledId === undefined ? null : String(controlledId);
}

// The stage's message window lines: the guardian's form, and, once a first
// completion's scene has finished, one line naming the newly lit district.
// The lit mark and the district name take the narrative emphasis (gold), the
// lit district's colour on the arrival card; the name is a text token, never
// parsed as markup.
export function riteStageLines(rite, newlyLit) {
  if (!rite) return [];
  const lines = [{ kind: "out", text: rite.guardian.form, seq: 1 }];
  if (newlyLit) {
    const name = rite.district.name;
    const tail = "的地圖亮了起來。";
    lines.push({
      kind: "out",
      text: `◆ ${name}${tail}`,
      seq: 2,
      tokens: [
        { kind: "open", tag: "span", classes: ["em"] },
        { kind: "text", value: `◆ ${name}` },
        { kind: "close" },
        { kind: "text", value: tail },
      ],
    });
  }
  return lines;
}

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
  const performers = computed(() => (rite.value ? ritePerformers(rite.value) : []));
  const performer = computed(
    () => performers.value.find((row) => row.id === view.value?.performerId) ?? performers.value[0] ?? null,
  );
  const canSwitch = computed(() => view.value?.canSwitch === true && panelShown.value);
  const lines = computed(() =>
    riteStageLines(rite.value, view.value?.newlyLit === true && !playing.value),
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
    return store.performRite(key) === true;
  }

  // The line-up identity under the pointer, or null. It never outlives the
  // pick it previews: activation, a keyboard step, the pointer leaving the
  // line-up and the panel going away all clear it.
  const hovered = ref(null);
  function clearHover() {
    hovered.value = null;
  }
  watch(canSwitch, (open) => {
    if (!open) clearHover();
  });

  /** The line-up's targeting input on the stage, or null. */
  function targeting({ controlledId }) {
    if (!onStage.value || !performer.value) return null;
    const own = riteFigureId(performer.value, controlledId);
    const lit = new Set(own === null ? [] : [own]);
    if (playing.value || pending.value) return { lit, selectable: new Set(), selected: new Set() };
    if (!canSwitch.value) return null;
    const selectable = new Set(
      performers.value.map((row) => riteFigureId(row, controlledId)).filter((id) => id !== null),
    );
    if (hovered.value !== null && selectable.has(hovered.value)) lit.add(hovered.value);
    return { lit, selectable, selected: new Set(own === null ? [] : [own]) };
  }

  /** A pointer on a line-up figure: hover previews, activation picks. */
  function onFigure(identity, action, { controlledId }) {
    if (!canSwitch.value || identity === null || identity === undefined) return false;
    const id = String(identity);
    const row = performers.value.find((candidate) => riteFigureId(candidate, controlledId) === id);
    if (!row) return false;
    if (action === "hover") {
      hovered.value = id;
      return true;
    }
    if (action !== "activate") return false;
    clearHover();
    return store.pickRitePerformer(row.id) === true;
  }

  /** Step the performer from the panel's arrows. */
  function step(delta) {
    clearHover();
    return store.stepRitePerformer(delta) === true;
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
    canSwitch,
    targeting,
    onFigure,
    clearHover,
    step,
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
