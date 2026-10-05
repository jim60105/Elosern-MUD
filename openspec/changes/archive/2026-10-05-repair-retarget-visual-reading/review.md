# Final visual review: archived desktop viewport retargets

Role: implementation-capable Game UI visual reviewer. This English change
note and evidence-backed review cover
`retarget-desktop-viewport-contract` (merge `e183bec3`) and
`retarget-browser-acceptance-viewports` (merge `e5f404e7`). Current specs take
precedence over those immutable archived artifacts.

## Actual-game method

The reviewer used the established `BrowserRuntime` / `ManagedServer` seed,
login and deterministic exploration/minimap fixtures, in an isolated temporary
SQLite database. No live user database, external LLM or art generation was
used. The authored SPA was built with pnpm and its assets collected into the
owned runtime's isolated static root. This collection step matters: reloading
a running fixture alone initially continued serving its older startup copy.

All navigation, controls and screenshots used the unique headless
`agent-browser` session `codex-final-visual`. The actual CSS reference viewport
was **1451 × 790**, devicePixelRatio 1. Actual native font metadata was read
from that same owned Chromium through CSS.getPlatformFontsForNode; CDP was
not used for screenshots or replacement browser interaction. Screenshots were
opened as images and assessed alongside DOM/SVG measurements.

Evidence is retained locally in **`/tmp/codex-final-visual-evidence/`**.
`measurements.json` records prose, viewport, SVG, platform-font and reader
measurements. Paths below are relative to that directory. The repair commit
is identified in the delivery response; fix files are listed here so this
report does not contain an impossible self-referential commit hash.

## Findings and repairs

| Severity | Relationship | Before evidence / reproduction | Root cause | Fix files | After proof |
| --- | --- | --- | --- | --- | --- |
| High | Related | `before-exploration.png`, `before-map-vertical.png`, `before-full-map-vertical.png`. The minimap's 16-unit label measured **12.89 effective CSS px**. The full-map whole-drawing fit made an eight-row map visibly unreadable. | SVG fitting shrank labels as well as geometry; historic map scenarios explicitly allowed a 0.75 island floor and even smaller full-map fits. | `use-map-lattice-geometry.js`, `map_view.js`, `use-map-view.js`; current map spec and amendment delta. | `after-map-vertical.png`, `after-full-map-vertical.png`, `after-full-map-north.png`, `after-full-map-recentre.png`, `after-minimap-graph.png`, `after-full-map-graph.png`: drawn labels **16px** at reference, full map **20px** after one zoom step; real panning reaches the opposite end without shrinking type. All topology remains in the model. |
| Medium | Related; disclosed minimap risk | `before-map-vertical.png`. At pitch **40**, the upper label's bottom intruded into the lower current marker's footprint. Label bottom/marker top measured approximately **387.42 / 386.66px** in the original view. | Pitch considered horizontally adjacent visible names but not an upper label against a lower marker. Suppressed lower wilderness labels could still have a marker. | `use-map-lattice-geometry.js`, `use-map-lattice-render.js`; existing island/browser regression owners. | `after-map-vertical.png`: derived pitch **47**, 16px glyphs, measured upper-label/lower-current-marker gap **6px**. Browser regression also checks an upper label above an unlabeled lower wilderness marker, a positive gap, and retention of all eight nodes. |
| Medium | Related; disclosed reader risk | The strengthened cold-font actual-SPA full-log regression reproduced **paragraphs 1–5 changing to 1–4** after an append while page number and box remained unchanged. Earlier warmed-font manual captures did not reproduce the literal historical 1→2 jump; they are not presented as evidence of that jump. | Mount-time `document.fonts.ready` did not request sliced Jim faces for new response glyphs. Initial synchronous fit probes could cut against fallback metrics; opening the full log loaded the missing faces, so the next append recut the old reader content. Resetting the test baseline after append hid this. | `use-message-measure.js`, `MessageWindow.vue`, `message_window_font_readiness.test.js`, existing `test_browser_input_narrative.py` journey. | Preparation loads the actual rendered response or beat-and-tail glyph stream in both weights before fitting. Superseded/unmounted requests cannot commit, and uncommitted bindings cannot pace old pages. The original offset-based retention semantics remain; there is no stale-page freeze or page-index special case. `after-message-Aminus.png`, `after-message-A.png`, `after-message-Aplus.png` and the corresponding full-log images cover all prose steps; final strict cold-font browser outcome is recorded under verification. |
| Medium | Unrelated | `before-unrelated-equipment-heading.png`: the equipment heading wrapped its two glyphs vertically, and its informational tag was nearly illegible. The tag's RGB was **97,90,76**, about **2.85:1** against the unchanged opaque ink backing. | A non-wrapping flex heading squeezed its anonymous text item; informational captions used the disabled-ink paper step. | `EquipmentDoll.vue`, `InventoryPanel.vue`, existing inventory browser journey. | `after-unrelated-equipment-heading.png`, `after-inventory-selected.png`: heading occupies **one text row**, tag can wrap separately, and informational tag/count/unit/empty-equipment text measures **8.02:1** against the nearest opaque backing. Regression covers reference and capped desktop viewports. |

