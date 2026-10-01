## Context

See proposal.md for motivation. The foundation inventory (`world/lore/npc_profiles/inventory.py`) lists every shipped source and its owner; each content slice proved its own rows; the producers made host and examiner references mandatory; the companion change made `npc_profile_key` mandatory; the quest and import changes made template occupants and the reference example carry cards. Boot steps run in `STARTUP_STEP_ORDER` through `_startup_step`, fail-loud by default; `starting_companion_validation` is the precedent of a registry-validation boot step.

## Goals / Non-Goals

**Goals:** one authoritative, deterministic completeness check over the whole shipped roster, run at boot and in tests; a written roster-wide review.

**Non-Goals:** touching persisted instances (cutover); judging prose quality automatically; checking dynamic (generated/imported-at-runtime) NPCs, which are validated by their own creation paths.

## Decisions

### D1. Derivation lives rules-side

`derive_shipped_sources()` needs `QUEST_TEMPLATE_POOL` (`world/ai`) and the example files, which lore must not import; it lives in `world/rules/npc_roster_validation.py` and returns frozen `NpcSource` keys identical to the inventory's. The foundation's data-contract test switches to it.

### D2. Checks and error reporting

`validate_npc_roster()` raises `NpcRosterError` listing every violation (not just the first), each naming the source kind/key and profile key: inventory mismatch (missing or stale rows); unresolved or invalid card; a dialogue table referenced by zero or several hosted places; a scripted host profile without `misunderstood`; a companion profile without `greeting`; an orphan profile (in `NPC_PROFILE_REGISTRY` but referenced by no place, rank, or declaration). Import examples are validated with `validate_character(record, NPC)`; template occupants through the shared characterization helper.

### D3. Boot placement

`npc_persona_roster_validation` runs after `state_reaction_rules` and before `sync_all`: it reads only immutable registries and files, so it can run before any world sync, and a failure aborts boot before any persistent write (fail-loud, like `starting_companion_validation`).

### D4. Review record

`docs/lore/npc-persona-roster-review.md` (Traditional Chinese prose, English headings allowed by docs convention) records: the roster table (source → profile → owner slice → review status), cross-slice same-profession comparisons (all merchants; all attendants; elder vs dean; examiners), issues found and their fixes, and whether representative free-form prompt/reply review was performed with an approved model — stated honestly when not.

## Risks / Trade-offs

- [A future NPC added without a profile blocks boot] → intended; the error names the source and the owning step to add.
- [Orphan-profile rejection blocks drafting ahead] → profiles must be referenced in the same change that adds them; drafts live outside the registry.
