"""Behavior test: committed physical-source dialogue availability refresh.

Covers ``authored-dialogue-refresh-physical`` against a synthetic table and the
shared synthetic kit. Each exact source-matrix writer is exercised through its
real deterministic entry point with no WebClient action context at all:

- ``apply_inventory_plan``/``toggle_equipment`` (carried item, worn exposure
  bias), ``apply_event`` (base exposure transition),
  ``set_social_identities``, ``award_practice_xp``,
  ``apply_lineage_auto_seed`` and ``cross_lineage_unlock.grant_owned_skill``
  each schedule one committed refresh for the canonical owner.
- The callback re-resolves the owner row, its acting body (possession), the
  host binding and the current generated phase before projecting, so a
  pre-commit snapshot or a pre-commit eligibility answer is never published.
- A watcher receives the freshly projected choices; an already delivered
  scene keeps its authored wording, and an outer rollback publishes nothing.
- ``affected_dialogue_owners`` returns only lawful owners: the player itself,
  a companion's bound owner plus its lawful possession owner and an explicit
  ``prior_owner`` captured before a detach -- never an account-wide sibling.
- A persona-prose write is not a source, and no helper creates a
  conversation, session or selection.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.db import transaction
from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation import watchers
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.registry import build_production_registry
from world.lore.dialogue.conditions import (
    Carries,
    Exposure,
    SkillOwned,
    SocialIdentityIs,
)
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic
from world.lore.scenes import Scene, Speech
from world.lore.sexual_vocab import EXPOSURE_LEVELS
from world.quests.catalog import register_catalog
from world.rules.cross_lineage_unlock import grant_owned_skill
from world.rules.dialogue import (
    clear_dialogue_session,
    live_dialogue_session,
    open_or_refresh_dialogue,
    select_authored_topic,
)
from world.rules.dialogue_availability import (
    TOPIC_LOCKED,
    TOPIC_OPEN,
    affected_dialogue_owners,
    queue_dialogue_refresh,
)
from world.rules.dialogue_sources import ResolvedDialogueSource
from world.rules.equipment import (
    apply_inventory_plan,
    plan_inventory_delta,
    toggle_equipment,
)
from world.rules.equipment_effects import EQUIPMENT_EFFECT_RULES
from world.rules.party import join_party, leave_party
from world.rules.possession import enter_possession, release_possession
from world.rules.progression import apply_lineage_auto_seed, award_practice_xp
from world.rules.progression._constants import SKILL_PROFICIENCY_XP_PER_LEVEL
from world.rules.rulebook.schema import Rule
from world.rules.sexual_transitions import apply_event
from world.rules.social_identity import set_social_identities
from world.skills.equipment import EquipmentSlot
from world.skills.eligibility import skill_identity_eligible
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_RACES,
    SYNTH_SKILLS,
    synthetic_registries,
)

_TABLE_KEY = "t_refresh_keeper"
_OPEN_TOPIC = f"{_TABLE_KEY}.open"
_CARRIES_TOPIC = f"{_TABLE_KEY}.carried"
_EXPOSURE_TOPIC = f"{_TABLE_KEY}.exposure"
_IDENTITY_TOPIC = f"{_TABLE_KEY}.identity"
_OWNED_TOPIC = f"{_TABLE_KEY}.owned"
_PROFICIENT_TOPIC = f"{_TABLE_KEY}.proficient"

_SENTINEL_DELIVERED = "SENTINEL-REFRESH-DELIVERED"
_SENTINEL_REFUSAL = "SENTINEL-REFRESH-REFUSAL"
_SENTINEL_OWNED = "SENTINEL-REFRESH-OWNED"
_SENTINEL_PROFICIENT = "SENTINEL-REFRESH-PROFICIENT"

_RACE_KEY = next(iter(SYNTH_RACES))
_SKILL_KEY = next(iter(SYNTH_SKILLS))
_ITEM_KEY = next(
    key for key, row in SYNTH_ITEMS.items() if row.equipment_slot is None
)


def _exposure_accessory() -> tuple[str, int]:
    """The kit's exposure-bias accessory key and its canonical bias magnitude."""
    biased = {
        key
        for key, rule in EQUIPMENT_EFFECT_RULES.items()
        if rule.exposure_bias > 0
    }
    for key, row in SYNTH_ITEMS.items():
        if row.equipment_slot is not EquipmentSlot.ACCESSORY:
            continue
        if row.modifier_key in biased:
            return key, int(EQUIPMENT_EFFECT_RULES[row.modifier_key].exposure_bias)
    raise AssertionError("the synthetic kit declares no exposure-bias accessory")


