## Context

`docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md` (D-12) and
`docs/superpowers/specs/2026-08-15-sexual-act-catalog-design.md` (§4.1) already decided that
`virgin` breaks only on vaginal intercourse between an opposite-sex pair, reusing the shipped
`sexual.yaml` split between `first_vaginal_penetration` (breaks `virgin`) and
`penetrative_sex_with_female` (adds `女女性愛`, never touches `virgin`). No rule changes are needed
for that branch — it lives in the act catalog (a later, separate change) and needs one input this
change supplies: a `sex` value on every participating entity.

Today no such input exists. `CHARACTER_SCHEMA_V1` declares `age`, `apparent_age`, `race`, and
`subrace`; `LivingEntity` declares `race`/`subrace` as `AttributeProperty` attributes. This change
adds the missing field only — it introduces no behavior that reads it.

## Goals / Non-Goals

**Goals:**
- Give every entity a `sex` value drawn from a fixed three-member vocabulary
  (`female`/`male`/`other`), with a single canonical source for that vocabulary.
- Make the value required and explicit for every imported character record.
- Give every entity constructed outside the import path (every `Monster` today, since no
  bestiary/spawn system exists) a safe, unambiguous default.

**Non-Goals:**
- Reading `sex` anywhere. No branch, rule, or presenter consumes it in this change; the sole
  consumer (the later `sexual-catalog-partner` proposal) is out of scope here.
- Wiring the player-character creation wizard (`world/rules/character_creation.py`) to collect
  `sex`. Player characters built through the wizard, not `CHARACTER_SCHEMA_V1`, are unaffected by
  this change and fall back to the class-level `"other"` default until a future change addresses
  this explicitly (see Open Questions).
- Any presentation surface (status display, character sheet). `sex` is mechanical input, not
  player-facing content, matching how `disguised_stats` and `sexual_baseline` are handled: stored
  verbatim, displayed nowhere by this layer.
- Gender identity, pronouns, or any narrative/social modeling. This field exists solely to gate one
  mechanical branch in a later change and deliberately carries no broader meaning.

## Decisions

**D1: A new lore module, `world/lore/sex.py`, owns the vocabulary — not an inline list in
`schema.py`.**

`world/lore/sexual_vocab.py` already establishes the pattern this project uses for a small,
dependency-free vocabulary consumed by more than one downstream module: define it once in
`world/lore/`, import it everywhere it's needed, never restate the literal values. `SEX_VALUES` will
have exactly two consumers by the time the full sexual-act-system design set lands — this change's
own schema enum, and the later `sexual-catalog-partner` proposal's opposite-sex branch — which is
the same shape `sexual_vocab.py` was built for. Declaring it inline in `schema.py` would force the
later proposal to import from the schema module (wrong dependency direction: content should not
depend on import validation) or to duplicate the tuple (exactly what
`AGENTS.md` forbids: "Consumers must read registry values instead of duplicating balance
constants").

Alternative considered: fold `sex` into `world/lore/sexual_vocab.py` itself. Rejected — that
module's own spec (`sexual-vocabulary`) scopes it explicitly to "the six ordered level-name
vocabularies from design doc §6.4" and states it "SHALL contain no behavior... and no dependency on
any `world/rules/` or `world/imports/` module" as an ordered-level vocabulary set. `sex` is not an
ordered level (there is no meaningful `female < male` ordering), so it does not belong in that set
conceptually, and mixing it in would blur that module's single stated purpose.

**D2: The default is the string `"other"`, not `None`.**

`race`/`subrace` default to `None` because their registries (`RACE_REGISTRY`/`SUBRACE_REGISTRY`)
have no "unspecified" member — `None` is the only way to represent "not yet set." `SEX_VALUES`
already contains an explicit unspecified/non-binary member, `"other"`, so a second null state would
be redundant and would force every future consumer to handle two "don't know" cases
(`None` and `"other"`) instead of one. `entity.sex` is therefore typed `str`, not `str | None`,
and defaults directly to `DEFAULT_SEX` (`"other"`).

This also directly satisfies the design doc's stated behavior: "An entity whose sex is unknown or
`other` never breaks virginity, which makes the monster case fall out for free instead of needing a
special case" (overview D-12). A `Monster` never sets `sex` and therefore reads `"other"` with zero
special-case code in whatever later change adds the branch.

The double duty `"other"` performs — both "explicitly declared" and "never set" — is only ambiguous
for a `LivingEntity` instance constructed outside the import loader. Today the only such instances
are `Monster`, which has no narrative sex/gender concept in the first place (monsters are already
treated as a single generic body-part channel elsewhere in the sexual-act design set, per
`sexual-act-catalog-design.md` D-8), so the collapse is harmless in the codebase as it exists now.
This reasoning would need revisiting if a future non-import-constructed `LivingEntity` subtype ever
needs a real, distinguishable sex value.

**D3: The schema requires `sex`; the typeclass defaults it. Both are necessary, and they're not
redundant.**

Making `sex` `required` in `CHARACTER_SCHEMA_V1` forces every future imported character record
(hand-authored or generated) to make an explicit choice rather than silently inheriting a default —
consistent with this schema's existing posture toward identity-adjacent fields (`age`,
`apparent_age`, and `race`/`subrace` are all required, none defaulted). The typeclass default exists
for the disjoint case of entities that never go through import validation at all (`Monster`, and any
future non-imported construction path) — the schema's `required` cannot reach those, since they
never see the schema.

