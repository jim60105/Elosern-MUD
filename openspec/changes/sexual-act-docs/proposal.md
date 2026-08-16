## Why

`docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md` §4.2 names `sexual-act-docs` as
the last of the six fully-parallel batch-6 tracks, scoped to `docs/game/commands.md` and
`docs/game/command-reference.md`, depending only on `B8` (`sexual-act-seeds`). `B8` and every proposal
this track structurally needs have landed and archived: `sexual-act-seeds`, five of the six catalog
lines (`sexual-catalog-solo/shame/partner/combat/interspecies`), and the in-combat half of the resist
chain (`sexual-resist-contest`, `sexual-resist-turn-cost`, `sexual-resist-cast-wiring`). Two adjacent
proposals are **not** archived yet and this change deliberately does not depend on or document their
behavior: `sexual-catalog-divine-core`/`sexual-catalog-divine-mutators` (神之秘法's seven individual
acts — `world/skills/sexual_acts/divine.py` still ships `DIVINE_ACTS: tuple = ()`, empty) and
`sexual-resist-out-of-combat` (the out-of-combat half of the affinity/auto-leave consequence —
`world/rules/cast_settlement.py` has no coercion-scanning function today). Both are catalog-data or
mechanism gaps, not documentation gaps, so their absence does not block this proposal; it only bounds
what this proposal is allowed to claim (see Non-Goals in design.md). The docs track itself was never
scheduled after B8 unblocked it, and it never got folded into any of the catalog proposals (each of
those is explicitly scoped to one line module and nothing else, per the overview's D-11/D-12
file-ownership discipline).

The result is a gap in an existing, tested documentation contract, not a missing feature. The
`game-command-docs` capability already requires `docs/game/command-reference.md` to be "the player-facing
contract for every typed in-game command," and its `cast` requirement was already extended once before,
for element-mastery freeform scaling, in the same in-place style this proposal repeats. `cast` and
`combat actions` are the only two commands a player ever needs to reach every already-shipped sexual act
(acts are ordinary `SkillDef` rows — see `sexual-act-registry`'s design D-1), but neither entry says
anything about how a 性愛 act is discovered, that a resistible act can be resisted, or that forcing one
on a companion in combat costs affinity and can end the party membership —
`sexual-resist-turn-cost` (archived) wires exactly that. A player has no in-game or documentation surface
that explains any of this before it happens to them.

## What Changes

- Extend the `### cast` entry in `docs/game/command-reference.md`: state that a character's unlocked
  性愛 (sexual act) skills are cast through the identical `cast <skill_key>[@<scale>][=<target_key>]`
  syntax once unlocked by play — no new syntax, no new command, no change to the curated manifest's
  `cast` row in `tests/test_command_docs.py`.
- Extend the `### combat actions` entry: state that the listed skills are grouped by category, and that
  unlocked 性愛 acts form their own category (sub-grouped by line) exactly as any other skill category
  once a character has met that act's unlock requirement.
- Add a prose block under the existing `### cast` heading, below its field table (not a new `###`
  canonical heading — a new heading with no matching mounted command would fail
  `test_no_orphan_canonical_entries`), documenting what a player needs to know before ever casting a
  性愛 act against another character:
  - Unlock is play-driven: nothing beyond the baseline `divine_sexual_arts` cast-gate skill is
    available at character creation.
  - A resistible act's target gets one resist roll, in combat or out of it (already wired everywhere by
    `sexual-resist-cast-wiring`): success wastes the caster's turn and the act does not execute; failure
    executes it.
  - Forcing a companion NPC **in combat** (a failed resist during a fight) costs relationship affinity
    and can trigger the companion auto-leaving the party; the caster receives a message when that
    happens. This is deliberately scoped to combat: the matching out-of-combat consequence is proposed
    by `sexual-resist-out-of-combat`, which has not landed, so this proposal does not claim it exists.
  - Sustained arousal, an in-progress climax, and high exposure surface as ordinary combat condition
    labels (高度興奮敏捷與準度減損、高潮進行中鎖定行動、高露出防禦減損) while active, exactly like any
    other buff/debuff.
  - 神之秘法 (divine arts) acts require a race-eligible caster — the pre-existing `divine_sexual_arts`
    gate skill and its `RaceProfile.can_use_divine_arts`/`_step1_divine_arts_gate` check predate every
    proposal in this design set and are unaffected by which catalog acts have landed.
- Update the `cast` row's description in `docs/game/commands.md`'s 技能施放 table: mention that
  sexual-act skills are included among castable skills, unlocked through play, and discoverable through
  `combat actions`'s category grouping.
- Add one `ADDED Requirement` delta to the `game-command-docs` spec, shaped exactly like the existing
  "cast command reference documents the optional scale token" requirement, so the new content is
  protected by `tests/test_command_docs.py` the same way every other documented command fact is.

No backward compatibility or migration concerns: this is a documentation-only change to two Markdown
files plus their protecting spec delta; it reads already-shipped, unchanged runtime behavior and writes
no code.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `game-command-docs`: adds a requirement that the `cast` and `combat actions` reference entries, and
  the `cast` row in the overview page, document the sexual act system — unlock-by-play, the resist
  contest, the in-combat affinity/party consequence of a forced act, the visible status conditions, and
  the divine-arts race gate.

## Impact

- **Modified files:** `docs/game/command-reference.md`, `docs/game/commands.md`.
- **New test coverage:** `tests/test_command_docs.py` gains assertions for the new `cast`/`combat
  actions` content, added under this change's tasks.
- **Reads (no changes) from:** `world/rules/sexual_resist.py` (resist contest, `auto_comply`),
  `world/rules/combat_session.py::_scan_sexual_coercion` (the **in-combat-only** affinity/auto-leave
  consequence and its player notification), `world/rules/rulebook/status_display.yaml` (the three
  condition labels quoted above), `world/skills/sexual_acts/` and
  `world/rules/sexual_state.py::SexualState.unlocked_act_keys()` /
  `world/skills/sexual_acts/__init__.py::unlocked_act_keys_for()` (unlock gating),
  `world/rules/combat_view.py::group_skill_views` (the category grouping `combat actions` renders) —
  every one of these already shipped and archived; none changes.
- **Dependencies:** `sexual-act-seeds`, `sexual-catalog-solo/shame/partner/combat/interspecies`, and
  `sexual-resist-contest/turn-cost/cast-wiring` (all archived) — this proposal only documents existing,
  shipped behavior and adds no new one. **Not** a dependency: `sexual-catalog-divine-core/mutators` or
  `sexual-resist-out-of-combat` (neither archived; neither's behavior is claimed by this proposal's new
  prose — see the Why section and design.md's Non-Goals).
