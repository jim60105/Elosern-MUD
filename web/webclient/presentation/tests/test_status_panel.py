"""Tests for status panel presentation (webclient-status-presentation)."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.status import STATUS_SCHEMA_VERSION, status_presenter
from world.rules.fatigue import SleepPosture, write_fatigue_state


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
        self.assertEqual(payload["schema_version"], 4)
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

        # Reading twice advances nothing: no fabricated countdown, no wake,
        # and no buff-cache write on either body.
        second = status_presenter(self._context(controlled))
        self.assertEqual(second["fatigue"], payload["fatigue"])
        self.assertEqual(
            (_stored_physiology(owner), _stored_physiology(controlled)), before
        )
