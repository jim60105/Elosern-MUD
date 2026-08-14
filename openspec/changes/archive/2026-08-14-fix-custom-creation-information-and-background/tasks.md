## 1. Human subraces and preset reassignment

- [x] 1.1 Add the five human social-class subraces (`human_royal`, `human_noble`, `human_wealthy`, `human_commoner`, `human_laborer`) to `world/lore/races.py` `SUBRACE_REGISTRY` with display/common names, specialty text, zero-sum `static_modifiers`, and `population=None`, following the D1 table and the `Subrace` dataclass contract
- [x] 1.2 Add regression assertions to `world/lore/tests/test_races.py`: every race has at least one subrace (including `human`), the five human entries exist with the documented names, and each human entry's `static_modifiers` sum to zero
- [x] 1.3 Update `world/lore/tests/test_races.py` `test_registry_membership` and any subrace-count/consistency assertions for the new registry size and the human entries
- [x] 1.4 Reassign the three human presets in `world/lore/player_presets.py` to human subraces (`violet_altoria` → `human_royal`, `lidzia_rosenthal` → `human_noble`, `human_wanderer` → `human_commoner`) and update `world/lore/tests/test_player_presets.py` accordingly
- [x] 1.5 Run a repository-wide sweep of every creation-facing `subrace=None` fixture (Telnet tests, `creation_wizard` `(None,) + subrace_keys` profile construction, web action/presentation payloads and draft normalization, browser seed/panel fixtures, AI proposal matrix, `PlayerPreset.subrace` typing/validation) and migrate them to real subraces; finish with a `git grep subrace=None` verification that only the internal sentinel in `resolve_starting_profile` and generic trait helpers remains
- [x] 1.6 Require `subrace` in the character import schema (`CHARACTER_SCHEMA_V1.required`) and reject a missing/blank/unregistered/incompatible subrace in the import semantic check, so an imported character without a subrace is a hard rejection; add import validation tests

## 2. Deterministic rules: required subrace, allocation briefing source, background field

- [x] 2.1 Reject a missing/empty/incompatible `subrace` in custom mode in `world/rules/character_creation.py` `preflight_character_creation` and `_validate_allocations` path, with a stable `CharacterCreationError` message; keep `resolve_starting_profile` tolerant of `None` for internal robustness
- [x] 2.2 Add the optional bounded `background` to `CharacterCreationRequest` (custom mode only), validate it as a ≤ `MAX_PERSONA_FIELD_LENGTH` text field (blank allowed) in preflight, and persist it at activation into `entity.db.persona["background"]` inside the same all-or-nothing transaction
- [x] 2.3 Extend `world/rules/creation_wizard.py` draft storage: `save_custom_draft` accepts and stores the optional `background`; `_normalize_draft` accepts the custom-draft background with its bound; `_request_from_draft` forwards it; the draft fingerprint and reconnect behavior include it
- [x] 2.4 Add a deterministic `world/rules/persona_edit.py` (or extend `world/rules/persona.py` with a write function) `update_background(character, text)` that validates the bound, creates the import-card-shaped persona record when none exists, preserves every existing persona key (including unknown keys), writes only the `background` key (empty clears it), and performs no trait/identity/clock writes; update the `world/rules/persona.py` module docstring to state that `PersonaStore` is read-only and persona records are written only by the import loader or the `world/rules` deterministic services
- [x] 2.5 Add `world/rules` tests: custom preflight rejects missing subrace; activation persists `background` in the persona record; draft save/reconnect preserves the background; `update_background` sets and clears the field (including on a character with no persona record) without touching other state; persona write failure still rolls back activation
- [x] 2.6 Add end-to-end background-journey tests through `creation_wizard`: background alone (no concept), background then concept-apply, concept-apply then custom save, and activation — `persona["background"]` equals the entered text at every step and the concept persona block survives when the race matches

## 3. Telnet command surface: wizard prompts, briefing, background, and the new command

