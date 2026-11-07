# Monster Species Names and Individual Names

**Date:** 2026-11-05
**Status:** approved design; implementation not started
**Origin:** `tmp/monster-ui-display-name-handoff.md`

## Problem

`construct_species_individual()` defaults the object `key` to the variant's
`display_name_zh`. Every player-facing surface reads `obj.key`, so wilderness
monsters are named after behavioural descriptors ("濕岸型", "守礁型"). The
species name never appears in-game.

Variant names are not creature names, but they are currently the only in-room
signal of a real combat difference: the variant selects stats, danger grade,
skill kit and behaviour. Removing them from the name must not remove them from
the game.

Bosses add a third name. Today an authored site label is passed as the object
key and leaves no trace afterwards, so nothing can tell a named individual from
an ordinary one.

## Goals

- Show the species name, or the individual name when one exists, as a monster's
  name.
- Keep the variant readable on surfaces with room for it.
- Store each fact once. Names that live in a registry are not copied to the
  individual.
- Send facts over the wire and leave display decisions to the client.
- Make the individual name a first-class nullable field that the UI, story and
  quest layers can read.

## Non-goals

- Adding a quest bound to a named boss. Only the rendering logic ships; a quest
  is a later game-data change.
- Adding species or variant entries to the in-game lore codex.
- Migrating existing rows. The database will be rebuilt.
- Showing the variant in text `look` or combat log lines.

## Data model

| Fact | Single source |
| --- | --- |
| Species name | `MonsterSpecies.display_name_zh` |
| Variant name | `MonsterVariant.display_name_zh` |
| Individual name | `Monster.individual_name` |

`Monster.individual_name: str | None` is an `AttributeProperty` with
`default=None, autocreate=False`, declared in the same style as `species_key`.
`None` means the individual has no name of its own.

`key` is not a source of any fact. Evennia requires `db_key` to be non-null and
`search()` matches on it, so it stays as the engine's search label.
`construct_species_individual()` writes it once as
`individual_name ?? species.display_name_zh`. Display code for a species-backed
monster reads the sources above, never `key`.

`MonsterSite.individual_label_zh` is renamed to `individual_name_zh`. It is the
name a site gives an individual at birth; after that the individual owns its
name. The existing validator stays: a site may declare a name only when its
composition bounds are exactly `(1, 1)`.

`construct_species_individual()` replaces its `key=` parameter with
`individual_name=`. There is no longer a way to pass an arbitrary key.
`world/rules/monster_ai/manual_campaign.py` and test fixtures that pass `key=`
move to `individual_name=` mechanically; a rule-level name bound applies only to
authored registries, so those fixtures remain legal.

A non-empty string is required when `individual_name` is supplied. Anything else
raises `MonsterConstructionError` before persistence.

### Length bound

`MONSTER_NAME_MAX_CODE_POINTS = 5` is the longest name the rail and figure plate
render without ellipsis. Registry load validation applies it to species names,
variant names and site individual names. No test pins a shipped name.

## Read model

`world/rules/monster_individual.py` gains a frozen `MonsterIdentityView` with
three fields, and one read function:

```python
@dataclass(frozen=True)
class MonsterIdentityView:
    individual_name: str | None
    species_name: str
    variant_name: str

def monster_identity_view(entity: Any) -> MonsterIdentityView | None: ...
```

The function reads the registry through the lenient `_registered_variant()` and
never raises. It returns `None` for players, NPCs, tier-only monsters, and
individuals whose variant no longer resolves.

## Wire contract

These rows gain a required, nullable `monster_identity` field:

- exploration interact `targets`
- exploration `look.entities`
- combat participants

```text
monster_identity: null | {
  individual_name: string | null,
  species_name: string,
  variant_name: string,
}
```

`display_name` remains because every entity row uses it. When
`monster_identity` is non-null, the presenter sets `display_name` to
`individual_name ?? species_name` directly from the read model. A key changed by
a GM rename therefore cannot make a payload disagree with itself.

The Python and JS validators reject a non-null identity whose `display_name`
differs from that value, and reject an empty name. When `monster_identity` is
null, `display_name` keeps its current `key` source.

`EXPLORATION_SCHEMA_VERSION` moves from 6 to 7 and
`CONTEXT_ACTIONS_SCHEMA_VERSION` from 7 to 8. The constants and validators in
`web/static/webclient/js/elosern/protocol/panels/` move with them.

The server sends no composed string.

## Client presentation

`web/webclient-app/components/monster-identity.js` is the only place that
decides how identity reads. It exports:

- `isNamedMonster(identity)`: true when `individual_name` is non-null.
- `monsterDetailTag(identity)`: `variant_name` for an unnamed individual, or
  `variant_name + species_name` for a named one; `null` without an identity.

| Surface | Unnamed | Named |
| --- | --- | --- |
| Presence rail name plate | 潮燈蟹 | 閉灣者, `data-named` |
| Figure plate name | 潮燈蟹 | 閉灣者, `data-named` |
| Rail hover or focus readout | 潮燈蟹 [守礁型] | 閉灣者 [守灣型吞潮鱷] |
| Combat target prompt | 潮燈蟹 [守礁型] | 閉灣者 [守灣型吞潮鱷] |
| Figure plate `title` and aria label | name and tag | name and tag |

