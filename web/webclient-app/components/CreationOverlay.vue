<script setup>
// CreationOverlay (B5 overlays family): the full-viewport character-creation
// wizard for the committed `creation` v2 panel (web/webclient/presentation/
// creation.py). Sub-states stay separate and testable (design D-risk): a
// preset-pick state, the custom form (name/adult/race/subrace/allocation/
// affinity/background/persona), and the concept state. The v2 panel carries
// the player-owned draft `persona` block and the optional transient concept
// `proposal` slot (retool-concept-transient-fill): the slot pre-fills the
// custom form revision-gated and never auto-submits. The adult gate (design
// D1) rejects BOTH the age and apparent_age fields below the descriptor's 18
// minimum before activation. Every action emits the exact OOB `creation.*`
// envelope — no field is invented; the server remains authoritative.
import { computed, reactive, ref, watch } from "vue";

// The same stable fallback line the store uses for a recognized non-success
// result with no usable message (webclient-action-result-feedback D-D); the
// overlay is the presenting surface in creation mode, so the fallback must
// exist here too. Kept byte-identical to the store constant, pinned by
// tests/overlays/creation_overlay.test.js.
const ACTION_RESULT_FALLBACK_MESSAGE = "動作未生效，請重試或返回上層。";

const props = defineProps({
  // The committed `creation` v2 panel payload (the available form, a
  // server-persisted wizard draft, or the registry-owned unavailable form).
  creation: { type: Object, required: true },
  open: { type: Boolean, default: true },
  // The store's last `ui_action_result` (or null): a rejected creation
  // action renders its code/message in the form message (the legacy
  // `creation-form-message` hook).
  result: { type: Object, default: null },
  // The store-driven creation dock stage (the legacy creation dock port):
  // null outside creation mode, otherwise the dock stage the keyboard router
  // and the confirmation screens mirror (root/presets/custom/confirm).
  stage: { type: Object, default: null },
  // A return-bearing dispatch callback (AppClient wraps `store.dispatchAction`):
  // returns the requestId when the mutation is admitted, null when the
  // single-mutation-in-flight gate rejects it. The concept apply sets its
  // loading state ONLY after admission, so a gate-rejected apply never
  // sticks a spinner (retool-concept-fill-navigation D1). Without the prop
  // (standalone mounts/tests) the apply falls back to the `action` event.
  dispatch: { type: Function, default: null },
  // The store's `view.dispatch` slice ({inFlight, submittedRequestId}): the
  // failure-match correlation and the global-gate release safety net (D1).
  dispatchState: { type: Object, default: null },
  // The action-feedback queue API (add-action-feedback-toasts). The form is
  // the SOLE writer of the concept-apply success confirmation toast (D3);
  // the store writes only failure crits.
  pushToast: { type: Function, default: null },
});

const emit = defineEmits(["action", "request-reset", "cancel-confirm"]);

const available = computed(() => props.creation.available === true);
const reason = computed(() => props.creation.reason?.message ?? "");
const presets = computed(() => (Array.isArray(props.creation.presets) ? props.creation.presets : []));
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
let latchedStage = undefined;

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

// Form state (custom + concept sub-states).
const name = ref("");
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
      props.stage !== latchedStage
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
    if (!conceptPending.value && props.stage !== latchedStage) {
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

// -- Transient concept proposal fill (retool-concept-transient-fill D1/D5) --
// The panel's optional `proposal` slot pre-fills the form only when its
// `revision` is strictly newer than the last applied revision: a panel
// rebuild re-publishes the same revision and must never discard the player's
// edits, while a fresh apply of byte-identical content raises the revision
// and does replace the generated fields. Nothing here auto-submits.
const lastAppliedRevision = ref(0);
const reviewPrompt = ref("");

function personaFilled() {
  return [persona.personality, persona.life_story, persona.habit].filter(
    (text) => text.trim() !== "",
  ).length;
}

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
  syncingDraft = true;
  try {
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
    // into the adult band and truncated texts, so the local gates stay as
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
  } finally {
    syncingDraft = false;
  }
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
    if (props.stage) latchedStage = props.stage;
    setMode("custom");
    if (typeof props.pushToast === "function") {
      props.pushToast({ title: "概念提案已套用到自訂表單", tone: "info" });
    }
  }
}

