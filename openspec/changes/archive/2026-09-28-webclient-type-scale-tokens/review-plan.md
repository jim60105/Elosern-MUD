# UI/UX review coverage and batch integration plan

## Provenance and decision boundary

Source: the interrupted review `uiux-review/REPORT.md` for master `d46c4e5d`, dated 2026-09-27, supplied at `/tmp/claude-1000/-var-home-jim60105-repos-MUD/8a54299f-771e-43cf-8bf1-afd39759ac31/scratchpad/uiux-review/REPORT.md`. The table below is the durable disposition of all **57 surface bullets**, including every composite concern and low-priority extra, rather than only the top ten. L-numbers refer to that report. Its opening summary and top-ten table repeat these findings; the final extras repeat map/dialogue/command-line/settings/motion/bag/lineage/top-bar/place/participant/lock rows below.

Review observations are accepted as observations, not evidence that every suggested cause or fix is correct. Current source and main specs were examined when choosing the bounded changes. No browser, art generation or application test was run while proposing. Creation was reviewed in Storybook only; reduced motion was inferred from code/tokens in the source review. Every visual proposal includes actual-surface smoke work for application. In particular the terminal-hold screenshot is real review evidence, but a mode-layer mismatch remains a source-supported cause to reproduce, not a verified runtime diagnosis; freezing canonical art is explicitly forbidden.

The architectural source of truth remains the engine design and the approved AVG desktop design. These proposals extend previously excluded drawer styling deliberately, do not redesign gameplay hierarchy, and explicitly amend root keyboard presentation/map numeric examples where needed. The project is pre-release: no compatibility adapters or persisted-data migrations. Planning artifacts stay on the primary branch; application branches are cut later by the apply workflow.

## Complete finding disposition

