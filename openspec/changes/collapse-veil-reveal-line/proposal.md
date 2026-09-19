## Why

`unveiling_eye` (揭帷之眼) is a reveal node whose declared job is to clear veils of NON-DIVINE origin.
No such veil exists in this world, and none can be authored into it by design:

- The only skill that veils anything is `status_disguise`, which declares
  `requires_divine_arts=True` and is therefore castable only by elves. `bestowed_veil` is the same
  verb aimed at a third party and writes the same divine provenance.
- No item, buff, or rule-table effect writes a disguise layer.
- Every authored `disguised_stats` declaration in shipped content belongs to an elf
  (`yuka_darknight`, `yuna_darknight`, `elosia_shadowmoon`). The only non-elf declaration anywhere in
  the repository is `world/imports/examples/example_character.json`, a schema example rather than
  world content.

Because `disguise_provenance_of()` grades any veil with no explicit record as mundane — a deliberate
choice recorded in `divine-veil-cast-path` D3, which needed authored veils to read mundane so a
self-cast would refresh rather than strip a character card's veil — those three authored elf veils
currently read as the WEAKEST grade in the game. `unveiling_eye` is available at `status_disguise`
Lv.3 and clears them.

So the node is simultaneously wrong and useless: today it strips exactly the veils the setting says
are unstrippable, and the moment that is corrected it has no target left at all. The setting has one
grade of veil, so the two-strength reveal grammar has nothing to distinguish. Removing the node and
the strength it exists to express fixes the defect by deletion and leaves the provenance record
answering the single question it is actually read for — did this verb place this veil? — which is
what `divine-veil-cast-path` D3 always meant by it.

## What Changes

- Remove the `unveiling_eye` skill from `SKILL_REGISTRY`.
- Rewire `true_name_sight`'s prerequisite from `unveiling_eye` Lv.5 to `status_disguise` Lv.5, so the
  veil line becomes `status_disguise` → {`bestowed_veil`, `true_name_sight`}.
- **BREAKING** (authoring grammar; no released users): retire `RevealStrength` entirely and make
  `reveal_disguise` a bare, payload-free prefix. The `reveal_disguise:true_name` form stops parsing,
  and `true_name_sight` declares the bare prefix. A reveal now either lifts the veil it finds or
  reports finding none.
- Simplify the reveal primitives accordingly: the pierce predicate loses its strength parameter and
  collapses to "does this entity carry a veil".
- **BREAKING** (persisted attribute; no released users): rename the companion record to say what it
  now means. With the reveal consumer gone it has exactly one reader — the self-cast toggle — and one
  question: did this verb place this veil? So `entity.db.disguise_provenance` becomes
  `entity.db.disguise_placed_by_cast` and changes from a two-value string to a boolean;
  `disguise_provenance_of() -> str` becomes `was_cast_placed() -> bool`;
  `record_disguise_provenance(entity, provenance)` becomes `record_cast_placement(entity)`; and the
  `DISGUISE_PROVENANCE_DIVINE` / `DISGUISE_PROVENANCE_MUNDANE` constants are deleted. An absent
  record means "not placed by the verb", exactly as an absent record means "mundane" today, so no
  data migration is needed.
- Update the veil-line documentation on `docs/lore/skill-trees/divine-mystery.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-effect-model`: the `reveal_disguise` grammar requirement, which currently mandates exactly
  two closed forms carrying two strengths.
- `skill-handler`: the provenance-scoped reveal primitive requirement is REMOVED and replaced by an
  unconditional reveal primitive carrying no strength vocabulary.
- `disguised-stats-boundary`: the provenance requirement is REMOVED and replaced by a placement
  requirement. Both are replacements rather than modifications because the concept changes, not just
  its wording; each delta therefore carries a **Reason** and **Migration** instead of a rewritten
  scenario set whose titles would still name the retired vocabulary.

The `divine-mystery` capability needs no delta: its requirements bound the family's cost, race gate
and composition behavior over synthetic chains, and no spec in `openspec/specs/` names
`unveiling_eye` or any particular chain edge.

## Impact

- `world/skills/registry.py` — remove one skill definition, rewire one prerequisite.
- `world/skills/effects.py` — delete `RevealStrength`, strip the strength field from
  `RevealDisguiseEffect`, simplify the `reveal_disguise` parse branch.
- `world/rules/skill_effects.py` — `reveal_can_pierce` and `reveal_disguise_effect` lose their
  strength parameter.
- `world/rules/action/effects/conferral.py` — `_handle_reveal_disguise` stops threading a strength.
- `world/rules/tests/test_divine_veil_reveal.py`, `world/skills/tests/test_skill_registry.py` —
  the mundane-strength cases become removal coverage; the registry catalog assertion drops one key.
- `docs/lore/skill-trees/divine-mystery.md` — this change owns the whole page (veil-line diagram,
  node table, and the 帷幕線 boundary bullet). The `dissolve-utility-lineage` change no longer edits
  it.
- The record rename additionally touches `world/rules/cast_settlement.py` and `world/rules/clock.py`
  (the `("disguise_provenance", None)` shell-default entries) and `world/rules/action/transaction.py`
  (the snapshot and restore key). These three carry the record by name only and make no decision from
  it.
- `world/rules/tests/test_divine_veil_cast.py` — unchanged by the reveal collapse, but its
  assertions on the retired constants are updated by the rename.
- `world/rules/tests/test_disguise_boundary.py` — its forbidden-module scan asserts on the record's
  attribute name, so the literal and the module comment are re-pointed, never dropped.
