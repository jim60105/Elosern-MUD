# Tasks: quest-issuer-component

## 1. Component

- [x] 1.1 Add `QuestIssuer(Component)` to `typeclasses/components.py` with `name = "quest_issuer"`
  and `service_id`, `issuer_key`, `service_binding`, `anchor_room_id` DBFields — the same four-field
  shape `GuildStaff` carries, with `issuer_key` where `branch_key` sits. `service_id` is REQUIRED:
  `world/rules/guild_economy.py::_find_service_host` reads `component.service_id` unconditionally on
  whichever class anchors a profession row, so a commissioner blueprint anchored on a field-less
  class would raise `AttributeError` inside `at_server_start`. The class holds identity and nothing
  else: no quest, reward, or record logic.
- [x] 1.2 Add `"quest_issuer": QuestIssuer` to `PROFESSION_COMPONENT_TYPES` in
  `world/rules/profession_config.py`; confirm the existing contract test (which fails when a
  component class has no vocabulary entry) now passes with the new pair.

## 2. Rulebook and authoring

- [x] 2.1 Add a commissioner blueprint row to `world/rules/rulebook/professions.yaml` following the
  existing row shape (`key`, `components` with `default_binding`, `schedule_template`,
  `default_tier`), anchored on `quest_issuer`. Choose `person` binding — a commission travels with
  the commissioner — and state the reason in the file's row-baseline comment block.
- [x] 2.2 Enforce that every profession row's FIRST component names a class defining `service_id`:
  `load_professions` rejects such a row with a named `ProfessionConfigError`, and a contract test
  pins the shipped rulebook and the named rejection. This invariant held only by convention
  (`scripted_dialogue` also lacks the field and is never placed first); making it explicit is what
  keeps the roster-sync reuse path from raising at startup.
- [x] 2.3 Do NOT add `issuer_key` to `_IDENTITY_KWARGS` in `world/rules/profession_assembly.py`.
  That set means "must be authored and non-empty" (`missing_identity_kwargs` rejects a blank), which
  is false for `issuer_key` — absent is the valid identity form. The accepted consequence is that
  `project_row_kwargs` never projects an authored `issuer_key` onto a roster-created commissioner,
  which therefore resolves to `npc:#<pk>`; authored content keys come through the import path, which
  passes kwargs verbatim via `resolve_component_plan`.
- [x] 2.4 Extend the `components` field description in `world/imports/schema.py` so `issuer_key`
  joins the enumerated service-identity values (`service_id`, `shop_key`, `branch_key`,
  `dialogue_key`).
- [x] 2.5 Verify the existing `resolve_component_plan` path attaches an explicit `quest_issuer`
  entry alongside another profession's blueprint components with no change to
  `world/rules/profession_assembly.py`.
- [x] 2.6 Amend `_converge_service_hosts` in `world/rules/guild_economy.py` (design D5):
  person-bound service components are never convergence-candidacy evidence — the roster can
  neither claim nor re-create them — and a host carrying one is never deleted; stale place-bound
  anchors on such a host keep the ambiguous-residue warning instead of deleting the commissioner.
- [x] 2.7 Add `_flag_duplicate_issuer_keys` to `world/imports/validate.py` (design D6): a batch in
  which two valid character records author the same non-empty `issuer_key` is rejected naming the
  key, in the entity-key contract style.

## 3. Key resolution

- [x] 3.1 Add `resolve_issuer_key(host)` to `world/rules/quest_issuance.py`: return `None` for a
  host without the component; `npc:<authored>` for a non-empty validated `issuer_key`; `npc:#<pk>`
  for an absent or empty one. Read-only, no registry lookup, malformed authored key raises the
  shared grammar error.
- [x] 3.2 Confirm `resolve_local_service_host(actor, QuestIssuer)` works unchanged, including its
  no-host and ambiguous-host outcomes.

## 4. Tests

- [x] 4.1 Component-shape test: exactly the four declared fields; no mutation surface.
- [x] 4.2 Authorization tests: an NPC without the component resolves to nothing; an NPC carrying
  `Merchant` and `ScriptedDialogue` but not `QuestIssuer` resolves to nothing.
- [x] 4.3 Resolution tests: authored form, identity form, malformed authored key raises, resolution
  succeeds with no registered issuance. Also pins non-string (including falsy) issuer_key values
  rejecting without coercion (design D7) and an unpersisted host failing closed.
- [x] 4.4 Host-resolver tests: single co-located carrier resolves; zero and several carriers give the
  same outcomes as the other service components.
- [x] 4.5 Import tests: an explicit `quest_issuer` entry attaches the component with its authored
  identity; a `merchant` profession plus an explicit `quest_issuer` entry attaches both; the loader
  never invents an `issuer_key`.
- [x] 4.6 Roster-sync tests: run the guild-economy sync TWICE with a `quest_issuer`-anchored
  commissioner row present, asserting the second run reuses the host through its `service_id` anchor
  without raising and creates no duplicate. Also assert a roster-created commissioner's `issuer_key`
  is empty and resolves to the identity form. The directly constructed row is an internal
  robustness fixture (config rejects person-bound roster rows); the imported-carrier survival
  test (4.12) pairs with it.
- [x] 4.7 Contract test: a profession row anchored on a class without `service_id` fails by row name;
  every shipped row passes.
- [x] 4.8 Startup non-regression: after `sync_service_content` with no commissioner content
  authored, no existing NPC carries the new component.
- [x] 4.9 Annotate tests with `covers_requirement` against the new `quest-issuer-authorization`
  requirement IDs; add the Evennia shard entry in `.github/evennia-shards.json` for any new
  integration test module.
- [x] 4.10 Run the observability lint plus the focused component, profession, import, and issuance
  test modules in the same batch.
- [x] 4.11 Batch-uniqueness tests: duplicate authored issuer keys reject the whole batch naming the
  key; distinct keys validate clean; an unauthored (identity-form) issuer key never counts toward
  duplicates; invalid records and world entries never join the duplicate scan.
- [x] 4.12 Convergence-survival test: an imported person-bound commissioner assembled with a
  non-roster service anchor survives `sync_service_content` with its component and resolved key
  intact (design D5).
