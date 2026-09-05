"""Tests for the version-1 ``roster`` presentation panel (webclient-character-roster)."""

from copy import deepcopy
import unittest
from unittest.mock import PropertyMock, patch

from django.test import override_settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
)
from web.webclient.presentation.registry import (
    UNAVAILABLE_REASON,
    build_production_registry,
)
from web.webclient.presentation.roster import (
    MAX_ROSTER_ROWS,
    ROSTER_LOCK_REASON,
    ROSTER_SCHEMA_VERSION,
    RosterPanelError,
    validate_roster,
)
from world.art.presenter import resolve_character
from world.rules.clock import get_world_clock


class RosterPresenterTests(EvenniaTest):
    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.account.characters.add(self.char1)
        self.registry = build_production_registry()

    def _render(self, actor=None):
        target = self.char1 if actor is None else actor
        context = PresentationContext(actor=target, protocol_version=1)
        return self.registry.render("roster", context)

    @covers_requirement(
        "webclient-character-roster::the-account-roster-is-a-committed-presentation-panel-available-in-every-mode",
        "webclient-character-roster::each-roster-row-reports-only-canonical-owned-character-facts",
    )
    def test_available_form_field_set(self):
        """Available roster payload matches exact schema and field set."""
        payload = self._render()
        self.assertEqual(payload["schema_version"], ROSTER_SCHEMA_VERSION)
        self.assertTrue(payload["available"])
        self.assertEqual(
            set(payload.keys()),
            {
                "schema_version",
                "available",
                "characters",
                "max_characters",
                "can_create",
                "switch_locked",
                "lock_reason",
            },
        )
        self.assertEqual(len(payload["characters"]), 1)
        row = payload["characters"][0]
        self.assertEqual(
            set(row.keys()),
            {"identity", "name", "current", "pending", "portrait"},
        )
        self.assertEqual(row["identity"], int(self.char1.pk))
        self.assertEqual(row["name"], str(self.char1.key))
        self.assertTrue(row["current"])
        self.assertFalse(row["pending"])

        portrait = row["portrait"]
        self.assertEqual(
            set(portrait.keys()),
            {
                "subject_key",
                "status",
                "url",
                "aspect_ratio",
                "alt",
                "placeholder",
            },
        )

    @covers_requirement(
        "webclient-character-roster::the-account-roster-is-a-committed-presentation-panel-available-in-every-mode"
    )
    def test_panel_available_for_creation_pending_actor(self):
        """The roster panel is available when creation_pending is True."""
        self.char1.db.creation_pending = True
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["schema_version"], ROSTER_SCHEMA_VERSION)
        self.assertTrue(payload["characters"][0]["pending"])

    @covers_requirement(
        "webclient-character-roster::the-account-roster-is-a-committed-presentation-panel-available-in-every-mode",
        "webclient-character-roster::the-roster-carries-the-account-s-capacity-and-switch-lock-facts",
    )
    def test_panel_available_in_combat(self):
        """The roster panel is available in combat with switch_locked: True."""
        with patch("world.rules.account_roster.is_in_active_session", return_value=True):
            payload = self._render()
            self.assertTrue(payload["available"])
            self.assertTrue(payload["switch_locked"])
            self.assertEqual(payload["lock_reason"], ROSTER_LOCK_REASON)

    @covers_requirement(
        "webclient-character-roster::the-account-roster-is-a-committed-presentation-panel-available-in-every-mode",
        "webclient-oob-protocol::presenter-registration-and-execution-are-isolated-and-read-only",
    )
    def test_account_roster_error_yields_common_non_internal_unavailable_form(self):
        """An unreadable account yields the common non-internal unavailable form."""
        expected_reason = {
            "code": UNAVAILABLE_REASON[0],
            "message": UNAVAILABLE_REASON[1],
        }

        # 1. Actor is None
        context_none = PresentationContext(actor=None, protocol_version=1)
        payload1 = self.registry.render("roster", context_none)
        self.assertEqual(payload1["schema_version"], ROSTER_SCHEMA_VERSION)
        self.assertFalse(payload1["available"])
        self.assertEqual(payload1["reason"], expected_reason)
        self.assertNotIn("correlation_id", payload1)

        # 2. Actor with no account
        orphan = create.create_object(self.character_typeclass, key="Orphan")
        context_orphan = PresentationContext(actor=orphan, protocol_version=1)
        payload2 = self.registry.render("roster", context_orphan)
        self.assertFalse(payload2["available"])
        self.assertEqual(payload2["reason"], expected_reason)
        self.assertNotIn("correlation_id", payload2)

        # 3. Account characters handler raises
        with patch.object(Account, "characters", new_callable=PropertyMock) as mock_chars:
            mock_chars.side_effect = RuntimeError("DB exploded")
            payload3 = self._render()
            self.assertFalse(payload3["available"])
            self.assertEqual(payload3["reason"], expected_reason)
            self.assertNotIn("correlation_id", payload3)

    @covers_requirement(
        "webclient-character-roster::roster-portraits-resolve-through-the-named-portrait-subject-mechanism"
    )
    def test_portrait_object_shapes(self):
        """Portraits resolve correctly for activated assets, pending assets, and pending shells."""
        char_pending, _ = self.account.create_character(key="PendingSibling")
        char_pending.db.creation_pending = True

        char_active2, _ = self.account.create_character(key="ActiveSecond")
        char_active2.db.creation_pending = False

        # Verify unpatched resolve_character on pending character returns unavailable "無肖像"
        native_pending = resolve_character(char_pending)
        self.assertEqual(native_pending["kind"], "unavailable")
        self.assertEqual(native_pending["label"], "無肖像")

        def mock_resolve(entity):
            if entity.pk == self.char1.pk:
                return {
                    "kind": "asset",
                    "status": "done",
                    "url": f"/art/portraits/character_{self.char1.pk}.png",
                    "aspect_ratio": "3:4",
                    "alt": "完成的肖像",
                    "subject_key": f"character:{self.char1.pk}",
                }
            elif entity.pk == char_active2.pk:
                return {
                    "kind": "missing",
                    "label": "未生成",
                    "status": "pending",
                    "url": None,
                    "aspect_ratio": None,
                    "alt": "未生成",
                    "subject_key": f"character:{char_active2.pk}",
                }
            else:
                return {
                    "kind": "unavailable",
                    "label": "無肖像",
                    "status": None,
                    "url": None,
                    "aspect_ratio": None,
                    "alt": "無肖像",
                    "subject_key": None,
                }

        with patch("web.webclient.presentation.roster.resolve_character", side_effect=mock_resolve):
            payload = self._render()
            rows_by_id = {c["identity"]: c for c in payload["characters"]}

            # 1. Activated with completed asset
            char1_portrait = rows_by_id[int(self.char1.pk)]["portrait"]
            self.assertEqual(char1_portrait["status"], "done")
            self.assertEqual(char1_portrait["url"], f"/art/portraits/character_{self.char1.pk}.png")
            self.assertEqual(char1_portrait["aspect_ratio"], "3:4")
            self.assertIsNone(char1_portrait["placeholder"])

            # 2. Activated with asset pending generation
            active2_portrait = rows_by_id[int(char_active2.pk)]["portrait"]
            self.assertEqual(active2_portrait["status"], "pending")
            self.assertIsNone(active2_portrait["url"])
            self.assertEqual(
                active2_portrait["placeholder"],
                {"kind": "missing", "label": "未生成"},
            )

            # 3. Pending creation shell (no policy)
            pending_portrait = rows_by_id[int(char_pending.pk)]["portrait"]
            self.assertIsNone(pending_portrait["status"])
            self.assertIsNone(pending_portrait["url"])
            self.assertIsNone(pending_portrait["subject_key"])
            self.assertEqual(
                pending_portrait["placeholder"],
                {"kind": "unavailable", "label": "無肖像"},
            )

    @covers_requirement(
        "webclient-character-roster::roster-presentation-is-read-only-and-version-mirrored"
    )
    def test_rendering_leaves_canonical_state_and_clock_untouched(self):
        """Rendering the roster mutates no character attributes and advances no clock ticks."""
        clock = get_world_clock()
        initial_tick = int(clock.tick)

        char2, _ = self.account.create_character(key="HeroTwo")
        attrs_before_1 = set(self.char1.attributes.all())
        attrs_before_2 = set(char2.attributes.all())

        payload = self._render()
        self.assertTrue(payload["available"])

        self.assertEqual(int(clock.tick), initial_tick)
        self.assertEqual(set(self.char1.attributes.all()), attrs_before_1)
        self.assertEqual(set(char2.attributes.all()), attrs_before_2)

    @covers_requirement(
        "webclient-character-roster::the-account-roster-is-a-committed-presentation-panel-available-in-every-mode"
    )
    def test_coordinator_full_snapshot_includes_roster_in_all_modes(self):
        """PresentationCoordinator.full_snapshot delivers roster panel in all modes."""
        class FakeClock:
            year, season_index, season_name = 1204, 1, "初春"
            day_in_season, hour, minute, second = 1, 12, 0, 0

        coordinator = PresentationCoordinator(
            self.session,
            registry=self.registry,
            calendar_provider=lambda: FakeClock(),
        )

        # 1. Exploration mode
        self.char1.db.creation_pending = False
        ctx_exp = PresentationContext(actor=self.char1, protocol_version=1)
        snap_exp = coordinator.full_snapshot(ctx_exp)
        self.assertEqual(snap_exp["mode"], "exploration")
        self.assertIn("roster", snap_exp["panels"])
        self.assertTrue(snap_exp["panels"]["roster"]["available"])

        # 2. Creation mode
        self.char1.db.creation_pending = True
        ctx_creation = PresentationContext(actor=self.char1, protocol_version=1)
        snap_creation = coordinator.full_snapshot(ctx_creation)
        self.assertEqual(snap_creation["mode"], "creation")
        self.assertIn("roster", snap_creation["panels"])
        self.assertTrue(snap_creation["panels"]["roster"]["available"])

        # 3. Combat mode
        self.char1.db.creation_pending = False
        with (
            patch("world.rules.combat_session.is_in_active_session", return_value=True),
            patch("world.rules.account_roster.is_in_active_session", return_value=True),
        ):
            ctx_combat = PresentationContext(actor=self.char1, protocol_version=1)
            snap_combat = coordinator.full_snapshot(ctx_combat)
            self.assertEqual(snap_combat["mode"], "combat")
            self.assertIn("roster", snap_combat["panels"])
            self.assertTrue(snap_combat["panels"]["roster"]["available"])
            self.assertTrue(snap_combat["panels"]["roster"]["switch_locked"])


