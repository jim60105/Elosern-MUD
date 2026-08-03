## Context

`webclient-oob-foundation` has landed and provides exact OOB envelopes, per-transport epochs and revisions, isolated presenters, an allowlisted dispatcher, a strict browser state store, keyboard routing, a GoldenLayout action dock, and required Node/Playwright gates. Its production action registry is intentionally empty and its action dock is a placeholder.

The deterministic combat core already persists `CombatSessionRecord`, reconstructs a `Battlefield`, preflights one selected player action, runs one initiative round or resolver-backed overwhelm sequence, and settles accumulated time once. Its public player facade still accepts one optional target, the Telnet command resolves one display name, and no read-only model enumerates owned combat actions or candidates. `ActionRequest` already supports explicit lists and the three approved AREA shorthands.

This design implements the approved `webclient-combat-menu` delivery unit from `docs/superpowers/specs/2026-08-02-webclient-combat-ui-design.md`. The browser remains a read-only renderer plus validated intent sender. All action authority remains in `world/rules/`, and every EventLog continues through the existing text output path.

## Goals / Non-Goals

**Goals:**

- Present every owned active skill, innate actions, participants, costs, target shape, current availability, and stable disabled reason in deterministic order.
- Complete Attack, Skills, NONE/SELF/SINGLE/AREA target selection, Flee, and confirmed Forfeit without typed commands.
- Reuse one side-effect-free rules query for menu previews, Telnet action listing, and server-side revalidation.
- Expand the combat-session facade and Telnet syntax to explicit multi-target values without changing round, overwhelm, examination, or settlement semantics.
- Preserve epoch/revision ordering, one-in-flight behavior, reconnect recovery, narrative output, keyboard accessibility, and required browser gates.

**Non-Goals:**

- No combat item use, defend mechanic, hotbar, auto-battle, damage estimate, hit percentage, or formula change.
- No art asset, portrait catalog, map, exploration, service, or character-creation implementation.
- No client-side target validation, rule calculation, canonical combat cache, or EventLog rendering.
- No mobile acceptance and no new runtime dependency.
- No compatibility overload for the old single-target combat-session API and no persisted-data migration.

## Decisions

### D1. Register one exact `context_actions` combat panel

The production presentation registry will add `context_actions` schema version 1. In combat mode its available form contains the validated session summary, ordered participants, ordered root and secondary actions, and ordered active-skill descriptors. Outside a valid active combat session it uses the common unavailable form; it does not fabricate exploration actions before their owning change lands.

The panel uses bounded, exact JSON. Participant IDs are positive ObjectDB IDs treated as opaque references, not labels or authorization. Lists are bounded below the foundation's global limits, and the complete payload must remain below the 65,536-byte envelope limit. Every participant has one stable Telnet token and a nullable `portrait_ref`; this change always emits `null` because the art capability is not a dependency. A later art change may introduce a new panel schema version rather than letting the browser construct portrait keys.

This keeps combat-specific state in one independently replaceable panel. Adding combat fields to `status` was rejected because status is intentionally compact and shared by every mode.

### D2. Build a frozen combat view before serialization

`world/rules/combat_session.py` will expose a side-effect-free combat view query that strictly reads the active record, reconstructs its battlefield, preserves `player_ids` and `enemy_ids` order, and returns frozen session, participant, skill-preview, and target-preview values. The WebClient presenter and `combat actions` command serialize that view; neither reads raw `.db.active_combat` fields independently.

The query will use public pure validation factored from `ActionResolver.preflight()`: ownership and active kind, resources, exact target shape, candidate validation, action capability, registered effect prefixes, and time metadata. It will additionally consume `actions_per_turn` through a no-create deterministic modifier context derived from existing stored buff and sexual-state data, so zero-action state has one authoritative preview/revalidation result without copying climax logic or lazily materializing a handler. It performs no roll, effect staging, EventLog construction, handler mutation, persistence, or time advance.

Calling full `preflight()` once for every target was rejected because it obscures which validation is skill-wide versus candidate-specific and encourages synthetic malformed requests. Copying formulas into presenters was rejected because availability would drift from execution.

### D3. Revalidate the preview boundary before initiative

`submit_player_action(actor, skill_key, targets_or_shorthand)` will accept only a concrete list or one approved shorthand. It reconstructs the current battlefield, canonicalizes every explicit object by participant ID against that reconstruction, requires an empty list for player-facing NONE/SELF input, binds SELF to the authenticated actor, applies the shared preview/capability checks, and then runs the existing preflight and orchestration. A zero-action player request, malformed target shape, duplicate target, stale participant, or unavailable skill rejects before initiative and consumes no round.

