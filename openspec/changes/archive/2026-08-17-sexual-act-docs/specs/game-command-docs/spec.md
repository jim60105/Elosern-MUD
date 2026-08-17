## ADDED Requirements

### Requirement: The command reference documents the sexual act system
The `cast` and `combat actions` entries in `docs/game/command-reference.md` SHALL document that
性愛 (sexual act) skills are ordinary castable skills reached through the two existing commands, with
no separate syntax or command of their own. The `cast` entry's 說明 field SHALL state that a
character's unlocked 性愛 skills are cast through the same `cast <skill_key>[@<scale>][=<target_key>]`
syntax — a few basic seed acts are available from character creation, the rest once unlocked by play —
and SHALL contain the substrings `性愛` and `解鎖`. The `combat actions` entry's 說明 field SHALL
state that owned skills are grouped by category and that unlocked 性愛 acts form their own category
once their unlock requirement is met, and SHALL contain the substring `性愛`. This requirement adds
documentation content only; it changes neither entry's `語法` nor `情境` field, and the curated
manifest in `tests/test_command_docs.py` (`EXPECTED_COMMANDS["cast"]` and `["combat actions"]`) is
unchanged.

#### Scenario: The cast entry mentions unlocked sexual acts
- **WHEN** the drift contract test inspects the `cast` canonical entry's 說明 field
- **THEN** the field contains the substrings `性愛` and `解鎖`, and states that unlocked sexual-act
  skills use the same cast syntax as any other skill

#### Scenario: The combat actions entry mentions category grouping
- **WHEN** the drift contract test inspects the `combat actions` canonical entry's 說明 field
- **THEN** the field contains the substring `性愛` and states that owned skills are grouped by
  category, with unlocked sexual acts forming their own category

### Requirement: The command reference documents the resist, affinity, and status consequences
`docs/game/command-reference.md` SHALL document, in prose placed under the existing `### cast`
heading (not as a new canonical heading — a new heading with no corresponding mounted command would
be an orphan canonical entry), the parts of the sexual act system a player must understand before
casting one against another character: that unlock is per-act — a few basic acts are available from
character creation while the rest are gained by meeting their unlock conditions in play (SHALL
contain the substring `解鎖`); that a resistible act's target receives one resist roll, in or out of
combat, where a successful resist leaves that target unaffected by the cast's target effects while
the cast still consumes time and the skill's resource cost (if any), and a failed resist executes the
act against the target (SHALL contain the substrings `抵抗` and `戰鬥`); that a forced act (a failed
resist) against a companion NPC costs relationship affinity and can trigger the companion
auto-leaving the party, with the caster notified when it happens — the consequence applies to forced
acts in combat and out of combat alike, both halves shipped and archived
(`sexual-resist-turn-cost`'s `_scan_sexual_coercion` and `sexual-resist-out-of-combat`'s
`_scan_out_of_combat_sexual_coercion`) (SHALL contain the substring `好感度`); that sustained arousal,
an in-progress climax, and high exposure appear as ordinary combat condition labels while active
(SHALL contain the substrings `興奮`, `高潮`, and `露出`, matching the shipped 高度興奮敏捷與準度減損,
高潮進行中鎖定行動, and 高露出防禦減損 labels); and that 神之秘法 (divine arts) acts require a
race-eligible caster and have no counter unlock threshold (SHALL contain the substring `神之秘法`),
without asserting which individual divine-arts acts exist and SHALL NOT name any of them.

#### Scenario: The reference documents the unlock ladder
- **WHEN** the drift contract test inspects the full text of the `### cast` section (its field table
  plus the trailing prose block)
- **THEN** the section contains the substring `解鎖` and states that basic acts are available from
  character creation while the rest unlock in play

#### Scenario: The reference documents the resist and affinity consequence
- **WHEN** the drift contract test inspects the full text of the `### cast` section
- **THEN** the section contains the substrings `抵抗`, `好感度`, and `戰鬥`

#### Scenario: The reference documents the status conditions
- **WHEN** the drift contract test inspects the full text of the `### cast` section
- **THEN** the section contains the substrings `興奮`, `高潮`, and `露出`

#### Scenario: The reference documents the divine-arts race gate
- **WHEN** the drift contract test inspects the full text of the `### cast` section
- **THEN** the section contains the substring `神之秘法`, states that casting acts on that line
  requires a race-eligible caster, and names no individual divine-arts act

#### Scenario: No orphan canonical heading is introduced
- **WHEN** `test_no_orphan_canonical_entries` runs after this content is added
- **THEN** it reports no new failure, because the new prose is not preceded by any new `### <key>`
  heading

### Requirement: The overview page describes the sexual act system's discoverability
`docs/game/commands.md`'s `cast` row (in its 技能施放 category table) SHALL state that sexual-act
skills are included among castable skills, are unlocked through play, and are discoverable through
`combat actions`'s category grouping, and SHALL contain the substring `性愛`. This requirement adds no
new row and no new key, so `test_overview_links_only_documented_keys_and_all_keys`'s exact-match
between overview links and canonical-entry keys is unaffected.

#### Scenario: The overview cast row mentions sexual acts
- **WHEN** the drift contract test inspects `docs/game/commands.md`'s 技能施放 table
- **THEN** the `cast` row's description contains the substring `性愛` and mentions that such skills are
  unlocked through play

#### Scenario: The overview link set is unchanged
- **WHEN** `test_overview_links_only_documented_keys_and_all_keys` runs after this content is added
- **THEN** the set of documented keys linked from the overview page is identical to the set before this
  change
