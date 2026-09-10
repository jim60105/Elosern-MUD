"""Pure bounded codex read-model tests (title-codex-removal task 4.2).

Covers the TitleCodexView matrix: registry-order fixed rows carrying the
authored hint while locked and the flavor once unlocked (never both), the
unlocked/total counters over the full registry, newest-first epithet ordering
with the deterministic reverse-collection tie-break, the server-derived
``can_remove`` verdict (sole and equipped rows are never removable), every
clipping cap as a contiguous prefix, byte-identical re-reads, the row-count
clip with full-view counters, the degraded ballot tab, and the fail-closed
strict reads.

The suite runs on the synthetic kit: the fixed-title registry holds the kit's
two invented rows, the guild-rank registry carries one invented F-row paired
with the kit's first title, and the starter epithet is a file-local synthetic
constant — every expected key/display/hint is read from those live scoped
rows, so a shipped-content rework cannot break this read-model contract.
"""


from unittest.mock import patch

from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from world.lore.guild import GuildRank
from world.lore.titles import StarterEpithet
from world.rules import titles as titles_module
from world.rules.title_view import (
    TITLE_MAX_BASIS_CHARS,
    TITLE_MAX_DISPLAY_CHARS,
    TITLE_MAX_ROWS,
    TitleDataError,
    build_title_codex_view,
)
from world.rules.titles import (
    PENDING_BALLOT_KEY,
    TITLE_COLLECTION_KEY,
    TITLE_EQUIPPED_KEY,
    bank_epithet,
    bank_fixed,
    grant_first_quest_epithet,
    grant_rank_title,
)

from ._combat_session_helpers import open_synthetic_scope
from ._knowledge_probes import live_fixed_title_registry, live_registry

# The kit's synthetic fixed-title rows (scoped in for every test).
T_FIRST = "t_synth_first_hunt"
T_LODGING = "t_synth_lodging_friend"

# One invented rank row paired with the kit's first title. The letter is a
# production rank-ladder identifier (never a catalog token); everything the
# view reads is authored here.
T_RANK_F = GuildRank(
    "F", 1, 10, 100, "Synthetic F-rank tasks.", T_FIRST, "霧鱗・灰秤", "合成公會考官"
)

# The starter epithet the (patched) guild-claim path banks.
T_STARTER = StarterEpithet("苔徑新旅", "你在合成公會完成第一次任務回報。")


def _starter():
    """The CURRENT starter epithet constant (synthetic inside a scope)."""
    return live_registry("world.lore.titles", "STARTER_EPITHET")


