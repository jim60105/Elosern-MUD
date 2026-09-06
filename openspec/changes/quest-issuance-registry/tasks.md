# Tasks: quest-issuance-registry

## 1. Issuer key grammar

- [ ] 1.1 New module `world/rules/quest_issuance.py` with `IssuerKeyError` and a shared
  `parse_issuer_key(value) -> ParsedIssuerKey` returning the namespace, the remainder, and (for the
  `npc:#` form) the positive integer database identity. Reject unknown namespaces, a missing
  separator, empty namespace or remainder, a non-positive-integer `npc:#` remainder, and any key
  over the shared key bound. No registry lookup happens in the parser.
- [ ] 1.2 Add the two constructor helpers the later changes call —
  `guild_issuer_key(branch_key)` and `npc_issuer_key(content_key=None, pk=None)` — so no consumer
  concatenates namespace strings by hand.

## 2. Issuance value

- [ ] 2.1 `Settlement` StrEnum with exactly `COUNTER = "counter"` and `AUTO = "auto"`.
- [ ] 2.2 Frozen `QuestIssuance` dataclass carrying exactly `definition_key`, `issuer_key`,
  `reward` (the existing `QuestReward`), and `settlement`, validating in `__post_init__`: the
  definition key names a registered `QUEST_DEFINITION_REGISTRY` entry, the issuer key parses, and
  the settlement value is in the closed vocabulary.
- [ ] 2.3 Merit rule: an `npc:`-namespaced issuance with non-zero `reward.merit` raises a named
  error at construction, before any registry write.

## 3. Registry and read seam

- [ ] 3.1 `QUEST_ISSUANCE_REGISTRY: dict[tuple[str, str], QuestIssuance]` plus
  `register_quest_issuance(issuance)`: refuse `guild:`-namespaced issuances with a named error;
  treat an equal re-registration as a no-op; raise on conflicting content under an existing
  identity without replacing the original.
- [ ] 3.2 `resolve_issuance(definition_key, issuer_key)`: parse the key (letting the parser's error
  propagate), dispatch `guild:` to `get_guild_offer` and wrap the result as a `QuestIssuance` with
  `Settlement.COUNTER`, dispatch `npc:` to the registry, and return `None` for an unregistered
  identity without fabricating anything. A `GuildOfferNotFound` becomes `None`, not an exception.
- [ ] 3.3 Emit the facade boundary event for private-commission registration per the observability
  catalog, with `quest` and `issuer` context keys.

## 4. Non-regression of the guild surface

- [ ] 4.1 Confirm by inspection and test that `GUILD_OFFER_REGISTRY`, `GuildQuestOffer`,
  `register_guild_offer`, `get_guild_offer`, and `list_guild_offers` are untouched — same storage,
  same value type, same signatures.
- [ ] 4.2 Test that a `guild:` key never writes into `QUEST_ISSUANCE_REGISTRY` and that resolving a
  `guild:` key reads only the guild offer registry.

## 5. Tests and wiring

- [ ] 5.1 New focused test module `world/rules/tests/test_quest_issuance.py` covering: all three
  grammar forms, every parser rejection branch, the `Settlement` vocabulary bound, `QuestIssuance`
  construction and immutability, the unregistered-definition rejection, the merit rule in both
  directions, registry idempotency and conflict rejection, the guild-key registry refusal, and all
  four `resolve_issuance` outcomes (guild hit, private hit, unregistered miss, malformed raise).
- [ ] 5.2 Annotate each test with `covers_requirement` against the new `quest-issuance` requirement
  IDs.
- [ ] 5.3 Update `.github/evennia-shards.json` if the new test module needs an Evennia shard entry;
  a pure-unittest module needs none.
- [ ] 5.4 Run the observability lint plus the focused tests in the same batch.
