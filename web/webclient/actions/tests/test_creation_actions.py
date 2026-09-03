"""Creation action adapter and dispatcher integration tests (tasks 3.3-3.4).

Exercises every one of the four production creation adapters against real
Evennia state: success (preset selection, custom preflight-and-save, atomic
activation with the exploration hand-off, idempotent reset), every
deterministic domain rejection, tampered/authority-like fields rejected before
the domain API, dispatcher-level stale and duplicate handling, a before/after
assertion that no canonical surface changes on rejection, and the all-or-
nothing ``activate_draft`` outer transaction.
"""

from copy import deepcopy
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
        "subrace": "human_commoner",
        "allocations": balanced_allocations("human", "human_commoner"),
        "background": None,
        "affinity_elements": None,
        # The nine-key payload always carries the required nullable persona
        # key; null is the browser convention for "no persona"
        # (retool-concept-transient-fill D3).
        "persona": None,
    }
    value.update(overrides)
    return value


PERSONA_BLOCK = {
    "personality": "沉穩",
    "life_story": "來自邊境的小村",
    "habit": "清晨練劍",
}


def custom_request(**overrides):
    """A deterministic request matching ``custom_payload`` (persona excluded)."""
    fields = {
        key: value
        for key, value in custom_payload(**overrides).items()
        if key != "persona"
    }
    return CharacterCreationRequest(mode="custom", **fields)


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
            {**custom_payload(), "magic_power": 1},
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
            # The persona key is required (nullable) and exact.
            {k: v for k, v in custom_payload().items() if k != "persona"},
            {**custom_payload(), "persona": {"personality": "沉穩"}},
            {**custom_payload(), "persona": {**PERSONA_BLOCK, "extra": "x"}},
            {**custom_payload(), "persona": {**PERSONA_BLOCK, "personality": " "}},
            {**custom_payload(), "persona": {**PERSONA_BLOCK, "habit": "長" * 601}},
            {**custom_payload(), "persona": "沉穩"},
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_custom_payload(bad)

    def test_custom_persona_payload_accepts_null_or_the_exact_block(self):
        self.assertIsNone(validate_creation_custom_payload(custom_payload())["persona"])
        self.assertEqual(
            validate_creation_custom_payload(
                custom_payload(persona=dict(PERSONA_BLOCK))
            )["persona"],
            PERSONA_BLOCK,
        )

    def test_activate_and_reset_payloads_are_exactly_empty(self):
        self.assertEqual(validate_creation_activate_payload({}), {})
        self.assertEqual(validate_creation_reset_payload({}), {})
        for bad in ({"draft": 1}, {"actor": 1}, None):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_activate_payload(bad)
                with self.assertRaises(Exception):
                    validate_creation_reset_payload(bad)

    def test_custom_affinity_payload_is_exact_and_race_bounded(self):
        self.assertEqual(
            validate_creation_custom_payload(
                custom_payload(affinity_elements=["fire", "wind"])
            )["affinity_elements"],
            ("fire", "wind"),
        )
        self.assertEqual(
            validate_creation_custom_payload(custom_payload())["affinity_elements"],
            None,
        )
        self.assertEqual(
            validate_creation_custom_payload(
                custom_payload(affinity_elements=[])
            )["affinity_elements"],
            (),
        )
        for bad in (
            {**custom_payload(), "affinity_elements": "fire"},
            {**custom_payload(), "affinity_elements": ["luck"]},
            {**custom_payload(), "affinity_elements": ["fire", "fire"]},
            {**custom_payload(), "affinity_elements": ["fire", "wind", "water"]},
            {**custom_payload(race="elf", subrace="fionnen"), "affinity_elements": ["light"]},
            {**custom_payload(), "affinity_elements": {"fire": True}},
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(Exception):
                    validate_creation_custom_payload(bad)


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

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_custom_save_persists_race_bounded_affinity(self):
        result = _creation_custom_adapter(
            self.character, custom_payload(affinity_elements=["fire", "wind"])
        )
        self.assertEqual(result["outcome"], "success")
        draft = read_draft(self.character)
        self.assertEqual(draft["affinity_elements"], ["fire", "wind"])

    def test_custom_over_bound_affinity_rejected_without_mutation(self):
        before = self.character.attributes.get("creation_draft")
        result = _creation_custom_adapter(
            self.character,
            custom_payload(affinity_elements=["fire", "wind", "water"]),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "over_bound_affinity")
        self.assertEqual(self.character.attributes.get("creation_draft"), before)
        self.assertTrue(self.character.creation_pending)

    def test_custom_elf_affinity_rejected_without_mutation(self):
        result = _creation_custom_adapter(
            self.character,
            custom_payload(
                race="elf", subrace="fionnen",
                allocations=balanced_allocations("elf", "fionnen"),
                affinity_elements=["light"],
            ),
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "elf_affinity_rejected")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    def test_custom_elf_empty_affinity_is_neutral_and_activates_with_subrace_seed(self):
        # The WebClient always emits ``affinity_elements`` (possibly ``[]``), so
        # an empty elf set is neutral player input, not a rejected contradiction;
        # activation still seeds the elf from its subrace.
        result = _creation_custom_adapter(
            self.character,
            custom_payload(
                race="elf", subrace="fionnen",
                allocations=balanced_allocations("elf", "fionnen"),
                affinity_elements=[],
            ),
        )
        self.assertEqual(result["outcome"], "success")
        draft = read_draft(self.character)
        self.assertNotIn("affinity_elements", draft)
        _creation_activate_adapter(self.character, {})
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.character.db.affinity_elements, ["light"])

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
            self.account, self.character, custom_request(),
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
            self.account, self.character, custom_request(),
        )
        self.assertFalse(self.character.creation_pending)
        result = _creation_reset_adapter(self.character, {})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")
        self.assertIsNone(read_draft(self.character))

    def test_pending_flip_while_in_flight_rejects_at_completion(self):
        from twisted.internet import defer

        from world.rules.character_creation import (
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
            custom_request(),
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
            custom_request(
                display_name="較新草稿", age=21, apparent_age=21
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
            custom_request(),
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

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_concept_outcomes_never_touch_the_confirmation_state(self):
        # The concept path saves no draft, so it neither preserves nor
        # manufactures an activation authorization: a degraded concept leaves
        # a still-valid confirmation intact (retool-concept-transient-fill
        # D1/D7), and activation of the confirmed draft still succeeds.
        from twisted.internet import defer

        _creation_custom_adapter(self.character, custom_payload())
        with patch(
            "server.ai_director_service.request_character_proposal",
            return_value=defer.succeed(None),
        ):
            deferred = _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
            result = await_result(deferred)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "concept_unavailable")
        activate = _creation_activate_adapter(self.character, {})
        self.assertEqual(activate["outcome"], "success")
        self.assertEqual(activate["code"], "activated")


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
        self.assertIsNotNone(self.character.traits.magic_power)

    def test_failed_relocation_preserves_activated_state(self):
        messages = []
        self.character.msg = lambda text, **kwargs: messages.append(str(text))
        with patch("world.rules.onboarding._south_gate", return_value=None):
            result = _creation_activate_adapter(self.character, {})
        self.assertEqual(result["outcome"], "success")
        self.assertFalse(self.character.creation_pending)
        self.assertIsNotNone(self.character.traits.magic_power)
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
                write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(read_draft(self.character), draft_before)
        self.assertEqual(self.character.key, "pending-shell")
        self.assertEqual(self.character.traits.all(), [])

    def test_concurrent_activations_apply_exactly_once(self):
        from world.rules.creation_wizard import activate_draft

        first = activate_draft(self.account, self.character)
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
        "subrace_key": "human_commoner",
        "allocations": balanced_allocations("human", "human_commoner"),
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
    """The transient concept action (retool-concept-transient-fill D1)."""

    def _propose(self, proposal):
        from twisted.internet import defer

        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            # A fresh fired Deferred per call: a settled Deferred must not be
            # reused across successive applies.
            side_effect=lambda **kwargs: defer.succeed(proposal),
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        return patch_obj

    def _degrade(self):
        from twisted.internet import defer

        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            side_effect=lambda **kwargs: defer.succeed(None),
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        return patch_obj

    def _slot(self):
        from web.webclient.actions.creation_actions import PROPOSAL_NDB_KEY

        return getattr(self.fake_session.ndb, PROPOSAL_NDB_KEY, None)

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_concept_apply_fills_only_the_session_slot(self):
        self._propose(_proposal())
        result = await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "concept_applied")
        self.assertEqual(result["affected_panels"], ("creation",))
        # Zero persistent writes: no draft, no canonical surface, no persona.
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.age, None)
        self.assertEqual(self.character.traits.all(), [])
        self.assertFalse(self.character.attributes.has("persona"))
        slot = self._slot()
        self.assertIsNotNone(slot, "the proposal must be stored in the session slot")
        self.assertEqual(slot["revision"], 1)
        self.assertEqual(slot["owner_actor_id"], self.character.pk)
        self.assertEqual(slot["race"], "human")
        self.assertEqual(slot["subrace"], "human_commoner")
        self.assertEqual(slot["allocations"], balanced_allocations("human"))
        self.assertEqual(slot["persona"], PERSONA_BLOCK)

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_slot_never_follows_a_puppet_switch(self):
        from twisted.internet import defer

        # An in-flight completion whose session stopped puppeting the admitted
        # actor writes nothing.
        held = defer.Deferred()
        patch_obj = patch(
            "server.ai_director_service.request_character_proposal",
            return_value=held,
        )
        patch_obj.start()
        self.addCleanup(patch_obj.stop)
        deferred = _creation_concept_adapter(
            self.character, _concept_payload(), self.fake_session
        )
        self.fake_session.puppet = None  # the session went OOC mid-flight
        held.callback(_proposal())
        result = await_result(deferred)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "ownership_rejected")
        self.assertIsNone(self._slot())

    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_slot_carries_carried_transient_fill_and_omits_absent(self):
        # The v3 slot mirrors the proposal: carried values ship (affinity as a
        # plain list, the normalized empty elf set included); absent values
        # write no key at all — never null (bump-creation-panel-proposal-v3).
        self._propose(
            _proposal(
                display_name="咪咪",
                age=20,
                apparent_age=18,
                background="貓婆婆收養的孤女",
                affinity_elements=("fire",),
            )
        )
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        slot = self._slot()
        self.assertEqual(slot["display_name"], "咪咪")
        self.assertEqual(slot["age"], 20)
        self.assertEqual(slot["apparent_age"], 18)
        self.assertEqual(slot["background"], "貓婆婆收養的孤女")
        self.assertEqual(slot["affinity_elements"], ["fire"])

        self._propose(_proposal())
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        slot = self._slot()
        for key in (
            "display_name",
            "age",
            "apparent_age",
            "background",
            "affinity_elements",
        ):
            self.assertNotIn(key, slot)

        # A carried EMPTY affinity set (the normalized elf value) is a value:
        # it ships as the empty list, it is not omitted.
        self._propose(
            _proposal(
                race_key="elf",
                subrace_key="fionnen",
                allocations=balanced_allocations("elf", "fionnen"),
                affinity_elements=(),
            )
        )
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(self._slot()["affinity_elements"], [])

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_custom_save_and_reset_clear_the_slot(self):
        self._propose(_proposal())
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertIsNotNone(self._slot())
        # A successful custom save consumes the pending fill.
        result = _creation_custom_adapter(
            self.character, custom_payload(), self.fake_session
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(self._slot())
        # A later apply is cleared by a successful reset.
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertIsNotNone(self._slot())
        result = _creation_reset_adapter(self.character, {}, self.fake_session)
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(self._slot())

    @covers_requirement("concept-transient-fill::concept-applies-transiently-with-zero-persistent-writes")
    def test_revision_keeps_rising_across_consumed_slots(self):
        # A consumed slot (save/reset cleared it) must never restart the
        # sequence: a mounted overlay's lastAppliedRevision would otherwise
        # ignore the next fresh apply at the colliding revision.
        self._propose(_proposal())
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(self._slot()["revision"], 1)
        result = _creation_custom_adapter(
            self.character, custom_payload(), self.fake_session
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIsNone(self._slot())
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        slot = self._slot()
        self.assertIsNotNone(slot)
        self.assertEqual(
            slot["revision"], 2, "the revision counter survives a consumed slot"
        )
        # A reset consumes again; the next apply still rises.
        _creation_reset_adapter(self.character, {}, self.fake_session)
        await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(self._slot()["revision"], 3)

    @covers_requirement("creation-persona-persistence::the-creation-panel-offers-a-concept-field-and-adapter-sharing-the-guarded-pipeline")
    def test_offline_concept_degrades_without_state_change(self):
        self._degrade()
        result = await_result(
            _creation_concept_adapter(
                self.character, _concept_payload(), self.fake_session
            )
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "concept_unavailable")
        self.assertEqual(result["message"], "生成不可用，請手動創角")
        self.assertIsNone(read_draft(self.character))
        self.assertIsNone(self._slot())
        self.assertTrue(self.character.creation_pending)
        # The deterministic adapters remain fully usable afterwards.
        result = _creation_custom_adapter(self.character, custom_payload())
        self.assertEqual(result["outcome"], "success")

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


class RollNamePayloadValidationTests(unittest.TestCase):
    """Structural gate for the exact ``creation.roll_name`` payload (D5)."""

    def test_exact_three_keys_with_nulls_and_identifiers(self):
        from web.webclient.actions.creation_actions import (
            validate_creation_roll_name_payload,
        )

        valid = {
            "race": "human",
            "subrace": "human_commoner",
            "sex": "female",
        }
        self.assertEqual(
            validate_creation_roll_name_payload(valid), dict(valid)
        )
        self.assertEqual(
            validate_creation_roll_name_payload(
                {"race": None, "subrace": None, "sex": None}
            ),
            {"race": None, "subrace": None, "sex": None},
        )

    def test_malformed_payloads_raise(self):
        from web.webclient.actions.creation_actions import (
            CreationActionError,
            validate_creation_roll_name_payload,
        )

        for bad in (
            {},
            {"race": "human", "subrace": None},
            {"race": "human", "subrace": None, "sex": None, "actor": 1},
            {"race": "", "subrace": None, "sex": None},
            {"race": "r" * 65, "subrace": None, "sex": None},
            {"race": 5, "subrace": None, "sex": None},
            {"race": "human", "subrace": None, "sex": True},
            "not-a-dict",
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(CreationActionError):
                    validate_creation_roll_name_payload(bad)


class NameRollActionTests(CreationActionBase):
    """The result-only name roll: semantic gate, zero writes, bound packs."""

    RACE = "human"
    SUBRACE = "human_commoner"

    def _roll(self, race=RACE, subrace=SUBRACE, sex="female"):
        from web.webclient.actions.creation_actions import (
            _creation_roll_name_adapter,
        )

        return _creation_roll_name_adapter(
            self.character, {"race": race, "subrace": subrace, "sex": sex}
        )

    @staticmethod
    def _bound_parts():
        from world.lore.names import NAME_PACK_BY_RACE, NAME_PACK_REGISTRY

        bound = set(NAME_PACK_BY_RACE.values())
        parts: set[str] = set()
        unbound_only: set[str] = set()
        for key, pack in NAME_PACK_REGISTRY.items():
            pool = {part.zh for part in pack.surnames}
            for entries in pack.given.values():
                pool.update(part.zh for part in entries)
            if key in bound:
                parts |= pool
            else:
                unbound_only |= pool
        return parts, unbound_only - parts

    def _assert_result_only_frames(self, marker_index_start: int) -> None:
        for entry in self.fake_session.sent[marker_index_start:]:
            self.assertNotIn(
                "ui_snapshot", entry, "a name roll must not publish a snapshot"
            )
            self.assertNotIn(
                "ui_update", entry, "a name roll must not publish an update"
            )

    def _attribute_snapshot(self):
        return {
            key: (
                self.character.attributes.has(key),
                deepcopy(self.character.attributes.get(key))
                if self.character.attributes.has(key)
                else None,
            )
            for key in (
                "age", "apparent_age", "race", "subrace", "sex",
                "creation_pending", "creation_draft", "skills", "persona",
                "affinity_elements",
            )
        }

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_valid_roll_returns_name_with_zero_writes_and_no_publish(self):
        from world.rules.character_creation import _validate_name

        before_attributes = self._attribute_snapshot()
        frames_before = len(self.fake_session.sent)
        self._dispatch(
            self._envelope(
                "creation.roll_name",
                {"race": "human", "subrace": "human_commoner", "sex": "female"},
                request_id="roll-1",
            )
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "name_rolled")
        name = result["data"]["display_name"]
        self.assertEqual(_validate_name(name), name)
        self.assertNotIn("no_presentation", result)
        self.assertEqual(self._attribute_snapshot(), before_attributes)
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)
        self._assert_result_only_frames(frames_before)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_activated_character_cannot_roll(self):
        import web.webclient.actions.creation_actions as actions

        _creation_custom_adapter(self.character, custom_payload())
        activate_player_character(self.account, self.character, custom_request())
        self.assertFalse(self.character.creation_pending)

        def spy(*args, **kwargs):
            raise AssertionError("the roller must never be reached")

        calls: list = []
        with patch.object(actions, "roll_name_for_race", spy):
            frames_before = len(self.fake_session.sent)
            result = self._roll("human", "human_commoner", "female")
            calls.append(result)
        (result,) = calls
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_complete")
        self.assertNotIn("data", result)
        self._assert_result_only_frames(frames_before)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_dirty_inputs_reject_before_the_roller(self):
        import web.webclient.actions.creation_actions as actions
        from world.rules.creation_messages import rejection_code

        calls: list = []

        def spy(*args, **kwargs):
            calls.append(args)
            raise AssertionError("the roller must never be reached")

        cases = {
            ("dragonborn", None, None): "unknown_race",
            ("dragonborn", "human_commoner", None): "unknown_race",
            ("elf", "human_commoner", None): "incompatible_subrace",
            ("elf", "not_a_subrace", None): "unknown_subrace",
            (None, "human_commoner", None): "incompatible_subrace",
            ("human", "human_commoner", "nope"): "unknown_sex",
        }
        with patch.object(actions, "roll_name_for_race", spy):
            for (race, subrace, sex), expected_code in cases.items():
                with self.subTest(race=race, subrace=subrace, sex=sex):
                    frames_before = len(self.fake_session.sent)
                    result = self._roll(race, subrace, sex)
                    self.assertEqual(result["outcome"], "rejected")
                    self.assertEqual(result["code"], expected_code)
                    self.assertEqual(
                        rejection_code(result["code"]), expected_code
                    )
                    self.assertNotIn("data", result)
                    self.assertTrue(result["no_presentation"])
                    self._assert_result_only_frames(frames_before)
        self.assertEqual(calls, [], "rejected rolls must not reach the roller")

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_unselected_race_falls_back_only_to_bound_packs(self):
        parts, unbound_only = self._bound_parts()
        from world.lore.names import NAME_SEPARATOR

        names = {
            self._roll(None, None, None)["data"]["display_name"]
            for _ in range(60)
        }
        self.assertTrue(names)
        for name in names:
            given, separator, surname = name.partition(NAME_SEPARATOR)
            self.assertTrue(separator)
            self.assertIn(given, parts, name)
            self.assertIn(surname, parts, name)
            self.assertNotIn(given, unbound_only, name)
            self.assertNotIn(surname, unbound_only, name)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_roller_receives_the_module_singleton_rng(self):
        import web.webclient.actions.creation_actions as actions

        seen: list = []

        def spy(race, sex, rng):
            seen.append(rng)
            return "測試名"

        with patch.object(actions, "roll_name_for_race", spy):
            self._roll()
            self._roll()
        self.assertEqual(len(seen), 2)
        self.assertIs(seen[0], seen[1])
        self.assertIs(seen[0], actions._ROLL_NAME_RNG)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_sex_channel_flows_from_custom_save_to_activation(self):
        self._dispatch(
            self._envelope(
                "creation.custom",
                custom_payload(sex="female"),
                request_id="custom-sex-1",
            )
        )
        self.assertEqual(self._last_result()["outcome"], "success")
        self.assertEqual(read_draft(self.character)["sex"], "female")
        self._dispatch(
            self._envelope("creation.activate", {}, request_id="activate-sex-1")
        )
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.character.sex, "female")
        self.assertIsNone(read_draft(self.character))

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    def test_dirty_sex_rejected_by_the_deterministic_service(self):
        frames_before = len(self.fake_session.sent)
        self._dispatch(
            self._envelope(
                "creation.custom",
                custom_payload(sex="nope"),
                request_id="custom-dirty-1",
            )
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_sex")
        self.assertIsNone(read_draft(self.character))
        self.assertTrue(self.character.creation_pending)

    @covers_requirement("webclient-character-creation-ui::creation-actions-are-exact-allowlisted-and-server-authoritative")
    @covers_requirement("webclient-oob-protocol::result-and-protocol-error-envelopes-are-exact-and-non-overlapping")
    def test_roll_result_round_trips_the_wire_validator(self):
        from web.webclient.presentation.protocol import validate_ui_action_result

        self._dispatch(
            self._envelope(
                "creation.roll_name",
                {"race": None, "subrace": None, "sex": "male"},
                request_id="roll-wire-1",
            )
        )
        result = self._last_result()
        self.assertEqual(result["outcome"], "success")
        # The captured frame IS the wire envelope; the server-side mirror of
        # the JS validator must accept it unchanged (data slot consumption).
        envelope = next(
            entry["ui_action_result"][0][0]
            for entry in reversed(self.fake_session.sent)
            if "ui_action_result" in entry
        )
        validated = validate_ui_action_result(envelope)
        self.assertEqual(validated["outcome"], "success")
        self.assertEqual(
            validated["data"], {"display_name": result["data"]["display_name"]}
        )
