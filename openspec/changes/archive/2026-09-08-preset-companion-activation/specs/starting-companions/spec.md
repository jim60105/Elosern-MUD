# starting-companions delta

## ADDED Requirements

### Requirement: Preset activation builds, seeds, and binds every declared companion atomically
`activate_player_character` SHALL, for each `StartingCompanion` the selected
preset declares, build the companion NPC, seed its affinity toward the
activating player at the declared value, and bind it as a party companion —
all inside the same `transaction.atomic()` block that writes the player's own
identity, traits, skills, inventory, and equipment. A preset declaring no
companions SHALL behave exactly as before.

The companion step SHALL run after the player's own attribute writes, because
the builder places the NPC at `player.location` and `join_party` requires
co-location and a persisted player key. It SHALL run before the activation's
portrait finalization so the ordering of the existing steps is otherwise
unchanged.

The binding SHALL go through `world/rules/party.py::join_party`, which remains
the sole writer of party membership; activation SHALL NOT assign
`player.db.party` or `npc.db.party_member` directly. The affinity seed SHALL go
through the seed writer in `world/rules/affinity.py`, which remains the sole
module writing affinity values.

Any failure in the companion step — a build error, a rejected join, or a
refused seed — SHALL delete every companion NPC built during this activation and
re-raise, so the whole activation rolls back and no partially formed companion
survives. A companion SHALL NOT be best-effort: a character that arrives without
the companion its card declares silently contradicts the card the player chose.

Because the declared seed value is above the rulebook `invite_threshold`, the
party auto-leave recheck SHALL never dismiss a companion on arrival.

#### Scenario: Choosing a twin starts the game with the other in the party
- **WHEN** a pending player activates `yuna_darknight`
- **THEN** an NPC built from `yuka_darknight` exists at the player's location, `player.db.party` contains its dbid, its `party_member` names the player, and its affinity toward the player is the declared value

#### Scenario: The pairing is symmetric
- **WHEN** a pending player activates `yuka_darknight` instead
- **THEN** an NPC built from `yuna_darknight` joins the party under the same rules

#### Scenario: A preset without companions is unchanged
- **WHEN** a pending player activates any preset declaring no companions
- **THEN** activation writes exactly what it wrote before this change and `player.db.party` is empty

#### Scenario: A failed companion step rolls the whole activation back
- **WHEN** a failure is injected into the build, seed, or join of a declared companion
- **THEN** activation raises, the character remains pending with no identity, trait, or inventory state, no companion NPC is persisted, and `player.db.party` is unset

#### Scenario: The companion occupies one of the four party slots
- **WHEN** a player who started with one declared companion invites additional NPCs
- **THEN** the four-companion bound counts the starting companion, and the fifth join is rejected by the existing gate

#### Scenario: A dismissed starting companion stays re-invitable
- **WHEN** the player dismisses the starting companion with `leave`
- **THEN** the NPC remains in the room with its seeded affinity intact, and because that value is above the invite threshold the ordinary `invite` command can bind it again

#### Scenario: The arrival is never auto-dismissed
- **WHEN** the party auto-leave recheck runs immediately after activation
- **THEN** the companion's seeded value is above `invite_threshold` and the binding survives