class TitleCodexViewTests(EvenniaTest):
    """The projection matrix over registry + state + ballot."""

    def setUp(self):
        # Scope before construction: title/rank identities resolve against kit
        # rows; the starter epithet seam is patched for the whole lifecycle.
        open_synthetic_scope(
            self, "titles", "guild_ranks", extra={"guild_ranks": {"F": T_RANK_F}}
        )
        starter = patch(  # noqa: F841 — held via addCleanup below
            "world.lore.titles.STARTER_EPITHET", T_STARTER
        )
        starter.start()
        self.addCleanup(starter.stop)
        super().setUp()
        self.character = create_object(
            typeclass="typeclasses.characters.PlayerCharacter",
            key="codex-view-holder",
        )

    def test_empty_character_renders_locked_registry_rows_and_zero_counters(self):
        registry = live_fixed_title_registry()
        view = build_title_codex_view(self.character)
        self.assertEqual(len(view.fixed_rows), len(registry))
        self.assertEqual(view.epithet_rows, ())
        self.assertEqual(view.unlocked, 0)
        self.assertEqual(view.total, len(registry))
        self.assertEqual(view.full_title, "")
        self.assertIsNone(view.equipped["fixed"])
        self.assertIsNone(view.equipped["epithet"])
        self.assertEqual(view.pending_ballot, ())
        for row in view.fixed_rows:
            self.assertFalse(row.unlocked)
            self.assertEqual(row.flavor, "")
            self.assertGreater(len(row.hint), 0)
            self.assertEqual(row.granted_tick, 0)

    @covers_requirement(
        "title-system::titlecodexview-is-a-pure-bounded-read-model-for-the-codex"
    )
    def test_locked_rows_show_hints_and_unlocked_rows_show_flavors_never_both(self):
        bank_fixed(self.character, T_FIRST, 100)
        view = build_title_codex_view(self.character)
        unlocked = [row for row in view.fixed_rows if row.unlocked]
        locked = [row for row in view.fixed_rows if not row.unlocked]
        self.assertEqual([row.key for row in unlocked], [T_FIRST])
        registry = live_fixed_title_registry()
        definition = registry[T_FIRST]
        row = unlocked[0]
        self.assertEqual(row.display, definition.display_name_zh)
        self.assertEqual(row.category, definition.category.value)
        self.assertEqual(row.flavor, definition.flavor_zh)
        self.assertEqual(row.hint, "")
        self.assertEqual(row.granted_tick, 100)
        self.assertEqual(view.unlocked, 1)
        self.assertEqual(view.total, len(registry))
        for other in locked:
            self.assertEqual(other.flavor, "")
            self.assertEqual(other.hint, registry[other.key].hint_zh)
        # Exclusivity holds in both directions on every row.
        for every in view.fixed_rows:
            self.assertFalse(every.hint and every.flavor)

    def test_fixed_rows_follow_registry_order(self):
        bank_fixed(self.character, T_FIRST, 100)
        view = build_title_codex_view(self.character)
        self.assertEqual(
            [row.key for row in view.fixed_rows],
            list(live_fixed_title_registry()),
        )

    def test_epithet_rows_are_newest_first_with_a_deterministic_tie_break(self):
        bank_epithet(self.character, "舊名", "舊事蹟。", 50)
        bank_epithet(self.character, "新名", "新事蹟。", 200)
        bank_epithet(self.character, "並列甲", "甲事蹟。", 120)
        bank_epithet(self.character, "並列乙", "乙事蹟。", 120)
        view = build_title_codex_view(self.character)
        # Strict ticks dominate; equal 120 ticks keep reverse bank order.
        self.assertEqual(
            [row.display for row in view.epithet_rows],
            ["新名", "並列乙", "並列甲", "舊名"],
        )
        self.assertEqual(
            [row.granted_tick for row in view.epithet_rows],
            [200, 120, 120, 50],
        )
        self.assertEqual(view.epithet_rows[0].basis, "新事蹟。")

    def test_can_remove_follows_the_server_gate_verdict(self):
        # Sole epithet (starter pair): never removable, and equipped.
        grant_rank_title(self.character, "F")
        grant_first_quest_epithet(self.character)
        view = build_title_codex_view(self.character)
        self.assertEqual(len(view.epithet_rows), 1)
        self.assertTrue(view.epithet_rows[0].equipped)
        self.assertFalse(view.epithet_rows[0].can_remove)
        # Second epithet: the multi-epithet gate opens, but the equipped row
        # STILL renders can_remove false (precedence-aware verdict).
        bank_epithet(self.character, "破城先鋒", "率先破門。", 200)
        view = build_title_codex_view(self.character)
        by_display = {row.display: row for row in view.epithet_rows}
        starter_display = _starter().display
        self.assertTrue(by_display["破城先鋒"].can_remove)
        self.assertFalse(by_display[starter_display].can_remove)
        self.assertTrue(by_display[starter_display].equipped)
        # Swapping moves the flag, never the rule.
        titles_module.equip_epithet(self.character, "破城先鋒")
        view = build_title_codex_view(self.character)
        by_display = {row.display: row for row in view.epithet_rows}
        self.assertFalse(by_display["破城先鋒"].can_remove)
        self.assertTrue(by_display[starter_display].can_remove)

    def test_full_title_and_equipped_dict_describe_the_live_composition(self):
        grant_rank_title(self.character, "F")
        grant_first_quest_epithet(self.character)
        view = build_title_codex_view(self.character)
        self.assertEqual(
            view.full_title, titles_module.compose_full_title(self.character)
        )
        # The starter pair auto-equips BOTH slots (D8): the composed full
        # title and the equipped dict must match the live state exactly.
        self.assertEqual(
            view.equipped,
            {"fixed": T_FIRST, "epithet": _starter().display},
        )

    @covers_requirement(
        "title-system::titlecodexview-is-a-pure-bounded-read-model-for-the-codex"
    )
    def test_clipping_is_a_contiguous_prefix_within_every_cap(self):
        long_quote = "援" * (TITLE_MAX_BASIS_CHARS + 40)
        bank_epithet(self.character, "破城先鋒", long_quote, 100)
        view = build_title_codex_view(
            self.character,
            max_rows=TITLE_MAX_ROWS,
            max_display_chars=5,
            max_basis_chars=TITLE_MAX_BASIS_CHARS,
        )
        row = view.epithet_rows[-1]
        self.assertEqual(row.display, "破城先鋒"[:5])
        self.assertEqual(row.basis, long_quote[:TITLE_MAX_BASIS_CHARS])
        # Caller-passed smaller caps clip too (pure, no floor surprises).
        tighter = build_title_codex_view(self.character, max_basis_chars=10)
        self.assertTrue(
            all(len(row.basis) <= 10 for row in tighter.epithet_rows)
        )

    def test_row_lists_clip_while_counters_stay_full_view(self):
        grant_rank_title(self.character, "F")
        grant_first_quest_epithet(self.character)
        for index in range(1, 6):
            bank_epithet(self.character, f"異名{index}", f"事蹟{index}。", 100 + index)
        view = build_title_codex_view(self.character, max_rows=3)
        self.assertEqual(len(view.epithet_rows), 3)
        # The three newest survive the clip; the newest-first order holds.
        self.assertEqual(
            [row.display for row in view.epithet_rows],
            ["異名5", "異名4", "異名3"],
        )
        # Counters/equipped still describe the FULL state (lineage precedent).
        self.assertEqual(view.unlocked, 1)
        self.assertEqual(view.total, len(live_fixed_title_registry()))

    def test_build_is_repeatable_and_byte_identical(self):
        grant_rank_title(self.character, "F")
        grant_first_quest_epithet(self.character)
        bank_fixed(self.character, T_FIRST, 100)
        first = build_title_codex_view(self.character)
        second = build_title_codex_view(self.character)
        self.assertEqual(first, second)

    def test_malformed_title_state_fails_closed(self):
        self.character.attributes.add(TITLE_COLLECTION_KEY, [{"kind": "nonsense"}])
        with self.assertRaises(TitleDataError):
            build_title_codex_view(self.character)

    def test_malformed_ballot_degrades_only_the_nomination_tab(self):
        bank_epithet(self.character, "破城先鋒", "率先破門。", 100)
        self.character.attributes.add(PENDING_BALLOT_KEY, "not-a-ballot")
        view = build_title_codex_view(self.character)
        self.assertEqual(view.pending_ballot, ())
        # The title rows survive the corrupt ballot untouched.
        self.assertEqual(view.epithet_rows[0].display, "破城先鋒")
        self.assertEqual(len(view.fixed_rows), len(live_fixed_title_registry()))

    def test_pending_ballot_projects_display_and_basis_only(self):
        self.character.attributes.add(
            PENDING_BALLOT_KEY,
            [
                {"display": "夜襲之人", "basis": "夜半三度出入敵陣。"},
                {"display": "不屈之壁", "basis": "重傷仍守住隘口。"},
            ],
        )
        view = build_title_codex_view(self.character)
        self.assertEqual(
            view.pending_ballot,
            (
                {"display": "夜襲之人", "basis": "夜半三度出入敵陣。"},
                {"display": "不屈之壁", "basis": "重傷仍守住隘口。"},
            ),
        )

    def test_display_cap_matches_the_epithet_storage_cap(self):
        # The rendered identifier never truncates below the storage cap, so a
        # matching banked display always round-trips intact.
        from world.rules.titles import MAX_EPITHET_DISPLAY_CODE_POINTS

        self.assertEqual(TITLE_MAX_DISPLAY_CHARS, MAX_EPITHET_DISPLAY_CODE_POINTS)

    def test_view_mutates_nothing(self):
        grant_rank_title(self.character, "F")
        grant_first_quest_epithet(self.character)
        before = (
            self.character.attributes.get(TITLE_COLLECTION_KEY),
            self.character.attributes.get(TITLE_EQUIPPED_KEY),
        )
        build_title_codex_view(self.character)
        after = (
            self.character.attributes.get(TITLE_COLLECTION_KEY),
            self.character.attributes.get(TITLE_EQUIPPED_KEY),
        )
        self.assertEqual(before[0], after[0])
        self.assertEqual(before[1], after[1])