// The mount-time fill runs at the end of setup (after the descriptor
// computeds exist); the watcher covers every later panel delivery.
watch(() => props.creation.proposal, applyProposal, { deep: true });

// Failure settlement (D1): this request's non-success result settles the
// loading window. The guard comes first — a standalone mount carrying a
// foreign result and no dispatch state must never deref.
const NON_SUCCESS_OUTCOMES = ["rejected", "stale", "error"];
watch(
  () => props.result,
  (r) => {
    if (!props.dispatchState || !r) return;
    // Name-roll settlement (namegen-creation-ui D6): the backfill happens
    // ONLY for the request this overlay submitted, with a success outcome
    // and a usable data slot; anything else just settles the in-flight
    // state and never touches the name the player may have typed since.
    if (rollPending.value && r.requestId === rollRequestId.value) {
      rollPending.value = false;
      if (
        r.outcome === "success" &&
        r.data &&
        typeof r.data.display_name === "string" &&
        r.data.display_name !== ""
      ) {
        name.value = r.data.display_name;
      }
    }
    if (!conceptPending.value) return;
    if (
      NON_SUCCESS_OUTCOMES.indexOf(r.outcome) !== -1 &&
      r.requestId === props.dispatchState.submittedRequestId
    ) {
      conceptPending.value = false;
    }
  },
);

// Global-gate safety net (D1c): a synchronous sender failure or a lost
// mutation releases the store gate WITHOUT any settlement this overlay can
// observe; the release itself settles the loading window (never a
// premature clear — during a healthy wait the gate stays held until the
// result commits and its presentation revision is reached).
watch(
  () => props.dispatchState,
  (d) => {
    if (!d || d.inFlight === null) {
      conceptPending.value = false;
      rollPending.value = false;
    }
  },
);

// -- Preset state -----------------------------------------------------------
function setMode(next) {
  mode.value = next;
}

function selectPreset(card) {
  selectedPresetKey.value = card.key;
  emit("action", { action_id: "creation.preset", payload: { preset_key: card.key } });
}

// -- Custom state -----------------------------------------------------------
const minimumAge = computed(() => custom.value?.adult?.age_minimum ?? 18);
const minimumApparentAge = computed(() => custom.value?.adult?.apparent_age_minimum ?? 18);

const races = computed(() => (Array.isArray(custom.value?.races) ? custom.value.races : []));

const raceInfo = computed(() => races.value.find((r) => r.key === race.value));
const hasSubraces = computed(() => Array.isArray(raceInfo.value?.subraces));
// The gender select renders the server descriptor verbatim; no label literal
// exists in this component (webclient-character-creation-ui D4).
const sexOptions = computed(() => (Array.isArray(custom.value?.sex) ? custom.value.sex : []));
const subraceOptions = computed(() => {
  const list = raceInfo.value?.subraces ?? [];
  const registry = custom.value?.subraces ?? {};
  return list.map((key) => ({ key, label: registry[key]?.display_name_zh ?? key }));
});
const affinity = computed(() => custom.value?.affinity?.[race.value]);
const affinityMax = computed(() => affinity.value?.maximum ?? 0);
const affinityElements = computed(() => affinity.value?.elements ?? []);

// Strict (race, subrace) match only — no same-race or first-profile
// fallback, so a missing profile shows no briefing rather than a wrong one.
const currentProfile = computed(() => {
  const profiles = Array.isArray(custom.value?.profiles) ? custom.value.profiles : [];
  const sub = subrace.value ?? null;
  return profiles.find((p) => p.race === race.value && (p.subrace ?? null) === sub) ?? null;
});

