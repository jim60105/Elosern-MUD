## Batch:

- depends-on: (none — dependency-free: no other monster change may land before this one, because every other change reads the registries this change creates)
- conflicts: none with `official-content-provenance` (that change is the declared downstream consumer of the species registry this change provides; it needs no edit here — its own proposal already names this catalog as its prerequisite, and its species-key wiring is its own work). File-level: `world/lore/monsters.py`, `world/lore/__init__.py` and `world/lore/sync.py` are shared with `monster-identity-construction` (which reads, never rewrites, the registries) and with `species-portrait-identity` (which reads species keys only); serialize this change first in that group. The registry test modules are new files registered fresh in `.github/evennia-shards.json`, so no shard collision with the six artwork changes, which touch only `world/art/`, `web/`, settings and deployment files.
- external-prerequisite: user balance approval for every numeric combat profile (HP/MP/SP/physical/agility/defense/magic_power) and every final guild danger grade. The bestiary approves narrative content only, so this change lands structure plus approved narrative fields with those numbers unpopulated, exactly as the balance-honesty rule permits (option b). A separate balance-approval content change will populate them; nothing here invents values.
- external-prerequisite: the six special abilities (wind grain-shaking, lamp-mimicking glow, earth burrow-packing, mana-drain on contact, fog-channeling, rock-sonance) exceed today's damage-oriented monster behaviour and the design forbids registering new skills here; they are a named external skill/behaviour-mechanics prerequisite (see design), never a fake implementation.
- external-prerequisite: the official artwork package for `monster/<species-key>/` identities is an out-of-repo deliverable of the artwork wave (`official-artwork-catalog`, `official-artwork-deployment`); this change ships keys and narrative only, no image bytes and no resolution change.

## Why

`docs/superpowers/specs/2026-10-05-monster-data-model-design.md` is approved and its layer model (species / variant / individual / placement / quest) is unimplementable today: `world/lore/monsters.py` carries only threat tiers, and wilderness population, scene materialization and DEFEAT objectives all pick monsters from `example_monsters_zh`, which is tier illustration text, not species identity. The first bestiary batch (six species, twelve named variant directions, content-approved 2026-10-05) has nowhere to live. Without stable `species_key`/`variant_key` registries there is no identity for construction, placement, quest selectors, kill accounting, or the `monster/<species-key>/` official-artwork identity that `official-content-provenance` already declares as its prerequisite.

## What Changes

- Add the read-only species and variant registries to the existing lore package (frozen dataclasses, keyed dicts, construction-time validation, idempotent startup mirror): `MonsterSpecies` with `key`, `display_name_zh`, published description/appearance/habitat prose, habitat compatibility tags, separated author-private fields (hidden truth / author explanation / unverified conjecture), `default_variant_key`, and an ordinary-vs-stronger classification; `MonsterVariant` with `key`, owning `species_key`, display name and description, threat tier, and classification — no inheritance or override chain, one complete record per variant.
- Validate identity at registry construction: a variant must belong to its species, and `default_variant_key` must name an ordinary variant of that same species. Display names and threat tiers never substitute for identity.
- Declare the numeric-combat-profile and guild-danger-grade slots as explicitly unpopulated pending user balance approval: a typed optional profile with a complete value set or nothing at all, and a partial or invented profile is a construction error. No nonzero MP/SP/`magic_power` may be inferred from flavored names or from the current low/mid tier construction, which zeroes them.
- Keep the six special abilities out of behaviour and skills: the registry may record the approved narrative boundary text, and the ability-mechanics seam is a named external prerequisite, not a skill key, not a TODO.
- Enforce the public/private projection: the published species/variant views expose only marked public fields, and author-private notes never serialize into player-facing output; unverified conjecture keeps its uncertainty marker.
- Keep habitat tags compatibility-only: no spawn decision reads them (the placement owner decides appearances in `monster-site-placement`).
- Land the approved bestiary narrative for the six species and twelve named variants as registry display strings in the canonical zh-TW prose, plus idempotent startup synchronization and boundary events through the `world.observability` facade.
- Existing tier behaviour is unchanged by this change: no caller switches to species identity here, so wilderness population, scene materialization, quest objectives and portrait resolution keep working exactly as today until their own changes land.

## Capabilities

### New Capabilities

- `monster-species-registry`: the read-only species and variant registries — frozen keyed data, identity validation (variant belongs to species, default variant is an ordinary variant of it), the balance-gated numeric and danger-grade slots, the public/private projection, habitat-as-compatibility-only, and idempotent synchronized narrative content from the approved bestiary.

### Modified Capabilities

- None. (This change adds new registry content and a new capability; no existing requirement changes. Existing `lore-registries` MonsterTier requirements and their consumers stay byte-identical, which is the point: identity is layered on, not swapped in under existing callers.)

## Impact

- Code: `world/lore/monster_species.py` (new registries + validation + published projections), `world/lore/monsters.py` (unchanged tier registry; a pointer docstring only), `world/lore/__init__.py` exports, `world/lore/sync.py` startup mirror step, `world/lore/tests/` new test modules, `.github/evennia-shards.json` shard registrations.
- Docs/lore: none beyond the design/bestiary delivery sections updated with this proposal set; `docs/game/commands.md` and `docs/game/command-reference.md` are untouched because no player command changes.
- No gameplay mechanics change, no database migration, no compatibility layer, no new skills, no art assets. Downstream owners: `monster-identity-construction` (individuals), `monster-site-placement` (placement), `monster-quest-objectives` (quests), `species-portrait-identity` (art identity), and the pre-existing `official-content-provenance` (official reference producer).
