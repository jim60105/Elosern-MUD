## 1. Skill Metadata and Rules Preview

- [x] 1.1 Add required bounded Traditional Chinese `label` and `description` fields to `SkillDef`, update every production definition and test fixture including dynamically registered `flee`, and add registry-wide immutability, completeness, bounds, and no-default tests.
- [x] 1.2 Centralize stable player-facing action/session rejection messages so Telnet commands and WebClient adapters use the same safe Traditional Chinese mapping, with tests covering every preview-visible `RejectReason` and session outcome.
- [x] 1.3 Factor the resolver's pure ownership, resource, target, capability, effect-prefix, and time-metadata checks into a frozen action-preview query; include `actions_per_turn == 0` through a no-create stored-state modifier context and test exact reason/detail parity with `preflight()` without handler/default materialization, rolls, staging, EventLogs, planner calls, mutation, or time advance.
- [x] 1.4 Implement frozen combat-session view models for session summary, persisted-order participants/tokens, active-skill descriptors, candidate IDs, applicable AREA shorthands, and bounded recovery state; test canonical reconstruction, stable order, limits, malformed/unreconstructable records, and complete read-only behavior.

## 2. Target and Combat-Session Contracts

- [x] 2.1 Tighten target-shape validation so NONE rejects candidates, SELF accepts normalized empty input or exactly the actor for trusted direct requests, SINGLE rejects shorthand and non-unit cardinality, and AREA rejects empty/duplicate explicit input while preserving four-stage filtering and `NO_VALID_TARGETS_IN_AREA`; separately require empty player-facing NONE/SELF facade input and add focused pure tests for every shape, existing monster-flee compatibility, and rejection order.
- [x] 2.2 Replace `submit_player_action`'s optional single target with an explicit object list or approved shorthand, canonicalize explicit participants through the reconstructed record, run shared preview and preflight before initiative, and update every production/test caller without a compatibility overload.
- [x] 2.3 Add combat-session regression tests for explicit AREA targets, all three shorthands, duplicate/remote/dead/fled/wrong-faction targets, zero-action pre-initiative rejection, mid-round invalidation, and unchanged ordinary/flee/overwhelm/victory/defeat/cap/exam/clock settlement behavior.
- [x] 2.4 Add `combat actions` with active skills and `aN`/`eN` tokens derived from persisted participant tuples; extend active-session `cast` parsing for one token, token-only comma lists, complete AREA shorthands, and retained one-target display-name search.
- [x] 2.5 Add command tests proving token stability across rounds and reconnect, stored skill order, exact help/examples, successful single/multi/shorthand dispatch, and pre-initiative rejection of unknown/duplicate/mixed tokens or shorthand mixtures.

## 3. Combat Presentation and Action Adapters

- [x] 3.1 Define exact bounded server and client schema-version-1 validation for `context_actions`, including session, participant, action, skill, disabled-reason, target, recovery, and nullable portrait-reference forms; add valid/invalid and worst-case envelope-size tests.
- [x] 3.2 Implement the read-only combat presenter from frozen combat views and register `context_actions` beside `status`; update coordinator/registry tests that currently assume a status-only production panel and prove exploration receives no fabricated combat actions.
- [x] 3.3 Implement exact payload validators for TargetSpec-dependent `combat.cast`, reserved-flee rejection, empty `combat.flee`, and session-guarded `combat.forfeit`, covering unknown fields, scalar/list bounds, booleans, duplicates, mutually exclusive target fields, and malformed session IDs.
- [x] 3.4 Implement the three adapters with authenticated-puppet identity, current-session re-read, participant-only ID resolution, shared preview revalidation, public combat-session API calls, and no direct writes; register exactly those production actions and update tests that currently require a mutation-empty registry.
- [x] 3.5 Factor shared command/UI combat-result rendering so every committed EventLog and terminal message uses ordinary escaped text output while OOB results remain bounded structured data; test one narrative emission for success, no fabricated log for rejection, and safe correlation-only internal failure.
- [x] 3.6 Add dispatcher/input-function integration tests for authentication, stale epoch/revision, current revision, duplicate request, one-in-flight busy state, remote/tampered IDs, domain rejection, success, terminal mode transition, affected `status`/`context_actions` publication before result, and session unlock.

## 4. Browser Combat Menu

