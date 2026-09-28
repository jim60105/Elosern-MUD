## 1. Implement the bounded surface

- [x] 1.1 Add the stage-only artwork variant, contour-preserving shadow and silhouette states; inspect done, missing, pending and load-failed stories with both alpha and opaque inputs.
- [x] 1.2 Keep drawer captions unchanged and preserve speaking/beat transitions; verify actor identity and state through accessible component assertions.
- [x] 1.3 Exercise 1280x720, 1440x900, 1920x1080 geometry with vitals, expanded command line and one to three foes; observe non-occluded labels and no new scroll.
- [x] 1.4 Exercise full/reduced/off on the actual stage; retain behavior regression for missing versus pending and motion preference transitions.

## 2. Verify and document the completed behavior

- [x] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [x] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [x] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [x] 2.4 Run `openspec validate webclient-stage-actor-grounding --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.

## Verification evidence

All commands and evidence paths below are relative to the change worktree root
`/var/home/jim60105/repos/MUD/.worktrees/webclient-stage-actor-grounding`,
not `web/webclient-app`. The evidence was captured from the offline production
showcase using headless agent-browser session `a5`.

- `pnpm test web/webclient-app/tests/core/stage_actor.test.js web/webclient-app/tests/core/reference_artwork.test.js web/webclient-app/tests/core/foe_lineup.test.js web/webclient-app/tests/app_client_stage_actor.test.js`: 46 passed across 4 files after the post-review fixes (the run exposing seven obsolete crop/identity/gauge assertions led to updated consumer contracts and a rerun of the same focused files).
- `pnpm run build-storybook`: passed; served `.storybook-out` locally.
- Headless `agent-browser --session a5`: all nine combinations of 1280x720,
  1440x900, 1920x1080 and 1–3 foes, with vitals and command line expanded.
  Player chest labels had no internal overflow; document dimensions equalled
  viewport dimensions. Compact label starts at x=216, beyond vitals' x=200
  right edge. Screenshots: `.storybook-out/a5-{1280,1440,1920}-{1,2,3}.png`.
- `Core/StageActor` player/opaque/missing/pending/failed/load-failed/dimmed/hit
  screenshots: `.storybook-out/a5-state-*.png`. Alpha contours survive;
  opaque backgrounds remain intact as specified. Missing/failed/load-failed
  computed animation is `none`; pending is `actor-pending`.
- Actual client's Settings buttons full → reduced → off → full changed the
  pending SVG's computed animation to `actor-pending` → `none` → `none` →
  `actor-pending`. Missing foe lineup inspected at 1280x720 with readable
  front/back labels: `.storybook-out/a5-foe-missing.png`.
- Dialogue host with a pending placeholder at 1280x720
  (`core-appshell--dialogue-host-pending`): the chest label's rendered ink
  ends at x=1040.66, clear of the map island's left edge x=1046, with no
  internal overflow and document 1280x720 equal to the viewport; the label
  reads cleanly in `.storybook-out/a5-dialogue-host-1280-check.png`.
- With the OS reduced-motion preference emulated
  (`agent-browser set media light reduced-motion`) on
  `core-stageactor--host-pending-placeholder`, the pending shimmer computes
  `none` while `<html>` carries no `data-motion` attribute and `actor-pending`
  once `data-motion="full"` is stored, matching the tokens.css
  `:root:not([data-motion])` fallback convention.
- `openspec validate webclient-stage-actor-grounding --strict`: passed.
- `uv run --locked python -m tools.spec_traceability list --json-output .storybook-out/a5-requirements.json`
  supplied the canonical ID; the existing substantive actor evidence bridge
  carries the annotation. `uv run --locked python -m tools.spec_traceability check --json-output .storybook-out/a5-traceability.json`: exit 0.
  The checker has no capability selector; no test suite or evidence sweep ran.
- Browser observations are retained in `.storybook-out/a5-evidence.json`.
  Screenshot paths are local ignored build artifacts, not committed assets.

## Review dispositions

Pre-implementation review required reconciliation of stage crop specifications
and explicit acceptance of supplied opaque backgrounds; both are recorded in
the deltas and design. Stage-only error text, a single accessible caption,
unchanged anchor ratios, vitals reservation, and overlapping-foe readability
were adopted and verified. Data-status, prop-based motion gating and grapheme
initial reuse were adopted.

The mandatory post-implementation review found no blockers. Its four concerns:

- Fixed OS-reduced fallback precedence to follow the existing
  `:root:not([data-motion])` convention, preserving explicit full preference.
- Preserved the degraded server `unavailable` reason and added a focused
  regression for the real null-status placeholder shape.
- Clarified root-relative evidence paths above and replaced the stock
  static-assets README beside the screenshots with a two-line provenance
  header naming the serve/observe commands, session `a5` and date.
- Added compact dialogue-host verification alongside the combat-player matrix.

Its three suggestions are dispositioned without expanding scope:

- Kept foe identity type at the shared readable token: observed three-foe
  fallback labels fit; shrinking text further is unnecessary.
- Kept ground ellipses inside each crossfading artwork: they follow each
  portrait's opacity, and no observed artifact warrants a new shared layer.
- Rejected source-selector assertions for animation: they pin implementation
  text without proving motion. Actual browser computed animations exercise
  preference transitions; component tests establish truthful state transitions.
