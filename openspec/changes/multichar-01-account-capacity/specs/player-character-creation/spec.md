# Delta spec: player-character-creation (multichar-01-account-capacity)

## ADDED Requirements

### Requirement: An account owns up to a configured number of independently created characters
The deployment SHALL configure the account character capacity through Evennia's
`MAX_NR_CHARACTERS` setting, derived from the `ELOSERN_MAX_CHARACTERS` environment knob with a
default of `5` and an inclusive 1-to-10 bound. An account SHALL be able to hold up to that many
player characters simultaneously, each carrying its own independent `creation_pending` lifecycle,
its own canonical identity attributes, and its own creation-gate cmdset resolution: activating one
character SHALL NOT clear another's pending marker, and a pending sibling SHALL NOT restrict an
activated character's command surface. Every character created through
`Account.create_character` SHALL receive the project account hook's pending marker, exactly as the
account's first auto-created shell does. A creation request beyond the configured capacity SHALL
be refused by the slot check without creating a character object, and the refusal SHALL be
reported to the caller rather than raised.

#### Scenario: An account holds several characters at once
- **WHEN** an account creates characters up to the configured capacity
- **THEN** every one of them appears in `account.characters`, each is marked pending creation, and
  each resolves its own creation-only command gate

#### Scenario: The capacity is enforced without side effects
- **WHEN** an account at the configured capacity requests one more character
- **THEN** the request returns the slot-limit error, no character object is created, and
  `account.characters` is unchanged

#### Scenario: Activation is per character
- **WHEN** an account owning two pending characters activates one of them through the
  deterministic-core activation
- **THEN** that character becomes activated with its chosen key and identity, and the other
  character remains pending with its own draft and gate intact

#### Scenario: The capacity knob is deployment-configurable
- **WHEN** the server is started with `ELOSERN_MAX_CHARACTERS=2`
- **THEN** an account can hold two characters and the third creation request is refused by the
  slot check
