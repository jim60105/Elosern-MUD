## Context

See proposal.md for the two publication gaps. Evennia 6.1 dispatches gallery `ui_action` results into the existing presentation coordinator; the Vue 3 SPA commits panels by their wire names. The registry registers `gallery` at lines 239–243, `art` at 247–251, and `roster` at 360–365. Dispatcher completion checks declared names against `registry.panel_names` at lines 388–402; an unknown name resets the declaration to `None` and publishes a recovery full snapshot. Consequently an F5-equivalent fallback can hide a misspelt declaration, and tests must distinguish the update transport from a snapshot.

The current completion subscriber in `art_push.py` considers connected webclients with an active puppet and already-attached coordinator. It renders art, checks its subject references and availability, and publishes only art. Gallery selection enters `PresentationContext` through `gallery_selection_snapshot`, which checks puppet identity and presentation epoch. The rendered gallery's `selected` also applies rail membership/fallback. Roster payloads carry `characters[*].portrait.subject_key` for the owning account, including characters outside the current room.

## Goals / Non-Goals

**Goals:** Close both gaps through existing read-only presenters and one revisioned update per qualifying session/event; make panel dependencies explicit; preserve session/epoch ownership and truthful store-derived rendering.

**Non-Goals:** No portrait-selection algorithm changes, worker scheduling/settlement redesign, schema-version changes, frontend changes, polling, retries, remembered subscriptions, new signal, command documentation changes, compatibility layer, or data migration. No new test module is needed.

## Decisions

### D1 — One shared uniform declaration for all six actions (fixed)

Rename `AFFECTED_GALLERY` to `AFFECTED_GALLERY_PANELS = ("gallery", "art", "roster")` in `gallery_actions.py`; use it in selection success/rejection, `_mutate` success, and `_rejected`. No legacy alias remains. The user chose uniform declarations even for selection/generation that cannot immediately change stage resolution. Per-action precision is not the plan: it creates another dependency inventory that future mutations can forget.

The dispatcher already renders every declared panel after the mutation, including domain rejections, and publishes one `ui_update` before the action result at the same presentation revision. Keep that behavior. Malformed wire payloads that never reach an adapter and cached duplicate requests keep their existing no-extra-publication behavior.

`select_gallery_subject` currently returns a redundant `affected_panels: ("gallery",)` hint, while the adapter unconditionally overwrites it. Remove that obsolete helper-level hint; the helper owns selection/result facts, not publication declarations, and its only production caller is the adapter. Do not import the action constant into the presentation selection module or establish a second constant there.

### D2 — Independent rendered-payload gates, not an art-first gate

For each eligible session on each valid `asset_completed(subject_key=...)` notification, reuse that session's coordinator/registry and build one fresh `PresentationContext` from its current puppet and session. Render all three panels against that same context and gate each independently:

| Panel | Matching subject references in its fresh available payload | Include when |
| --- | --- | --- |
| `art` | `scene.subject_key` and every `portrait_catalog` entry's `subject_key` (existing `_subject_keys` rule) | completed key is referenced |
| `gallery` | `selected` only, not every rail `subjects` entry | completed key equals rendered selected key |
| `roster` | every `characters[*].portrait.subject_key`, not only the current row | completed key is referenced by any owned row |

Only available matching payloads enter the publication map. Do not return early because art is unavailable or does not match: a completion visible only in a selected gallery, or only for an off-room roster sibling, still publishes. A panel unavailable in the current mode or because of a presenter failure has no usable subject reference and is omitted; it cannot block another successfully rendered matching panel. Registry-owned presenter failure isolation continues to apply.

Publish the nonempty map once with `coordinator.panel_update(context, panels)`; an empty map does not advance revision. This targets all three panel types, not unconditional inclusion of every panel on every notification. A completion referenced by all three sends all three together; a scene-only completion still sends only art. Existing coordinator mode coherence may append a freshly rendered `dialogue` panel in dialogue mode; this invariant is not overridden by subset assertions. Do not create a full snapshot fallback in this subscriber.

Always publishing all three per session was considered and rejected: it would produce irrelevant updates on every global completion, contradict the existing targeted late-completion rule, and still require three renders. Gating gallery on rail membership was rejected because it is not the displayed selected gallery. Gating roster only on the live puppet was rejected because the roster displays every owned character.

### D3 — Current canonical state is the late-completion safety mechanism

The notification remains a subject key, not a remembered payload, job/image pointer, room, or epoch. Gallery uses the context's owned selection and then the renderer's current rail fallback; roster uses the current account's canonical rows; art uses the current scene/catalog. A subject absent from a panel after movement, entity removal, selection change, account/puppet change, or eligibility change cannot enter that panel's update. No old selection is restored and no completed card is auto-selected or made default. A subject that remains legitimately referenced by a different panel can still refresh that panel: leaving the room must not suppress a roster sibling or selected gallery match.

