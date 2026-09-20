## 1. Move the authored dialogue rows to lore

- [x] 1.1 Create the `world/lore/dialogue/` package: `shape.py` holding `KeywordResponse` and
  `DialogueDefinition`, `guild.py` holding the `guild_staff` row moved from
  `world/rules/dialogue.py`, and empty `altoria.py` and `ciaran.py` slices for the
  content changes to fill. The moved row keeps every contract-pinned substring of the
  original prose — the scripted-dialogue spec's `回報` keyword, the unregistered
  register-first fallback, and all eight taught `guild` commands — but is re-authored in
  the clerk's in-character 正體中文 voice (never a recited command manual) and carries
  at most four keyword answers: the dialogue panel ships `DIALOGUE_MAX_CHOICES` entries
  and silently drops the rest, so a fifth keyword is one no player can ever press.
  Every content slice authored under this package follows both rules.
- [x] 1.2 `__init__.py` assembles `DIALOGUE_ROWS` from the slices in a fixed, commented order,
  matching how `places.py` assembles its settlement slices.
- [x] 1.3 In `world/rules/dialogue.py`, re-export both dataclasses and assemble
  `DIALOGUE_TABLE` from `DIALOGUE_ROWS` behind the same `MappingProxyType`. Every existing
  import path keeps working.
- [x] 1.4 Verify no importer is left naming a moved symbol from a module that no longer
  defines it: `grep -rn "DialogueDefinition\|KeywordResponse" --include="*.py" .` and confirm
  each hit still resolves. The synthetic kit and the webclient presentation tests both import
  from `world.rules.dialogue`; both must stay untouched.
- [x] 1.5 Run the scripted-dialogue suite and confirm it is green with no edits to it — that is
  the proof the move changed no answer.

## 2. The attendant blueprint

- [ ] 2.1 Add the `attendant` row to `world/rules/rulebook/professions.yaml`: one
  `{ type: scripted_dialogue, default_binding: place }`, `schedule_template: null`,
  `default_tier: null`. Extend the module header comment to say what the row is for, matching
  how the existing rows document their provenance.
- [ ] 2.2 Cover the blueprint over a synthetic place row: a host that carries the dialogue
  component bound to the authored key and carries none of merchant / guild-staff /
  guild-examiner / quest-issuer. Use the synthetic kit's existing dialogue fixture, not a
  shipped key.
- [ ] 2.3 Cover the two rejections with synthetic rows — an attendant authoring `shop_key`
  (dead kwarg) and an attendant declaring assortments (shop identity required). Both already
  fail through existing rules; the tests pin that they keep failing for an attendant.

## 3. Bind a host to a table that exists

- [ ] 3.1 In `validate_service_hosts`, after blueprint coverage resolves each component's
  identity fields, reject a row whose profession includes `scripted_dialogue` and whose
  authored `dialogue_key` is absent from the dialogue registry. Name the place and the key.
  The check fires for every dialogue-bearing profession, the guild hall's included.
- [ ] 3.2 Import the registry function-locally inside `validate_service_hosts`, matching how
  that function already reaches `profession_config`, so the config module keeps its import
  shape.
- [ ] 3.3 Cover the rejection with a synthetic place row naming an unregistered key, and cover
  that a runtime lookup of an unregistered key still returns the no-understanding line without
  raising — the two rules that must not collapse into each other.

## 4. Prove nothing shipped moved

- [ ] 4.1 Assert the derived roster after this change equals the roster before it, field by
  field, and that no shipped row names `attendant`. This is the neutrality gate: the blueprint
  ships unused.
- [ ] 4.2 Run the guild-config, guild-economy-sync and scripted-dialogue suites, plus
  `uv run --locked python -m tools.spec_traceability check`.
