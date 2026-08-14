## Context

The cast gate lives entirely in `world/rules/progression.py`:
`can_cast_spell_tier(entity, element, tier)` returns `True` when
`entity.traits.magic_level.value >= MAGIC_TIER_THRESHOLDS[tier]` (學徒0/術師16/
大師31/賢者71/主宰91) or when the entity directly owns `<element>_mastery`.
The threshold table deliberately places 主宰 at 91 (> human `magic_cap` 90) so
that "humans can rarely cast 究極 magic" is a mechanical fact. `magic_level`
is a single counter grown by the XP system in the same module; there is no
per-element state anywhere. `Subrace.affinity_elements` exists in
`world/lore/races.py` but has no consumer. Human affinities exist only
implicitly in preset skill kits.

## Goals / Non-Goals

**Goals:**

- Keep exactly one growing `magic_level` counter; XP accumulation, the
  level-up formula, and `magic_rank_title` are untouched.
- Make element affinity mechanical: favored elements unlock tiers earlier,
  non-favored elements later, with the world's fixed five-tier threshold table
  unchanged.
- Preserve current behavior bit-for-bit for any entity that declares no
  affinities (monsters, most NPCs, imports without the field, beastfolk as
  currently registered) — the default multiplier is exactly 1.0.
- Let a human reach 主宰-tier for a favored element (level 83) while
  non-favored elements remain forever below 主宰, keeping the "究極 almost
  impossible" lore intact via both the gate and the MP-cost tiering.
- Declare affinities through the three existing identity channels: player
  presets, custom creation, and character import. Elves inherit them from
  their chosen subrace.
- Race-bounded custom creation counts: **human ≤ 2, beastfolk ≤ 1, elf from
  the subrace seed (not player-chosen)**.

**Non-Goals:**

- No per-element XP pools, no per-element magic levels, no per-element
  thresholds (each would break the "one number" model).
- No affinity effect on spell damage/power or on `effective_value("magic_level")`
  (a future per-element power axis may build on the same data).
- No in-game learning of new spells/skills.
- No change to mastery override semantics (direct ownership stays a binary
  override; conferred grants still never satisfy it).

## Decisions

### D1. Affinity is a multiplicative effective-level derivation

`can_cast_spell_tier` compares `floor(magic_level.value ×
element_affinity_multiplier(entity, element))` against the fixed thresholds.
Rationale: monotonic in `magic_level`, tier-consistent (passing a higher tier
implies passing every lower tier), continuous, and zero new state. The
derivation is a pure read, so the single-writer boundary is untouched.

Alternatives considered:
- Per-element threshold tables: flexible but a matrix of magic numbers that
  drift out of sync; rejected.
- Per-element XP pools: real per-element levels, but breaks the "one number"
  requirement and adds write paths in `world/rules/progression`; rejected.

### D2. Three multiplier outcomes, defaulting to 1.0

`element_affinity_multiplier(entity, element)` returns:
- `1.1` when `element` is in `entity.db.affinity_elements`;
- `0.9` when `entity.db.affinity_elements` is non-empty and `element` is not
  in it;
- `1.0` when `entity.db.affinity_elements` is empty/absent.

The 1.0 default is the load-bearing compatibility property: every existing
spec scenario and test that builds an entity without affinities keeps its
exact current behavior, so this change needs no rewrites of unrelated tests.
Human results under 1.1/0.9: 學徒0, 術師15/18, 大師29/35, 賢者65/79, 主宰
83/never.

### D3. `affinity_elements` is one validated per-entity attribute

A single attribute `entity.db.affinity_elements: list[str]` holds lowercase,
de-duplicated, registry-valid element keys. All identity channels write the
same attribute so the gate query has exactly one source of truth. Subrace
`affinity_elements` becomes the *seed* for elves at activation, not a live
fallback — there is no dual source.

Validation rules (shared by custom creation and import): every key must exist
in `ELEMENT_REGISTRY`, no duplicates, and the count must respect the
channel/race bound. Subrace seeds may exceed the custom-mode bound (eolas
seeds all eight); the bound applies to player input and to human/beastfolk
import input, while elf import input is rejected entirely (the elf set is
always the subrace seed). The race-dependent input bound is expressed by
exactly one deterministic mapping, `max_affinity_elements(race_key)` (`human`
→ 2, `beastfolk` → 1, `elf` → 0), from which the WebClient descriptor and the
validation code both derive their numbers so the layers cannot drift.

