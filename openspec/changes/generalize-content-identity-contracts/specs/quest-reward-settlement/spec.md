# Spec Delta

## MODIFIED Requirements

### Requirement: The first-ever reward claim grants the starter epithet atomically
`turn_in_quest` SHALL detect, before appending this claim's quest ID, that the
actor's `guild_reward_claims` list is empty — the actor's first-ever reward
claim for any quest definition (never keyed to a particular `definition_key`) —
and inside that same all-or-nothing claim transaction call
`world/rules/titles.py::grant_first_quest_epithet`.

#### Scenario: First completed claim grants the epithet
- **WHEN** a registered member with an empty claims list turns in any completed quest
- **THEN** the configured starter display and origin are banked and an empty epithet slot auto-equips in the reward commit; every claim surface echoes 「獲得異名：」 followed by that display

#### Scenario: Later claims never re-grant
- **WHEN** the same member turns in any further completed quest, including a second acceptance of the same definition
- **THEN** the reward pays normally, `title_collection` is unchanged, and no epithet notification line appears in the response

#### Scenario: A rolled-back first claim revokes the epithet
- **WHEN** any write in the first claim's transaction fails after the epithet was banked
- **THEN** wallet, inventory, merit, quest log, claims, and both title attributes equal their pre-turn-in values

#### Scenario: The grant is definition-independent
- **WHEN** the first-ever claim completes a quest whose `definition_key` is not `introductory_hunt`
- **THEN** the epithet grants exactly as for any other first claim

#### Scenario: The grant banks the starter epithet through the regular writer
- **WHEN** the first-claim grant runs inside the claim transaction
- **THEN** the regular writer banks the authored starter display and origin basis and auto-equips only an empty epithet slot

#### Scenario: The grant notification merges into the claim response and echoes everywhere
- **WHEN** the first-ever claim succeeds
- **THEN** the grant notification carrying the configured display joins title_notifications; CLI, dialogue keyword and webclient claim echo it with the reward summary

#### Scenario: Title attributes join the claim transaction's snapshot set
- **WHEN** the claim transaction takes its snapshot set
- **THEN** the title attributes join it, so a rolled-back claim removes the epithet

#### Scenario: Display dedupe is the second guard against re-grants
- **WHEN** a later claim, replay, or repeated invocation reaches the grant path
- **THEN** `bank_epithet` display dedupe makes it an inert no-op granting nothing and notifying
  nothing
