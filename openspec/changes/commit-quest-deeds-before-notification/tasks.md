# Tasks

## 1. Make completion planning pure

- [x] 1.1 Remove completion-observer dispatch from `fulfill_record_for` and migrate pure planners and their callers, verifying an inventory, delivery, arrival or action plan that predicts completion and is then discarded produces no observer call or nomination request.
- [x] 1.2 Add a regression that a purchase plan calculating its inventory replacement never notifies before the purchase transaction opens, verifying no request exists at that point.

## 2. Notify from the completion owner

- [x] 2.1 Build a frozen completion receipt from the authoritative pre-completion bindings and the actually satisfied objective, carrying it through the existing quest transition plan, verifying reach, delivery and escort completions keep their destination and relevant bound identities and roles.
- [x] 2.2 Dispatch completion observers only from the quest transition writer after the immutable completion fact is finalized, through an outer `on_commit` callback that supplies the canonical source identity and finalized envelope, verifying a first-ever purchase completion is admitted only after purchase and completion commit.
- [x] 2.3 Cover automatic chain and direct replacement callers, verifying each intermediate completion retains its own objective snapshot before bindings are cleared and only actually completed quests produce facts.
- [x] 2.4 Make unchanged terminal replacement and replayed completion notifications inert, verifying neither creates another event nor another attempt while an independent later wake or logout remains eligible.
- [x] 2.5 Update the quest/narrative technical documentation for the owner-notification contract and verify the documented flow matches the observer signatures.

## 3. Integration verification

- [x] 3.1 Inject a failure after the quest writer records completion evidence but before the outer purchase or action commit, verifying purchase effects, gameplay state and completion evidence roll back and no nomination begins.
- [x] 3.2 Run the real completion envelope into the nomination service, verifying it uses the supplied source identity rather than rebuilding one and that rendered context can cite the committed completion.
- [x] 3.3 Run the focused quest, economy and title test labels plus `uv run --locked python -m tools.contract_gate`, verifying existing quest outcomes and command behavior are unchanged.
