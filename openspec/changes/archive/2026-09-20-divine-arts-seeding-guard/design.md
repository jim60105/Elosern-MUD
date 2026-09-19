## Context

Three authored-content paths can write a disguise layer, and the boundary capability already
enumerates them as the sanctioned writers: `world/imports/loader.py` (import records),
`world/rules/character_creation.py` (preset activation), and `world/rules/starting_companions.py`
(the companion builder, which seeds each declared partner's own preset card).

Each of those writers is preceded by a validator that decides whether the declaration is admissible
at all, and it is the validators — not the writers — that this change touches:

- `world/lore/player_presets.py::_validate_preset_disguised_stats` runs at lore-registry import and
  raises, so a bad card cannot reach any activation. Its sibling `_validate_preset_skill_kits` already
  rejects a divine-arts skill on a non-divine race, which is the exact precedent this change follows.
- `world/imports/validate.py` runs before construction and reports issues into a batch report, where
  a rejection fails the whole batch. `can_use_divine_arts` currently appears nowhere in that module.

The companion builder needs no separate guard: it seeds from preset cards, so the preset validator
covers it.

`docs/development/adding-player-presets.md` documents each validator's rejections in a table, and
`tests/test_preset_authoring_docs_contract.py` — a registered data-contract test — holds that table
to the code. A new rejection therefore lands in the doc in the same change.

## Goals / Non-Goals

**Goals:**

- Make "only a divine-capable entity can wear a veil" an enforced invariant at every seeding
  boundary, not a convention that authored content happens to respect.
- Agree across the two authored-content paths: what the preset registry refuses at import, the import
  validator refuses too.
- Leave no shipped example in violation of the rule the change introduces.

**Non-Goals:**

- Changing the cast-time gate, the veil write, the display layer, or the companion record beside it.
- Adding a runtime check on the writers. The validators run before persistence and the boundary
  capability already forbids a writer from reading the layer back to make a decision; a second check
  inside the writer would duplicate the rule in a place that cannot report it usefully.
- Backfilling or migrating any stored entity. Pre-release, no saves carried across builds.
- Deciding whether a non-divine race should ever gain a veil source. That question was settled
  separately: it should not.

## Decisions

### D1: The check reads race capability, never skill ownership

A record could declare a veil without declaring `status_disguise`, or declare the skill without a
veil. The rule is about the bloodline, so the check asks `RaceProfile.can_use_divine_arts` directly.
Inferring from skill ownership would let a card carry a veil merely by omitting the skill from its
own declaration, which is the loophole a naive reading invites.

### D2: Fail closed on an unresolvable race

An unknown race resolves to `None`, and `None` is treated as unable to use divine arts — the same
stance `world/rules/action/gates.py` takes at cast time. The alternative, treating an unresolved race
as permissive, makes a typo in the race field into a way past the guard.

Both surfaces already reject an unresolvable race on their own terms, so in practice this arm is
defence in depth rather than the primary report. It is specified anyway so the check's behavior does
not depend on another validator's ordering.

### D3: Rejections, not warnings, on the import path

`validate.py` distinguishes warnings (implausible but loadable, such as an out-of-band stat) from
rejections (the record cannot load). A veil on a non-divine wearer is not implausible content — it is
state no engine path can produce, and loading it would create exactly the inconsistency the veil
system's guarantees depend on. It belongs with the rejections.

### D4: An empty declaration is not a layer

`disguised_stats` normalizes an empty mapping to `None` at all three writers — `loader.py`'s
`record["disguised_stats"] or None`, and `dict(preset.disguised_stats) or None` in both
`character_creation.py` and `starting_companions.py` — so an empty declaration seeds nothing. The guard
therefore triggers on a NON-EMPTY declaration only, which keeps a card or record that declares the
field and leaves it empty from being rejected for describing no veil at all.

### D5: The reference example loses its disguise layer, not its race

`world/imports/examples/example_character.json` is `race: "human"` with a `disguised_stats` block.
Changing its race to an elf would make it pass while destroying its purpose: it is the human baseline
reference that `world/imports/tests/test_reference_example.py` and the authoring docs point at.
Removing the two-key disguise block keeps the example doing its job and demonstrates the rule rather
than dodging it.

### D6: Behavior tests over synthetic fixtures, not over the shipped cards

The temptation is to assert that the three shipped elf cards still validate and that some shipped
human card does not. That is a data-echo test: it would pass for as long as the content happens to
line up and teach nothing about the rule. The tests instead construct a synthetic preset registry and
synthetic import records covering the divine-capable, non-divine, unresolvable-race and
empty-declaration cases, so they establish the mechanic and stay correct when content changes.

### D7: The example keeps the `disguised_stats` key, empty, and its own spec requirement follows

`CHARACTER_SCHEMA_V1` requires the `disguised_stats` key on every character record (see D4's
enumeration of the three writers that normalize an empty mapping to `None` — the schema's own
requiredness is a separate, structural fact). So D5's "remove the block" is `{}`, not omitting the
key. That leaves `import-reference-example`'s "exercises every major schema branch" requirement
holding a scenario that asserts the field non-empty — true before this change, false after, since the
example's race (`human`) can never carry a populated layer once the guard lands. `openspec validate`
refuses a MODIFIED block that drops or renames a scenario the current spec still has, and also refuses
the same title in both an ADDED and a REMOVED block in one delta file, so the requirement is retired
under its old title (REMOVED, verbatim) and replaced under a new one — "...it can demonstrate on its
race" (ADDED) — carrying the four unaffected scenarios unchanged and rewriting only the disguised_stats
one. The title change moves the requirement's traceability ID, so
`world/imports/tests/test_schema.py`'s `covers_requirement` call that named the old ID is repointed to
the new one, and `test_reference_example.py`'s
`test_reference_example_is_clean_and_exercises_contract` — whose own assertions already cover the new
requirement's scenarios — gains the new ID alongside its existing one. Its
`assertTrue(record["disguised_stats"])` becomes `assertFalse(...)`.

## Risks / Trade-offs

- **Authored content in flight may break.** Any card or record written against the old permissive
  rule now fails at import. That is the point, and the failure is a named validation error at load
  time rather than a silent inconsistency at play time.
- **The rule is enforced in two places rather than one.** The preset path and the import path each
  carry their own check, because they have different reporting contracts (raise vs. batch report) and
  neither can call the other's. Mitigated by specifying both arms in one requirement so they cannot
  drift apart, and by covering both with the same four-case behavior matrix.
- **A future non-preset seeding path could bypass the guard.** The boundary capability bounds the
  writer set, so adding one is already a spec change; this requirement gives that change an explicit
  obligation to satisfy.
