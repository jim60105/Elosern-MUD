# blueprint-portrait-policy Design

## Context

The ScenarioDirector produces AI quest blueprints (`world/ai/scenario_director.py::QuestBlueprint`)
whose stages carry `npc_reqs` entries (`BlueprintNpcReq`: role, tier, disposition). `BlueprintNpcReq`
enforces immutability by construction (`_reject_mutable_containers` rejects any nested dict/list),
and `QuestBlueprint.to_payload()` / `from_payload()` serialize only role, tier, and disposition —
so a portrait field must be a frozen value object and every serialization path must carry it.
The SceneBuilder (`world/quests/scene_builder.py`) materializes those requirements into rooms and
occupants, and the art pipeline schedules a unique portrait for any occupant carrying
`{"mode": "named", "stable_key": ...}` in `db.portrait_policy` — the seam shipped by `art-assets`.
The deterministic compile boundary (`world/quests/compile.py::compile_quest_blueprint`, invoked by
the composition root `server/ai_director_service.py`) re-validates the payload and builds
`StageSpawnRequirement`; `world/quests` never imports `world/ai`, and `world/ai` does not import
`world/quests` today.

The focused design (`2026-08-09-generated-named-portraits-design.md`) adds optional per-occupant
characterization to the blueprint: `display_name`, paired `age`/`apparent_age`, and
`portrait: {stable_key}`. The generative layer authors these like speech; deterministic validation
bounds them; the adult gate stays code-level.

This change delivers the proposal/compile half: blueprint shape, validation, serialization, and
carry-through. The spawn application (writing the attributes, exercising the portrait seam end to
end) is the follow-up `spawn-named-portraits` change.

Constraints that shaped this design:

- No module under `world/ai/` writes state; blueprint validation is a pure function.
- `world/quests/compile.py` must not import from `world/ai/`; the deterministic compile boundary
  re-validates the payload, so validation rules must live where both layers can reach them.
- Balance/lore constants are never copied: the age upper bound comes from
  `RACE_REGISTRY[race].lifespan`, reached through `NPC_TIER_REGISTRY[tier].race_key`.
- The adult floor (18) is a hard invariant; it applies to both `age` and `apparent_age`, in
  addition to the art-side `adult-portrait-gate` re-check at enqueue.
- All `NPC_TIER_REGISTRY` entries are human today; the elf lifespan band (800–1200) is only
  reachable in tests if shipped content includes an elven tier.

## Goals / Non-Goals

**Goals:**

- Blueprint `npc_req` entries may declare `display_name`, `age`/`apparent_age`, and a named
  portrait `stable_key`.
- Every declared field survives the full blueprint lifecycle: output schema, `to_payload()`,
  `from_payload()`, canonical digest serialization, and the compiled spawn requirements.
- Every declared field is validated at the proposal boundary (world/ai) and again at the compile
  boundary (world/quests), with one shared rule source.
- Hand-written template quests can carry the same fields so offline quests are not second-class.
- Existing blueprints without the new fields compile exactly as today.

**Non-Goals:**

- Spawn-side application (`db.portrait_policy`, `db.age`, `db.display_name` writes) — the
  `spawn-named-portraits` change.
- Portrait description authorship by the LLM — descriptions stay deterministic.
- Any change to `QuestDefinition` (the runtime registry) — hand-written runtime definitions keep
  their current shape.
- Age affecting dialogue, persona, or look rendering — portrait description and canonical
  attributes only (future changes own the rest).

## Decisions

### D1: A frozen `BlueprintPortrait` value object; characterization lives on `BlueprintNpcReq`

`BlueprintNpcReq` gains `display_name: str | None`, `age: int | None`, `apparent_age: int | None`,
and `portrait: BlueprintPortrait | None`, where `BlueprintPortrait` is a frozen dataclass with
exactly one field, `stable_key: str`. A frozen dataclass passes `_reject_mutable_containers` (the
guard traverses dataclass fields, rejecting only dict/list), so immutability-by-construction is
preserved. Characterization is per-occupant because one `npc_req` entry spawns one NPC; a
quest-level block would force every occupant to share a name and age.

Alternatives considered: a raw dict `portrait` field (rejected: violates the immutability guard);
a quest-level `characterization` block (rejected: per-occupant granularity lost); folding ages
into the portrait object (rejected: `age`/`apparent_age` are character data that future features —
dialogue persona, schedule — consume independently of portraits).

### D2: The portrait policy shape reuses the art contract exactly

`portrait.stable_key` means `mode == "named"` at spawn; there is no `mode` field in the blueprint.
`character_subject_for()` already requires `{"mode": "named", "stable_key": ...}` on the entity, so
the spawn side materializes the full dict. The blueprint stays minimal and the art-side subject
rules (non-empty, no colon, no control characters, bounded) are the validation target.

