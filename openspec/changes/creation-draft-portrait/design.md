# Design

## Context

See `proposal.md`. This seventh change is the concrete live-slot/drawer integration slice. Backend request, schema-8 state/push and lifecycle cleanup belong to changes 4–6. The stepped form/empty slot belong to change 3. `GalleryGenerateDrawer.vue` currently takes `model`, `preview`, `disabled`, `rejected` and emits `submit({fields, custom_prompt})`; it is passive and can already hide field selection using capabilities.

## Goals / Non-Goals

**Goals:** request and inspect a live portrait while editing the form, using existing drawer and dispatch/revision contracts.

**Non-Goals:** another generation action, another portrait state store, retry loop, backend/lifecycle redesign, art material changes, concept prompt changes or automatic invalidation.

## Decisions

### Passive slot and shared drawer contract

Extend `CreationPortraitSlot.vue` props with `portrait`, `disabled` and `canGenerate`; emit `generate` only. Its host derives silhouette by change 3’s table lookup, current form name and the committed portrait union. Empty/pending/failed/unavailable show the current supplied silhouette; ready passes server artwork unchanged to `ArtworkPreview`. Generation controls are present only after this integration change; pending/unavailable are disabled, failed/empty/ready permit explicit generate/regenerate subject to shared dispatch gate and existing identity input constraints. Do not run full custom-form validation just to open a portrait request.

Announce status with `role="status"` and text, never animation alone. Decorative silhouettes are aria-hidden; ready art carries meaningful current-name alternative text. Native buttons keep visible focus. Spinner/breathing and card transitions respect existing full/reduced/off preferences; no new token or text below `--text-xs`.

Mount the real `GalleryGenerateDrawer` from the creation overlay, above the creation modal at the existing drawer tier, with `context="creation"`. Add its optional `context` prop defaulting to `gallery`. Creation switches only its approved contextual copy and suppresses the existing-character/equipment link and misleading gallery-only explanatory text. Gallery usage with absent prop retains all current behavior.

Pass a small view-model projection, not a second gallery state: `{capabilities: {supports_field_selection: false, supports_free_text: true, max_cards: 1}, groups: [], selected: null, equipment_summary: null}` and a ready-art preview when available. Drawer `submit` may still emit `fields: []`; the host deliberately constructs only the five creation payload keys. The slot emits intent and drawer emits data; neither dispatches.

### Request ownership and lifecycle

Add `composables/use-creation-portrait.js`, composed by `useCreationOverlay` after existing form state. It holds only local `drawerOpen`, admitted request id and request presentation epoch/generation, rejected state and focus opener. On submit read current `race`, `subrace`, `sex`, `apparentAge` refs at that instant and the drawer’s own prompt; do not reuse persisted draft values or concept text. Call the existing return-bearing dispatch prop once with `creation.portrait.generate`. For standalone event-based stories use the existing event seam, with explicit simulated correlated results rather than pretending server success.

If dispatch returns null, keep the drawer/input open and editable with rejection feedback; do not enter pending. An admitted dispatch disables submit until its matching result and declared revision settle. Keep input on matching rejection; close drawer on matching success after its pending publication is committed, then return focus to the slot. A foreign/stale-session result never settles it. A synchronous transport send failure/gate release clears local submitting state without resending. Disconnect/epoch or actor change closes the local drawer and forgets only its pending UI; reconnect reads server state and does not retry. Mode/step changes preserve unsent form fields; leaving creation tears down the local handler/focus state.

The committed panel is the sole source for pending/ready/failed; local submit loading must not fabricate a portrait state. Portrait-only publications never reset local step, name, concept revision or other unsent values. Generation does not save a custom draft or open activation confirmation. Reusing the existing drawer trap gives Escape priority and restores focus; wall/dock capture must ignore the nested drawer.

### Real-component evidence and human review

Update `stories/Overlays/CreationOverlay.stories.js` and synthetic schema-8 fixtures to cover every mode/step, all portrait states, drawer open, refusal, confirmation and common unavailability. Add real slot/drawer stories or declare them through the overlay’s component-manifest mapping. No production import of the reference prototype. Produce this change’s `visual-review.md` as human-reviewed evidence for approved §§7/11/12, at 1451x790 and 2560x1440 and each motion level. Tests establish behavior/geometry, not wording, preset counts or exact markup.

## Risks / Trade-offs

The gallery drawer is a nested modal; it must be above creation, retain its own keyboard ownership and restore focus to a surviving opener. The portrait request may complete before the drawer result arrives; existing result-plus-revision gating avoids optimistic state and preserves typed input through a refused request.

## Dependency and code-conflict matrix

Abbreviations: A artwork, W wall, S steps, R request, P panel, C cleanup, I integration. `shared` means sequence shared files or the same spec requirement; `parallel` means disjoint substantive code, with ordinary documentation/manifest integration.

