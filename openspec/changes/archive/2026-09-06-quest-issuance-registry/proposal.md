# Proposal: quest-issuance-registry

## Why

Quest issuance is guild-only today: `GuildQuestOffer` is keyed `(definition_key,
issuer_branch_key)` and every reward, rank band, and settlement rule assumes an adventurer-guild
branch. The world needs commissions issued by ordinary NPCs — a shopkeeper's delivery run, a clue
that pays out on arrival — that live in the same quest log but are not guild quests and settle
themselves instead of at a counter.

`world/quests/` is already fully guild-agnostic (`QuestRecord` and `QuestDefinition` carry no guild
field; progress and the COMPLETED transition need no host). The coupling lives entirely in the
wrapper layer, exactly as the engine design intends: "Guild quest economics **wrap** the
deterministic quest definition rather than moving quest state into an NPC or command." This change
lands the second wrapper's data model so the record, settlement, delivery, and read-model changes
can build on it.

## What Changes

- New `Settlement` closed vocabulary: `counter` (claimed at the issuer's counter) and `auto`
  (settled inside the transaction that completes the quest).
- New immutable `QuestIssuance` value: `definition_key`, `issuer_key`, `reward`, `settlement`.
- New `issuer_key` grammar, validated by one shared parser: `guild:<branch_key>`,
  `npc:<content_key>` (authored), and `npc:#<pk>` (runtime-registered). Any other namespace,
  an empty segment, or an over-long key rejects with a named error.
- New `QUEST_ISSUANCE_REGISTRY` holding **only** `npc:`-namespaced issuances, with idempotent
  registration that rejects conflicting content under an existing identity — the same semantics
  `register_guild_offer` already has.
- New `resolve_issuance(definition_key, issuer_key)`: the single normalized read seam. A `guild:`
  key builds the view from the existing `GUILD_OFFER_REGISTRY`; an `npc:` key reads the new
  registry. Unknown identities return `None`, never a fabricated issuance.
- Validation rule: an `npc:`-namespaced issuance SHALL carry `reward.merit == 0`. Merit is guild
  currency; a private commission never grants it.
- `GUILD_OFFER_REGISTRY`, `GuildQuestOffer`, `register_guild_offer`, `get_guild_offer`, and
  `list_guild_offers` are **left unchanged**. No existing call site or test is touched.

## Capabilities

### New Capabilities

- `quest-issuance`: the issuer layer's data model — the `issuer_key` grammar, the `Settlement`
  vocabulary, the `QuestIssuance` value, the npc-namespaced registry with its idempotent
  registration and conflict rejection, the normalized `resolve_issuance` read seam, and the
  merit-free rule for private commissions.

### Modified Capabilities

(None. This change is purely additive: no existing requirement's behavior changes, and the guild
offer surface keeps its exact contract.)

## Impact

- New module `world/rules/quest_issuance.py` (or an additive section of `world/rules/guild_offers.py`
  — the design decides); no edit to the guild offer storage or API.
- New focused unit test module; `.github/evennia-shards.json` updated if a new Evennia-integration
  module is added.
- No consumer lands in this change. The registry is a deliberate forward-declared seam
  (`quest-record-issuer-key`, `quest-auto-settlement`, `webclient-quest-log-panel`, and
  `quest-issuance-generative` consume it), consistent with the project's existing practice of
  landing guarded seams ahead of their owning change.
