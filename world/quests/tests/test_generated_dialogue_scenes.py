"""Generated-package scene contract, immutable publication and trusted provider.

One change owns the exact generated dialogue shape: shared actor-first topic
primitives with local IDs namespaced by package/role/phase, external effect
associations, whole-package validation before the existing immutable DB
publication, and the trusted runtime provider that re-resolves the published
package role and its currently selected phase. A removed response-only payload
resolves to no source, never to a converted view.
"""

from unittest.mock import patch
import json

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.components import ScriptedDialogue
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from tools.spec_traceability import covers_requirement
from world.lore.dialogue.codec import (
    parse_generated_scene_id,
    parse_generated_topic_id,
)
from world.lore.dialogue import DIALOGUE_SNAPSHOT
from world.quests import scene_store
from world.quests.encounters import publish_scene_package
from world.quests.scene_package import (
    ScenePackageError,
    validate_scene_package,
)
from world.quests.scene_store import ScenePackageConflictError
from world.quests.tests._compile_helpers import _issuer_key
from world.quests.tests._fixtures import RegistryIsolationMixin, register_catalog_once
from world.quests.tests._scene_package_fixtures import (
    LONG_PROSE,
    dialogue as _dialogue,
    anchor_locator,
    guild_package,
    package as _package,
    phase as _phase,
    quest_payload,
    role,
    topic as _topic,
    topic_scene as _topic_scene,
)
from world.rules.dialogue_sources import dialogue_source_for_host
from world.rules.dialogue import (
    complete_dialogue_delivery,
    live_dialogue_session,
    select_authored_topic,
)
from world.quests.story_dialogue import transition_story_dialogue
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.dialogue import dialogue_presenter
from web.webclient.presentation.registry import PanelUnavailableError
from web.webclient.actions.exploration_actions import validate_talk_scripted_descriptor
from world.narrative.dialogue_reading import completed_topic_ids

from commands.talk import CmdsTalk
from world.narrative import dispatch
from world.narrative.authoring import confirm_draft, save_draft
from world.narrative.dispatch_runner import StageClients, run_next
from world.narrative.models import CreativeRequest
from world.narrative.tests.test_dream_dispatch_runner import REQUIREMENTS
from world.narrative.tests.test_story_director_beats import (
    StoryDirectorBeatsTestCase,
    _recorded,
)
from world.quests.tests._compile_helpers import CompileRegistryIsolation
from world.quests.encounter_activation import activate_scene_encounter
from world.rules.tests._combat_session_helpers import open_synthetic_scope

REFUSAL_TEXT = "她垂下眼，沒有回答。"


def _rich_package(**overrides) -> dict:
    """A package whose declared topics carry every generated scene feature."""
    payload = _package()
    mother = _dialogue("mother")
    searching = mother["phases"][0]
    searching["topics"] = [
        _topic("open", "線索", LONG_PROSE),
        _topic(
            "first",
            "起頭",
            LONG_PROSE,
        ),
        _topic(
            "second",
            "接續",
            LONG_PROSE,
            predecessors=["first"],
            disclosure="pure_chain",
        ),
        _topic(
            "qualified",
            "追問",
            LONG_PROSE,
            requires={
                "kind": "quest_is",
                "definition_key": "placeholder",
                "state": "not_accepted",
            },
            predecessors=["first"],
        ),
        _topic(
            "locked",
            "衣著",
            LONG_PROSE,
            requires={"kind": "exposure", "minimum": 2},
            unavailable="locked",
            refusal=_topic_scene(
                "locked_refusal", REFUSAL_TEXT, actor_line="你把視線移開。"
            ),
        ),
    ]
    payload["dialogue"] = [mother, _dialogue("daughter")]
    payload.update(overrides)
    _bind_definition(payload, _definition_key(payload))
    return payload


def _definition_key(payload: dict) -> str:
    from world.quests.compile.compiler import compile_blueprint_core

    return compile_blueprint_core(
        payload["quest"], package_roles=frozenset(r["role_id"] for r in payload["roles"])
    ).definition.key


def _bind_definition(payload: dict, definition_key: str) -> None:
    for entry in payload["dialogue"]:
        for phase in entry["phases"]:
            for topic in phase["topics"]:
                requires = topic.get("requires")
                if requires and requires.get("definition_key") == "placeholder":
                    requires["definition_key"] = definition_key


