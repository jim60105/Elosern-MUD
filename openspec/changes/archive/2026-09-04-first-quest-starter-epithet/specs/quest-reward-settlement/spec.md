# quest-reward-settlement — delta

## ADDED Requirements

### Requirement: The first-ever reward claim grants the starter epithet atomically
`turn_in_quest` SHALL detect, before appending this claim's quest ID, that the
actor's `guild_reward_claims` list is empty — the actor's first-ever reward
claim for any quest definition (never keyed to a particular `definition_key`) —
and inside that same all-or-nothing claim transaction call
`world/rules/titles.py::grant_first_quest_epithet`, which banks the starter
epithet 「南門新客」 (`origin_quote` from `world/lore/titles.py`'s
`STARTER_EPITHET`) through the regular `bank_epithet` writer, auto-equipping an
empty epithet slot. The grant notification 「獲得異名：南門新客」 SHALL merge
into the claim response payload (`title_notifications`) and every claim surface
(CLI turn-in, the turn-in dialogue keyword, the webclient claim action) SHALL
echo those lines with the reward summary. The title attributes SHALL join the
claim transaction's snapshot set: a rolled-back claim removes the epithet.
`bank_epithet` display dedupe is the second guard — any later claim, replay, or
repeated invocation is an inert no-op granting nothing and notifying nothing.

#### Scenario: First completed claim grants the epithet
- **WHEN** a registered member with an empty claims list turns in any completed quest for the first time
- **THEN** the epithet 「南門新客」 is banked and auto-equipped in the same commit as the reward, and the response carries 「獲得異名：南門新客」 for every claim surface to echo

#### Scenario: Later claims never re-grant
- **WHEN** the same member turns in any further completed quest, including a second acceptance of the same definition
- **THEN** the reward pays normally, `title_collection` is unchanged, and no epithet notification line appears in the response

#### Scenario: A rolled-back first claim revokes the epithet
- **WHEN** any write in the first claim's transaction fails after the epithet was banked
- **THEN** wallet, inventory, merit, quest log, claims, and both title attributes equal their pre-turn-in values

#### Scenario: The grant is definition-independent
- **WHEN** the first-ever claim completes a quest whose `definition_key` is not `introductory_hunt`
- **THEN** the epithet grants exactly as for any other first claim
