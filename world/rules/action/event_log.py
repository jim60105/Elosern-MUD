"""Event-log construction for a resolved action (step 7).

Maps staged ``PendingEffect`` descriptions to replayable ``EventEntry``
values, derives defeat/knock-out crossings over projected HP, and assembles
the final ``EventLog``.
"""

from typing import Any

from world.rules.event_log import EventEntry, EventLog
from world.skills.registry import SkillDef

from world.rules.action.contracts import (
    _entity_key,
    _event_context,
    ActionRequest,
    PendingEffect,
    RejectedAction,
    RejectReason,
)
from world.rules.action.gates import _stored_trait_value


_ENTRY_TEMPLATES = {
    "resource_spend": "{actor} 消耗了資源。",
    "self_return_clear": "{actor} 重整架勢，重返戰鬥位置。",
    "session_stamp": "{actor} 立下了殉者之誓。",
    "skill_granted": "{actor} 對 {target} 施展了「統御術」的部分效果。",
    "disguise_set": "{actor} 改變了 {target} 的偽裝狀態。",
    "disguise_lifted": "{actor} 解除了 {target} 的偽裝狀態。",
    "reveal_lifted": "{actor} 看穿了 {target} 的偽裝。",
    "reveal_noop": "{actor} 未能看穿 {target} 的偽裝。",
    "buff_applied": "{actor} 對 {target} 施加了狀態效果。",
    "grants_revoked": "{actor} 收回了 {target} 身上的一切授予。",
    "self_buff_applied": "{actor} 凝聚精神，狀態獲得提升。",
    "buffs_cleansed": "{actor} 淨化了 {target} 的異常狀態。",
    "equipment_immune": "{target} 的裝備抵銷了{actor} 施加的負面效果——{target} 對此免疫。",
    "sexual_transition": "{target} 的狀態發生了變化。",
    "sexual_resist": "{target} 面對 {actor} 的意圖，做出了自己的選擇。",
    "pleasure_gain": "{target} 的快感提升了。",
    "sexual_counter": "{target} 的性行為計數提升了。",
    "trait_delta": "{target} 的能力值發生了變化。",
    "roll": "{actor} 對 {target} 的攻擊擲出了 {data[raw_roll]}。",
    "damage": "{actor} 對 {target} 造成了 {data[amount]} 點傷害。",
    "heal": "{actor} 對 {target} 恢復了 {data[amount]} 點生命。",
    "self_heal": "{actor} 恢復了 {data[amount]} 點生命。",
    "target_defeated": "{actor} 擊敗了 {target}。",
    "target_knocked_out": "{actor} 擊倒了 {target}。",
    "disengage_attempt": "{actor} 嘗試脫離戰鬥。",
    "skill_practice": "{actor} 累積了技能熟練度。",
    "combat_kill_xp": "",
    "knocked_out_mark": "",
    "divine_pleasure_max": "{actor} 以神之律令，將 {target} 的快感推至頂點。",
    "divine_climax_extension": "{actor} 以神之律令，延續了 {target} 的絕頂。",
    "divine_drain": "{actor} 從 {target} 身上汲取了神域之力。",
    "divine_drain_actor": "",
    "divine_saturate_sensitivity": "{actor} 以神之律令，重塑了 {target} 的感官。",
    "divine_clamp_shame": "{actor} 以神之律令，剝奪了 {target} 的羞恥。",
    "divine_mark_submission": "{actor} 以神之律令，將 {target} 化為絕對從屬。",
    "divine_restore_purity": "{actor} 以神之律令，使 {target} 回歸純淨。",
    "pleasure_peak": "{actor} 使 {target} 的快感推至頂點。",
    "gauge_transfer": "{actor} 對 {target} 發動了量表轉移。",
    "gauge_transfer_actor": "",
    "damage_divert": "",
}


