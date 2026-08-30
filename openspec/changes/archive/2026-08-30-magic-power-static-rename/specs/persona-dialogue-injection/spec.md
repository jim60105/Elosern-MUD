## MODIFIED Requirements

### Requirement: The no-leak validator binds a per-call bounded secret set including disguise true values
The reply no-leak check SHALL be installed for a call whenever its secret set is non-empty —
independently of whether an affinity context exists — and SHALL validate speech against that
per-call set: the affinity value and cap (when present) plus the true trait values of `atk_phys`,
`agility`, `defense`, `magic_power`, and `hp` when the NPC has an active `disguised_stats` record
whose value for that key differs from the true trait value. All five values SHALL be read from the
traits' current `.value` (for `hp`, the current gauge value, not the maximum). A reply whose
speech contains any bound secret as a decimal integer substring (fullwidth digit forms folded via
NFKC normalization) SHALL be treated as a validation failure, retried within the budget, and on
budget exhaustion degrade to `None` rather than present the leak. The binding SHALL be per call
through the request descriptor so interleaved calls never cross-contaminate; stage names SHALL
remain allowed; and when no disguise is active and no affinity context exists the set SHALL be
empty and no leak check SHALL be installed.

#### Scenario: A reply echoing a disguised true value is retried
- **WHEN** an NPC with an active disguise (true `atk_phys` 88 disguised as 60) receives a reply
  whose speech contains "88"
- **THEN** the output is rejected by the no-leak validator and retried within the budget, while a
  speech containing "60" passes

#### Scenario: The leak check fires without any affinity record
- **WHEN** an NPC with an active disguise faces a player with no affinity record
- **THEN** the call still installs the no-leak validator over the disguise true values, and a
  reply echoing one of them is rejected and retried, while a player-facing conversation that
  never echoes them proceeds normally

#### Scenario: hp is protected at its current gauge value
- **WHEN** an NPC has a disguise whose `hp` differs from the true current `hp.value` (and
  `hp.value != hp.max`)
- **THEN** the current `hp.value` is bound as a secret and a reply echoing it is rejected, while
  the maximum is not treated as the protected value

#### Scenario: No disguise adds no extra bindings
- **WHEN** the NPC has no `disguised_stats` record or every disguise value equals the true value
- **THEN** the secret set is exactly the affinity value and cap (or empty when no affinity
  context exists), and existing affinity-only leak behavior is unchanged

#### Scenario: The secret set is per-call isolated
- **WHEN** two calls with different disguise/affinity contexts run concurrently
- **THEN** each reply is validated only against its own call's secrets, never the other call's
  numbers
