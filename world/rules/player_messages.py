"""Stable player-facing messages for action and combat-session outcomes.

Telnet commands and the WebClient combat adapters consume the same mapping so
rejection prose and terminal announcements never drift between transports. All
messages are safe, bounded Traditional Chinese strings ready for ordinary
escaped text output.
"""

from world.rules.action import RejectReason


_REJECTION_MESSAGES: dict[RejectReason, str] = {
    RejectReason.UNKNOWN_SKILL: "你不會使用這項技能。",
    RejectReason.SKILL_NOT_ACTIVE: "被動技能不能主動施展。",
    RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT: "這項技能無法在目前場合施展。",
    RejectReason.INSUFFICIENT_RESOURCE: "你的資源不足。",
    RejectReason.TARGET_SPEC_MISMATCH: "這項技能的目標形式不符合。",
    RejectReason.TARGET_NOT_PRESENT: "目標不在這裡。",
    RejectReason.TARGET_DEAD: "目標已失去行動能力。",
    RejectReason.TARGET_OUT_OF_RANGE: "目標超出範圍。",
    RejectReason.TARGET_FACTION_FORBIDDEN: "這項技能不能指定該目標。",
    RejectReason.NO_VALID_TARGETS_IN_AREA: "範圍內沒有有效的目標。",
    RejectReason.ACTION_FORBIDDEN: "你目前無法行動。",
    RejectReason.DIVINE_ARTS_FORBIDDEN: "只有擁有神性的種族才能施展這項技能。",
    RejectReason.SCALED_CAST_FORBIDDEN: "尚未掌握該屬性精髓，無法自由調整威力。",
    RejectReason.UNKNOWN_EFFECT_ID: "這項技能的效果無法發動。",
    RejectReason.EFFECT_RESOLUTION_FAILED: "這項技能的效果無法發動。",
    RejectReason.MISSING_EFFECT_CONTEXT: "目前的場合無法提供這項技能所需的情境。",
    RejectReason.RESOURCE_DEDUCTION_FAILED: "你的資源不足。",
    RejectReason.EVENT_LOG_CONSTRUCTION_FAILED: "這項行動無法完成。",
    RejectReason.TIME_COST_LOOKUP_FAILED: "這項行動無法完成。",
    RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE: "這項行動無法完成。",
    RejectReason.COMMIT_FAILED: "這項行動無法完成。",
}

_REJECTION_FALLBACK = "這項行動無法完成。"

# Stable combat-session rejection messages shared by command and adapter paths.
SESSION_REASON_MESSAGES: dict[str, str] = {
    "not_a_player": "這個角色不能參與戰鬥。",
    "already_in_combat": "你已經在戰鬥中了。",
    "no_active_session": "目前沒有進行中的戰鬥。",
    "not_hostile": "這個目標不是敵對魔物。",
    "not_present": "目標不在這裡。",
    "target_dead": "目標已經無法行動。",
    "room_missing": "戰鬥場合已不存在。",
    "moved": "你已離開戰鬥場合。",
    "missing_participant": "戰鬥成員已無法確認。",
    "duplicate_participant": "戰鬥成員重複。",
    "malformed_session": "戰鬥紀錄異常。",
    "invalid_recovery": "你已經無法行動，戰鬥結束了。",
    "unknown_session_id": "無法確認當前戰鬥。",
}

# Stable terminal outcome announcements shared by command and adapter paths.
TERMINAL_OUTCOME_MESSAGES: dict[str, str] = {
    "victory": "戰鬥結束，你取得了勝利。",
    "defeat": "你被擊敗了，倒地不起，許久之後才在原地醒轉。",
    "fled": "你脫離了戰鬥。",
    "exam_passed": "你通過了公會考核。",
    "exam_failed": "你未能通過公會考核。",
    "cap": "戰鬥超出了回合上限，回合結束。",
}

CONTINUE_COMBAT_MESSAGE = "繼續戰鬥。"


def rejection_message(reason: RejectReason, detail: str | None = None) -> str:
    """Return the stable safe player-facing message for one rejection reason.

    ``detail`` never changes the message; it is retained for structured callers
    that need the exact rejected resource or target key.
    """
    del detail
    return _REJECTION_MESSAGES.get(reason, _REJECTION_FALLBACK)


def session_reason_message(reason: str) -> str:
    """Return the stable safe player-facing message for a session rejection."""
    return SESSION_REASON_MESSAGES.get(reason, _REJECTION_FALLBACK)


def terminal_outcome_message(outcome: str) -> str:
    """Return the stable announcement for one terminal session outcome."""
    return TERMINAL_OUTCOME_MESSAGES.get(outcome, CONTINUE_COMBAT_MESSAGE)


# Stable defeat-aftermath EventLog templates (defeat-aftermath-core D-C6).
# Every new aftermath kind ships its zh-tw offline template line here and the
# rendered text flows through the ordinary EventLog path (Telnet and WebClient
# alike). ``defeat_settle`` renders the PG wake prose carried in its entry
# data; the prose itself lives in the rulebook's ``pg_lines`` section so the
# rulebook stays the single content source.
DEFEAT_AFTERMATH_TEMPLATES: dict[str, str] = {
    "defeat_settle": "{data[wake]}",
    "violator_depart": "{actor} 對倒地的你失去興趣，逕自離開了。",
    "weak_granted": "虛弱感籠罩全身——你暫時使不出全力。",
    "recovery_advance": "你昏迷了 {data[seconds]} 秒，意識回籠時四肢依然沉重——體力只恢復了一小部分。",
    # The violation-sequence kinds (defeat-aftermath-violation-sequence):
    # the tone anchor is embarrassed-flavor, light-adventure prose — the
    # negative weight lands on the degraded body state, never on suffering.
    "violation_attempt": "{actor} 撲了上來，把你壓在身下，熾熱的鼻息就落在頸邊——牠還沒有滿足。",
    "violation_resisted": "你拚死扭動，總算掙開了 {actor} 的侵犯——牠不滿地低吼，動作收斂了許多。",
    "violation_act": "{actor} 得逞了。你的身體被肆意擺布，不聽話地發熱發顫，那種難為情的感覺揮之不去。",
    # Companion victims (defeat-aftermath-companion-victims): the same
    # light-adventure embarrassed tone observed from the player's side;
    # {target} names the companion the attempt actually targeted.
    "violation_attempt_companion": "{actor} 撲向了倒地的{target}，熾熱的鼻息就落在頸邊——牠還沒有滿足。",
    "violation_resisted_companion": "{target} 拚死扭動，總算掙開了 {actor} 的侵犯——牠不滿地低吼，動作收斂了許多。",
    "violation_act_companion": "{actor} 對{target}得逞了。她的身體被肆意擺布，不聽話地發熱發顫，那種難為情的感覺揮之不去。",
    # The knocked-out companion's own wake observation (a read of the
    # outcome, no new mutation): one line per selected companion victim.
    "companion_wake": "{actor} 也悠悠轉醒——她狼狽地撐起身子，拍了拍凌亂的衣擺，紅著臉別開了視線。",
}


def defeat_aftermath_template(kind: str) -> str:
    """Return the stable offline template for one aftermath EventLog kind."""
    return DEFEAT_AFTERMATH_TEMPLATES[kind]
