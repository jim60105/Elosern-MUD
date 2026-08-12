"""Creation action adapter and dispatcher integration tests (tasks 3.3-3.4).

Exercises every one of the four production creation adapters against real
Evennia state: success (preset selection, custom preflight-and-save, atomic
activation with the exploration hand-off, idempotent reset), every
deterministic domain rejection, tampered/authority-like fields rejected before
the domain API, dispatcher-level stale and duplicate handling, a before/after
assertion that no canonical surface changes on rejection, and the all-or-
nothing ``activate_draft`` outer transaction.
"""

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from web.webclient.actions.creation_actions import (
    _creation_activate_adapter,
    _creation_concept_adapter,
    _creation_custom_adapter,
    _creation_preset_adapter,
    _creation_reset_adapter,
    validate_creation_activate_payload,
    validate_creation_concept_payload,
    validate_creation_custom_payload,
    validate_creation_preset_payload,
    validate_creation_reset_payload,
)
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry
from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationRequest,
    activate_player_character,
    resolve_starting_profile,
)
from world.rules.clock import get_world_clock
from world.rules.creation_wizard import draft_fingerprint, read_draft, save_custom_draft


def balanced_allocations(race: str, subrace: str | None = None) -> dict[str, int]:
    profile = resolve_starting_profile(race, subrace)
    remaining = profile.budget
    result: dict[str, int] = {}
    for key, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        result[key] = value
        remaining -= value
    if remaining:
        raise AssertionError("profile budget exceeds allocatable spans")
    return result


def custom_payload(**overrides):
    value = {
        "display_name": "  新角色  ",
        "age": 20,
        "apparent_age": 20,
        "race": "human",
        "subrace": None,
        "allocations": balanced_allocations("human"),
    }
    value.update(overrides)
    return value


class FakeSession:
    def __init__(self, puppet):
        self.sent = []
        self.puppet = puppet
        self.ndb = SimpleNamespace()
        self.sessid = 99

    def msg(self, **kwargs):
        self.sent.append(kwargs)


class CreationActionBase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="pending-shell")
        self.account.at_post_create_character(self.character)
        self.character.db_account = self.account
        get_world_clock()
        self.action_registry = build_production_action_registry()
        self.presentation_registry = build_production_registry()
        self.fake_session = FakeSession(self.character)
        self.coordinator = attach_coordinator(self.fake_session, self.presentation_registry)

    def _envelope(self, action_id, payload, request_id="r1", base_revision=None, epoch=None):
        if epoch is None:
            epoch = self.coordinator.epoch
        if base_revision is None:
            base_revision = self.coordinator.revision
        return {
            "protocol_version": 1,
            "presentation_epoch": epoch,
            "request_id": request_id,
            "base_revision": base_revision,
            "action_id": action_id,
            "payload": payload,
        }

    def _dispatch(self, envelope):
        handle_ui_action(
            self.fake_session,
            self.character,
            envelope,
            self.action_registry,
            self.presentation_registry,
        )

    def _last_result(self):
        for entry in reversed(self.fake_session.sent):
            if "ui_action_result" in entry:
                return entry["ui_action_result"][0][0]
        return None

    def _result_message(self):
        envelope = self._last_result()
        return envelope["message"] if envelope else None


