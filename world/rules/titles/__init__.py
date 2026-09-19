"""Deterministic title storage, composition, equip surface, and grants.

Two kinds of titles live on a character: fixed titles (registry-driven,
append-only) and epithets (banked entries, adopted by the nomination system;
``db.title_collection`` holds entries identified by ``(kind, key | display)``;
``db.title_equipped`` holds the two slot identifiers. Every reader and mutator
passes through the single strict ``read_title_state`` parser: missing
attributes read as the defaults, present-but-malformed state raises
``TitleDataError`` (fail closed), and the D8 slot-non-empty invariant is
asserted on every read.

The only delete path in the title surface is ``remove_epithet`` — the
two-gated, two-step epithet removal (change H, title-system D5 §8). It deletes
exactly one epithet collection entry, never a fixed entry and never an
equipped-identifier list, and leaves the equipment slots byte-identical; the
D8 invariant stays structurally unbreakable. Fixed titles have no removal
path, and no module-level callable other than ``remove_epithet`` deletes a
title entry (the structural-absence boundary test guards this).

The event-effect planner (``title_event_effect_planner``) evaluates the
registry's pending predicates against a committed action's ``EventLog`` and
persistent reads, staging fixed-title grants into the triggering action's own
transaction; guild rank grants ride their rank-change transactions instead
(``register_adventurer`` / ``settle_exam_outcome``). The package never writes
outside a caller's transaction.

The split:

- :mod:`world.rules.titles.state` — storage keys, wire caps, the strict
  parser, and the bank/equip/compose/context-entry surface.
- :mod:`world.rules.titles.planner` — the no-create predicate reads,
  ``predicate_satisfied``, ``title_event_effect_planner``, and the guild
  grant writers.
- :mod:`world.rules.titles.ballot` — the epithet nomination ballot reads and
  the three rules-layer ballot writers (D4, change G).
- :mod:`world.rules.titles.removal` — the two-gated epithet removal face
  (D5 §8, change H) — the ONLY delete path.

Everything the historical ``world.rules.titles`` module exposed is re-exported
here.
"""

from world.rules.titles.state import (  # noqa: F401
    BALLOT_BASIS_MAX_CHARS,
    DECLINED_LOG_KEY,
    MAX_BALLOT_CANDIDATES,
    MAX_DECLINE_RECORDS,
    MAX_EPITHET_DISPLAY_CODE_POINTS,
    MAX_FULL_TITLE_CODE_POINTS,
    MAX_REMOVAL_RECORDS,
    MAX_TITLE_ENTRIES,
    PENDING_BALLOT_KEY,
    REMOVALS_LOG_KEY,
    TITLE_COLLECTION_KEY,
    TITLE_EQUIPPED_KEY,
    TitleDataError,
    TitleEquipError,
    _DAY_SECONDS,
    _EPITHET_KIND,
    _FIXED_KIND,
    _FULL_WIDTH_SPACE,
    _LINEAGE_CROWN_CAP,
    _assert_slot_invariant,
    _optional_identifier,
    _parse_collection_entry,
    _require_identifier,
    _require_tick,
    _write_title_state,
    bank_epithet,
    bank_fixed,
    banked_epithets,
    banked_fixed_keys,
    compose_full_title,
    compose_title,
    equip_epithet,
    equip_fixed,
    fixed_display_name,
    read_title_state,
    safe_full_title,
    safe_title_context_entries,
    title_context_entries,
)
from world.rules.titles.planner import (  # noqa: F401
    _event_defeats_tier,
    _experience_type_members,
    _owned_skill_keys,
    _quest_completed,
    _sexual_counter_value,
    grant_first_quest_epithet,
    grant_rank_title,
    predicate_satisfied,
    register_title_planner,
    title_event_effect_planner,
)
from world.rules.titles.ballot import (  # noqa: F401
    TitleBallotError,
    TitleBallotReason,
    _parse_ballot_entry,
    accept_epithet,
    decline_epithet_ballot,
    decline_records,
    declined_digest,
    nomination_cooldown_active,
    nomination_suppressed,
    owned_epithet_displays,
    persist_nomination_ballot,
    read_pending_ballot,
    safe_pending_ballot,
)
from world.rules.titles.removal import (  # noqa: F401
    TitleRemovalError,
    TitleRemovalReason,
    epithet_removal_gate,
    removal_digest,
    removal_records,
    remove_epithet,
)
