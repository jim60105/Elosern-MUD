# quest-issuance Specification

## Purpose
Defines the issuer layer's data model: the `issuer_key` grammar, the `Settlement` closed vocabulary, the immutable `QuestIssuance` value, the private commission registry (`QUEST_ISSUANCE_REGISTRY`) with idempotent registration and conflict rejection, the normalized `resolve_issuance` read seam, and the merit-free rule for private commissions.

## Requirements

### Requirement: An issuer key is a namespaced, validated identity

The issuer layer SHALL define exactly three issuer-key forms and one shared parser that validates
them: `guild:<branch_key>` for an adventurer-guild branch, `npc:<content_key>` for an authored
character identity, and `npc:#<pk>` for a runtime-registered character identity. The parser SHALL
return the namespace and the remainder as separate values. A key carrying an unknown namespace, no
separator, an empty namespace, an empty remainder, an `npc:#` form whose remainder is not a
positive integer, or a total length exceeding the shared key bound SHALL reject with a named error
rather than being coerced or truncated. The parser SHALL perform no registry lookup, so an issuer
key is well-formed or not independently of whether any issuance exists for it.

#### Scenario: Each of the three forms parses into namespace and remainder
- **WHEN** `guild:guild_branch_altoria`, `npc:grey_granny`, and `npc:#1234` are parsed
- **THEN** each yields its namespace and remainder, and the `npc:#1234` form additionally reports
  the positive integer database identity `1234`

#### Scenario: A malformed issuer key rejects with a named error
- **WHEN** a key with an unknown namespace, no separator, an empty namespace, an empty remainder,
  an `npc:#` remainder that is not a positive integer, or a length over the shared bound is parsed
- **THEN** the parser raises a named error and returns nothing

### Requirement: Settlement is a closed two-value vocabulary

The issuer layer SHALL define `Settlement` as exactly two values: `counter`, meaning the reward is
claimed at the issuer's counter through the existing turn-in path, and `auto`, meaning the reward
is settled inside the transaction that transitions the record to COMPLETED. A value outside this
vocabulary SHALL reject; the vocabulary SHALL NOT be widened by a caller-supplied string.

#### Scenario: The vocabulary admits exactly two values
- **WHEN** the `Settlement` vocabulary is inspected
- **THEN** it contains exactly `counter` and `auto`, and constructing it from any other string
  raises

### Requirement: A quest issuance is an immutable value binding one definition to one issuer

The issuer layer SHALL define `QuestIssuance` as a frozen value carrying exactly `definition_key`,
`issuer_key`, `reward`, and `settlement`. `reward` SHALL be the existing immutable `QuestReward`
value, so the issuer layer introduces no second reward shape. Construction SHALL validate that the
definition key names a registered quest definition, that the issuer key parses, and that the
settlement value is in the closed vocabulary; a violation SHALL raise a named error before any
registry write.

#### Scenario: A valid issuance constructs and is immutable
- **WHEN** a `QuestIssuance` is constructed for a registered definition with a parseable issuer key,
  a valid `QuestReward`, and a vocabulary settlement value
- **THEN** the value is created and every field assignment on it raises

#### Scenario: An unregistered definition key rejects
- **WHEN** a `QuestIssuance` is constructed for a definition key absent from the quest definition
  registry
- **THEN** construction raises a named error and nothing is registered

### Requirement: A private commission never grants guild merit

An issuance whose issuer key is `npc:`-namespaced SHALL carry `reward.merit == 0`. Merit is guild
currency and is earned only through the adventurer guild; a non-zero merit on a private commission
SHALL reject with a named error at construction, before any registry write. A `guild:`-namespaced
issuance SHALL keep the existing guild reward validation unchanged.

#### Scenario: A private commission with merit rejects
- **WHEN** an `npc:`-namespaced issuance is constructed with a reward carrying non-zero merit
- **THEN** construction raises a named error and the registry is unchanged

#### Scenario: A private commission with zero merit is accepted
- **WHEN** an `npc:`-namespaced issuance is constructed with a reward carrying copper, items, and
  zero merit
- **THEN** construction succeeds

### Requirement: The issuance registry stores private commissions idempotently

The issuer layer SHALL own `QUEST_ISSUANCE_REGISTRY`, a process-local mapping keyed
`(definition_key, issuer_key)` that stores `npc:`-namespaced issuances only. Registering a
`guild:`-namespaced issuance SHALL reject with a named error, because guild offers keep their own
sole writer. Registering content equal to what is already stored under an identity SHALL be a
no-op; registering conflicting content under an existing identity SHALL raise before replacing the
original — the same idempotency and conflict semantics the guild offer registry already applies.

#### Scenario: Registering the same private commission twice is a no-op
- **WHEN** an identical `npc:`-namespaced issuance is registered a second time
- **THEN** the call succeeds and the stored value is unchanged

#### Scenario: A conflicting registration raises without replacing
- **WHEN** an issuance with a different reward is registered under an identity already present
- **THEN** the call raises a named error and the originally stored issuance is unchanged

#### Scenario: A guild-namespaced registration is refused
- **WHEN** a `guild:`-namespaced issuance is passed to the private-commission registry writer
- **THEN** the call raises a named error and nothing is stored

### Requirement: One normalized read seam resolves an issuance for any issuer kind

The issuer layer SHALL expose `resolve_issuance(definition_key, issuer_key)` as the single read
path every consumer uses. A `guild:`-namespaced key SHALL resolve through the existing
`GUILD_OFFER_REGISTRY` lookup and return a `QuestIssuance` view carrying that offer's reward and
`Settlement.COUNTER`. An `npc:`-namespaced key SHALL return the stored private commission. An
identity with no registered issuance SHALL return `None`; the seam SHALL NOT fabricate an issuance,
a reward, or a settlement value. A malformed issuer key SHALL raise the parser's named error rather
than returning `None`, so a caller bug is distinguishable from an absent commission.

#### Scenario: A guild key resolves to a counter-settled view of the registered offer
- **WHEN** `resolve_issuance` is called for a definition offered at a registered guild branch
- **THEN** it returns a `QuestIssuance` whose reward equals the registered `GuildQuestOffer` reward
  and whose settlement is `counter`

#### Scenario: A private key resolves to the stored commission
- **WHEN** `resolve_issuance` is called for a registered `npc:`-namespaced identity
- **THEN** it returns exactly the stored `QuestIssuance`

#### Scenario: An unknown identity resolves to nothing
- **WHEN** `resolve_issuance` is called for a definition and issuer with no registered issuance
- **THEN** it returns `None` and no issuance is fabricated

#### Scenario: A malformed issuer key raises rather than resolving to nothing
- **WHEN** `resolve_issuance` is called with an issuer key that does not parse
- **THEN** it raises the parser's named error

### Requirement: The guild offer surface is unchanged by the issuer layer

The issuer layer SHALL NOT modify the storage, value type, writer, or reader contract of
`GUILD_OFFER_REGISTRY`, `GuildQuestOffer`, `register_guild_offer`, `get_guild_offer`, or
`list_guild_offers`. Guild offers keep exactly one writer, private commissions keep exactly one
writer, and the two stores are joined only by the read seam, so they cannot drift.

#### Scenario: Guild offer registration and lookup behave identically after the issuer layer lands
- **WHEN** a guild offer is registered and read back through the existing guild API
- **THEN** the stored value type, idempotency, conflict rejection, and board eligibility results are
  identical to their behavior before this change
