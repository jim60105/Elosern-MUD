## Context

`_handle_set_disguise` requires `event_context["disguise"]` and writes it through
`world.rules.skill_effects.apply_disguise_effect(entity, overrides)`, which is the classified runtime
writer in the disguise boundary ledger. The only production supplier of that key is
`commands/action.py`, which special-cases `status_disguise` and passes the caller's *existing*
`disguised_stats` back in. `get_display_value()` is the single sanctioned reader, and the displayed
combat five are `atk_phys`, `agility`, `defense`, `magic_power`, `hp`. See `proposal.md` — Why for
motivation.

## Goals / Non-Goals

**Goals:**

- A veil cast that actually changes what observers see, with no caller-supplied numbers.
- Keep every existing boundary invariant: one accessor, one writer module, no combat module reading
  the layer.

**Non-Goals:**

- Seeing through a veil. `divine-veil-reveal` owns that, including the divine/mundane provenance
  marker.
- Player-chosen disguise values (see D2).
- Any change to appearance prose, guild-registration snapshots, or the NPC-dialogue perception path.
  Those read the layer and keep reading it unchanged.

## Decisions

### D1: The veil renders the mundane ceiling, read from the race registry

The recipe sets each displayed combat five key to the top of the corresponding mundane band declared by
`RACE_REGISTRY["human"]` (`RACE_REGISTRY["human"].static_baseline` for `atk_phys`, `agility`, `defense` and `magic_power` —
all four axes live on that one `StaticBand`, and `StaticTier.magic_band` on the tier registry is a
different, tier-scoped field this recipe does NOT read — plus
`RACE_REGISTRY["human"].vital_baseline.hp`'s ceiling for `hp`). No literal appears in the code — the
registry is the source of truth, exactly as the project's balance-constant rule requires. The result is
deterministic, reproducible, and lore-true: a veiled elf reads as an exceptional human, which is
precisely what "精靈能在人類社會低調行動" asks for.

*Alternative rejected:* deriving from the veiled entity's own true values by a fixed divisor. It leaks
the true magnitude through the ratio and produces different answers for monsters, companions and
players.

### D2: No player-supplied numbers

Letting the caster type displayed values needs a command-syntax extension, a webclient option surface,
and validation that the values are plausible — and it hands players a knob to render themselves as
anything. The derived recipe needs none of that and cannot be abused.

### D3: Self-cast toggles against a DIVINE veil only; a mundane veil is refreshed, not lifted

Removal is otherwise impossible until the reveal line's chain end, which would trap a self-veiled
player behind their own face for most of a chain. But an unconditional toggle is wrong: three shipped
preset cards own `status_disguise`, and two of them also start the game wearing an authored
`disguised_stats` declaration. Under an unconditional toggle their very first self-cast — the natural
first action for a player activating the line — would STRIP that authored veil and expose true stats,
breaking the wave's own worked example (精靈能在人類社會低調行動).

The rule is therefore provenance-scoped: a self-cast lifts a veil this verb itself placed (divine) and
applies over anything else (mundane, or unveiled). It toggles only what it owns.

*Alternative rejected:* toggling on any target regardless of provenance. It would let the veil verb
strip another caster's veil, which is the reveal line's job, and would make two chain poles redundant.

### D3a: Provenance is written here, not in `divine-veil-reveal`

D3 needs the record, so this change owns writing it; `divine-veil-reveal` owns *consuming* it. The
record lives beside the display mapping rather than inside it: the mapping's keys are validated as a
subset of trait keys by the import schema and consumed key-by-key by `get_display_value()`, so
smuggling a source marker into it would break that contract and every consumer's assumption. An entity
with no record reads as mundane, which makes every pre-existing authored veil correct with no
migration.

*Alternative rejected:* inferring provenance from the values ("do they match the mundane recipe?"). It
is ambiguous the moment an authored preset declares the same numbers.

### D4: The handler derives; the writer still only writes

`apply_disguise_effect` keeps its narrow contract (assign `entity.db.disguised_stats`, touch nothing
else, mention no trait expression) and the derivation lives in a separate helper in the same module.
The boundary test's writer ledger therefore needs no new entry, and the "no reference to entity.traits"
scenario on the writer stays true.

### D5: Dropping the required context key is what makes the skill castable at all

With the derivation internal, `set_disguise` needs no `event_context`, so preflight and the shared
preview stop rejecting it and `commands/action.py`'s special case becomes dead code and is removed.

## Risks / Trade-offs

- **A veiled entity whose true stats are below the mundane ceiling looks stronger, not weaker** →
  accepted: the veil's job is to hide what you are, not to look weak, and the reader is display-only so
  nothing in combat changes.
- **Preset-authored disguises and cast veils now write the same attribute with different recipes** →
  they always did; this change makes the runtime recipe deterministic instead of a no-op refresh, marks
  which recipe wrote the live veil, and leaves the authored seeders untouched.
- **A new persisted attribute some rollback path forgets** → it is registered everywhere
  `disguised_stats` already is, and a rollback test asserts both restore byte-equal together.
- **Self-toggle can be mistaken for a failed cast** → the resolver's event log reports the applied and
  lifted cases distinctly; a test asserts both paths report.