_ACCESSORY_KEY, _ACCESSORY_BIAS = _exposure_accessory()
_EXPOSURE_BASELINE_ORDINAL = 1
_EXPOSURE_THRESHOLD = min(
    _EXPOSURE_BASELINE_ORDINAL + _ACCESSORY_BIAS, len(EXPOSURE_LEVELS) - 1
)
_BASELINE_EXPOSURE = EXPOSURE_LEVELS[_EXPOSURE_BASELINE_ORDINAL]


def _social_identity_key() -> str:
    """One canonical identity key the sole writer accepts."""
    from world.lore.social_identities import SOCIAL_IDENTITY_REGISTRY

    return next(iter(SOCIAL_IDENTITY_REGISTRY))


_IDENTITY_KEY = _social_identity_key()

CALENDAR = SimpleNamespace(
    year=1,
    season_index=0,
    season_name="春季",
    day_in_season=3,
    hour=12,
    minute=0,
    second=0,
)


def _scene(scene_id: str, host_text: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="合成問句。"),
            Speech(speaker="host", text=host_text),
        ),
    )


def _dialogue() -> AuthoredDialogue:
    """One table with a source per wired writer."""
    return AuthoredDialogue(
        greeting="合成櫃檯後的人抬眼：「有事就說。」",
        topics=(
            AuthoredTopic(
                topic_id=_OPEN_TOPIC,
                keyword="合成開場",
                label="合成開場",
                fallback=_scene("t_refresh_open", _SENTINEL_DELIVERED),
            ),
            AuthoredTopic(
                topic_id=_CARRIES_TOPIC,
                keyword="合成持有",
                label="合成持有",
                fallback=_scene("t_refresh_carried_formal", "合成持有答覆。"),
                requires=Carries(item_key=_ITEM_KEY),
                unavailable="locked",
                refusal=_scene("t_refresh_carried_refusal", _SENTINEL_REFUSAL),
            ),
            AuthoredTopic(
                topic_id=_EXPOSURE_TOPIC,
                keyword="合成衣著",
                label="合成衣著",
                fallback=_scene("t_refresh_exposure_formal", "合成衣著答覆。"),
                requires=Exposure(minimum=_EXPOSURE_THRESHOLD),
                unavailable="locked",
                refusal=_scene("t_refresh_exposure_refusal", _SENTINEL_REFUSAL),
            ),
            AuthoredTopic(
                topic_id=_IDENTITY_TOPIC,
                keyword="合成身分",
                label="合成身分",
                fallback=_scene("t_refresh_identity_formal", "合成身分答覆。"),
                requires=SocialIdentityIs(identity_key=_IDENTITY_KEY),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_OWNED_TOPIC,
                keyword="合成技能",
                label="合成技能",
                fallback=_scene("t_refresh_owned_formal", _SENTINEL_OWNED),
                requires=SkillOwned(skill_key=_SKILL_KEY),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_PROFICIENT_TOPIC,
                keyword="合成熟練",
                label="合成熟練",
                fallback=_scene("t_refresh_proficient_formal", _SENTINEL_PROFICIENT),
                requires=SkillOwned(skill_key=_SKILL_KEY, min_proficiency=1),
                unavailable="hidden",
            ),
        ),
    )


