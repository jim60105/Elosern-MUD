## 1. Implement the bounded behavior

- [x] 1.1 Wire explicit optional choice to real sleep outcomes in text/browser adapters; verify zero-duration, rejection, ordinary sleep and actual interrupted results.
- [x] 1.2 Expose server-authored dream state/remaining count and confirm/draft/awaken actions with text parity and a core-design-aligned narrative folio; verify forged owner/stale request rejection, sixth cap and the interactive offline storyboard with agent-browser.
- [x] 1.3 Preserve sleep association and generation-free escape across reconnect/failure; verify tick/gauges/live effects unchanged after departure.
- [x] 1.4 Update both command docs and contract tests, then run changed-path offline sleep→dream→draft/confirm→awaken smoke; verify the complete approved presentation contract.

## 2. Evidence and handoff

- [x] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [x] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [x] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [x] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate dream-sleep-surface --strict`; record exercised results and leave broad browser/evidence gates CI-owned.

## Exercised evidence

- Focused Evennia run: 84 tests passed (`test_dream_surface`,
  `test_dream_session`, `test_skip_commands`, `tests.test_command_docs`).
- Browser-adapter/presenter/skip-command focused run: 26 tests passed.
- Focused Vitest dream and waiting surfaces: 10 tests passed, including shared
  core button classes, disclosure focus and the real stage-mounted storyboard.
- Dependency-free Node protocol/echo gate: 479 tests passed.
- The recorded/offline changed-path smoke is
  `DreamSurfaceTests.test_recorded_changed_path_sleep_exchange_draft_confirm_awaken_smoke`:
  accepted sleep, real guarded FakeLLMClient scene/dialogue, draft, explicit
  confirmation and model-free awakening; physical state remains post-sleep.
- `tools.contract_gate` passed (1859 requirements covered; zero traceability,
  observability, test-data or manifest violations; 18 contracts passed).
- `openspec validate dream-sleep-surface --strict` passed.
- User-requested frontend follow-through uses the `agent-browser` skill and
  `World / DreamPanel / Storyboard`: pending input, generation failure without
  counting, successful scene/dialogue with count decrement, cap, saved thread
  direction, reconnect, explicit confirmation and awakening were exercised
  against the offline Storybook build. The synthetic sleep stayed at 100 → 100.
  Story-only publication controls and production actions both reuse core
  `ui-btn` chrome; confirmation is the only primary action.
- The user-requested UX correction replaces simultaneously exposed inputs and
  raw JSON with one conversational entry, a saved-direction preview, optional
  plain-language preferences and owner-visible factual story labels. The
  sticky footer explicitly distinguishes confirmation/departure, draft storage
  and immediate awakening. Agent-browser exercised the corrected flow and
  captured desktop/narrow screenshots; the 390px viewport had a 390px page
  width (no horizontal overflow).
- The user-requested immersive artwork uses the supplied image-generator and
  natural-language prompt-builder skills and the full `.env` scene profile.
  A reviewed, bundled 1536×864 AVIF supplies the white-bed/adult-goddess
  dream stage; no permanent test or runtime UI calls sd-webui.
- The supplied core-panel notes replace the framed drawer with a full artwork
  stage and a bottom-left feathered-ink/brass-mounted dialogue instrument.
  Native keyboard focus remains trapped, closed disclosure fields are excluded,
  and Escape uses the existing revision-gated awakening action.
- The frozen showcase manifest remains frozen with 64 registered components.
  The four existing showcase evidence modules were exercised and six assertions
  expose legacy drift unrelated to DreamPanel: every one names only
  `World/LettersPanel`, `Overlays/GalleryStageTransformModal`, and (the overlay
  coverage assertion only) `Core/CompanionLineup`, plus the World and Overlays
  story-directory partitions that omit `LettersPanel.stories.js` and
  `GalleryStageTransformModal.stories.js`. Master's manifest already carries
  those keys while the frozen baselines omit them, so the assertions fail
  identically on master. DreamPanel is registered in each affected assertion,
  and those unrelated frozen baselines are intentionally unchanged.
- Resume verification completed the browser action-catalog lockstep the
  committed dream surface implied: the four `dream.*` adapters now appear in
  `command_echo_coverage_manifest.json`, the dependency-free Node coverage
  fixture (`command_echo.test.js`), the Vitest per-surface behavioral table
  (`web/webclient-app/tests/store/command_echo_surfaces.test.js`), and the
  exact production-registry pin
  (`web/webclient/actions/tests/test_dispatcher/test_registry.py`), and the
  `dream` panel in the exact panel-name pin
  (`web/webclient/presentation/tests/test_combat_panel/test_presenter.py`).
  The `webclient-action-dispatch` requirement is carried as a MODIFIED delta.
- Focused Evennia rerun: `world.narrative.tests.test_dream_surface` 15 tests
  passed; `test_dispatcher.test_registry`, `test_combat_panel.test_presenter`
  and `test_action_catalog_coverage` ran 23 tests with two failures that now
  name only the pre-existing `letters.list`, `letters.collect`, `letters.read`,
  `letters.send` and `gallery.stage.update` registry drift. Those five ids were
  registered on master by the correspondence and gallery-stage-transform
  changes without catalog entries, so both pins fail identically on master;
  this change no longer contributes to either diff and the unrelated ids are
  intentionally unchanged.
- Final gate rerun: full Vitest suite 136 files / 1523 tests passed, the
  dependency-free Node gate 479 tests passed, `pnpm run build`,
  `pnpm run build-storybook` and the 64-component `showcase-coverage` gate
  passed, `openspec validate dream-sleep-surface --strict` passed, and
  `tools.contract_gate` passed.
- Broad managed-browser, aggregate coverage and complete evidence gates remain
  CI-owned. Delta-only requirement annotations remain archive-sync owned.

## Review dispositions

The preimplementation critique was folded into actual-tick association, explicit
zero-duration opt-in, authoritative session association, shared owner identity,
pending-submission callback gates rather than revision equality, confirmed-draft
authority, generation-free escape and late-delivery/control tests. Its assertion
that the text command already used `advance_skip` was incorrect; the existing
text and browser settlement seams were preserved instead of introducing a
gratuitous physical-path migration. The actual catalog remains the existing
documentation table. Interrupted results use a synthetic short-commit seam
because the real clock is all-or-nothing.

The single final critique found no blocking issues. Both non-blocking findings
and four suggestions were fixed with focused regressions:

- NB-1: bare confirmation now reads the authoritative durable draft; subsequent
  chat cannot silently replace a saved thread direction or its preferences.
- NB-2: ended surfaces do not query story-thread choices.
- S-1: changed same-session draft fields rehydrate without clearing unsent chat.
- S-2: empty bare confirmation is refused concretely; empty awakening does not
  create a meaningless draft.
- S-4: empty/oversized text input reports its specific stable refusal code.
- S-5: text confirm/awakening delivers its ending once.
- S-3 is deliberately retained: the initial refresh is needed when `dream say`
  is a typed WebSocket command, where no action dispatcher publishes pending
  state. The final refresh publishes completion; neither calls another model.