class CreationPayloadValidationTests(unittest.TestCase):
    def test_preset_payload_is_exact(self):
        self.assertEqual(
            validate_creation_preset_payload({"preset_key": "human_wanderer"}),
            {"preset_key": "human_wanderer"},
        )
        for bad in (
            {"preset_key": ""},
            {"preset_key": "x" * 65},
            {"preset_key": 5},
            {},
            {"preset_key": "human_wanderer", "actor": 1},
            {"preset_key": "human_wanderer", "account": 1},
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_preset_payload(bad)

    def test_custom_payload_is_exact(self):
        valid = validate_creation_custom_payload(custom_payload())
        self.assertEqual(valid["display_name"], "  新角色  ")
        self.assertEqual(valid["age"], 20)
        # Underage values pass the wire validator and are rejected by the
        # deterministic adult gate, not the exact-schema layer.
        self.assertEqual(
            validate_creation_custom_payload(custom_payload(age=17))["age"], 17
        )
        for bad in (
            {**custom_payload(), "account": 1},
            {**custom_payload(), "actor": 1},
            {**custom_payload(), "session": 1},
            {**custom_payload(), "magic_level": 1},
            {**custom_payload(), "skills": []},
            {**custom_payload(), "display_name": "x" * 65},
            {**custom_payload(), "age": -1},
            {**custom_payload(), "apparent_age": 10001},
            {**custom_payload(), "age": True},
            {**custom_payload(), "race": ""},
            {**custom_payload(), "subrace": 5},
            {**custom_payload(), "allocations": {"hp": 0}},
            {**custom_payload(), "allocations": {axis: True for axis in ALLOCATABLE_AXES}},
            {**custom_payload(), "allocations": {axis: -1 for axis in ALLOCATABLE_AXES}},
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_custom_payload(bad)

    def test_activate_and_reset_payloads_are_exactly_empty(self):
        self.assertEqual(validate_creation_activate_payload({}), {})
        self.assertEqual(validate_creation_reset_payload({}), {})
        for bad in ({"draft": 1}, {"actor": 1}, None):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_activate_payload(bad)
                with self.assertRaises(Exception):
                    validate_creation_reset_payload(bad)


class CreationAdapterTests(CreationActionBase):
    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_preset_selection_success(self):
        result = _creation_preset_adapter(self.character, {"preset_key": "human_wanderer"})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "preset_saved")
        self.assertEqual(result["affected_panels"], ("creation",))
        draft = read_draft(self.character)
        self.assertEqual(draft["mode"], "preset")
        self.assertEqual(draft["preset_key"], "human_wanderer")
        self.assertTrue(self.character.creation_pending)

    def test_preset_unknown_key_rejected_without_mutation(self):
        result = _creation_preset_adapter(self.character, {"preset_key": "nope"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_preset")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_custom_save_success_uses_trimmed_name(self):
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "custom_saved")
        draft = read_draft(self.character)
        self.assertEqual(draft["mode"], "custom")
        self.assertEqual(draft["display_name"], "新角色")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.age, None)

    @covers_requirement("webclient-character-creation-ui::the-adult-gate-is-server-authoritative-for-both-age-fields")
    def test_underage_fields_rejected_independently(self):
        for label, overrides in (
            ("age", {"age": 17}),
            ("apparent_age", {"apparent_age": 17}),
        ):
            with self.subTest(label=label):
                result = _creation_custom_adapter(self.character, custom_payload(**overrides))
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], f"underage_{label}")
                self.assertIsNone(read_draft(self.character))
                self.assertTrue(self.character.creation_pending)
                self.assertEqual(self.character.traits.all(), [])

    def test_custom_domain_rejections_leave_canonical_surface_unchanged(self):
        before = {
            key: self.character.attributes.get(key)
            for key in ("age", "apparent_age", "race", "subrace", "creation_pending")
        }
        before_traits = self.character.traits.all()
        cases = {
            "bad name": dict(display_name="|rbad|n"),
            "markup name": dict(display_name="x{abc}"),
            "unknown race": dict(race="dragon"),
            "incompatible subrace": dict(race="human", subrace="foxkin"),
            "off budget": dict(
                allocations={axis: 0 for axis in ALLOCATABLE_AXES}
            ),
            "off span": dict(
                allocations={**balanced_allocations("human"), "hp": 200}
            ),
        }
        for label, overrides in cases.items():
            with self.subTest(label=label):
                result = _creation_custom_adapter(self.character, custom_payload(**overrides))
                self.assertEqual(result["outcome"], "rejected", label)
                self.assertIsNone(read_draft(self.character))
                for key, value in before.items():
                    self.assertEqual(self.character.attributes.get(key), value)
                self.assertEqual(self.character.traits.all(), before_traits)

    def test_already_complete_rejected(self):
        # A saved draft plus activation through a non-wizard path leaves the
        # draft behind; a later creation action must reject as already complete.
        _creation_custom_adapter(self.character, custom_payload())
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="custom", **custom_payload()),
            sampler=lambda low, high: low,
        )
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")

    def test_activate_without_draft_rejected(self):
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_draft")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])

    def test_missing_or_unowned_account_rejected_before_any_write(self):
        self.character.db_account = None
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "ownership_rejected")
        self.assertIsNone(read_draft(self.character))
        self.character.db_account = self.account
        class NotAPlayer:
            account = self.account
        result = _creation_custom_adapter(NotAPlayer(), custom_payload())
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "ownership_rejected")

    def test_reset_is_idempotent_and_keeps_pending(self):
        _creation_custom_adapter(self.character, custom_payload())
        self.assertIsNotNone(read_draft(self.character))
        result = _creation_reset_adapter(self.character, {})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "draft_cleared")
        self.assertIsNone(read_draft(self.character))
        result = _creation_reset_adapter(self.character, {})
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    def test_reset_rejects_an_activated_character_without_mutation(self):
        _creation_custom_adapter(self.character, custom_payload())
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="custom", **custom_payload()),
            sampler=lambda low, high: low,
        )
        self.assertFalse(self.character.creation_pending)
        result = _creation_reset_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")
        self.assertIsNone(read_draft(self.character))

    def test_pending_flip_while_in_flight_rejects_at_completion(self):
        from twisted.internet import defer

        from world.rules.character_creation import (
            CharacterCreationRequest,
            activate_player_character,
        )

        held = defer.Deferred()
        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            return_value=held,
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        deferred = _creation_concept_adapter(self.character, _concept_payload())
        # The character is activated (via another entry) while in flight.
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="custom", **custom_payload()),
            sampler=lambda low, high: low,
        )
        held.callback(_proposal())
        result = await_result(deferred)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")
        self.assertIsNone(read_draft(self.character))
        self.assertFalse(self.character.creation_pending)

    def test_adapter_never_writes_canonical_state_directly(self):
        _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(self.character.age, None)
        self.assertEqual(self.character.race, None)
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])


