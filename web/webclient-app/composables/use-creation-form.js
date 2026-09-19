// The creation wizard's core form state (extracted verbatim from
// CreationOverlay.vue so the SFC stays a passive renderer): the panel-derived
// computeds, the custom-form field refs, the touched-tracking watchers and the
// server-draft resync. Watchers 1–3 keep their registration order here; the
// proposal/settlement/stage watchers join in the sibling groups through the
// use-creation-overlay.js facade.
import { computed, reactive, ref, watch } from "vue";

export function useCreationForm(props) {
  const available = computed(() => props.creation.available === true);
  const reason = computed(() => props.creation.reason?.message ?? "");
  const presets = computed(() =>
    (Array.isArray(props.creation.presets) ? props.creation.presets : []),
  );
  const custom = computed(() => props.creation.custom);
  const draft = computed(() => props.creation.draft);

  // In-flight concept apply (retool-concept-fill-navigation D1): the local
  // loading window from an ADMITTED dispatch until the request settles (fresh
  // proposal applied, matching non-success result, or the global dispatch gate
  // releases without a matching settlement). Reconnect/remount resets it to
  // false naturally.
  const conceptPending = ref(false);
  // The stage object of the publish whose completion navigation this overlay
  // just performed (D3 completion-publish pin): while `props.stage` IS that
  // object, its stale root value must not overwrite the completion tab. One
  // publish exactly — every later publish mirrors normally, keeping the
  // keyboard-router mirror alive.
  // `undefined` is the never-matching sentinel: the latch only ever records a
  // real stage object, so a null `stage` prop (outside creation mode / in
  // standalone mounts) can never be mistaken for a consumed completion publish.
  // Held as a plain box so the proposal/stage groups share one latch.
  const latchedStage = { value: undefined };

  // The apply button is frozen while this request waits AND while any other
  // mutation holds the store's single-dispatch gate (a gate-held apply could
  // never be admitted; freezing the control matches the affordance).
  const applyFrozen = computed(
    () =>
      conceptPending.value ||
      Boolean(props.dispatchState && props.dispatchState.inFlight !== null),
  );

  // The wizard resumes from the draft's own stage; without a draft it opens
  // the preset state. Live snapshot updates to the `creation` prop re-sync the
  // wizard from the server-persisted draft (webclient-character-creation-ui:
  // the server owns the draft — the browser resumes at the saved stage).
  const stageMode = (stage) =>
    stage === "custom_filled" ? "custom" : "preset";
  const mode = ref("preset");

  function setMode(next) {
    mode.value = next;
  }

  // Form state (custom + concept sub-states).
  const name = ref("");
  // A plain authored starting age for the fresh form (a suggested value, not a
  // bound): the descriptor's 0..10000 age bounds are the only gate.
  const age = ref(18);
  const apparentAge = ref(18);
  const race = ref("human");
  const subrace = ref(null);
  const allocations = reactive({ hp: 0, mp: 0, sp: 0, atk_phys: 0, agility: 0, defense: 0, magic_power: 0 });
  const background = ref("");
  // Mirror of world/lore/sex.py DEFAULT_SEX (key only — the option labels are
  // server-owned prose shipped in `custom.sex`). Kept byte-identical to the
  // creation_menu.js DEFAULT_SEX_KEY and pinned by
  // tests/test_creation_parity_contract.py (namegen-creation-ui D11).
  const SEX_DEFAULT_KEY = "other";
  const sex = ref(SEX_DEFAULT_KEY);
  // The player-owned persona block (retool-concept-transient-fill D3/D5):
  // three always-rendered prose textareas, all-empty or all-filled at submit.
  const persona = reactive({ personality: "", life_story: "", habit: "" });
  const affinitySelected = ref(new Set());
  const conceptText = ref("");
  const selectedPresetKey = ref(null);

  function zeroAllocations() {
    allocations.hp = 0;
    allocations.mp = 0;
    allocations.sp = 0;
    allocations.atk_phys = 0;
    allocations.agility = 0;
    allocations.defense = 0;
    allocations.magic_power = 0;
  }

  // Tracks any local form input since the last server draft: a no-draft
  // snapshot must never discard typed values (e.g. a pointer-opened custom form
  // hit by a reconnect snapshot without a draft). Draft-driven field fills are
  // guarded by `syncingDraft` so they never count as user input, and leaving
  // the form (preset mode) clears the flag.
  const formTouched = ref(false);
  let syncingDraft = false;
  function markFormTouched() {
    if (!syncingDraft) {
      formTouched.value = true;
    }
  }
  watch(
    [name, age, apparentAge, race, subrace, background, persona, conceptText, allocations, sex],
    markFormTouched,
    { deep: true, flush: "sync" },
  );
  watch(mode, (m) => {
    if (m === "preset") {
      formTouched.value = false;
    }
  });

  // Re-sync every wizard field from the server-confirmed draft carried by the
  // latest `creation` panel payload; with no draft, reset to the preset state
  // with default field values.
  function syncFromDraft() {
    const d = props.creation.draft;
    if (!d) {
      // With no server draft the wizard resets to the preset state UNLESS the
      // store-driven dock stage is already on a form (keyboard navigation into
      // the custom/concept form must survive a fresh snapshot that carries no
      // draft, e.g. a stale-save rejection) or the player has typed into the
      // local form (a pointer-opened form must survive a no-draft snapshot too).
      const stage = props.stage ? props.stage.stage : null;
      // The in-flight pin and the completion-publish pin (D2/D3): during a
      // pending apply — and for the single publish whose completion this
      // overlay already navigated — the store's stage signal never moves the
      // presented tab. Field sync below stays untouched.
      if (
        stage !== "custom" &&
        stage !== "concept" &&
        !formTouched.value &&
        !conceptPending.value &&
        props.stage !== latchedStage.value
      ) {
        mode.value = "preset";
        selectedPresetKey.value = null;
      }
      return;
    }
    syncingDraft = true;
    try {
      // A live concept apply flips the store-driven dock stage to "custom" so the
      // pre-filled custom form shows; a resumed concept draft (no stage flip) keeps
      // the concept field (stageMode maps concept_filled -> concept).
      const stage = props.stage ? props.stage.stage : null;
      if (!conceptPending.value && props.stage !== latchedStage.value) {
        mode.value = stage === "custom" ? "custom" : stageMode(d.stage);
      }
      if (d.mode === "preset") {
        selectedPresetKey.value = d.preset_key ?? null;
        return;
      }
      name.value = d.display_name ?? "";
      age.value = d.age ?? 18;
      apparentAge.value = d.apparent_age ?? 18;
      race.value = d.race ?? "human";
      subrace.value = d.subrace ?? null;
      sex.value = d.sex ?? SEX_DEFAULT_KEY;
      zeroAllocations();
      if (d.allocations) {
        for (const axis of Object.keys(allocations)) {
          allocations[axis] = d.allocations[axis] ?? 0;
        }
      }
      background.value = d.background ?? "";
      affinitySelected.value = new Set(d.affinity_elements ?? []);
      const block = d.persona ?? null;
      persona.personality = block?.personality ?? "";
      persona.life_story = block?.life_story ?? "";
      persona.habit = block?.habit ?? "";
      formTouched.value = false;
    } finally {
      syncingDraft = false;
    }
  }

  syncFromDraft();
  watch(() => props.creation.draft, syncFromDraft, { deep: true });

  function personaFilled() {
    return [persona.personality, persona.life_story, persona.habit].filter(
      (text) => text.trim() !== "",
    ).length;
  }

  // The transient proposal fill runs in the sibling group but shares this
  // group's draft-sync guard: a proposal fill must never count as user input.
  function runGuardedSync(fill) {
    syncingDraft = true;
    try {
      fill();
    } finally {
      syncingDraft = false;
    }
  }

  return {
    available,
    reason,
    presets,
    custom,
    draft,
    conceptPending,
    latchedStage,
    applyFrozen,
    stageMode,
    mode,
    setMode,
    name,
    age,
    apparentAge,
    race,
    subrace,
    allocations,
    background,
    SEX_DEFAULT_KEY,
    sex,
    persona,
    affinitySelected,
    conceptText,
    selectedPresetKey,
    zeroAllocations,
    formTouched,
    syncFromDraft,
    personaFilled,
    runGuardedSync,
  };
}