- [x] 3.1 Rewrite the `character create` wizard in `commands/character_creation.py`: subrace prompt lists every registered subrace for the chosen race with display name (+ specialty), requires a selection, and rejects empty/`none`; the allocation step is preceded by a briefing block (budget, six axes, per-axis 0–span, sum-must-equal-budget) built from the resolved profile
- [x] 3.2 Add the optional background prompt to the `character create` wizard and carry the accepted value into the `CharacterCreationRequest`
- [x] 3.3 Update the concept continuation (`_complete_interactively`) and `_proposal_summary` for a guaranteed non-null proposal subrace (no `或 '無'` fallback) and the shared name/age prompts
- [x] 3.4 Add a new `設定背景` command (alias `背景`) in `commands/` (e.g. `commands/background.py`) that shows the current background with no args, routes set/clear through `world/rules.persona_edit.update_background` (an empty argument clears the field; a character without a persona record is handled), and rejects over-bound input; register it in `commands/default_cmdsets.py` `CharacterCmdSet`
- [x] 3.5 Update `commands/tests/test_character_creation.py`: replace `"none"`/empty human subrace replies with real `human_*` keys; assert the subrace prompt lists the subrace names, the allocation briefing appears before the first allocation input, an empty subrace is rejected, and the background prompt/cancel flow works
- [x] 3.6 Add command tests for `設定背景` (no-arg view, set, clear, over-bound rejection, no other state change, works without a persona record)

## 4. WebClient presentation: panel, schema, and parity