// Allocation briefing (character-creation-ux contract): before the
// allocation inputs, state the profile budget, each axis's 0–span range, and
// the rule that the total must equal the budget.
const allocationTotal = computed(() =>
  Object.values(allocations).reduce((sum, value) => sum + (Number(value) || 0), 0));
const budgetBriefing = computed(() => {
  const profile = currentProfile.value;
  if (!profile) return "";
  const ranges = profile.axes.map((a) => `${a.label} ${a.minimum}-${a.maximum}`).join(" · ");
  return `點數額度 ${profile.budget}｜${ranges}｜總和須等於額度 ${profile.budget}`;
});

// The adult gate (design D1): reject when EITHER age field is below the
// descriptor's minimum (18) — the server stays authoritative.
const gatePassed = computed(
  () => Number(age.value) >= minimumAge.value && Number(apparentAge.value) >= minimumApparentAge.value,
);
const gateError = ref(false);
const budgetError = ref(false);
const subraceError = ref(false);
const personaError = ref(false);

// The legacy `creation-form-message` hook (Phase-0 audit §2.3 REMAP-TO-TESTID):
// a single form-message element that surfaces a server rejection (result.code /
// result.message) or the first active local validation error. The element is
// rendered only while a message is active.
// Local validation messages only. A server action result never renders here:
// it speaks verbatim through the always-reachable result region below
// (webclient-action-result-feedback: showing `result.code` would paraphrase
// the server-authored message).
const formMessage = computed(() => {
  if (gateError.value) return `年齡與外觀年齡皆須 ≥ ${minimumAge.value}`;
  if (subraceError.value) return "已選擇有血統的種族時，必須先選擇血統";
  if (budgetError.value) return `點數總和 ${allocationTotal.value} 不等於額度 ${currentProfile.value?.budget}`;
  if (personaError.value) return "人設三欄（個性、生平、習慣）需全部填寫或全部留空";
  return "";
});

// The overlay's presentation of a recognized non-success result
// (webclient-action-result-feedback D-C): while the overlay is mounted it is
// THE surface for the envelope's message, so it renders the message verbatim
// across every wizard stage (preset/custom/concept/confirm) in one
// always-reachable region; the stable fallback covers the malformed
// message-less edge.
const RESULT_NON_SUCCESS = ["rejected", "stale", "error"];
const resultMessage = computed(() => {
  const r = props.result;
  if (!r || RESULT_NON_SUCCESS.indexOf(r.outcome) === -1) return "";
  const m = typeof r.message === "string" && r.message.trim() !== "" ? r.message : ACTION_RESULT_FALLBACK_MESSAGE;
  return m;
});

function onRaceChange() {
  const info = races.value.find((r) => r.key === race.value);
  if (!info || !Array.isArray(info.subraces)) subrace.value = null;
  const max = affinityMax.value;
  const keys = [...affinitySelected.value];
  if (keys.length > max) affinitySelected.value = new Set(keys.slice(0, max));
}

function toggleAffinity(elementKey) {
  const next = new Set(affinitySelected.value);
  if (next.has(elementKey)) {
    next.delete(elementKey);
  } else if (next.size < affinityMax.value) {
    next.add(elementKey);
  }
  affinitySelected.value = next;
}

