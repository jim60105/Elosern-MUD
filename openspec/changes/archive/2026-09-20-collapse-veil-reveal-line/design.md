## Context

The veil subsystem has one writer and, today, two readers of its provenance record, each asking a
different question of the same two-valued field:

- `world/rules/action/effects/conferral.py`'s `set_disguise` handler asks **placement** — did this
  verb place the veil I am casting over? A self-cast lifts a veil it owns and refreshes over anything
  else. `divine-veil-cast-path` D3 introduced this and needed authored veils to answer "not mine".
- `world/rules/skill_effects.py::reveal_can_pierce` asks **grade** — is this veil strong enough to
  resist a weak reveal? `divine-veil-reveal` D3 introduced this and inherited D3's value, which is
  where the defect comes from.

The proposal establishes that the grade question has no referent: nothing in this world can veil an
entity except a bloodline-gated divine mystery, so every veil is of one grade. Removing the grade
reader removes the collision at its root, which is why this change needs no new vocabulary, no
derivation and no migration — the surviving reader has always been served correctly by the field as
it stands.

With one reader left, the field's NAME becomes the remaining problem, which is why the rename rides
in this change rather than trailing it. The attribute is `disguise_provenance`, its values are
`"divine"` and `"mundane"`, and its accessor is `disguise_provenance_of()` — every one of those names
describes the grade this change retires. Shipping the collapse while leaving that vocabulary in place
would leave the next contributor a field that still says veils come in provenances, and that a
mundane one is weaker: the exact inference that produced the defect. The two halves are one story and
share every file, so splitting them would only mean editing the same six modules twice.

Fixed constraints:

- `openspec validate` refuses to drop or rename a scenario inside a MODIFIED requirement block, but
  places no such constraint on a REMOVED requirement paired with an ADDED replacement. Two spec
  requirements can therefore be replaced cleanly; one cannot, because it is a large shared block
  covering every effect prefix. See D4.
- `world/rules/tests/test_divine_veil_reveal.py` is built on a `_FakeEntity` double whose fixtures
  are all `race="human"`; its mundane-strength cases are the ones this change converts.
- `world/skills/tests/test_skill_registry.py` asserts a catalog key list that includes
  `unveiling_eye`.

## Goals / Non-Goals

**Goals:**

- A veil declared on an elf character card is lifted by nothing but `true_name_sight`.
- The reveal vocabulary stops expressing a distinction the setting does not make, so the hole cannot
  be reopened by authoring a skill against a strength that should not exist.
- The veil's companion record ends the change with exactly one reader, one meaning, and a name and
  type that state that meaning.

**Non-Goals:**

- Re-introducing a grade axis under any other name.
- Any behavior change from the rename half: every branch must resolve identically before and after.
- Introducing any mundane veil source — an enchanted disguise item or similar. Explicitly rejected
  by the setting owner: non-divine disguise does not exist in this world.
- Changing the veil write's derived-value recipe, the self-cast toggle's behavior, the display layer,
  or the `disguised_stats` mapping and its import schema. The record beside the mapping is renamed;
  the mapping itself is untouched.
- Any edit to `docs/lore/skill-trees/` other than `divine-mystery.md`, which this change now owns in
  full.

## Decisions

### D1: Delete the node rather than re-grade the veils it wrongly pierces

The alternative considered first was to keep `unveiling_eye` and make authored elf veils read at
divine grade, by widening the provenance vocabulary to three values and deriving an authored veil's
grade from `RaceProfile.can_use_divine_arts`. That was designed in full and rejected once the setting
question was settled: it preserves a node whose corrected target class — an authored veil on a wearer
without divine arts — is empty in shipped content and, per the setting owner, unfillable in
principle. It would have bought a dead node three new constants, two new predicates, a reader that
consults the race registry, and a migration story, to fix a defect that deletion removes outright.

The project has applied this standard consistently in the same pass: a capability with no mechanical
referent is removed rather than given a mechanism to justify it.

### D2: Retire `RevealStrength` entirely instead of collapsing it to one member

A single-member enum is a comment with a type. `RevealDisguiseEffect` becomes a payload-free marker
like `RevokeGrantsEffect`, `reveal_can_pierce` loses its parameter and collapses to "does this entity
carry a veil", and `reveal_disguise` joins `revoke_grants` as a bare prefix.

The security-relevant half of this is that `reveal_disguise:true_name` must stop parsing rather than
becoming a tolerated alias. If the payload form still parsed, the retired distinction would remain
expressible in authored data, and the first skill to declare the bare form under the old reading
would silently reopen the hole this change closes.

### D3: `true_name_sight` inherits `status_disguise` Lv.5 as its prerequisite

The removed node sat between them at Lv.3 → Lv.5. Attaching the survivor to the chain root at the
same Lv.5 threshold keeps the reveal capstone's depth roughly where it was rather than promoting it
to a cheaper rung, and leaves the line as a root with two independent children. The capstone
`crown_apotheosis` still requires `true_name_sight` Lv.10 and is unaffected.

