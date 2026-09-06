# Proposal: quest-issuance-dialogue-gate

## Why

`_apply_offer_quest` in `world/rules/npc_intents.py` rejects any speaker that is not an `NPC`
carrying `GuildStaff` with a `branch_key`. So even after private commissions exist, are authored, and
are registered, no NPC can actually hand one to a player in conversation — the whole
private-commission stack stays unreachable from dialogue.

This is the last connection needed, and it is the one that touches the AI boundary, so it is
separated from the content-pipeline work in `quest-issuance-generative` and reviewed on its own.

## What Changes

- The speaker gate widens from "`GuildStaff` only" to "`GuildStaff` or `QuestIssuer`". This is not a
  loosening: `QuestIssuer` is authored data, so only NPCs an author deliberately marked can issue,
  and the applier still verifies a registered issuance at the speaker's resolved issuer key before
  any write.
- Eligibility is per issuer kind. A guild speaker keeps the registered-offer, registration, and
  rank-band checks byte-for-byte. A private commissioner is eligible exactly when an issuance is
  registered at its resolved key — a private errand has no rank band, so no registration or rank gate
  applies and none is invented.
- A speaker carrying both components with an issuance registered for the same quest key under both
  namespaces fails verification rather than the applier picking one. Silently choosing would make the
  reward and settlement mode depend on an arbitrary precedence rule.
- The applier passes the speaker's resolved issuer key into `accept_quest`, so the created record
  names the exact issuance whose reward and settlement govern it.
- The existing atomic snapshot, affinity credit, budget-cap handling, and rollback behavior are
  unchanged.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `dialogue-offer-quest`: the intent's deterministic verification admits an authorized private
  commissioner alongside a guild branch host, with the private path's own eligibility rule, and the
  applier names the resolved issuance when assigning.
- `npc-dialogue`: the applier-routing requirement's `offer_quest` prose and its two offer-quest
  scenarios no longer describe a `GuildStaff`-only gate; they name the authored issuing authority
  and per-kind eligibility instead. Routing and failure semantics are unchanged.

## Impact

- `world/rules/npc_intents.py`: `_apply_offer_quest` verification and the `accept_quest` call.
- No change to the intent's payload, the whitelist, the speech-preserved failure mode, or the
  affinity path.
- Depends on `quest-issuance-registry` (the resolve seam), `quest-record-issuer-key` (the
  `accept_quest` issuer argument), and `quest-issuer-component` (the authorization carrier).
  `quest-issuance-generative` is a sibling, not a dependency: this change verifies whatever issuances
  exist, however they were registered.
