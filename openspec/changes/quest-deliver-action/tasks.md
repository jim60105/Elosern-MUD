# Tasks: quest-deliver-action

## 1. Shared deterministic rule

- [ ] 1.1 New rule in `world/rules/` exposing one `deliver_quest_item(actor, recipient, item_key)`
  entry point that both player surfaces call. It resolves the actor's active `DELIVER` stage bound to
  that recipient, preflights co-location, the bound-recipient match, and the held quantity, then
  performs the hand-over through the existing `_transfer_items` primitive so the delivery observer
  advances the stage inside the same transaction.
- [ ] 1.2 Refusal branches with stable reason codes and safe Traditional Chinese messages: recipient
  not co-located, no active bound delivery stage for that recipient, item not held, record terminal.
  Every refusal returns before any write.
- [ ] 1.3 Emit the boundary event through the observability facade with `char`, `quest`, and the
  recipient in context.

## 2. Web client action

- [ ] 2.1 Add `explore.deliver` to `web/webclient/actions/exploration_actions.py` with a payload
  validator accepting exactly the integer recipient identity and the bounded item key, rejecting
  extra, missing, mistyped, and out-of-bound fields.
- [ ] 2.2 Register the action id, validator, and adapter in `web/webclient/actions/registry.py`. The
  adapter takes the actor from the authenticated session, re-resolves the recipient and the record,
  and trusts no client-supplied quest ID, stage, quantity, or reward.
- [ ] 2.3 Mirror the new action id in the client-side action allowlist so a stale client rejects
  rather than dispatches it.

## 3. Exploration affordance

- [ ] 3.1 Add `explore.deliver` to `ACTION_CODE_ALLOWLIST` in
  `web/webclient/presentation/affordances.py`.
- [ ] 3.2 Emit one entry per co-located bound recipient of an active delivery stage, with
  validator-normalized params naming the recipient identity and the item key: enabled when the item
  is held, otherwise disabled with the rule's stable reason code and message. Emit nothing when no
  active bound stage matches a co-located entity.
- [ ] 3.3 Confirm both consumers — the `exploration` panel presenter and the `context_actions`
  exploration presenter — enumerate the entry identically, per the shared-vocabulary requirement.

## 4. Player command

- [ ] 4.1 New command class (`交付`, alias `給`) parsing the recipient and item from the argument
  string, resolving the recipient by the ordinary local search, and calling the same shared rule.
  Register it in `commands/default_cmdsets.py`.
- [ ] 4.2 Refuse during an active combat session with the existing combat gate idiom.

## 5. Documentation

- [ ] 5.1 Add the canonical entry to `docs/game/command-reference.md`: key, aliases, syntax,
  availability context, and the Traditional Chinese description covering the bound-recipient rule and
  the no-op refusal.
- [ ] 5.2 Add the row to the appropriate category table in `docs/game/commands.md`.
- [ ] 5.3 Add the matching entry to the curated manifest in `tests/test_command_docs.py` and keep the
  drift contract test green.

## 6. Tests

- [ ] 6.1 Offline test: with every `LLM_PROFILES` entry configured to fail, a delivery completes end
  to end through the deterministic path.
- [ ] 6.2 Parity test: the same delivery through the action and through the command produces
  identical state changes and identical rejection reasons.
- [ ] 6.3 Payload tests: extra, missing, mistyped, and out-of-bound fields are rejected before the
  adapter; the adapter re-resolves rather than trusting client-supplied quest state.
- [ ] 6.4 Refusal tests, one per branch, each asserting both inventories and the quest log are
  byte-for-byte unchanged.
- [ ] 6.5 Affordance tests: enabled entry for a held item, disabled entry with a stable code for an
  unheld item, no entry with no active bound stage, and identical enumeration from both consumers.
- [ ] 6.6 Annotate with `covers_requirement` against the added `quest-delivery` and
  `game-command-docs` requirement IDs and the modified `exploration-affordances` requirement ID;
  update `.github/evennia-shards.json` for new integration modules.
- [ ] 6.7 Run the observability lint, the command-docs drift test, and the focused affordance,
  action-dispatch, and delivery test modules in the same batch.
