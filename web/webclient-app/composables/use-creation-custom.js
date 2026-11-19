// The custom-form descriptor derivations, the point-buy briefing, the local
// validation gates and the custom submit builder (extracted verbatim from
// CreationOverlay.vue so the SFC stays a passive renderer): everything derived
// from the server-owned `custom` descriptor plus the form-message /
// result-message presentation surfaces. Registers no watchers (order-neutral).
import { computed, ref } from "vue";

// The same stable fallback line the store uses for a recognized non-success
// result with no usable message (webclient-action-result-feedback D-D); the
// overlay is the presenting surface in creation mode, so the fallback must
// exist here too. Kept byte-identical to the store constant, pinned by
// tests/overlays/creation_overlay.test.js.
const ACTION_RESULT_FALLBACK_MESSAGE = "動作未生效，請重試或返回上層。";

// Every allocation point range in the custom form reads `low~high`.
export function formatPointRange(low, high) {
  return `${low}~${high}`;
}

export function useCreationCustom(props, form, emit) {
  const {
    custom,
    race,
    subrace,
    allocations,
    name,
    age,
    apparentAge,
    background,
    sex,
    SEX_DEFAULT_KEY,
    affinitySelected,
    persona,
    personaFilled,
  } = form;

  const minimumAge = computed(() => custom.value?.age?.age_minimum ?? 0);
  const minimumApparentAge = computed(() => custom.value?.age?.apparent_age_minimum ?? 0);

  const races = computed(() => (Array.isArray(custom.value?.races) ? custom.value.races : []));

  function raceDisplayName(raceKey) {
    const found = races.value.find((r) => r.key === raceKey);
    return found?.display_name_zh ?? raceKey;
  }

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
  // allocation inputs, state the profile budget, each axis's
  // zero-through-point-cap range, every conversion that is not one point per
  // stat unit, and the rule that the total must equal the budget.
  const allocationTotal = computed(() =>
    Object.values(allocations).reduce((sum, value) => sum + (Number(value) || 0), 0));
  const budgetBriefing = computed(() => {
    const profile = currentProfile.value;
    if (!profile) return "";
    const ranges = profile.axes.map((a) => `${a.label} ${formatPointRange(0, a.point_cap)}`).join(" ‧ ");
    const conversions = profile.axes
      .filter((a) => a.point_cap > 0 && a.value_at_cap - a.minimum !== a.point_cap)
      .map((a) => `${a.label} ${a.point_cap} 點換算為 ${a.value_at_cap}（起點 ${a.minimum}）`);
    const conversionText = conversions.length ? `｜${conversions.join(" ‧ ")}` : "";
    return `點數額度 ${profile.budget}｜${ranges}｜總和須等於額度 ${profile.budget}${conversionText}`;
  });

  // The pre-modifier starting value each allocation yields, from the server's
  // own point policy and the same half-up conversion activation applies.
  // BigInt intermediates keep the ratio exact; results stay safe integers.
  function previewValue(axis, points) {
    const cap = axis.point_cap;
    if (cap === 0) return axis.minimum;
    const spent = Math.min(cap, Math.max(0, Number.isInteger(points) ? points : 0));
    const two = BigInt(2);
    const scaled = two * BigInt(axis.value_at_cap - axis.minimum) * BigInt(spent) + BigInt(cap);
    return axis.minimum + Number(scaled / (two * BigInt(cap)));
  }
  const allocationPreview = computed(() => {
    const profile = currentProfile.value;
    if (!profile) return [];
    return profile.axes.map((axis) => ({
      axis: axis.axis,
      label: axis.label,
      point_cap: axis.point_cap,
      value: previewValue(axis, Number(allocations[axis.axis])),
    }));
  });

  // The age bounds gate (design D1): reject when EITHER age field is below the
  // descriptor's minimum — the server stays authoritative.
  const ageMeetsMinimum = computed(() => Number(age.value) >= minimumAge.value);
  const apparentMeetsMinimum = computed(() => Number(apparentAge.value) >= minimumApparentAge.value);
  const gatePassed = computed(() => ageMeetsMinimum.value && apparentMeetsMinimum.value);
  const gateError = ref(false);
  const budgetError = ref(false);
  const capError = ref(null);
  const subraceError = ref(false);
  const personaError = ref(false);
  // The field identifiers (use-creation-steps.js FIELD_STEP keys) the gate
  // that set the active error points at: structured presentation data for the
  // step rail and focus routing, so nothing ever parses `formMessage`. Written
  // only beside the flags below; the stepped form drops entries once the
  // player edits that step, and a fresh proposal fill clears them.
  const formErrorFields = ref([]);

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
    if (capError.value) return capError.value;
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
    clearZeroCapAllocations();
  }

  // A user-driven profile change zeroes the new profile's zero-cap axes so they
  // lock at once. Draft sync and proposal fill never call this.
  function clearZeroCapAllocations() {
    const profile = currentProfile.value;
    if (!profile) return;
    for (const axis of profile.axes) {
      if (axis.point_cap === 0) allocations[axis.axis] = 0;
    }
  }

  function onSubraceChange() {
    clearZeroCapAllocations();
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
    capError.value = null;
    subraceError.value = false;
    personaError.value = false;
    formErrorFields.value = [];
    if (!gatePassed.value) {
      gateError.value = true;
      formErrorFields.value = [
        ...(ageMeetsMinimum.value ? [] : ["age"]),
        ...(apparentMeetsMinimum.value ? [] : ["apparent_age"]),
      ];
      return;
    }
    if (hasSubraces.value && !subrace.value) {
      subraceError.value = true;
      formErrorFields.value = ["subrace"];
      return;
    }
    const profile = currentProfile.value;
    if (profile) {
      const outOfCap = profile.axes.find((axis) => {
        const value = Number(allocations[axis.axis]);
        return !Number.isInteger(value) || value < 0 || value > axis.point_cap;
      });
      if (outOfCap) {
        // A point value outside the server-declared cap is rejected here with
        // its own field; the server revalidates the exact budget anyway.
        capError.value = `${outOfCap.label} 配點需為 ${formatPointRange(0, outOfCap.point_cap)} 的整數`;
        formErrorFields.value = [`allocations.${outOfCap.axis}`];
        return;
      }
    }
    if (profile && allocationTotal.value !== profile.budget) {
      budgetError.value = true;
      // The budget is a sum, so the error lands on the first displayed axis
      // that can take points (a locked zero-cap field cannot take focus).
      const target = profile.axes?.find((axis) => axis.point_cap > 0) ?? profile.axes?.[0];
      formErrorFields.value = target ? [`allocations.${target.axis}`] : [];
      return;
    }
    // Persona local validation is all-empty-or-all-filled (design D5): a
    // partially-filled triple blocks submission with a localized reason.
    const filled = personaFilled();
    if (filled !== 0 && filled !== 3) {
      personaError.value = true;
      // The partial triple lands on its first empty textarea.
      const empty = ["personality", "life_story", "habit"].find((key) => persona[key].trim() === "");
      formErrorFields.value = empty ? [`persona.${empty}`] : [];
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

  return {
    minimumAge,
    minimumApparentAge,
    races,
    raceDisplayName,
    raceInfo,
    hasSubraces,
    sexOptions,
    subraceOptions,
    affinity,
    affinityMax,
    affinityElements,
    currentProfile,
    allocationTotal,
    budgetBriefing,
    allocationPreview,
    gatePassed,
    formMessage,
    formErrorFields,
    resultMessage,
    onRaceChange,
    onSubraceChange,
    toggleAffinity,
    confirmCustom,
  };
}
