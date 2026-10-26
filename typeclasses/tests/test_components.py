"""Source tests proving service components delegate all state writes (task 3.6)."""

from tools.spec_traceability import covers_requirement

import ast
import inspect
import unittest
from pathlib import Path

from evennia.utils.create import create_object
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.test_resources import EvenniaTest

from typeclasses import components as components_module
from typeclasses.components import GuildExamReception, GuildStaff, Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.guild import GuildServiceError, resolve_local_service_host


class ComponentModuleSourceTests(unittest.TestCase):
    FORBIDDEN_ASSIGNMENTS = (
        "guild_rank",
        "merit",
        "wallet",
        "inventory",
        "quest_log",
        "guild_reward_claims",
        "active_combat",
        "guild_exam",
        "guild_registration",
        "disguised_stats",
    )

    @covers_requirement("guild-registration::guild-service-components-are-capability-adapters-not-state-writers")
    def test_components_define_only_capability_markers_and_service_data(self):
        source = inspect.getsource(components_module)
        tree = ast.parse(source)
        forbidden_hits = []
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for target in targets:
                unparsed = ast.unparse(target)
                for keyword in self.FORBIDDEN_ASSIGNMENTS:
                    if keyword in unparsed:
                        forbidden_hits.append(unparsed)
        self.assertEqual(
            forbidden_hits,
            [],
            f"components module assigns forbidden player-state: {forbidden_hits}",
        )

    def test_components_import_no_deterministic_write_api(self):
        source = inspect.getsource(components_module)
        self.assertNotIn("world.rules", source)
        self.assertNotIn("world.quests", source)

    def test_each_component_has_unique_stable_name(self):
        components = (GuildStaff, GuildExamReception, Merchant)
        names = {component.name for component in components}
        # Uniqueness and the slot-identity invariant are the contract; the
        # name VALUES are code-defined component identifiers already pinned
        # by their consumers, so they are never echoed as literals here
        # ("merchant" also names a shipped rulebook row the data gate
        # reserves for data-contract files).
        self.assertEqual(len(names), len(components))
        for component in components:
            self.assertTrue(component.name)
            self.assertTrue(
                component.name.replace("_", "").islower()
                and component.name.replace("_", "").isascii()
            )

    def test_component_slots_match_names(self):
        for component in (GuildStaff, GuildExamReception, Merchant):
            self.assertEqual(component.get_component_slot(), component.name)

    def test_module_has_no_function_bodies_writing_state(self):
        tree = ast.parse(inspect.getsource(components_module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Attribute) and child.attr in self.FORBIDDEN_ASSIGNMENTS:
                    self.fail(
                        f"function {node.name} references forbidden state {child.attr}"
                    )


class ExamReceptionComponentSlotTests(EvenniaTest):
    def test_every_reader_uses_only_the_reception_slot_after_reload(self):
        room = create_object(Room, key="reception room")
        holder = create_object(NPC, key="reception clerk", location=room)
        holder.components.add(
            GuildExamReception.create(
                holder, service_id="counter", branch_key="t_branch"
            )
        )
        holder.save()

        # Simulated process reload: the component handler is rebuilt from the
        # persisted slot name and DBFields alone.
        flush_cache()
        reloaded = NPC.objects.get(id=holder.id)
        slot = GuildExamReception.get_component_slot()
        self.assertTrue(reloaded.components.has(slot))
        self.assertFalse(reloaded.components.has("guild_examiner"))
        component = reloaded.components.get(slot)
        self.assertEqual(
            (component.service_id, component.branch_key), ("counter", "t_branch")
        )

        # Counter discovery resolves the same reloaded holder by the new slot.
        actor = create_object(NPC, key="reception actor", location=reloaded.location)
        self.assertIs(resolve_local_service_host(actor, GuildExamReception), reloaded)

        # Two holders make the slot-based discovery ambiguous, exactly as for
        # every other service component.
        second = create_object(NPC, key="second clerk", location=reloaded.location)
        second.components.add(
            GuildExamReception.create(second, service_id="other", branch_key="t_branch")
        )
        with self.assertRaises(GuildServiceError):
            resolve_local_service_host(actor, GuildExamReception)


if __name__ == "__main__":
    unittest.main()