| Report finding | Implementation owner(s) | Disposition / boundary |
|---|---|---|
| Top bar 1 (L18) | `webclient-chrome-navigation-polish` | Accept stable slots, but absent controls stay absent rather than aria-disabled substitutes. |
| Top bar 2 (L19) | `webclient-chrome-navigation-polish`, `webclient-drawer-frame-unification` | Existing title/aria names are not absent; add focus-visible tooltip and shared glyphs. |
| Top bar 3 (L20) | `webclient-chrome-navigation-polish` | Accept baseline/tracking polish. |
| Place card 1 (L23) | `webclient-chrome-navigation-polish` | Accept hierarchy, tabular time and removal of orphan separator. |
| Vitals 1 (L26) | `webclient-zh-tw-copy-and-labels` | Accept readable condition names and localized modifiers; preserve severity/duration/overflow. |
| Vitals 2 (L27) | `webclient-combat-participant-polish` | Accept ribbon; reject blind round+1, show preparation at zero and preserve canonical positive counts. |
| Vitals 3 (L28) | `webclient-type-scale-tokens` | Accept numeral face/tabular figures. |
| Vitals 4 (L29) | `webclient-stage-actor-grounding` | Accept compact-view silhouette-label clearance; preserve HUD authority. |
| Minimap / full map 1 (L32) | `webclient-map-legibility` | Accept ordinary-label target and geometry pass; reject blanket non-adjacent-label removal and universal floor for arbitrary dense fixed-canvas maps. |
| Minimap / full map 2 (L33) | `webclient-map-legibility` | Accept marker clarity/material tuning; existing dots/one-vignette already provide material, reject invented terrain contours and unreserved pin offset. |
| Minimap / full map 3 (L34) | `webclient-map-legibility` | Accept readable header; retain textual orientation, not icon-only convention. |
| Stage & portraits 1 (L37) | `art-default-portraits-transparent`, `webclient-stage-actor-grounding` | Static defaults must be newly generated from project prompts and processed by existing cutout pipeline; client adds grounding, not a new cutout or blanket ellipse mask. |
| Stage & portraits 2 (L38) | `webclient-stage-actor-grounding` | Accept standing silhouette; generating label/shimmer only for truly pending state. |
| Stage & portraits 3 (L39) | `webclient-stage-caption-and-hold-backdrop` | Accept one truthful badge and meaningful caption; reject hover-only hiding of required status/control. |
| Stage & portraits 4 (L40) | `webclient-stage-actor-grounding` | Accept stage-only visual caption suppression; retain accessible identity and drawer captions. |
| Stage & portraits 5 (L41) | `webclient-combat-participant-polish` | Accept foe names, gauge outline and acting/target cue without interactive stage controls. |
| Stage & portraits 6 (L42) | `webclient-combat-participant-polish` | Accept head clearance; keep existing depth ratios and never crop heads to hide overlap. |
| Stage & portraits 7 (L43) | `webclient-stage-caption-and-hold-backdrop` | Observation accepted; mode-layer cause is source-supported hypothesis, not newly reproduced. Retain combat decoration, never freeze canonical scene identity. |
| Stage & portraits 8 (L44) | `webclient-stage-caption-and-hold-backdrop` | Accept modest veil/desaturation with motion tokens. |
| Message window 1 (L47) | `webclient-band-material-pass` | Accept feather, edge ornament and divider without changing fixed band/art budget. |
| Message window 2 (L48) | `webclient-ansi-narrative-tones` | Accept muted foreground palette; saturation ceiling differs deliberately to preserve theme gold. |
| Message window 3 (L49) | `webclient-message-typesetting` | Accept progressive prose-only CJK spacing; no global halt or ASCII-map mutation. |
| Message window 4 (L50) | `webclient-message-typesetting` | Accept marker at prose edge within reserved strip. |
| Message window 5 (L51) | `webclient-message-typesetting` | Accept 1.5 line height/.45em paragraph gap; reject 26px change, preserve contracted 28px reference and measured paging. |
| Message window 6 (L52) | `webclient-message-typesetting` | Accept name-aligned underline. |
| Message window 7 (L53) | `webclient-message-typesetting` | Accept focus-only reader rule. |
| Command panel / scene overview 1 (L56) | `webclient-band-material-pass` | Accept quieter container and strong active-row focus; retain visible container focus when it owns focus. |
| Command panel / scene overview 2 (L57) | `webclient-band-material-pass` | Accept opaque popover and single target heading; retain other breadcrumbs. |
| Command panel / scene overview 3 (L58) | `webclient-band-material-pass`, `webclient-type-scale-tokens` | Accept shared strip baseline/readable hint and keycap treatment. |
| Command panel / scene overview 4 (L59) | `webclient-band-material-pass` | Accept secondary button styling of existing footer actions; no new actions. |
| Dialogue 1 (L62) | `webclient-message-typesetting` | Accept corner ornaments and leave-icon tint; no destructive whole-row frame. |
| Dialogue 2 (L63) | `webclient-message-typesetting` | Accept non-activating local first-enabled highlight; respect reader eligibility gate. |
| Combat 1 (L66) | `webclient-combat-command-window` | Accept vertical root presentation; amend horizontal keyboard contracts while preserving actual resolver hierarchy/confirmation. |
| Combat 2 (L67) | `webclient-combat-command-window` | Accept bounded list, reserved hints and current category/group detail. |
| Combat 3 (L68) | `webclient-combat-command-window`, `webclient-zh-tw-copy-and-labels` | Accept basic-attack eligible-foe initial focus and localized enum display; no candidate reorder or auto-submit. |
| Combat 4 (L69) | `webclient-combat-command-window` | Accept exact neutral inline count. |
| Combat 5 (L70) | `webclient-combat-participant-polish` | Accept readable compact thumbnails/HP; reject aria-only tokens because visible tokens support existing targeting contract. |
| Combat 6 (L71) | `webclient-combat-command-window` | Accept waiting/skip cue; reject fake determinate percentage. |
| Character creation 1 (L74) | `webclient-creation-display-labels`, `webclient-creation-screen-redesign` | Accept bounded regions, native themed controls, localized race/axis labels, usable presets and bounded allocation bars. Reject new custom-select framework, unprovided preset art and new radar/stat engine; Storybook observation only, live acceptance required at application. |
| Drawers & overlays 1 (L77) | `webclient-drawer-frame-unification` | Accept opaque panel/scrim; reject viewport-bottom inset that conflicts with command-line clearance. |
| Drawers & overlays 2 (L78) | `webclient-drawer-frame-unification` | Accept shared presentational header/close; preserve distinct modal lifecycles. |
| Drawers & overlays 3 (L79) | `webclient-zh-tw-copy-and-labels` | Accept localized real controls reference and meaningful heading. |
| Drawers & overlays 4 (L80) | `webclient-drawer-content-polish` | Accept left subject-related art; remove irrelevant art instead of inventing chapter illustrations; one truthful state. |
| Drawers & overlays 5 (L81) | `webclient-drawer-content-polish` | Accept committed hero identity, action row and aligned content-sized cards. |
| Drawers & overlays 6 (L82) | `webclient-drawer-content-polish` | Accept shared empty guidance; keep unavailable reasons distinct. |
| Drawers & overlays 7 (L83) | `webclient-zh-tw-copy-and-labels` | Accept server race display title, structured local dates, localized party term; no parsing keys or persistent renaming. |
| Drawers & overlays 8 (L84) | `webclient-full-log-frame` | Accept shared log frame, echo separators in place and return-to-latest. |
| Drawers & overlays 9 (L85) | `webclient-drawer-content-polish` | Accept compact rows/nearby progress and root-node subtitle from existing payload. |
| Drawers & overlays 10 (L86) | `webclient-drawer-content-polish` | Already backed by current item-presentation contract; verify/tune frames from supplied rarity, do not invent item metadata or reimplement icon pipeline. |
| Settings 1 (L89) | `webclient-settings-reading-preview` | Accept native-semantic theme switches and isolated preference sample. |
| Settings 2 (L90) | `webclient-settings-reading-preview`, `webclient-type-scale-tokens` | Accept readable help and balanced cards, not fixed blank filler heights. |
| Command line 1 (L93) | `webclient-band-material-pass`, `webclient-type-scale-tokens` | Accept one focus frame and centered readable input while retaining monospace input semantics. |
| Motion 1 (L96) | `webclient-band-material-pass` | Accept restrained tokenized wipe/fade; no 72-degree flip. |
| Motion 2 (L97) | `webclient-message-typesetting` | Accept slower low-travel bob; reduced/off static. |
| Motion 3 (L98) | `webclient-stage-actor-grounding` | Accept pending-only shimmer; reduced/off static. |
| Cross-cutting 1 (L101) | `webclient-proportional-ui-scale` | Accept single-factor chrome scaling; reject whole-root zoom/double-scaled vh prose/art. |
| Cross-cutting 2 (L102) | `webclient-type-scale-tokens`, `webclient-proportional-ui-scale` | Accept type/numeral and radius consolidation. Reject literal-CSS/token-list guards; use rendered readability and geometry proof. |