**D4: The loader assigns `entity.sex` the same way it assigns `race`/`subrace` — direct property
assignment, not a `entity.db.*` seam attribute.**

`loader.py` already has two shapes for record fields: identity-like scalars go through direct
`AttributeProperty` assignment (`entity.race = record["race"]`), while opaque/seam-owned blobs go
through `entity.db.*` (`entity.db.persona = record["persona"]`, reserved for a future handler to
mount on the bare name). `sex` is a plain, present-tense scalar exactly like `race`/`subrace`, not an
opaque payload a future handler will wrap — so it takes the first shape:
`entity.sex = record["sex"]`.

## Risks / Trade-offs

- **[Risk] Adding a required schema field is breaking.** → **Mitigation**: explicitly acceptable per
  project convention (pre-release, zero users; `tmp/propose.md` and `AGENTS.md` both waive
  backward-compatibility obligations). The one shipped example record
  (`world/imports/examples/example_character.json`) is updated in this same change, and it is the
  sole fixture every schema/loader/dispatch test builds on via
  `world/imports/tests/helpers.py::example_record()`, so the blast radius is fully contained to this
  change.
- **[Risk] Player characters never get a real `sex` value under this change**, so the later
  opposite-sex branch would treat every player as `"other"` until the creation wizard is wired up. →
  **Mitigation**: this is a real, acknowledged gap, not an oversight — see Open Questions. Defaulting
  to `"other"` is the conservative failure mode (fewer virginity-breaking events fire, never more),
  which matches this codebase's general fail-closed posture (e.g. the divine-arts gate rejecting an
  actor with no resolvable race rather than defaulting open).
- **[Risk] A new lore module for two constants may look like ceremony.** → **Mitigation**: the
  precedent this mirrors (`sexual_vocab.py`) was justified by exactly this reasoning — one module,
  many consumers, zero duplicated literals — and `SEX_VALUES` is already known to gain a second
  consumer in the immediately following proposal in the same design set.

## Migration Plan

No runtime migration: zero users, and the only persisted data this change's schema touches is
future imports. Rollback is a plain revert; no data backfill is required in either direction.

## Open Questions

- **Should the player-character creation wizard collect `sex`?** Deliberately deferred, but flagged
  here as an unowned gap, not a settled deferral. The sexual-act-system design set's proposal
  ownership table scopes this change (`S1`) to `world/imports/schema.py`,
  `world/imports/examples/`, and `typeclasses/` only — `world/rules/character_creation.py` belongs
  to no proposal anywhere in the current 22-proposal sequence, including `C4`
  (`sexual-catalog-partner`), the proposal that will actually read `entity.sex`. Left unaddressed,
  every player character stays at the `"other"` default indefinitely, which — per
  `sexual-act-catalog-design.md`'s own event table — means the opposite-sex `virgin`-break branch
  this field exists to enable can fire for an NPC/NPC or NPC/monster pair but **never for a real
  player character**. That would leave the mechanic's most important participant permanently
  excluded from the reason this change exists. This is functionally safe today (no incorrect
  behavior ships) but should become a tracked proposal in the sequence — not left as prose in an
  Open Question — before `C4` is implemented.