Alternatives considered: carrying `mode` in the blueprint (rejected: one mode exists today; a
future `generic` mode can be added as a whitelist value later).

### D3: One shared validation helper under `world/quests/`, imported read-only by `world/ai`

The age bound must be checked both when the scenario director validates a proposed blueprint and
when the compiler validates the accepted blueprint payload. `world/quests/compile.py` cannot
import `world/ai`; the rule source must be importable from both sides. The helper lives under
`world/quests/` (the deterministic side owns the bound), is a pure function taking the raw values
plus the resolved race-lifespan bound, and is imported by the scenario director read-only — the
same read-only direction `world/ai` already uses for `world/lore` registries. No cycle exists:
`world/quests` never imports `world/ai`, and the helper imports no state-mutating API.

The helper validates with `type(value) is int` (booleans and `None` reject, matching the art
gate's check in `world/art/adult.py`), distinguishes a missing key from a key whose value is
`None`, and rejects a `portrait` that is not a mapping or carries any key other than exactly one
`stable_key`.

Alternatives considered: duplicating the rules in `world/ai` and `world/quests` (rejected: drift
risk is exactly what the mirror-validation pattern exists to prevent); putting the helper in
`world/lore` (rejected: the rules are blueprint-contract rules, not immutable world data).

### D4: The adult floor is a constant; the upper bound is registry data; an elven tier ships

`18` is the project's non-negotiable adult invariant and stays a named constant in the shared
helper. The upper bound comes from `RaceProfile.lifespan` — human 80, beastfolk 70, elf 1200 — read
through the tier's `race_key`, never copied into Python. Because every existing `NPC_TIER_REGISTRY`
entry is human, this change adds one elven NPC tier (`elven_civilian`: elf / `elf_common`, a real
static tier that already exists for the elf race) so the race-band validation is exercised by
shipped content, and the focused design's elf scenarios are testable end to end.

Alternatives considered: an elf-specific hard cap (rejected: contradicts the lore registry — the
design session caught this exact error); fixture-only elf scenarios (rejected: the scenario
director resolves tiers through the shipped registry, so shipped content is the honest test bed).

### D5: Absent fields are fully backward compatible

All four fields are optional. A blueprint without them validates, serializes, digests, and compiles
to exactly the shapes it produces today; the spawn side keeps its no-policy behavior. The
carry-through extends `StageSpawnRequirement`'s per-occupant requirement with an optional frozen
characterization value; existing consumers unpack the original fields unchanged.

### D6: Duplicate `stable_key` within one blueprint must carry identical characterization

Two `npc_req` entries sharing a `stable_key` in the same blueprint SHALL declare the same
`display_name` and ages; conflicting characterization under the same key is a blueprint error and
rejects. Across quests, the shared key resolves to one asset whose description is set by the first
materialization (first-writer-wins, the existing queue behavior) — documented, not silently
"last wins". This keeps the portrait key an identity rather than an accident.

### D7: The anti-hallucination number ban narrows to mechanical values

The main spec's "the proposal never chooses numbers, stats, or class lineage" requirement
(`openspec/specs/scene-builder/spec.md`) is amended in this change: the ban covers mechanical and
balance values (numeric stats, rewards, bands, typeclass paths). Validated characterization ages
(`age`/`apparent_age`) are authored content like speech, bounded by the adult floor and the race
lifespan, and are explicitly excluded from the ban. The SceneBuilder still derives every stored
numeric stat deterministically from the lore tables.

### D8: The template pool gets the same surface

`director_templates.py` may declare the fields on its `npc_reqs` entries; validation is the same.
This keeps deterministic offline quests able to spawn named characters, which the follow-up change
needs for its integration tests without the LLM.

## Risks / Trade-offs

- [Validation drift between proposal and compile] → Single shared helper (D3) is the only rule
  source; both layers call it; a repository test asserts both call sites exist and no duplicate
  inline checks were introduced.
- [Field loss in blueprint round-trips] → D1 + a round-trip test: `from_payload(to_payload(b))`
  preserves the four fields; the output jsonschema declares them; the digest serialization
  includes them so equal-content/different-content keys stay correct.
- [The LLM invents names or ages that break story tone] → Same trust model as speech: format and
  bounds are enforced; tone is authored content. The adult gate and lifespan bounds are
  mechanical backstops.
- [Age bound edge: `apparent_age` differs from `age`] → The paired-fields shape allows divergence;
  this change validates both independently; a future change may add a divergence policy.
- [Scope creep into spawn behavior] → Explicitly non-goaled; the spawn write and portrait
  end-to-end tests belong to `spawn-named-portraits`.

## Open Questions

- None blocking. Whether the portrait key should ever be namespaced by quest key (e.g. to force
  per-quest uniqueness) is a future balance decision; the shared-key-reuses-portrait behavior is
  intended for now.
