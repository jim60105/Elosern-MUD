# world/rules guide

The general deterministic engine. Every rule here must give the same result for
the same inputs and must work with every LLM service offline. Nothing in this
package calls a generative layer to decide an outcome.

Each module's first docstring line states what it owns. Read that line before
you read the body.

## Find the owner

| You are changing | Modules |
| --- | --- |
| How a skill or action resolves | `action/` (`contracts`, `gates`, `routing`, `effects/`, `costs`, `event_log`, `transaction`, `resolver`), `action_gates.py`, `action_preview.py`, `action_evidence.py`, `cast_settlement.py`, `field_cast.py`, `skill_effects.py`, `targeting.py`, `target_facts.py`, `spell_conditions.py`, `event_log.py` |
| Combat | `combat/` (d100 resolution), `combat_session/` (persistent sessions, rounds, settlement, exits), `combat_initiation.py`, `combat_modifiers.py`, `combat_beats.py`, `combat_result.py`, `combat_identity.py`, `disengage.py`, `overwhelm.py`, `defeat_aftermath/`, `field_contact.py`, `world_escape.py` |
| Monster decisions | `monster_behaviour.py`, `monster_ai/`, `monster_individual.py` |
| World time, rest, fatigue | `clock.py`, `quantum.py`, `time_skip.py`, `skip_safety.py`, `sleep_control.py`, `sleep_receipt.py`, `camping.py`, `upkeep.py`, `fatigue.py`, `mental_time.py`, `settlement_alignment.py` |
| Movement and travel | `movement.py`, `movement_edges.py`, `movement_settlement.py`, `travel_cost.py`, `travel_plan.py`, `travel_capacity.py`, `travel_events.py`, `travel_interrupts.py`, `sight.py`, `city_gates.py` |
| What the player knows of the map | `map_knowledge.py`, `map_discovery.py`, `map_district_lighting.py`, `wilderness_disclosure.py` |
| Money, items, equipment, shops | `wallet.py`, `economy.py`, `equipment.py`, `equipment_effects.py`, `item_effects.py`, `items/`, `party_inventory.py`, `shop_hours.py`, `caravan_arrivals.py` |
| Guild, exams, quest offers | `guild.py`, `guild_config/`, `guild_economy.py`, `guild_offers.py`, `guild_exams.py`, `guild_exam_request.py`, `guild_exam_restrictions.py`, `exam_schedule_holds.py`, `human_guild_hosts.py`, `quest_issuance.py`, `quest_delivery.py` |
| Church | `church.py`, `church_rulebook.py` |
| Character creation, traits, identity | `character_creation.py`, `creation_wizard.py`, `creation_messages.py`, `traits.py`, `identity.py`, `social_identity.py`, `persona.py`, `persona_edit.py`, `starting_companions.py`, `start_location.py`, `account_roster.py` |
| Skills, progression, titles, buffs | `progression/`, `lineage_query.py`, `cross_lineage_unlock.py`, `skill_ownership.py`, `titles/`, `title_view.py`, `buffs/`, `mp_flow.py` |
| Party and companions | `party.py`, `party_scope.py`, `possession.py`, `player_control.py`, `affinity.py`, `affinity_config.py`, `unlock_notices.py` |
| NPCs, dialogue, services | `npc_capabilities.py`, `npc_identity.py`, `npc_intents.py`, `npc_persona.py`, `npc_roster_validation.py`, `npc_schedules.py`, `npc_services.py`, `dialogue.py`, `dialogue_*.py`, `service_gate.py`, `service_targets.py`, `service_windows.py`, `service_messages.py`, `met_people.py` |
| Lore codex, scene visits, story effects | `lore_knowledge.py`, `scene_visits.py`, `story_effects.py`, `correspondence.py` |
| Landmark rites | `landmark_rites.py`, `landmark_rite_record.py` |
| Adult systems | `sexual_state/`, `sexual_transitions.py`, `sexual_resist.py`, `sexual_act_effects.py`, `pleasure.py`, `stored_sexual_reads.py`, `state_reactions.py`, `phase_hooks.py`, `state_derived_roll.py` |
| A read model for a client | `*_view.py` (`art_view`, `combat_view`, `service_view`, `title_view`), `status_query/`, `status_display.py`, `status_text.py`, `displayed_stats.py`, `action_preview.py` |
| Operator repairs | `gm.py` |
| Shared plumbing | `surfaces.py`, `presentation_events.py`, `rulebook/`, `dice.py`, `namegen.py`, `player_messages.py` |

