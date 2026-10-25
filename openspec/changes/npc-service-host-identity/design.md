# Design

## Context

guild_economy._row_anchor_class reads profession.components[0]; _find_service_host searches its service_id; _sync_service_host relocates reused hosts. _converge_service_hosts inspects all component IDs and npc_title to delete residue. Existing hosts already carry canonical `npc_profile_key` through NPC_PROFILE_PROVENANCE_ATTRIBUTE. Stock initialization belongs to _initialize_merchant_stock, outside component assembly.

## Goals / Non-Goals

Deliver `H` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

### Identity and lifecycle ownership

Add `host_key` to ServiceHostRow, derived explicitly as the place's existing `host_profile_key`; require unique nonempty host_key/profile_key among host rows. They are the same canonical stable authored profile identity, not a display name or a component service ID. Lookup by NPC_PROFILE_PROVENANCE_ATTRIBUTE (`npc_profile_key`) across NPC family, reject more than one candidate before writes. A matching persistent adventurer person provenance is an ownership conflict and rejects; do not take over an adventurer. Never fall back to component order, component IDs, names or locations. Changing host_profile_key intentionally declares a different person; editing profile content under the same key preserves identity. No new general NPC identity table or legacy adoption scan.

Keep source ownership on the existing NPC using a `service_host` tag in category `content_source` written by normal sync when its row is applied. This tag grants the existing roster lifecycle owner authority over deletion when a whole host declaration is removed. It never authorizes component-ID inference. Retired tagged hosts follow the existing explicit whole-row removal operation and existing NPC deletion hooks; untagged NPCs survive. Duplicate canonical identity rejects before tag writes. Reuse never relocates, renames, retitles, rebuilds traits, replaces persona or resets race/age/inventory/relations/schedules. Creation retains the separate existing initialization owners. This removes the title-based residue heuristic before titles are removed.

### Managed set and field allowlists

On a source-managed row the six supported capability slots are the owned set: guild_staff, guild_exam_reception, merchant, scripted_dialogue, quest_issuer, church_host. Converge that set against the resolved declaration, including zero entries; remove obsolete slots through ComponentHandler removal. Preserve every component outside that closed vocabulary. A manually attached member of the six-slot set is still source-managed on this host and is removed unless declared. Imported/unmanaged NPCs are never swept. No second persisted per-NPC capability list is needed.

Update only explicit configuration allowlists: service_id plus branch_key (staff/reception), shop_key (merchant), dialogue_key (dialogue), issuer_key (quest issuer), church and initial_arousal (church), and service_binding/anchor_room_id. Merchant merchant_stock/last_restock_day are never authored or rewritten. initial_arousal is configuration; the existing creation-only church baseline owner applies it only on initial ChurchHost installation and never resets a reused host's sexual state. Existing stock initializer runs only for newly attached/uninitialized merchant state, never on config-only changes. Changing shop identity preserves stock/restock state; existing shop validation governs old stock keys, with no normalization by sync.

Validate catalog identities, all rows, duplicates and anchors before any persistent writes, then perform the full host operation in one transaction with in-process ComponentHandler/Attribute cache restoration on failure. Post-commit logs/pushes never describe rolled-back work. The temporary blueprint resolver supplies the exact same resolved plan until D replaces inputs. No compatibility mechanism is added.

### Planned ownership boundary

Source-managed set removal is covered separately from whole-row retirement: changing a row to components=[] preserves its canonical NPC. Row retirement alone invokes deletion. The unmanaged-person guard covers guild_adventurer_person_key even when another source accidentally reuses the same npc_profile_key.


## Risks / Trade-offs

H follows R because the managed vocabulary uses reception. D owns later input replacement; N/P/GM share guild_economy/identity/specs. Existing authored dialogue content uses profile identity unchanged; no topic/body edit is needed. Serialize deletion callback edits with authored-dialogue-refresh-lifecycle and webclient-publication-settlements.

The root-level batch contract in `../npc-examination-reception/batch.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync world.rules.tests.test_service_binding_persistence world.rules.tests.test_guild_config.test_service_host_roster
uv run --locked python -m tools.contract_gate
openspec validate npc-service-host-identity --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