// The custom form cannot submit without a subrace for a subrace-bearing
// race (webclient-character-creation-ui: the form SHALL require a subrace
// selection; the "no subrace" radio is never rendered) — send nothing.
function confirmCustom() {
  gateError.value = false;
  budgetError.value = false;
  subraceError.value = false;
  personaError.value = false;
  if (!gatePassed.value) {
    gateError.value = true;
    return;
  }
  if (hasSubraces.value && !subrace.value) {
    subraceError.value = true;
    return;
  }
  const profile = currentProfile.value;
  if (profile && allocationTotal.value !== profile.budget) {
    budgetError.value = true;
    return;
  }
  // Persona local validation is all-empty-or-all-filled (design D5): a
  // partially-filled triple blocks submission with a localized reason.
  const filled = personaFilled();
  if (filled !== 0 && filled !== 3) {
    personaError.value = true;
    return;
  }
  const payload = {
    display_name: name.value,
    age: Number(age.value),
    apparent_age: Number(apparentAge.value),
    race: race.value,
    subrace: subrace.value,
    // The wire payload always carries the exact nine keys (the server
    // revalidates the set); blank fields emit their JSON-safe defaults, the
    // same convention as the legacy creation menu.
    background: background.value.trim() !== "" ? background.value.trim() : null,
    affinity_elements: [...affinitySelected.value],
    allocations: {
      hp: Number(allocations.hp),
      mp: Number(allocations.mp),
      sp: Number(allocations.sp),
      atk_phys: Number(allocations.atk_phys),
      agility: Number(allocations.agility),
      defense: Number(allocations.defense),
      magic_power: Number(allocations.magic_power),
    },
    // All-empty ships null; a filled triple ships the trimmed block verbatim
    // (upload-is-intent — the server stores it without semantic filtering).
    persona:
      filled === 0
        ? null
        : {
            personality: persona.personality.trim(),
            life_story: persona.life_story.trim(),
            habit: persona.habit.trim(),
          },
    // The optional tenth key: the mirrored default is omitted (the server
    // normalizes identically); any explicit non-default selection ships
    // verbatim (namegen-creation-ui D2/D11).
    ...(sex.value && sex.value !== SEX_DEFAULT_KEY ? { sex: sex.value } : {}),
  };
  emit("action", { action_id: "creation.custom", payload });
}

// -- Concept state -----------------------------------------------------------
function applyConcept() {
  // Admission-gated pending (retool-concept-fill-navigation D1a): with the
  // return-bearing dispatch prop, pending flips ONLY when the store admits
  // the mutation — a gate-rejected apply never creates a waiting state.
  // Without the prop (standalone mounts/tests) the emit path sets pending
  // optimistically; the gate-release safety net still settles it.
  if (typeof props.dispatch === "function") {
    if (props.dispatch({ action_id: "creation.concept", payload: { concept: conceptText.value } }) === null) {
      return;
    }
    conceptPending.value = true;
  } else {
    conceptPending.value = true;
    emit("action", { action_id: "creation.concept", payload: { concept: conceptText.value } });
  }
}

// -- Name roll ---------------------------------------------------------------
// The dice button shares the store's single-mutation gate: like the concept
// apply, the loading state flips ONLY after admission (a gate-held click
// never shows a spinner and never double-dispatches, retool-concept-fill-
// navigation D1a semantics reused).
const rollPending = ref(false);
const rollRequestId = ref(null);

function rollName() {
  const payload = {
    race: race.value ?? null,
    subrace: subrace.value ?? null,
    // The DISPLAYED selection is always sent: the select model is a concrete
    // key (D11), so a fresh roll carries the mirrored default.
    sex: sex.value ?? null,
  };
  if (typeof props.dispatch === "function") {
    const requestId = props.dispatch({ action_id: "creation.roll_name", payload });
    if (requestId === null) return;
    rollPending.value = true;
    rollRequestId.value = requestId;
  } else {
    rollPending.value = true;
    rollRequestId.value = null;
    emit("action", { action_id: "creation.roll_name", payload });
  }
}

// Shared dispatch gate: any in-flight mutation (this roll, a save, a concept
// apply) disables the dice button through the store's dispatch slice.
const rollDisabled = computed(
  () =>
    rollPending.value ||
    Boolean(props.dispatchState && props.dispatchState.inFlight !== null),
);

// -- Frame actions -----------------------------------------------------------
// Activation and the destructive reset always traverse the confirmation
// screen (the legacy creation dock contract): the store opens the confirm
// stage after a successful save or on a reset request, and only the confirm
// screen's 確認 button dispatches `creation.activate` / `creation.reset`.
function requestReset() {
  emit("request-reset");
}