The map amendment removes the historical vertical-clearance exception and
below-floor fit behavior rather than weakening the global text requirement.
Its readable windows use existing pan, zoom, recentre, focus-reveal and
remembered-name paths. It does not move HUD anchors, drop nodes or alter
bearings to achieve readability.

## Surface critique and coverage

- **Exploration/message:** `after-exploration.png`, `after-message-Aminus.png`,
  `after-message-A.png`, `after-message-Aplus.png`. The stage, message band,
  top bar and minimap remain anchored. The long Chinese response wraps without
  horizontal document overflow. Larger prose consumes more page capacity
  rather than overlapping the action dock.
- **Combat:** `after-combat.png` is real deterministic engage gameplay.
  `after-combat-five-foes.png`, `after-combat-targets.png` and
  `after-combat-targets-last.png` exercise a validated synthetic two-ally,
  five-foe snapshot through the actual SPA and real attack/target/keyboard
  controls. The complete side roster is readable; only the three stage foes
  selected by the existing stage rules have silhouettes. The scrolling dock
  is exercised, not mistaken for a permanently clipped final target.
- **Dialogue:** `after-dialogue.png` is the scripted fixture NPC's actual
  dialogue entry and choices, followed by the real end-dialogue control.
  No generated free-form dialogue is claimed.
- **Status/inventory:** `after-status.png`,
  `after-unrelated-equipment-heading.png`, `after-inventory-selected.png`.
  The drawers preserve their existing scrolling body and contain readable
  stat/value rows. Empty/missing portraits are the fixture's honest placeholder
  state, not a missing live-art dependency hidden by the review.
- **Settings/full log:** `after-settings-Aminus.png`, `after-settings-A.png`,
  `after-settings-Aplus.png`, `after-full-log-Aminus.png`,
  `after-full-log-A.png`, `after-full-log-Aplus.png`, and
  `after-full-log-latest-Aminus.png`, `after-full-log-latest-A.png`,
  `after-full-log-latest-Aplus.png`. The actual A− / A / A+ controls select
  **16 / 18 / 20px**, with message leading **24 / 27 / 30px** and full-log
  leading **28 / 31.5 / 35px**. The native glyph metadata for the long Chinese
  `.out` prose reports the custom **Jim Mono TC** face, not just its family
  token. Home/return-to-latest/close controls are exercised while appending.
- **Minimap/full map:** the vertical, 64-node dense, remembered-name wilderness
  and radial graph fixtures are validated snapshots in the actual SPA.
  `after-minimap-dense-edges.png`, `after-full-map-dense-edges.png`,
  `after-full-map-dense-zoom.png`, `after-minimap-wilderness-names.png`,
  `after-full-map-wilderness-names.png`, `after-minimap-graph.png` and
  `after-full-map-graph.png` cover these shapes. Named wilderness edge-marker
  text measures **16px** on the full map. Oversized map views deliberately
  clip off-window geometry; existing view operations make it reachable.
