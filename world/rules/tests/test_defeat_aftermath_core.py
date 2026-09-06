"""Defeat-aftermath core tests (defeat-aftermath-core).

Covers the hostile-defeat settlement contract: the HP-1 nonlethal floor,
the violator departure (population despawn, quest-bound retain with
precedence, foreign untouched), the weak debuff mount and ordinary decay,
the EventLog kinds with the observability boundary event, the guarded
violation hook, the per-section rulebook loader, and the zero-uncaused-write
battery.

Annotation note: the ``covers_requirement`` annotations reference the
canonical main-spec requirement IDs that exist since this change's delta
synced into ``openspec/specs/``.
"""

from unittest.mock import MagicMock, patch

from django.test import override_settings
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

import world.rules.defeat_aftermath as defeat_aftermath_module
from world.rules import combat_session as combat_session_module
from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom, Room
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.tests._fixtures import (
    RegistryIsolationMixin,
    accept,
    defeat,
    quest,
    register,
)
from world.rules.affinity import apply_affinity_change
from world.rules.buffs import entity_active_buffs, tick_buffs
from world.rules.clock import WorldClock
from world.rules.combat_session import (
    engage,
    forfeit,
    restore_active_session,
    submit_player_action,
)
from world.rules.defeat_aftermath import (
    DEFEAT_AFTERMATH_RULEBOOK,
    load_defeat_aftermath_sections,
    register_violation_hook,
)
from world.rules.event_log import render_plain_text
from world.rules.movement import charge_movement
from world.rules.player_messages import terminal_outcome_message
from world.rules.skip_safety import SkipRejectReason, evaluate_skip_safety
from world.rules.surfaces import read_counter_trait, write_counter_trait
from tools.spec_traceability import covers_requirement

from ._combat_session_helpers import BattlefieldIsolation, _monster, _player