// The store-driven creation dock stage mirrors the wizard's mode so keyboard
// and pointer share one flow: root/presets -> preset, custom -> custom,
// concept -> concept, confirm -> the confirmation screen overlays the body.
// Only a stage VALUE change re-syncs (a pointer tab click must not be
// overridden by an unchanged root stage re-publish).
let lastStage = null;
watch(
  () => props.stage,
  (s) => {
    const value = s ? s.stage : null;
    if (value === null || value === lastStage) {
      return;
    }
    // The in-flight pin and the completion-publish pin (D2/D3): while a
    // concept apply is pending, the store's stage signal never moves the
    // presented tab (a republish — including the dispatch's own re-emitted
    // root — must not kick the player off the concept tab); and the stage
    // object of the publish whose completion navigation this overlay already
    // performed is recognized as stale, so it cannot overwrite the landing
    // on the custom tab. The pin is exactly one publish: any later publish
    // (new object identity) mirrors normally, keeping keyboard navigation
    // intact.
    if (conceptPending.value) {
      lastStage = value;
      return;
    }
    if (s === latchedStage) {
      lastStage = value;
      return;
    }
    lastStage = value;
    if (value === "custom") {
      mode.value = "custom";
    } else if (value === "concept") {
      mode.value = "concept";
    } else if (value === "root" || value === "presets") {
      mode.value = "preset";
    }
  },
);

function confirmCurrent() {
  const actionId = props.stage && props.stage.confirmAction;
  if (actionId) {
    emit("action", { action_id: actionId, payload: {} });
  }
}

function cancelConfirm() {
  emit("cancel-confirm");
}

// Mount-time proposal fill: a panel that already carries an unconsumed
// proposal (a same-session remount) pre-fills the form before first paint.
applyProposal();
</script>

