# Tasks: quest-issuance-generative

## 1. Compile boundary

- [x] 1.1 Replace `CompiledQuest.issuer_branch_key` with an issuance descriptor carrying the issuer
  key and the settlement mode, keeping `reward` as it is.
- [x] 1.2 `compile_quest_blueprint` maps the blueprint's declared issuer onto that descriptor,
  re-validating: the issuer key parses; a `guild:` key names a registered branch; an `npc:` key names
  a carrier authorized to issue and carries zero reward merit. Every violation raises
  `QuestCompileError` before any mutation.
- [x] 1.3 Confirm the definition-key digest is unchanged — reward and issuer stay offer-level and
  excluded — so two commissioners of identical stages still share a definition key and are
  distinguished by issuance identity, exactly as two guild branches are today.

## 2. Registration

- [x] 2.1 `register_generated_quest` dispatches on the issuer namespace: a guild issuance writes a
  `GuildQuestOffer` through `register_guild_offer`; a private issuance writes a `QuestIssuance`
  through `register_quest_issuance`. Neither store gains a second writer.
- [x] 2.2 Preserve the all-or-nothing contract: preflight all three registries' equal/conflict states
  before writing any, roll back every write if a later one fails, and leave no spawn-requirement
  entry behind on a rolled-back publication.
- [x] 2.3 `register_restored_quest` dispatches the same way through the shared preflight-and-write,
  so a conflicting entry during restore leaves no definition registered without its issuance.

## 3. Durable store

- [x] 3.1 The `GeneratedQuestStore` payload carries the issuance (issuer key, settlement, reward)
  rather than a guild-shaped `offer` section; update the serializer and `payload_to_registrations`
  (which returns the reconstructed `CompiledQuest`). The store identifies payloads by
  `(definition key, issuer key)` so two commissioners of one definition coexist durably;
  `remove_payload` takes the same composite identity.
- [x] 3.2 `_validate_restored_payload` checks the issuance binds the exact definition and that the
  namespace rules hold, raising loudly rather than registering a mismatched pair.
- [x] 3.3 `restore_generated_quests` reconstructs and registers both kinds, definition first, and
  stays idempotent across repeated restarts.
- [x] 3.4 Record that existing store contents are unreadable and must be cleared; write no migration.

## 4. Tests

- [x] 4.1 Compile tests: a private commission compiles and registers into the issuance registry with
  the guild offer registry unchanged; non-zero merit fails; an unauthorized carrier fails; two
  commissioners of identical stages share a definition key and register two distinct issuances.
- [x] 4.2 Registration atomicity tests: a conflicting issuance rolls back the definition and the
  requirements for both issuer kinds.
- [x] 4.3 Restart tests: a restored private commission resolves its reward and settlement; restore is
  idempotent across repeated restarts for both kinds.
- [x] 4.4 Annotate with `covers_requirement` against the modified `scenario-director` and
  `quest-lifecycle` requirement IDs; update `.github/evennia-shards.json` as needed.
- [x] 4.5 Run the observability lint plus the focused compile, generated-store, scenario-director,
  and bootstrap test modules in the same batch.