- **Desktop scales:** `after-1741-exploration.png` records CSS viewport
  **1741 × 948**, scale **1.1999**, message box about **1124.67 × 237.64px**,
  and map canvas about **287.97px** square. `after-2560-exploration.png` and
  `after-2560-full-log.png` record **2560 × 1440**, capped scale **1.4**,
  message box about **1664.67 × 370.23px**, and map canvas about **336px** square.
  These are CSS dimensions, not sizes inferred from the image reader's
  display thumbnail.

Reference scans of exploration, combat root/targets, status, inventory,
settings and full log found no visible leaf text below 16 CSS px and no
horizontal document overflow. SVG sizes were multiplied by getScreenCTM's
rendered scale; the final five-foe HTML scan also accounted for ancestor
transforms and found no text below the floor. Nodes outside deliberately clipped map windows are not claimed
to be simultaneously visible. Contrast measurements above use the actual
computed informational colors and nearest opaque backing; this review does
not claim a pixel-perfect contrast audit of every background image or every
colorblind theme.

## Verification

Final exercised checks include:

- `pnpm test`: **137 files, 1546 tests passed**.
- `pnpm exec vitest run` on the four focused message/font/beat/typing files:
  **61 tests passed**, including production asynchronous readiness cases.
- `pnpm run build`: passed. Existing warnings concern the runtime-resolved
  `/art/defaults/man.webp` reference and bundle chunk size.
- `node --test web/static/webclient/js/tests/*.test.js`: **479 passed**.
- `pnpm run build-storybook` and `pnpm run showcase-coverage`: passed;
  **64 required components and 64 registered story titles covered**.
- Focused browser driver: strict cold-font retained-log, resize and prose
  preference cases **3 passed**; inventory grid **2 passed**; full-map
  navigation/drag/remembered-name cases **5 passed**; proportional scale
  module **5 passed**; local-map geometry **3 passed**; map legibility
  **3 passed**.
- `uv run --locked python -m tools.contract_gate`: passed,
  **1867/1867 requirements covered**, zero traceability errors and **18
  contract tests passed**; observability, data and manifest checks passed.
- `openspec validate --all --strict`: **283 passed, zero failed**.

Intermediate checks exposed obsolete map-fit assertions, a missing import after removal of
obsolete fit-inset math, and the cold-font reader-content defect. These were
repaired; their failed intermediate checks are not reported as passes.
Browser journey methods were extended in place, preserving existing
traceability and shard ownership rather than introducing weaker replacement
journeys. No project lint script is defined (`pnpm run lint` reports a missing
script); no lint pass is claimed.

## Scope limits and stylistic suggestions

Desktop only. The dense map and five-foe cases are synthetic protocol coverage,
not claims of naturally occurring gameplay populations. The deterministic
fixture covers real login, exploration, scripted dialogue and engage controls;
no live LLM, generated art, free-form conversation or user browser is involved.
The literal historical 1→2 reader jump was not reproduced in the already
warmed manual session; the cold-font text displacement was reproduced by the
strict actual-game regression and addressed at its font-readiness root.

The compact tag can occupy two rows and decorative silhouette text can be
occluded by the intentionally stacked foreground actor; authoritative names
remain readable in their labels/roster. Those are stylistic observations, not
additional clipping/reader-risk repairs or excuses for a smaller font floor.
No gratuitous HUD redesign is proposed.

The initial working tree was clean. Only the reviewer's explicitly listed
repair, tests, current docs/specs and new amendment artifacts are to be staged.
Previously mentioned user-owned test-guard/count-runner files and the old
visual-reading worktree/branch are not part of this repair. The owned browser
was closed and the owned managed service stopped; its recorded processes and
isolated runtime are cleaned by `ManagedServer.stop()`. The temporary launcher
and runtime metadata were removed. Screenshots and measurement evidence remain.
