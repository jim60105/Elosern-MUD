# Proposal

## Why

World canon states that every elf is female (`docs/lore/overview.md`, 性別與生殖 and the 真相
bullet 「精靈全族皆為女性，成因是與三位女神的直系血脈連結」). The deterministic core still treats
race and sex as independent channels, on **both** sides of the world:

- Player side: `preflight_character_creation` accepts `sex="male"` for `race="elf"`, a preset card
  may declare any vocabulary member, and `CHARACTER_SCHEMA_V1` permits every `SEX_VALUES` member
  for every race, so a player can create or import an elf the world's own canon says cannot exist.
- NPC side: the five official NPC creation paths (JSON import; place-registry service hosts; quest
  scene instantiation through the LLM/dream scenario-director pipeline; starting companions;
  published scene-package encounters) declare **no sex at all**. They therefore land every elf NPC
  on `LivingEntity.sex`'s `"other"` default — including dream-generated scene and encounter NPCs —
  and nothing anywhere checks the combination.

## What Changes

- Add a per-race permitted-sex declaration to the lore race registry:
  `RaceProfile.allowed_sexes: tuple[str, ...]` (dataclass default `SEX_VALUES`; the elf declares
  `("female",)`). `SEX_VALUES` and `DEFAULT_SEX` are unchanged, so the sex-vocabulary capability
  keeps its current contract.
- Add one deterministic seam, `world/rules/identity.py`, owning the whole rule: `permitted_sexes()`,
  `resolve_sex(race_key, sex)` (an omitted sex resolves to `DEFAULT_SEX` when the race permits it,
  otherwise to the race's single permitted sex; a member the race forbids raises `IdentityError`),
  and `ensure_entity_sex(entity, sex=None)`, which writes the resolved value and is the only
  production writer of an NPC's sex.
- Route every creation path through that seam: the import loader, the place-host sync, the shared
  quest/scene/encounter spawn, the starting-companion builder, and the player creation validator
  (which keeps its own `CharacterCreationError` surface and stable rejection code while delegating
  the rule itself).
- Keep the AI layer state-free: the scenario-director/LLM blueprint stays sex-less and the
  deterministic instantiator supplies the sex, because `world/ai/` must never write state and a
  blueprint sex field would carry exactly one legal value for an elf.
- Enforce the same set at the authored-data boundaries: the preset registry load validator (an elf
  card declaring a non-female sex fails at import) and the place registry (an elf host declaring a
  non-female `host_sex` fails at load).
- Keep the WebClient and the legacy creation panel unchanged: the server already returns a named
  rejection whose Traditional Chinese message the overlay renders, and an elf form saved without an
  explicit sex reads back with the resolved value, so no client rule is added and the `creation`
  panel stays at version 6.
- Update the two developer-facing guides in the same change: `docs/development/adding-npcs.md`
  (the path table and mechanism paragraph, the host question, the NPC card rules, the CLI note) and
  `docs/development/adding-player-presets.md` (the race/subrace question, the load-time validator
  table row, the common-mistakes entry), each kept factually consistent with the requirements.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lore-registries`: `RaceProfile` gains `allowed_sexes` and the elf's declaration, plus the
  registry invariant that every set is non-empty and drawn from the canonical vocabulary.
- `living-entity-hierarchy`: the bounded-sex attribute requirement gains the race bound, the
  single-seam resolution, the per-path scenarios, and the blueprint-stays-sex-less clause.
- `player-character-creation`: three requirements gain the race-bounded sex rule (custom identity,
  preset activation, and the omitted-sex normalization / accepted-vocabulary scenarios).
- `import-validation`: one added requirement bounds an imported record's sex by its race.
- `settlement-place-registry`: one added requirement bounds an authored host's sex by its host race.
- `webclient-character-creation-ui`: the draft-storage requirement states the race-permitted
  default instead of an unconditional `DEFAULT_SEX`, with the rejection and the panel contract
  otherwise untouched.
- `npc-name-generation`: the race-level roll is bounded by the race's declared sex set.
- `preset-authoring-docs`: the guide's validator and mistake tables must document the new rule.

## Impact

Production files: `world/lore/races.py`, `world/rules/identity.py` (new), `world/rules/character_creation.py`,
`world/rules/creation_messages.py`, `world/rules/guild_economy.py`, `world/rules/starting_companions.py`,
`world/lore/player_presets/validation.py`, `world/lore/settlements/places.py`,
`world/imports/loader.py`, `world/imports/validate.py`, `world/quests/materializer.py`,
`world/rules/namegen.py`.

Tests: `world/rules/tests/test_identity.py` is the only **new** module and MUST be registered in
`.github/evennia-shards.json` in the same change; every other test joins an existing registered
module. No browser test is added, so `.github/browser-shards.json` stays untouched.

Docs: `docs/development/adding-npcs.md` and `docs/development/adding-player-presets.md`.

The one new player-facing string (the Traditional Chinese rejection line) is **human-reviewed**:
`review.md` in this change directory names the exact text, its canon basis and the checklist. Its
wording is deliberately outside the specs — the requirements pin the stable code and the shared
message table, never the prose.

No new log event is added (see design D8), and `tools/observability_freeze.json` is untouched.

Persistence: the project is unreleased with no users, so this change adds **no migration and no
repair path** for any already-persisted male elf character or NPC. Any such row is a development
artifact and is discarded with the development database, per `AGENTS.md`'s no-backward-compatibility
stance.

This change extends `docs/superpowers/specs/2026-09-08-player-preset-field-parity-design.md` §7's
contract — that no change adds to or alters `SEX_VALUES` or `DEFAULT_SEX` — without weakening it,
and it honours `docs/superpowers/specs/2026-09-03-npc-namegen-design.md` §5.1's rules-layer stance
(`sex` stays a `SEX_VALUES` member or `None`) while narrowing which member a race may resolve.
