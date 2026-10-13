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
  // The hovered or focused presence-rail entry's content
  // (exploration-presence-rail design D6).
  const rail = ref(null);
  // The hovered or focused place-card button and 建議 pill
  // (exploration-room-actions design D6).
  const place = ref(null);
  const pill = ref(null);
  const flash = ref(null);
  let timer = null;

  function setAim(next) {
    aim.value = next;
  }

  function setRail(next) {
    rail.value = next;
  }

  function setPlace(next) {
    place.value = next;
  }

  function setPill(next) {
    pill.value = next;
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
    rail.value = null;
    place.value = null;
    pill.value = null;
  }

  if (getCurrentScope()) {
    onScopeDispose(() => clearTimeout(timer));
  }

  const content = computed(() =>
    readoutContent({
      flash: flash.value,
      aim: aimReadout(aim.value),
      rail: rail.value,
      place: place.value,
      pill: pill.value,
      idle: idle(),
    }),
  );

  return { aim, rail, place, pill, flash, content, setAim, setRail, setPlace, setPill, showFlash, clear };
}

export function useExitCompass(store, { panel, compassRef }) {
  const explorationPanel = computed(() => panel("exploration"));

  const targets = computed(() =>
    resolveTargets(store.view.explorationExits || [], store.view.localMapModel, {
      currentNode: store.view.explorationCurrentNode,
    }),
  );

  // Wilderness rooms can be reused across coordinates. Include the committed
  // node so every logical arrival is observed even when the room id survives.
  const compassArrivalKey = computed(() => {
    const identity = explorationPanel.value?.look?.room?.identity;
    return identity === undefined
      ? null
      : `${identity}:${store.view.explorationCurrentNode ?? ""}`;
  });

  const compassBusy = computed(() => !!store.view.submitLocked);

  // The compass is the live control only at the exploration root, with no
  // drawer or overlay over it; anything else stops a walk.
  // An open presence card (exploration-presence-rail) or room card — the
  // wait or suggestions card (exploration-room-actions) — stops it too.
  const compassActive = computed(
    () =>
      store.view.mode === "exploration" &&
      store.view.dockSource === "exploration.root" &&
      !store.view.presenceCard &&
      !store.view.roomCard &&
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
  // body, a removed element) or on the dock itself moves; a later re-mount in
  // the same stretch (the panel turning available again) leaves focus to the
  // unmount rescue below and the shell's focus home.
  //
  // The compass unmounting while it held focus (the exploration panel turned
  // unavailable, a degraded root) would drop focus to the body: it goes to
  // the dock, the exploration screen's remaining focus home
  // (exploration-room-actions).
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
    async (compass, previous) => {
      if (!compass) {
        if (!previous || typeof document === "undefined") {
          return;
        }
        await nextTick();
        if (store.view.mode !== "exploration") {
          return;
        }
        const active = document.activeElement;
        if (!active || active === document.body || active === document.documentElement || !active.isConnected) {
          document.getElementById("action-dock")?.focus({ preventScroll: true });
        }
        return;
      }
      if (entered || store.view.mode !== "exploration") {
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
    // The presence rail's readout feed and the departed flash
    // (exploration-presence-rail design D6).
    onRailHover: readout.setRail,
    // The place card's buttons and the 建議 pill (exploration-room-actions).
    onPlaceHover: readout.setPlace,
    onPillHover: readout.setPill,
    showReadoutFlash: readout.showFlash,
  };
}
