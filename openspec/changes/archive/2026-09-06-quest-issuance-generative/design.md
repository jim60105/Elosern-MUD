## Context

`compile.py` produces `(definition, GuildQuestOffer, requirements)`; the durable store mirrors that
shape; `offer_quest` rejects any speaker without `GuildStaff`. The private-commission stack is
therefore unreachable from content generation and from dialogue.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §4.4 and the
generative-pipeline gap noted in its §3.

## Goals / Non-Goals

**Goals:**

- A blueprint can compile to either issuer kind.
- Both kinds survive a restart through the durable store.

**Non-Goals:**

- No change to the definition-key digest, which deliberately excludes reward and issuer.
- No prompt or blueprint-schema redesign beyond carrying the issuer.
- No dialogue-gate widening — that is `quest-issuance-dialogue-gate`, split out so an AI-boundary
  change is reviewed on its own rather than inside a large refactor.

## Decisions

### D1: Dispatch at registration, not a merged store

`register_generated_quest` chooses the writer by namespace and each store keeps its single writer.
This preserves the property `quest-issuance-registry` established: guild offers and private
commissions cannot drift because neither has a second writer.

### D2: The digest stays as it is

`_definition_key` deliberately excludes reward and issuer so that two blueprints with identical
stages share a definition and are distinguished at the offer level. That is exactly the property
private commissions need — two shopkeepers issuing the same errand share a definition and differ by
issuance. Folding the issuer into the digest would fragment the definition registry and break the
existing scene-requirement dedup.

### D3: The durable store's identity is (definition key, issuer key)

Two commissioners of identical stages share one definition key and register two distinct issuances,
so one payload per definition cannot persist them: `append_payload` would reject the second as a
conflict. The store therefore identifies each payload by `(definition.key, issuer_key)` — equal
content under one identity is a no-op, differing content under one identity is a conflict, and two
identities under one definition coexist as separate entries. `remove_payload` takes the same
composite identity, so a rolled-back publication removes only its own payload. Existing store
contents become unreadable (payload shape change); developers clear the store, no migration.

### D4: One publication path for both registration entries

`_publish_registration` is the single preflight-and-write used by `register_generated_quest` and
`register_restored_quest` alike: it preflights the definition, the namespace's own store, and the
spawn requirements before writing any, writes definition first (the `QuestIssuance` constructor
requires the registered definition), then the issuance, then the requirements, and rolls back every
entry it added on a defensive failure. The restored path keeps its own entry point (it never
touches the store) but no longer writes before validating, so a conflicting requirements entry
during restore cannot leave a definition registered without its issuance.

## Risks / Trade-offs

- **The durable store's payload shape changes** → Existing store contents become unreadable. Stated
  in the proposal; developers clear the store. No migration, per the project's no-released-users rule.
- **`CompiledQuest` shape change ripples into the director's tests** → Bounded to the compile,
  registration, store, and director test modules, all enumerated in the tasks.
