"""Behavior tests for delayed regional recovery and its merged chronology.

Every ecology row, composition, policy and site here is a file-local synthetic
seam injected into the owners' own bindings, and every individual is built by
the real construction owner from the synthetic species/variant catalogs, so no
shipped density, timing, count or prose value is named or pinned. The real map
world is published because the owners read the shared placement surface and a
zone's parent region.

The assertions establish mechansims with independently known outcomes: which
occurrence tick a loss is accounted at, whether a due wave may create anything,
what a cancelled episode leaves behind, and how an equal elapsed interval
partitions. They never echo fixture content.
"""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.monsters import Monster
from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    MonsterSite,
    WeightedComposition,
    variant_species_key,
)
from world.maps import monster_sites, population_lifecycle, regional_population
from world.maps.population_lifecycle import settle_population_lifecycle
from world.maps.regional_population import (
    PopulationPresence,
    PopulationTransition,
    initialize_population_seed,
    initialize_zone,
    plan_population_wave,
    population_counts,
    presence_of,
    read_population_timeline,
    record_population_protection,
    record_population_transition,
    zone_state,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules import clock as clock_module
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.combat_session.rounds import _record_round_defeats
from world.rules.combat_session import engage, read_session
from world.rules.combat_session import submit_player_action
from world.rules.combat_session.settlement import (
    _ROUND_SECONDS,
    _record_terminal_population_protection,
)
from world.rules.tests._combat_session_helpers import (
    _player,
    complete_party_draft,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.rules.monster_individual import construct_species_individual
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import (
    SYNTH_SKILLS,
    SYNTH_MONSTER_TIERS,
    SYNTH_MONSTER_VARIANTS,
    synthetic_registries,
)

PROBE = (500, 700)
ORDINARY = next(iter(SYNTH_MONSTER_VARIANTS))
TIER = next(iter(SYNTH_MONSTER_TIERS))
SEED = 11
ZONE_KEY = "t_recovery_zone"
SITE_KEY = "t_recovery_site"

LOCAL = tuple((510 + offset, 700) for offset in range(4))

#: Four eligible cells at 75/99 individuals per hundred give the synthetic
#: zone an exact lower and upper bound of three.
LOWER_DENSITY = 75
UPPER_DENSITY = 99
DELAY = 10
REPLENISH = 5


def _solo_composition(key: str = "t_recovery_solo") -> EncounterComposition:
    """One complete one-member composition (a lawful wave of one)."""
    return EncounterComposition(key, (CompositionMember(ORDINARY, 1, 1),))


class RecoveryLifecycleTests(RegistryIsolationMixin, EvenniaTest):
    """Delayed episodes, chronological waves, and their protection."""

    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries("monster_species", "monster_variants", "monster_tiers")
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.region = region_for_coordinates(*PROBE)
        self.clock = get_world_clock()
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        population_lifecycle.register_regional_population()
        self.addCleanup(
            clock_module._EVENT_SOURCES.pop,
            population_lifecycle.STAGE_KIND,
            None,
        )
        self.compositions = {"t_recovery_solo": _solo_composition()}

    # -- seams --------------------------------------------------------------

    def _use_zone(
        self,
        *,
        wave_budget: int = 3,
        cell_capacity: int = 3,
        cells: tuple[tuple[int, int], ...] = LOCAL,
        site: MonsterSite | None = None,
        recovery_delay: int = DELAY,
    ) -> EcologyZone:
        zone = EcologyZone(
            ZONE_KEY,
            self.region,
            ((0, 0, 0, 0),),
            (WeightedComposition("t_recovery_solo", 1),),
            LOWER_DENSITY,
            UPPER_DENSITY,
            cell_capacity,
            recovery_delay=recovery_delay,
            replenishment_interval=REPLENISH,
            wave_budget=wave_budget,
        )
        self.enterContext(
            patch.object(
                regional_population,
                "ECOLOGY_ZONE_REGISTRY",
                MappingProxyType({zone.key: zone}),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType(dict(self.compositions)),
            )
        )
        self.enterContext(
            patch.object(
                monster_sites,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType(dict(self.compositions)),
            )
        )
        self.enterContext(
            patch.object(
                regional_population, "SETTLEMENT_BIRTH_POLICY_REGISTRY", MappingProxyType({})
            )
        )
        self.enterContext(
            patch.object(
                regional_population, "eligible_birth_cells", lambda *a, **k: tuple(cells)
            )
        )
        self.enterContext(
            patch.object(regional_population, "_region_cells", lambda zone: frozenset(cells))
        )
        self.enterContext(
            patch.object(
                monster_sites,
                "MONSTER_SITE_REGISTRY",
                MappingProxyType({} if site is None else {site.key: site}),
            )
        )
        return zone

    def _initialized(self, tick: int = 0) -> tuple[int, ...]:
        return initialize_zone(self.wilderness, ZONE_KEY, seed=SEED, tick=tick)

    def _kill(self, individual, tick: int) -> None:
        """Zero one living individual's HP and record its loss occurrence."""
        before = presence_of(self.wilderness, individual)
        individual.traits.hp.current = 0
        record_population_transition(
            self.wilderness,
            PopulationTransition(
                source_id=f"test-loss:{individual.pk}:{tick}",
                individual_id=int(individual.pk),
                occurred_tick=tick,
                before=before,
                after=presence_of(self.wilderness, individual, alive=False),
            ),
        )

    def _restore(self, individual, tick: int) -> None:
        """Restore one dead individual and record the lawful revival."""
        individual.traits.hp.current = individual.traits.hp.max
        record_population_transition(
            self.wilderness,
            PopulationTransition(
                source_id=f"test-restore:{individual.pk}:{tick}",
                individual_id=int(individual.pk),
                occurred_tick=tick,
                before=PopulationPresence(
                    alive=False,
                    position=None,
                    home_zone=individual.db.home_ecology_zone,
                    site_key=individual.db.site_key,
                ),
                after=presence_of(self.wilderness, individual, alive=True),
            ),
        )

    def _local(self, tick: int | None = None) -> frozenset[int]:
        return population_counts(self.wilderness, ZONE_KEY, at_tick=tick).local_ids

    def _individuals(self) -> tuple[Monster, ...]:
        return tuple(Monster.objects.all_family())

    def _advance_parts(self, parts: tuple[int, ...]) -> None:
        for seconds in parts:
            self.clock.advance(seconds, AdvanceSource.SKIP, [])

    # -- delayed episode ----------------------------------------------------

    @covers_requirement(
        "regional-population::deficits-recover-only-through-delayed-game-time-episodes"
    )
    def test_a_loss_only_schedules_one_delayed_due_and_never_births_early(self):
        self._use_zone(wave_budget=3)
        created = self._initialized(tick=100)
        self.assertEqual(len(created), 3)
        self.clock.tick = 100
        lost = Monster.objects.get(pk=created[0])
        self._kill(lost, 100)

        # Nothing about the loss itself births anything, and the episode keeps
        # its single due time across further passes.
        self.assertEqual(len(self._individuals()), 3)
        settle_population_lifecycle(100, 100)
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 110)
        self.assertEqual(len(self._individuals()), 3)

        # Before the due tick the deficit stays unresolved and untouched.
        settle_population_lifecycle(100, 109)
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 110)
        self.assertEqual(len(self._individuals()), 3)

        # At the due tick the living population is recomputed first; it is one
        # short, so exactly one complete wave restores the authored lower band.
        before_sequence = zone_state(self.wilderness, ZONE_KEY).generation_sequence
        settle_population_lifecycle(110, 110)
        state = zone_state(self.wilderness, ZONE_KEY)
        self.assertEqual(state.generation_sequence, before_sequence + 1)
        self.assertIsNone(state.recovery_due_tick)
        self.assertEqual(len(self._local()), 3)
        self.assertNotIn(lost.pk, self._local())

    @covers_requirement(
        "regional-population::deficits-recover-only-through-delayed-game-time-episodes"
    )
    def test_consecutive_waves_keep_the_budget_and_recover_eventually(self):
        self._use_zone(wave_budget=1)
        created = self._initialized(tick=100)
        self.clock.tick = 100
        for pk in created:
            self._kill(Monster.objects.get(pk=pk), 100)
        settle_population_lifecycle(100, 100)
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 110)

        baseline = zone_state(self.wilderness, ZONE_KEY).generation_sequence
        expected_counts = (1, 2, 3)
        expected_tick = 110
        for expected in expected_counts:
            with self.subTest(local=expected):
                events = settle_population_lifecycle(expected_tick, expected_tick)
                self.assertEqual(
                    [event.kind for event in events].count("monster_population_wave"), 1
                )
                self.assertEqual(len(self._local()), expected)
                state = zone_state(self.wilderness, ZONE_KEY)
                self.assertEqual(state.generation_sequence, baseline + expected)
                if expected < expected_counts[-1]:
                    self.assertEqual(
                        state.recovery_due_tick, expected_tick + REPLENISH
                    )
                    expected_tick += REPLENISH
                else:
                    self.assertIsNone(state.recovery_due_tick)
        # No wave ever created more individuals than the authored budget.
        self.assertEqual(len(self._local()), 3)

    @covers_requirement(
        "regional-population::deficits-recover-only-through-delayed-game-time-episodes"
    )
    def test_a_manual_restoration_cancels_without_a_birth_or_sequence_change(self):
        self._use_zone()
        created = self._initialized(tick=100)
        self.clock.tick = 100
        lost = Monster.objects.get(pk=created[0])
        self._kill(lost, 100)
        settle_population_lifecycle(100, 100)
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 110)
        sequence = zone_state(self.wilderness, ZONE_KEY).generation_sequence

        self.clock.tick = 105
        self._restore(lost, 105)
        settle_population_lifecycle(105, 105)
        self.assertIsNone(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick)

        events = settle_population_lifecycle(110, 110)
        self.assertEqual(events, [])
        self.assertEqual(
            zone_state(self.wilderness, ZONE_KEY).generation_sequence, sequence
        )
        self.assertEqual(len(self._individuals()), 3)

    @covers_requirement(
        "regional-population::deficits-recover-only-through-delayed-game-time-episodes"
    )
    def test_an_operator_hp_restoration_cancels_through_the_real_gm_route(self):
        from world.rules import gm

        self._use_zone()
        created = self._initialized(tick=100)
        self.clock.tick = 100
        target = f"#{created[0]}"
        gm.set_gauge(target, "hp", 0)
        settle_population_lifecycle(100, 100)
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 110)
        sequence = zone_state(self.wilderness, ZONE_KEY).generation_sequence

        self.clock.tick = 105
        restored = Monster.objects.get(pk=created[0])
        gm.set_gauge(target, "hp", int(restored.traits.hp.max))
        settle_population_lifecycle(105, 105)
        self.assertIsNone(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick)
        self.assertEqual(settle_population_lifecycle(110, 110), [])
        self.assertEqual(
            zone_state(self.wilderness, ZONE_KEY).generation_sequence, sequence
        )

    # -- occurrence timing --------------------------------------------------

    @covers_requirement(
        "regional-population::historical-population-evidence-preserves-removed-ownership-and-cell-protection"
    )
    @covers_requirement(
        "regional-population::loss-timing-and-encounter-protection-survive-deferred-combat-settlement"
    )
    def test_a_later_combat_occurrence_is_never_earlier_birth_headroom(self):
        self._use_zone()
        created = self._initialized(tick=100)
        self.clock.tick = 100
        doomed = Monster.objects.get(pk=created[0])
        self._kill(doomed, 118)

        # Projecting at 110 restores the still-future loss for accounting only.
        self.assertIn(doomed.pk, self._local(110))
        settle_population_lifecycle(110, 110)
        self.assertEqual(len(self._individuals()), 3)
        self.assertIsNone(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick)

        # The 118 boundary starts its own delayed episode; 120 is far too
        # early, and 128 is the earliest lawful due.
        settle_population_lifecycle(118, 118)
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 128)
        settle_population_lifecycle(120, 120)
        self.assertEqual(len(self._individuals()), 3)
        settle_population_lifecycle(128, 128)
        self.assertIsNone(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick)
        self.assertEqual(len(self._local()), 3)

    @covers_requirement(
        "regional-population::population-lifecycle-replays-loss-and-site-boundaries-chronologically"
    )
    def test_a_later_loss_after_a_restored_wave_starts_a_new_due(self):
        self._use_zone()
        created = self._initialized(tick=100)
        self.clock.tick = 100
        first = Monster.objects.get(pk=created[0])
        later = Monster.objects.get(pk=created[1])
        self._kill(first, 100)
        self._kill(later, 118)
        settle_population_lifecycle(100, 100)
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 110)

        # The 110 wave restores density while the 118 loss is still recorded
        # as future evidence.
        settle_population_lifecycle(110, 110)
        self.assertIsNone(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick)
        # At 110 the still-future 118 loss belongs to the living population, so
        # the wave restores the lower band without counting it as headroom.
        self.assertEqual(len(self._local(110)), 3)

        settle_population_lifecycle(118, 118)
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 128)
        settle_population_lifecycle(120, 120)
        self.assertEqual(len(self._local()), 2)
        settle_population_lifecycle(128, 128)
        self.assertIsNone(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick)
        self.assertEqual(len(self._local()), 3)

    # -- protection ---------------------------------------------------------

    @covers_requirement(
        "regional-population::loss-timing-and-encounter-protection-survive-deferred-combat-settlement"
    )
    @covers_requirement(
        "wilderness-monster-population::active-encounters-retain-protected-individuals-and-cells"
    )
    def test_a_protected_cell_blocks_the_due_wave_and_retries_next_interval(self):
        self._use_zone()
        created = self._initialized(tick=100)
        self.clock.tick = 100
        self._kill(Monster.objects.get(pk=created[0]), 100)
        for cell in LOCAL:
            record_population_protection(
                self.wilderness,
                engagement_id=f"t-fight:{cell[0]}",
                cell=cell,
                start_tick=100,
                end_tick=110,
            )
        settle_population_lifecycle(100, 100)
        sequence = zone_state(self.wilderness, ZONE_KEY).generation_sequence

        # The due endpoint is still protected: nothing is born, the sequence is
        # untouched, and the retry is one positive interval later.
        events = settle_population_lifecycle(110, 110)
        self.assertEqual(
            [event.kind for event in events], ["monster_population_recovery_blocked"]
        )
        state = zone_state(self.wilderness, ZONE_KEY)
        self.assertEqual(state.generation_sequence, sequence)
        self.assertEqual(state.recovery_due_tick, 110 + REPLENISH)
        self.assertEqual(len(self._individuals()), 3)

        # Passing the interval retires the closed protection and the next due
        # wave uses the cell lawfully.
        settle_population_lifecycle(115, 115)
        self.assertIsNone(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick)
        self.assertEqual(len(self._local()), 3)

    @covers_requirement(
        "regional-population::historical-population-evidence-preserves-removed-ownership-and-cell-protection"
    )
    @covers_requirement(
        "regional-population::loss-timing-and-encounter-protection-survive-deferred-combat-settlement"
    )
    @covers_requirement(
        "wilderness-monster-population::active-encounters-retain-protected-individuals-and-cells"
    )
    def test_a_terminal_mapped_session_protects_its_closed_interval(self):
        cell = LOCAL[0]
        monster = construct_species_individual(
            variant_species_key(ORDINARY), ORDINARY
        )
        self.wilderness.db.itemcoordinates[monster] = cell
        record = CombatSessionRecord(
            session_id="hostile:1:100",
            engagement_id="hostile:1:100:1",
            mode="hostile",
            room_id=1,
            player_ids=(self.char1.pk,),
            enemy_ids=(monster.pk,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=3,
            exam_id=None,
            started_tick=100,
            population_cell={
                "wilderness": WILDERNESS_NAME,
                "x": cell[0],
                "y": cell[1],
            },
        )
        _record_terminal_population_protection(record)
        protection = read_population_timeline(self.wilderness).protection
        self.assertEqual(len(protection), 1)
        self.assertEqual((protection[0].start_tick, protection[0].end_tick), (100, 118))

        self.assertIn(cell, regional_population._protected_cells(self.wilderness, at_tick=118))
        self.assertNotIn(
            cell, regional_population._protected_cells(self.wilderness, at_tick=119)
        )
        # A reload re-reads the same durable evidence: protection is not an
        # in-process cache.
        reloaded = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.assertIn(
            cell, regional_population.protected_cells(reloaded, at_tick=118)
        )

    # -- combat occurrence evidence ----------------------------------------

    @covers_requirement(
        "regional-population::loss-timing-and-encounter-protection-survive-deferred-combat-settlement"
    )
    def test_a_round_defeat_is_recorded_at_its_round_offset(self):
        cell = LOCAL[0]
        monster = construct_species_individual(
            variant_species_key(ORDINARY), ORDINARY
        )
        self.wilderness.db.itemcoordinates[monster] = cell
        monster.traits.hp.current = 0
        record = CombatSessionRecord(
            session_id="hostile:1:100",
            engagement_id="hostile:1:100:1",
            mode="hostile",
            room_id=1,
            player_ids=(self.char1.pk,),
            enemy_ids=(monster.pk,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=3,
            exam_id=None,
            started_tick=100,
            population_cell={
                "wilderness": WILDERNESS_NAME,
                "x": cell[0],
                "y": cell[1],
            },
        )
        battlefield = SimpleNamespace(roster={str(monster.pk): monster}, fled=set())

        _record_round_defeats(record, battlefield, {monster.pk: 5}, {monster.pk: 0}, 3)

        transitions = read_population_timeline(self.wilderness).transitions
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].occurred_tick, 100 + 3 * _ROUND_SECONDS)
        self.assertTrue(transitions[0].before.alive)
        self.assertFalse(transitions[0].after.alive)
        # Replaying the same committed round changes nothing.
        _record_round_defeats(record, battlefield, {monster.pk: 5}, {monster.pk: 0}, 3)
        self.assertEqual(len(read_population_timeline(self.wilderness).transitions), 1)

    # -- partition and site chronology --------------------------------------

    def _reset(self, zone: EcologyZone, tick: int) -> tuple[int, ...]:
        for individual in self._individuals():
            individual.delete()
        self.wilderness.db.itemcoordinates = {}
        self.wilderness.db.regional_population = {}
        self.wilderness.db.population_timeline = {
            "settled_through_tick": tick,
            "transitions": [],
            "protection": [],
        }
        self.clock.tick = tick
        return tuple(initialize_zone(self.wilderness, zone.key, seed=SEED, tick=tick))

    def _scenario_outcome(
        self,
    ) -> tuple[int, int | None, int, tuple[tuple[int, int], ...]]:
        state = zone_state(self.wilderness, ZONE_KEY)
        counts = population_counts(self.wilderness, ZONE_KEY)
        positions = tuple(
            sorted(
                regional_population.actual_cell(
                    self.wilderness, Monster.objects.get(pk=pk)
                )
                for pk in counts.local_ids
            )
        )
        return state.generation_sequence, state.recovery_due_tick, len(counts.local_ids), positions

    @covers_requirement(
        "regional-population::deficits-recover-only-through-delayed-game-time-episodes"
    )
    def test_equal_clock_advances_agree_under_any_partition(self):
        zone = self._use_zone(wave_budget=1)

        def run(parts: tuple[int, ...]):
            created = self._reset(zone, 100)
            baseline = zone_state(self.wilderness, ZONE_KEY).generation_sequence
            self._kill(Monster.objects.get(pk=created[0]), 100)
            self._kill(Monster.objects.get(pk=created[1]), 118)
            self._advance_parts(parts)
            return baseline, self._scenario_outcome()

        single = run((30,))
        halves = run((10, 20))
        steps = run((1, 29))
        self.assertEqual(single, halves)
        self.assertEqual(single, steps)
        # The outcome is a real recovered pair of waves, not an untouched state.
        baseline, outcome = single
        self.assertEqual(outcome[0], baseline + 2)
        self.assertEqual(outcome[2], 3)
        self.assertIsNone(outcome[1])

    def _use_site(
        self, *, cleared_at_tick: int = 100, recover_after_ticks: int = 40
    ) -> MonsterSite:
        site = MonsterSite(
            key=SITE_KEY,
            kind="camp",
            region_key=self.region,
            coordinates=LOCAL[0],
            composition_key="t_recovery_solo",
            capacity=1,
            one_shot=False,
            recover_after_ticks=recover_after_ticks,
        )
        self.wilderness.db.monster_sites = {
            SITE_KEY: {
                "state": "cleared",
                "cleared_at_tick": cleared_at_tick,
                "seed": 7,
                "generation_sequence": 0,
                "member_ids": [999999],
            }
        }
        return site

    @covers_requirement(
        "regional-population::population-lifecycle-replays-loss-and-site-boundaries-chronologically"
    )
    def test_a_later_site_recovery_never_consumes_the_earlier_wave(self):
        site = self._use_site()
        zone = self._use_zone(wave_budget=1, site=site)

        def run(parts: tuple[int, ...]):
            # Both runs start from the identical site baseline: the record is
            # part of the input, not leftover state from the previous run.
            self._use_site()
            created = self._reset(zone, 100)
            baseline = zone_state(self.wilderness, ZONE_KEY).generation_sequence
            self._kill(Monster.objects.get(pk=created[0]), 100)
            self._advance_parts(parts)
            site_state = monster_sites.site_state(SITE_KEY, wilderness=self.wilderness)
            return (
                baseline,
                self._scenario_outcome(),
                site_state.state,
                len(
                    [
                        individual
                        for individual in self._individuals()
                        if individual.db.site_key == SITE_KEY
                    ]
                ),
            )

        single = run((60,))
        split = run((25, 35))
        self.assertEqual(single, split)
        # The 110 wave happened before the 140 site recovery, and the 140
        # arrivals are not visible to it: the wave's plan used only the
        # headroom that existed at 110.
        baseline, outcome = single[0], single[1]
        self.assertEqual(outcome[0], baseline + 1)
        # The 110 wave restored the band (3) and the 140 site group joined it.
        self.assertEqual(outcome[2], 4)
        self.assertEqual(single[2], "populated")
        self.assertEqual(single[3], 1)

    @covers_requirement(
        "regional-population::population-lifecycle-replays-loss-and-site-boundaries-chronologically"
    )
    def test_a_same_tick_site_birth_cancels_the_pending_episode(self):
        site = self._use_site(cleared_at_tick=95, recover_after_ticks=25)
        zone = self._use_zone(
            wave_budget=1, recovery_delay=30, site=site
        )

        def run(parts: tuple[int, ...]):
            self._use_site(cleared_at_tick=95, recover_after_ticks=25)
            created = self._reset(zone, 100)
            baseline = zone_state(self.wilderness, ZONE_KEY).generation_sequence
            self._kill(Monster.objects.get(pk=created[0]), 100)
            # A later loss is recorded while the first episode is still
            # pending; the 120 site birth must cancel that episode first.
            self._kill(Monster.objects.get(pk=created[1]), 125)
            self._advance_parts(parts)
            state = zone_state(self.wilderness, ZONE_KEY)
            return (
                baseline,
                state.generation_sequence,
                state.recovery_due_tick,
                len(self._local()),
            )

        single = run((60,))
        split = run((21, 39))
        self.assertEqual(single, split)
        # One wave only: the 155 due from the 125 loss, not an early 130 wave.
        self.assertEqual(single[1], single[0] + 1)
        self.assertIsNone(single[2])
        self.assertEqual(single[3], 3)

    @covers_requirement(
        "regional-population::loss-timing-and-encounter-protection-survive-deferred-combat-settlement"
    )
    def test_a_protected_cell_defers_site_births_until_it_passes(self):
        site = self._use_site(cleared_at_tick=100, recover_after_ticks=10)
        self._use_zone(site=site)
        self._initialized(tick=100)
        self.clock.tick = 100
        record_population_protection(
            self.wilderness,
            engagement_id="t-site-fight",
            cell=LOCAL[0],
            start_tick=100,
            end_tick=110,
        )

        settle_population_lifecycle(100, 110)
        self.assertEqual(
            monster_sites.site_state(SITE_KEY, wilderness=self.wilderness).state,
            "cleared",
        )
        self.assertEqual(
            [
                individual
                for individual in self._individuals()
                if individual.db.site_key == SITE_KEY
            ],
            [],
        )
        settle_population_lifecycle(110, 111)
        self.assertEqual(
            monster_sites.site_state(SITE_KEY, wilderness=self.wilderness).state,
            "populated",
        )
        self.assertEqual(
            len(
                [
                    individual
                    for individual in self._individuals()
                    if individual.db.site_key == SITE_KEY
                ]
            ),
            1,
        )

    @covers_requirement(
        "regional-population::loss-timing-and-encounter-protection-survive-deferred-combat-settlement"
    )
    def test_a_lawful_clear_still_retains_the_closed_protection(self):
        from world.rules.combat_session.lifecycle import clear_session
        from world.rules.combat_session.records import to_storage

        cell = LOCAL[0]
        monster = construct_species_individual(
            variant_species_key(ORDINARY), ORDINARY
        )
        self.wilderness.db.itemcoordinates[monster] = cell
        record = CombatSessionRecord(
            session_id="hostile:1:100",
            engagement_id="hostile:1:100:1",
            mode="hostile",
            room_id=1,
            player_ids=(self.char1.pk,),
            enemy_ids=(monster.pk,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=3,
            exam_id=None,
            started_tick=100,
            population_cell={
                "wilderness": WILDERNESS_NAME,
                "x": cell[0],
                "y": cell[1],
            },
        )
        self.char1.db.active_combat = to_storage(record)

        # An operator/GM cleanup clears the session directly; the interval must
        # not disappear with the record.
        clear_session(self.char1, None, record)
        self.assertIsNone(self.char1.db.active_combat)
        protection = read_population_timeline(self.wilderness).protection
        self.assertEqual([(p.start_tick, p.end_tick) for p in protection], [(100, 118)])

    @covers_requirement(
        "regional-population::historical-population-evidence-preserves-removed-ownership-and-cell-protection"
    )
    def test_a_deferred_site_clear_keeps_the_loss_occurrence(self):
        from world.rules.combat_session.records import to_storage

        site = self._use_site(cleared_at_tick=0, recover_after_ticks=1000)
        self._use_zone(site=site)
        # The site has never been populated: its first settlement creates the
        # group whose loss this test follows.
        self.wilderness.db.monster_sites = {}
        self._initialized(tick=100)
        self.clock.tick = 100
        settle_population_lifecycle(100, 100)
        members = [
            individual
            for individual in self._individuals()
            if individual.db.site_key == SITE_KEY
        ]
        self.assertEqual(len(members), 1)
        member = members[0]
        self._kill(member, 106)
        # A persisted combat session still owns this defeat.
        record = CombatSessionRecord(
            session_id="hostile:1:100",
            engagement_id="hostile:1:100:1",
            mode="hostile",
            room_id=1,
            player_ids=(self.char1.pk,),
            enemy_ids=(member.pk,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=1,
            exam_id=None,
            started_tick=100,
            population_cell=None,
        )
        self.char1.db.active_combat = to_storage(record)

        settle_population_lifecycle(100, 110)
        self.assertEqual(
            monster_sites.site_state(SITE_KEY, wilderness=self.wilderness).state,
            "populated",
        )
        # The committed occurrence survives the deferred clear.
        self.assertTrue(read_population_timeline(self.wilderness).transitions)

        self.char1.db.active_combat = None
        settle_population_lifecycle(110, 120)
        cleared = monster_sites.site_state(SITE_KEY, wilderness=self.wilderness)
        self.assertEqual(cleared.state, "cleared")
        self.assertEqual(cleared.cleared_at_tick, 106)

    @covers_requirement(
        "regional-population::deficits-recover-only-through-delayed-game-time-episodes"
    )
    def test_the_pure_boundary_projects_an_unpersisted_episode(self):
        self._use_zone()
        created = self._initialized(tick=100)
        self.clock.tick = 100
        self._kill(Monster.objects.get(pk=created[0]), 100)
        self.assertIsNone(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick)
        self.assertEqual(
            population_lifecycle.next_population_lifecycle_boundary(100, 130), 110
        )

    @covers_requirement(
        "regional-population::historical-population-evidence-preserves-removed-ownership-and-cell-protection"
    )
    def test_incomplete_timeline_evidence_refuses(self):
        from world.maps.regional_population import MalformedPopulationState

        good = {
            "alive": True,
            "position": {"wilderness": WILDERNESS_NAME, "x": 1, "y": 2},
            "home_zone": None,
            "site_key": None,
        }
        self.wilderness.db.population_timeline = {
            "settled_through_tick": 0,
            "transitions": [
                {
                    "source_id": "s",
                    "individual_id": 1,
                    "occurred_tick": 5,
                    "before": {"alive": True},
                    "after": good,
                }
            ],
            "protection": [],
        }
        with self.assertRaises(MalformedPopulationState):
            read_population_timeline(self.wilderness)

        self.wilderness.db.population_timeline = {
            "settled_through_tick": 0,
            "transitions": [],
            "protection": [
                {
                    "engagement_id": "e",
                    "cell": {"wilderness": WILDERNESS_NAME, "x": 1, "y": 2},
                    "start_tick": 10,
                    "end_tick": 5,
                }
            ],
        }
        with self.assertRaises(MalformedPopulationState):
            read_population_timeline(self.wilderness)

    @covers_requirement(
        "regional-population::historical-population-evidence-preserves-removed-ownership-and-cell-protection"
    )
    def test_a_deleted_home_member_still_counts_before_its_loss(self):
        self._use_zone()
        first = construct_species_individual(
            variant_species_key(ORDINARY), ORDINARY
        )
        second = construct_species_individual(
            variant_species_key(ORDINARY), ORDINARY
        )
        for individual, cell in ((first, LOCAL[0]), (second, LOCAL[1])):
            individual.db.home_ecology_zone = ZONE_KEY
            self.wilderness.db.itemcoordinates[individual] = cell
        self.clock.tick = 100
        before = presence_of(self.wilderness, first)
        after = presence_of(self.wilderness, first, alive=False)
        first_pk = int(first.pk)
        self.assertNotEqual(first_pk, int(second.pk))
        record_population_transition(
            self.wilderness,
            PopulationTransition(
                source_id="deleted-home-member",
                individual_id=first_pk,
                occurred_tick=110,
                before=before,
                after=after,
            ),
        )
        first.delete()

        # Same variant (same label), distinct persistent identities, both home
        # owners; the deleted member still consumes headroom before its loss.
        early = population_counts(self.wilderness, ZONE_KEY, at_tick=100)
        self.assertEqual(len(early.local_ids), 2)
        self.assertIn(first_pk, early.home_ids)
        late = population_counts(self.wilderness, ZONE_KEY, at_tick=110)
        self.assertNotIn(first_pk, late.local_ids)
        self.assertEqual(len(late.local_ids), 1)
        self.assertEqual(len(self._individuals()), 1)

    @covers_requirement(
        "regional-population::deficits-recover-only-through-delayed-game-time-episodes"
    )
    def test_settlement_progress_agrees_under_partition(self):
        zone = self._use_zone()

        def run(parts: tuple[int, ...]) -> int:
            self._reset(zone, 100)
            self._advance_parts(parts)
            return read_population_timeline(self.wilderness).settled_through_tick

        self.assertEqual(run((60,)), run((25, 35)))
        self.assertEqual(run((60,)), 160)

    @covers_requirement(
        "regional-population::historical-population-evidence-preserves-removed-ownership-and-cell-protection"
    )
    def test_operator_spawn_and_delete_are_counted_presence_evidence(self):
        from world.maps import gm as map_gm

        self._use_zone()
        enter_wilderness(self.char1, coordinates=LOCAL[0], name=WILDERNESS_NAME)
        room = self.char1.location
        self.clock.tick = 100
        spawned = map_gm.spawn_monster(
            variant_species_key(ORDINARY), ORDINARY, f"#{room.pk}"
        )
        individual_id = int(spawned["target"].lstrip("#"))
        self.assertIn(
            individual_id, population_counts(self.wilderness, ZONE_KEY).local_ids
        )
        # A reload reads the same registration.
        reloaded = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.assertIn(
            individual_id, population_counts(reloaded, ZONE_KEY).local_ids
        )

        map_gm.delete_entity(f"#{individual_id}")
        self.assertNotIn(
            individual_id, population_counts(self.wilderness, ZONE_KEY).local_ids
        )
        losses = [
            transition
            for transition in read_population_timeline(self.wilderness).transitions
            if transition.individual_id == individual_id
            and not transition.after.alive
        ]
        self.assertEqual(len(losses), 1)
        self.assertTrue(losses[0].before.alive)
        self.assertFalse(losses[0].after.alive)

    @covers_requirement(
        "regional-population::historical-population-evidence-preserves-removed-ownership-and-cell-protection"
    )
    def test_an_operator_departure_keeps_home_ownership_and_schedules(self):
        from world.rules.movement_settlement import settle_relocation

        self._use_zone()
        self.assertTrue(
            enter_wilderness(self.char2, coordinates=PROBE, name=WILDERNESS_NAME)
        )
        destination = self.char2.location
        created = self._initialized(tick=100)
        self.clock.tick = 100
        settle_relocation(Monster.objects.get(pk=created[0]), destination)
        counts = population_counts(self.wilderness, ZONE_KEY)
        self.assertEqual(len(counts.local_ids), 2)
        self.assertEqual(len(counts.home_ids), 3)
        settle_population_lifecycle(100, 100)
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 110)

    # -- observation routes -------------------------------------------------

    @covers_requirement(
        "regional-population::deficits-recover-only-through-delayed-game-time-episodes"
    )
    def test_reads_re_entry_and_acceptance_never_birth(self):
        from world.quests.definitions import QuestStage
        from world.quests.tests._fixtures import accept, defeat, quest, register

        self._use_zone()
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        created = self._initialized(tick=100)
        self.clock.tick = 100
        self._kill(Monster.objects.get(pk=created[0]), 100)
        settle_population_lifecycle(100, 100)
        due = zone_state(self.wilderness, ZONE_KEY).recovery_due_tick
        self.assertEqual(due, 110)
        before = sorted(individual.pk for individual in self._individuals())

        # Pure reads, map preparation and an undersupplied hunt acceptance
        # cannot stand in for the clock-settled wave.
        population_counts(self.wilderness, ZONE_KEY)
        plan_population_wave(self.wilderness, ZONE_KEY, tick=110)
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.wilderness.mapprovider.at_prepare_room(PROBE, self.char1, self.char1.location)
        definition = register(
            quest(
                "t_recovery_hunt",
                stages=(QuestStage(0, defeat(TIER, quantity=1)),),
            )
        )
        accept(self.char1, definition.key)

        self.assertEqual(
            sorted(individual.pk for individual in self._individuals()), before
        )
        self.assertEqual(zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, due)


class RealSessionRecoveryTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """A real multi-round session: the round occurrence drives recovery."""

    ROUND_PATCHES = (
        "world.rules.combat.battlefield.roll_d100",
        "world.rules.combat.damage.roll_d100",
        "world.rules.combat.rounds.roll_d100",
    )

    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "items",
            "item_effect_profiles",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries("monster_species", "monster_variants", "monster_tiers")
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.region = region_for_coordinates(*PROBE)
        self.clock = get_world_clock()
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        population_lifecycle.register_regional_population()
        self.addCleanup(
            clock_module._EVENT_SOURCES.pop,
            population_lifecycle.STAGE_KIND,
            None,
        )
        self.compositions = {"t_recovery_solo": _solo_composition()}
        self.zone = self._use_zone(wave_budget=1)
        # The clock is the persisted occurrence source every builder reads: the
        # scenario starts at a committed tick, not an in-memory assignment.
        self.clock.advance(100, AdvanceSource.SKIP, [])
        self.created = initialize_zone(
            self.wilderness, ZONE_KEY, seed=SEED, tick=100
        )
        self.baseline_sequence = zone_state(
            self.wilderness, ZONE_KEY
        ).generation_sequence
        self.player = _player("recovery fighter")
        self.skill = SYNTH_SKILLS["t_ember_burst"].key
        self.player.traits.magic_power.base = 30
        grant_lineage(self.player, [self.skill])
        self.player.traits.hp.base = 100000
        self.player.traits.hp.current = 100000
        self.assertTrue(
            enter_wilderness(
                self.player, coordinates=LOCAL[0], name=WILDERNESS_NAME
            )
        )
        self.combatant = Monster.objects.get(pk=self.created[1])
        # The synthetic tier vocabulary is a zone-authoring seam; give the live
        # behaviour rulebook the same key so the round policy resolves an
        # authored archetype for the zone-born individual.
        from world.rules import monster_behaviour

        rulebook = dict(monster_behaviour.MONSTER_BEHAVIOUR_YAML)
        tier_defaults = dict(rulebook["tier_default_archetype"])
        tier_defaults[self.combatant.threat_tier] = next(iter(tier_defaults.values()))
        rulebook["tier_default_archetype"] = tier_defaults
        self.enterContext(
            patch.object(monster_behaviour, "MONSTER_BEHAVIOUR_YAML", rulebook)
        )
        self.combatant.traits.hp.base = 100000
        self.combatant.traits.hp.current = 100000
        regional_population.register_explicit_individual(
            self.wilderness, self.combatant, LOCAL[0], tick=100
        )
        engage(self.player, self.combatant)
        # One earlier loss leaves the zone deficient and due at 110.
        self._kill(Monster.objects.get(pk=self.created[0]), 100)
        settle_population_lifecycle(100, 100)
        self.assertEqual(
            zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 110
        )

    def _use_zone(self, *, wave_budget: int) -> EcologyZone:
        zone = EcologyZone(
            ZONE_KEY,
            self.region,
            ((0, 0, 0, 0),),
            (WeightedComposition("t_recovery_solo", 1),),
            LOWER_DENSITY,
            UPPER_DENSITY,
            3,
            recovery_delay=DELAY,
            replenishment_interval=REPLENISH,
            wave_budget=wave_budget,
        )
        self.enterContext(
            patch.object(
                regional_population,
                "ECOLOGY_ZONE_REGISTRY",
                MappingProxyType({zone.key: zone}),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType(dict(self.compositions)),
            )
        )
        self.enterContext(
            patch.object(
                monster_sites,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType(dict(self.compositions)),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "SETTLEMENT_BIRTH_POLICY_REGISTRY",
                MappingProxyType({}),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "eligible_birth_cells",
                lambda *a, **k: tuple(LOCAL),
            )
        )
        self.enterContext(
            patch.object(
                regional_population, "_region_cells", lambda zone: frozenset(LOCAL)
            )
        )
        self.enterContext(
            patch.object(monster_sites, "MONSTER_SITE_REGISTRY", MappingProxyType({}))
        )
        return zone

    def _kill(self, individual, tick: int) -> None:
        before = presence_of(self.wilderness, individual)
        individual.traits.hp.current = 0
        record_population_transition(
            self.wilderness,
            PopulationTransition(
                source_id=f"test-loss:{individual.pk}:{tick}",
                individual_id=int(individual.pk),
                occurred_tick=tick,
                before=before,
                after=presence_of(self.wilderness, individual, alive=False),
            ),
        )

    def _round(self) -> dict:
        submitted = submit_player_action(
            self.player, self.skill, [self.combatant]
        )
        from world.rules import combat as combat_package
        from world.rules.combat import damage

        real_apply = damage._apply_hp_delta
        combatant_pk = int(self.combatant.pk)

        def apply_hp(entity, delta):
            if getattr(entity, "pk", None) == combatant_pk:
                entity.traits.hp.current = 0
                return
            real_apply(entity, delta)

        with (
            patch(self.ROUND_PATCHES[0], return_value=100),
            patch(self.ROUND_PATCHES[1], return_value=100),
            patch(self.ROUND_PATCHES[2], return_value=100),
            # The enemy takes no action: this control is about the party's
            # committed defeat occurrence, not enemy policy.
            patch(
                "world.rules.combat_session.policies._enemy_policy",
                lambda *a, **k: None,
            ),
            patch.object(damage, "_apply_hp_delta", apply_hp),
            patch.object(combat_package, "_apply_hp_delta", apply_hp),
        ):
            return complete_party_draft(
                self.player, self.combatant, submitted
            )

    @covers_requirement(
        "regional-population::loss-timing-and-encounter-protection-survive-deferred-combat-settlement"
    )
    @covers_requirement(
        "wilderness-monster-population::active-encounters-retain-protected-individuals-and-cells"
    )
    def test_a_real_session_persists_its_occurrence_and_protection(self):
        self.assertEqual(self._round()["outcome"], "round")
        self.assertEqual(self._round()["outcome"], "round")
        reloaded = read_session(self.player)
        self.assertEqual(reloaded.started_tick, 100)
        self.assertEqual(
            reloaded.population_cell,
            {"wilderness": WILDERNESS_NAME, "x": LOCAL[0][0], "y": LOCAL[0][1]},
        )
        self.assertEqual(reloaded.rounds_elapsed, 2)

        self.combatant.traits.hp.current = 1
        with self.captureOnCommitCallbacks(execute=True):
            result = self._round()
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(read_session(self.player))
        self.assertEqual(
            get_world_clock().tick, 100 + 3 * _ROUND_SECONDS
        )
        # The durable session evidence survives the fight: its exact cell and
        # closed [start, end] interval are protected after the clear.
        protection = read_population_timeline(self.wilderness).protection
        self.assertEqual(
            [(p.start_tick, p.end_tick) for p in protection],
            [(100, 100 + 3 * _ROUND_SECONDS)],
        )

    @covers_requirement(
        "regional-population::loss-timing-and-encounter-protection-survive-deferred-combat-settlement"
    )
    def test_a_late_terminal_failure_rolls_back_the_wave_and_keeps_the_session(self):
        self.assertEqual(self._round()["outcome"], "round")
        self.assertEqual(self._round()["outcome"], "round")
        self.combatant.traits.hp.current = 1

        with patch(
            "world.narrative.events.record_narrative_event",
            side_effect=RuntimeError("synthetic post-advance failure"),
        ):
            with self.assertRaises(RuntimeError):
                self._round()

        # The clock, the wave and the state rolled back together; the session
        # is still exactly the pre-round one for one clean retry.
        self.assertEqual(self.clock.tick, 100)
        session = read_session(self.player)
        self.assertIsNotNone(session)
        self.assertEqual(session.rounds_elapsed, 2)
        self.assertEqual(
            zone_state(self.wilderness, ZONE_KEY).generation_sequence,
            self.baseline_sequence,
        )
        self.assertEqual(
            zone_state(self.wilderness, ZONE_KEY).recovery_due_tick, 110
        )
        self.assertEqual(len(population_counts(self.wilderness, ZONE_KEY).local_ids), 2)
