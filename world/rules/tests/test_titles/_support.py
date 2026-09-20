"""Synthetic title fixtures and seams shared by the `test_titles` slices.

Module-level fixtures, helpers, and bases moved verbatim from the
original flat module (not a collected test module).
"""

from tools.spec_traceability import covers_requirement
import ast
import contextlib
import functools
import inspect
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.titles import (
    FixedTitleDef,
    StarterEpithet,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.rules import titles as titles_module
from world.rules.titles import removal as titles_removal_module
from world.rules.action import (
    CommitFailed,
    PendingEffect,
    _EVENT_EFFECT_PLANNERS,
    _commit,
    ActionRequest,
)
from world.rules.cast_settlement import settle_out_of_combat_cast
from world.rules.clock import CLOCK_YAML, WorldClock, _EVENT_SOURCES
from world.rules.event_log import EventEntry, EventLog, render_plain_text
from world.rules.guild import register_adventurer
from world.rules.titles import (
    DECLINED_LOG_KEY,
    MAX_DECLINE_RECORDS,
    MAX_REMOVAL_RECORDS,
    MAX_TITLE_ENTRIES,
    PENDING_BALLOT_KEY,
    REMOVALS_LOG_KEY,
    TITLE_COLLECTION_KEY,
    TITLE_EQUIPPED_KEY,
    TitleBallotError,
    TitleBallotReason,
    TitleDataError,
    TitleEquipError,
    TitleRemovalError,
    TitleRemovalReason,
    accept_epithet,
    bank_epithet,
    bank_fixed,
    banked_epithets,
    banked_fixed_keys,
    compose_full_title,
    compose_title,
    decline_epithet_ballot,
    decline_records,
    declined_digest,
    equip_epithet,
    equip_fixed,
    epithet_removal_gate,
    fixed_display_name,
    grant_rank_title,
    grant_first_quest_epithet,
    nomination_cooldown_active,
    nomination_suppressed,
    owned_epithet_displays,
    persist_nomination_ballot,
    predicate_satisfied,
    read_pending_ballot,
    read_title_state,
    register_title_planner,
    remove_epithet,
    removal_digest,
    removal_records,
    safe_full_title,
    safe_pending_ballot,
    title_context_entries,
    title_event_effect_planner,
)
from world.rules.tests.test_cast_settlement import (
    _CastSettlementTestCase,
    _raising_stage,
)
from world.lore.guild import GuildRank
from world.tests.synthetic_data import make_title
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._knowledge_probes import basic_attack_key, live_fixed_title_registry, live_guild_rank_registry, live_registry

# --- synthetic title-cluster data (locally authored ladder + pair rows) ------
# The title scope carries four locally authored fixed-title rows whose
# predicates are the guild-rank pairing family, and the guild-rank scope
# carries the matching F/E ladder (plus two extra rows so no shipped-shape
# kit row dangles). Every pairing fact the suite asserts is authored here —
# a rework of the shipped seven-pair ladder cannot break this suite.
_LADDER = (
    ("F", "t_pair_first_hunt", "霧鱗・初獵", "合成公會考官"),
    ("E", "t_pair_woodland", "苔徑・巡林", "合成公會考官乙"),
    ("t_bronze", "t_pair_bronze_badge", "灰鱗・銅徽", "合成公會銅階考官"),
    ("t_silver", "t_pair_silver_badge", "霜鬃・銀環", "合成公會銀階考官"),
)


_PAIR_TITLES = {
    title_key: make_title(
        title_key,
        display_name_zh=f"合成稱號{rank}",
        predicate=TitlePredicate(
            family=TitlePredicateFamily.GUILD_RANK_REACHED, guild_rank=rank
        ),
    )
    for rank, title_key, _examiner, _examiner_title in _LADDER
}


# One counter-driven extra bankable row for multi-key bank/equip sequences.
_T_PROBE_KEY = "t_synth_probe"


_PROBE_TITLE = make_title(
    _T_PROBE_KEY,
    display_name_zh="探徑合成者",
    predicate=TitlePredicate(
        family=TitlePredicateFamily.COUNTER_THRESHOLD,
        counter="t_synthetic_probe_counter",
        threshold=1,
    ),
)


_PAIR_TITLES[_T_PROBE_KEY] = _PROBE_TITLE


# Rank letters are production ladder identifiers (never catalog tokens); the
# rows themselves are authored here, so the ladder content is fully local.
_PAIR_RANKS = {
    "F": GuildRank("F", 1, 50, 400, "合成 F 階委託。", "t_pair_first_hunt", "霧鱗・初獵", "合成公會考官"),
    "E": GuildRank("E", 2, 400, 4_000, "合成 E 階委託。", "t_pair_woodland", "苔徑・巡林", "合成公會考官乙"),
    "t_bronze": GuildRank("t_bronze", 3, 4_000, 40_000, "合成銅階委託。", "t_pair_bronze_badge", "灰鱗・銅徽", "合成公會銅階考官"),
    "t_silver": GuildRank("t_silver", 4, 40_000, 400_000, "合成銀階委託。", "t_pair_silver_badge", "霜鬃・銀環", "合成公會銀階考官"),
}


T_F_KEY = "t_pair_first_hunt"


T_E_KEY = "t_pair_woodland"


T_F_DISPLAY = _PAIR_TITLES[T_F_KEY].display_name_zh


T_E_DISPLAY = _PAIR_TITLES[T_E_KEY].display_name_zh


# The (patched) starter-epithet seam constant the guild claim path banks.
T_STARTER = StarterEpithet("苔徑新旅", "你在合成公會完成第一次任務回報。")


def _open_title_scope(test):
    """Pairing titles + the F/E ladder + the patched starter-epithet seam."""
    open_synthetic_scope(
        test,
        "titles",
        "guild_ranks",
        extra={"guild_ranks": _PAIR_RANKS, "titles": _PAIR_TITLES},
    )
    seam = patch("world.lore.titles.STARTER_EPITHET", T_STARTER)
    seam.start()
    test.addCleanup(seam.stop)


def _starter():
    """The CURRENT starter-epithet constant (synthetic inside the scope)."""
    return live_registry("world.lore.titles", "STARTER_EPITHET")


_FIXED = {"kind": "fixed", "key": T_F_KEY, "granted_tick": 3}


_EPITHET = {
    "kind": "epithet",
    "display": T_STARTER.display,
    "origin_quote": "你在苔徑分部的目送下踏入合成驛鎮。",
    "granted_tick": 4,
}


# A counter-driven row used only by tests: the shipped registry holds the
# seven guild pairings, so the injectable faces are exercised here instead.
_COUNTER_ROW_KEY = "t_watched_legend"


_COUNTER_ROW = FixedTitleDef(
    _COUNTER_ROW_KEY,
    "受矚者",
    TitleCategory.ROMANCE,
    "眾人的目光落在你身上，你已不再閃避。",
    "累積足夠的被觀看次數即可獲得。",
    TitlePredicate(
        family=TitlePredicateFamily.COUNTER_THRESHOLD, counter="watched_count", threshold=1
    ),
)


def _with_counter_row(func):
    """Run one test with the counter-driven row injected into the registry.

    The patch has to outlive the grant: composition resolves a banked key
    through the live registry, so an assertion made after the context closes
    would (correctly) see the key fallback rather than the display name.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # The published registry is an immutable proxy, so the seam replaces
        # the module attribute wholesale (merged with the scoped rows) for
        # the duration of the test.
        with _patched_fixed_registry(
            {**live_fixed_title_registry(), _COUNTER_ROW_KEY: _COUNTER_ROW}
        ):
            return func(self, *args, **kwargs)

    return wrapper


@contextlib.contextmanager
def _patched_fixed_registry(rows):
    """Replace the fixed-title registry for every submodule binding that reads it.

    After the titles package split, the planner scans the registry through its
    own module binding while ``bank_fixed``/``fixed_display_name`` resolve
    through the state binding, so one seam must patch both to outlive the
    grant (composition asserts made after the patch closes would correctly
    see the key fallback, not the display name).
    """
    with contextlib.ExitStack() as stack:
        for _module in ("world.rules.titles.planner", "world.rules.titles.state"):
            stack.enter_context(patch(f"{_module}.FIXED_TITLE_REGISTRY", rows))
        yield rows


def _event_log(*entries: EventEntry) -> EventLog:
    return EventLog(
        actor="tester",
        skill_key=basic_attack_key(),
        targets=("monster",),
        entries=entries,
        time_cost_seconds=1,
    )


def _defeated(tier: str, target_id: int = 7) -> EventEntry:
    return EventEntry(
        kind="target_defeated",
        actor="tester",
        target="monster",
        data={"target_id": target_id, "monster_tier": tier},
        text_template="{actor}擊敗{target}",
    )


_FIRST_KILL_ROW = FixedTitleDef(
    "t_first_high",
    "高階獵手",
    TitleCategory.COMBAT,
    "你把第一隻高階魔物留在身後。",
    "擊敗第一隻高階魔物即可獲得。",
    TitlePredicate(
        family=TitlePredicateFamily.FIRST_KILL_TIER, monster_tier="high"
    ),
)


_DAY = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]


def _ballot(*pairs):
    return [{"display": display, "basis": basis} for display, basis in pairs]


def get_world_clock_tick() -> int:
    from world.rules.clock import get_world_clock

    return get_world_clock().tick


class _Request:
    """Minimal action-request surrogate carrying only an actor."""

    def __init__(self, actor):
        self.actor = actor