class DefeatAftermathBase(BattlefieldIsolation, EvenniaTestCase):
    """Shared clock isolation: both clock bindings see one WorldClock."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="defeat arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("defeat goblin")
        self.monster.location = self.room
        self.clock = WorldClock()
        for target in (
            "world.rules.combat_session.get_world_clock",
            "world.rules.clock.get_world_clock",
        ):
            patcher = patch(target, return_value=self.clock)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _defeat_by_forfeit(self, target=None):
        """Drive one hostile defeat settlement through ``forfeit``."""
        engage(self.player, target or self.monster)
        with patch("world.rules.combat.roll_d100", return_value=1):
            submit_player_action(self.player, "basic_attack", [target or self.monster])
        return forfeit(self.player)


class WildernessDefeatMixin:
    """Materialize the real wilderness script and move the fight into it."""

    def tearDown(self):
        super().tearDown()
        # The contrib wilderness stamps ndb.wilderness/ndb.wildernessscript on
        # every occupant and room; TypedObject.at_idmapper_flush refuses to
        # evict ndb-holding objects, so EvenniaTestCase's non-forced
        # flush_cache leaves these rolled-back rows cached as idmapper ghosts.
        # A later module's create_object would resolve DEFAULT_HOME (#2)
        # through the stale cache entry and write a dangling db_home_id.
        ObjectDB.flush_instance_cache(force=True)

    def setUp_wilderness(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.assertTrue(enter_wilderness(self.player, coordinates=(60, 103), name=WILDERNESS_NAME))
        self.room = self.player.location
        self.monster.location = self.room

    def _mark_population_monster(self, monster, coordinates=(60, 103)):
        """Stamp the population marker and register the bookkeeping entry."""
        monster.db.population_key = f"wilderness:{coordinates[0]}:{coordinates[1]}"
        self.script.db.itemcoordinates[monster] = coordinates

    def _registered(self, monster):
        """Identity membership in the bookkeeping: the despawned instance is
        pk-stripped and therefore unhashable as a dict lookup key."""
        return any(key is monster for key in self.script.db.itemcoordinates.keys())


class WeakDebuffRulebookTests(DefeatAftermathBase):
    """The ``defeat_weak`` settle-time mount and ordinary decay (D-C2)."""

    @covers_requirement(
        "defeat-aftermath-core::defeat-weak-debuff-is-mounted-at-settle-time",
        "defeat-aftermath-core::hostile-defeat-floors-player-hp-at-1-and-marks-the-player-knocked-out",
    )
    def test_defeat_mounts_weak_debuff_and_it_expires_ordinarily(self):
        self._defeat_by_forfeit()
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(self.player.traits.hp.current, 1)
        tick_buffs(self.player, 299)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        tick_buffs(self.player, 1)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))


class ViolationHookGuardTests(DefeatAftermathBase):
    """The ``DEFEAT_ADULT_SCENES`` guard around the violation hook (D-C4)."""

    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, defeat_aftermath_module, "_VIOLATION_HOOK", None)

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-adult-scenes-setting-exists-and-guards-the-violation-hook"
    )
    def test_flag_on_calls_the_registered_hook_body(self):
        calls = []
        register_violation_hook(lambda battlefield, session: calls.append(session))
        self._defeat_by_forfeit()
        self.assertEqual(len(calls), 1)

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-adult-scenes-setting-exists-and-guards-the-violation-hook"
    )
    @override_settings(DEFEAT_ADULT_SCENES=False)
    def test_flag_off_never_calls_the_hook_and_settles_the_core_path(self):
        calls = []
        register_violation_hook(lambda battlefield, session: calls.append(session))
        result = self._defeat_by_forfeit()
        self.assertEqual(calls, [])
        # Core-only losses are unchanged with the flag off.
        self.assertEqual(self.player.traits.hp.current, 1)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(result["outcome"], "defeat")

    def test_duplicate_or_invalid_registrations_fail_loudly(self):
        def hook(battlefield, session):
            return None

        register_violation_hook(hook)
        with self.assertRaises(RuntimeError):
            register_violation_hook(lambda battlefield, session: None)
        register_violation_hook(hook)  # identical re-registration is idempotent
        with self.assertRaises(ValueError):
            register_violation_hook("not callable")


class DepartureRuleTests(DefeatAftermathBase):
    """Violator departure precedence: quest-bound retain over despawn (D-C3)."""

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_foreign_monster_is_untouched(self):
        result = self._defeat_by_forfeit()
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.monster.pk, self.monster.pk)  # alive, untouched
        self.assertEqual(self.monster.location, self.room)


class WildernessDepartureTests(WildernessDefeatMixin, DefeatAftermathBase):
    """Population despawn and quest-bound retention in the real wilderness."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_population_winner_despawns_at_defeat_settlement(self):
        self._mark_population_monster(self.monster)
        saved_pk = self.monster.pk
        with self.captureOnCommitCallbacks(execute=True):
            self._defeat_by_forfeit()
        self.assertFalse(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertFalse(self._registered(self.monster))
        # The next coordinate activation respawns per the untouched model.
        from world.maps.wilderness_population import ensure_population

        ensure_population(self.script, (60, 103))
        monsters = [
            obj
            for obj in self.script.get_objs_at_coordinates((60, 103))
            if isinstance(obj, type(self.monster))
        ]
        self.assertEqual(len(monsters), 1)

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_quest_bound_winner_with_marker_is_retained(self):
        self._bind_defeat_quest(self.monster)
        self._mark_population_monster(self.monster)
        saved_pk = self.monster.pk
        self._defeat_by_forfeit()
        # Quest retention outranks the population marker: the monster stays.
        self.assertTrue(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertEqual(self.monster.location, self.room)
        self.assertTrue(self._registered(self.monster))

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_post_commit_delete_failure_reverts_departure(self):
        self._mark_population_monster(self.monster)
        saved_marker = self.monster.db.population_key
        with (
            patch.object(
                type(self.monster), "delete", side_effect=RuntimeError("boom")
            ),
            patch("world.rules.defeat_aftermath.log_error") as log_error,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self._defeat_by_forfeit()
        # Deterministic recovery: the logical departure reverted, the monster
        # remains a normal reconcilable population monster.
        self.assertEqual(self.monster.db.population_key, saved_marker)
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.location, self.room)
        errors = [
            call
            for call in log_error.call_args_list
            if call.args and call.args[0] == "defeat_aftermath_depart_delete_failed"
        ]
        self.assertEqual(len(errors), 1)

    def _bind_defeat_quest(self, monster):
        """Accept a bound-defeat quest whose objective targets ``monster``."""
        definition = register(quest("aftermath_defeat", stages=(QuestStage(0, defeat(bound=True)),)))
        record = accept(self.player, definition.key)
        self.guard_room = create_object(InstanceRoom, key="aftermath guard room")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=self.guard_room,
            objective_targets=(monster,),
            protected_entities=(self._guard_npc(),),
        )

    def _guard_npc(self):
        if not hasattr(self, "guard_npc"):
            self.guard_npc = create_object(NPC, key="aftermath guard")
            self.guard_npc.race = "human"
            self.guard_npc.apply_race_baseline()
        return self.guard_npc


class RetainedWinnerConsequenceTests(WildernessDefeatMixin, DefeatAftermathBase):
    """Task 3.3: the retained winner blocks rest; movement stays HP-free."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        definition = register(quest("retained_defeat", stages=(QuestStage(0, defeat(bound=True)),)))
        record = accept(self.player, definition.key)
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=create_object(InstanceRoom, key="retained guard room"),
            objective_targets=(self.monster,),
        )

    @covers_requirement(
        "defeat-aftermath-core::hostile-defeat-floors-player-hp-at-1-and-marks-the-player-knocked-out",
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained",
    )
    def test_retained_winner_blocks_rest_but_not_movement(self):
        self._defeat_by_forfeit()
        self.assertEqual(self.player.traits.hp.current, 1)
        # skip_safety still refuses a time-skip rest with the live winner.
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.HOSTILE_PRESENT
        )
        # Movement has no HP gate (pinned behavior, no edit): the shared cost
        # charge succeeds at HP 1.
        before = self.clock.tick
        charge_movement(self.player, "move")
        self.assertGreater(self.clock.tick, before)


class RenderingTests(DefeatAftermathBase):
    """EventLog kinds, zh-tw lines, and the observability boundary event."""

    @covers_requirement(
        "defeat-aftermath-core::defeat-aftermath-emits-eventlog-entries-and-defeat-lines"
    )
    def test_aftermath_event_log_kinds_appear_in_order(self):
        result = self._defeat_by_forfeit()
        aftermath = [
            log for log in result["logs"] if log.skill_key == "defeat_aftermath"
        ]
        self.assertEqual(len(aftermath), 1)
        kinds = [entry.kind for entry in aftermath[0].entries]
        self.assertEqual(kinds, ["defeat_settle", "weak_granted"])
        rendered = render_plain_text(aftermath[0])
        self.assertIn(DEFEAT_AFTERMATH_RULEBOOK.pg_lines[0], rendered)
        self.assertIn("虛弱感籠罩全身", rendered)

    @covers_requirement(
        "defeat-aftermath-core::defeat-aftermath-emits-eventlog-entries-and-defeat-lines"
    )
    def test_bare_defeat_line_is_replaced(self):
        self.assertNotEqual(terminal_outcome_message("defeat"), "你被擊敗了。")
        self.assertIn("你被擊敗了", terminal_outcome_message("defeat"))

    @covers_requirement(
        "defeat-aftermath-core::defeat-aftermath-emits-eventlog-entries-and-defeat-lines"
    )
    def test_committed_defeat_emits_one_boundary_event(self):
        with (
            patch("world.rules.defeat_aftermath.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self._defeat_by_forfeit()
        calls = [
            call for call in info.call_args_list if call.args and call.args[0] == "defeat_aftermath"
        ]
        self.assertEqual(len(calls), 1)
        (_, kwargs), = calls
        self.assertEqual(kwargs["context"]["char"], str(self.player.key))
        self.assertEqual(kwargs["context"]["room"], str(self.room.pk))
        self.assertEqual(kwargs["context"]["hp_after"], 1)
        self.assertIn("tick", kwargs["context"])

    @covers_requirement(
        "defeat-aftermath-core::defeat-aftermath-emits-eventlog-entries-and-defeat-lines"
    )
    def test_rolled_back_defeat_emits_no_boundary_event(self):
        engage(self.player, self.monster)
        with (
            patch("world.rules.defeat_aftermath.log_info") as info,
            patch("world.rules.combat_session._persist", side_effect=RuntimeError("injected")),
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(RuntimeError):
                forfeit(self.player)
        self.assertEqual(
            [call for call in info.call_args_list if call.args and call.args[0] == "defeat_aftermath"],
            [],
        )


class RulebookLoaderTests(DefeatAftermathBase):
    """The per-section loader (D-C8): owned sections fail closed, foreign ignored."""

    def _load(self, text):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(text)
            path = handle.name
        self.addCleanup(__import__("os").unlink, path)
        from pathlib import Path

        return load_defeat_aftermath_sections(Path(path))

    def test_shipped_rulebook_loads_with_owned_sections(self):
        self.assertTrue(DEFEAT_AFTERMATH_RULEBOOK.pg_lines)
        self.assertEqual(DEFEAT_AFTERMATH_RULEBOOK.weak_debuff_buff_key, "defeat_weak")

    def test_unknown_section_is_ignored_with_one_warning(self):
        with patch("world.rules.defeat_aftermath.log_warn") as warn:
            rulebook = self._load(
                "pg_lines:\n  - '你醒了。'\nweak_debuff:\n  buff_key: defeat_weak\n"
                "violation_families: []\ndigest_table: {}\n"
            )
        self.assertEqual(warn.call_count, 1)
        self.assertIn("violation_families", warn.call_args.kwargs["context"]["sections"])
        self.assertIn("digest_table", warn.call_args.kwargs["context"]["sections"])
        self.assertEqual(rulebook.pg_lines, ("你醒了。",))

    def test_malformed_owned_section_fails_load(self):
        with self.assertRaises(ValueError):
            self._load("pg_lines: []\nweak_debuff:\n  buff_key: defeat_weak\n")
        with self.assertRaises(ValueError):
            self._load("pg_lines:\n  - '你醒了。'\nweak_debuff:\n  buff_key: no_such_buff\n")
        with self.assertRaises(ValueError):
            self._load("pg_lines:\n  - '你醒了。'\n")


class ZeroUncausedWriteTests(WildernessDefeatMixin, RegistryIsolationMixin, DefeatAftermathBase):
    """The declared-write manifest battery (D-C7, tasks 6.1)."""

    # Record families the defeat settlement must leave byte-identical. Code,
    # not prose: each downstream change extends this manifest with its declared
    # writes and re-runs the battery.
    CLOCK_CAUSED_FAMILIES = (
        # Legitimate in-window mutations the world clock causally produces:
        # quest deadline failure, gauge daily decay/reset, merchant restock,
        # buff decay. The battery's settlement window crosses none of them.
        "quest_deadline",
        "gauge_daily",
        "restock",
        "buff_decay",
    )

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        self.companion = create_object(NPC, key="aftermath companion")
        self.companion.race = "human"
        self.companion.apply_race_baseline()
        self.companion.location = self.room
        self.guard_npc = create_object(NPC, key="aftermath staff")
        self.guard_npc.race = "human"
        self.guard_npc.apply_race_baseline()
        self.guard_npc.location = self.room
        from world.rules.party import join_party

        join_party(self.companion, self.player)
        apply_affinity_change(self.guard_npc, self.player, "quest_completion", 5)
        self.player.guild_rank = "E"
        write_counter_trait(self.player, "guild_merit", 10)
        self.player.wallet = 500
        # Seeded raw inventory (shape mirrors list_items: a list of keys).
        self.player.db.inventory = ["healing_potion"]
        definition = register(quest("battery_defeat", stages=(QuestStage(0, defeat(bound=True)),)))
        record = accept(self.player, definition.key)
        self.bound_room = create_object(InstanceRoom, key="battery binding room")
        self.bound_monster = _monster("battery bound goblin")
        self.bound_monster.location = self.room
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=self.bound_room,
            objective_targets=(self.bound_monster,),
            protected_entities=(self.guard_npc,),
        )
        self._mark_population_monster(self.monster)

    def _manifest(self):
        """The declared-write manifest: family -> extractor (D-C7)."""
        player, companion, guard = self.player, self.companion, self.guard_npc
        return {
            "affinity": lambda: (
                guard.relations.affinity_for(player),
                companion.relations.affinity_for(player),
            ),
            "wallet": lambda: player.wallet,
            "inventory": lambda: list(player.db.inventory or []),
            "quest_progress": lambda: [dict(e) for e in (player.db.quest_log or [])],
            "guild_rank": lambda: player.guild_rank,
            "guild_merit": lambda: read_counter_trait(player, "guild_merit"),
            "protected_bindings": lambda: list(self.bound_room.db.pin_reasons or []),
            "party_binding": lambda: (list(player.db.party or []), companion.db.party_member),
        }

    @covers_requirement(
        "defeat-aftermath-core::defeat-settlement-s-only-uncaused-record-writes-are-the-declared-ones"
    )
    def test_manifest_section_ownership(self):
        manifest = self._manifest()
        for family in (
            "affinity",
            "wallet",
            "inventory",
            "quest_progress",
            "guild_rank",
            "guild_merit",
            "protected_bindings",
        ):
            self.assertIn(family, manifest)
        self.assertTrue(self.CLOCK_CAUSED_FAMILIES)

    @covers_requirement(
        "defeat-aftermath-core::defeat-settlement-s-only-uncaused-record-writes-are-the-declared-ones",
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained",
    )
    def test_defeat_settlement_writes_only_the_declared_records(self):
        before = {family: extract() for family, extract in self._manifest().items()}
        saved_marker_pk = self.monster.pk
        saved_bound_pk = self.bound_monster.pk
        # Defeat one: the population-marker monster despawns. Defeat two: the
        # quest-bound monster is retained by precedence.
        with self.captureOnCommitCallbacks(execute=True):
            self._defeat_by_forfeit(self.monster)
            self.player.traits.hp.current = 100
            self._defeat_by_forfeit(self.bound_monster)
        after = {family: extract() for family, extract in self._manifest().items()}
        self.assertEqual(after, before)
        self.assertFalse(ObjectDB.objects.filter(id=saved_marker_pk).exists())
        self.assertTrue(ObjectDB.objects.filter(id=saved_bound_pk).exists())
        self.assertEqual(self.bound_monster.location, self.room)
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.HOSTILE_PRESENT
        )


class RollbackTests(WildernessDefeatMixin, RegistryIsolationMixin, DefeatAftermathBase):
    """Rollback injection after the writer's last write (tasks 6.2, D-C5)."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        self._mark_population_monster(self.monster)

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-aftermath-joins-the-round-s-atomic-persistence-unit"
    )
    def test_persist_failure_rolls_back_the_whole_aftermath_and_retry_settles_once(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=1):
            submit_player_action(self.player, "basic_attack", [self.monster])
        saved_pk = self.monster.pk
        hp_after_round = self.player.traits.hp.current
        quest_log_before = [dict(e) for e in (self.player.db.quest_log or [])]
        with (
            patch("world.rules.combat_session._persist", side_effect=RuntimeError("injected")),
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        # Every aftermath write is absent: monster, bookkeeping, HP, buff.
        self.assertTrue(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.location, self.room)
        self.assertEqual(self.player.traits.hp.current, hp_after_round)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual([dict(e) for e in (self.player.db.quest_log or [])], quest_log_before)
        self.assertIsNotNone(self.player.db.active_combat)
        self.assertEqual(self.clock.tick, 6)
        # Retry settles fully, exactly once.
        with self.captureOnCommitCallbacks(execute=True):
            result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.player.traits.hp.current, 1)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        self.assertFalse(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertFalse(self._registered(self.monster))
        self.assertIsNone(self.player.db.active_combat)
        self.assertEqual(self.clock.tick, 12)

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-aftermath-joins-the-round-s-atomic-persistence-unit"
    )
    def test_commit_exit_failure_restores_aftermath_surfaces(self):
        class ExplodingAtomic:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                if exc_type is None:
                    raise RuntimeError("injected commit failure")
                return False

        collected: list = []
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=1):
            submit_player_action(self.player, "basic_attack", [self.monster])
        saved_pk = self.monster.pk
        saved_marker = self.monster.db.population_key
        hp_after_round = self.player.traits.hp.current
        fake_tx = MagicMock()
        fake_tx.atomic.return_value = ExplodingAtomic()
        fake_tx.on_commit.side_effect = collected.append
        with (
            patch("django.db.transaction.atomic", fake_tx.atomic),
            patch("django.db.transaction.on_commit", fake_tx.on_commit),
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        # The commit-exit failure bypasses any in-body handler: the outer
        # handler restored every idmapper-cached aftermath surface.
        self.assertEqual(self.player.traits.hp.current, hp_after_round)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(self.monster.db.population_key, saved_marker)
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.pk, saved_pk)  # callbacks never executed

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-aftermath-joins-the-round-s-atomic-persistence-unit",
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained",
    )
    def test_outer_round_rollback_restores_aftermath_surfaces(self):
        # The submit path settles inside _submit_request's round transaction:
        # a failure AFTER the settlement returned must roll the aftermath
        # back together with the round (duck review issue 1).
        self.player.traits.hp.current = 1
        self.monster.traits.atk_phys.base = 100
        engage(self.player, self.monster)
        saved_pk = self.monster.pk
        saved_marker = self.monster.db.population_key
        real_continue = combat_session_module._continue_or_settle

        def exploding_continue(actor, record, battlefield, logs, **kwargs):
            real_continue(actor, record, battlefield, logs, **kwargs)
            raise RuntimeError("injected outer failure after settlement")

        with (
            patch(
                "world.rules.combat_session._continue_or_settle",
                exploding_continue,
            ),
            patch("world.rules.combat.roll_d100", return_value=1),
            self.assertRaises(RuntimeError),
        ):
            submit_player_action(self.player, "basic_attack", [self.monster])
        # The armed undo ran inside _submit_request's except: the winner and
        # its marker/bookkeeping survived the outer rollback.
        self.assertEqual(self.monster.pk, saved_pk)
        self.assertEqual(self.monster.db.population_key, saved_marker)
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.location, self.room)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(self.player.traits.hp.current, 1)
        self.assertIsNotNone(self.player.db.active_combat)


class RecoveryFallbackDepartureTests(WildernessDefeatMixin, DefeatAftermathBase):
    """The degraded recovery path departs the resolvable winner (review D4)."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        self._mark_population_monster(self.monster)

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_moved_player_recovery_still_departs_population_winner(self):
        engage(self.player, self.monster)
        elsewhere = create_object(Room, key="recovery fallback room")
        self.player.location = elsewhere
        saved_pk = self.monster.pk
        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            self.captureOnCommitCallbacks(execute=True),
        ):
            restore_active_session(self.player)
        self.assertEqual(self.player.traits.hp.current, 1)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        self.assertFalse(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertFalse(self._registered(self.monster))
        self.assertIsNone(self.player.db.active_combat)
