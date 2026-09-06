# Proposal: quest-issuance-generative

## Why

Every generated quest is a guild quest. `compile_quest_blueprint` produces a `CompiledQuest` carrying
a mandatory `issuer_branch_key`, `register_generated_quest` writes a `GuildQuestOffer`, and the
durable store's payload has an `offer` section shaped exactly like one. And the dialogue `offer_quest`
applier rejects any speaker lacking `GuildStaff`.

So the whole private-commission stack — the issuance registry, the `QuestIssuer` component, automatic
settlement, delivery — is unreachable from the systems that actually create content and hand quests
to players. This change connects them.

## What Changes

- `CompiledQuest` carries an issuance descriptor (issuer key and settlement) instead of a mandatory
  guild branch, so a blueprint can compile to either a guild offer or a private commission.
- `register_generated_quest` and `register_restored_quest` dispatch on the issuer namespace: a
  `guild:` issuance writes a `GuildQuestOffer` exactly as today; an `npc:` issuance writes a
  `QuestIssuance`. Both keep the existing idempotency and conflict-rejection semantics.
- The durable `GeneratedQuestStore` payload carries the issuance rather than a guild-shaped offer, and
  `restore_generated_quests` reconstructs both kinds. **BREAKING** for existing generated-quest store
  contents; the project has no released users and no migration is written.
- Blueprint validation rejects a private commission carrying non-zero merit, matching the issuance
  rule, and rejects an issuer key naming no authorized carrier.

The `offer_quest` dialogue gate is deliberately NOT part of this change. Widening an AI-reachable
boundary belongs in its own reviewable unit, and bundling it here would exceed one workday; it is
`quest-issuance-dialogue-gate`.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `scenario-director`: the deterministic compile boundary produces an issuance rather than a
  mandatory guild branch, and `register_generated_quest` dispatches on the issuer namespace while
  keeping its all-or-nothing preflight-and-rollback contract. (`quest-blueprint` needs no delta — it
  covers the runtime definition type, which is unchanged; the compile and registration contract lives
  in `scenario-director`.)
- `quest-lifecycle`: generated quest definitions resolving after a restart now covers private
  commissions as well as guild offers.

## Impact

- `world/quests/compile.py`: `CompiledQuest`, the payload serializer and reconstructor, and both
  registration paths.
- `world/quests/bootstrap.py`: the restore path.
- Existing `GeneratedQuestStore` contents become unreadable; developers clear the store.
- Depends on `quest-issuance-registry` (the registry and grammar), `quest-issuer-component` (the
  authorized-carrier check), and `quest-record-issuer-key` (blueprints that compile to a private
  commission are only reachable once a record can name one).
- The definition-key content digest is unchanged: reward and issuer stay offer-level and excluded
  from it, so two blueprints with identical stages and different commissioners still share a
  definition key and are distinguished by their issuance identity — exactly as two guild branches are
  today.