The round loop keeps its zero-action skip behavior for NPCs and for state that changes after player preflight. This preserves committed earlier initiative turns while preventing a tampered UI or Telnet request from using a disabled player action to start a round.

The old optional-single-object overload is removed. All production and test callers change in the same commit because the project has no released consumers.

### D4. Make target wire shapes unambiguous

`combat.cast` has exactly these payload forms:

- NONE and SELF: `skill_key` only;
- SINGLE: `skill_key` plus `target_ids` containing exactly one positive integer;
- AREA: `skill_key` plus either one nonempty bounded list of unique positive `target_ids` or one approved `target_shorthand`, never both.

The generic payload validator rejects unknown fields, booleans as integers, duplicates, oversized values, and mutually exclusive fields. The adapter then loads the current `SkillDef`, checks that the submitted shape matches it, re-resolves IDs only from the active session record, and invokes the facade. SELF binds the authenticated puppet inside the rules layer; the browser never sends an actor ID.

NONE currently ignores supplied candidates. This change deliberately tightens it to `target_spec_mismatch`. SELF continues to accept either resolver-normalized empty input or an explicit actor from trusted direct `ActionRequest` producers such as monster policy, but the player-facing facade and wire schema accept no SELF target field. SINGLE shorthands are rejected even if expansion would happen to yield one entity. Empty explicit AREA input is malformed; a valid nonempty list or shorthand whose candidates all fail ordinary presence/alive/range/faction checks remains `no_valid_targets_in_area`.

### D5. Keep AREA filtering but reject duplicate intent

Explicit and shorthand-expanded AREA candidates still pass presence, alive, range, and faction checks independently; invalid candidates are dropped, and at least one must survive. Duplicate explicit IDs or objects reject before filtering so one target cannot receive the same effect twice from one submitted selection. Shorthand expansion is deterministic from the battlefield roster, applies only to AREA, and then uses the same four validators.

Changing AREA to fail when any candidate becomes invalid was rejected because the current deterministic contract intentionally filters invalid members and supports live area selections during initiative changes.

### D6. Extend immutable skill metadata directly

`SkillDef` gains required `label` and `description` strings. They are bounded Traditional Chinese presentation metadata owned by the same immutable registry as cost, target shape, element, and effects. Every production definition, including the dynamically registered innate `flee`, supplies both fields. The menu sends effect IDs only as internal validation inputs; players receive the curated description rather than raw effect grammar.

A parallel display registry was rejected because it would require cross-registry completeness checks and duplicate skill identity. A fallback from key to generated prose was rejected because every active skill must have stable player-facing text. Existing constructors are updated directly without defaults or compatibility shims.

### D7. Register three narrow production actions

The production action registry will contain exactly:

- `combat.cast`, with the conditional exact payload above and rejection of the reserved `flee` key;
- `combat.flee`, with an exact empty payload and server-selected innate `flee` skill;
- `combat.forfeit`, with exactly the currently rendered `session_id` as a stale-selection guard.

The dispatcher still supplies the actor from the authenticated puppet and owns epoch/revision, deduplication, and one-in-flight admission. Adapters re-read the active record, re-resolve participant IDs, invoke only combat-session public APIs, and never write attributes or battlefield state directly. `session_id` cannot select a session; Forfeit compares it with the actor's current record before calling `forfeit(actor)`.

Basic Attack uses `combat.cast` with `basic_attack`. Every presentation of the innate `flee` skill uses `combat.flee`, preventing a second wire path through `combat.cast`. Items and Defend have no action ID and remain focusable disabled descriptors with `not_implemented`. A generic `combat.command` adapter was rejected because it would bypass exact schemas and duplicate the text parser.

### D8. Share result rendering between command and UI adapters

Command and UI paths will call one presentation helper that maps resolver/session outcomes to stable Traditional Chinese messages and emits every returned EventLog through `actor.msg(render_plain_text(log))`. OOB results contain only bounded outcome/code/message data; they do not carry prose or EventLogs. After adapter settlement, the dispatcher publishes canonical `status` and `context_actions` replacements before the matching action result unlocks the browser.

This preserves the stock narrative channel, escaping behavior, and unread handling. Client-side EventLog rendering was rejected because narrative must remain playable and authoritative without OOB.

### D9. Generate Telnet tokens from persisted participant order