<template>
  <section
    v-if="open"
    class="elosern creation-overlay"
    role="dialog"
    aria-modal="true"
    aria-label="角色創建"
    data-testid="creation-overlay"
    :data-available="available ? 'true' : 'false'"
    :data-mode="mode"
  >
    <header class="creation-overlay__header">
      <h2 class="creation-overlay__title" data-testid="creation-overlay-title">角色創建</h2>
    </header>

    <div class="creation-overlay__body" data-testid="creation-body">
      <template v-if="available">
        <p
          v-if="resultMessage"
          class="creation-result-message"
          role="alert"
          data-testid="creation-result-message"
          :data-outcome="result && result.outcome"
        >
          {{ resultMessage }}
        </p>
        <template v-if="stage && stage.stage === 'confirm'">
          <div class="creation-confirm" data-testid="creation-confirm">
            <div class="creation-confirm-title" data-testid="creation-confirm-title">
              {{ stage.confirmLabel }}
            </div>
            <div class="creation-confirm-actions">
              <button
                type="button"
                class="ui-btn ui-btn--primary"
                data-testid="creation-confirm-ok"
                @click="confirmCurrent"
              >
                確認
              </button>
              <button
                type="button"
                class="ui-btn"
                data-testid="creation-confirm-cancel"
                @click="cancelConfirm"
              >
                取消
              </button>
            </div>
          </div>
        </template>
        <template v-else>
          <nav class="ui-tabs creation-overlay__modes" aria-label="建角方式">
            <button
              type="button"
              class="ui-tabs__tab creation-overlay__mode"
              :class="{ 'is-active': mode === 'preset' }"
              :aria-pressed="mode === 'preset'"
              data-testid="creation-mode-preset"
              @click="setMode('preset')"
            >
              預設
            </button>
            <button
              type="button"
              class="ui-tabs__tab creation-overlay__mode"
              :class="{ 'is-active': mode === 'custom' }"
              :aria-pressed="mode === 'custom'"
              data-testid="creation-mode-custom"
              @click="setMode('custom')"
            >
              自訂
            </button>
            <button
              type="button"
              class="ui-tabs__tab creation-overlay__mode"
              :class="{ 'is-active': mode === 'concept' }"
              :aria-pressed="mode === 'concept'"
              data-testid="creation-mode-concept"
              @click="setMode('concept')"
            >
              概念
            </button>
          </nav>

        <div v-if="mode === 'preset'" class="creation-overlay__presets">
          <button
            v-for="card in presets"
            :key="card.key"
            type="button"
            class="creation-preset-card"
            data-testid="creation-preset-card"
            :data-preset-key="card.key"
            :data-selected="selectedPresetKey === card.key ? 'true' : 'false'"
            @click="selectPreset(card)"
          >
            <span class="creation-preset-card__name" data-testid="creation-preset-name">
              {{ card.display_name }}
            </span>
            <span class="creation-preset-card__race">{{ card.race }}</span>
            <span class="creation-preset-card__emphasis">{{ card.emphasis }}</span>
            <span class="creation-preset-card__background">{{ card.background }}</span>
          </button>
          <p v-if="formMessage" class="creation-form-message" data-testid="creation-form-message">{{ formMessage }}</p>
        </div>

        <div v-else-if="mode === 'custom'" class="creation-overlay__custom">
          <p v-if="reviewPrompt" class="creation-proposal-review" role="status" data-testid="creation-proposal-review">
            {{ reviewPrompt }}
          </p>
          <p
            v-if="budgetBriefing"
            class="creation-budget-briefing"
            data-testid="creation-budget-briefing"
          >
            {{ budgetBriefing }}
          </p>

          <div class="creation-overlay__field">
            <label class="creation-overlay__name-line" for="creation-name-input">
              <span>名稱</span>
              <span class="creation-overlay__name-row">
                <input
                  id="creation-name-input"
                  type="text"
                  data-testid="creation-field-displayName"
                  :minlength="custom?.name?.min_length ?? 1"
                  :maxlength="custom?.name?.max_length ?? 64"
                  v-model="name"
                />
                <button
                  type="button"
                  class="creation-roll-button"
                  data-testid="creation-roll-name"
                  aria-label="擲名"
                  :disabled="rollDisabled"
                  @click="rollName"
                >
                  🎲
                </button>
              </span>
            </label>
          </div>

          <label class="creation-overlay__field">
            <span>性別</span>
            <select data-testid="creation-sex" v-model="sex">
              <option v-for="option in sexOptions" :key="option.key" :value="option.key">{{ option.label }}</option>
            </select>
          </label>

          <label class="creation-overlay__field">
            <span>年齡</span>
            <input type="number" data-testid="creation-field-age" :min="minimumAge" v-model.number="age" />
          </label>
          <label class="creation-overlay__field">
            <span>外觀年齡</span>
            <input type="number" data-testid="creation-field-apparentAge" :min="minimumApparentAge" v-model.number="apparentAge" />
          </label>

          <label class="creation-overlay__field">
            <span>種族</span>
            <select v-model="race" data-testid="creation-race" @change="onRaceChange">
              <option v-for="r in races" :key="r.key" :value="r.key">{{ r.key }}</option>
            </select>
          </label>
          <p v-if="raceInfo?.description" class="creation-race-description" data-testid="creation-race-description">
            {{ raceInfo.description }}
          </p>

          <label v-if="hasSubraces" class="creation-overlay__field">
            <span>血統</span>
            <select v-model="subrace" data-testid="creation-subrace">
              <option v-for="o in subraceOptions" :key="o.key" :value="o.key">{{ o.label }}</option>
            </select>
          </label>

          <div class="creation-allocations">
            <label v-for="ax in currentProfile?.axes" :key="ax.axis" class="creation-overlay__field">
              <span>{{ ax.label }}（{{ ax.explanation }}）</span>
              <input
                type="number"
                :min="ax.minimum"
                :max="ax.maximum"
                v-model.number="allocations[ax.axis]"
                :data-testid="`creation-field-${ax.axis}`"
              />
            </label>
          </div>
           <p v-if="currentProfile" class="creation-allocation-total" data-testid="creation-allocation-total">
             已配置點數：{{ allocationTotal }} / {{ currentProfile.budget }}
           </p>

          <fieldset v-if="affinityMax > 0" class="creation-affinity" data-testid="creation-affinity">
            <legend>元素親和（上限 {{ affinityMax }}）</legend>
            <label v-for="el in affinityElements" :key="el.key" class="creation-affinity-item">
              <input
                type="checkbox"
                :checked="affinitySelected.has(el.key)"
                :disabled="!affinitySelected.has(el.key) && affinitySelected.size >= affinityMax"
                :data-testid="`creation-affinity-${el.key}`"
                @change="toggleAffinity(el.key)"
              />
              <span>{{ el.label }}</span>
            </label>
          </fieldset>

          <label class="creation-overlay__field">
            <span>背景（可選）</span>
            <textarea data-testid="creation-background" rows="3" v-model="background"></textarea>
          </label>

          <label class="creation-overlay__field">
            <span>個性</span>
            <textarea
              data-testid="creation-persona-personality"
              rows="3"
              maxlength="600"
              v-model="persona.personality"
            ></textarea>
          </label>
          <label class="creation-overlay__field">
            <span>生平</span>
            <textarea
              data-testid="creation-persona-life_story"
              rows="3"
              maxlength="600"
              v-model="persona.life_story"
            ></textarea>
          </label>
          <label class="creation-overlay__field">
            <span>習慣</span>
            <textarea
              data-testid="creation-persona-habit"
              rows="3"
              maxlength="600"
              v-model="persona.habit"
            ></textarea>
          </label>

          <p v-if="formMessage" class="creation-form-message" data-testid="creation-form-message">{{ formMessage }}</p>
        </div>

        <div v-else class="creation-overlay__concept">
          <label class="creation-overlay__field">
            <span>角色概念</span>
            <textarea
              data-testid="creation-field-concept"
              rows="4"
              :disabled="conceptPending"
              v-model="conceptText"
            ></textarea>
          </label>
          <div
            v-if="conceptPending"
            class="creation-concept-loading"
            role="status"
            data-testid="creation-concept-loading"
          >
            <span class="creation-concept-spinner" aria-hidden="true"></span>
            <p class="creation-concept-loading-text">概念生成中，請稍候…</p>
          </div>
        </div>

        <!-- One action bar for the whole wizard (never a bare stretched
             button inside the form column): the destructive reset sits at the
             leading edge, the mode's single decisive action at the trailing
             edge, and the bar sticks to the bottom of the scrolling body so
             the primary action is reachable from any scroll position. -->
        <footer class="creation-overlay__footer">
          <button
            type="button"
            class="ui-btn ui-btn--danger creation-reset"
            data-testid="creation-reset"
            @click="requestReset"
          >
            重設
          </button>
          <button
            v-if="mode === 'custom'"
            type="button"
            class="ui-btn ui-btn--primary creation-custom-confirm"
            data-testid="creation-submit"
            @click="confirmCustom"
          >
            確認自訂
          </button>
          <button
            v-else-if="mode === 'concept'"
            type="button"
            class="ui-btn ui-btn--primary creation-concept-apply"
            data-testid="creation-concept-submit"
            :disabled="applyFrozen"
            @click="applyConcept"
          >
            {{ conceptPending ? "生成中…" : "套用概念" }}
          </button>
        </footer>
        </template>
      </template>

      <p v-else class="creation-unavailable-reason" data-testid="creation-unavailable-reason">
        {{ reason }}
      </p>
    </div>
  </section>