| Pair | Conflict and required order |
| --- | --- |
| A/W | artwork props/fixtures consumed by wall; A before W |
| A/S | silhouette table/fixtures consumed by slot; A before S |
| A/R | presenter/fallback APIs and art tests; A before R |
| A/P | same panel/mirror/fixtures and version requirement; A before P |
| A/C | parallel after R; no common requirement replacement |
| A/I | descriptor/fixture consumer; A before I |
| W/S | same overlay/CSS/stories and workspace requirement; W before S |
| W/R | parallel code after A; registry vs UI, shared docs/manifests only |
| W/P | parallel code after A/R; shared fixtures/docs require integration |
| W/C | parallel code after R; overlay tests shared |
| W/I | same overlay/stories/focus; W before I |
| S/R | parallel substantive code after prerequisites |
| S/P | fixture/docs/store integration; no same requirement replacement |
| S/C | parallel code; shared overlay tests |
| S/I | same slot/overlay/composable/stories; S before I |
| R/P | receipt/read model and publication result; R before P |
| R/C | same rules/service/queue/tests, autogen spec file but different requirement blocks; R before C |
| R/I | request/echo consumed by drawer host; R before I |
| P/C | receipt/error/reset publication semantics; P before C |
| P/I | union/result/state consumed by slot; P before I |
| C/I | lifecycle browser journey; C before I |

| Other currently open change | Conflict against A/W/S/R/P/C/I |
| --- | --- |
| ciaran-village-local-goods | none in product files/specs; no creation/art/data regeneration overlap |
| fionnen-village-craft-homes | none in product files/specs; only CI manifests if new tests are registered |
| fionnen-village-fare-homes | none in product files/specs; only CI manifests if new tests are registered |

Dependency DAG: A → W → S; A → R → P → C; S and C → I. A safe single-engineer delivery order is A, W, S, R, P, C, I. No child Git repo is needed.

## Design resolutions and preserved predecessor decisions

The approved two deliveries are decomposed into seven bounded engineer-day slices because protocol, two UI surfaces and request/state/lifecycle integration each have separate test owners. The seventh is live UI integration, not an undefined umbrella. The concept guide belongs with S, keeping the original concept behavior.

Preserved verbatim from the surviving generator: schema 6 → 7 replacements, the duplicate race-version sentence removal and neutral “a race label” scenario, and both full ADDED artwork/silhouette requirements including their scenarios. Preserve the chosen canonical card-only official default, alpha terminal, null generation fields, empty retention, no writes, exact table partition/cap and dual-validator rejection. The `other` ambiguity is resolved by actor-specific future-subject hashing; no requirement text or existing band rule is retuned. Existing `proposal` remains an optional top-level field even though the handoff’s shorthand field list omitted it.

Two schema-shape cutovers mean versions 7 then 8, rather than an increment in every newly split delivery. The form’s “always visible” persona scenario is narrowed to the story step with retained values to implement the approved stepped form. Copied control scenarios replace inherited shipped race/affinity values with registry-relative mechanisms; no user content decision changes. Activation rollback guarantees distinguish newly introduced state from previously committed draft art, as approved §14 requires.

Connectivity is the one behavioral deviation from approved §7.3: preserve the authoritative handoff and existing diagnostic-only contract, not the design's offline pre-disable/rejection sentence. Creation never probes connectivity or gates on its cache; a valid offline request reaches the worker and reports its real failure with explicit retry. `unavailable` is reserved for structural receipt/authorization failure, not a cached network verdict. No extra connectivity surface or continue-anyway probe is added.

Strict validation requires existing scenario titles to survive MODIFIED replacement. Keep the historical numeric “Schema version ships as the integer 6” title while its outcome asserts the new version, and keep “Preset lacks artwork” while its body describes absent official art. These are scenario-identity mechanics, not compatibility behavior.

## Acceptance and documentation

Add `tests/overlays/creation_portrait.test.js`; extend existing overlay/concept and gallery editor tests. Implement `web/tests/browser/test_browser_creation_portrait.py` using the managed server’s injected fake art client and real worker/service/publication path. Add a server fixture/seed entry using the repository’s existing browser seed registry pattern, never inject a synthetic ready panel as the generation journey. Each method uses synthetic data and deterministic committed-state waits.

The focused browser methods must cover generation to ready while editing steps, failed generation/retry, disconnect/reconnect without replay, reset/canceled late settle, and custom/preset activation disposition. Existing keyboard custom and preset journeys retain their assertions; geometry checks use both reference viewports. Update the frontend and synchronization guides. Register new methods/modules with the shard tool and map actual tests to added delta scenarios without guessed traceability ids.

```text
pnpm exec vitest run web/webclient-app/tests/overlays/creation_portrait.test.js web/webclient-app/tests/overlays/creation_overlay.test.js web/webclient-app/tests/overlays/concept_fill_navigation.test.js
pnpm run build
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_creation_portrait.CreationPortraitJourneys.test_generate_while_editing
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_creation_portrait.CreationPortraitJourneys.test_reconnect_and_reset
pnpm run build-storybook
pnpm run showcase-coverage
openspec validate creation-draft-portrait --strict
```