class DialogueRefreshPhysicalTests(EvenniaTest):
    """The seven committed physical writers and their owner discovery."""

    def setUp(self) -> None:
        super().setUp()
        # ACQUIRE replacement resolution reads the registered quest catalog.
        register_catalog()
        self.scope = synthetic_registries(
            "races",
            "items",
            "skills",
            "dialogue",
            extra={"dialogue": {_TABLE_KEY: _dialogue()}},
        )
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)
        watchers.clear_watchers()
        self.addCleanup(watchers.clear_watchers)

        self.room = create_object(Room, key="合成刷新廳")
        self.player = create_object(PlayerCharacter, key="合成刷新玩家")
        self.player.race = _RACE_KEY
        self.player.apply_race_baseline()
        self.player.db.inventory = []
        self.player.db.sexual = {"exposure": _BASELINE_EXPOSURE}
        self.player.location = self.room
        self.host = create_object(NPC, key="合成刷新店主", location=self.room)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_TABLE_KEY)
        )
        self.registry = build_production_registry()
        self._sessid = 700

    def tearDown(self) -> None:
        clear_dialogue_session(self.player)
        if self.player.db.possession:
            release_possession(self.player, reason="handback")
        super().tearDown()

    # -- helpers ---------------------------------------------------------

    def _register_watcher(self, puppet):
        real = ServerSession()
        real.init_session(
            "webclient/websocket", ("localhost", 9999), self.sessionhandler
        )
        self._sessid += 1
        real.sessid = self._sessid
        self.sessionhandler[real.sessid] = real
        real.protocol_key = "webclient/websocket"
        real.puppet = puppet
        puppet.sessions.add(real)
        recorded: list[dict] = []
        real.msg = lambda **kwargs: recorded.append(kwargs)
        coordinator = PresentationCoordinator(
            real, self.registry, calendar_provider=lambda: CALENDAR
        )
        real.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(
            PresentationContext(actor=puppet, protocol_version=1)
        )
        watchers.register_watcher(real)
        self.addCleanup(lambda: self.sessionhandler.__delitem__(real.sessid))
        return real, recorded

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    @staticmethod
    def _panels(recorded: list[dict]) -> list[dict]:
        panels = []
        for call in recorded:
            message = call.get("ui_snapshot") or call.get("ui_update")
            if message:
                panels.append(message[0][0]["panels"])
        return panels

    def _choices(self, recorded: list[dict]) -> dict[str, dict]:
        panels = self._panels(recorded)
        self.assertTrue(panels, "the committed refresh must fan a panel out")
        dialogue = panels[-1]["dialogue"]
        if not dialogue.get("available"):
            return {}
        return {choice["topic_id"]: choice for choice in dialogue["choices"]}

    def _delivery(self, recorded: list[dict]) -> dict | None:
        dialogue = self._panels(recorded)[-1]["dialogue"]
        return dialogue.get("delivery")

    def _open_line_session(self) -> None:
        open_or_refresh_dialogue(self.player, self.host, "合成招呼。")

    def _deliver_open_topic(self) -> object:
        session = live_dialogue_session(self.player)
        delivery = select_authored_topic(
            self.player,
            self.host,
            _OPEN_TOPIC,
            selection_id="sel-refresh-open",
            expected_context_id=None if session is None else session.context_id,
        )
        self.assertEqual(delivery.kind, "formal")
        return delivery

    # -- source matrix ---------------------------------------------------

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_inventory_writer_refreshes_without_any_session_context(self):
        """Carried item: a no-session write reaches both live connections."""
        self._open_line_session()
        self._deliver_open_topic()
        first, first_recorded = self._register_watcher(self.player)
        second, second_recorded = self._register_watcher(self.player)
        self.assertEqual(self._choices(first_recorded)[_CARRIES_TOPIC]["availability"], TOPIC_LOCKED)

        plan = plan_inventory_delta(self.player, additions=(_ITEM_KEY,))
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            apply_inventory_plan(plan)
        self.assertEqual(len(list(callbacks)), 1)

        for recorded in (first_recorded, second_recorded):
            choice = self._choices(recorded)[_CARRIES_TOPIC]
            self.assertEqual(choice["availability"], TOPIC_OPEN)
            self.assertIsNone(choice["requirement_hint"])
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)

    def test_no_session_owner_refresh_is_a_silent_success(self):
        """A committed write with no watcher and no session creates nothing."""
        self.assertIsNone(live_dialogue_session(self.player))
        plan = plan_inventory_delta(self.player, additions=(_ITEM_KEY,))
        with self.captureOnCommitCallbacks(execute=True):
            apply_inventory_plan(plan)
        self.assertEqual(self.player.db.inventory, [_ITEM_KEY])
        self.assertIsNone(live_dialogue_session(self.player))
        self.assertEqual(tuple(watchers.watchers_for(self.player)), ())

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_outer_rollback_publishes_nothing(self):
        """Inventory and skill writes inside a failed transaction refresh nothing."""
        self._open_line_session()
        _real, recorded = self._register_watcher(self.player)
        baseline = self._choices(recorded)[_CARRIES_TOPIC]["availability"]
        self.assertEqual(baseline, TOPIC_LOCKED)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    apply_inventory_plan(
                        plan_inventory_delta(self.player, additions=(_ITEM_KEY,))
                    )
                    award_practice_xp(self.player, _SKILL_KEY, 1)
                    raise RuntimeError("owning operation rolled back")
            except RuntimeError:
                pass
        self.assertEqual(list(callbacks), [])
        # Only the initial snapshot exists; no committed-scale update followed.
        self.assertEqual(len(self._panels(recorded)), 1)
        self.assertNotIn(_IDENTITY_TOPIC, self._choices(recorded))

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_worn_equipment_crosses_the_threshold_and_keeps_the_delivery(self):
        """Worn exposure bias re-projects choices; delivered wording survives."""
        self._open_line_session()
        delivery = self._deliver_open_topic()
        _real, recorded = self._register_watcher(self.player)
        self.assertEqual(
            self._choices(recorded)[_EXPOSURE_TOPIC]["availability"], TOPIC_LOCKED
        )

        self.player.db.inventory = [_ACCESSORY_KEY]
        with self.captureOnCommitCallbacks(execute=True):
            result = toggle_equipment(self.player, _ACCESSORY_KEY)
        self.assertEqual(result.outcome, "success")

        choices = self._choices(recorded)
        self.assertEqual(choices[_EXPOSURE_TOPIC]["availability"], TOPIC_OPEN)
        self.assertIsNone(choices[_EXPOSURE_TOPIC]["requirement_hint"])
        self.assertEqual(self._delivery(recorded)["delivery_id"], delivery.delivery_id)
        self.assertEqual(
            [line["text"] for line in self._delivery(recorded)["lines"]],
            [line.text for line in delivery.lines],
        )

        with self.captureOnCommitCallbacks(execute=True):
            toggle_equipment(self.player, _ACCESSORY_KEY)
        self.assertEqual(
            self._choices(recorded)[_EXPOSURE_TOPIC]["availability"], TOPIC_LOCKED
        )

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_base_exposure_transition_refreshes_once_after_commit(self):
        """``apply_event`` publishes the converged exposure exactly once."""
        self._open_line_session()
        delivery = self._deliver_open_topic()
        _real, recorded = self._register_watcher(self.player)
        rule = Rule(
            id="t_refresh_exposure_up",
            when={"event": "t_refresh_exposure"},
            then={"field": "exposure", "set": EXPOSURE_LEVELS[_EXPOSURE_THRESHOLD]},
        )
        with patch("world.rules.sexual_transitions._RULES", [rule]):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                changes = apply_event(self.player, "t_refresh_exposure")
        self.assertEqual(changes, {"exposure": "up"})
        self.assertEqual(len(list(callbacks)), 1)
        self.assertEqual(
            self._choices(recorded)[_EXPOSURE_TOPIC]["availability"], TOPIC_OPEN
        )
        self.assertEqual(self._delivery(recorded)["delivery_id"], delivery.delivery_id)

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_identity_tag_change_refreshes_but_persona_prose_does_not(self):
        """Structured identities are the source; persona prose is not."""
        self._open_line_session()
        delivery = self._deliver_open_topic()
        _real, recorded = self._register_watcher(self.player)
        self.assertNotIn(_IDENTITY_TOPIC, self._choices(recorded))

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            set_social_identities(self.player, [_IDENTITY_KEY])
        self.assertEqual(len(list(callbacks)), 1)
        self.assertEqual(
            self._choices(recorded)[_IDENTITY_TOPIC]["availability"], TOPIC_OPEN
        )
        self.assertEqual(self._delivery(recorded)["delivery_id"], delivery.delivery_id)

        panels_before = len(self._panels(recorded))
        with self.captureOnCommitCallbacks(execute=True) as prose_callbacks:
            # Persona prose that literally names the identity term is not a
            # structured assignment: it neither qualifies the topic nor
            # schedules a refresh (there is no prose source hook).
            self.player.attributes.add(
                "npc_persona_card", {"prose": f"這個人自稱{_IDENTITY_KEY}。"}
            )
        self.assertEqual(list(prose_callbacks), [])
        self.assertEqual(len(self._panels(recorded)), panels_before)

        with self.captureOnCommitCallbacks(execute=True):
            set_social_identities(self.player, [])
        self.assertNotIn(_IDENTITY_TOPIC, self._choices(recorded))

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_skill_ownership_and_proficiency_flips_are_separate(self):
        """Ownership and proficiency cross their own thresholds independently."""
        self._open_line_session()
        self._deliver_open_topic()
        _real, recorded = self._register_watcher(self.player)
        self.assertNotIn(_OWNED_TOPIC, self._choices(recorded))
        self.assertNotIn(_PROFICIENT_TOPIC, self._choices(recorded))

        definition = SYNTH_SKILLS[_SKILL_KEY]
        self.assertTrue(skill_identity_eligible(self.player, definition))
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.assertTrue(
                grant_owned_skill(self.player, _SKILL_KEY, SYNTH_SKILLS)
            )
        self.assertEqual(len(list(callbacks)), 1)
        choices = self._choices(recorded)
        self.assertEqual(choices[_OWNED_TOPIC]["availability"], TOPIC_OPEN)
        self.assertNotIn(_PROFICIENT_TOPIC, choices)

        # A repeated grant writes nothing and schedules nothing.
        with self.captureOnCommitCallbacks(execute=True) as repeat_callbacks:
            self.assertFalse(
                grant_owned_skill(self.player, _SKILL_KEY, SYNTH_SKILLS)
            )
        self.assertEqual(list(repeat_callbacks), [])

        with self.captureOnCommitCallbacks(execute=True) as xp_callbacks:
            award_practice_xp(self.player, _SKILL_KEY, SKILL_PROFICIENCY_XP_PER_LEVEL)
        self.assertEqual(len(list(xp_callbacks)), 1)
        self.assertEqual(
            self._choices(recorded)[_PROFICIENT_TOPIC]["availability"], TOPIC_OPEN
        )

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_lineage_seed_refreshes_the_owned_player_and_skips_unowned_bodies(self):
        """The auto-seed hook refreshes a player and stays silent on an NPC."""
        self._open_line_session()
        _real, recorded = self._register_watcher(self.player)
        self.player.db.skills = {"active": [_SKILL_KEY], "passive": []}
        self.player.db.skill_proficiency = {}
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            apply_lineage_auto_seed(self.player)
        self.assertEqual(len(list(callbacks)), 1)
        self.assertEqual(
            self._choices(recorded)[_OWNED_TOPIC]["availability"], TOPIC_OPEN
        )

        bystander = create_object(NPC, key="合成無主旁觀者", location=self.room)
        with self.captureOnCommitCallbacks(execute=True) as npc_callbacks:
            apply_lineage_auto_seed(bystander)
        self.assertEqual(list(npc_callbacks), [])

    def test_skill_write_on_a_possessed_body_refreshes_the_acting_body(self):
        """A possession-origin write refreshes the body the player is acting as."""
        companion = create_object(NPC, key="合成刷新同伴", location=self.room)
        join_party(companion, self.player)
        enter_possession(self.player, companion)
        self.addCleanup(release_possession, self.player, companion, "handback")
        self.assertEqual(affected_dialogue_owners(companion), (self.player,))

        with patch(
            "web.webclient.presentation.dialogue_push.push_dialogue_update"
        ) as push:
            with self.captureOnCommitCallbacks(execute=True):
                award_practice_xp(companion, _SKILL_KEY, 1)
        push.assert_called_once_with(companion)

    def test_prior_owner_is_refreshed_after_a_detach(self):
        """A pre-detach owner capture still refreshes the owner that lost a body."""
        companion = create_object(NPC, key="合成離隊同伴", location=self.room)
        join_party(companion, self.player)
        self.assertEqual(affected_dialogue_owners(companion), (self.player,))
        self.assertEqual(affected_dialogue_owners(self.player), (self.player,))

        leave_party(companion, self.player, reason="test")
        self.assertEqual(affected_dialogue_owners(companion), ())
        affected = affected_dialogue_owners(companion, prior_owner=self.player)
        self.assertEqual(affected, (self.player,))

        # An unrelated (sibling) character is never dragged in by an account
        # or a party read.
        self.assertNotIn(self.char2, affected_dialogue_owners(self.player))
        with patch(
            "web.webclient.presentation.dialogue_push.push_dialogue_update"
        ) as push:
            with self.captureOnCommitCallbacks(execute=True):
                for owner in affected:
                    queue_dialogue_refresh((owner,), cause="party_change")
        push.assert_called_once_with(self.player)

    def test_stale_possession_mirror_without_a_binding_resolves_no_owner(self):
        """Matching mirror references never substitute for a lawful binding."""
        companion = create_object(NPC, key="合成偽造同伴", location=self.room)
        companion.db.possessed_by = int(self.player.pk)
        self.player.db.possession = {
            "npc_dbid": int(companion.pk),
            "since_tick": 0,
        }
        self.addCleanup(setattr, self.player.db, "possession", None)
        self.addCleanup(setattr, companion.db, "possessed_by", None)

        self.assertEqual(affected_dialogue_owners(companion), ())
        # The owner's refresh must not be redirected to the unbound body.
        with patch(
            "web.webclient.presentation.dialogue_push.push_dialogue_update"
        ) as push:
            with self.captureOnCommitCallbacks(execute=True):
                queue_dialogue_refresh((self.player,), cause="control")
        push.assert_called_once_with(self.player)

    def test_generated_binding_phase_is_resolved_at_callback_time(self):
        """The callback re-resolves the generated phase and host binding.

        The generated provider seam is replaced here, so this is provider-seam
        coverage of the source-neutral callback contract; production published
        package acceptance belongs to ``authored-dialogue-generated-packages``.
        """
        generated = create_object(NPC, key="合成生成刷新角色", location=self.room)
        generated.components.add(
            ScriptedDialogue.create(
                generated, dialogue_key="scene_role:pkg_synth:elder"
            )
        )
        open_or_refresh_dialogue(self.player, generated, "生成招呼。")
        _real, recorded = self._register_watcher(self.player)

        def _source(context):
            phase_id = getattr(context.source_identity, "phase_id", None)
            local = "open_a" if phase_id == "phase_1" else "open_b"
            return ResolvedDialogueSource(
                identity=context.source_identity,
                host_key=context.host_key,
                dialogue=AuthoredDialogue(
                    greeting="生成招呼。",
                    topics=(
                        AuthoredTopic(
                            topic_id=f"phase.{local}",
                            keyword=f"生成{local}",
                            label=f"生成{local}",
                            fallback=_scene(f"t_generated_{local}", "生成答覆。"),
                        ),
                    ),
                ),
                phase_revision=1 if phase_id == "phase_1" else 2,
            )

        with patch(
            "world.rules.dialogue.generated_dialogue_for",
            return_value=SimpleNamespace(revision=1),
        ), patch(
            "world.rules.dialogue_sources.resolve_dialogue_source",
            side_effect=_source,
        ), self.captureOnCommitCallbacks(execute=False) as callbacks:
            queue_dialogue_refresh((self.player,), cause="inventory")
        self.assertEqual(len(list(callbacks)), 1)

        # The published phase advances after the write but before commit
        # callbacks run; the callback must project the NEW phase.
        with patch(
            "world.rules.dialogue.generated_dialogue_for",
            return_value=SimpleNamespace(revision=2),
        ), patch(
            "world.rules.dialogue_sources.resolve_dialogue_source",
            side_effect=_source,
        ):
            for callback in list(callbacks):
                callback()

        choices = self._choices(recorded)
        self.assertEqual(set(choices), {"phase.open_b"})
        self.assertEqual(self._delivery(recorded)["lines"][-1]["text"], "生成招呼。")

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-refresh-includes-generated-scene-contexts"
    )
    def test_generated_context_qualification_refreshes_through_the_equipment_hook(
        self,
    ):
        """A generated topic's exposure qualification refreshes after commit.

        The source comes from the published generated binding, never from a
        static dialogue-registry entry, and the immutable authored package
        payload is exactly what it was before the refresh.
        """
        generated = create_object(NPC, key="合成生成衣著角色", location=self.room)
        generated.components.add(
            ScriptedDialogue.create(
                generated, dialogue_key="scene_role:pkg_synth:elder"
            )
        )
        open_or_refresh_dialogue(self.player, generated, "生成招呼。")
        authored = AuthoredDialogue(
            greeting="生成招呼。",
            topics=(
                AuthoredTopic(
                    topic_id="scene.generated_exposure",
                    keyword="生成衣著",
                    label="生成衣著",
                    fallback=_scene(
                        "t_generated_exposure_formal", "生成衣著答覆。"
                    ),
                    requires=Exposure(minimum=_EXPOSURE_THRESHOLD),
                    unavailable="locked",
                    refusal=_scene(
                        "t_generated_exposure_refusal", _SENTINEL_REFUSAL
                    ),
                ),
            ),
        )

        def _source(context):
            return ResolvedDialogueSource(
                identity=context.source_identity,
                host_key=context.host_key,
                dialogue=authored,
                phase_revision=1,
            )

        self.player.db.inventory = [_ACCESSORY_KEY]
        with patch(
            "world.rules.dialogue.generated_dialogue_for",
            return_value=SimpleNamespace(revision=1),
        ), patch(
            "world.rules.dialogue_sources.resolve_dialogue_source",
            side_effect=_source,
        ):
            _real, recorded = self._register_watcher(self.player)
            self.assertEqual(
                self._choices(recorded)["scene.generated_exposure"][
                    "availability"
                ],
                TOPIC_LOCKED,
            )
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                result = toggle_equipment(self.player, _ACCESSORY_KEY)
            self.assertEqual(result.outcome, "success")
            self.assertEqual(len(list(callbacks)), 1)

        choices = self._choices(recorded)
        self.assertEqual(
            choices["scene.generated_exposure"]["availability"], TOPIC_OPEN
        )
        self.assertIsNone(choices["scene.generated_exposure"]["requirement_hint"])
        # The refresh projects the package; it never rewrites it.
        self.assertEqual(
            authored.topics[0].requires, Exposure(minimum=_EXPOSURE_THRESHOLD)
        )
        self.assertEqual(authored.greeting, "生成招呼。")

    def test_queue_validates_its_inputs_and_never_creates_state(self):
        with self.assertRaises(ValueError):
            queue_dialogue_refresh((self.player,), cause="")
        with self.assertRaises(TypeError):
            queue_dialogue_refresh(self.player, cause="inventory")

        self.assertEqual(affected_dialogue_owners(None), ())
        self.assertIsNone(live_dialogue_session(self.player))
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            queue_dialogue_refresh((), cause="inventory")
        self.assertEqual(list(callbacks), [])
        self.assertIsNone(live_dialogue_session(self.player))


if __name__ == "__main__":
    import unittest

    unittest.main()
