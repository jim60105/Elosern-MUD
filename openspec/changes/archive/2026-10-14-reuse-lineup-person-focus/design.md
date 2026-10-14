# Design

## Context

See `proposal.md` for motivation. In `AppClient.vue:114-132`, dialogue checks `hostAlreadyInLineup` using `companionLineupSlots`, while exploration returns an actor-right standee unconditionally. The `speaking-identity` prop is dialogue-host-only at lines 328-337. `CompanionLineup.vue` already gives a matching non-controlled companion z `COMPANION_LINEUP_MAX + 1` and removes its listener dim; the controlled figure uses the independent `dimmed` prop and alone receives beat gestures.

`companionFigures` uses up to four current party rows plus a controlled front figure. Possession exchanges the possessed row and roster player without moving other slots. Status identities are strings; party/interact identities are numbers. An unavailable party panel means no party rows, yet possession can still render a front placeholder with the status identity. Actual lineup membership therefore differs from raw `party.slots` membership. The lineup is decorative and each figure has equal scale 1, lift 0 and geometry-derived baseline z.

`use-person-focus.js` derives the target from the committed interact list. The store's `settlePresence` closes on movement/mode change and departure, while preserving the card across in-flight/intermediate exploration commits. Opening/back is local; talk submits once and the card holds until its dialogue commit. Keep that lifecycle owner. The engine design's single-writer boundary excludes gameplay mutations from display focus.

## Goals / Non-Goals

**Goals:** represent each selected identity once and reuse current companion emphasis without moving any figure or changing who is controlled.

**Non-Goals:** protocol/art changes, a new focus store, delayed imperative z cleanup, a second renderer, altered dialogue/control semantics, new input bindings or geometry/CSS redesign. Existing keyboard/pointer activation and ChoiceCard focus trap remain authoritative; no gamepad surface is added to this desktop-only scoped fix.

## Decisions

### D1. Join actual committed rendered figures

Use the bounded `companionLineupSlots` used by `CompanionLineup`, restricted to its displayed maximum, for both dialogue and exploration membership checks. Compare `String(identity)` using the existing wire-identity convention, with explicit null guards. Join by identity even if portraits are null and names collide. Raw party rows fail under possession, truncated rows or an unavailable party panel; joining by image ref fails for missing imagery. Do not fabricate party membership or mutate `status.actor` to focus.

Derive a focused-lineup slot from exploration mode, an open verbs card and a surviving committed `focusTarget`. Actor-right is null when this identity is actually represented in the lineup; otherwise retain the existing non-party standee and identity key. Re-evaluate on every committed party/status/roster/possession change. If a target remains present but leaves the rendered lineup, its card remains open, the old companion's emphasis clears and it becomes the normal non-party actor-right target in that commit. If it enters the lineup, remove actor-right and emphasize the existing figure. There must be no overlapping transition-leaving duplicate when membership changes; suppress the old right-side leave phase for this representation transfer, while preserving ordinary non-party entrance/exit behavior.

### D2. Feed exploration emphasis through the existing companion signal

Derive one shell-local emphasis identity. In dialogue, keep the current committed host-speaker branch. In exploration, use the selected non-controlled rendered slot's actual identity as the `speakingIdentity` prop value, retaining its native numeric party identity. This avoids passing a string to a Number prop and the existing strict comparison. No other mode supplies exploration emphasis. The controlled slot is never treated as a non-controlled speaking companion; if an incoming local card refers to it, suppress duplication but leave its baseline z, independent dim and beat behavior unchanged.

Keep `dimmed` controlled by existing dialogue host/player logic, so selecting a companion lights/elevates that companion and leaves the controlled figure's current exploration behavior intact. Other non-controlled figures retain listener dim and baseline z. `StageActor` and `CompanionLineup` already implement these values. No new focus class, z token, animation timer or CSS filter convention is required. Geometry stays byte-equivalent for the same committed lineup before/after card focus. Ordinary dialogue compaction at a mode change remains permitted by its existing contract.

### D3. Derived state clears on the current lifecycle

