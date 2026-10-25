"""Lawful possessed authored conversations with owner-correct relationships.

Covers the authored-dialogue-possession change:

- complete party-scope authorization in ``resolve_dialogue_context`` (forged
  mirrors, unrelated actor, missing driving session, remote and self hosts,
  stale control identity);
- the session stays on the acting body while host relations and affinity stay
  with the owning player, including when both relationship records exist;
- authored open/select/leave through the web adapters and the text command;
- release and handback retire the acting body's playback with cache rollback;
- possessed trade keeps the commander purse and the member bag.

The synthetic dialogue scope supplies the authored host table, so no shipped
prose is named here.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.talk import CmdsTalk
from tools.spec_traceability import covers_requirement
from typeclasses.components import Merchant, ScriptedDialogue
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
from web.webclient.actions.exploration_actions import (
    _dialogue_leave_adapter,
    _talk_open_adapter,
    _talk_scripted_adapter,
)
from web.webclient.actions.service_actions import _buy_adapter
from web.webclient.presentation.affordances import exploration_affordances
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.clock import get_world_clock
from world.rules.dialogue import (
    StaleContextError,
    clear_dialogue_session,
    live_dialogue_session,
    select_authored_topic,
)
from world.rules.dialogue_context import (
    DialogueContextError,
    resolve_dialogue_context,
)
from world.rules.party import join_party
from world.rules.possession import (
    REASON_POSSESSED_TALK,
    PossessionWriteError,
    enter_possession,
    release_possession,
)
from world.quests.catalog import register_catalog
from world.tests.synthetic_data import synthetic_registries

#: The kit authored row used as this module's host (four topics, greeting).
_HOST_DIALOGUE_KEY = "t_synth_lodgekeeper"
_TOPIC_ID = f"{_HOST_DIALOGUE_KEY}.topic_01"


@synthetic_registries("dialogue")
class AuthoredDialoguePossessionTests(EvenniaTest):
    """Integration tests for lawful possessed authored conversations."""

    def setUp(self):
        super().setUp()
        register_catalog()
        get_world_clock()
        self.room1 = create_object(Room, key="交談大廳")
        self.char1.location = self.room1
        self.char1.race = "human"
        self.char1.apply_race_baseline()

        self.host = create_object(NPC, key="合成店主", location=self.room1)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_HOST_DIALOGUE_KEY)
        )

        self.companion = create_object(LLMNPC, key="合成同伴", location=self.room1)
        self.companion.race = "elf"
        self.companion.apply_race_baseline()
        self.companion.db.inventory = []
        join_party(self.companion, self.char1)
        enter_possession(self.char1, self.companion)

    def tearDown(self):
        clear_dialogue_session(self.companion)
        clear_dialogue_session(self.char1)
        release_possession(self.char1, npc=self.companion, reason="handback")
        super().tearDown()

    def _run_talk(self, args: str) -> str:
        """Run the text ``talk`` command as the possessed acting body."""
        messages: list[str] = []
        with patch.object(self.companion, "msg", side_effect=messages.append):
            command = CmdsTalk()
            command.caller = self.companion
            command.args = args
            command.func()
        return "\n".join(messages)

    # ------------------------------------------------------------------
    # Context ownership
    # ------------------------------------------------------------------

    def _owner_affinity(self) -> int:
        return self.host.relations.affinity_for(self.char1)

    @covers_requirement(
        "authored-dialogue-selection::authored-selection-delivers-complete-scenes-atomically"
    )
    @covers_requirement(
        "authored-dialogue-possession::lawful-possession-can-initiate-authored-dialogue"
    )
    def test_lawful_possession_keeps_the_session_on_the_actor_and_affinity_on_the_owner(self):
        context = resolve_dialogue_context(self.companion, self.host)
        self.assertIs(context.owner, self.char1)
        self.assertIs(context.actor, self.companion)
        # Asymmetric races stay on the acting body.
        self.assertNotEqual(context.actor.race, context.owner.race)

        affinity_before = self._owner_affinity()
        delivery = select_authored_topic(
            self.companion,
            self.host,
            _TOPIC_ID,
            selection_id="req-possessed-1",
            expected_context_id=None,
        )
        self.assertEqual(delivery.actor_id, int(self.companion.pk))
        self.assertEqual(delivery.owner_id, int(self.char1.pk))
        self.assertEqual(self._owner_affinity(), affinity_before + 1)
        self.assertFalse(self.host.relations.has_record(self.companion))

        session = live_dialogue_session(self.companion)
        self.assertIsNotNone(session)
        self.assertEqual(session.actor_id, int(self.companion.pk))
        self.assertEqual(session.owner_id, int(self.char1.pk))
        self.assertEqual(session.delivery.delivery_id, delivery.delivery_id)
        self.assertIsNone(self.char1.db.dialogue_session)

    @covers_requirement(
        "scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines"
    )
    def test_dual_relationship_records_change_only_the_owner_record(self):
        apply_affinity_change(self.host, self.char1, AffinitySource.QUEST_COMPLETION, 10)
        apply_affinity_change(
            self.host, self.companion, AffinitySource.QUEST_COMPLETION, 40
        )
        owner_before = self.host.relations.affinity_for(self.char1)
        companion_before = self.host.relations.affinity_for(self.companion)

        select_authored_topic(
            self.companion,
            self.host,
            _TOPIC_ID,
            selection_id="req-possessed-dual",
            expected_context_id=None,
        )

        self.assertEqual(self.host.relations.affinity_for(self.char1), owner_before + 1)
        self.assertEqual(
            self.host.relations.affinity_for(self.companion), companion_before
        )

    @covers_requirement(
        "authored-dialogue-selection::authored-selection-delivers-complete-scenes-atomically"
    )
    @covers_requirement(
        "authored-dialogue-possession::lawful-possession-can-initiate-authored-dialogue"
    )
    @covers_requirement(
        "authored-dialogue-possession::possessed-shopping-and-unrelated-restrictions-remain-unchanged"
    )
    def test_forged_mirrors_and_illegal_hosts_reject_without_state(self):
        selection_arguments = {
            "selection_id": "req-forged",
            "expected_context_id": None,
        }
        relation_before = dict(self.host.db.relations_data or {})
        binding = dict(self.char1.db.possession)
        remote = create_object(NPC, key="遠方店主", location=self.room2)
        remote.components.add(
            ScriptedDialogue.create(remote, dialogue_key=_HOST_DIALOGUE_KEY)
        )

        def _owner_mirror_missing():
            # The owner-side mirror is gone while the acting body still says it
            # is possessed: reading the mirror yields no authority.
            self.char1.db.possession = None

        def _actor_mirror_foreign():
            self.companion.db.possessed_by = int(self.char2.pk)

        cases = (
            ("owner_mirror", _owner_mirror_missing, self.host),
            ("actor_mirror", _actor_mirror_foreign, self.host),
            ("remote_host", None, remote),
            ("self_host", None, self.companion),
        )

        try:
            for label, break_mirror, host in cases:
                with self.subTest(case=label):
                    if break_mirror is not None:
                        break_mirror()
                    with self.assertRaises(DialogueContextError):
                        resolve_dialogue_context(self.companion, host)
                    with self.assertRaises(DialogueContextError):
                        select_authored_topic(
                            self.companion, host, _TOPIC_ID, **selection_arguments
                        )
                    self.assertIsNone(self.companion.db.dialogue_session)
                    self.assertEqual(
                        dict(self.host.db.relations_data or {}), relation_before
                    )
                    # Restore the lawful mirrors for the next case.
                    self.char1.db.possession = dict(binding)
                    self.companion.db.possessed_by = int(self.char1.pk)
        finally:
            self.char1.db.possession = dict(binding)
            self.companion.db.possessed_by = int(self.char1.pk)
            remote.delete()

    def test_stale_control_identity_retires_the_live_session(self):
        select_authored_topic(
            self.companion,
            self.host,
            _TOPIC_ID,
            selection_id="req-stale-control",
            expected_context_id=None,
        )
        session = live_dialogue_session(self.companion)
        self.assertIsNotNone(session)

        binding = dict(self.char1.db.possession)
        self.char1.db.possession = {
            **binding,
            "since_tick": int(binding.get("since_tick", 0)) + 1,
        }
        try:
            self.assertIsNone(live_dialogue_session(self.companion))
            with self.assertRaises(StaleContextError):
                select_authored_topic(
                    self.companion,
                    self.host,
                    _TOPIC_ID,
                    selection_id="req-stale-control-2",
                    expected_context_id=session.context_id,
                )
        finally:
            self.char1.db.possession = binding

    # ------------------------------------------------------------------
    # Entry surfaces
    # ------------------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-selection::text-and-browser-resolve-the-same-authored-topic"
    )
    @covers_requirement(
        "authored-dialogue-possession::lawful-possession-can-initiate-authored-dialogue"
    )
    def test_web_open_select_and_leave_use_the_actor_body(self):
        owner_before = self._owner_affinity()
        open_result = _talk_open_adapter(self.companion, {"npc_id": int(self.host.pk)})
        self.assertEqual(open_result["outcome"], "success")
        session = live_dialogue_session(self.companion)
        self.assertIsNotNone(session)
        self.assertEqual(session.kind, "line")
        self.assertIsNone(self.char1.db.dialogue_session)

        select_result = _talk_scripted_adapter(
            self.companion,
            {
                "npc_id": int(self.host.pk),
                "topic_id": _TOPIC_ID,
                "context_id": session.context_id,
            },
        )
        self.assertEqual(select_result["outcome"], "success")
        self.assertEqual(self._owner_affinity(), owner_before + 1)
        scene_session = live_dialogue_session(self.companion)
        self.assertEqual(scene_session.kind, "scene")
        self.assertFalse(self.host.relations.has_record(self.companion))

        leave_result = _dialogue_leave_adapter(
            self.companion, {"npc_id": int(self.host.pk)}
        )
        self.assertEqual(leave_result["outcome"], "success")
        self.assertIsNone(self.companion.db.dialogue_session)

    @covers_requirement(
        "webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting"
    )
    def test_forged_web_open_rejects_with_the_fixed_possession_refusal(self):
        self.char1.db.possession = None
        result = _talk_open_adapter(self.companion, {"npc_id": int(self.host.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], REASON_POSSESSED_TALK)
        self.assertIsNone(self.companion.db.dialogue_session)

    @covers_requirement(
        "authored-dialogue-selection::text-and-browser-resolve-the-same-authored-topic"
    )
    def test_text_talk_selects_the_authored_scene_as_the_actor(self):
        owner_before = self._owner_affinity()
        output = self._run_talk(f"{self.host.key} 住宿")
        self.assertNotIn("無法", output)
        session = live_dialogue_session(self.companion)
        self.assertIsNotNone(session)
        self.assertEqual(session.kind, "scene")
        self.assertEqual(session.actor_id, int(self.companion.pk))
        self.assertEqual(session.owner_id, int(self.char1.pk))
        self.assertEqual(self._owner_affinity(), owner_before + 1)
        self.assertFalse(self.host.relations.has_record(self.companion))

    @covers_requirement(
        "webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting"
    )
    def test_text_talk_rejects_a_forged_possession_before_content(self):
        self.char1.db.possession = None
        output = self._run_talk(f"{self.host.key} 住宿")
        self.assertIn("附身狀態下無法與他人開啟對話。", output)
        self.assertIsNone(self.companion.db.dialogue_session)
        self.assertFalse(self.host.relations.has_record(self.companion))
        self.assertFalse(self.host.relations.has_record(self.char1))

    @covers_requirement(
        "exploration-affordances::the-shared-read-only-affordance-vocabulary-supports-possessed-shop-access"
    )
    @covers_requirement(
        "authored-dialogue-possession::possessed-shopping-and-unrelated-restrictions-remain-unchanged"
    )
    def test_vocabulary_enables_lawful_authored_talk_and_keeps_freeform_refused(self):
        freeform_host = create_object(LLMNPC, key="合成吟遊詩人", location=self.room1)
        entries = exploration_affordances(self.companion)
        scripted = [
            entry
            for entry in entries
            if entry.action_id == "explore.talk_scripted"
            and entry.params.get("npc_id") == int(self.host.pk)
        ]
        self.assertTrue(scripted)
        self.assertTrue(all(entry.enabled for entry in scripted))
        freeform = [
            entry
            for entry in entries
            if entry.action_id == "explore.talk_freeform"
            and entry.params.get("npc_id") == int(freeform_host.pk)
        ]
        self.assertTrue(freeform)
        self.assertFalse(freeform[0].enabled)
        self.assertEqual(freeform[0].disabled_reason[0], REASON_POSSESSED_TALK)

    @covers_requirement(
        "webclient-possession-presentation::shop-access-does-not-delegate-other-npc-services-during-possession"
    )
    def test_text_talk_guild_turnin_stays_refused_while_possessing(self):
        """Guild 回報 keeps its player-only authority behind the possession refusal.

        The service never receives the acting body, so no claim, reward or
        ledger state can change; ordinary authored guild topics are covered by
        the enabled authored path above.
        """
        from typeclasses.components import GuildStaff
        from world.rules.dialogue import (
            GUILD_STAFF_DIALOGUE_KEY,
            GUILD_STAFF_TURNIN_KEYWORD,
        )
        from world.rules.possession import POSSESSED_REFUSAL_MESSAGES

        staff = create_object(NPC, key="合成公會職員", location=self.room1)
        staff.components.add(
            GuildStaff.create(
                staff, service_id="synth_staff", branch_key="synth_branch"
            )
        )
        staff.components.add(
            ScriptedDialogue.create(staff, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        wallet_before = self.char1.db.wallet

        with patch("commands.talk.dialogue_turn_in") as turn_in:
            output = self._run_talk(
                f"{staff.key} {GUILD_STAFF_TURNIN_KEYWORD} synth-quest-1"
            )

        turn_in.assert_not_called()
        self.assertEqual(output, POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK])
        self.assertEqual(self.char1.db.wallet, wallet_before)
        self.assertIsNone(self.companion.db.dialogue_session)

    @covers_requirement(
        "authored-dialogue-possession::possessed-informational-dialogue-covers-generated-roles"
    )
    def test_possessed_generated_host_authorizes_by_package_role_binding(self):
        """A generated role needs no static profile to authorize a possessed body.

        The scene provider for generated phases stays the deferred generated
        seam, so this slice owns the source-neutral authorization: the acted
        context resolves the package/role identity with actor/owner separation,
        while generated service/commission keywords stay refused and deliver no
        protected success body or session.
        """
        from world.lore.dialogue.codec import (
            GeneratedDialogueIdentity,
            make_generated_host_key,
        )
        from world.rules.dialogue_sources import resolve_dialogue_source
        from world.rules.possession import POSSESSED_REFUSAL_MESSAGES

        generated = create_object(NPC, key="生成角色", location=self.room1)
        generated.components.add(
            ScriptedDialogue.create(
                generated, dialogue_key="scene_role:pkg_synth:elder"
            )
        )

        context = resolve_dialogue_context(self.companion, generated)
        self.assertIs(context.actor, self.companion)
        self.assertIs(context.owner, self.char1)
        self.assertEqual(
            context.source_identity,
            GeneratedDialogueIdentity("pkg_synth", "elder", "phase_1"),
        )
        self.assertEqual(
            context.host_key, make_generated_host_key("pkg_synth", "elder")
        )
        # The provider seam, not a static profile, is the only source.
        self.assertIsNone(resolve_dialogue_source(context))

        refusal = _talk_scripted_adapter(
            self.companion,
            {"npc_id": int(generated.pk), "keyword_id": "委託"},
        )
        self.assertEqual(refusal["outcome"], "rejected")
        self.assertEqual(refusal["code"], REASON_POSSESSED_TALK)
        self.assertEqual(
            refusal["message"], POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_TALK]
        )
        self.assertIsNone(self.companion.db.dialogue_session)

    # ------------------------------------------------------------------
    # Release and trade
    # ------------------------------------------------------------------

    @covers_requirement(
        "companion-possession-core::possession-is-a-mirrored-single-writer-transactional-binding"
    )
    def test_release_retires_the_acting_body_playback(self):
        select_authored_topic(
            self.companion,
            self.host,
            _TOPIC_ID,
            selection_id="req-release",
            expected_context_id=None,
        )
        self.assertIsNotNone(live_dialogue_session(self.companion))
        stored_before = self.companion.db.dialogue_session

        release_possession(self.char1, npc=self.companion, reason="handback")

        self.assertIsNone(self.companion.db.dialogue_session)
        self.assertIsNone(live_dialogue_session(self.companion))

        # Re-establish possession for the shared tearDown release.
        enter_possession(self.char1, self.companion)
        self.assertIsNotNone(stored_before)

    @covers_requirement(
        "companion-possession-core::possession-is-a-mirrored-single-writer-transactional-binding"
    )
    def test_failed_release_restores_the_acting_body_playback(self):
        select_authored_topic(
            self.companion,
            self.host,
            _TOPIC_ID,
            selection_id="req-release-rollback",
            expected_context_id=None,
        )
        stored_before = dict(self.companion.db.dialogue_session)

        with patch(
            "world.rules.possession._bump_released_owner_view",
            side_effect=RuntimeError("injected release failure"),
        ):
            with self.assertRaises(PossessionWriteError):
                release_possession(self.char1, npc=self.companion, reason="handback")

        self.assertEqual(dict(self.companion.db.dialogue_session), stored_before)
        self.assertIsNotNone(live_dialogue_session(self.companion))

    @covers_requirement(
        "shop-economy::possessed-trades-use-the-named-bag-and-the-party-purse"
    )
    @covers_requirement(
        "authored-dialogue-possession::possessed-shopping-and-unrelated-restrictions-remain-unchanged"
    )
    def test_trade_after_an_authored_scene_keeps_the_commander_purse_and_member_bag(self):
        from world.rules.tests._combat_session_helpers import open_synthetic_scope
        from world.rules.tests._guild_service_probes import (
            install_synthetic_catalog,
            synth_catalog,
            synth_offer_rule,
            synth_shop_config,
        )
        from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS

        select_authored_topic(
            self.companion,
            self.host,
            _TOPIC_ID,
            selection_id="req-trade",
            expected_context_id=None,
        )
        _dialogue_leave_adapter(self.companion, {"npc_id": int(self.host.pk)})

        open_synthetic_scope(self, "items", "prices", "shops")
        shop_key = next(iter(SYNTH_SHOPS))
        potion = SYNTH_ITEMS["t_ember_spray"].key
        offer = synth_offer_rule(potion, max_stock=10, initial_stock=5)
        install_synthetic_catalog(
            self,
            synth_catalog(
                shop_configs={
                    shop_key: synth_shop_config(
                        shop_key, (potion,), offer_rules=(offer,)
                    )
                }
            ),
        )
        get_world_clock()._persist(12 * 3600)
        merchant_host = create_object(NPC, key="合成商人", location=self.room1)
        merchant = Merchant.create(
            merchant_host, service_id="possessed_dialogue_store", shop_key=shop_key
        )
        merchant_host.components.add(merchant)
        merchant.merchant_stock = {potion: 5}

        self.char1.db.wallet = 5000
        wallet_before = self.char1.db.wallet
        companion_bag = list(self.companion.db.inventory)
        owner_bag = list(self.char1.db.inventory or [])

        result = _buy_adapter(
            self.companion,
            {
                "item_key": potion,
                "quantity": 1,
                "recipient_id": self.companion.pk,
            },
        )

        self.assertEqual(result["outcome"], "success", result)
        self.assertEqual(self.char1.db.wallet, wallet_before - offer.buy_copper)
        self.assertEqual(list(self.companion.db.inventory), companion_bag + [potion])
        self.assertEqual(list(self.char1.db.inventory or []), owner_bag)
        self.assertFalse(merchant_host.relations.has_record(self.companion))
