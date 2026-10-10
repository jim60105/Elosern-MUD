// The exploration root pane's compass wiring (exploration-exit-compass design
// D2/D3/D4/D6): the compass targets from the committed exit rows and local
// map, the commit signals it steps on, its gated submission, the rejection
// feedback it stops on, the shared readout's state, and the minimap's aimed
// node. The compass itself (ExitCompass.vue) sends nothing; this composable
// is the only place its `move` reaches the store.
import { computed, getCurrentScope, nextTick, onScopeDispose, ref, watch } from "vue";
import { resolveTargets } from "../components/compass-model.js";
import {
  FLASH_MS,
  aimReadout,
  blockedReadout,
  idleReadout,
  presentCount,
  readoutContent,
} from "../components/exploration-readout.js";
import { NON_SUCCESS_OUTCOMES } from "../stores/elosern/shared.js";

// The readout's local state (design D4): the compass aim and a blocked-move
// flash that holds the line for FLASH_MS. `idle` is a getter for the idle
// summary content.
export function useReadoutState(idle) {
  const aim = ref(null);
  const flash = ref(null);
  let timer = null;

  function setAim(next) {
    aim.value = next;
  }

  function showFlash(content) {
    clearTimeout(timer);
    flash.value = content;
    timer = setTimeout(() => {
      timer = null;
      flash.value = null;
    }, FLASH_MS);
  }

  function clear() {
    clearTimeout(timer);
    timer = null;
    flash.value = null;
    aim.value = null;
  }

  if (getCurrentScope()) {
    onScopeDispose(() => clearTimeout(timer));
  }

  const content = computed(() =>
    readoutContent({ flash: flash.value, aim: aimReadout(aim.value), idle: idle() }),
  );

  return { aim, flash, content, setAim, showFlash, clear };
}

export function useExitCompass(store, { panel, compassRef }) {
  const explorationPanel = computed(() => panel("exploration"));

  const targets = computed(() =>
    resolveTargets(store.view.explorationExits || [], store.view.localMapModel, {
      currentNode: store.view.explorationCurrentNode,
    }),
  );

  // The arrival signal: the committed room identity, which changes exactly on
  // movement (the same key the dock's room-change reset uses).
  const compassArrivalKey = computed(() => {
    const identity = explorationPanel.value?.look?.room?.identity;
    return identity === undefined ? null : identity;
  });

  const compassBusy = computed(() => !!store.view.submitLocked);

  // The compass is the live control only at the exploration root, with no
  // drawer or overlay over it; anything else stops a walk.
  const compassActive = computed(
    () =>
      store.view.mode === "exploration" &&
      store.view.dockSource === "exploration.root" &&
      !store.view.degradedRoot &&
      !store.view.hudDrawer &&
      !store.view.hudOverlay,
  );

  const readout = useReadoutState(() =>
    idleReadout(targets.value.cycle.length, presentCount(explorationPanel.value)),
  );

  // The compass's own last request, so its result (and only its result) can
  // stop a walk or explain a stop.
  let pendingRequestId = null;

  function resultFor(requestId) {
    const result = store.view.lastActionResult;
    return requestId && result && result.requestId === requestId ? result : null;
  }

  function onCompassMove(item) {
    const exitRef = item && item.payload ? item.payload.exit_ref : null;
    const outcome = exitRef === null ? { sent: false } : store.activateExit(exitRef);
    if (outcome.sent) {
      pendingRequestId = outcome.requestId;
      return;
    }
    // The gate refused (a stale row, a lock the compass did not see, a lost
    // connection): the compass must not wait for an arrival that never comes.
    compassRef.value?.halt(outcome.reason === "disabled" ? outcome.item?.disabledReason?.message || null : null);
  }

  function onCompassAim(aim) {
    readout.setAim(aim);
  }

  function onCompassBlocked(blocked) {
    const result = resultFor(pendingRequestId);
    readout.showFlash(blockedReadout(blocked, { resultMessage: result ? result.message : null }));
  }

  // A rejected, stale, or failed result for the compass's request stops the
  // walk with the server's message.
  watch(
    () => store.view.lastActionResult,
    (result) => {
      if (!result || !pendingRequestId || result.requestId !== pendingRequestId) {
        return;
      }
      if (NON_SUCCESS_OUTCOMES.includes(result.outcome)) {
        pendingRequestId = null;
        compassRef.value?.halt(result.message || null);
      }
    },
  );

  // The minimap highlight (design D6): the aimed exit's destination node,
  // when it is a committed minimap node.
  const aimedNode = computed(() => {
    const target = readout.aim.value?.target;
    return target && target.destinationOnMap ? target.destination : null;
  });

  // Entering exploration focuses the compass (redesign §5.4). The shell
  // hands focus over on a mode change into exploration; this covers the
  // compass's first appearance in an exploration stretch (the session's first
  // snapshot, whose mode never "changes"). Only focus that sits nowhere (the
  // body, a removed element) or on the dock itself moves; later re-mounts in
  // the same stretch (returning from the waiting frame) leave focus to the
  // router's path.
  let entered = false;
  watch(
    () => store.view.mode,
    (mode) => {
      if (mode !== "exploration") {
        entered = false;
      }
    },
  );
  watch(
    compassRef,
    async (compass) => {
      if (!compass || entered || store.view.mode !== "exploration") {
        return;
      }
      entered = true;
      await nextTick();
      if (typeof document === "undefined") {
        return;
      }
      const active = document.activeElement;
      const dock = document.getElementById("action-dock");
      if (!active || active === document.body || active === document.documentElement || !active.isConnected || active === dock) {
        compass.focus();
      }
    },
    { flush: "post" },
  );

  return {
    compassTargets: targets,
    compassArrivalKey,
    compassBusy,
    compassActive,
    readoutContent: readout.content,
    aimedNode,
    onCompassMove,
    onCompassAim,
    onCompassBlocked,
  };
}
