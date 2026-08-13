## Context

World lore (`tmp/story_settings/world_info.md`, not committed) states 神之秘法 requires 神性,
possessed only by the three elf subraces, and costs "精神力" rather than mana. Per D7 of the approved
design doc, this round explicitly does not build a 精神力 resource — mechanized mysteries are free-cost
ACTIVE skills gated purely by race. 悠奈's character data (`tmp/story_settings/character/
YunaDarknight.md`) explicitly lists both 性魔法主宰 and 神之秘法：性愛系統 as distinct owned skills.

**Correction to the approved design doc**: §6 assumed a new `RaceProfile` field would be needed for
race-gating. While writing this proposal, `RACE_REGISTRY`'s existing `can_use_divine_arts` field
(landed under `lore-registries`, already `True` only for `"elf"`) was found to already provide exactly
this fact. This proposal reuses it and adds no new `RaceProfile` field — a scope reduction from the
design doc, not a deviation from its intent.

## Goals / Non-Goals

**Goals:**
- `divine_sexual_arts` is castable, race-gated, free-cost, and reuses the existing rule-driven
  `sexual_transitions.py` engine rather than inventing a new one.
- The four unmechanized mysteries are declared, race-gated content — not silently missing, not
  secretly mechanized.

(`reincarnation_boon_yuna`'s malformed effect string is fixed by `skill-effects-typed-model`, not this
change — moved there during rubber-duck review so the batch's universal prerequisite is self-consistent
on its own.)

**Non-Goals:**
- No 精神力 resource (D7, unchanged from the approved design).
- No mechanization of 時間加速/減速, 空間扭曲, 物質轉換, 生命延續 — each implies its own subsystem
  (tick-rate manipulation, teleport/permission system, item generation, aging/death model) not built by
  this or any other proposal in this batch.
- `divine_sexual_mastery` does **not** gate `divine_sexual_arts`'s castability in this pass —
  `divine_sexual_arts` is directly ownable and its only gate is `can_use_divine_arts`. Making
  `divine_sexual_mastery` a hard prerequisite would require a `SexualMasteryEffect`-based cast-gate
  mechanism mirroring `can_cast_spell_tier`, which is unwarranted complexity for a single skill (unlike
  the eight-element, eighty-spell case `can_cast_spell_tier` exists to serve). `divine_sexual_mastery`
  is flavor/title content for this round, structurally ready for a future gate if the 性魔法 skill
  family grows.

## Decisions

- **`SexualMasteryEffect` is its own effect class, not a parameterized `ElementMasteryEffect`.** 性魔法
  is explicitly not one of the eight canonical elements (`ELEMENT_REGISTRY` has no "sexual" entry, and
  should not gain one just to shoehorn this in) — giving it a distinct class keeps `ElementMasteryEffect`
  honestly scoped to the `ELEMENT_REGISTRY` domain.
- **Race-gating via the existing `RaceProfile.can_use_divine_arts` field**, not a hardcoded race-name
  check scattered at each divine-mystery skill's cast site — this field already exists for exactly this
  purpose (`lore-registries` spec, "Only elves can use divine arts"), so this change is purely a
  consumer of it, adding no new lore-registry surface.
- **Which skills are gated is declared per-skill via `SkillDef.requires_divine_arts`**, not inferred
  from effect prefixes: the six 神之秘法 skills set the flag, while the generic `sexual_event`
  mechanism stays race-neutral so a future non-divine sexual skill is not silently made elf-only.
  Rubber-duck review caught that an effect-family predicate including `sexual_event` would have
  changed the generic mechanism's contract; the explicit marker keeps the gate data-driven.
- **`divine_sexual_arts` reuses `sexual_event:<name>` targeting other entities.** `apply_event` (in
  `world/rules/sexual_transitions.py`) already supports an arbitrary target and arbitrary event name
  via its rule-table lookup — no new targeting mechanism needed, only new rule rows for whatever
  specific event name(s) this skill triggers, which is a data-authoring task, not an architecture
  decision.

## Risks / Trade-offs

- [Risk] `divine_sexual_arts`'s exact `sexual_event` name(s) and their rule-table effects are not fully
  specified by the approved design doc (it only says the skill "routes to" the existing engine).
  → Mitigation: task list requires reading `world/rules/rulebook/`'s existing sexual-transition rule
  data before authoring new rows, to reuse existing event vocabulary where one already fits rather than
  inventing a parallel one.
- [Risk] Four inert flavor-only skills could be mistaken for "not implemented yet" bugs by a future
  contributor. → Mitigation: `DivineMysteryEffect(mechanized=False)` is a structurally distinct,
  explicitly-named state (per `skill-effects-typed-model`'s D1 precedent for `FlavorEffect`), not a
  missing entry — self-documenting in the type itself.

## Migration Plan

No data migration. Lands after `skill-effects-typed-model`; independent of every other mechanism
change in this batch (only shares the foundation dependency).

## Open Questions

None.
