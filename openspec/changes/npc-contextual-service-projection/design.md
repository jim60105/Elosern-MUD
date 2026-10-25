# Design

## Context

The existing service model handles shop, guild registration/board/report and independent examination requests. Church enrollment is a real text command, not an existing web drawer. Guild 回報 has deterministic reportable_quest_summary behavior; other prose such as drill-yard 考核 does not provide an examination service. Authored scene reading already distinguishes formal/refusal/opening/service deliveries; generated-packages will provide current source-aware topic identities.

## Goals / Non-Goals

Deliver `P` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

### One derived owner and bounded wire

Add `world/rules/npc_services.py::project_npc_services(actor, viewer, npc)` returning frozen `NpcServices(state, entries)` where state is `none|ready|unreadable`. entries have exact `{key,label,enabled,disabled_reason,route}`. key is a stable semantic 1..64 ASCII identifier; label 1..64 Unicode code points; reason uses exact `{code,message}` with code 1..64 ASCII and message 1..240 code points, null iff enabled. At most 16 unique entries sorted by the mapping order below, then explicit association key. No persisted derived list or per-NPC presentation registry. A projection failure returns unreadable with zero entries; empty success returns none; ready requires >=1 entry. Preserve the existing service_gate diagnostic policy and do not materialize attributes on read.

Exploration schema version 4 -> 5 adds exact target field `services:{state,entries}` beside existing identity/display_name/portrait_ref/affordances. Services are outside the current <=8 general-affordance limit so they cannot displace editor/party controls. Remove old guild/shop navigate affordances; keep npc_persona ordinary navigation. Python presenter, registry, UMD exact mirror, fixtures, frame resolvers and the existing flat verb builder consume the new services field together in this slice. The flat builder appends service rows so the feature is usable before U adds groups. Existing common/conditional ordering stays until U's explicit fixed-slot cutover.

Routes are exact discriminated objects `{kind:"services",npc_id,section:"shop|registration|board|report|rank"}`, `{kind:"dialogue",npc_id,topic_id}` or `{kind:"command",npc_id,command:"church join"}`. npc_id must equal the selected positive JS-safe target. services routes use T's correlated read and existing section. Dialogue routes open that exact host and focus the associated topic in client-local state after current choices commit; they never automatically select a topic. The player must explicitly activate it through the existing context/selection boundary, including read-only guild report. Thus opening a generated offer_commission service accepts no quest. Command routes only focus/pre-fill church join #id. Validate exact fields and preserve source-aware dialogue IDs up to 2048 bytes.

### Exhaustive production mapping and order

| Capability | Semantic keys in order | Existing route | Entry availability owner |
|---|---|---|---|
| Merchant | shop | services/shop | co-presence, binding, schedule, control; preserve current ability to inspect closed shops |
| GuildStaff | guild.register, guild.board, guild.report | services/registration, board, report | current guild entry gates; registration already registered is explained inside registration; quest/product eligibility stays inside flow |
| GuildExamReception | guild.exam | services/rank | request-entry rules, never disable merely for insufficient merit or absent qualified adventurer |
| ChurchHost | church.enroll | command/church join | existing player/enrollment/service/schedule rules; already enrolled retains row with inline reason |
| ScriptedDialogue with explicit source services | dialogue.<association key> | dialogue/exact topic_id | canonical topic disclosure/permission plus that component's explicit binding; hidden omitted, locked focusable/disabled |
| QuestIssuer alone; narrative-only ScriptedDialogue | no automatic entries | none | capability authority alone is insufficient to promise a public service |

No gameplay entry is inferred from name, title, profession, prose keyword or component order. GuildStaff's guild.report covers deterministic reporting already available in the drawer. The explicit dialogue association shipped here is `key:guild_report_dialogue`, topic_id `guild_staff.topic_04`, label `交談回報委託`; it opens the existing deterministic report/list dialogue path, distinct from the drawer report route. No other static topic becomes a service by prose.

Add optional source services rows of exact `{key,topic_id,label}` to common static/generated dialogue; default empty. Association key matches `[a-z][a-z0-9_]{0,54}` so its dialogue. prefix fits the 64-character final key. Require unique keys/topics and same-source/same-phase supported deterministic associations: current native guild report or a declared authorized generated offer_commission topic. Informational topics reject as services. Validate each source and every complete host capability/source combination before publication/assembly; native plus associated entries must total at most 16 in every phase. Reject excess, never truncate or treat accepted overflow as a runtime read failure.

Generated service-bound dialogue uses D's explicit RoleDefinition.capabilities carrier. Extend its allowed generated types with scripted_dialogue when a phase declares services; require complete kwargs `{dialogue_key:"scene_role:<package_id>:<role_id>",service_id:"scene_role:<package_id>:<role_id>"}` and explicit binding `{kind:"person"}`. The package validator requires exactly that trusted binding and the declared quest_issuer for effect-bearing associations. RoleSpawn carries the validated plan; encounter_activation/materializer install it through assemble_capabilities inside existing activation rollback. An existing bound actor with incompatible dialogue/issuer config rejects rather than being overwritten. Narrative-only roles remain unbound. No generic implicit person default is added. Test actual package publication, role activation and service projection, then opening with zero quest acceptance and a separate explicit topic activation using existing effect authority.

### Closed intermediate route behavior

The existing flat verb builder appends every new service route, including a real church command-input handoff, before U groups the rows. This slice changes church join to required `church join <npc>` and uses its existing resolver to validate the exact co-present ChurchHost at submission. Update both command references and the command manifest for this syntax now. Opening the route only focuses/pre-fills the existing command input; the player's later explicit submission invokes the existing enrollment owner. No service demonstration pane or unimplemented handler ships. Remaining text discovery and other targeted command suffixes belong to X.


## Risks / Trade-offs

P follows D/T plus authored-dialogue-generated-packages and content-guild because it adds source services against their final codecs/topic IDs. All other nine content slices remain independent of P but share authoring docs/codecs test inventory; their prose cannot imply a service. Serialize constants/presenters/frame-resolvers with active publication and immutable-adoption work. U follows P.

The root-level batch contract in `../npc-examination-reception/batch.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_npc_services world.rules.tests.test_authored_dialogue_runtime web.webclient.presentation.tests.test_exploration_panel
node --test web/static/webclient/js/tests/exploration_menu.test.js
uv run --locked python -m tools.contract_gate
openspec validate npc-contextual-service-projection --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
