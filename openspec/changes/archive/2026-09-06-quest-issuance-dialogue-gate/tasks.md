# Tasks: quest-issuance-dialogue-gate

## 1. Speaker gate

- [x] 1.1 Widen the speaker check in `_apply_offer_quest` (`world/rules/npc_intents.py`) from
  `GuildStaff` only to `GuildStaff` or `QuestIssuer`, still requiring the speaker to be an `NPC`.
  A speaker carrying neither fails verification with a documented reason, preserving the speech.
- [x] 1.2 Resolve the speaker's issuer key: a `GuildStaff` speaker through the shared
  `guild_issuer_key(branch_key)` constructor, a `QuestIssuer` speaker through `resolve_issuer_key`.
  No string concatenation at this call site.

## 2. Per-kind eligibility

- [x] 2.1 Guild speaker: keep the existing checks byte-for-byte — a `GuildQuestOffer` registered at
  that branch, the player registered with a canonical rank inside the offer's band, using the same
  canonical eligibility check the board applies.
- [x] 2.2 Private commissioner: eligible exactly when `resolve_issuance(quest_key, issuer_key)`
  returns an issuance. No registration gate, no rank gate, none invented — a private errand has no
  rank band.
- [x] 2.3 Dual-component speaker with an issuance registered under both namespaces for the same
  quest key: fail verification with a documented reason rather than choosing an issuer.

## 3. Assignment

- [x] 3.1 Pass the resolved issuer key into `accept_quest(actor, quest_key, issuer_key)`.
- [x] 3.2 Leave the atomic quest-log and relations snapshots, the `+1 guild` affinity credit, the
  budget-capped-write handling, and the rollback path exactly as they are.

## 4. Tests

- [x] 4.1 Guild path non-regression: every existing `offer_quest` scenario passes unchanged, and the
  assigned record now carries `guild:<branch_key>`.
- [x] 4.2 Private path: an authorized commissioner with a registered issuance assigns successfully
  with no registration and no rank check; the record carries the resolved `npc:` key and resolves to
  that commission's reward and settlement.
- [x] 4.3 Refusal paths, each asserting `applied=False`, speech preserved, no state change: a
  commissioner with no issuance for the quest key; an NPC carrying neither component even while an
  issuance exists elsewhere; a dual-component speaker with issuances under both namespaces.
- [x] 4.4 Boundary test: the AI cannot choose the issuer — the applier derives it from the speaker's
  components only, and a payload naming a quest key registered under a different issuer is refused.
- [x] 4.5 Annotate with `covers_requirement` against the modified and added `dialogue-offer-quest`
  requirement IDs.
- [x] 4.6 Run the observability lint plus the focused npc-intent, dialogue, and issuance test modules
  in the same batch.
