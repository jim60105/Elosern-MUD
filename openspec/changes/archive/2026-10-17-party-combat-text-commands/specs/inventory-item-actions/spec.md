# Spec Delta

## MODIFIED Requirements

### Requirement: Text clients expose the same deterministic item operations
The player command surface SHALL provide `使用 <item_key> [target]` with alias `use` and
`裝備 <item_key>` with alias `equip`. These commands SHALL pass only the parsed item key, and for
`使用` the optional parsed target token, into the same deterministic APIs used by UI adapters.
Both commands SHALL be available in exploration and active combat. Active-combat use SHALL confirm the commander draft entry; companion use SHALL be available through combat command with an explicit actor token. Equip remains commander-only and free. Command additions and syntax
SHALL update both `docs/game/commands.md` and `docs/game/command-reference.md` in the same
change.

#### Scenario: Telnet healing matches WebClient healing
- **WHEN** equivalent injured actors in exploration use the same potion through the text command and `inventory.use`
- **THEN** both paths produce the same eligibility, HP, consumption and exploration-time outcomes

#### Scenario: Text equipment toggle uses exact item semantics
- **WHEN** a text client toggles a held accessory by item key
- **THEN** the same named accessory is equipped or unequipped under the five-slot rule without duplicating mutation logic

#### Scenario: Telnet targeting matches WebClient targeting
- **WHEN** equivalent actors in exploration use the same single-scope item on the same target, once through
  `使用 <item_key> <target>` and once through `inventory.use` with a `target_key`
- **THEN** both paths resolve the same target, apply the same effects, and consume the same resources

#### Scenario: A missing target renders the stable reason
- **WHEN** a text client runs `使用` on a single-scope item with no target argument
- **THEN** the no-target rejection renders in Traditional Chinese through the shared reason surface and
  nothing is consumed

#### Scenario: Combat use costs one round and equip costs none
- **WHEN** a text-client combat use is accepted before the draft is complete and, separately, a text-client equipment toggle completes
- **THEN** the combat use saves only the commander entry with no round/time/item consumption; the equipment toggle consumes no round

#### Scenario: Stable rejections match UI reason semantics
- **WHEN** a text command hits a stable rejection such as no-target or invalid-target
- **THEN** it renders the same Traditional Chinese reason semantics as the corresponding UI
  action

#### Scenario: Final text item selection has graphical command parity
- **WHEN** equivalent actors submit the same final item selection through combat command and guarded combat.command
- **THEN** both complete the same party draft and resolve the item at its actor initiative position with the same targets, costs and once-only round result