## Dependency and code-conflict matrix

All changes target at most one engineer-day: the large drawers bundle is split into frame, content and log; creation is split into labels/protocol and layout; stage actors and combat participant information are separate. Each proposal contains its own machine-readable `depends-on` lines. **These are application dependencies, not archive prerequisites.** Artifact creation itself remains one proposal commit per change on master.

The exact conservative queue is below. ANSI and static-art work may start independently alongside the first type-token change. All other UI work runs in the listed serial chain because it shares shell composition, design tokens, stories, or the same current main-spec files. Do not interpret “different component” as parallel-safe when both deltas modify one capability. This sacrifices speculative parallelism to avoid lost contract updates; a supervisor need not infer transitive conflicts.

| Queue | Change | Direct dependencies | One-day boundary | Potential code/spec conflicts |
|---|---|---|---|---|
| 1 | `webclient-ansi-narrative-tones` | none | Tone down ANSI foreground colors without changing server markup or background colors. | MessageWindow story conflict with typesetting; palette ground coordinated with band. |
| 2 | `art-default-portraits-transparent` | none | Regenerate shipped default portraits from project prompts, then run the existing alpha-cutout workflow; no runtime pipeline redesign. | Independent of UI code; static-art output/provenance paths only. |
| 3 | `webclient-type-scale-tokens` | none | Establish a readable shared chrome type/numeral scale and remove arbitrary size sprawl. | Serialize with the preceding/following UI slice; styles/tokens.css and existing component/styles font declarations except map geometry; stories and focused runtime readability checks |
| 4 | `webclient-stage-caption-and-hold-backdrop` | `webclient-type-scale-tokens` | Consolidate truthful stage captions and keep combat decoration through terminal playback. | Serialize with the preceding/following UI slice; AppClient.vue, SceneBackdrop.vue, styles/app-shell.css, styles/tokens.css; backdrop/terminal-playback stories and journeys |
| 5 | `webclient-stage-actor-grounding` | `webclient-stage-caption-and-hold-backdrop`, `art-default-portraits-transparent` | Ground standing portraits and honest no-art silhouettes without changing the art pipeline. | Serialize with the preceding/following UI slice; StageActor.vue, ReferenceArtwork.vue (stage-only variant), FoeLineup.vue, styles/app-shell.css; actor stories and geometry journeys |
| 6 | `webclient-combat-participant-polish` | `webclient-stage-actor-grounding` | Make participant and foe identities legible while preserving canonical HP and round semantics. | Serialize with the preceding/following UI slice; ParticipantFrame.vue, FoeLineup.vue, StatusPanel.vue and combat status header owner, styles/app-shell.css; combat stories/journeys |
| 7 | `webclient-band-material-pass` | `webclient-combat-participant-polish` | Unify the bottom-band material, focus hierarchy, exploration popover and motion. | Serialize with the preceding/following UI slice; HudFrame.vue, ActionDock.vue, SceneOverview.vue, DockVerbPopover.vue, CommandLine.vue, styles/app-shell.css, styles/tokens.css |
| 8 | `webclient-message-typesetting` | `webclient-band-material-pass`, `webclient-ansi-narrative-tones` | Improve CJK prose spacing and anchor reading furniture to the actual text measure. | Serialize with the preceding/following UI slice; MessageWindow.vue, FullLogOverlay.vue prose styles, DialogueChoices.vue, styles/tokens.css; narrative measurement tests and stories |
| 9 | `webclient-combat-command-window` | `webclient-message-typesetting` | Present the unchanged combat hierarchy as a vertical command window with truthful contextual detail. | Serialize with the preceding/following UI slice; DockTabBar.vue cutover, ActionDock.vue, DockMenu.vue, SkillDetailPane.vue, AppClient.vue, combat_menu.js and frame resolver/store focus derivation |
| 10 | `webclient-drawer-frame-unification` | `webclient-combat-command-window` | Unify reference drawer and overlay framing without moving their modal boundary. | Serialize with the preceding/following UI slice; OverlayHost.vue, HudDrawer.vue, GalleryPanel.vue header, AppClient.vue overlay title/icon mapping, shared DrawerHeader component and styles |
| 11 | `webclient-drawer-content-polish` | `webclient-drawer-frame-unification` | Normalize drawer content hierarchy, honest art placement and empty states. | Serialize with the preceding/following UI slice; CharacterStatusDrawer.vue, QuestLog.vue, LoreCodexDrawer.vue, PartyDrawer.vue, InventoryPanel.vue, LineagePanel.vue, AppClient.vue art slots, shared EmptyState component |
| 12 | `webclient-map-legibility` | `webclient-drawer-content-polish` | Raise map chrome readability while preserving truthful geometry and simplify the current-location ornament. | Serialize with the preceding/following UI slice; LocalMap.vue, MapOverlay.vue, MapLattice.vue, map-lattice.css and shared geometry/label declarations; map stories/geometry browser checks |
| 13 | `webclient-chrome-navigation-polish` | `webclient-map-legibility` | Stabilize top-navigation placement and polish the place card without changing visibility rules. | Serialize with the preceding/following UI slice; DesktopNavigation.vue, TopBar.vue, PlaceCard.vue, dock-icons.js, styles/app-shell.css |
| 14 | `webclient-settings-reading-preview` | `webclient-chrome-navigation-polish` | Give reading preferences a safe live sample and consistent controls. | Serialize with the preceding/following UI slice; SettingsOverlay.vue, existing reader/typewriter helper, settings stories/tests |
| 15 | `webclient-full-log-frame` | `webclient-settings-reading-preview` | Frame the full log as a readable reference surface with an explicit return-to-latest control. | Serialize with the preceding/following UI slice; FullLogOverlay.vue, shared DrawerHeader, log stories and reading tests |
| 16 | `webclient-zh-tw-copy-and-labels` | `webclient-full-log-frame` | Remove English/raw-key leaks from help, combat labels, conditions, codex and gallery copy. | Serialize with the preceding/following UI slice; lib/controls-reference.js, lib/condition_label.js, ConditionChips.vue, HelpOverlay.vue, SkillDetailPane.vue, PartyDrawer.vue, GalleryPanel.vue and gallery formatting helper, presentation/gallery.py, lore codex read-model label owner |
| 17 | `webclient-creation-display-labels` | `webclient-zh-tw-copy-and-labels` | Expose canonical creation race display names and distinguish mana resource from magic offense. | Serialize with the preceding/following UI slice; world/rules creation read-model, web/webclient/presentation/creation.py, JS protocol creation validator, CreationOverlay.vue and creation menu consumers/fixtures |
| 18 | `webclient-creation-screen-redesign` | `webclient-creation-display-labels` | Compose the existing creation wizard into a bounded three-region desktop workspace. | Serialize with the preceding/following UI slice; CreationOverlay.vue, creation-overlay.css, existing creation form/allocation preview components and stories |
| 19 | `webclient-proportional-ui-scale` | `webclient-creation-screen-redesign` | Scale desktop chrome with the 1080p reference without double-scaling prose or stage art. | Serialize with the preceding/following UI slice; styles/tokens.css, HudFrame.vue/AppShell.vue, styles/app-shell.css, fixed chrome dimensions in touched navigation/island/dock/drawer/creation components |