- [x] 4.1 Add the optional `background` to the `creation.custom` action payload schema and the custom draft payload in `web/webclient/presentation/creation.py` (and the `creation` panel custom descriptor if needed for the briefing), keeping the exact-field and OOB-envelope contracts
- [x] 4.2 Bump `web/webclient/presentation/character.py` `CHARACTER_SCHEMA_VERSION` to 2, add the `persona` section (`background` nullable bounded string) to the exact payload and validator, and update its serialization from `build_character_read_model`/persona record; update the Python `web/webclient/presentation/registry.py` character panel registration for v2
- [x] 4.3 Mirror the character panel v2 schema (including `persona.background`) and the `creation.custom` background field in `web/static/webclient/js/elosern/protocol.js` validators and the JS character-menu model, and update every v1-dependent consumer (character panel renderer, the exact-shape Node validator tests, the OOB round-trip / unavailable-envelope parity tests, and the browser character-panel journeys) so a v2 payload renders and passes both Python and JS validation
- [x] 4.4 Add Node and browser coverage for the character panel v2 `persona.background` (renders the player's own background, renders nothing for a character without one, panel stays read-only) and for the `creation.custom` background field round-trip

## 5. WebClient dock: subrace required, briefing, background field, pointer + keydown fix

- [x] 5.1 Update `web/static/webclient/js/elosern/creation_menu.js`: drop the `subrace-none` item and the "無子種族" radio (a subrace is required), add the allocation-briefing data helper (budget, axis count, per-axis spans, summing rule) and the background field to the custom state/payload
- [x] 5.2 Update `web/static/webclient/js/plugins/creation_dock.js`: render the allocation briefing above the allocation fields, render the required-subrace radios without "none", add the bounded background input, and include background/subrace in `customPayload` and the draft restore path
- [x] 5.3 Add pointer activation for the creation-form action buttons (確認建立 / 清除草稿 / 返回 / 套用構想) that shares the router's disabled/in-flight/awaiting-revision gate, and generalize `_formKeyBound` to claim every keydown while the form owns focus (exempting the drawer field) so no "NO plugin handled this Keydown" is logged — without `preventDefault` on Tab, modifier keys, IME composition, or character input, and with the exact-once contract (a pointer click and a simultaneous keyboard Enter emit at most one mutation)
- [x] 5.4 Update the Node tests (`web/static/webclient/js/tests/creation_menu.test.js` and any dock contract tests) and the ui-contract tests for the subrace-required form, the briefing, the background field, and the claimed keydown contract; add browser coverage that the form claims keys without breaking typing/Tab/IME, and that pointer clicks on the action buttons submit exactly once while in-flight gates hold
- [x] 5.5 Add a briefing-vs-profile parity test (Node): for `human` and for a vital-overriding subrace such as `foxkin`, the rendered briefing's budget and per-axis spans exactly equal `resolve_starting_profile`'s values

## 6. Character panel and look display (self, other players, NPCs)

- [x] 6.1 Append the flattened persona block (including `背景：` when present) to the shared look appearance path (used by the text 「看」 command and the WebClient look action) for ANY living entity: `LivingEntity.get_display_desc`/`at_look` renders `PersonaStore.flatten(("personality", "life_story", "habit", "background"))` when the target has a persona record, covering looking at themself, at another player character, and at an NPC; looking at the room or an object never appends a persona block, and a persona-less entity (e.g. a monster) renders nothing
- [x] 6.2 Add `背景：` to `world/rules/persona.py` `_FIELD_LABELS` and keep the default flatten field set unchanged; add persona-store tests for the explicitly requested background section, the unchanged default flatten, and the look display (look self with/without a persona block, look at another player character shows that character's block, look at a persona-bearing NPC shows the NPC's block, look at room/object omits it, onboarding look beat unaffected)
- [x] 6.3 Update the WebClient character dock/menu to render the `persona.background` row from the v2 panel and add browser/Node coverage that the background renders and the panel stays read-only

## 7. NPC flavor-text authoring seam

- [x] 7.1 Extend `world/quests/characterization.py` `characterize_errors` with the optional bounded top-level `background` (and the optional import-card persona prose block) fields for a stage's `npc_req` characterization, reusing the persona field bound; reject any nested key beyond the three prose fields inside `persona` (background flavor belongs at the top level); update `duplicate_stable_key_errors` agreement rule to include the persona/background identity when relevant
- [x] 7.2 Update `world/quests/scene_builder.py` `_apply_characterization` to write the validated persona/background into the spawned NPC's `entity.db.persona` inside the same atomic materialization (the sole NPC-persona writer seam), and update `world/quests/tests/test_characterization.py`/scene-builder tests for the new fields and the anti-hallucination boundary (flavor text never feeds stats)
- [x] 7.3 Update `world/ai/scenario_director.py` `_validate_npc_characterization` to pass through the shared helper so an AI-generated NPC can carry the authored persona/background from spawn, and extend the scenario-director validator tests
- [x] 7.4 Extend `world/imports/examples/example_character.json` with a `background` key in its persona object (keeping the opaque shape), and update `world/imports/tests`/reference-example tests so an administrator-authoring NPC has a documented shape to copy

## 8. AI layer: subrace required in proposals

- [x] 8.1 Update `world/ai/character_creation.py`: make `subrace_key` non-nullable in `CHARACTER_CREATION_OUTPUT_SCHEMA`, require a registered, race-compatible subrace in `_validate_subrace` (reject null/missing), and update `CharacterProposal` typing accordingly
- [x] 8.2 Update `world/ai/tests/test_character_creation.py` for the required-subrace contract (a null/missing/incompatible subrace rejects the whole proposal and retries)

## 9. Command documentation and repository contract

- [x] 9.1 Update `docs/game/commands.md` and `docs/game/command-reference.md` for the new `設定背景` command (canonical entry, syntax, context) and the revised `character create` description (subrace required, allocation briefing, optional background)
- [x] 9.2 Update `tests/test_command_docs.py` (curated manifest) for the new command and any `character` syntax description changes, and keep the drift contract green

## 10. Full verification

- [x] 10.1 Run the affected Evennia test packages (`commands`, `typeclasses`, `world`, `web.webclient`) with `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb`
- [x] 10.2 Run the Node test suites (`node --test web/static/webclient/js/tests/*.test.js`) and the managed browser creation/character journeys
- [x] 10.3 Run `uv run --locked python -m tools.spec_traceability check`, `openspec validate fix-custom-creation-information-and-background --strict`, `uv run --locked python -m compileall -q world typeclasses commands server`, and `git diff --check`; confirm a `git grep subrace=None` sweep is clean except the internal sentinel
- [x] 10.4 Before archive, obtain the canonical requirement IDs with `uv run --locked python -m tools.spec_traceability list`, apply `covers_requirement` to a discoverable `test_*` for every new main requirement, and run the verifier's `verify --evidence` mode with the required test entry points
