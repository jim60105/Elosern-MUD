"""Data-contract test: church enrollment office and vestment handover contract

The deterministic enrollment rite (design §5.1, church-ordination delta):
``world/rules/church.py::enroll`` materializes the ``db.church`` ledger, stamps
``enrolled_tick``, and emits ``church_enrolled`` through the transaction-commit
seam; a female ``human_royal`` initiate is additionally granted
``saintess_vessel`` through the canonical granted-passive write path with
exactly one ``saintess_vessel_granted`` event (no office uniqueness — every
eligible royal becomes a saintess, and the trickle stays disarmed until
enrollment); and every initiate receives exactly one clerical vestment —
``saintess_vestments`` for the vessel branch, ``sister_vestments`` otherwise —
unconditionally, through the ``QuestReward`` item-quantity rail, transactional
with the ledger write.

Shipped subrace/vessel/vestment/event names appear literally because this
module IS the shipped-content contract for the enrollment mechanics (the
test-data-independence gate exempts tagged data-contract tests).
"""

from unittest.mock import patch

from django.db import transaction

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ChurchHost
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules import church
from world.rules.church import (
    SAINTESS_VESTMENTS_KEY,
    SISTER_VESTMENTS_KEY,
    EnrollmentError,
    EnrollmentReason,
    VESSEL_KEY,
    enroll,
)
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.skill_ownership import owns_stored_skill

GRANT_EVENT = "saintess_vessel_granted"
ENROLL_EVENT = "church_enrolled"


def _royal():
    """A female ``human_royal`` character shell, the vessel-eligible branch."""
    character = create_object(PlayerCharacter, key="royal initiate")
    character.race = "human"
    character.subrace = "human_royal"
    character.sex = "female"
    character.apply_race_baseline()
    return character


class ChurchHostIsolation(EvenniaTest):
    """One on-duty ChurchHost NPC beside the caller, with a frozen clock."""

    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="t_church_hall")
        self.char1.location = self.hall
        self.celebrant = create_object(NPC, key="t_celebrant", location=self.hall)
        self.component = ChurchHost.create(self.celebrant, service_id="t_celebrant")
        self.celebrant.components.add(self.component)
        self.clock = WorldClock(tick=0)
        self._clock_patch = patch(
            "world.rules.church.get_world_clock", return_value=self.clock
        )
        self._clock_patch.start()
        self.addCleanup(self._clock_patch.stop)

    def _events(self, info_mock):
        return [call.args[0] for call in info_mock.call_args_list if call.args]

    def _persisted_attribute_keys(self, character):
        """The attribute keys actually persisted for one object (DB, no cache)."""
        from evennia.objects.models import ObjectDB

        through = ObjectDB.db_attributes.through
        return {
            getattr(row, "attribute").db_key
            for row in through.objects.filter(objectdb__pk=character.pk)
        }


