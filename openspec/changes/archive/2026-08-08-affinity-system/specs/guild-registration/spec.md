## MODIFIED Requirements

### Requirement: Registration grants F rank and records one displayed-stat snapshot
`register_adventurer()` SHALL accept only an unregistered PlayerCharacter co-located with a GuildStaff
host. It SHALL read all eight trait keys through `get_display_value()`, persist the branch, current world
tick, and displayed values in `guild_registration`, set `guild_rank` to `F`, and grant +1 affinity
(`guild` source) with the GuildStaff host through the sole-writer affinity API
(`world/rules/affinity.py`) — all in one atomic operation, with the host's affinity record included
in the registration snapshot/restore surfaces so a failed registration restores it.
The branch SHALL be derived exclusively from the validated GuildStaff component; callers SHALL NOT
supply or override it. Registration SHALL NOT derive rank from either displayed or true stats.

#### Scenario: Undisguised character registers at F
- **WHEN** an unregistered character registers with local GuildStaff and has no `disguised_stats`
- **THEN** rank becomes F, every registration snapshot value equals the corresponding true trait
  value, and the GuildStaff host's affinity value rises by 1

#### Scenario: Disguise affects only the registration snapshot
- **WHEN** an elf whose true `atk_phys` is 88 registers while `disguised_stats.atk_phys` is 8
- **THEN** the snapshot records 8, rank is F, the true `atk_phys` remains 88, and the affinity
  gain still applies

#### Scenario: Registration failure is atomic
- **WHEN** persistence is fault-injected after either rank, registration metadata, or the affinity
  record is written
- **THEN** rank, registration metadata, and the affinity record — and their in-process caches —
  equal their pre-registration values
#### Scenario: Staff component is the sole branch authority
- **WHEN** registration occurs at Altoria GuildStaff
- **THEN** the stored branch equals that component's branch and no caller-provided branch input exists
