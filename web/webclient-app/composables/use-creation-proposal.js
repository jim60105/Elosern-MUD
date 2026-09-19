// The transient concept proposal fill (retool-concept-transient-fill D1/D5),
// extracted verbatim from CreationOverlay.vue so the SFC stays a passive
// renderer. Registers the proposal watcher (the fourth registration, after the
// form group's touched/draft watchers); the mount-time fill is invoked by the
// use-creation-overlay.js facade at the end of setup, exactly as the original
// SFC did.
import { ref, watch } from "vue";

export function useCreationProposal(props, form, custom) {
  const {
    conceptPending,
    latchedStage,
    mode,
    setMode,
    name,
    age,
    apparentAge,
    race,
    subrace,
    allocations,
    background,
    persona,
    affinitySelected,
    runGuardedSync,
    personaFilled,
  } = form;
  const { races, affinityMax, affinityElements } = custom;

  // The panel's optional `proposal` slot pre-fills the form only when its
  // `revision` is strictly newer than the last applied revision: a panel
  // rebuild re-publishes the same revision and must never discard the player's
  // edits, while a fresh apply of byte-identical content raises the revision
  // and does replace the generated fields. Nothing here auto-submits.
  const lastAppliedRevision = ref(0);
  const reviewPrompt = ref("");

  function applyProposal() {
    const p = props.creation.proposal;
    if (!p || typeof p.revision !== "number" || p.revision <= lastAppliedRevision.value) {
      return;
    }
    reviewPrompt.value = "";
    // A race-changing proposal over locally-typed persona prose shows a
    // non-blocking review prompt naming the incoming race (design D5 — the
    // server never overwrites or clears what the player typed).
    if (p.race !== race.value && personaFilled() > 0) {
      reviewPrompt.value = `概念提案的種族為「${p.race}」，與目前選擇不同；請確認人設文字是否仍適合。`;
    }
    runGuardedSync(() => {
      race.value = p.race;
      const info = races.value.find((r) => r.key === p.race);
      subrace.value =
        info && Array.isArray(info.subraces) && info.subraces.includes(p.subrace)
          ? p.subrace
          : null;
      if (p.allocations) {
        for (const axis of Object.keys(allocations)) {
          if (typeof p.allocations[axis] === "number") {
            allocations[axis] = p.allocations[axis];
          }
        }
      }
      persona.personality = p.persona.personality;
      persona.life_story = p.persona.life_story;
      persona.habit = p.persona.habit;
      // Transient-fill fields (retool-concept-fill-navigation D4): an absent
      // key never encodes as null — it leaves the local value untouched; a
      // present key replaces it. The generation layer already clamped ages
      // into the 0..10000 range and truncated texts, so the local gates stay as
      // a second line of defence, never re-normalised here.
      if (typeof p.display_name === "string" && p.display_name !== "") {
        name.value = p.display_name;
      }
      if (typeof p.background === "string" && p.background !== "") {
        background.value = p.background;
      }
      if (typeof p.age === "number") {
        age.value = p.age;
      }
      if (typeof p.apparent_age === "number") {
        apparentAge.value = p.apparent_age;
      }
      if (Array.isArray(p.affinity_elements)) {
        // Affinity is written only from the (already-assigned) new race's
        // registered element keys and capped to its maximum (the wire may
        // carry a different race's legal set).
        const registered = new Set(affinityElements.value.map((el) => el.key));
        const capped = p.affinity_elements.filter((key) => registered.has(key)).slice(0, affinityMax.value);
        affinitySelected.value = new Set(capped);
      } else {
      // The new race may cap the affinity selection; trim as onRaceChange does.
        const max = affinityMax.value;
        const keys = [...affinitySelected.value];
        if (keys.length > max) affinitySelected.value = new Set(keys.slice(0, max));
      }
    });
    lastAppliedRevision.value = p.revision;
    // Completion of a concept apply (D1/D3): settle the loading window, and
    // when the player is still on the concept tab, navigate to the custom tab
    // and confirm exactly once through the action-feedback queue (the form is
    // the sole writer of the success toast; the store stays silent on
    // success). A mount-time fill lands outside the concept tab, so it never
    // navigates or confirms. The completion-publish pin records THIS stage
    // object: its (stale) root value must not overwrite the navigation the
    // later-registered stage watcher would otherwise mirror within the same
    // flush.
    if (conceptPending.value) conceptPending.value = false;
    if (mode.value === "concept") {
      if (props.stage) latchedStage.value = props.stage;
      setMode("custom");
      if (typeof props.pushToast === "function") {
        props.pushToast({ title: "概念提案已套用到自訂表單", tone: "info" });
      }
    }
  }

  // The mount-time fill runs at the end of setup (after the descriptor
  // computeds exist); the watcher covers every later panel delivery.
  watch(() => props.creation.proposal, applyProposal, { deep: true });

  return { applyProposal, reviewPrompt };
}
