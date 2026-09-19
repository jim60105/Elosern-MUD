"""Deterministic d100 combat built on the shared action resolver.

The package splits the single-writer combat core into cohesive modules:

- :mod:`world.rules.combat.battlefield` — the shipped ``combat.yaml``,
  the roster (``Battlefield``/``BattlefieldActionContext``), the bounded
  ``BattleResult``, the stored-hp/effective-stat readers, and the
  initiative/terminal predicates.
- :mod:`world.rules.combat.damage` — the ``damage`` effect handler: d100 hit
  resolution, damage-policy strikes, divert planning, and hp-delta staging.
- :mod:`world.rules.combat.healing` — the ``heal``/``self_heal`` effect
  handlers and their commit-time-alive, no-revival clamping.
- :mod:`world.rules.combat.rounds` — the default monster attack policy, the
  in-round order fold, end-of-round upkeep, ``run_round``, and ``run_battle``.

Everything the historical ``world.rules.combat`` module exposed is
re-exported here, and importing the package registers the combat-owned
effect handlers exactly as the old module did.
"""

from world.rules.combat.battlefield import (  # noqa: F401
    COMBAT_YAML,
    ActionProvider,
    Battlefield,
    BattlefieldActionContext,
    BattleResult,
    RoundRequest,
    _MAX_ACTIONS_PER_TURN,
    _adjusted_attack,
    _adjusted_defense,
    _max_hp,
    _stored_hp,
    effective_power,
    is_battle_over,
    roll_initiative,
)
from world.rules.combat.damage import (  # noqa: F401
    _apply_hp_delta,
    _apply_hp_delta_nonlethal,
    _extract_damage_policy,
    _extract_effect_coefficient,
    _handle_damage,
    _noop,
    _parse_damage_effect,
    _roll_multiplier,
    _to_hit,
)
from world.rules.combat.healing import (  # noqa: F401
    _apply_heal,
    _handle_heal,
    _handle_self_heal,
    _heal_magnitude,
    _parse_heal_effect,
    _parse_self_heal_effect,
    _restored_amount,
)
from world.rules.combat.rounds import (  # noqa: F401
    _action_skipped_event_log,
    _end_of_round_upkeep,
    _entity_round_order_op,
    _fold_round_order,
    default_attack_policy,
    run_battle,
    run_round,
)
#: Historical re-exports: the old flat module exposed these names for
#: consumers that route round requests and targeting relations through it.
from world.rules.items import ItemUseRequest  # noqa: F401
from world.rules.targeting import Relation  # noqa: F401
