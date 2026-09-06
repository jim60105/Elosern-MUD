# player-combat-session delta

## MODIFIED Requirements

### Requirement: A round and its settlement form one atomic persistence unit
A combat round's writes — all entity effects, the EventLog entries, the
round advance, and, on a hostile-defeat terminal outcome, the complete
defeat aftermath (violator departure, weak buff grant, and the adult
phases contributed by later changes) — SHALL commit in one database
transaction together with the `settled_tick` marker and the session-record
clearing. If any part fails, no partial state SHALL be observable: the
battlefield, the participants' attributes, the session record, and every
aftermath write SHALL all match the pre-round state.

#### Scenario: Settlement failure leaves no trace
- **WHEN** settlement fails after staging effects
- **THEN** the session record still shows the previous settled tick, every entity's attributes are unchanged, and no defeat-aftermath write (departure, buff, HP floor) is observable

#### Scenario: Defeat aftermath commits with its round
- **WHEN** a hostile defeat settles
- **THEN** the `settled_tick` marker, the session clearing, and the whole aftermath are visible or absent together

### Requirement: The knocked-out player settles the session as defeat
If the player is in the battlefield's knocked-out set at the round cap or
when the round otherwise ends without a side eliminated, the session SHALL
settle with outcome `defeat` — the defeated player SHALL be settled at HP
1 (the nonlethal floor applied by the defeat aftermath), never left at a
0-HP persisted statue.

#### Scenario: Cap reached with the player knocked out
- **WHEN** the player is in the knocked-out set when ROUND_CAP completes
- **THEN** the session settles with outcome `defeat` and the player's stored HP equals the aftermath floor `1` before the recovery phase advances it
