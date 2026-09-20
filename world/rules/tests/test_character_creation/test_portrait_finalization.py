"""Slice of ``test_character_creation``: PortraitFinalizationTests."""
from tools.spec_traceability import covers_requirement
from copy import deepcopy
import inspect
from inspect import signature
from dataclasses import replace
from unittest.mock import patch
import unittest
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.lore.races import StatModifiers
from world.lore.starting_kits import SubraceStartingKit
from world.lore.sex import DEFAULT_SEX
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    MAX_PERSONA_FIELD_LENGTH,
    PERSONA_IMPORT_CARD_KEYS,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
    preflight_character_creation,
    resolve_preset_values,
    resolve_starting_profile,
)
from world.skills.equipment import EquipmentSlot
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SKILLS,
    SYNTH_SUBRACES,
    StaticBand,
    Vitals,
    _SYNTH_ELEMENT,
    make_element,
    make_item,
    make_race,
    make_preset,
    make_subrace,
    make_skill,
    synthetic_registries,
)
from world.skills.registry import SkillPrerequisite
from world.rules.tests._combat_session_helpers import (
    live_skill_registry,
    open_synthetic_scope,
)

from ._support import (
    _portrait_ensure_callbacks,
    _race_key,
    balanced_allocations,
)


class PortraitFinalizationTests(EvenniaTest):
    """Shared portrait finalization on every activation path
    (fix-creation-finalization-safety D3 / art-asset-lifecycle)."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": next(iter(SYNTH_SUBRACES)),
            "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    def _portrait_key(self):
        return f"art:portrait:character:{self.character.pk}"

    def _gallery_jobs(self):
        from world.art.store import ArtAssetRecord

        return [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_activation_sets_the_named_policy_and_schedules_exactly_one_ensure(self):
        from world.art.store import ArtAssetRecord

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            activate_player_character(
                self.account, self.character, self.request(),
            )
        self.assertEqual(
            self.character.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.character.pk)},
        )
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        # The retrofit: the committed creation owns exactly one gallery job,
        # never a classic fixed-identity record.
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0].db_key.startswith(f"{self._portrait_key()}:gen:"))
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key=self._portrait_key()).count(), 0
        )

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    def test_web_activation_produces_identical_portrait_state(self):
        from web.webclient.actions.creation_actions import (
            _creation_activate_adapter,
            _creation_custom_adapter,
        )
        from world.art.store import ArtAssetRecord

        web = create_object(PlayerCharacter, key="web-shell")
        self.account.at_post_create_character(web)
        web.db_account = self.account
        _creation_custom_adapter(
            web,
            {
                "display_name": "網頁角色",
                "age": 20,
                "apparent_age": 20,
                "race": _race_key(),
                "subrace": next(iter(SYNTH_SUBRACES)),
                "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
                "background": None,
                "affinity_elements": [],
                "persona": None,
            },
        )
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            _creation_activate_adapter(web, {})
        self.assertFalse(web.creation_pending)
        self.assertEqual(
            web.db.portrait_policy,
            {"mode": "named", "stable_key": str(web.pk)},
        )
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        # Same retrofit on the web activation path: one gallery job, no
        # classic fixed-identity record.
        self.assertEqual(len(self._gallery_jobs()), 1)
        self.assertEqual(
            ArtAssetRecord.objects.filter(
                db_key=f"art:portrait:character:{web.pk}"
            ).count(),
            0,
        )

    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    def test_failed_activation_leaves_no_policy_and_no_job(self):
        from world.art.store import ArtAssetRecord
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(self.account, self.character, self.request())

        def fail(stage):
            if stage == "portrait_policy":
                raise RuntimeError("injected portrait failure")

        with self.assertRaisesRegex(RuntimeError, "injected portrait failure"):
            activate_draft(
                self.account, self.character,
                write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("portrait_policy"))
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key=self._portrait_key()).count(),
            0,
        )
        self.assertEqual(self._gallery_jobs(), [])

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_skipped_activation_establishes_the_policy_and_enqueues_nothing(self):
        from world.art import gallery as gallery_api
        from world.art.presenter import PLACEHOLDER_MISSING, resolve_entity
        from world.art.subjects import ArtSubject, ArtSubjectKind

        with self.captureOnCommitCallbacks(execute=True):
            activate_player_character(
                self.account, self.character, self.request(skip_portrait=True),
            )
        # The named policy exists on the skipped path too — the character
        # stays eligible for a later request.
        self.assertEqual(
            self.character.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.character.pk)},
        )
        self.assertEqual(self._gallery_jobs(), [])
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(self.character.pk))
        self.assertEqual(gallery_api.cards_for(subject), [])
        # Empty-gallery resolution reaches the chain's terminal fallback seam
        # (world.art.gallery_match.fallback_for): filled by
        # gallery-builtin-fallbacks, the seam now resolves a committed
        # built-in default for the artless character.
        with patch("world.observability.log_info"):
            payload = resolve_entity(self.character)
        self.assertEqual(payload["kind"], "asset")
        self.assertTrue(payload["url"].startswith("/art/defaults/"))
        with patch(
            "world.art.presenter.fallback_for",
            return_value={"identity": "fallback/character/default.png"},
        ):
            served = resolve_entity(self.character)
        self.assertEqual(served["kind"], "asset")

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_default_activation_still_schedules_one_generation(self):
        with self.captureOnCommitCallbacks(execute=True):
            activate_player_character(
                self.account, self.character, self.request(),
            )
        self.assertEqual(len(self._gallery_jobs()), 1)

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_a_rolled_back_skipped_activation_leaves_nothing(self):
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(
            self.account, self.character, self.request(skip_portrait=True)
        )

        def fail(stage):
            if stage == "portrait_policy":
                raise RuntimeError("injected portrait failure")

        with self.assertRaisesRegex(RuntimeError, "injected portrait failure"):
            activate_draft(self.account, self.character, write_observer=fail)
        self.assertFalse(self.character.attributes.has("portrait_policy"))
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertEqual(self._gallery_jobs(), [])