def _entries_from_effect(
    actor_key: str,
    effect: PendingEffect,
) -> tuple[EventEntry, ...]:
    parts = effect.description.split("|")
    if len(parts) < 2 or parts[0] not in _ENTRY_TEMPLATES:
        raise ValueError(f"malformed pending-effect description {effect.description!r}")
    kind, target, *values = parts
    if kind == "resource_spend":
        data = {
            "resource_key": values[0],
            "amount": int(values[1]),
        }
    elif kind == "skill_granted":
        data = {
            "skill_key": values[0],
            "scale": float(values[1]),
        }
    elif kind == "buff_applied":
        data = {"buff_key": values[0]}
    elif kind == "self_buff_applied":
        data = {"buff_key": values[0]}
    elif kind == "equipment_immune":
        if len(values) != 1:
            raise ValueError(
                f"malformed equipment_immune pending effect {effect.description!r}"
            )
        data = {"buff_key": values[0]}
    elif kind == "buffs_cleansed":
        if len(values) != 1:
            raise ValueError(
                f"malformed buffs_cleansed pending effect {effect.description!r}"
            )
        data = {"count": int(values[0])}
    elif kind == "sexual_transition":
        data = {"event": values[0]}
    elif kind == "pleasure_gain":
        if len(values) != 1:
            raise ValueError(
                f"malformed pleasure_gain pending effect {effect.description!r}"
            )
        data = {"amount": int(values[0])}
    elif kind == "sexual_counter":
        if len(values) != 1:
            raise ValueError(
                f"malformed sexual_counter pending effect {effect.description!r}"
            )
        data = {"counter": values[0]}
    elif kind == "sexual_resist":
        if len(values) != 3:
            raise ValueError(
                f"malformed sexual_resist pending effect {effect.description!r}"
            )
        data = {
            "resisted": bool(int(values[0])),
            "auto_comply": bool(int(values[1])),
            "roll": None if values[2] == "none" else int(values[2]),
        }
    elif kind == "damage":
        if len(values) != 3:
            raise ValueError(
                f"malformed damage pending effect {effect.description!r}"
            )
        raw_roll, hit_flag, amount = map(int, values)
        roll_entry = EventEntry(
            kind="roll",
            actor=actor_key,
            target=target,
            data={"raw_roll": raw_roll, "hit": bool(hit_flag)},
            text_template=_ENTRY_TEMPLATES["roll"],
        )
        if not hit_flag:
            return (roll_entry,)
        return (
            roll_entry,
            EventEntry(
                kind="damage",
                actor=actor_key,
                target=target,
                data={"amount": amount},
                text_template=_ENTRY_TEMPLATES["damage"],
            ),
        )
    elif kind == "disengage_attempt":
        if len(values) != 4:
            raise ValueError(
                f"malformed disengage pending effect {effect.description!r}"
            )
        success_flag, raw_roll, actor_agility, pursuer_agility = values
        data = {
            "success": bool(int(success_flag)),
            "roll": None if raw_roll == "none" else int(raw_roll),
            "actor_agility": float(actor_agility),
            "pursuer_agility": (
                None
                if pursuer_agility == "none"
                else float(pursuer_agility)
            ),
        }
    elif kind in ("heal", "self_heal"):
        if len(values) != 1:
            raise ValueError(
                f"malformed heal pending effect {effect.description!r}"
            )
        data = {"amount": int(values[0])}
    elif kind == "combat_kill_xp":
        return ()
    elif kind == "knocked_out_mark":
        return ()
    elif kind == "divine_drain_actor":
        # Internal actor-side drain effect: the resource gain is rolled back
        # with the cast, and the logged narration is the single target-side
        # divine_drain entry — an actor entry would misnarrate as the caster
        # draining themselves.
        return ()
    elif kind == "gauge_transfer_actor":
        return ()
    elif kind == "damage_divert":
        return ()
    elif kind == "gauge_transfer":
        data = {
            "gauge": values[0] if len(values) > 0 else "mp",
            "direction": values[1] if len(values) > 1 else "drain",
            "amount": int(values[2]) if len(values) > 2 else 0,
        }
    else:
        data = {}
    entry = EventEntry(
        kind=kind,
        actor=actor_key,
        target=target,
        data=data,
        text_template=_ENTRY_TEMPLATES[kind],
    )
    if kind != "resource_spend":
        return (entry,)
    return (
        entry,
        EventEntry(
            kind="trait_delta",
            actor=actor_key,
            target=target,
            data={
                "trait_key": data["resource_key"],
                "delta": -data["amount"],
            },
            text_template=_ENTRY_TEMPLATES["trait_delta"],
        ),
    )