</template>

<style scoped>
.creation-overlay {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: flex;
  flex-direction: column;
  background: var(--ink-950);
  color: var(--paper-100);
  font-family: var(--f-sans);
}

.creation-overlay__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-4) var(--sp-6);
  border-bottom: var(--line);
}

.creation-overlay__title {
  margin: 0;
  color: var(--paper-50);
  font-family: var(--f-display);
  font-size: 20px;
}

/* Chrome and controls come from the shared control layer in styles/tokens.css
   (`.ui-btn`, `.ui-tabs`); the rules below add only layout. */

.creation-overlay__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-4) var(--sp-6);
  overflow: auto;
}

/* The display-name row pairs the input with the dice button (🎲) at its
   right; the gender select rides directly below the name field. */
.creation-overlay__name-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.creation-overlay__name-line {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.creation-roll-button {
  flex: none;
  line-height: 1;
}

/* The mode switch is the shared segmented tray (`.ui-tabs`); it only needs to
   stop stretching inside the body's flex column. */
.creation-overlay__modes {
  flex: none;
  overflow-x: auto;
}

.creation-overlay__presets {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--sp-3);
}

.creation-preset-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  box-sizing: border-box;
  padding: var(--sp-3);
  color: var(--paper-100);
  background: var(--ink-860);
  border: var(--line);
  border-left: 3px solid var(--seal-500);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
}