`combat actions` lists active skills in handler order and participants using `a1`, `a2`, ... for `record.player_ids` and `e1`, `e2`, ... for `record.enemy_ids`. Tokens remain bound to the same dbref for that session because the persisted tuples are immutable. They are presentation aliases, never database references stored on the character.

Inside an active session, `cast skill=e1` resolves one token, comma-separated input accepts tokens only, and an AREA shorthand must occupy the complete right-hand side. Existing one-target display-name search remains. Unknown, duplicate, mixed token/name, or shorthand/token input rejects before initiative. Deriving tokens from battlefield `frozenset` order was rejected as nondeterministic.

### D10. Keep menu selection DOM-independent

A DOM-independent combat-menu module will transform the validated panel into root, skill, target, multi-select, confirmation, and detail models consumed by `KeyboardRouter`. Arrow keys move focus, Enter opens or submits, Escape pops one level, and Space toggles only AREA candidates. The module preserves the originating skill focus on backtracking, paginates without reordering, and chooses the nearest surviving item deterministically after a newer panel replacement.

The GoldenLayout renderer creates controls with text nodes, associated disabled explanations, numeric resource text, and a live result region. Focus changes emit only client-local events. With `portrait_ref: null`, they send no focus packet and do not create a key or URL.

### D11. Reconnect always rebuilds from canonical session state

Transport loss leaves the old view under the foundation offline overlay and disables submission. A new epoch's full snapshot reconstructs participants, round, status, skills, targets, and menu root from persistence even when its revision is lower than the retired epoch. No pending selection or mutation is resubmitted. A validly parsed session with an unreconstructable participant yields a bounded recovery view with confirmed Forfeit and the text command path. A malformed record uses isolated unavailable presentation and retains text access until deterministic startup recovery handles it. Presenters do not repair or clear sessions while rendering.

Persisting menu depth or target selection was rejected because these values are client-local and stale after reconnect.

### D12. Extend every existing verification layer

Pure Python tests cover preview purity, metadata completeness, target shape, canonical re-resolution, token order, and all domain outcomes. Evennia integration tests cover adapter authentication/staleness/deduplication, EventLog text delivery, round semantics, and Telnet parity. Node tests cover exact panel reduction and combat menu state. Managed Playwright tests cover keyboard-only Attack, active skills, NONE/SELF/SINGLE/AREA, disabled Items/Defend, Flee, Forfeit confirmation, reconnect, narrative/status updates, and both supported viewports.

Tests use the existing isolated harness and deterministic fixtures. No test calls an LLM, image generator, or remote service. Main-spec requirements receive canonical `covers_requirement` annotations and execution evidence through the existing Python entry points.

## Risks / Trade-offs

- [Skill-by-participant preview can enlarge the panel] → Cap skills and participants below protocol limits, reference participant IDs instead of repeating participant objects, fail the panel closed if the complete envelope cannot fit, and test worst-case serialization size.
- [Preview can drift from final resolution] → Factor pure checks from the resolver, call the same combat view revalidation immediately before session preflight, and retain full final resolution after initiative starts.
- [AREA filtering can hide a stale selected member] → Preserve the existing filtering contract, return only committed canonical results, and replace the complete panel after every action.
- [A runtime-invalid persisted session cannot be repaired by a read-only presenter] → Expose a bounded recovery state, retain text and confirmed Forfeit, and keep startup deterministic recovery unchanged.
- [Adding required skill metadata touches many test fixtures] → Update all constructors directly and add a registry-wide completeness/bounds test; do not add permissive defaults.
- [Combat UI lands before portraits] → Emit only nullable server-authored portrait references and test that focus sends no packet; the art change owns populated catalog values and any schema bump.
- [Browser journeys increase CI time] → Reuse one managed server per test class where isolation permits, keep rule cases in pure/Node tests, and reserve Playwright for focus, transport, layout, and real integration behavior.

## Migration Plan

No stored schema changes. Implement the change in dependency order: shared metadata and pure preview, exact target/session facade, Telnet syntax, server presenter/adapters, client reducer/menu/renderer, then integration and browser gates. Update all old facade callers and exact-field fixtures in the same change. Existing active `CombatSessionRecord` values remain readable because their storage shape does not change.

Deployment is the ordinary unreleased-project code update followed by static collection and server restart. Rollback uses the prior code revision; no data rollback or dual reader is required.

## Open Questions

None. The observable scope, menu hierarchy, target forms, desktop viewports, reconnect ordering, Telnet parity, and non-goals are fixed by the approved parent and focused designs.