class ChurchEnrollmentRiteTests(ChurchHostIsolation):
    """The three-stage transaction: commit, events, rejections, rollback."""

    @covers_requirement(
        "church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost"
    )
    def test_clean_enrollment_commits_ledger_and_one_event(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True) as callbacks,
        ):
            record = enroll(self.char1, self.celebrant)
        self.assertEqual(record["vessel_branch"], False)
        self.assertEqual(record["item"], SISTER_VESTMENTS_KEY)
        self.assertEqual(church.read_ledger(self.char1)["enrolled_tick"], 0)
        self.assertEqual(church.enrolled_tick(self.char1), 0)
        self.assertEqual(self._events(info), [ENROLL_EVENT])
        (event,), kwargs = info.call_args
        self.assertEqual(event, ENROLL_EVENT)
        self.assertEqual(kwargs["context"]["char"], str(self.char1))
        self.assertEqual(kwargs["context"]["host"], self.celebrant.key)
        self.assertEqual(kwargs["context"]["item"], SISTER_VESTMENTS_KEY)
        self.assertLessEqual(len(callbacks), 2)
        self.assertEqual(
            list(self.char1.db.inventory), [SISTER_VESTMENTS_KEY]
        )

    @covers_requirement(
        "church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost"
    )
    def test_re_enrollment_is_a_stable_inert_rejection(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        with self.captureOnCommitCallbacks(execute=True):
            enroll(self.char1, self.celebrant)
        before_ledger = church.read_ledger(self.char1)
        before_inventory = list(self.char1.db.inventory or [])
        before_skills = self.char1.db.skills
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(EnrollmentError) as caught:
                enroll(self.char1, self.celebrant)
        self.assertEqual(caught.exception.args[0], EnrollmentReason.ALREADY_ENROLLED)
        self.assertEqual(self._events(info), [])
        self.assertEqual(church.read_ledger(self.char1), before_ledger)
        self.assertEqual(list(self.char1.db.inventory or []), before_inventory)
        self.assertEqual(self.char1.db.skills, before_skills)
        # The first enrollment legitimately persists church + inventory; the
        # rejected second call must add nothing (no skills row either).
        self.assertEqual(
            self._persisted_attribute_keys(self.char1) & {"church", "skills", "inventory"},
            {"church", "inventory"},
            "re-enrollment writes nothing at the DB level",
        )

    @covers_requirement(
        "church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost"
    )
    def test_a_non_player_actor_is_rejected(self):
        room = create_object(Room, key="t_not_a_player")
        with self.assertRaises(EnrollmentError) as caught:
            enroll(room, self.celebrant)
        self.assertEqual(caught.exception.args[0], EnrollmentReason.NOT_A_PLAYER)

    @covers_requirement(
        "church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost"
    )
    def test_missing_or_incapable_host_is_a_stable_rejection(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        # A host without the ChurchHost component (e.g. the sanctum steward).
        steward = create_object(NPC, key="t_steward", location=self.hall)
        with self.assertRaises(EnrollmentError) as caught:
            enroll(self.char1, steward)
        self.assertEqual(caught.exception.args[0], EnrollmentReason.NO_HOST)
        self.assertIsNone(getattr(self.char1.db, "church", None))
        # A remote host (not co-located) is refused by the service gate.
        elsewhere = create_object(Room, key="t_elsewhere")
        remote = create_object(NPC, key="t_remote_celebrant", location=elsewhere)
        remote.components.add(
            ChurchHost.create(remote, service_id="t_remote_celebrant")
        )
        with self.assertRaises(EnrollmentError) as caught:
            enroll(self.char1, remote)
        self.assertEqual(caught.exception.args[0], EnrollmentReason.REMOTE_HOST)
        self.assertIsNone(getattr(self.char1.db, "church", None))

    @covers_requirement(
        "church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost"
    )
    def test_malformed_ledger_is_a_stable_inert_rejection(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.db.church = "not_a_mapping"
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(EnrollmentError) as caught:
                enroll(self.char1, self.celebrant)
        self.assertEqual(
            caught.exception.args[0], EnrollmentReason.MALFORMED_LEDGER
        )
        self.assertEqual(self._events(info), [])
        self.assertEqual(getattr(self.char1.db, "church", None), "not_a_mapping")
        self.assertIsNone(getattr(self.char1.db, "inventory", None))

    @covers_requirement(
        "church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost"
    )
    def test_caller_outer_rollback_emits_nothing_and_is_byte_identical(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                enroll(self.char1, self.celebrant)
                transaction.set_rollback(True)
        self.assertEqual(self._events(info), [], "no event survives a rollback")
        # The DB — not the transaction-unaware in-memory attribute cache —
        # proves the byte-identical guarantee: no attribute row survives.
        self.assertFalse(
            {"church", "skills", "inventory"}
            & self._persisted_attribute_keys(self.char1),
            "a rolled-back enrollment leaves no persisted state",
        )

    @covers_requirement(
        "church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost"
    )
    def test_internal_failure_restores_persisted_and_cached_surfaces(self):
        # A failure INSIDE the enrollment transaction (after the inventory
        # plan applied) must roll the DB back and restore the in-memory
        # attribute cache so the character is byte-identical.
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        from world.rules.equipment import apply_inventory_plan as real_apply

        def write_then_raise(plan):
            real_apply(plan)
            raise RuntimeError("simulated post-write enrollment failure")

        with (
            patch("world.rules.equipment.apply_inventory_plan", side_effect=write_then_raise),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            enroll(self.char1, self.celebrant)
        self.assertEqual(self._events(info), [])
        self.assertIsNone(getattr(self.char1.db, "church", None))
        self.assertIsNone(getattr(self.char1.db, "skills", None))
        self.assertIsNone(getattr(self.char1.db, "inventory", None))
        self.assertFalse(
            {"church", "skills", "inventory"}
            & self._persisted_attribute_keys(self.char1),
            "no persisted writes survive",
        )

    @covers_requirement(
        "church-ordination::enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost"
    )
    def test_events_wait_for_the_caller_outer_commit(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                enroll(self.char1, self.celebrant)
                self.assertEqual(
                    self._events(info),
                    [],
                    "commit-bound events must not fire inside the transaction",
                )
        self.assertEqual(self._events(info), [ENROLL_EVENT])


class SaintessOfficeBranchTests(ChurchHostIsolation):
    """The subrace/sex office branch (design §7, no uniqueness)."""

    def _enroll(self, character):
        with self.captureOnCommitCallbacks(execute=True):
            return enroll(character, self.celebrant)

    def _set_identity(self, character, subrace, sex="female", race=None):
        character.location = self.hall
        character.race = race or (
            "human" if subrace.startswith("human_") else subrace
        )
        character.subrace = subrace
        character.sex = sex
        character.apply_race_baseline()
        return character

    @covers_requirement(
        "church-ordination::enrollment-grants-the-saintess-office-to-female-royal-initiates-only-without-uniqueness",
        "saintess-vessel::saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive",
    )
    def test_female_royal_enrollment_grants_the_vessel_in_one_transaction(self):
        royal = self._set_identity(_royal(), "human_royal")
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            record = enroll(royal, self.celebrant)
        self.assertTrue(record["vessel_branch"])
        self.assertTrue(record["vessel_granted"])
        self.assertEqual(record["item"], SAINTESS_VESTMENTS_KEY)
        self.assertEqual(royal.db.skills["passive"], [VESSEL_KEY])
        self.assertTrue(owns_stored_skill(royal, VESSEL_KEY))
        self.assertEqual(
            self._events(info), [ENROLL_EVENT, GRANT_EVENT], "exactly one of each"
        )
        grant_kwargs = info.call_args_list[1].kwargs
        self.assertEqual(grant_kwargs["context"]["entity"], str(royal))
        self.assertEqual(grant_kwargs["context"]["source"], "church_enrollment")
        self.assertEqual(grant_kwargs["context"]["passive"], VESSEL_KEY)

    @covers_requirement(
        "church-ordination::enrollment-grants-the-saintess-office-to-female-royal-initiates-only-without-uniqueness",
        "saintess-vessel::saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive",
    )
    def test_every_other_initiate_gets_no_skill(self):
        cases = (
            # Male royal: same subrace, wrong sex.
            {
                "key": "male royal",
                "subrace": "human_royal",
                "sex": "male",
                "race": "human",
            },
            # Female of another human bloodline.
            {
                "key": "noble lady",
                "subrace": "human_noble",
                "sex": "female",
                "race": "human",
            },
            # Female elf.
            {
                "key": "fionnen lady",
                "subrace": "fionnen",
                "sex": "female",
                "race": "elf",
            },
            # Female beastfolk.
            {
                "key": "foxkin lady",
                "subrace": "foxkin",
                "sex": "female",
                "race": "beastfolk",
            },
        )
        for index, case in enumerate(cases):
            with self.subTest(case=case["key"]):
                initiate = create_object(
                    PlayerCharacter, key=f"{case['key']} {index}"
                )
                initiate.location = self.hall
                initiate.race = case["race"]
                initiate.subrace = case["subrace"]
                initiate.sex = case["sex"]
                initiate.apply_race_baseline()
                with (
                    patch("world.rules.church.log_info") as info,
                    self.captureOnCommitCallbacks(execute=True),
                ):
                    record = enroll(initiate, self.celebrant)
                self.assertFalse(record["vessel_branch"])
                self.assertFalse(record["vessel_granted"])
                self.assertEqual(record["item"], SISTER_VESTMENTS_KEY)
                self.assertFalse(owns_stored_skill(initiate, VESSEL_KEY))
                self.assertNotIn(GRANT_EVENT, self._events(info))
                self.assertEqual(self._events(info), [ENROLL_EVENT])

    @covers_requirement(
        "church-ordination::enrollment-grants-the-saintess-office-to-female-royal-initiates-only-without-uniqueness",
        "saintess-vessel::saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive",
    )
    def test_two_eligible_royals_both_become_saintesses(self):
        first = self._set_identity(_royal(), "human_royal")
        second = create_object(PlayerCharacter, key="second royal")
        self._set_identity(second, "human_royal")
        self._enroll(first)
        self._enroll(second)
        self.assertTrue(owns_stored_skill(first, VESSEL_KEY))
        self.assertTrue(owns_stored_skill(second, VESSEL_KEY))
        self.assertEqual(second.db.skills["passive"], [VESSEL_KEY])

    @covers_requirement(
        "church-ordination::enrollment-grants-the-saintess-office-to-female-royal-initiates-only-without-uniqueness"
    )
    def test_re_enrollment_re_grants_nothing(self):
        royal = self._set_identity(_royal(), "human_royal")
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            enroll(royal, self.celebrant)
        self.assertEqual(self._events(info), [ENROLL_EVENT, GRANT_EVENT])
        with (
            patch("world.rules.church.log_info") as info2,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(EnrollmentError):
                enroll(royal, self.celebrant)
        self.assertEqual(self._events(info2), [])
        self.assertEqual(royal.db.skills["passive"], [VESSEL_KEY])

    @covers_requirement(
        "church-ordination::enrollment-grants-the-saintess-office-to-female-royal-initiates-only-without-uniqueness",
        "saintess-vessel::saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive",
    )
    def test_pre_owned_vessel_enrollment_emits_no_false_grant(self):
        royal = self._set_identity(_royal(), "human_royal")
        royal.db.skills = {"active": [], "passive": [VESSEL_KEY]}
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            record = enroll(royal, self.celebrant)
        self.assertTrue(record["vessel_branch"])
        self.assertFalse(record["vessel_granted"])
        self.assertEqual(record["item"], SAINTESS_VESTMENTS_KEY)
        self.assertEqual(royal.db.skills["passive"], [VESSEL_KEY])
        self.assertEqual(self._events(info), [ENROLL_EVENT], "no false grant event")

    @covers_requirement(
        "church-ordination::enrollment-grants-the-saintess-office-to-female-royal-initiates-only-without-uniqueness"
    )
    def test_the_vessel_trickle_stays_disarmed_before_enrollment(self):
        # A female royal who never enrolled settles byte-identically to a
        # non-holder: no pin, no fluctuation — she only becomes functionally
        # Saintess at her enrollment transaction.
        royal = self._set_identity(_royal(), "human_royal")
        plain = create_object(PlayerCharacter, key="plain non-holder")
        plain.race = "human"
        plain.apply_race_baseline()
        for entity in (royal, plain):
            entity.db.skills = {"active": [], "passive": []}
            entity.sexual.pleasure.base = 20
        def sexual_record(entity):
            return entity.attributes.get(
                "sexual_traits", default={}, category="traits"
            )

        royal_before = sexual_record(royal)
        plain_before = sexual_record(plain)
        clock = WorldClock(tick=0)
        for _ in range(6):
            clock.advance(6, AdvanceSource.SKIP, [royal, plain])
        self.assertEqual(sexual_record(royal), royal_before)
        self.assertEqual(sexual_record(plain), plain_before)
        self.assertEqual(royal.sexual.pleasure.base, 20)
        # A full decay interval crosses to the 平靜 floor exactly like a
        # non-holder (14), never the holder's 15 pin.
        clock.advance(1800, AdvanceSource.SKIP, [royal, plain])
        self.assertEqual(royal.sexual.pleasure.base, plain.sexual.pleasure.base)
        self.assertEqual(royal.sexual.arousal.level, "平靜")


class VestmentHandoverTests(ChurchHostIsolation):
    """The unconditional single-robe handover (design §7, ID 3)."""

    def _ordinary(self, key="ordinary initiate"):
        character = create_object(PlayerCharacter, key=key)
        character.location = self.hall
        character.race = "human"
        character.subrace = "human_plains"
        character.sex = "female"
        character.apply_race_baseline()
        return character

    @covers_requirement(
        "church-ordination::enrollment-hands-over-exactly-one-vestment-unconditionally"
    )
    def test_ordinary_initiate_receives_exactly_one_sister_robe(self):
        initiate = self._ordinary()
        with self.captureOnCommitCallbacks(execute=True):
            record = enroll(initiate, self.celebrant)
        self.assertEqual(record["item"], SISTER_VESTMENTS_KEY)
        self.assertEqual(list(initiate.db.inventory), [SISTER_VESTMENTS_KEY])

    @covers_requirement(
        "church-ordination::enrollment-hands-over-exactly-one-vestment-unconditionally"
    )
    def test_vessel_branch_without_the_robe_receives_exactly_one_saintess_robe(self):
        royal = _royal()
        royal.location = self.hall
        with self.captureOnCommitCallbacks(execute=True):
            record = enroll(royal, self.celebrant)
        self.assertEqual(record["item"], SAINTESS_VESTMENTS_KEY)
        self.assertEqual(list(royal.db.inventory), [SAINTESS_VESTMENTS_KEY])
        self.assertEqual(royal.db.skills["passive"], [VESSEL_KEY])

    @covers_requirement(
        "church-ordination::enrollment-hands-over-exactly-one-vestment-unconditionally"
    )
    def test_initiate_already_carrying_the_key_still_receives_its_one(self):
        initiate = self._ordinary(key="already vested")
        initiate.db.inventory = [SISTER_VESTMENTS_KEY]
        with self.captureOnCommitCallbacks(execute=True):
            enroll(initiate, self.celebrant)
        inventory = list(initiate.db.inventory)
        self.assertEqual(inventory.count(SISTER_VESTMENTS_KEY), 2, inventory)
        self.assertEqual(initiate.db.inventory, [SISTER_VESTMENTS_KEY] * 2)

    @covers_requirement(
        "church-ordination::enrollment-hands-over-exactly-one-vestment-unconditionally"
    )
    def test_a_rolled_back_enrollment_returns_the_robe(self):
        initiate = self._ordinary(key="rollback robe")
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                enroll(initiate, self.celebrant)
                transaction.set_rollback(True)
        self.assertEqual(self._events(info), [])
        self.assertFalse(
            {"inventory", "church", "skills"}
            & self._persisted_attribute_keys(initiate),
            "a rolled-back enrollment returns the robe at the DB level",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()