## How code here is written

1. **One writer per state.** A module whose docstring says "sole writer" (for
   example `church.py` for `db.church`, `party.py`, `affinity.py`,
   `map_knowledge.py`, `lore_knowledge.py`, `met_people.py`, `mp_flow.py`) is
   the only place that state is written. To change that state, call the
   writer. Do not assign the attribute from another module, a command, a
   typeclass or a webclient action.
2. **Validate, then write once.** A multi-step write follows the order in
   `surfaces.py`: parse, validate, compute the replacement values, then apply
   every write inside one `transaction.atomic()` block. On an exception the
   database rolls back and the Evennia attribute and trait caches are restored
   with the helpers in `surfaces.py`. A half-applied result is always a bug.
3. **Numbers live in the rulebook.** Balance values are rows in
   `rulebook/*.yaml`, loaded with `rulebook.schema.load_rules` or
   `load_sectioned_rules`. Do not write a balance constant in Python and do not
   copy a rulebook value into a second place.
4. **Read models do not write.** A `*_view` or `status_query` function returns
   frozen data. It never creates a handler, a record or a default.
5. **Stored traits are literal.** Skill multipliers are applied when a value is
   resolved, never baked into a stored trait. Combat and resolution use true
   traits; `disguised_stats` is for display.
6. **Money is integer copper.** Convert units only when formatting text.
7. **Player text is Traditional Chinese with a stable code.** Rejections and
   outcomes come from `player_messages.py`, `service_messages.py` and
   `creation_messages.py`. Add a code there instead of writing prose at the
   call site.
8. **Publish after commit.** A presentation side effect is registered with
   `presentation_events.on_publication_commit`, so nothing is pushed to a
   client for a write that rolled back.
9. **Log through the facade.** A committed state change emits its boundary
   event (`action_commit`, `clock_advance`, ...) with the business identifiers
   in `context`. See "Observability" in the root `AGENTS.md`.

## Tests

- Tests are in `tests/`; a module is one test label:
  `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.<module>`
- Pure logic uses `unittest.TestCase`. Use `EvenniaTest` only when the test
  needs database objects.
- Game data comes from `world.tests.synthetic_data`
  (`synthetic_registries(...)`, `make_item(...)`, `make_skill(...)`), never
  from shipped content. Shared builders are in `tests/combat_fixtures.py`,
  `tests/rite_fixtures.py` and the `tests/_*.py` helper modules.
- State the expected number independently. Never compute it by calling the
  function under test or by copying its formula.
- A new test module needs a CI owner:
  `uv run --locked python -m tools.shard_register fix`.

## Mistakes that have happened here

- A test left a registry entry, a clock event source or a battlefield behind,
  and a later test in the same process failed. Restore every module-level
  mutation in `addCleanup`, and key fixtures by a stable identity, not by a
  database primary key.
- A rolled-back write left a stale idmapper object, and the next test read it.
  Use the cache helpers in `surfaces.py` instead of flushing the whole
  database.
- A tier default was added to a rulebook after its consumer had cached the
  resolved tuning. When you add a rulebook row, check where the table is
  resolved and cached.
- A fix read a live gauge where only a base value was being written, or the
  reverse. Check which of base, current and displayed value the owner means
  before you touch a trait.