**Elf authority.** For elves the subrace is the sole affinity authority in
every channel: custom mode rejects any player-supplied set, an elf preset
SHALL declare an empty set (validated at registry load), an elf import record
SHALL NOT supply a set (rejected semantically), and the loader/activation
seeds the elf's `affinity_elements` from `SUBRACE_REGISTRY[subrace]`. This
removes the ambiguity where an elf preset or import could contradict its
subrace (e.g. a fionnen elf declaring `wind`). The subrace seed itself is
validated (keys exist, no duplicates) at registry load.

### D4. Custom-creation affinity is race-bounded

- **Human**: player picks 0–2 elements.
- **Beastfolk**: player picks 0–1 element.
- **Elf**: affinity is taken from `SUBRACE_REGISTRY[subrace].affinity_elements`
  (fionnen → `light`, ciaran → `fire,dark`, eolas → all eight); no player pick
  is collected for elves, keeping the subrace the affinity authority.

Rationale: humans currently have no subrace-level affinity identity, so a
player-bounded choice fills the gap with the largest palette; beastfolk lore
gives them a narrower, single-element aptitude; elves already express affinity
through subraces. Presets continue to declare their own affinities explicitly
regardless of race.

### D5. Balance constants live in `progression.yaml`

`affinity_element_multiplier: 1.1` and `non_affinity_element_multiplier: 0.9`
join the existing provisional balance constants. The module reads them once at
import like `MAGIC_XP_PER_LEVEL`, so tuning is a yaml edit, not code. Both
constants are validated as finite and non-negative at module load (mirroring
the existing `effective_magic_growth_multiplier` guard), so a `nan`, negative,
or infinite yaml value fails closed at import.

### D6. Unknown element keys fail closed before the mastery override

`can_cast_spell_tier` validates the element key against `ELEMENT_REGISTRY`
first, raises `ValueError` for an unknown key, and only then applies the
mastery override and the effective-level comparison. This keeps fail-closed
behavior even for an entity that happens to own a fabricated
`<unknown>_mastery`. `monster_behaviour._gate_allows` wraps the whole gate
(not only `spell_tier_for`) in its existing `ValueError → False` handler, so a
malformed spell or element never breaks monster action selection.
`ActionResolver._step1_ownership` already converts the same `ValueError` into
an `UNKNOWN_SKILL` rejection, unchanged.

### D7. Consumption points stay where they are

`ActionResolver._step1_ownership` and `monster_behaviour._gate_allows` both
already funnel through `can_cast_spell_tier`, so the amendment needs no other
call-site changes. `magic_rank_title` and `effective_value("magic_level")` are
deliberately left reading the raw counter.

## Risks / Trade-offs

- **Elf non-affinity pacing changes**: elf subraces now get 0.9 on non-favored
  elements. Elf `magic_cap` is 900, so every tier remains reachable; only early
  pacing shifts. → Accepted as the intended "affinity shapes pacing" outcome;
  documented in the specs.
- **eolas becomes uniformly fast**: its all-eight affinity removes the
  0.9 penalty everywhere. → Accepted as lore (an elf branch said to excel at
  all elements); the effect is small.
- **Number drift**: 1.1/0.9 are provisional. → Centralized in
  `progression.yaml`; a recalibration change touches only the yaml and the
  few scenarios that pin exact unlock levels.
- **Player-picked human affinity is new player input**: the creation command
  surface changes. → The pick is bounded, validated, and documented in the
  command docs; `tests/test_command_docs.py` is updated in this change.
- **"Humans rarely cast 主宰 magic" is not guaranteed by MP cost alone**: a
  human can reach 200 MP and 主宰 spells cost 120–180, so a level-83 human
  can afford at least one favored-element cast. → The spec states only
  verifiable facts (unlock at 83 for chosen elements only; high MP cost limits
  *sustained* casting) and does not promise a hard rarity guarantee, which
  would need a separate affordability constraint out of scope.
- **Existing element-mastery scenarios**: some scenarios build entities
  without affinities and must stay green unchanged (D2). → The neutral-default
  property is itself asserted by new tests.

## Migration Plan

No released users and no migrations required: `affinity_elements` is a new
optional attribute defaulting to `[]` via the handler read path. Presets and
import examples are updated in the same change. The design doc amendment for
§4.2 (D4) is applied as an explicit amendment note.

## Open Questions

None blocking. Follow-up (not in scope): whether affinity should later feed a
per-element power axis, and whether beastfolk subraces should gain their own
affinity declarations.
