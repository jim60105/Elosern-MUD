## 1. Preparation (verify shipped state at the apply-time tip)

- [ ] 1.1 Re-confirm every contract this change widens against current source (codegraph/LSP): `run_round`'s bundle leg (`combat.py` ~907 `== 0` skip), the single `roll_initiative` call (~895) and the untouched `first_actor` docstring, `_merge_adjustments`' add/replace fold, `action_preview.py`'s `actions_per_turn == 0` pin, `buffs.load_buff_definitions`' marker-clause validation block, `state_reactions.validate_state_reaction_rules`' then-vocabulary recognition, and `schema.evaluate_condition`'s recognized-keys set — this change adds NO condition-engine key (chance rides `then`, never `when`).
- [ ] 1.2 Confirm the `.github/evennia-shards.json` current content before appending (wave siblings also append).

## 2. Buff-definition order clause (buff-handler-integration delta)

- [ ] 2.1 Add the `round_order` load clause beside `marker` in `load_buff_definitions` per design D2: closed operation vocabulary {advance_to_head, retreat_to_tail} inside a wrapper mapping, shape fail-closed naming the offending key; carry it on `BuffDefinition` as an optional field (the `marker` field's shape).
- [ ] 2.2 Confirm zero live `buffs.yaml` rows use the clause at this change's ship (inert grammar); lifecycle stays ordinary (no new apply/remove paths).

## 3. Round-loop consumption (combat-resolution deltas)

- [ ] 3.1 Widen `run_round`'s provisioning leg per design D1: the `== 0` skip stays first and verbatim; a positive/absent count provisions `min(count, _MAX_ACTIONS_PER_TURN=3)` slots at the same sequence position, re-checking the shipped liveness predicate (fled/KO/hp≤0) before each slot; item/action/notification legs unchanged per slot; document the round-stays-one-transaction invariant in the docstring. Every shipped bundle (`actions_per_turn ∈ {absent, 0}`) must resolve byte-identically — the golden fixed-seed tests are the tripwire.
- [ ] 3.2 Implement the order fold per design D2/D3: local snapshot list; before each not-yet-acted key's turn, read live `round_order` marker instances across the remaining tail (definitions via `BUFF_DEFINITIONS`, instances via the shipped active-instance read), collapse same-key ops last-declared-wins, relocate advance→head-of-tail / retreat→tail-end; already-acted or absent keys are silent no-ops; `roll_initiative` and `first_actor` untouched; ZERO element keys.
- [ ] 3.3 Implement the chance gate per design D4: chance-bearing `actions_per_turn: 0` rolls exactly one `roll_d100()` per gated combatant per round at the combatant's turn; ≤ chance → shipped `action_skipped` with `data {"chance", "roll"}`; > chance → normal action; absent chance = certain skip verbatim.
- [ ] 3.4 `combat_modifiers.py`: rule load validation for the narrow `chance` key — legal ONLY beside `actions_per_turn: 0`, integer 0-100, non-boolean, fail-closed naming the rule id; the rule's `chance` key passes through the unmodified shipped additive fold with NO consumer (the generic merge gains zero chance awareness); the decision reads `matched_combat_modifiers`' per-rule bundles only (certain-zero-dominates / else max chance, design D4); `evaluate_combat_modifiers` stays pure (no roll, no context key added to `schema.evaluate_condition`); `action_preview` untouched.
- [ ] 3.5 `state_reactions.py`: recognize `mark_order_op:<definition-key>` in `then` (load-validates the named definition exists AND carries `round_order`; mutually exclusive with `counter_damage`/`apply_buff_to_source` in one `then`); dispatch applies the named definition to the event source with the shipped `apply_buff_to_source` attribution/rollback semantics and zero sequence mutation.

## 4. Tests (synthetic rows only; zero data-catalog tests)

- [ ] 4.1 In-file: extend the round-loop test module's bundle-leg coverage — count=1 byte-identity (existing pins verbatim), count=2 provisions two slots in order, mid-round defeat/KO cuts the second slot with no event, the fuse clamps an over-provisioned bundle, chance-bearing zero skips/acts on fixed dice with the roll recorded, certain-zero (no chance) byte-identical.
- [ ] 4.2 New focused module (register in `.github/evennia-shards.json`): ordering fold (advance on not-yet-acted reorders the tail with every other relative order preserved; retreat pushes to tail; already-acted key is a no-op; next round re-rolls clean; relocation never changes action count), malformed `round_order` rows fail load closed, `mark_order_op` load/dispatch (source marked once, sourceless no-op, malformed rules fail closed), malformed chance rules fail load closed.
- [ ] 4.3 Run ONLY the touched modules (`world/rules/tests/…`, the new module) — no project-wide suite.

## 5. Census / hygiene

- [ ] 5.1 Grep census: zero `round_order`/`mark_order_op`/`chance` live rows in the shipped rulebooks at ship time; no element key entered generic code; `BLOCKING_BUFF_KEYS`, every shipped `actions_per_turn: 0` lock rule (paralysis/suffocation/water_bind/fear/climax plus the landed ice rungs), `roll_initiative`, `first_actor`, and `DamagePolicy` byte-unchanged (`git diff --stat` proof in the PR body).
- [ ] 5.2 `openspec validate turn-order-control --strict` green.
