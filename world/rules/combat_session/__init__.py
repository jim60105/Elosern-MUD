"""Persistent player combat-session orchestration (guild-economy D-6).

One JSON-safe ``CombatSessionRecord`` lives under
``PlayerCharacter.db.active_combat`` and stores participant dbrefs plus
fled/knockout identity and the accumulated round count -- never live objects.
``engage`` creates a session and waits for player input; each preflight-valid
player action drives exactly one ordinary round -- compression is reachable
only through ``submit_opening_action``, the sole sanctioned requester -- and
the accumulated round time settles exactly once at a terminal outcome through
``settle_combat_result``.

Package layers (dependency direction one-way, low to high):

- :mod:`~world.rules.combat_session.errors` -- error type and stable reasons
- :mod:`~world.rules.combat_session.records` -- record parse/serialize/read
- :mod:`~world.rules.combat_session.targeting` -- ``aN``/``eN`` token resolution
- :mod:`~world.rules.combat_session.battlefield` -- reconstruction + policy
- :mod:`~world.rules.combat_session.lifecycle` -- engage/persist/clear
- :mod:`~world.rules.combat_session.policies` -- round action providers
- :mod:`~world.rules.combat_session.snapshot` -- round rollback snapshots
- :mod:`~world.rules.combat_session.scans` -- post-round affinity scans
- :mod:`~world.rules.combat_session.settlement` -- terminal settlement/recovery
- :mod:`~world.rules.combat_session.rounds` -- submissions + round transaction
"""

from world.rules import combat as _combat
from world.rules import overwhelm as _overwhelm
from world.rules.action import (  # noqa: F401  (compat: the historical module namespace re-exported these resolver seams)
    ActionRequest,
    ActionResolver,
)
from world.rules.combat import (  # noqa: F401  (compat: the historical module namespace re-exported these round seams)
    Battlefield,
    BattlefieldActionContext,
    run_round,
)
from world.rules.combat_session.battlefield import (
    _context_for,
    _session_policy,
    reconstruct_battlefield,
)
from world.rules.combat_session.errors import (  # noqa: F401
    CombatSessionError,
    SessionReason,
)
from world.rules.combat_session.lifecycle import (  # noqa: F401
    _persist,
    clear_session,
    engage,
    engage_group,
)
from world.rules.combat_session.policies import (  # noqa: F401
    BASIC_ATTACK_KEY,
    _basic_attack_request,
    _enemy_policy,
    _overwhelm_provider,
    _round_provider,
)
from world.rules.combat_session.records import (  # noqa: F401
    CombatSessionRecord,
    from_storage,
    is_in_active_session,
    read_session,
    session_id_for,
    to_storage,
)
from world.rules.combat_session.rounds import (  # noqa: F401
    _current_tick,
    _knocked_out_ids,
    _preflight_skill_submission,
    _primary_opponent_id,
    _submit_request,
    submit_opening_action,
    submit_player_action,
    submit_player_item_use,
)
from world.rules.combat_session.scans import (  # noqa: F401
    _scan_friendly_fire,
    _scan_sexual_coercion,
)
from world.rules.combat_session.settlement import (  # noqa: F401
    _continue_or_settle,
    _delete_exam_opponent,
    _find_exam_opponent,
    _restore_exam_participants,
    _round_cap,
    _settle_with_restore,
    _team_living,
    _terminal_outcome,
    forfeit,
    restore_active_session,
    settle_session,
)
from world.rules.combat_session.snapshot import (  # noqa: F401
    _restore_round_touched,
    _snapshot_party_surfaces,
    _snapshot_round_touched,
)
from world.rules.combat_session.targeting import (  # noqa: F401
    parse_session_targets,
    resolve_target_token,
)
from world.rules.clock import (  # noqa: F401  (compat: the historical module namespace re-exported these clock seams)
    get_world_clock,
    settle_combat_result,
)
from world.rules.monster_behaviour import (  # noqa: F401  (compat: the historical module namespace re-exported this enemy-policy seam)
    monster_behaviour_policy,
)
from world.rules.overwhelm import (  # noqa: F401  (compat: the historical module namespace re-exported these overwhelm seams)
    classify_overwhelm,
    resolve_overwhelm,
)

# The historical combat_session module namespace re-exported the whole world
# combat and overwhelm modules (``combat.RoundRequest`` type references, the
# overwhelm verdict helpers), so attribute access keeps resolving them here.
combat = _combat
overwhelm = _overwhelm

__all__ = [
    "BASIC_ATTACK_KEY",
    "ActionRequest",
    "ActionResolver",
    "Battlefield",
    "BattlefieldActionContext",
    "CombatSessionError",
    "CombatSessionRecord",
    "SessionReason",
    "_basic_attack_request",
    "_context_for",
    "_continue_or_settle",
    "_current_tick",
    "_delete_exam_opponent",
    "_enemy_policy",
    "_find_exam_opponent",
    "_knocked_out_ids",
    "_overwhelm_provider",
    "_persist",
    "_preflight_skill_submission",
    "_primary_opponent_id",
    "_restore_exam_participants",
    "_restore_round_touched",
    "_round_cap",
    "_round_provider",
    "_scan_friendly_fire",
    "_scan_sexual_coercion",
    "_session_policy",
    "_settle_with_restore",
    "_snapshot_party_surfaces",
    "_snapshot_round_touched",
    "_submit_request",
    "_team_living",
    "_terminal_outcome",
    "classify_overwhelm",
    "clear_session",
    "combat",
    "engage",
    "engage_group",
    "forfeit",
    "from_storage",
    "get_world_clock",
    "is_in_active_session",
    "monster_behaviour_policy",
    "overwhelm",
    "parse_session_targets",
    "read_session",
    "reconstruct_battlefield",
    "resolve_overwhelm",
    "resolve_target_token",
    "restore_active_session",
    "run_round",
    "session_id_for",
    "settle_combat_result",
    "settle_session",
    "submit_opening_action",
    "submit_player_action",
    "submit_player_item_use",
    "to_storage",
]


def __getattr__(name: str):
    """Delegate the mutable token-cache read to its owning module.

    ``_TOKEN_RE`` lives in :mod:`world.rules.combat_session.targeting` and is
    a lazily populated module-level cache; a plain re-export would freeze the
    pre-population ``None``, so the historical
    ``world.rules.combat_session._TOKEN_RE`` read resolves live here.
    """
    if name == "_TOKEN_RE":
        from world.rules.combat_session import targeting as _targeting_module

        return _targeting_module._TOKEN_RE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
