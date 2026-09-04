# Tasks: webclient-align-05-party-hud

## 1. Store join + quickbar

- [x] 1.1 Expose committed `party.slots` and the combat-participant identity→token join in the
  Vue store (no new protocol surface; pure derivation from committed panels).
- [x] 1.2 New `PartyStrip.vue` per the draft `.comps` island: `同伴 N / 4` header; per-slot cell
  (initial-letter/gold avatar with portrait-catalog fallback, name, HP hairline bar, state row
  `hp/max bond` with joined `aN` prefix); dashed `+ 邀請` padding cells to four; empty party →
  four dashed cells; unavailable panel / creation mode → island absent; activation opens the
  drawer, dispatches nothing.

## 2. Party drawer

- [x] 2.1 New `PartyDrawer.vue` on the shared drawer shell: `N / 4` sub-count; compbig rows
  (avatar, name, 羈絆 stage line, HP bar + numerals, joined 參戰 token, 請其離隊 →
  `explore.party_leave` under the confirmation contract); 空位 row with the stage-name-word
  invite rule (no raw threshold number) and `邀請當前 NPC…` → `explore.party_invite`, enabled only
  with a committed invite-capable interact target; three verbatim 跟隨規則 lines; the draft's
  per-row 詳情 button intentionally dropped (no companion-status read model).
- [x] 2.2 Wire both in `AppClient.vue` under the shared visibility matrix and escape/return
  discipline (drawer returns to the quickbar).

## 3. Showcase lockstep

- [x] 3.1 `component-manifest.json`: add `PartyStrip`/`PartyDrawer` entries;
  `stories/Overlays/PartyStrip.stories.js` + `PartyDrawer.stories.js` with deterministic offline
  party payloads bound to the derived view shape (shared fixture helper).
- [x] 3.2 `tests/overlays/deferred_surfaces_absent.test.js`: remove the Party entry +
  `party-`/`companion-` prefixes and `/\bParty\b/`/`/\bCompanions?\b/` title patterns; trim the
  `DEFERRED_SURFACES` record to the three surviving entries; `npm run showcase-coverage` green.

## 4. Tests

- [x] 4.1 Vitest: quickbar mirrors committed slots (names/bars/numerals/stage, invite padding,
  token join by identity, no-token when not fighting, initial-letter fallback, unavailable hides
  island, activation opens drawer without dispatch); drawer rows, invite enabled/disabled
  preconditions, leave dispatch rides the confirmation flow, verbatim follow rules. Land
  `covers_requirement` literal IDs for the party quickbar/drawer IDs at the archive/sync commit
  (IDs unknown to the checker before sync; magic-xp P1 precedent).

## 5. Verification

- [x] 5.1 Focused Vitest suites + `tools.spec_traceability check`.
- [x] 5.2 Live container check 1600x900: quickbar cells match the draft geometry; 請其離隊
  confirm → row removal on commit; drawer invite row states the rule without numerals.
