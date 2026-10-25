// The dialogue choice list's wiring (webclient-dialogue-choices-overlay
// D3/D4/D7/D8): when the list is shown, where its exit rows come from, and
// where focus goes around it. The list itself (DialogueChoices.vue) is
// passive; every dispatch goes through the store's single entry.
//
// Authored scenes (authored-dialogue-playback): the shared manual player
// (`use-authored-scene.js`) is instantiated here, over the committed panel's
// delivery, because it gates the list. While a scene plays the list waits
// for its explicit finish (never the window's last-page state), and the
// stage speaker follows each line's explicit attribution; native lines
// (the opening greeting, a freeform reply) keep the window's reader state
// and the dispatch-state speaker.
import { computed, nextTick, ref, watch } from "vue";
import { useAuthoredScene } from "./use-authored-scene.js";

export function useDialogueChoices(store, shellRef, dialogueVM) {
  // The window's reader state (design D3), reported by `reading-change`.
  // True until the window says otherwise: a reconnect inside a native
  // conversation line shows the last page complete, so the choices show at
  // once (an authored scene replays from line one instead, below).
  const readingComplete = ref(true);
  function onReadingChange(complete) {
    readingComplete.value = !!complete;
  }

  // The shared scene player over the committed delivery. The transport
  // generation is part of its key, so a reconnect replays the same delivery
  // from line one without selecting again.
  const sceneSource = computed(() => {
    const vm = dialogueVM.value;
    return {
      playable: store.view.mode === "dialogue" && !!vm,
      generation: store.view.generation,
      contextId: vm?.contextId ?? null,
      delivery: vm?.delivery ?? null,
      actorName: vm?.actor?.displayName ?? "",
      hostName: vm?.host?.displayName ?? "",
      bondStage: vm?.bondStage ?? null,
    };
  });
  const scene = useAuthoredScene(sceneSource);
  const scenePresentation = scene.presentation;
  function onSceneAdvance() {
    scene.advance();
  }

  // A scripted topic pick awaiting its reply holds the window, so its
  // transcript never types before the scene delivery commits; so does a
  // freeform line sent over a scene, so its reply is read as new text when
  // the reply's commit retires the scene. The dispatch lock releases in the
  // same commit that carries the reply's panel.
  const sceneHold = computed(() => {
    if (store.view.mode !== "dialogue") {
      return false;
    }
    const actionId = store.view.dispatch.inFlightActionId;
    return actionId === "explore.talk_scripted" || (actionId === "explore.talk_freeform" && scene.active.value);
  });

  // The stage speaker: "actor" | "host" | null (narration), or null outside
  // an available conversation. A native freeform line in flight lights the
  // actor (dispatch state); an authored scene follows its current line's
  // explicit attribution (including while a later pick awaits its reply);
  // a native line is the host's.
  const dialogueStageSpeaker = computed(() => {
    if (store.view.mode !== "dialogue" || !dialogueVM.value) {
      return null;
    }
    if (store.view.dialogueSpeaker === "player") {
      return "actor";
    }
    if (scene.active.value) {
      return scene.speaker.value;
    }
    return "host";
  });

  // Design D4: the list shows only in dialogue with the panel available,
  // once the line is fully read — an authored scene once its final page
  // received the explicit finish activation — and never while an action is
  // in flight (a pick or free speech awaiting its reply).
  const choicesShown = computed(
    () =>
      store.view.mode === "dialogue" &&
      !!dialogueVM.value &&
      (scene.active.value ? scene.readingComplete.value : readingComplete.value) &&
      store.view.dispatch.inFlight == null,
  );

  // A scene that starts while focus fell to the document (a reconnect's
  // replay) gives the page surface focus, so Space/Enter read it at once.
  // Focus anywhere else is never moved.
  watch(
    scene.key,
    async (key, previous) => {
      if (key === null || key === previous || !scene.active.value) {
        return;
      }
      await nextTick();
      const active = document.activeElement;
      if (!active || active === document.body || active === document.documentElement || !active.isConnected) {
        shellRef.value?.focusMessagePage?.();
      }
    },
    { flush: "post" },
  );

  // The committed exit rows (exploration-exit-compass design D9): the
  // `moveItems` rows the exit compass also reads, sourced independently of
  // the router's root frame (which carries no exit item).
  const dialogueExits = computed(() => store.view.explorationExits || []);

  // `↦ 移動…` then an exit row: the same payload and echo descriptor the
  // exit compass submits (design D8).
  function onDialogueMove(item) {
    if (!item || !item.actionId) {
      return;
    }
    store.dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
  }

  // Design D7: park focus on the message page before an activation, so the
  // list's removal on the next render never drops it.
  function beforeChoiceActivate() {
    shellRef.value?.focusMessagePage?.();
  }

  // Design D7: when the list appears while focus sits on the message window
  // (its page, anywhere in the message region) or on the body, the list
  // takes it, first row active. Focus elsewhere (a drawer, an overlay, the
  // command field) is never stolen.
  watch(
    choicesShown,
    async (shown) => {
      if (!shown) {
        return;
      }
      await nextTick();
      const list = document.querySelector('[data-anchor="choices"] [data-testid="dialogue-choices"]');
      const active = document.activeElement;
      const onWindow =
        !active ||
        active === document.body ||
        active === document.documentElement ||
        !active.isConnected ||
        !!active.closest?.('[data-anchor="band-message"]');
      if (list && onWindow) {
        list.focus({ preventScroll: true });
      }
    },
    { flush: "post" },
  );

  return {
    readingComplete,
    onReadingChange,
    scene,
    scenePresentation,
    sceneHold,
    onSceneAdvance,
    onSceneFinished: scene.onSceneFinished,
    dialogueStageSpeaker,
    choicesShown,
    dialogueExits,
    onDialogueMove,
    beforeChoiceActivate,
  };
}
