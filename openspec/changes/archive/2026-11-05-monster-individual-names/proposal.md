# Proposal

## Why

Every species-backed monster is named after its variant ("濕岸型") because construction copies the variant's descriptor into the object key, so the species name never appears in-game. The variant is still the only in-room signal of a real combat difference, and an individual name given to a rare single monster leaves no trace after construction, so the UI, story and quest layers cannot treat that monster as someone specific.

## What Changes

- A monster's key defaults to its species name; the variant name no longer names anything.
- `Monster` gains a nullable `individual_name`, the only stored copy of an individual's own name. `key` remains Evennia's required search label and is never a source of truth.
- **BREAKING** `construct_species_individual()` replaces `key=` with `individual_name=`.
- **BREAKING** `MonsterSite.individual_label_zh` becomes `individual_name_zh`.
- **BREAKING** The `exploration` panel moves to schema version 7 and `context_actions` to version 8. Exploration targets, `look.entities` and combat participants carry a required, nullable `monster_identity` of facts. The server sends no composed name or tag.
- The client owns how identity reads: rail and plates show the name, while the hover readout and target prompt show a variant tag.
- A named individual gets a shared treatment built from existing rank language, which moves no box and does not read as selection.
- LLM monster entries and defeat evidence expose identity facts, and a bound objective on a named site renders that name.
- Registry load validation bounds species, variant and site individual names to what the rail and plates render without ellipsis.

There is no data migration. The development database will be rebuilt. No quest game data is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monster-individual-construction`: default key, the nullable individual name, the identity read model, and defeat evidence.
- `monster-site-placement`: a designated individual receives an individual name.
- `monster-species-registry`: display name length bound.
- `webclient-exploration-menu`: exploration schema version 7 and `monster_identity`.
- `webclient-context-actions`: `context_actions` schema version 8.
- `webclient-context-actions-suggestions`: the suggestions envelope and client mirror at version 8.
- `webclient-combat-menu`: participant `monster_identity`, the target prompt tag, and the named plate.
- `webclient-presence-rail`: the rail's named treatment and readout tag.
- `quest-detail-view`: a bound objective on a named site renders the name.
- `action-options-layer`: monster entries carry identity facts.

## Impact

- **Rules and data:** `world/rules/monster_individual.py`, `typeclasses/monsters.py`, `world/lore/monster_species.py`, `world/lore/monster_placement.py`, `world/maps/monster_sites.py`, `world/rules/combat_view.py`, `world/rules/action/event_log.py`, `world/rules/upkeep.py`, `world/quests/describe.py`, `world/rules/monster_ai/manual_campaign.py`.
- **Presenters and LLM:** `web/webclient/presentation/exploration.py`, `web/webclient/presentation/combat_panel.py`, `server/option_proposal_service/situation.py`, `world/ai/action_options/context.py`, `world/ai/action_options/prompt.py`.
- **Client:** `web/static/webclient/js/elosern/protocol/`, `web/static/webclient/js/elosern/exploration_menu.js`, `web/webclient-app/stores/elosern/stage_targets.js`, and `PresenceRail.vue`, `presence-rail.js`, `FigurePlate.vue`, `figure-plate.js`, `ExplorationReadout.vue`, `ActionDock.vue`, plus a new `monster-identity.js`.
- **Docs and fixtures:** `docs/development/adding-monsters.md`, `docs/development/monster-field-behaviour.md`, and every Python, Node and Storybook panel fixture.
- **Design references:** `docs/superpowers/specs/2026-11-05-monster-individual-names-design.md` and `docs/design/monster-individual-names/`.