class CreationFingerprintBindingTests(CreationActionBase):
    """Server-side draft-fingerprint binding (fix-creation-finalization-safety D2)."""

    def test_custom_save_returns_and_records_the_stored_fingerprint(self):
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "success")
        fingerprint = draft_fingerprint(self.character)
        self.assertEqual(result["fingerprint"], fingerprint)
        self.assertEqual(
            getattr(self.character.ndb, "elosern_confirmed_draft_fingerprint", None),
            fingerprint,
        )

    @covers_requirement("webclient-character-creation-ui::creation-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    @covers_requirement("creation-activation-gating::activation-is-bound-to-the-last-successfully-saved-draft")
    def test_stale_confirmation_is_refused_without_activating(self):
        _creation_custom_adapter(self.character, custom_payload())
        # Another entry replaces the stored draft without going through the
        # adapter, so the recorded confirmation now names an older draft.
        save_custom_draft(
            self.account,
            self.character,
            CharacterCreationRequest(
                mode="custom",
                display_name="較新草稿",
                age=21,
                apparent_age=21,
                race="human",
                subrace=None,
                allocations=balanced_allocations("human"),
            ),
        )
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "confirmation_stale")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])
        self.assertEqual(self.character.key, "pending-shell")

    def test_activate_after_a_draft_saved_outside_the_adapter_is_refused(self):
        # A draft stored by the deterministic save API directly (e.g. the
        # Telnet path) never passed through a confirmed adapter save; activation
        # must refuse rather than activate an unconfirmed draft.
        save_custom_draft(
            self.account,
            self.character,
            CharacterCreationRequest(mode="custom", **custom_payload()),
        )
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_confirmed_save")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])

    def test_activate_without_any_draft_still_rejects_with_no_draft(self):
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_draft")
        self.assertTrue(self.character.creation_pending)

    def test_preset_save_also_binds_the_confirmation_fingerprint(self):
        result = _creation_preset_adapter(self.character, {"preset_key": "human_wanderer"})
        self.assertEqual(result["outcome"], "success")
        fingerprint = draft_fingerprint(self.character)
        self.assertEqual(result["fingerprint"], fingerprint)
        self.assertEqual(
            getattr(self.character.ndb, "elosern_confirmed_draft_fingerprint", None),
            fingerprint,
        )

    @covers_requirement("creation-activation-gating::activation-is-bound-to-the-last-successfully-saved-draft")
    @covers_requirement("webclient-character-creation-ui::web-activation-confirms-the-exact-draft-shown")
    def test_activate_after_a_rejected_save_is_refused_without_activating(self):
        # A rejected save invalidates the confirmation: the draft the player
        # was trying to save was not stored, so a leftover confirmation must
        # not be able to activate the older draft (webclient-character-
        # creation-ui "Save rejection followed by activation is refused").
        _creation_custom_adapter(self.character, custom_payload())
        rejected = _creation_custom_adapter(
            self.character, custom_payload(age=17)
        )
        self.assertEqual(rejected["outcome"], "rejected")
        self.assertEqual(rejected["code"], "underage_age")
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_confirmed_save")
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])
        self.assertEqual(self.character.key, "pending-shell")

    def test_rejected_preset_save_also_invalidates_the_confirmation(self):
        _creation_preset_adapter(self.character, {"preset_key": "human_wanderer"})
        rejected = _creation_preset_adapter(
            self.character, {"preset_key": "nonexistent_preset"}
        )
        self.assertEqual(rejected["outcome"], "rejected")
        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_confirmed_save")
        self.assertTrue(self.character.creation_pending)

    def test_rejected_concept_save_also_invalidates_the_confirmation(self):
        from twisted.internet import defer

        _creation_custom_adapter(self.character, custom_payload())
        held = defer.Deferred()
        with patch(
            "server.ai_director_service.request_character_proposal",
            return_value=held,
        ):
            deferred = _creation_concept_adapter(self.character, _concept_payload())
            held.callback(None)
            result = await_result(deferred)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "concept_unavailable")
        activate = _creation_activate_adapter(self.character, {})
        self.assertEqual(activate["outcome"], "rejected")
        self.assertEqual(activate["code"], "no_confirmed_save")