### Contract ownership and merge rules

- `webclient-contextual-hud`: caption/hold owns its two full modified requirements; participant polish owns participant content; combat-window renames/modifies the root requirement; proportional scaling modifies stage geometry last. Other UI slices add distinct requirement titles rather than overwrite those requirements.
- `webclient-combat-menu`: combat-window owns the existing root-keyboard requirement and its scenarios. The current resolver's real root inventory and explicit Forfeit confirmation are authoritative, not the review's illustrative list.
- `webclient-local-map`: map-legibility owns the full existing map-rendering requirement; proportional scaling intentionally carries the post-legibility version and changes only the outer reference-scale square. Apply in that order; never replace it with an old main-spec copy.
- `webclient-character-creation-ui`: display-labels owns v6 exact-schema and race-option changes, retaining transient proposal/draft semantics; creation-layout only adds presentation requirements. No data migration or v5 compatibility parsing.
- `webclient-vue-application`: type readability and final proportional scaling add separate behavioral requirements. The literal-CSS guard suggested by the review is explicitly rejected. No fabricated requirement IDs or evidence wrappers are part of this plan.
- Verification SHALL NOT assert literal CSS declarations, token lists, or source text; it SHALL assert rendered geometry and readability in browser-level checks.
- Shared-header and EmptyState additions require component manifest/stories/showcase updates during application; replacing DockTabBar requires removing its obsolete callers/story/manifest entry, not an alias. Full-log uses the shared header without adding a second trap.
- Item icons/rarity already have a substantive current contract. The drawer-content slice validates the observed surface and tunes backed styling rather than inventing metadata or a second presentation pipeline.

## Verification and review record

Proposal readiness is established by complete proposal/design/delta/tasks artifacts and strict OpenSpec validation, not by checked implementation boxes. All implementation tasks remain unchecked. The whole set, including the static-art proposal, received one blocking rubber-duck critique before handoff. The critique's three blocking findings (orphaned tab-bar contracts in `webclient-combat-command-window`, restored base numeric scenarios in the two local-map deltas, and viewport qualification in `webclient-proportional-ui-scale`) plus its material non-blocking items were applied to the artifacts; revalidation outcome and commit evidence are reported in the handoff. No application correctness claim is made by this planning document.
