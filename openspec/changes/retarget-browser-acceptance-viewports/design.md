# Design — retarget-browser-acceptance-viewports

## Context

The dependency change `retarget-desktop-viewport-contract` moves the contract's reference
viewport to 1451x790 and its cap behavior (2560x1440 renders at S = 1.4, not 4/3). The browser
suites under `web/tests/browser/` are the acceptance surface: `browser_base.py` opens every
journey at `DEFAULT_VIEWPORT` and the geometry journeys iterate a fixed viewport tuple. All of
it still names the retired sizes. This change retargets the acceptance half only — test base,
tuples, assertions, and the acceptance requirements that are pure viewport enumerations.

## Goals / Non-Goals

**Goals:**
- CI proves the contract at the sizes the contract names: the reference (1451x790), an uncapped
  large display (1741x948, S = 1.2), and the capped display (2560x1440, S = 1.4).
- Every acceptance requirement keeps its assertions; only the viewport enumerations and the
  reference values they compare against move.
- One clean partition from the dependency change: requirements amended there are never touched
  here, because a MODIFIED delta replaces its whole requirement block.

**Non-Goals:**
- No new fixtures, journeys, or frameworks (`openspec/config.yaml` forbids new test frameworks);
  the tuple elements change, the journeys do not.
- No `web/webclient-app` source edits — if a journey's expected geometry differs from the
  dependency change's spec values, the bug is in whichever side is wrong against the spec, not
  in this change's scope to paper over.

## Decisions

### D1: Acceptance pair (1451x790, 2560x1440); three-element iteration tuple with 1741x948

Two-element requirements (prose "at X and Y") take the pair: the reference is the tight contract
size every surface must fit; 2560x1440 is the capped extreme where chrome stops growing while
the viewport keeps growing — the failure mode a scale-once contract can introduce. Three-element
iterations (the tuples in the Playwright modules) additionally keep a middle, uncapped display:
1741x948, whose height ratio is exactly 1.2 and whose width ratio is 1.1999 (1741 / 1451, the
value the engine's four-decimal rounding writes), is the cheapest viewport that proves chrome
scales proportionally *below* the cap (the old tuple's 1920x1080 did that job against the old
reference). 1440x900 and 1280x720 leave the tuple entirely — they remain valid windows (S = 1
floor) but prove nothing the pair does not.

### D2: Assertion values come from the amended specs, not from measuring renders

Where a journey asserts an absolute (band height 220px at reference, island canvas 240px, page
text 18px at default prose scale, 336px island at the 1.4 cap), the expected value is copied from
the dependency change's amended requirement text — the spec stays the single source; if a test
and the spec disagree, the spec wins and the failure is investigated, never re-pinned to the
render. Tolerances stay as written (±1px geometry, ±0.5px font). Where a module iterates more
than one acceptance viewport, the expected value is derived per viewport from the requirement's
own mechanism (`S = clamp(1, min(h / 790, w / 1451), 1.4)`, the `clamp(190px * S, 27.85vh,
400px * S)` band, `--actor-h = min(62vh, 680px * S, stage box)`), because the three acceptance
viewports render at three different chrome factors; a single absolute cannot state all three.
Assertions must also respect the two active media-query branches: `max-height: 820px` is active
at the reference and inactive at 1741x948/2560x1440, so cross-viewport comparisons are made
within a branch (the reference against itself; the two taller sizes against each other).

### D3: Partition by requirement ownership

`retarget-desktop-viewport-contract` owns every requirement whose text carries derived geometry
(vue-application, contextual-hud, desktop-shell, local-map, input-narrative) and also restates
the viewport enumerations inside those requirements. This change owns the remaining
requirements that name acceptance viewports: browser-verification's foundation journey, the
per-feature keyboard-only/pointer/art acceptance requirements, and creation-ui's bounded-desktop
requirement. The grep gate in tasks proves the two delta sets are disjoint and that, after both
archive, no main-spec requirement names 1440x900 or 1280x720.

## Risks / Trade-offs

- **Losing 1280x720 coverage.** A below-reference size where chrome sits at S = 1 stops being
  CI-proven. Accepted per the user decision: it is off-contract, and the reference at 1451x790
  is a strictly tighter fit test than 1280x720 ever was for the layouts that matter.
- **Journey churn.** ~43 modules change tuples and some assertions; each is mechanical, and the
  suite itself is the review gate.

## Migration plan

Land after the dependency change. Green suite = this change done. If a journey is red because
the dependency's geometry is wrong, fix that change, not the assertion here (D2).

## Open Items

- None.