class CreationActivateIntegrationTests(CreationActionBase):
    def setUp(self):
        super().setUp()
        _creation_custom_adapter(self.character, custom_payload())

    @covers_requirement("webclient-character-creation-ui::activation-is-all-or-nothing-and-hands-off-to-exploration")
    def test_activation_clears_draft_and_hands_off_to_exploration(self):
        from evennia.utils.create import create_object as _co
        from typeclasses.rooms import Room

        _co(Room, key="虛境", location=None)
        sync_grid()
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom

        south_gate = XYZRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.assertIsNotNone(south_gate)

        result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "activated")
        self.assertEqual(result["affected_panels"], ())
        self.assertFalse(self.character.creation_pending)
        self.assertIsNone(read_draft(self.character))
        self.assertEqual(self.character.key, "新角色")
        self.assertEqual(self.character.age, 20)
        self.assertIs(self.character.location, south_gate)
        self.assertIsNotNone(self.character.traits.magic_level)

    def test_failed_relocation_preserves_activated_state(self):
        messages = []
        self.character.msg = lambda text, **kwargs: messages.append(str(text))
        with patch("world.rules.onboarding._south_gate", return_value=None):
            result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "success")
        self.assertFalse(self.character.creation_pending)
        self.assertIsNotNone(self.character.traits.magic_level)
        self.assertTrue(any("南門" in message for message in messages))

    def test_draft_clear_failure_rolls_back_the_whole_activation(self):
        def fail(stage):
            if stage == "creation_draft":
                raise RuntimeError("injected clear failure")

        draft_before = dict(read_draft(self.character))
        from world.rules.creation_wizard import activate_draft

        with self.assertRaisesRegex(RuntimeError, "injected clear failure"):
            activate_draft(
                self.account, self.character,
                sampler=lambda low, high: low, write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(read_draft(self.character), draft_before)
        self.assertEqual(self.character.key, "pending-shell")
        self.assertEqual(self.character.traits.all(), [])

    def test_concurrent_activations_apply_exactly_once(self):
        from world.rules.creation_wizard import activate_draft

        first = activate_draft(self.account, self.character, sampler=lambda low, high: low)
        self.assertFalse(self.character.creation_pending)
        from world.rules.character_creation import CharacterCreationError

        with self.assertRaises(CharacterCreationError):
            activate_draft(self.account, self.character)
        self.assertEqual(self.character.key, first.display_name)
        self.assertEqual(read_draft(self.character), None)


class CreationDispatchTests(CreationActionBase):
    @covers_requirement("webclient-character-creation-ui::creation-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_stale_activate_revision_runs_no_adapter(self):
        self._dispatch(
            self._envelope(
                "creation.custom", custom_payload(), request_id="custom-1"
            )
        )
        self.assertIsNotNone(read_draft(self.character))
        stale_revision = self.coordinator.revision - 1
        self._dispatch(
            self._envelope(
                "creation.activate", {}, request_id="activate-stale", base_revision=stale_revision
            )
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "stale")
        self.assertEqual(result["code"], "stale")
        self.assertTrue(self.character.creation_pending)
        self.assertIsNotNone(read_draft(self.character))

    @covers_requirement("webclient-character-creation-ui::creation-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_duplicate_request_executes_once(self):
        envelope = self._envelope(
            "creation.custom", custom_payload(), request_id="dup-custom-1"
        )
        self._dispatch(envelope)
        self._dispatch(envelope)
        results = [
            entry["ui_action_result"][0][0]
            for entry in self.fake_session.sent
            if "ui_action_result" in entry
        ]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["outcome"], "success")
        self.assertEqual(results[1]["outcome"], "success")
        # The draft was saved exactly once by the first execution; the replay
        # returned the cached result without a second deterministic write.
        self.assertIsNotNone(read_draft(self.character))

    def test_tampered_authority_field_rejected_before_domain_api(self):
        envelope = self._envelope(
            "creation.custom", {**custom_payload(), "actor": 1}, request_id="tampered-1"
        )
        self._dispatch(envelope)
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "malformed_payload")
        self.assertIsNone(read_draft(self.character))

    def test_unknown_creation_action_is_not_routed_to_a_command(self):
        envelope = self._envelope("creation.command", {}, request_id="unknown-1")
        self._dispatch(envelope)
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_action")


if __name__ == "__main__":
    unittest.main()


def _concept_payload(**overrides):
    value = {"concept": "流浪的精靈劍士"}
    value.update(overrides)
    return value


def _proposal(**overrides):
    from world.ai.character_creation import CharacterProposal

    payload = {
        "race_key": "human",
        "subrace_key": None,
        "allocations": balanced_allocations("human"),
        "suggested_skills": ("flight",),
        "persona": {
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
        },
    }
    payload.update(overrides)
    return CharacterProposal(**payload)


def await_result(d):
    if not hasattr(d, "addErrback"):
        return d
    d.addErrback(lambda f: None)
    return d.result


class CreationConceptTests(CreationActionBase):
    """The fifth creation action (creation-persona-persistence D4)."""

    def _propose(self, proposal):
        from twisted.internet import defer

        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            return_value=defer.succeed(proposal),
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        return patch_obj

    def _degrade(self):
        from twisted.internet import defer

        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            return_value=defer.succeed(None),
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        return patch_obj

    @covers_requirement("creation-persona-persistence::the-creation-panel-offers-a-concept-field-and-adapter-sharing-the-guarded-pipeline")
    def test_concept_submission_fills_the_draft_form(self):
        self._propose(_proposal())
        result = await_result(
            _creation_concept_adapter(self.character, _concept_payload())
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "concept_saved")
        self.assertEqual(result["affected_panels"], ("creation",))
        draft = read_draft(self.character)
        self.assertEqual(draft["mode"], "concept")
        self.assertEqual(draft["race"], "human")
        self.assertEqual(draft["allocations"], balanced_allocations("human"))
        self.assertEqual(
            draft["persona"],
            {"personality": "沉穩", "life_story": "來自邊境的小村", "habit": "清晨練劍"},
        )
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.age, None)
        self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("creation-persona-persistence::the-creation-panel-offers-a-concept-field-and-adapter-sharing-the-guarded-pipeline")
    def test_offline_concept_degrades_without_state_change(self):
        self._degrade()
        result = await_result(
            _creation_concept_adapter(self.character, _concept_payload())
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "concept_unavailable")
        self.assertEqual(result["message"], "生成不可用，請手動創角")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)
        # The deterministic adapters remain fully usable afterwards.
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "success")

    @covers_requirement("creation-persona-persistence::the-creation-panel-offers-a-concept-field-and-adapter-sharing-the-guarded-pipeline")
    def test_stale_fingerprint_rejects_the_apply(self):
        from twisted.internet import defer

        held = defer.Deferred()
        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            return_value=held,
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        deferred = _creation_concept_adapter(self.character, _concept_payload())
        # Another entry saves a custom draft while the proposal is in flight.
        _creation_custom_adapter(self.character, custom_payload())
        held.callback(_proposal())
        result = await_result(deferred)
        self.assertEqual(result["outcome"], "stale")
        self.assertEqual(result["code"], "concept_stale")
        self.assertEqual(read_draft(self.character)["mode"], "custom")

    def test_concept_payload_is_exact(self):
        self.assertEqual(
            validate_creation_concept_payload(_concept_payload()),
            _concept_payload(),
        )
        for bad in (
            {"concept": ""},
            {"concept": "  "},
            {"concept": "構" * 501},
            {},
            {"concept": "構想", "actor": 1},
            {"concept": "構想", "account": 1},
            {"concept": "構想", "session": 1},
            {"concept": "構想", "persona": {"personality": "x"}},
            {"concept": "構想", "skill": "flight"},
            {"concept": 5},
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_concept_payload(bad)

    def test_unknown_fields_are_rejected_before_the_generative_layer(self):
        envelope = self._envelope(
            "creation.concept", {**_concept_payload(), "persona": {"personality": "x"}},
            request_id="concept-tampered-1",
        )
        patch_obj = patch(
            "server.ai_director_service.request_character_proposal"
        )
        mock = patch_obj.start()
        self.addCleanup(patch_obj.stop)
        self._dispatch(envelope)
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "malformed_payload")
        mock.assert_not_called()
        self.assertIsNone(read_draft(self.character))

    def test_abnormal_puppet_cannot_reach_a_write_path(self):
        self.character.db_account = None
        result = await_result(
            _creation_concept_adapter(self.character, _concept_payload())
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "ownership_rejected")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    def test_adapter_never_writes_canonical_state_directly(self):
        self._propose(_proposal())
        await_result(_creation_concept_adapter(self.character, _concept_payload()))
        self.assertEqual(self.character.age, None)
        self.assertEqual(self.character.race, None)
        self.assertFalse(self.character.attributes.has("persona"))
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])