class RosterValidatorTests(unittest.TestCase):
    def _valid_portrait(self, **overrides):
        portrait = {
            "subject_key": "character:1",
            "status": "done",
            "url": "/art/portraits/character_1.png",
            "aspect_ratio": "3:4",
            "alt": "英雄肖像",
            "placeholder": None,
        }
        portrait.update(overrides)
        return portrait

    def _valid_row(self, identity=1, name="Hero", current=True, pending=False, **overrides):
        row = {
            "identity": identity,
            "name": name,
            "current": current,
            "pending": pending,
            "portrait": self._valid_portrait(),
        }
        row.update(overrides)
        return row

    def _valid_payload(self, **overrides):
        payload = {
            "schema_version": ROSTER_SCHEMA_VERSION,
            "available": True,
            "characters": [self._valid_row()],
            "max_characters": 5,
            "can_create": True,
            "switch_locked": False,
            "lock_reason": None,
        }
        payload.update(overrides)
        return payload

    def test_valid_payload_normalizes_cleanly(self):
        payload = self._valid_payload()
        self.assertEqual(validate_roster(payload), payload)

    def test_one_current_row_invariant_enforced(self):
        """Zero current rows or multiple current rows raise ProtocolValidationError."""
        # Zero current rows
        row0 = self._valid_row(current=False)
        with self.assertRaises(ProtocolValidationError) as ctx0:
            validate_roster(self._valid_payload(characters=[row0]))
        self.assertIn("must contain exactly one current character", str(ctx0.exception))

        # Two current rows
        row1 = self._valid_row(identity=1, current=True)
        row2 = self._valid_row(identity=2, current=True)
        with self.assertRaises(ProtocolValidationError) as ctx2:
            validate_roster(self._valid_payload(characters=[row1, row2]))
        self.assertIn("must contain exactly one current character", str(ctx2.exception))

    def test_reciprocal_lock_reason_invariant_enforced(self):
        """lock_reason must be ROSTER_LOCK_REASON when locked, None when unlocked."""
        # Unlocked with a reason string -> rejected
        with self.assertRaises(ProtocolValidationError):
            validate_roster(self._valid_payload(switch_locked=False, lock_reason=ROSTER_LOCK_REASON))

        # Locked with None reason -> rejected
        with self.assertRaises(ProtocolValidationError):
            validate_roster(self._valid_payload(switch_locked=True, lock_reason=None))

        # Locked with wrong reason string -> rejected
        with self.assertRaises(ProtocolValidationError):
            validate_roster(self._valid_payload(switch_locked=True, lock_reason="其他原因"))

        # Locked with exact ROSTER_LOCK_REASON -> accepted
        valid_locked = self._valid_payload(switch_locked=True, lock_reason=ROSTER_LOCK_REASON)
        self.assertEqual(validate_roster(valid_locked), valid_locked)

    def test_duplicate_character_identity_rejected(self):
        row1 = self._valid_row(identity=1, current=True)
        row2 = self._valid_row(identity=1, current=False)
        with self.assertRaises(ProtocolValidationError) as ctx:
            validate_roster(self._valid_payload(characters=[row1, row2]))
        self.assertIn("strictly ascending", str(ctx.exception))

    def test_non_ascending_character_identities_rejected(self):
        row1 = self._valid_row(identity=2, current=True)
        row2 = self._valid_row(identity=1, current=False)
        with self.assertRaises(ProtocolValidationError) as ctx:
            validate_roster(self._valid_payload(characters=[row1, row2]))
        self.assertIn("strictly ascending", str(ctx.exception))

    def test_invalid_url_rejected(self):
        bad_portrait = self._valid_portrait(url="http://evil.com/pic.png")
        row = self._valid_row(portrait=bad_portrait)
        with self.assertRaises(ProtocolValidationError):
            validate_roster(self._valid_payload(characters=[row]))

    def test_exceeding_max_roster_rows_rejected(self):
        rows = [
            self._valid_row(identity=i, current=(i == 1))
            for i in range(1, MAX_ROSTER_ROWS + 2)
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_roster(self._valid_payload(characters=rows))

    def test_unsupported_schema_version_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_roster(self._valid_payload(schema_version=999))

    def test_unavailable_form_rejected_by_available_validator(self):
        with self.assertRaises(ProtocolValidationError):
            validate_roster({"schema_version": 1, "available": False, "characters": []})

    def test_oversized_payload_rejected(self):
        row = self._valid_row(name="A" * 128)
        row["portrait"]["alt"] = "B" * 512
        payload = self._valid_payload(characters=[row])
        with patch("web.webclient.presentation.roster.json_byte_size", return_value=MAX_CANONICAL_JSON_BYTES + 1):
            with self.assertRaises(ProtocolValidationError) as ctx:
                validate_roster(payload)
            self.assertIn("exceeds the OOB envelope limit", str(ctx.exception))
