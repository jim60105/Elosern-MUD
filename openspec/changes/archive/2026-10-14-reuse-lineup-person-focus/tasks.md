# Tasks

All tasks remain unchecked for a later apply assignment. Acceptance follows both delta specs and design D1-D4. Eight engineer-hours total. The portrait change is a soft integrated-proof prerequisite; this behavior also works with valid current-schema null-art fixtures.

## 1. Rendered-lineup identity and local emphasis (1.5h)

- [x] 1.1 Derive exploration focus membership from the actual displayed committed `companionLineupSlots`, normalizing identity only for the join; reuse that membership policy for dialogue, suppress actor-right for represented identities and pass a matched non-controlled slot's native identity into the existing companion focus signal; verify accepted-snapshot cases in `app_client_presence_rail.test.js` show zero actions/new frames, one left figure, no right duplicate, correct dim/z and preserved controlled props, including two companions, null art and same-name non-party controls.
- [x] 1.2 Preserve existing `CompanionLineup`/`StageActor` rendering and figure geometry; document the exploration emphasis and actual-membership exception in the existing `docs/development/frontend-vue-architecture.md` companion-lineup section and relevant shell/composable comments; verify focused `tests/core/companion_lineup.test.js` cases keep size/lift/ground-line/baseline z and controlled beat behavior unchanged.

## 2. Committed lifecycle and possession regressions (2.5h)

- [x] 2.1 Extend integrated focus tests for Escape/返回/look-close, movement, target departure after the existing submission lock permits settlement, absent target/panel, epoch reset and full/reduced/off final states; include locked/unavailable-presence departure followed by unlocked settlement, asserting immediate derived-emphasis removal, delayed card closure and one departure notice; keep current store card/focus restoration ownership and verify opener restoration and no movement-only departure message.
- [x] 2.2 Add actual-lineup controls for truncated raw party rows, unavailable party panel and string status identity; exercise possession/release and membership transfer in both directions while the target survives; remove any right-side transition-leaving duplicate during same-identity representation transfer; verify the controlled front retains baseline/dim/gesture semantics, the old slot loses emphasis, and DOM actor counts stay singular through full-motion transfer.
- [x] 2.3 Extend card-to-dialogue tests with one talk action, retained focus across intermediate exploration commits, failed talk with surviving target, accepted dialogue host then player speaking signals and non-party standee continuity; verify no premature cleanup or dialogue companion duplication and update lifecycle documentation/comments beside the existing owners without adding another focus state machine.

## 3. Existing renderer showcase coverage (1h)

- [x] 3.1 Extend synthetic AppShell exploration companion-focus stories and existing CompanionLineup speaker toggle to demonstrate card-open emphasis and baseline restoration; retain `DialogueCompanionSpeaks`, non-party presence and missing-art examples; verify story controls show selected lit/high-z versus listener dim while no geometry or new component-manifest convention is introduced, and comments distinguish rendering fixtures from real wire acceptance.

## 4. Integrated acceptance and handoff (3h)

- [x] 4.1 Extend the existing synthetic browser exploration navigation journey with committed companion/roster/status/possession data and admitted image media, reusing the portrait change's fixture when present; verify one focused managed method covers actual medallion/overflow opening, no dispatch/frame, single representation, dim/z, card restoration and talk handover. Register every new method in `.github/browser-shards.json` in the same commit; update `.github/evennia-shards.json` only if a non-browser module is added/moved.
- [x] 4.2 Use agent-browser with the live client at 1451×790 and 1920×1080 and existing Storybook to record selected companion brightness/z, no right duplicate and unchanged boxes/ground lines before/open/back, plus single representation through approved existing talk behavior; repeat final focus state at reduced/off, record no credentials or unapproved persistent writes and keep content-specific observations outside regression fixtures.
- [x] 4.3 Run affected Vitest files, one focused browser method after a normal frontend build, relevant showcase coverage, `openspec validate reuse-lineup-person-focus --strict` and `uv run --locked python -m tools.contract_gate`; obtain canonical traceability IDs at spec sync, verify both delta sets survive sequential integration and report exact exercised results without a full managed browser run or CI-only evidence verification.
