# Proposal

## Why

The approved possession decision allows party-scoped shop transactions through the controlled companion, using the existing commander authority and purse. Adapter refusals and the services-panel guard currently prevent that behavior and make `party-management-acceptance` task 3.1 impossible to exercise as written.

## What Changes

- **BREAKING (pre-release)** Replace the possessed shop refusal with normal text `buy`/`sell` and web `shop.buy`/`shop.sell` settlement. Keep named-member bags, commander purse and merchant affinity, configured prices, and all existing trade gates unchanged.
- Make text `inventory` report the same party purse while preserving the caller's bag rows and existing breakdown header.
- While possessed, omit guild service content and navigation entirely; resolve the merchant normally and publish its host and shop. Keep the owner-keyed player summary. Combat still nulls every remote service surface.
- Preserve refusal of every other NPC service, including guild register/board/quests/turnin/merit and exam; church join/pray/offer/redeem/merit; scripted and freeform talk; combat engage; and quest-issuer commissions. Add no possession-aware routing to those services.
- Amend all contradictory active contracts, both player command documents and their drift manifest, and all four possession-refusal restatements in the party-management design (§3.2, §4.3, §4.9, §13). Convert old refusal tests to successful trades while preserving ordinary rejection coverage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shop-economy`: replace possession refusal with normal party-authorized transactions and truthful text purse reporting.
- `webclient-shop-window`: replace the unsatisfiable possession-refusal scenario with unchanged rows and successful normal trades.
- `webclient-possession-presentation`: remove shop actions from the refusal list; omit the possessed guild surface; retain talk/engage zero-write refusals.
- `exploration-affordances`: enable the normal merchant opener, omit the guild opener while possessed, and preserve disabled engage/talk entries.
- `webclient-service-menus`: specify the possession-only guild omission with merchant host/shop, owner summary, and unchanged combat suppression.

## Impact

Changes concentrate in `commands/economy.py`, `web/webclient/actions/service_actions.py`, `web/webclient/presentation/affordances.py`, and `world/rules/service_view.py`, plus their existing regressions and shop UI fixtures. Retire unused `possessed_shop` constants/messages and misleading current examples, without changing transaction rules or payload schemas. No migrations, compatibility layer, new possession state, console verb, or other service delegation is needed. This is one engineer-day of implementation and focused regression/documentation work.

## Batch:

No prerequisite active change; required party authority, possession follow, and shop presentation already exist on master.

```text
depends-on: none
```

Declared order: implement and land `possession-shop-access` first; then resume `party-management-acceptance` task 3.1 on its existing branch. The acceptance change is a consumer, never a prerequisite, and its artifacts/worktree are untouched by this proposal.

| Change | Depends on | Code-conflict notes | Queue order |
|---|---|---|---|
| `possession-shop-access` | none | Owns trade adapters, services/affordances, command docs and their regressions; no concurrent edits to these seams | 1 |
| `party-management-acceptance` (existing consumer) | `possession-shop-access` lands | Semantic/evidence conflict in possessed-shop acceptance; any shared browser journey edits must be reconciled after landing | 2, resume task 3.1 |