.creation-preset-card[data-selected="true"] {
  border-color: var(--seal-500);
  box-shadow: 0 0 0 2px var(--seal-glow);
}

.creation-preset-card__name {
  color: var(--paper-50);
  font-family: var(--f-display);
  font-size: var(--text-body);
}

.creation-preset-card__race {
  color: var(--paper-500);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

.creation-preset-card__emphasis {
  color: var(--gold-400);
}

.creation-preset-card__background {
  color: var(--paper-300);
}

.creation-overlay__custom,
.creation-overlay__concept {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.creation-budget-briefing {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-300);
  background: var(--panel-hi);
  border: 1px dashed var(--warn);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

.creation-overlay__field {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  color: var(--paper-300);
  font-size: var(--text-sm);
}

.creation-overlay__field input,
.creation-overlay__field select,
.creation-overlay__field textarea {
  color: var(--paper-100);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-1) var(--sp-2);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
}

.creation-allocations {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-2);
}

.creation-allocation-total {
  margin: 0;
  color: var(--paper-300);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

.creation-affinity {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.creation-affinity legend {
  color: var(--paper-500);
}

.creation-affinity-item {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  color: var(--paper-300);
}

.creation-result-message,
.creation-form-message {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--seal-400);
  background: var(--panel-hi);
  border: 1px solid var(--seal-500);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.creation-concept-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-5) 0;
}

.creation-concept-spinner {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 4px solid var(--line);
  border-top-color: var(--gold-400);
  animation: concept-spin 0.9s linear infinite;
}

@keyframes concept-spin {
  to {
    transform: rotate(360deg);
  }
}

.creation-concept-loading-text {
  margin: 0;
  color: var(--paper-300);
  font-size: var(--text-sm);
}


/* The sticky action bar: pulled out to the body's padding edges so it reads
   as a bar, and pinned to the bottom of the scroll box. `margin-top: auto`
   keeps it at the foot of a short form instead of floating mid-panel. */
.creation-overlay__footer {
  position: sticky;
  bottom: calc(-1 * var(--sp-4));
  z-index: 1;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: auto calc(-1 * var(--sp-6)) calc(-1 * var(--sp-4));
  padding: var(--sp-3) var(--sp-6);
  background: var(--ink-900);
  border-top: var(--line);
}

/* The decisive action sits at the trailing edge, opposite the reset. */
.creation-overlay__footer .ui-btn--primary {
  margin-left: auto;
}

.creation-confirm {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  padding: var(--sp-4);
  border: 1px solid var(--warn);
  border-radius: var(--radius-md);
  background: var(--panel-hi);
}

.creation-confirm-title {
  margin: 0;
  color: var(--paper-50);
  font-size: var(--text-lg);
}

.creation-confirm-actions {
  display: flex;
  gap: var(--sp-2);
}


.creation-unavailable-reason {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-300);
  background: var(--panel-hi);
  border: 1px dashed var(--warn);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}
</style>