| Event | Representation and emphasis |
| --- | --- |
| Card opens from rail/overflow | Selected rendered non-controlled figure lit/elevated, no actor-right, no packet/frame |
| Escape/返回 or successful 查看 close | Restore baseline z/dim for current lineup; existing opener restoration |
| Focused interact identity removed | No stale target or emphasis; existing card/departure notice settlement runs once submission lock releases |
| Committed room changes | Card and exploration emphasis clear; no departure claim solely for movement |
| Party unavailable or rendered membership changes | Recompute from actual slots, transfer to actor-right only if target survives as non-lineup; never retain an old selected slot |
| Possession/release swap | Derive again from current slots; controlled front retains its baseline/beat semantics; selected remaining companion may stay emphasized |
| Talk in flight or intermediate exploration commit | Keep card/focus while its target and lineup survive; do not clear on dispatch |
| Accepted dialogue commit | Clear exploration-only emphasis in the same commit; retain one left companion and apply existing host/player dialogue speaking focus |
| Rejected talk while target survives | Keep current card/emphasis and display existing action feedback |
| Missing/unavailable exploration target, mode change, epoch reset | No exploration emphasis or stale right-side focus; preserve store lifecycle/focus restoration semantics |

The derived `focusTarget` becoming null suffices to remove emphasis even if degraded/in-flight store settlement temporarily retains the card. Do not bypass `settlePresence`'s submission lock to fabricate a departure during intermediate talk commits. Correctness under reduced/off motion follows from reactive state, with no delayed cleanup dependent on transition end.

### D4. Amend complete existing requirement blocks

The presence-rail requirement for client-local verb cards must describe the lineup exception and closing restoration. Its verb payload requirement must describe conditional dialogue continuity; its departure requirement must distinguish removing a temporary actor-right standee from restoring a surviving lineup's baseline. Its live two-viewport requirement must verify both representation paths. Keep all existing scenarios. Extend the contextual-HUD lineup requirement's speaking focus to exploration, preserving equal geometry, speaker/control behavior and possession specs unchanged.

The portrait proposal modifies the presence display requirement and adds non-party image behavior; this proposal modifies the anchor, closure, handover and live-proof requirements. Both full deltas must survive later sync. This slice neither depends on nor modifies schema versioning; valid fixtures must use the current branch's accepted schema.

## Acceptance and Evidence Plan

Integrated `app_client_presence_rail.test.js` must drive accepted snapshots and updates through `store.receive`, including party, roster, status, art and possession banner, then open the actual medallion or overflow row. Independently assert no sent focus action, unchanged router depth, one matching actor-left figure, zero actor-right figures, selected `data-speaking=true` and z above every baseline, listener dim, and preserved controlled props. Use at least two companions so wrong-slot emphasis fails. Include equal names with different identities, null art, non-party actor-right, truncated raw party rows, absent party panel and string status identity.

Exercise back/Escape/look-close, departure after the normal gate permits settlement, movement, membership transfer both ways, possession/release, failed talk, dialogue commit with host then player speaker, panel unavailability and epoch reset. Existing non-party StageActor handover identity must remain intact. Component tests pin selected and baseline z/dim; full/reduced/off cases pin final props and geometry, with no changed scale/lift/slot position.

Extend `stories/Core/AppShell.stories.js` with synthetic exploration companion focus and retain `DialogueCompanionSpeaks`. Existing `CompanionLineup.stories.js:CompanionSpeaks` already proves the renderer's dim/z branch; demonstrate both focus and restoration. Use existing browser navigation synthetic fixtures, extending them with committed party data and admitted real local media for integrated proof after the portrait proposal. Add exact new method ownership to `.github/browser-shards.json`; existing non-browser module ownership stays unchanged. Live agent-browser proof at 1451×790 and 1920×1080 compares boxes and ground lines before/open/back, verifies lit/z and no actor-right duplicate, then talks to a real eligible companion host and verifies dialogue single representation. Keep credentials out of artifacts and record no unapproved game writes.

## Risks / Trade-offs

- Raw party has more rows than stage can display -> actual rendered slots decide membership; a truncated companion remains actor-right when selected.
- String/number differences select no figure -> normalize only for the join and pass the matched slot's native identity into the existing prop.
- Possessed front mistaken for a listener -> inspect `isControlled` and leave its existing dim/z/gestures unchanged.
- Right-side transition residue during a lineup transfer -> bypass that leave phase only for the same identity transferring representation; test DOM counts through the transfer, including full motion.
- Lifecycle lock temporarily retains the card -> derive emphasis only while a committed target exists; preserve current submission settlement rather than adding another state machine.
- Shared tests/stories/manifests conflict -> integrate sequentially after `restore-exploration-portrait-refs`, preserving its portrait cases; full matrix and eight-hour budget are in `proposal.md`.

## Migration Plan

No saved-state migration or compatibility path. Deploy the normal rebuilt frontend bundle. Reconnect resets local focus and reconstructs the committed lineup. Operational rollback restores the frontend bundle and its code; no backend state needs repair. Planning only here.
