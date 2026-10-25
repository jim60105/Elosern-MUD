# Design

## Context

npc_identity.npc_display_name/npc_title_value feed typeclasses/npcs.py, exploration/dialogue/party/skill_use presenters, party_scope matching, command item messages, progression unlocks and GM npcs readers. npc.persona.read emits npc_title and the editor composable stores npcTitle. H has already removed the last title-based host cleanup reader.

## Goals / Non-Goals

Deliver `S` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

### Presentation cutover and exact consumer categories

Delete npc_display_name, npc_title_value, title-renderability helpers, separator and full_identity opt-in presentation paths. Use the existing plain key/label path at each consumer, preserving its current safe-read/error boundary and truncation. Do not replace the removed composer with an identically named plain-name shim. `validate_npc_name`, name collision helpers and title authoring validator stay for N's next cutover. Old npc_title attributes remain stored but no read can affect presentation or authority.

Update typeclasses/npcs get_display_name/return_appearance/_npc_context and room appearance's full_identity callers; remove the NPC `title` prompt context key while preserving player title prompt context. Update world/rules/dialogue.py panel budget preview, party_scope member-token matching, progression unlock messages; commands/items.py, commands/party_views.py, commands/localized/general.py; webclient actions/{party_actions,service_actions,npc_persona_actions}.py and presentation/{exploration,dialogue,party,skill_use}.py; web/gm/readers/npcs.py identity/detail/item labels. Membership/search accepts ordinary keys/dbrefs under existing ambiguity rules, never the removed composed alias. Party capacity, identity ownership and eligibility are unchanged.

Remove npc_title from the exact private npc.persona.read result on server and browser mirror, use-npc-persona-editor.js header, NPC editor view, stories/fixtures and browser intercept fixtures. It is currently a header field rather than an editable title setter; do not claim an editor write API existed. Remove any independent title management row and duplicate profession summary from GM list/detail now; GM services remain component diagnostics until G adds the contextual section. No cross-app component imports.

### Sequential validity

Existing creators may still validate/write titles during this slice; those writes have no reader and are deleted completely by N. This is deletion of presentation before producer deletion, without an alternate legacy contract. Protocol cutovers remove the field atomically from every producer/consumer and fixture; no dual schema or ignored extra field.

### Acceptance

Seed db.npc_title with sentinel text, malformed objects and raising accessors; actual room look, explore.look, dialogue host, party list/member scope, item messages, skill targets and GM list/detail show only the authored key and never access that attribute. Existing player title codex/equipped/full_title behavior and generative player context stay unchanged. Test outputs and semantic state, never source-text scans.


## Risks / Trade-offs

Follows H so removing npc_title_value does not leave a convergence reader. Shares dialogue.py with generated-packages, AppClient/editor fixtures with reading-client and GM readers with G. Serialize shared files; preserve source-aware dialogue IDs and publication semantics. N deletes remaining authoring after this completed slice.

The root-level batch contract in `../npc-examination-reception/batch.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb typeclasses.tests.test_appearance world.rules.tests.test_party_scope web.webclient.actions.tests.test_npc_persona_actions web.webclient.presentation.tests.test_dialogue_panel web.webclient.presentation.tests.test_party_panel web.gm.tests.test_reader_npcs
pnpm exec vitest run web/webclient-app/tests/npc_persona_editor.test.js
uv run --locked python -m tools.contract_gate
openspec validate npc-plain-name-presentation --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
