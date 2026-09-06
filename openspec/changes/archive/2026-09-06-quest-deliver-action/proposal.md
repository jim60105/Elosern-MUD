# Proposal: quest-deliver-action

## Why

`quest-deliver-objective` made `DELIVER` work, but the only way to move an item from a player to an
NPC is the dialogue `take_item` intent — the model has to decide to take the parcel. The registered
exploration actions are `move`, `look`, `talk_scripted`, `talk_freeform`, `dialogue_leave`,
`party_invite`, `party_leave`, `engage`, `wait`, `possess`, `possess_release`; there is no give verb
and no `給` command anywhere in `commands/`.

That makes every delivery quest unfinishable with the LLM offline, violating the project's headline
invariant that the deterministic game stays fully playable when all generative services are down.
The player needs a deterministic way to hand something over.

## What Changes

- New OOB action `explore.deliver` with a bounded payload naming the recipient identity and the item
  key, validated by its own payload validator and dispatched through the existing action registry.
- New player command (`交付`) covering the same capability from the text surface, so the verb exists
  for telnet play too. It carries no alias: the natural `給` name is already owned by the localized
  general give (`commands/localized/general.py::CmdGive`, mounted in `CharacterCmdSet`), contrary to
  this proposal's earlier claim that no give verb existed. When the general give later grows a
  quest-delivery branch, the shared deterministic rule is already its seam.
- Both routes call one shared deterministic rule that reuses the existing `_transfer_items` primitive
  and therefore the delivery observer, so a hand-over advances the objective atomically with the item
  movement.
- Honest gating: the action is offered and accepted only for a co-located recipient the holder has an
  active `DELIVER` stage bound to, for an item the holder actually holds. Every rejection carries a
  stable reason code, and a rejected attempt changes nothing.
  Amended during implementation review: the earlier "record terminal" refusal is subsumed — the
  strict reader guarantees a terminal record carries no runtime bindings
  (`validate_record_runtime`), so a post-completion hand-over to the same recipient and item refuses
  with `no_active_delivery`, and no separate terminal branch can exist.
- The exploration affordance surface offers the delivery when one is available at the player's
  location, so the action is reachable by pointer as well as by keyboard and command line.
- `docs/game/commands.md` and `docs/game/command-reference.md` updated in this change, keeping
  `tests/test_command_docs.py` green.

## Capabilities

### New Capabilities

(None. The delivery capability contract is owned by `quest-delivery`; this change adds its player
surfaces, so the requirements belong in the existing capabilities below.)

### Modified Capabilities

- `quest-delivery`: gains the deterministic player-initiated hand-over requirements — the offline
  playability guarantee, the `explore.deliver` registration and payload contract, and the honest
  refusal rules. The action registration lives here rather than in `webclient-action-dispatch`,
  following the precedent set by `webclient-service-menus`, which added its own action IDs as
  requirements of the owning capability rather than restating the base enumeration.
- `exploration-affordances`: `ACTION_CODE_ALLOWLIST` is exhaustively enumerated in that capability,
  so admitting `explore.deliver` genuinely changes the requirement and needs a full MODIFIED delta.
- `game-command-docs`: the command surface gains the delivery verb.

## Impact

- `web/webclient/actions/registry.py` and `web/webclient/actions/exploration_actions.py`: the action
  id, payload validator, and adapter.
- `web/webclient/presentation/exploration.py`: the exploration panel schema version bumps 1 → 2 —
  exactly the `explore.deliver` action affordance carries a `params` field (the validator-normalized
  dispatch payload), because the dock cannot re-derive a bound quest payload from the target
  identity alone. The client panel validator mirrors the version and the conditional field.
- `web/webclient/presentation/affordances.py`: the delivery affordance.
- New command module or an addition to `commands/items.py`; `commands/default_cmdsets.py`
  registration.
- `docs/game/commands.md`, `docs/game/command-reference.md`, `tests/test_command_docs.py`.
- New shared rule in `world/rules/` calling `_transfer_items`; no new economy or inventory primitive.