Keep delivery on the existing reactor-side signal path, stable `DISPATCH_UID`, and the checks for live webclient transport, active puppet, and attached coordinator. Keep the outer per-session exception boundary so one broken session never stops later sessions or propagates to the worker. Rendering remains read-only and introduces no `web/` import under `world/art/`.

### D4 — Observability follows the existing facade

Preserve exactly one `gallery_action` completion event per adapter and existing service/worker settlement events. The expanded successful cross-system publication emits one bounded `art_completion_push` info event through a named `world.observability.log_info` import, with `subject`, `session`, and emitted panel names in a `context` dict. Retain `art_push_unavailable` warning/`exc=` on the session failure boundary and include the known completed subject in its context. Do not log payloads, paths, prompts, or player-facing prose; no silent exceptions. Tests patch bindings in `art_push`, not the facade module. This is boundary instrumentation required by repository invariants, not a telemetry redesign.

### D5 — Spec homes and canonical traceability

Keep existing requirement titles unchanged so canonical IDs from `uv run --locked python -m tools.spec_traceability list --json-output ...` remain stable:

| Delta home | Canonical requirement ID | Existing-module evidence |
| --- | --- | --- |
| `webclient-gallery-management-actions` | `webclient-gallery-management-actions::six-gallery-management-actions-are-registered-with-exact-payload-validators` | All six adapter outcomes plus dispatcher three-panel publication; existing malformed-admission tests retained |
| `webclient-gallery-management-actions` | `webclient-gallery-management-actions::subject-selection-writes-only-session-presentation-state` | Existing selection isolation/retirement test with expanded panel assertions |
| `webclient-gallery-panel` | `webclient-gallery-panel::subject-selection-is-session-presentation-state-retired-with-the-options-layer` | Same selection test; helper returns selection facts only |
| `webclient-art-panel` | `webclient-art-panel::worker-completion-pushes-a-targeted-art-panel-update` | Extend `test_art_push.py` for combined, gallery-only, roster-only, failure, late, isolation, reconnect, and unavailable-panel cases |

Completion delivery stays in `webclient-art-panel` because it already owns worker notification, targeting, revision, isolation, and reconnect rules. Its historical title still accurately includes a targeted art update; the body now owns the companion panels too. Adding parallel completion requirements in gallery/roster would duplicate one subscriber contract. `webclient-character-roster::roster-portraits-resolve-through-the-named-portrait-subject-mechanism` remains unchanged: preserve/verify its existing resolution tests, rather than adding a roster delta about delivery.

The gallery-panel selection text currently says gallery-affected, and the management selection requirement and Purpose describe a single gallery update. Amend both selection requirements with complete retained scenarios; update Purpose during implementation/sync, not in this artifact-only proposal commit. The stale tuple at `test_gallery_actions.py:412` and gallery-only helper assertion at line 195 must be replaced, not supplemented with contradictory tests. Extend existing registered modules; if implementation unexpectedly adds/moves one, update `.github/evennia-shards.json` in that same implementation commit. Use synthetic fixtures, pure `unittest.TestCase` for pure gate logic, and the existing Evennia fixture conventions for integration paths.

### D6 — No frontend changes (fixed)

The left stage actor consumes the committed current roster row's portrait; dialogue-host/right combat portraits consume art's catalog. `currentPortrait` and `hostPortrait` are computed refs, so existing `ui_update` commits re-evaluate them. `StageActor` already crossfades on a new portrait URL under scene-transitions D5. Verify these existing assumptions without editing SPA code or introducing a frontend workaround. Completion does not guarantee a new URL when canonical resolution still chooses a different default/binding; the client must display the actual freshly resolved value, not the just-completed image by fiat.

## Risks / Trade-offs

- [Uniform action declarations add two renders even for selection/generation] → Accept the fixed correctness-over-precision decision; reuse existing presenters and publish only once.
- [Every completion renders three bounded panels per eligible session] → Accept the read cost for stateless, correct targeting; reuse one context and coordinator registry, with no subscription cache or per-panel registry rebuild.
- [A single art-first early return would preserve gap B] → Assert gallery-only and off-room roster-only publication with no art match, plus an art-unavailable case.
- [Incorrect declared key hides behind a full snapshot] → Assert exact registered names and `ui_update` with no `ui_snapshot` in action regressions.
- [Pending spinner disappears but a stage URL need not change] → Assert gallery settles truthfully and portraits equal current resolver output; never invent a new default.
- [Concurrent `square-face-rect-contract` work shares action code/tests and one main spec file] → No dependency; integrate distinct requirement blocks and preserve its square-validation behavior/fixtures. Only this proposal directory is edited here. `configurable-http-user-agent` has no planned overlapping files.

## Migration Plan

Deploy the backend declaration/subscriber change together with focused regressions. No migration, compatibility shim, client rollout, or worker restart protocol is needed. Rollback is a normal revert of this backend behavior change, restoring the known refresh gap rather than adding dual contracts. Main specs are synchronized only in the subsequent implementation/archive workflow, not by this proposal.
