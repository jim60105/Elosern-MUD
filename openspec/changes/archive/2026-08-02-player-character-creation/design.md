## Context

With `MULTISESSION_MODE = 0`, Evennia creates a `PlayerCharacter` and puppets
it while creating an account. `LivingEntity.at_object_creation()` deliberately
leaves the trait handler empty because it has no identity yet. The project has
not supplied the missing product-level step that assigns that identity.

The resulting object can receive the normal character command set while it has
no race, no adult identity, and no traits. `rest` consequently reaches the
magic-study clock stage with no `magic_level` trait. The existing import path
is intentionally unsuitable for player registration: it is an operator-facing
JSON ingestion API and does not bind a character to an account.

## Goals / Non-Goals

**Goals:**

- Make every newly registered player complete a validated character before
  gameplay commands can mutate or settle world state.
- Offer a small set of shipped presets and a custom path with player-owned
  name and identity choices.
- Keep starting characters inside race and subrace limits with a finite,
  explicit allocation budget.
- Preserve the adult invariant and the deterministic-core single-writer
  boundary.

**Non-Goals:**

- Importing, editing, deleting, or migrating characters.
- Multiple character slots, appearance editing, persona authoring, equipment,
  starting inventory, or skill selection.
- Changing combat formulas, skill multipliers, progression rules, or race
  caps.

## Decisions

### D-1: Gate the existing auto-created character until one activation commits

`Account.at_post_create_character()` will first call `super()` to preserve
Evennia's character relation, last-puppet reference, and ownership locks, then
mark the default account-owned `PlayerCharacter` as pending creation. Ownership
preflight will read the persistent `account.characters` relation, never the
session-dependent `character.account` convenience property.

Command-set resolution will derive a creation-only gate from the persistent
pending marker on every merge. That gate will use `mergetype="Replace"`, a
priority above project exits, and `no_exits`/`no_objs` so it admits only the
creation command and harmless help/quit facilities. Activation changes only
the persisted pending marker; it performs no separately fallible command-set
removal. Reconnection and reload therefore re-derive the correct command set.
No command may infer a race or silently finish the character.

This uses Evennia's existing account-to-character ownership and auto-puppeting
instead of creating a second object. Replacing the command set is preferable
to checking every gameplay command individually, because default Evennia and
future project commands are covered by the same boundary.

### D-2: Use one command with a wizard for both modes

`character` will display pending status and offer two modes. `character preset
<key>` selects a frozen, shipped `PlayerPreset`. `character create` runs a
prompted draft that collects display name, actual age, apparent age, race, an
optional compatible subrace, and allocations for the six starting axes. The
draft remains in the command session until final confirmation; cancelling,
disconnecting, or invalid input leaves the character unchanged.

The custom path deliberately permits free player text only for the display
name. The service trims it, requires 1–80 printable non-control characters,
and rejects Evennia markup delimiters before atomically assigning it to the
existing object's key; it is therefore the visible in-world identity. Race and
subrace are selected by registry key, and all mechanical inputs are numbers
validated by the deterministic creation service. This avoids turning a
narrative field into a mechanical authority.

### D-3: Put validation and writes in `world.rules.character_creation`

The command will convert its input into an immutable request and call a
deterministic service. That service will preflight ownership, pending state,
adult fields, display name, registry membership, preset content, and the
allocation before sampling magic or writing anything. It will then use a Django
transaction to replace the trait configuration and persist identity,
activation state, and the sampled magic level as one operation. On failure it
will restore the trait-handler cache and attributes, following the project's
existing multi-surface rollback conventions.

This gives commands a presentation role and retains the single-writer
boundary. It also guarantees that a rejected request cannot consume a magic
roll or leave a partially initialized character.

### D-4: Normalize a finite allocation budget around lore ranges