def _all_topics(payload: dict):
    for entry in payload["dialogue"]:
        for phase in entry["phases"]:
            for topic in phase["topics"]:
                yield entry["role_id"], phase["phase_id"], topic


class GeneratedSceneContractTests(EvenniaTest):
    """The closed generated-local schema and deterministic namespacing."""

    def _validated(self) -> dict:
        payload = _rich_package()
        _bind_definition(payload, _definition_key(payload))
        return payload

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_topics_and_scenes_are_namespaced_by_package_role_and_phase(self):
        payload = self._validated()
        definition = validate_scene_package(payload)
        mother = definition.role_dialogue("mother")
        searching = mother.phases[0]
        self.assertTrue(searching.topics)
        for topic in searching.topics:
            package_id, role_id, phase_id, local_topic = parse_generated_topic_id(
                topic.topic_id
            )
            self.assertEqual(
                (package_id, role_id, phase_id),
                (definition.package_id, "mother", searching.phase_id),
            )
            self.assertTrue(local_topic)
            for scene in (
                topic.fallback,
                *(variant.scene for variant in topic.variants),
            ):
                scene_package, scene_role, scene_phase, local_scene = (
                    parse_generated_scene_id(scene.scene_id)
                )
                self.assertEqual(
                    (scene_package, scene_role, scene_phase),
                    (definition.package_id, "mother", searching.phase_id),
                )
                self.assertTrue(local_scene)

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_a_response_only_topic_is_rejected(self):
        payload = _rich_package()
        payload["dialogue"][0]["phases"][0]["topics"] = [
            {"keyword": "舊格式", "response": LONG_PROSE}
        ]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(payload)
        self.assertIn("topic_id", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_duplicate_topic_and_variant_ids_are_rejected(self):
        payload = _rich_package()
        topic = _topic("open", "線索", LONG_PROSE)
        variant = {
            "variant_id": "twice",
            "priority": 1,
            "when": {"kind": "exposure", "minimum": 0},
            "scene": _topic_scene("open_variant", LONG_PROSE),
        }
        topic["variants"] = [variant, {**variant, "scene": _topic_scene("open_variant_2", LONG_PROSE)}]
        payload["dialogue"][0]["phases"][0]["topics"].append(topic)
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(payload)
        self.assertIn("open", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_dangling_and_cyclic_predecessors_are_rejected(self):
        for predecessors in (["missing"], ["second"], ["first"]):
            with self.subTest(predecessors=predecessors):
                payload = _rich_package()
                searching = payload["dialogue"][0]["phases"][0]
                searching["topics"] = [
                    _topic("first", "起頭", LONG_PROSE, predecessors=predecessors),
                    _topic(
                        "second",
                        "接續",
                        LONG_PROSE,
                        predecessors=["first"],
                        disclosure="pure_chain",
                    ),
                ]
                with self.assertRaises(ScenePackageError):
                    validate_scene_package(payload)

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_a_cross_phase_predecessor_is_dangling(self):
        payload = _rich_package()
        daily = payload["dialogue"][0]["phases"][2]
        daily["topics"] = [
            _topic("open", "近況", LONG_PROSE, predecessors=["closed_topic"])
        ]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(payload)
        self.assertIn("predecessor", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_effect_scope_requires_a_commission_qualification_and_refusal(self):
        definition_key = _definition_key(_rich_package())
        cases = ("no_requires", "no_refusal", "unknown_verb", "foreign_reference")
        for name in cases:
            with self.subTest(case=name):
                payload = _rich_package()
                phase = payload["dialogue"][0]["phases"][0]
                topic = phase["topics"][0]
                topic["requires"] = {
                    "kind": "quest_is",
                    "definition_key": definition_key,
                    "state": "not_accepted",
                }
                if name != "no_refusal":
                    topic["refusal"] = _topic_scene("effect_refusal", REFUSAL_TEXT)
                if name == "no_requires":
                    topic.pop("requires")
                verb = "grant_reward" if name == "unknown_verb" else "offer_commission"
                reference = (
                    "npc:foreign_commission"
                    if name == "foreign_reference"
                    else definition_key
                )
                phase["topic_effects"] = [
                    {
                        "topic_id": "open",
                        "verb": verb,
                        "reference": reference,
                    }
                ]
                with self.assertRaises(ScenePackageError):
                    validate_scene_package(payload)

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_an_effect_on_a_non_commission_role_is_rejected(self):
        payload = _rich_package()
        definition_key = _definition_key(payload)
        daughter = payload["dialogue"][1]
        phase = daughter["phases"][0]
        phase["topics"] = [
            _topic(
                "open",
                "線索",
                LONG_PROSE,
                requires={
                    "kind": "quest_is",
                    "definition_key": definition_key,
                    "state": "not_accepted",
                },
                refusal=_topic_scene("daughter_refusal", REFUSAL_TEXT),
            )
        ]
        phase["topic_effects"] = [
            {
                "topic_id": "open",
                "verb": "offer_commission",
                "reference": definition_key,
            }
        ]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(payload)
        self.assertIn("commission", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_an_effect_on_a_pure_chain_successor_is_rejected(self):
        payload = _rich_package()
        definition_key = _definition_key(payload)
        phase = payload["dialogue"][0]["phases"][0]
        phase["topic_effects"] = [
            {
                "topic_id": "second",
                "verb": "offer_commission",
                "reference": definition_key,
            }
        ]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(payload)
        self.assertIn("pure-chain", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_oversized_scenes_and_bundles_are_rejected(self):
        # Every individual field is legal; the scene's canonical bytes exceed
        # the 8,192-byte scene budget.
        payload = _rich_package()
        fallback = payload["dialogue"][0]["phases"][0]["topics"][0]["fallback"]
        fallback["lines"] = [
            {"kind": "speech", "speaker": "actor", "text": "字" * 1900},
            {"kind": "speech", "speaker": "host", "text": "字" * 1900},
        ]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(payload)
        self.assertIn("canonical UTF-8", str(caught.exception))

        # Two individually legal scenes whose selected public bundle exceeds
        # the 16,384-byte delivery budget.
        bundled = _rich_package()
        topics = bundled["dialogue"][0]["phases"][0]["topics"]
        topics.append(
            _topic(
                "third",
                "再續",
                LONG_PROSE,
                predecessors=["first"],
                disclosure="pure_chain",
            )
        )
        for topic in topics:
            if topic["topic_id"] in {"first", "second", "third"}:
                topic["fallback"]["lines"] = [
                    {"kind": "speech", "speaker": "actor", "text": "字" * 650},
                    *[
                        {"kind": "narration", "text": "字" * 650}
                        for _ in range(2)
                    ],
                ]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(bundled)
        self.assertIn("public successors", str(caught.exception))

    def test_content_identity_includes_the_dialogue(self):
        first = _rich_package()
        second = _rich_package()
        second["dialogue"][0]["phases"][0]["topics"][0]["fallback"]["lines"][1][
            "text"
        ] = LONG_PROSE + "（改寫）"
        first_id = validate_scene_package(first).package_id
        second_id = validate_scene_package(second).package_id
        self.assertNotEqual(first_id, second_id)


class GeneratedPackagePublicationTests(RegistryIsolationMixin, EvenniaTest):
    """Publication is immutable, idempotent and never a static registration."""

    def _payload(self) -> dict:
        return _rich_package()

    def test_publication_is_idempotent_and_conflicting_content_is_refused(self):
        payload = self._payload()
        first = publish_scene_package(payload, owner="tester", source_id="beat-1")
        again = publish_scene_package(payload, owner="tester", source_id="beat-1")
        self.assertTrue(first.created)
        self.assertFalse(again.created)
        self.assertEqual(first.package_id, again.package_id)
        changed = self._payload()
        changed["dialogue"][0]["phases"][0]["topics"][0]["fallback"]["lines"][0][
            "text"
        ] = "改寫後的第一句。"
        with self.assertRaises(ScenePackageConflictError):
            publish_scene_package(changed, owner="tester", source_id="beat-1")

    def test_publication_writes_no_static_registry_or_source_tree(self):
        before = dict(DIALOGUE_SNAPSHOT)
        publish_scene_package(self._payload(), owner="tester", source_id="beat-2")
        self.assertEqual(dict(DIALOGUE_SNAPSHOT), before)
        self.assertIsNone(
            DIALOGUE_SNAPSHOT.get("scene_role:anything")
        )

    def test_a_durable_row_revalidates_to_byte_identical_namespaced_ids(self):
        published = publish_scene_package(
            self._payload(), owner="tester", source_id="beat-3"
        )
        row = scene_store.read_package(published.package_id)
        reloaded = validate_scene_package(row.payload)
        self.assertEqual(reloaded.package_id, published.package_id)
        before = {
            topic.topic_id
            for entry in published.definition.dialogue
            for phase in entry.phases
            for topic in phase.topics
        }
        after = {
            topic.topic_id
            for entry in reloaded.dialogue
            for phase in entry.phases
            for topic in phase.topics
        }
        self.assertEqual(before, after)


class GeneratedSourceProviderTests(RegistryIsolationMixin, EvenniaTest):
    """The trusted provider re-resolves the package role and current phase."""

    def _active_host(self, payload: dict):
        from world.quests.compile.compiler import compile_blueprint_core
        from typeclasses.rooms import AnchorRoom
        from world.quests.tests._compile_helpers import _anchor_key

        published = publish_scene_package(payload, owner="tester")
        host = create_object(NPC, key="生成角色", location=self.room1)
        host.components.add(
            ScriptedDialogue.create(
                host,
                dialogue_key=f"scene_role:{published.package_id}:mother",
            )
        )
        binding = scene_store.bind_role(
            scene_store.read_package(published.package_id), "mother", host.pk
        )
        self.assertEqual(binding.npc_id, host.pk)
        scene_store.set_dialogue_phase(
            scene_store.read_package(published.package_id),
            "mother",
            validate_scene_package(payload).role_dialogue("mother").initial_phase,
        )
        return published, host

    def test_the_provider_returns_the_complete_current_phase_and_effects(self):
        payload = _rich_package()
        definition_key = _definition_key(payload)
        phase = payload["dialogue"][0]["phases"][0]
        phase["topics"][0]["requires"] = {
            "kind": "quest_is",
            "definition_key": definition_key,
            "state": "not_accepted",
        }
        phase["topics"][0]["refusal"] = _topic_scene(
            "open_refusal", REFUSAL_TEXT, actor_line="你停頓了一下。"
        )
        phase["topic_effects"] = [
            {
                "topic_id": "open",
                "verb": "offer_commission",
                "reference": definition_key,
            }
        ]
        _published, host = self._active_host(payload)
        source = dialogue_source_for_host(host)
        self.assertIsNotNone(source)
        definition = validate_scene_package(payload)
        self.assertEqual(source.identity.package_id, definition.package_id)
        self.assertEqual(source.identity.role_id, "mother")
        self.assertEqual(
            [topic.keyword for topic in source.dialogue.topics],
            ["線索", "起頭", "接續", "追問", "衣著"],
        )
        self.assertEqual(source.phase_revision, 0)
        self.assertEqual(len(source.effects), 1)
        declared = next(iter(source.effects.values()))
        self.assertEqual(declared.verb, "offer_commission")
        self.assertEqual(declared.reference, definition_key)

    def test_a_removed_response_only_payload_resolves_to_no_source(self):
        # A pre-cutover row written directly to the immutable store: it cannot
        # pass the current validator, so the provider must not convert or
        # partially deliver it.
        row, _created = scene_store.publish_package(
            package_id="pkg_legacy_response_only",
            source_id=None,
            owner_id="tester",
            payload={
                "dialogue": [
                    {
                        "role_id": "mother",
                        "initial_phase": "searching",
                        "phases": [
                            {
                                "phase_id": "searching",
                                "conditions": [{"default": True}],
                                "greeting": LONG_PROSE,
                                "topics": [{"keyword": "線索", "response": LONG_PROSE}],
                            }
                        ],
                    }
                ]
            },
        )
        host = create_object(NPC, key="舊格式角色", location=self.room1)
        host.components.add(
            ScriptedDialogue.create(
                host, dialogue_key=f"scene_role:{row.package_id}:mother"
            )
        )
        scene_store.bind_role(row, "mother", host.pk)
        with patch("world.rules.dialogue_sources.log_warn") as log:
            self.assertIsNone(dialogue_source_for_host(host))
        log.assert_called_once()
        self.assertEqual(log.call_args.args[0], "dialogue_source_rejected")

    def _playable_host(self):
        register_catalog_once()
        payload = _rich_package()
        published, host = self._active_host(payload)
        player = create_object(PlayerCharacter, key="生成訪客", location=self.room1)
        host.location = self.room1
        source = dialogue_source_for_host(host)
        topic_id = next(
            topic.topic_id for topic in source.dialogue.topics if topic.keyword == "線索"
        )
        select_authored_topic(
            player,
            host,
            topic_id,
            selection_id="generated-1",
            expected_context_id=None,
        )
        return published, host, player

    def test_a_qualified_completion_never_returns_as_chain_playback(self):
        _published, host, player = self._playable_host()
        from world.rules.dialogue import chain_deliveries

        def topic_id(keyword: str) -> str:
            return next(
                topic.topic_id
                for topic in dialogue_source_for_host(host).dialogue.topics
                if topic.keyword == keyword
            )

        def select(keyword: str, selection_id: str):
            session = live_dialogue_session(player)
            return select_authored_topic(
                player,
                host,
                topic_id(keyword),
                selection_id=selection_id,
                expected_context_id=session.context_id,
            )

        root = select("起頭", "root-1")
        complete_dialogue_delivery(
            player,
            delivery_id=root.delivery_id,
            context_id=root.context_id,
            topic_id=root.topic_id,
            scene_revision=root.scene_revision,
        )
        qualified = select("追問", "qualified-1")
        complete_dialogue_delivery(
            player,
            delivery_id=qualified.delivery_id,
            context_id=qualified.context_id,
            topic_id=qualified.topic_id,
            scene_revision=qualified.scene_revision,
        )
        # Selecting the root again must not resurrect the explicitly
        # completed qualified topic as a public chain node.
        select("起頭", "root-2")
        session = live_dialogue_session(player)
        nodes = chain_deliveries(session, host, actor=player)
        self.assertNotIn(qualified.topic_id, [node.delivery.topic_id for node in nodes])

    def test_a_cancelled_package_suppresses_the_stored_playback(self):
        published, _host, player = self._playable_host()
        scene_store.cancel_package(published.package_id)
        with self.assertRaises(PanelUnavailableError):
            dialogue_presenter(PresentationContext(actor=player, protocol_version=1))

    def test_the_panel_projects_only_the_current_phase_completions(self):
        published, host, player = self._playable_host()
        session = live_dialogue_session(player)
        delivery = session.delivery
        complete_dialogue_delivery(
            player,
            delivery_id=delivery.delivery_id,
            context_id=delivery.context_id,
            topic_id=delivery.topic_id,
            scene_revision=delivery.scene_revision,
        )
        completed = delivery.topic_id

        with self.captureOnCommitCallbacks(execute=True):
            transition_story_dialogue(
                published.package_id,
                "mother",
                expected_revision=0,
                provenance={"closure": True},
                tick=9,
            )
        panel = dialogue_presenter(PresentationContext(actor=player, protocol_version=1))
        self.assertEqual(panel["completed_topic_ids"], [])

        with self.captureOnCommitCallbacks(execute=True):
            transition_story_dialogue(
                published.package_id,
                "mother",
                expected_revision=1,
                provenance={"closure": False},
                tick=10,
            )
        panel = dialogue_presenter(PresentationContext(actor=player, protocol_version=1))
        self.assertEqual(panel["completed_topic_ids"], [completed])


def _enabled(_name):
    return True


class GeneratedDispatchAcceptanceTests(
    EvenniaCommandTestMixin, CompileRegistryIsolation, StoryDirectorBeatsTestCase
):
    """The real dream dispatch publishes, then plays offline through both surfaces."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "items",
            "guild_branches",
            "archetypes",
            "anchors",
            "anchor_placements",
        )
        super().setUp()
        from world.ai.scenario_director import register_scenario_director
        from world.quests.tests._compile_helpers import _anchor_key

        register_scenario_director()
        from typeclasses.rooms import AnchorRoom

        self.anchor = _anchor_key()
        self.acceptance_room = create_object(AnchorRoom, key="生成南門")
        self.acceptance_room.db.anchor_key = self.anchor
        self.owner.location = self.acceptance_room
        self.package_payload = _rich_package()
        self.owner.guild_rank = self.package_payload["quest"]["rank"]

    def _queued_work(self):
        draft = save_draft(
            owner_id=str(self.owner.pk),
            direction={
                "summary": "在南門遇見一個女孩，帶她找媽媽。",
                "kind": "new_story",
                "thread_id": None,
                "effects": [],
                "revisions": [],
                "requirements": list(REQUIREMENTS),
            },
            tick=self.now,
        )
        request = confirm_draft(
            draft_id=draft.draft_id, owner_id=str(self.owner.pk), tick=self.now
        )
        work = dispatch.find_by_submission(request.submission_key)
        self.assertIsNotNone(work)
        return request, work

    def _extended_blueprint(self):
        extended = dict(self.package_payload["quest"])
        extended["display_name"] = self.package_payload["display_name"]
        for key in (
            "roles",
            "relationships",
            "knowledge",
            "encounters",
            "dialogue",
            "commissions",
            "outcome_groups",
        ):
            if key in self.package_payload:
                extended[key] = self.package_payload[key]
        return extended

    def _client(self):
        client = _recorded("quest_seed")
        client.add_response(
            lambda descriptor: descriptor.schema_id == "scenario_director",
            json.dumps(self._extended_blueprint(), ensure_ascii=False),
        )
        return client

    def _play_host(self, package_id: str, role_id: str):
        from evennia.objects.models import ObjectDB

        binding = scene_store.get_role_binding(package_id, role_id)
        return ObjectDB.objects.filter(id=binding.npc_id).first()

    def test_a_dispatched_generated_host_plays_offline_through_web_and_text(self):
        _request, work = self._queued_work()
        client = self._client()
        with self.captureOnCommitCallbacks(execute=True):
            result = run_next(
                clients=StageClients(story=client, scenario=client),
                capability_enabled=_enabled,
                tick=self.now,
            ).result
        self.assertEqual(result.outcome, "arranged")
        self.assertEqual(len(scene_store.list_packages()), 1)

        # The production scene route rendered the scene-specific prompt and
        # carried the immutable reference frame; the checkpoint preserves every
        # dialogue declaration byte for byte.
        scene_call = client.calls[1]
        self.assertIn("場景企劃", scene_call.messages[0]["content"])
        frame = json.loads(scene_call.messages[1]["content"])
        self.assertIn("dialogue_references", frame)
        settled = dispatch.find_work(work.dispatch_id)
        self.assertEqual(
            settled.scene_checkpoint["blueprint"]["dialogue"],
            self.package_payload["dialogue"],
        )

        # Materialize the package through the real encounter path, then stop
        # using models entirely.
        south = activate_scene_encounter(
            self.owner, result.package_id, "south_gate", room=self.acceptance_room, tick=self.now
        )
        self.assertTrue(south.activated, south.reason)
        market = activate_scene_encounter(
            self.owner, result.package_id, "market", room=self.acceptance_room, tick=self.now
        )
        self.assertTrue(market.activated, market.reason)
        mother = self._play_host(result.package_id, "mother")
        calls_before = len(client.calls)
        source = dialogue_source_for_host(mother)
        self.assertIsNotNone(source)
        topic_ids = {topic.keyword: topic.topic_id for topic in source.dialogue.topics}

        # Web: the public chain root selects, pre-delivers exactly its public
        # successor and never the qualified descendant.
        from web.webclient.actions.exploration_actions import _talk_scripted_adapter

        outcome = _talk_scripted_adapter(
            self.owner,
            {
                "npc_id": int(mother.pk),
                "topic_id": topic_ids["起頭"],
                "context_id": None,
                "selection_id": "web-chain",
            },
        )
        self.assertEqual(outcome["outcome"], "success")
        from world.rules.dialogue import chain_deliveries

        session = live_dialogue_session(self.owner)
        nodes = chain_deliveries(session, mother, actor=self.owner)
        self.assertEqual(
            [node.delivery.topic_id for node in nodes], [topic_ids["接續"]]
        )
        root = session.delivery
        complete_dialogue_delivery(
            self.owner,
            delivery_id=root.delivery_id,
            context_id=root.context_id,
            topic_id=root.topic_id,
            scene_revision=root.scene_revision,
        )

        # Text: the locked condition ships only its canonical refusal, and an
        # open informational topic ships the complete attributed scene.
        refusal = self.call(CmdsTalk(), f"{mother.key} 衣著", caller=self.owner)
        self.assertIn(REFUSAL_TEXT, refusal)
        self.assertNotIn(LONG_PROSE, refusal)
        answer = self.call(CmdsTalk(), f"{mother.key} 線索", caller=self.owner)
        self.assertIn(LONG_PROSE, answer)
        self.assertIn("你說", answer)
        self.assertEqual(len(client.calls), calls_before)

        # Committed refresh and phase return keep the saved completion while
        # retiring the obsolete phase's choices.
        with self.captureOnCommitCallbacks(execute=True):
            transition_story_dialogue(
                result.package_id,
                "mother",
                expected_revision=0,
                provenance={"closure": True},
                tick=self.now + 1,
            )
        everyday = dialogue_source_for_host(mother)
        self.assertEqual(
            [topic.keyword for topic in everyday.dialogue.topics], ["近況"]
        )
        with self.captureOnCommitCallbacks(execute=True):
            transition_story_dialogue(
                result.package_id,
                "mother",
                expected_revision=1,
                provenance={"closure": False},
                tick=self.now + 2,
            )
        returned = live_dialogue_session(self.owner)
        self.assertIsNotNone(returned)
        self.assertEqual(
            [topic.keyword for topic in dialogue_source_for_host(mother).dialogue.topics],
            ["線索", "起頭", "接續", "追問", "衣著"],
        )
        from world.rules.dialogue_context import host_dialogue_binding
        from world.narrative.dialogue_reading import completed_topic_ids

        host_key, _identity = host_dialogue_binding(mother)
        self.assertIn(topic_ids["起頭"], completed_topic_ids(self.owner, host_key))
        self.assertEqual(len(client.calls), calls_before)


class GeneratedUnicodeIdentityTests(RegistryIsolationMixin, EvenniaTest):
    """Maximal Unicode components keep exact bytes through every Python boundary."""

    def test_maximal_unicode_role_and_phase_round_trip(self):
        register_catalog_once()
        role_id = "母" * 64
        phase_id = "階" * 64
        payload = guild_package()
        unicode_role = role(role_id)
        unicode_role["characterization"]["display_name"] = "生成住民"
        unicode_role["characterization"]["portrait"] = {
            "stable_key": "generated_unicode_portrait"
        }
        payload["roles"] = [unicode_role]
        payload["relationships"] = []
        payload["knowledge"] = []
        payload["encounters"] = [
            {
                "scene_id": "south_gate",
                "role_ids": [role_id],
                "locator": anchor_locator(),
                "prerequisites": [],
            }
        ]
        entry = _dialogue(role_id)
        entry["initial_phase"] = phase_id
        entry["phases"] = [
            _phase(
                phase_id,
                [{"default": True}],
                topics=[_topic("unicode_topic", "線索", LONG_PROSE)],
            )
        ]
        payload["dialogue"] = [entry]
        definition = validate_scene_package(payload)
        topic_id = definition.role_dialogue(role_id).phases[0].topics[0].topic_id
        self.assertGreater(len(topic_id), 400)
        self.assertLessEqual(len(topic_id.encode("ascii")), 2048)

        published = publish_scene_package(payload, owner="tester")
        host = create_object(NPC, key="生成角色", location=self.room1)
        player = create_object(PlayerCharacter, key="生成訪客", location=self.room1)
        host.components.add(
            ScriptedDialogue.create(
                host, dialogue_key=f"scene_role:{published.package_id}:{role_id}"
            )
        )
        scene_store.bind_role(
            scene_store.read_package(published.package_id), role_id, host.pk
        )
        scene_store.set_dialogue_phase(
            scene_store.read_package(published.package_id), role_id, phase_id
        )

        source = dialogue_source_for_host(host)
        self.assertEqual(source.dialogue.topics[0].topic_id, topic_id)
        self.assertEqual(source.identity.role_id, role_id)
        self.assertEqual(source.identity.phase_id, phase_id)
        descriptor = validate_talk_scripted_descriptor(
            {"npc_id": int(host.pk), "topic_id": topic_id, "context_id": None}
        )
        self.assertEqual(descriptor["topic_id"], topic_id)

        delivery = select_authored_topic(
            player,
            host,
            topic_id,
            selection_id="unicode-selection",
            expected_context_id=None,
        )
        self.assertEqual(delivery.topic_id, topic_id)
        self.assertEqual(delivery.scene_id, source.dialogue.topics[0].fallback.scene_id)
        session = live_dialogue_session(player)
        self.assertEqual(session.source_identity.role_id, role_id)
        self.assertEqual(session.delivery.topic_id, topic_id)
        complete_dialogue_delivery(
            player,
            delivery_id=delivery.delivery_id,
            context_id=delivery.context_id,
            topic_id=topic_id,
            scene_revision=delivery.scene_revision,
        )
        player.attributes.reset_cache()
        host_key = session.host_key
        self.assertEqual(completed_topic_ids(player, host_key), (topic_id,))
        restored = live_dialogue_session(player)
        self.assertEqual(restored.delivery.topic_id, topic_id)