- [x] 4.1 Extend `elosern/protocol.js` and the state controller with exact atomic `context_actions` validation/replacement and Node tests for available, unavailable, recovery, malformed, revision, and reconnect cases.
- [x] 4.2 Implement a DOM-independent combat-menu model for root, active-skill pagination, details, NONE/SELF/SINGLE/AREA target flows, Space multi-selection, shorthand selection, secondary Forfeit confirmation, submenu backtracking, and deterministic focus restoration after panel replacement.
- [x] 4.3 Add Node tests for stable skill/participant order, passive exclusion, disabled focus without send, Items/Defend placeholders, all target shapes, duplicate toggle suppression, Escape restoration, repeated Enter, in-flight locking, stale selection removal, and no focus packet.
- [x] 4.4 Replace the action-dock guidance in combat mode with accessible controls and detail panes driven only by the validated menu model; keep the foundation guidance outside combat and render every server string through text APIs.
- [x] 4.5 Wire menu submissions to `elosern_actions.js` using exact payloads, keep SELF actor binding and portrait focus client-local, restore root focus only after the declared presentation revision, and preserve the uncertain-result/no-retry reconnect behavior.
- [x] 4.6 Extend status rendering to display exact rule-provided combat modifiers and add ink-night/vermilion combat styles for visible non-color focus, selected AREA targets, associated disabled reasons, confirmation state, pagination, reduced motion, and safe 1440x900/1280x720 overflow.

## 5. Managed Browser Acceptance

- [x] 5.1 Extend deterministic isolated browser fixtures with ordinary, examination, zero-action, disabled-skill, all-TargetSpec, multi-target, and terminal combat sessions without touching the developer database or invoking a remote, LLM, or image service.
- [x] 5.2 Add keyboard-only Playwright journeys for Attack, complete active-skill order, NONE, SELF, SINGLE, explicit AREA, shorthand AREA, Flee, Items/Defend disabled explanations, and confirmed/cancelled Forfeit; assert exact OOB payloads and ordinary narrative delivery.
- [x] 5.3 Add browser rejection tests for insufficient resources, no valid target, zero-action state, tampered/stale target, duplicate request, and one-in-flight suppression, asserting no unauthorized round or clock advance and canonical menu refresh.
- [x] 5.4 Add active-combat disconnect/reconnect tests proving offline locking, uncertain-result notice, no retry, same persisted session/round reconstruction in a lower-revision new epoch, retired-epoch rejection, and deterministic root focus.
- [x] 5.5 Run combat journeys at 1440x900 and 1280x720 and assert narrative, numeric HP/MP/SP, applied modifier text, disabled explanation, and action controls remain visible, keyboard-operable, literal-text safe, and localhost-only.

## 6. Regression, Spec Sync, and Verification

- [x] 6.1 Run focused skill, targeting, resolver, combat-session, command, presenter, dispatcher, Node, and Playwright tests while iterating; fix regressions without weakening atomicity, target validation, text fallback, protocol bounds, or accessibility assertions.
- [x] 6.2 Compare implementation and tests with all six delta specs and both approved WebClient designs; confirm item use, Defend, map, exploration, services, creation, art/portrait assets, mobile, and combat formulas remain outside this change.
- [x] 6.3 Sync the new capability and five modified capability deltas into `openspec/specs/`, inspect the merged requirements, obtain canonical IDs with `uv run --locked python -m tools.spec_traceability list`, and annotate only substantively matching Python unit/integration/browser tests.
- [x] 6.4 Run `uv run --locked python -m tools.spec_traceability check`, `node --test web/static/webclient/js/tests/*.test.js`, and `uv run --locked python -m unittest discover -s web/tests/browser -t .` with the shared evidence path; close every genuine requirement gap without skipped or placeholder evidence.
- [x] 6.5 Run both required evidence-producing Python entry points and `uv run --locked python -m tools.spec_traceability verify --evidence <shared-path>`; preserve successful evidence for all current main requirements.
- [x] 6.6 Run the exact two-file aggregate branch-coverage sequence for `commands`, `server`, `typeclasses`, `web`, and `world`, verify coverage roots, and keep combined branch coverage at or above 90% with only `*/tests/*` omitted.
- [x] 6.7 Run `openspec validate webclient-combat-menu --strict`, `openspec validate --all --strict`, `uv run --locked python -m compileall -q world typeclasses commands server web`, and `git diff --check`; verify no runtime/test path contacts a remote service or developer database.