The six allocable axes are `hp`, `mp`, `sp`, `atk_phys`, `agility`, and
`defense`. A player starting profile will resolve each axis's lower and upper
bounds from `RaceProfile.vital_baseline` and `static_baseline`; a valid
subrace replaces vital bands and applies its static modifier after allocation,
using the same order and `round(value * (1 + modifier))` behavior as trait
construction.

For a profile with resolved pre-modifier spans, the exact allocation budget is
`floor(sum(axis_max - axis_min) / 2)`. Each requested allocation is a
non-negative integer no greater than that axis's span, and the six allocations
must sum exactly to the profile budget. The final base values are lower bound
plus allocation. This creates a race-scaled midpoint aggregate while allowing
a player to trade one strength for another; it prevents both an all-minimum
character and a character at every documented maximum, without prohibiting
individual-axis specialization.

`guild_merit` starts at zero. Skill multipliers are never allocation inputs or
stored values. The profile is derived only from immutable lore registries, so
the implementation contains no per-race balance constants.

### D-5: Record average starting magic in lore and sample a bounded integer

`RaceProfile` will gain `starting_magic_level`, the immutable average for an
adult newly created player. Initial values are `30` for humans, `10` for
beastfolk, and `300` for elves. They preserve the documented cap ratios and
admit a meaningful integral ±10% roll.

Activation calculates the inclusive integer interval with integer arithmetic,
`low = (average * 9 + 9) // 10` and `high = average * 11 // 10`, then samples
uniformly inside it. The service explicitly rejects a non-integer sample or a
sample outside both `low..high` and `0..magic_cap` before writing; it never
uses `assert` for this invariant. The resulting ranges are 27–33, 9–11, and
270–330. The random source is injected into the deterministic service for
tests; production uses a local pseudorandom source, and the sampled result is
persisted exactly once. Presets receive the same roll so a preset cannot be
used to bypass the creation rule.

### D-6: Presets are immutable data validated by the same service

`world.lore.player_presets` will contain frozen `PlayerPreset` records, each
with adult identity fields and a complete allocation vector. The catalog will
ship at least one valid preset for each selectable race. Presets do not carry
their own magic level, equipment, skills, or an escape hatch from allocation
limits. The service validates preset identity and allocation exactly as it
validates custom input before activation.

### D-7: Store adult identity on the player character

The activation service will persist `age` and `apparent_age` alongside race,
subrace, and display name. It also resets every creation-owned mechanical
surface: trait configuration, `magic_xp`, skill proficiency, skills, equipment,
inventory, wallet, quest log, guild rank, and guild merit. Both age fields must
be integers at least 18; the actual and apparent values are checked
independently. The custom wizard does not provide a default for either field,
and a preset must declare both. Creation leaves the existing shell's dbref,
account relation, location, and puppeting unchanged.

## Risks / Trade-offs

- [Command-set interactions can leak a normal command while pending] → Add
  integration tests that attempt `rest`, exit traversal, object interaction,
  combat, and creation after reconnecting and reload; the pending command set
  must reject the first four before any rules call.
- [The existing default character is already persisted before the wizard] →
  Treat it as an inert account-owned shell and make activation the only path
  that supplies traits, rather than creating or deleting another object.
- [A static allocation budget can become stale after lore tuning] → Derive it
  from registry bands at activation and test the profile against every current
  race and subrace.
- [Random creation values can make tests flaky] → Inject the integer sampler,
  test both endpoints and invalid out-of-band results, and use fixed values in
  tests; the production result is persisted and therefore replayable after
  creation.
- [A requested subrace can alter a stat after allocation] → Validate raw
  allocations against pre-modifier bands and use the established subrace order
  to produce final values, rather than applying a second unbudgeted bonus.

## Migration Plan

There are no released users and no compatibility layer or migration is needed.
New accounts start pending. Existing blank development characters can use the
same pending creation command after the change is deployed; operators may
delete test data in their normal local-development workflow.

## Open Questions

None. The preset catalog can grow without changing the creation contract.
