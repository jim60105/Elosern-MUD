"""Tests for status panel presentation (webclient-status-presentation)."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from unittest.mock import patch

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.status import STATUS_SCHEMA_VERSION, status_presenter
from world.rules.fatigue import SleepPosture, write_fatigue_state
from world.rules.party import join_party
from world.rules.possession import enter_possession


def _stored_physiology(entity):
    """The persisted physiology and buff cache, for a no-write assertion."""
    return (
        entity.attributes.get("mental_reserve_units"),
        entity.attributes.get("sleep_posture"),
        dict(entity.attributes.get("buffs", default={}) or {}),
    )


class StatusPanelPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.player = create_object(
            PlayerCharacter,
            key="StatusActor",
            location=self.room1,
        )
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.save()
        self.registry = build_production_registry()

    def _context(self, actor=None):
        return PresentationContext(actor or self.player, 1)

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_status_panel_renders_zero_maximum_gauge_verbatim(self):
        traits = dict(self.player.attributes.get("traits", category="traits"))
        traits["mp"] = {"base": 0, "mod": 0, "mult": 1, "current": 0}
        self.player.attributes.add("traits", traits, category="traits")

        context = self._context()
        payload = status_presenter(context)
        self.assertEqual(payload["schema_version"], STATUS_SCHEMA_VERSION)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["resources"]["mp"], {"current": 0, "maximum": 0})

        # Also confirm rendering through registry produces an available payload
        rendered = self.registry.render("status", context)
        self.assertEqual(rendered["schema_version"], STATUS_SCHEMA_VERSION)
        self.assertTrue(rendered["available"])
        self.assertEqual(rendered["resources"]["mp"], {"current": 0, "maximum": 0})

    def test_status_panel_negative_and_nonzero_on_zero_maximum_fail_closed(self):
        traits = dict(self.player.attributes.get("traits", category="traits"))
        # (b1) negative computed maximum
        traits["mp"] = {"base": -5, "mod": 0, "mult": 1, "current": 0}
        self.player.attributes.add("traits", traits, category="traits")
        rendered = self.registry.render("status", self._context())
        self.assertEqual(rendered["schema_version"], STATUS_SCHEMA_VERSION)
        self.assertFalse(rendered["available"])
        self.assertEqual(rendered["reason"]["code"], "presentation_unavailable")

        # (b2) nonzero current on zero maximum
        traits["mp"] = {"base": 0, "mod": 0, "mult": 1, "current": 10}
        self.player.attributes.add("traits", traits, category="traits")
        rendered = self.registry.render("status", self._context())
        self.assertEqual(rendered["schema_version"], STATUS_SCHEMA_VERSION)
        self.assertFalse(rendered["available"])
        self.assertEqual(rendered["reason"]["code"], "presentation_unavailable")

    @covers_requirement(
        "webclient-status-presentation::fatigue-presentation-identifies-its-physiological-subject"
    )
    def test_possession_identifies_both_physiological_subjects_without_writes(self):
        owner = self.player
        controlled = create_object(
            PlayerCharacter, key="相伴者", location=self.room1
        )
        controlled.race = "human"
        controlled.apply_race_baseline()
        write_fatigue_state(owner, 288000, SleepPosture.AWAKE)
        write_fatigue_state(controlled, 7200, SleepPosture.FORCED)
        controlled.db.possessed_by = owner.pk
        before = (_stored_physiology(owner), _stored_physiology(controlled))

        payload = status_presenter(self._context(controlled))
        self.assertEqual(payload["schema_version"], 5)
        # Resources stay owner-keyed; the actor identity names the controlled
        # body, so no owner gauge can be relabelled as the companion's truth.
        self.assertEqual(payload["actor"]["identity"], str(controlled.pk))
        self.assertEqual(
            payload["resources"]["hp"]["current"], int(owner.traits.hp.current)
        )
        rows = {row["identity"]: row for row in payload["fatigue"]}
        self.assertEqual(set(rows), {str(owner.pk), str(controlled.pk)})
        self.assertEqual(rows[str(owner.pk)]["reserve_percent"], 80)
        self.assertEqual(rows[str(owner.pk)]["stage"], "normal")
        self.assertIsNone(rows[str(owner.pk)]["restriction"])
        self.assertEqual(rows[str(controlled.pk)]["reserve_percent"], 2)
        self.assertEqual(rows[str(controlled.pk)]["stage"], "forced_sleep")
        self.assertEqual(rows[str(controlled.pk)]["severity"], "critical")
        self.assertIsNotNone(rows[str(controlled.pk)]["restriction"])
        self.assertIs(rows[str(owner.pk)]["asleep"], False)
        self.assertIs(rows[str(controlled.pk)]["asleep"], True)

        # Reading twice advances nothing: no fabricated countdown, no wake,
        # and no buff-cache write on either body.
        second = status_presenter(self._context(controlled))
        self.assertEqual(second["fatigue"], payload["fatigue"])
        self.assertEqual(
            (_stored_physiology(owner), _stored_physiology(controlled)), before
        )


class StatusPanelPresentTravellerTests(EvenniaTest):
    """Version 5: one body-keyed row per source-present traveller."""

    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        write_fatigue_state(self.char1, 288000, SleepPosture.AWAKE)
        self.resting = self._companion("合成甲", 180000, SleepPosture.VOLUNTARY)
        self.collapsed = self._companion("合成乙", 3600, SleepPosture.FORCED)

    def _companion(self, key, units, posture, location=None):
        npc = create_object(NPC, key=key, location=self.room1)
        join_party(npc, self.char1)
        write_fatigue_state(npc, units, posture)
        if location is not None:
            # A bound member elsewhere does not travel with the party.
            npc.location = location
        return npc

    def _rows(self, actor):
        payload = status_presenter(PresentationContext(actor, 1))
        self.assertEqual(payload["schema_version"], STATUS_SCHEMA_VERSION)
        return payload, payload["fatigue"]

    @covers_requirement(
        "webclient-status-presentation::compact-status-reports-canonical-true-resources"
    )
    def test_each_present_traveller_has_its_own_asleep_row(self):
        remote = self._companion("合成丙", 360000, SleepPosture.AWAKE, location=self.room2)
        before = [_stored_physiology(body) for body in (self.char1, self.resting, self.collapsed, remote)]
        _payload, rows = self._rows(self.char1)
        # The status source first, then the present companions in scope
        # order; the remote member travels with nobody and has no row.
        self.assertEqual(
            [row["identity"] for row in rows],
            [str(self.char1.pk), str(self.resting.pk), str(self.collapsed.pk)],
        )
        by_id = {row["identity"]: row for row in rows}
        self.assertEqual(
            (by_id[str(self.char1.pk)]["asleep"], by_id[str(self.char1.pk)]["reserve_percent"]),
            (False, 80),
        )
        # Voluntary and forced sleep are both asleep, each with its own
        # reserve and its own stage.
        self.assertEqual(
            (by_id[str(self.resting.pk)]["asleep"], by_id[str(self.resting.pk)]["stage"]),
            (True, "sleeping"),
        )
        self.assertEqual(by_id[str(self.resting.pk)]["reserve_percent"], 50)
        self.assertEqual(
            (by_id[str(self.collapsed.pk)]["asleep"], by_id[str(self.collapsed.pk)]["stage"]),
            (True, "forced_sleep"),
        )
        self.assertEqual(by_id[str(self.collapsed.pk)]["reserve_percent"], 1)
        # A read materializes nothing on any body.
        self._rows(self.char1)
        self.assertEqual(
            [_stored_physiology(body) for body in (self.char1, self.resting, self.collapsed, remote)],
            before,
        )

    @covers_requirement(
        "webclient-status-presentation::fatigue-presentation-identifies-its-physiological-subject"
    )
    def test_possession_keeps_rows_body_keyed_without_duplicates(self):
        enter_possession(self.char1, self.resting)
        payload, rows = self._rows(self.resting)
        identities = [row["identity"] for row in rows]
        # Owner (status source), the controlled body, then the other present
        # companion: every body exactly once, none relabelled.
        self.assertEqual(
            identities,
            [str(self.char1.pk), str(self.resting.pk), str(self.collapsed.pk)],
        )
        by_id = {row["identity"]: row for row in rows}
        self.assertEqual(by_id[str(self.char1.pk)]["reserve_percent"], 80)
        self.assertIs(by_id[str(self.char1.pk)]["asleep"], False)
        self.assertEqual(by_id[str(self.resting.pk)]["reserve_percent"], 50)
        self.assertIs(by_id[str(self.resting.pk)]["asleep"], True)
        # The resources stay owner-keyed under possession.
        self.assertEqual(payload["resources"]["hp"]["current"], int(self.char1.traits.hp.current))

    def test_unreadable_or_unbuilt_companion_physiology_has_no_row(self):
        self.collapsed.attributes.remove("mental_reserve_units")
        self.collapsed.attributes.remove("sleep_posture")
        self.resting.attributes.add("sleep_posture", "dozing")
        payload, rows = self._rows(self.char1)
        self.assertTrue(payload["available"])
        self.assertEqual([row["identity"] for row in rows], [str(self.char1.pk)])
        # Nothing was constructed for the never-built body.
        self.assertFalse(self.collapsed.attributes.has("mental_reserve_units"))

    def test_row_bound_trims_only_the_optional_tail(self):
        from world.rules.status_query import build_fatigue_subject

        companion_row = build_fatigue_subject(self.resting)
        many = tuple(
            companion_row.__class__(**{**companion_row.__dict__, "identity": str(9000 + n)})
            for n in range(12)
        )
        with patch("web.webclient.presentation.status.present_fatigue_subjects", return_value=many):
            _payload, rows = self._rows(self.char1)
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]["identity"], str(self.char1.pk))
