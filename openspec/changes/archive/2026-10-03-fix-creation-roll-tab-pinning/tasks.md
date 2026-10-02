## 1. Extend the existing stage pin

- [x] 1.1 Wire the dispatch group's existing `rollPending` ref into `useCreationStage` from `use-creation-overlay.js`, preserving dispatch-before-stage construction and watcher registration order. Verify the stage group receives the same reactive ref used by the roll button, with no copied flag or new state owner.
- [x] 1.2 Extend the stage watcher pin condition in `use-creation-stage.js` to `conceptPending.value || rollPending.value`, retaining its `lastStage = value` write and the separate `latchedStage` branch; update comments to cover both request types. Verify unchanged-stage post-settlement publishes are value-gated and genuine later stage changes still mirror normally, without changing dispatch/backfill/settlement behavior.

## 2. Add the real-store regression

- [x] 2.1 Add a regression to `web/webclient-app/tests/overlays/creation_overlay.test.js` mirroring the real-store AppClient/fake-transport harness in `concept_fill_navigation.test.js`. Enter creation with no draft, pointer-click the custom tab without first editing fields, click `creation-roll-name` (`.creation-roll-button`), and verify exactly one admitted `creation.roll_name` dispatch, disabled roll button, and creation-surface `data-mode="custom"` after flushing the synchronous dispatch publish.
- [x] 2.2 Extend that regression with a matching-request success result carrying `data.display_name`; verify the name backfill lands and the creation surface stays `custom` after result settlement, shared gate release/button re-enable, and an additional unchanged-stage publish. Use deterministic store/DOM synchronization rather than sleeps; distinguish the surface's tab mode from the shared dock's `data-mode="creation"`.

## 3. Validate the focused fix

- [x] 3.1 Run `pnpm test` from the repo root after implementation; verify the new roll regression and existing concept-navigation, name-roll settlement, and creation keyboard coverage pass. Keep validation in the pnpm/dev-time JS suite; add no Evennia test module or `.github/evennia-shards.json` change.
- [x] 3.2 Run `openspec validate fix-creation-roll-tab-pinning --strict`; verify the proposal, design, delta requirement, and completed implementation tasks remain consistent. Confirm no backend/protocol/player-command change was introduced and leave command docs unchanged.
