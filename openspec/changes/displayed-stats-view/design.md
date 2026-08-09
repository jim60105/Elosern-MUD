## Context

`disguised_stats` is the display-only disguise layer (master design D2). Its only sanctioned
reader, `get_display_value()` (`world/rules/traits.py:192-202`), serves exactly three consumers:
appearance rendering, guild-registration snapshots, and appraisal — with the docstring naming
"appraisal items". Two consumers are live today (appearance via the look/status read model, and
the guild-registration snapshot at `world/rules/guild.py:210`, the only production
`get_display_value()` call site); the third is a forward-declared seam kept by the accessor
docstring and the boundary contract test (`world/rules/tests/test_guild_registration.py:198`).

The owner decided the appraisal consumer is a direct system surface, not an item: the player reads
any present living target's displayed combat values straight from `look <target>`. No item, no NPC
service, no see-through-disguise mechanic.

Target look flows through `caller.at_look(target)` (`typeclasses/characters.py:47`), which
`NPC` already extends to append the affinity stage line (`typeclasses/npcs.py`); the same shared
appearance path feeds the text 「看」 command, the onboarding `at_look` hook, and the WebClient
`explore.look` action.

## Goals / Non-Goals

**Goals:**
- Render the displayed combat five (`atk_phys`, `agility`, `defense`, `magic_level`, `hp`) through
  `get_display_value()` for any explicitly targeted present living entity.
- Identical output across the text command and the WebClient look action via one shared renderer.
- Keep the forbidden-caller boundary intact: combat, resolution, and damage never read displayed
  values.
- Amend the design doc and main specs so the documentation matches the implementation.

**Non-Goals:**
- Appraisal items or appraiser services (explicitly dropped for the direct view).
- Viewing true values or any see-through-disguise mechanism (forbidden by D2).
- A combat-time target stat panel (the combat surface already carries `context_actions`).
- Displaying `mp`, `sp`, or `guild_merit` in the block.
- Structured WebClient panel fields (the block ships as text; a structured panel is a future seam).

## Decisions

### D1: The block lives in a new `world/rules/displayed_stats.py` as `display_stat_block(entity) -> str | None`
One renderer, fixed key order (`atk_phys`, `agility`, `defense`, `magic_level`, `hp`), one
`label：value` row per key, every value via `get_display_value()`, using the canonical
character-panel labels (`生命` / `攻擊` / `敏捷` / `防禦` / `魔法階級`). Returns `None` for
non-living targets so `look` appends nothing.
*Alternatives considered:* placing it in `world/rules/status_query.py` — rejected: that module is
frozen no-create ("never constructs `entity.traits`"), and the accessor reads traits through the
lazy handler, so the renderer needs a module not bound by that contract. A dedicated module also
keeps the frozen read model untouched. The `hp` row renders the gauge's current value (what the
accessor returns); a current/max form is a future balance decision, not part of this contract.

### D2: The block appends in the shared target-appearance path, not in each command
`PlayerCharacter.at_look(target)` / the looked-at object's `get_display_desc(looker)` is the single
funnel for text 「看」, the `at_look` hook, and `explore.look`. Appending `display_stat_block(self)`
in a `LivingEntity.get_display_desc` override — after the description, before onboarding guidance —
guarantees byte-identical output across all three entry paths (the same guarantee
`localized-appearance` already makes for the affinity stage line; the NPC override's `super()`
chain yields description → block → affinity stage line). The onboarding `at_look` beat detection is
untouched: it fires on the hook itself, not on block content.
*Alternative considered:* appending in each command/adapter separately — rejected: three call
sites would drift; the affinity stage-line precedent already routes through the shared path.

### D3: The block appears only for explicitly named targets, never for room look
The design contract distinguishes `look` (room) from `look <target>`. Appending on the
target-look path only keeps room look unchanged and avoids noise.
*Alternative considered:* showing the block on room look for every present entity — rejected:
room look is spatial narrative, not a stat screen.

### D4: The block implements the appearance-rendering consumer; the consumer wording is unchanged
The block is D2's first consumer — appearance rendering (`look`) — now genuinely implemented via
`get_display_value()`. The three-consumer contract keeps its exact wording (appearance rendering,
guild registration records, appraisal items); the spec update states that appearance rendering is
implemented through the block and that appraisal items MAY remain deferred. The accessor docstring
and the forbidden-caller boundary stay identical. The master design D2/§5.2 note is amended to
record the block as the implemented appearance-rendering consumer.
*Alternative considered:* renaming "appraisal items" to the block and claiming three implemented
consumers — rejected after review: the block is a look-path appearance consumer, and counting it
as both appearance rendering and a third consumer would misstate the implemented boundary; the
deferral for appraisal items is retained honestly.

### D5: The accessor is hardened against malformed disguise records
`get_display_value()` SHALL treat a non-mapping `disguised_stats` (e.g. an integer or boolean) as
"no disguise" and fall back to the true trait value instead of raising. The renderer additionally
omits — never raises on — a missing or malformed trait row. A regression test covers the
non-mapping disguise record.
*Alternative considered:* guarding only inside the renderer — rejected: the accessor is the single
sanctioned disguise read, so its own tolerance belongs in the accessor, and other future consumers
get the same protection.

## Risks / Trade-offs

- [The block reveals an entity's displayed power, which could read as a stat-screen leak for
  undisguised entities] → Mitigation: values ARE the displayed values (true when not disguised);
  this is the intended system mechanic per owner decision, and the combat/resolution boundary
  keeps it presentation-only.
- [Appending in the shared appearance path could disturb onboarding beat output] → Mitigation: the
  block appends before guidance and only on living targets; the onboarding look-beat scenario
  stays as a regression test.
- [Command-docs drift contract] → Mitigation: `docs/game/commands.md` / `command-reference.md`
  and `tests/test_command_docs.py` are updated unconditionally in the same change.
- [WebClient look could diverge from text look] → Mitigation: D2's single funnel makes both paths
  call the identical renderer; a parity test asserts equal output.

## Migration Plan

No migration. The project is unreleased with zero users; the change adds output and renames a
documented consumer contract, both backward-compatible in code.

## Open Questions

- None blocking. Whether the block later becomes structured WebClient panel fields, and whether a
  future item/service reuses the same renderer as a paid convenience, are deferred decisions; the
  renderer is the shared seam either way.
