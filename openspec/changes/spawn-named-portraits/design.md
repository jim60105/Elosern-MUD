# spawn-named-portraits Design

## Context

`blueprint-portrait-policy` delivered the blueprint surface, the lifecycle carry-through, and the
compile boundary: `StageSpawnRequirement` now exposes optional `display_name`, paired
`age`/`apparent_age`, and a named-portrait `stable_key` per `npc_req` entry, validated through a
shared helper; the digest distinguishes scenes by characterization. The SceneBuilder
(`world/quests/scene_builder.py`) still ignores them: `_spawn_npc` builds an NPC from
`NPC_TIER_REGISTRY[tier]` (race, static tier, magic start) and never sets a display name, ages, or
a portrait policy. Every spawned occupant therefore falls through `_schedule_occupant_portraits`
unconditionally — the seam shipped by `art-assets` has no producer.

The art side needs nothing new: `character_subject_for()` derives the subject from
`db.portrait_policy`; `character_description(entity, age)` builds the adult-safe description from
display name, race label, and the age; `world/art/adult.py` re-checks `age`/`apparent_age >= 18`
immediately before enqueue (using `type(value) is int`, missing values reject); the internal
sd-webui client renders the prompt from that description alone (no LLM elaboration stage exists in
the pipeline). The adult gate is a hard floor: values 18..1200 are valid for an elf, so a
portrait-bearing elven occupant with the baseline 25 passes.

This change makes the spawn path apply the characterization and proves the whole loop with
integration tests that reach the fake worker.

## Goals / Non-Goals

**Goals:**

- `_spawn_npc` applies display name, canonical adult ages, and the named portrait policy from the
  compiled requirement, with precisely specified per-field behavior.
- Absent ages for a portrait-bearing occupant get a deterministic adult baseline so the gate
  always passes; absent policy keeps today's no-portrait behavior.
- End-to-end coverage: spawn → post-commit ensure → adult gate → fake worker receives an adult,
  story-driven description with the right subject key.
- Template quests (from `blueprint-portrait-policy`) provide the integration fixtures without the
  LLM.

**Non-Goals:**

- Any art-layer code change (subjects, adult gate, queue, worker, presenter).
- Story-driven ages flowing anywhere beyond canonical attributes and the portrait description
  (dialogue, persona, and look are future changes' business).
- Persisting named NPC identity across instance reclamation (the portrait key is the identity
  face; a persistent-identity change is out of scope).

## Decisions

### D1: Per-field application, not all-or-nothing

Each carried field applies independently:

- `display_name` present → `npc.db.display_name` set.
- `age`/`apparent_age` present (always paired by the blueprint contract) → both set.
- `portrait` present → `npc.db.portrait_policy = {"mode": "named", "stable_key": ...}` set, and,
  when ages are absent, `npc.db.age = npc.db.apparent_age = 25` (the baseline) so the adult gate
  has canonical inputs.
- No `portrait` → no policy and no baseline; an occupant with only a name or only ages keeps
  those and remains portrait-less.

This keeps the three input shapes (name-only, ages-only, portrait-only, and combinations)
well-defined instead of leaving the baseline branch to implementer judgment.

### D2: The spawn applies the full policy dict, not a blueprint-shaped fragment

`character_subject_for()` requires exactly `{"mode": "named", "stable_key": ...}`. The spawn writes
that complete dict. The blueprint carries only `stable_key`; the `mode` is materialized here. This
keeps the art contract the single source of truth for policy shape.

### D3: Baseline ages are a deterministic constant, race-agnostic

Absent ages default to 25 for every race. Rationale: the adult floor is the invariant, and the
validation range is adult-floor to lifespan maximum — 25 is valid for every race (18..80 human,
18..1200 elf), so the gate provably passes. A race-aware baseline (e.g. lifespan midpoint) would
make a default elf a thousand-year elder, which contradicts the "young-looking elf" stories a
field-less blueprint may still want.

Alternatives considered: race-aware midpoints (rejected: default-elf-as-elder is a worse default);
no baseline at all (rejected: the adult gate requires canonical ages, so a portrait-bearing
occupant without ages would be permanently rejected).

### D4: Only portrait-bearing occupants receive the baseline

A name-only or ages-only occupant keeps today's portrait-less behavior; only the branch that
materializes a named policy sets the baseline ages (which the portrait description needs).

### D5: The existing seam stays the only scheduling path; shared keys are first-writer-wins

No new scheduling code. `_spawn_npc` sets the attributes; the existing
`_schedule_occupant_portraits` loop picks the occupant up inside the same atomic materialization
and schedules the ensure via `transaction.on_commit`. The `scene-builder` main spec's atomicity
guarantees (rolled-back materialization emits no job) are preserved without touching the loop.
A `stable_key` shared across quests resolves to one asset; the queue does not overwrite a done
record, so the first materialized occupant's description wins — documented, deterministic
behavior.

## Risks / Trade-offs

- [Gate rejection if ages are ever absent for a policy occupant] → The branch always sets the
  baseline before the policy, so the gate's inputs are guaranteed present; a repository test
  asserts the invariant.
- [Shared portrait key across quests collapses distinct characters] → Intended behavior (key is
  identity); first-writer-wins is documented and tested.
- [Baseline 25 surprises a story that wanted a default-age named elf] → The story must declare
  ages; the baseline is a backstop, not an authorial choice. The design doc records this.
- [Integration test flakiness around deferred on_commit] → The test explicitly captures and
  executes commit callbacks (`captureOnCommitCallbacks(execute=True)`) around materialization,
  then drains with the injected fake client; no timing dependence.

## Open Questions

- None blocking. Whether `apparent_age` divergence policy is needed is deferred; the paired-fields
  shape already permits it.
