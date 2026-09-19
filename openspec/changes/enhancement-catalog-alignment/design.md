## Context

See proposal.md — Why. The facts that shape the approach:

- `GrowthRateEffect(stat, multiplier)` parses today but has **no production consumer** — only `world/skills/tests/test_effects.py` names it. `_practice_growth_factors()` reads `growth_rate_multiplier(entity)`, which scans `conferred_growth_rate` *buff* instances only.
- `_practice_growth_factors()` is the single shared composite behind both practice entry points (the per-use grant and the booked-hourly settlement), and it already validates its result is finite and non-negative before any caller writes.
- `SkillHandler` has a working precedent for exactly this shape: `effective_value()` walks owned keys, pulls each skill's `parsed_effects`, and multiplies the matching `StatMultiplyEffect`s together, with `_matching_multiplier()` raising when one skill declares two multipliers for the same trait.
- `flight` and `flash_step` are already `PASSIVE` per `skill-registry`; their `cost` dicts survive only because the taxonomy change that reclassified them was explicitly forbidden from touching any other field.

## Goals / Non-Goals

**Goals:**

- A `growth_rate` effect that cannot be authored without saying which tree it accelerates.
- One shared factor, so the two practice entry points cannot diverge.
- The inert cost dicts gone, with the spec saying why they may not come back.

**Non-Goals:**

- No scope vocabulary beyond element keys (see D1). No change to the conferred-buff path. No backfill for characters already holding the boon — pre-release, zero users.

## Decisions

### D1. Scope is an element key, not a general scope language

`cross-lineage-unlock` introduces a richer scope grammar (`category` + `group`, or explicit keys) for a different purpose. Reusing it here would make this change depend on that one for no shipped benefit: the only scoped growth rate the project ships is 伊洛希雅's, and it names one element tree.

So `<scope>` is validated against `ELEMENT_REGISTRY` and nothing else. A future boon scoped to the martial or divine trees is a grammar extension at that time, with a real case to shape it. Building the general form now would be unused generality that still has to be maintained.

### D2. Four segments, scope last, and the old form fails closed

`growth_rate:<stat>:<multiplier>:<scope>` keeps `<multiplier>` where it already is, so the parse branch grows a segment rather than being rewritten.

The three-segment form is **rejected**, not defaulted. A default scope would silently keep `growth_rate:practice:100` meaning something, and the whole point of the change is that an unscoped global growth rate is the broken design being retired. Failing closed forces the one shipped row to be re-authored deliberately, and the registry's own import is the test.

### D3. The consumer reads owned skills, mirroring `effective_value()`

The factor is computed by walking the actor's owned keys, reading each resolvable skill's `parsed_effects`, and multiplying every `GrowthRateEffect` whose `scope` equals the practised skill's element. Rationale: the effect is declared *on a skill*, and ownership of that skill is what the lore says confers it. This is the same traversal `SkillHandler.effective_value()` already performs for `stat_multiply`, so the codebase has one idiom for "a passive I own modifies a derived number", not two.

Within a single skill, two `growth_rate` effects sharing a scope raise, matching `_matching_multiplier()`'s duplicate guard. Across different owned skills, matching multipliers multiply — the same composition rule the stat multipliers already use.

The affinity test (`_is_elemental_magic`) decides what "the practised skill's element" means: a physical skill carrying an element (`light_sword_style`) is not elemental magic and takes `1.0`, exactly as the affinity factor already treats it. Reusing that predicate keeps the two element-keyed factors from disagreeing about what an elemental skill is.

### D4. The authored content decision: ×5, scoped to wind

The multiplier comes from `docs/lore/skill-trees/innate-gift.md`, which sets ×5 against the elf ×10.0 learning multiplier to make reincarnators *depth* and elves *breadth*.

The **tree** is a genuine authoring choice, not a derivation: 伊洛希雅's kit carries `wind_mastery`, `light_mastery`, `dominion_art` and `status_disguise`, so either wind or light could be argued. Wind is chosen because her kit leads with `wind_mastery` and she carries `flight`, whose lore gate is wind understanding. This is the one place in this change where a different answer is defensible and should be confirmed rather than assumed correct.

Note the stacking consequence, which is intended: 伊洛希雅 is an elf, so inside the wind tree her composite is `10.0 × 5 = ×50` before affinity. That is the "prodigy in her one tree" the lore describes; outside wind she is an ordinary elf at ×10.

### D5. Removing the inert costs is a spec statement, not just a deletion

Deleting the two dicts alone would leave nothing preventing a future author from adding them back. The `skill-registry` delta therefore states the rule — a PASSIVE skill declares an empty cost, because it has no cast action to deduct from — and adds the scenario that pins it.

The existing assertion `flight.cost == {"mp": 22}` in `test_rehomed_acquired_passives_keep_their_mechanics` is updated in place rather than deleted: that test's job is proving the *taxonomy reclassification* changed no mechanics, which remains true and worth keeping; it simply now compares against the corrected value.

## Risks / Trade-offs

- **An elf reincarnator reaches ×50 in one tree.** → Intended and documented, but it is the largest growth multiplier in the game and the first place to look if progression feels too fast in playtesting. The number lives in one registry row and one lore table, so retuning is a data edit.
- **The scope names an element, but the lore says "系譜樹".** → For the eight element trees these coincide exactly. They stop coinciding if a boon ever needs to scope the martial or divine trees, which D1 defers deliberately.
- **`world/rules/progression.py` is edited by `cross-lineage-unlock` too.** → Different functions (`_practice_growth_factors()` here, `grant_skill_practice_xp()` there). Whichever merges second rebases; no requirement overlap.
- **Existing saved characters holding the boon keep an unparseable effect string.** → Not applicable: skills are resolved from `SKILL_REGISTRY` by key at read time, and storage holds keys, not effect strings. The registry row changes and every holder picks up the new effect immediately.

## Open Questions

- Should 伊洛希雅's boon scope be **wind** (chosen, per D4) or **light**? Both are in her kit. The mechanics, grammar, specs and task list are identical either way — only the one string in the registry row differs — so this is safe to confirm at implementation time without reopening any artifact.