### D4: Two requirements are REPLACED; one is MODIFIED with two titles carried over

`openspec validate` treats a MODIFIED requirement as a whole-block replacement and rejects any delta
that drops or renames a scenario the current spec still has. Several scenario titles across the three
affected requirements name the strength vocabulary this change retires, so a MODIFIED delta would
carry those titles into the main specs attached to bodies that contradict them.

Where the concept itself is being replaced rather than reworded, REMOVED + ADDED avoids that
entirely and is the more honest shape. Both `skill-handler`'s reveal primitive and
`disguised-stats-boundary`'s provenance record are replaced this way, each carrying the **Reason**
and **Migration** the format requires, and each gaining a name and scenario set that describe the new
concept from the start.

`skill-effect-model` cannot take that treatment: the reveal grammar lives inside
"parse_effect classifies every declared prefix into a typed dataclass", one large requirement
covering every effect prefix in the project, which cannot be removed to change one paragraph. That
delta is therefore MODIFIED, and exactly two titles are carried over verbatim with corrected bodies
("The bare reveal prefix parses at mundane-only strength", "The true-name form parses at
any-provenance strength"). Task 6.4 corrects those two by direct edit to `openspec/specs/` after
archive, because a scenario titled "the true-name form parses at any-provenance strength" whose body
asserts a `ValueError` is exactly the kind of stale artifact this change exists to remove.

### D5: The placement record is a boolean with an absent-is-false reading

The surviving question is yes/no, so the type is `bool`. `True` is written only by the veil verb;
nothing ever writes `False`, because "not placed by the verb" is exactly the state of having no
record — which is already what every authored veil and every pre-existing entity has. Absent-is-false
therefore preserves today's absent-is-mundane semantics exactly, with no migration and no backfill.

*Alternative rejected:* keeping a string with honest values (`"cast"` / `"authored"`). It is a
boolean with extra steps: a constant pair, a comparison at every read, and a decision about what an
unrecognized value means — the same shape that let the original field drift into answering two
questions.

### D6: The attribute is renamed outright, and its writer loses its value parameter

`entity.db.disguise_provenance` becomes `entity.db.disguise_placed_by_cast` with no compatibility
shim. Pre-release with zero users and no saves carried across builds, a shim would be dead code whose
only effect is to keep the retired name greppable — the opposite of the change's purpose. The three
carrier sites (two shell-default tables and the action snapshot) are updated in the same commit.

`record_disguise_provenance(entity, provenance)` exists because there were two values to choose from.
With one, a value parameter is a way to write the wrong thing, so the writer becomes
`record_cast_placement(entity)`, called from exactly one place beside the display-mapping write
inside `apply_divine_disguise`.

## Risks / Trade-offs

- **A shipped skill is deleted, not deprecated.** Any character that already owns `unveiling_eye`
  holds a key that no longer resolves in `SKILL_REGISTRY`. Pre-release with zero users, no saves are
  carried across builds, and no shipped preset or companion grants it — verified by grep before
  writing this. The registry's own load-time validation will name the key if one is missed.
- **The veil line loses a rung, so the 帷幕 chain is shallower than the other two divine-mystery
  lines.** Accepted: chain length is not a balance lever here, the digestion cadence already governs
  progression speed, and a rung that does nothing was not providing depth.
- **Two stale scenario titles exist between this change's archive and task 6.3.** Bounded, recorded,
  and fixed by a step inside this change rather than left to a future reader to notice.
- **A persisted attribute is renamed with no shim.** An entity stored by an older build keeps a
  `disguise_provenance` attribute nothing reads, and reads as "not placed by the verb" — the correct
  answer for every authored veil, and the wrong one only for a veil a cast placed before the rename.
  Accepted: pre-release, no saves carried across builds, and the failure mode is a self-cast
  refreshing instead of lifting, not a veil becoming pierceable.
- **The rename half is mechanically broad but semantically empty.** It touches six production files
  and two test files to change nothing observable, which makes review tedious and a silent behavioral
  edit easy to hide. Mitigated by task 5.3: the existing veil tests must pass with mechanical
  substitutions only, and any assertion needing real restructuring is a signal that behavior moved
  and must be investigated rather than accommodated.
- **The merged change is a full, busy workday.** The reveal collapse and the rename were scoped as
  two changes before being merged at the owner's direction; they share every file, so splitting them
  would mean editing the same six modules twice. If the day runs long, task group 5 is the safe
  place to stop — the code is coherent and green at the end of group 4.
- **If the setting later gains a mundane veil source, this work is partly reversed.** The setting
  owner has ruled that out. Re-adding a grade axis would be a deliberate new change with its own
  justification, which is a better position than keeping an unused axis alive on speculation.