- The named treatment is approved in the Storybook prototype at
  `docs/design/monster-individual-names/` and is driven by `data-named`.
- Named styling reuses rank language and adds no new colour or ornament:
  - The name takes `--gold-400` and `--f-display`, keeping the ordinary size,
    line height and spacing.
  - The rail medallion gains an inner gold rule, after `GuildRankCard`'s stamp.
  - The rail name, the readout name and the target-prompt name sit between two
    horizontal gold hairlines that fade at both ends.
  - The figure plate gains the same hairline along its top, and its brass crown
    stays single.
- The treatment avoids the client's selection cues: vertical side rules, a single
  underline, an outer ring, and a doubled crown.
- The rules are a shape cue, so a named individual does not rely on hue.
- Every rule is an overlay or background layer. A named box matches an unnamed
  box in position and size on every surface, and no name is truncated.
- `presence-rail.js` carries the identity through `railReadout()`, and
  `ExplorationReadout.vue` gains a `tag` prop.
- `stage_targets.js` carries the identity on member positions, and
  `ActionDock.vue` appends the tag to its existing `summary.tags`.
- Ambiguity between same-species variants on the rail and plate is accepted. A
  D-grade and an A-grade individual share a plate name, and the readout or
  target prompt separates them.

## Story and quest surfaces

**LLM context.** The monster record carries `individual_name`, `species_name`
and `variant_name`, so any surviving proposal or presentation consumer can
treat a named boss as a specific creature and keep the variant it previously
saw through `key`.

**Event data.** `world/rules/action/event_log.py` and `world/rules/upkeep.py`
already record `species_key` and `variant_key` for a species-backed target. Both
add `individual_name` there when it is non-null, so narrative consumers read a
fact and never guess from a label.

**Quests.** In `describe_objective_parts()`, a bound objective whose `site_key`
names a site with `individual_name_zh` renders `討伐{name}` with no note. The
`(1, 1)` composition rule makes a quantity redundant. Other bound objectives keep
their current text. No shipped quest takes this path yet, so tests use synthetic
fixtures.

## Unchanged behaviour

- Text `look`, combat log labels and map sighting labels keep reading `key`,
  which now holds the individual or species name.
- Command targeting matches `key`. `engage 濕岸型` stops working, and
  same-species individuals stay distinguishable by index.
- Identity remains `species_key` and `variant_key`. `individual_name` never
  participates in identity, resolution or balance.
- The observability freeze list is untouched. Event data is not a logging path.

## Failure handling

- Invalid `individual_name` at construction raises `MonsterConstructionError`
  and persists nothing.
- A name over the bound fails registry load.
- An unresolvable identity reads as `None`, and the row degrades to its `key`
  with no tag.
- A malformed `monster_identity` payload fails protocol validation on both sides,
  like any other panel field.

## Testing

All tests use synthetic fixtures, not shipped species or sites.

- **Construction:** the default key is the species name; a supplied name sets
  both `individual_name` and `key`; the attribute is `None` by default; an empty
  name fails with nothing persisted. This replaces the variant-label assertions
  in `world/rules/tests/test_monster_individual.py:213` and `:360-365`.
- **Read model:** ordinary, named, tier-only, non-monster and retired-variant
  cases.
- **Registry:** the name bound rejects an over-long species, variant and site
  name.
- **Presenters:** exploration and combat payloads for the same cases, including
  a monster whose `key` was changed after construction.
- **Protocol parity:** Python and JS accept the identity shape, reject a
  `display_name` mismatch, and agree on schema versions.
- **Client:** `monster-identity.js` unit tests; rail and plate render a
  five-code-point name with full DOM text; `data-named` appears only on named
  individuals; a named and an unnamed rail entry and plate share one geometry;
  the named plate works with the `target` and `acting` states; the readout and
  target prompt render the tag.
- **Story and quests:** `monster_entries` and event data carry the fields; a
  synthetic named site renders `討伐{name}`.

## Documentation

Update `docs/development/adding-monsters.md` and
`docs/development/monster-field-behaviour.md` for the renamed site field and the
new construction parameter. `openspec/specs/monster-individual-construction`
and the affected exploration, combat and quest capabilities change through the
OpenSpec proposal.

## Acceptance criteria

1. A default-constructed individual's `key` is the species name, and no default
   key is a variant name.
2. `individual_name` is null unless supplied, and it is the only stored copy of
   an individual's name besides the engine's `key`.
3. The wire carries `monster_identity` facts and no composed name or tag string.
4. The rail and plates show the individual or species name without ellipsis at
   the reference scale; the readout and target prompt show the variant.
5. Named individuals are distinct on the rail and plates by shape as well as
   colour, without reading as selected and without moving any box.
6. LLM context and event data expose `individual_name`, and a bound objective on
   a named site renders that name.
7. `uv run --locked python -m tools.contract_gate` passes, along with the test
   data lint, spec traceability, Python and JS test suites.