def _defeated_entry(
    actor_key: str,
    entity: Any,
    amount: int,
    projected: dict[int, float],
    defeated_ids: set[int],
    nonlethal: bool = False,
    simulated: bool = False,
) -> EventEntry | None:
    """Emit one ``target_defeated`` or ``target_knocked_out`` crossing entry.

    Pending damage is applied in order over shared projected HP, so two damage
    effects against one target neither use stale HP nor duplicate the defeat.
    Under a nonlethal policy a positive-to-non-positive crossing emits a
    ``target_knocked_out`` identity instead of ``target_defeated``, giving
    kill-credit/quest/loot consumers no defeat entry to observe. A simulated
    battle (guild examination) keeps the ordinary lethal ``target_defeated``
    entry but tags it ``simulated``, so kill-credit consumers can skip the
    defeat without hiding that the HP really crossed zero
    (exam-simulated-battle-redesign D4).
    """
    if amount <= 0:
        return None
    trait = getattr(entity, "traits", None)
    hp = getattr(trait, "hp", None)
    if hp is None:
        return None
    dbref = getattr(entity, "pk", None)
    if dbref is None:
        return None
    identity = id(entity)
    current = projected.get(identity, _stored_trait_value(hp))
    projected[identity] = current - amount
    if not (current > 0 and projected[identity] <= 0):
        return None
    if dbref in defeated_ids:
        return None
    defeated_ids.add(dbref)
    kind = "target_knocked_out" if nonlethal else "target_defeated"
    data: dict[str, Any] = {"target_id": int(dbref)}
    if not nonlethal:
        data["monster_tier"] = getattr(entity, "threat_tier", None)
    if simulated:
        data["simulated"] = True
    return EventEntry(
        kind=kind,
        actor=actor_key,
        target=str(entity.key),
        data=data,
        text_template=(
            _ENTRY_TEMPLATES["target_knocked_out"]
            if nonlethal
            else _ENTRY_TEMPLATES["target_defeated"]
        ),
    )


def _step7_build_event_log(
    request: ActionRequest,
    skill: SkillDef,
    pending: list[PendingEffect],
) -> EventLog:
    try:
        entries: list[EventEntry] = []
        projected: dict[int, float] = {}
        defeated_ids: set[int] = set()
        event_context = _event_context(request)
        nonlethal = bool(event_context.get("nonlethal", False))
        nonlethal_keys = frozenset(event_context.get("nonlethal_keys", ()))
        simulated = bool(event_context.get("simulated", False))
        for effect in pending:
            entries.extend(
                _entries_from_effect(
                    _entity_key(request.actor),
                    effect,
                )
            )
            if effect.description.startswith("damage|"):
                parts = effect.description.split("|")
                amount = int(parts[4])
            elif effect.description.startswith("gauge_transfer|"):
                parts = effect.description.split("|")
                if len(parts) >= 5 and parts[2] == "hp" and parts[3] == "drain":
                    amount = int(parts[4])
                else:
                    continue
            else:
                continue
            defeated = _defeated_entry(
                _entity_key(request.actor),
                effect.entity,
                amount,
                projected,
                defeated_ids,
                nonlethal=nonlethal or str(effect.entity.key) in nonlethal_keys,
                simulated=simulated,
            )
            if defeated is not None:
                entries.append(defeated)
    except Exception as error:
        raise RejectedAction(
            RejectReason.EVENT_LOG_CONSTRUCTION_FAILED,
            str(error),
        ) from error
    return EventLog(
        actor=_entity_key(request.actor),
        skill_key=skill.key,
        targets=_logged_targets(pending),
        entries=tuple(entries),
        time_cost_seconds=0,
    )


def _logged_targets(pending: list[PendingEffect]) -> tuple[str, ...]:
    targets: list[str] = []
    for effect in pending:
        if effect.description.startswith(
            (
                "resource_spend|",
                "combat_kill_xp|",
                "knocked_out_mark|",
                "self_return_clear|",  # Design D4: actor clearing own marker must not appear as target
            )
        ):
            continue
        key = effect.description.split("|", 2)[1]
        if key not in targets:
            targets.append(key)
    return tuple(targets)
