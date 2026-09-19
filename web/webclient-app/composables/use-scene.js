// The scene surface: the dialogue presentation (webclient-align-08 /
// align-11), the Tab-completion candidates, the possession banner and context
// affordances, the minimap move echo (complete-ui-command-echo D3), the
// pending epithet ballot, and the objective-tracker gate. Extracted verbatim
// from AppClient.vue so the SFC stays a passive renderer.
import { computed } from "vue";
import LocalMapLogic from "../lib/local_map.js";
import { dialogueViewModel } from "../stores/dialogue-view.js";

export function useScene(store, { panel, panelAvailable, dispatchIntent }) {
  // The dialogue surface source (webclient-align-08-dialogue-surface): the ONE
  // derived view model over the committed `dialogue` panel (webclient-align-11:
  // the feed dialogue variant is its ONLY presentation — the dock has no
  // dialogue form) — the client never keeps a second copy of the picks.
  const dialogueVM = computed(() =>
    store.view.mode === "dialogue" ? dialogueViewModel(panel("dialogue")) : null,
  );
  // Feed-variant activation shares the dock's dispatch contract (the store owns
  // the single dispatch entry and the freeform-borrow path).
  function onDialoguePick(pick) {
    store.dispatchAction(pick.actionId, pick.payload || {}, pick.commandDisplay || null);
  }
  function onDialogueFreeform() {
    store.borrowDialogueCommand();
  }
  // The caption's exit row (webclient-align-11-dialogue-ux): ends the live
  // session through the deterministic exit seam. The committed full snapshot
  // re-homes the mode; no client-side optimistic state.
  function onDialogueLeave() {
    const vm = dialogueVM.value;
    if (!vm) {
      return;
    }
    store.dispatchAction("explore.dialogue_leave", { npc_id: vm.host.identity }, null);
  }

  // Tab-completion candidates from the committed exploration panel only
  // (webclient-align-02-quickbar-shortcuts): exit move-row labels and
  // interact-target display names. An unavailable or absent panel contributes
  // nothing — the client never reads uncommitted state.
  const completionCandidates = computed(() => {
    const p = panelAvailable("exploration") ? panel("exploration") : null;
    if (!p) {
      return [];
    }
    const exits = Array.isArray(p.move) ? p.move.map((row) => row?.label).filter(Boolean) : [];
    const targets = Array.isArray(p.interact)
      ? p.interact.map((row) => row?.display_name).filter(Boolean)
      : [];
    return [...exits, ...targets];
  });

  const possessionBanner = computed(() => panel("possession_banner"));
  const contextAffordances = computed(() => panel("context_actions")?.affordances || []);
  const releaseAffordance = computed(() => contextAffordances.value.find((a) => a.action_id === "explore.possess_release") || null);

  const titleBallotPanel = computed(() => panel("title_ballot"));
  const titleBallotCandidates = computed(() => {
    const p = titleBallotPanel.value;
    return !!p && p.available === true && Array.isArray(p.candidates) ? p.candidates : [];
  });

  function onMapMove(moveData) {
    // The minimap node action carries `exit_ref` + `destination`; the
    // `explore.move` payload requires exactly `{ exit_ref, current_node }`,
    // where `current_node` is the actor's current node (the committed
    // `local_map.current_node`), not the destination. The echo label is the
    // uniquely matching traversable edge label (else the destination node's
    // committed label; else nothing — never an invented exit, D3).
    const model = store.view.localMapModel ?? null;
    const exitLabel = LocalMapLogic.exitLabelFor(
      model,
      model?.currentNode ?? null,
      moveData.destination ?? null
    );
    dispatchIntent(
      "explore.move",
      {
        exit_ref: moveData.exit_ref,
        current_node: model?.currentNode ?? null,
      },
      exitLabel ? { exitLabel } : null
    );
  }

  const showObjectiveTracker = computed(() => {
    return (
      store.objectivesAvailable &&
      store.objectivesRows.length > 0 &&
      store.view.mode !== "creation"
    );
  });

  return {
    completionCandidates,
    contextAffordances,
    dialogueVM,
    onDialogueFreeform,
    onDialogueLeave,
    onDialoguePick,
    onMapMove,
    possessionBanner,
    releaseAffordance,
    showObjectiveTracker,
    titleBallotCandidates,
    titleBallotPanel,
  };
}
