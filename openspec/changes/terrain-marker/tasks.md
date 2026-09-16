## Batch order (earth wave — integration contract in ./design.md D4/D5)

0. Predecessors: none — this change is wave-first and owns the terrain-marker fact, the marker
   buff lifecycle and the `buff:<key>` DamagePolicy seam. `on-hit-counter-damage` is file-disjoint
   EXCEPT the shared `world/rules/combat.py` `_handle_damage` (its `physical_hit` dispatch leg in
   the staged `apply()`, ~85 lines from this change's policy-decision hunk — disjoint hunks, same
   function): the supervisor SEQUENCES the two merges, this change first. `earth-spell-catalog`
   is strictly after BOTH merge and authors data only.

## 1. Marker clause on the definition grammar

- [ ] 1.1 Inspect current source/exported references (codegraph/LSP) for `load_buff_definitions`/`BuffDefinition`, `entity_active_buffs`, `remove_by_selector`, the `DamagePolicy.__post_init__` predicate validator, `matches_target_predicate`, and every `combat_session.py` settlement write of `fled_ids`/`knocked_out_ids` and session teardown before editing.
- [ ] 1.2 Add the validated top-level `marker` field to `BuffDefinition` and `load_buff_definitions`: closed vocabulary `{"ground"}`; malformed values (element names, booleans, numbers, other strings) fail the load naming the offending definition key; rows without the field load bit-identically. This change ships ZERO live marker rows in `buffs.yaml` (catalog owns data).

## 2. Battlefield-exit extinguishment

- [ ] 2.1 Implement the marker sweep on the existing removal path (`remove_by_selector`-equivalent instance removal, zero damage/revive writes): consult only definitions declaring `marker: ground`.
- [ ] 2.2 Wire the sweep at the three already-persisted transitions in `world/rules/combat_session.py`: newly-fled participant, newly-knocked-out participant, and session end (win/loss/withdraw teardown). One observability facade boundary line per swept removal; non-marker instances are never visited (control-buff behavior byte-identical).

## 3. The `buff:<key>` dynamic-fact predicate seam

- [ ] 3.1 Extend `DamagePolicy.__post_init__`: accept `buff:<key>` entries ONLY when the key is in `BUFF_DEFINITIONS`; keep every other namespaced form and every bare-entry rule (ELEMENT_REGISTRY ∪ COMBAT_TRAITS_VOCABULARY, duplicate rejection) failing with the existing message shapes; add the independent `unconditional_defense_bypass: bool` field (default False, rejected or accepted per design D3.5 — well-formed only with a non-empty predicate, the shipped conditional `bypass_defense` semantics unchanged); update `test_namespaced_predicate_entries_raise` in-place so its non-`buff:` rejections stay verbatim while the blanket colon-pin retires with the widened requirement.
- [ ] 3.2 Extend `matches_target_predicate`: `buff:`-named entries match iff the target holds a live (unexpired, non-paused) instance of the named definition, read through the shipped no-create `entity_active_buffs` reader; static facts never satisfy `buff:` entries and vice versa; any-match-once semantics unchanged; widen the module docstring's fact-source list with the requirement text.
- [ ] 3.3 Wire `unconditional_defense_bypass` in `_handle_damage`'s policy read: defense subtraction is skipped for every target when True, independent of predicate match; the multiplier stays predicate-conditional.

## 4. Behavioral evidence and integration

- [ ] 4.1 Synthetic behavior module for the marker lifecycle (suggested `world/rules/tests/test_terrain_marker.py`): hazard rate ticking through real tick/upkeep for the authored synthetic duration; flee, knockout and session-end sweeps observed through real `combat_session` settlement each with a non-marker control buff persisting unchanged; still-active holder's marker surviving rounds until expiry; malformed marker values failing the definition load.
- [ ] 4.2 Synthetic behavior module (or additions to `world/rules/tests/test_conditional_damage.py`, whichever the shipped module layout favors) for the predicate seam: `_handle_damage` strikes against live/expired/absent synthetic instances flip the multiplier exactly once per strike; composition with static facts stays any-match-once; `buff:<unknown>`, `terrain:cracked`, bare unknowns each rejected at construction. No data-echo, key-set or row-mirror assertions anywhere (ratified NON-GOAL).
- [ ] 4.3 Register each new non-browser test module in exactly one shard in `.github/evennia-shards.json`; verify the ownership optimization contract test.
- [ ] 4.4 Run the focused labels below after editing stops; `tools.observability_lint check` in the same batch; `tools.test_data_lint check`; `tools.spec_traceability check`; `openspec validate terrain-marker --strict`. Canonical IDs via `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-sync; annotate exactly the tests establishing `terrain-marker::a-ground-marker-buff-row-makes-holding-it-the-canonical-standing-on-it-fact`, `terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield`, the MODIFIED `buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate` and `skill-effect-model::conditional-damage-policies-compose-without-double-matching`.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_terrain_marker world.rules.tests.test_buffs world.skills.tests.test_effects world.rules.tests.test_conditional_damage world.rules.tests.test_action_evidence world.rules.tests.test_combat_session_flow world.rules.tests.test_combat_session_persistence world.rules.tests.test_stateful_spells
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate terrain-marker --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. `world.rules.tests.test_terrain_marker` is the intended synthetic module owned by this change, not an existing-test claim. No full local suite/browser/aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn.
