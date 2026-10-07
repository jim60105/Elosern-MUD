"""Transport delegates writes only to registered S6 and legitimate S4/S5 seams."""
import ast
import unittest
from pathlib import Path
from web.gm.tests.test_read_only_contract import forbidden_assignments, forbidden_calls, forbidden_imports
from server.console.registry import VERBS

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_SERVICES={
    'console_api.py': {'verbs.dispatch','snapshot_policy.policy.execute','apply_raw'},
    'saves_api.py': {'snapshot_policy.manual_save','snapshot.request_restore','snapshot.delete_save'},
    'world_api.py': {'reset_prompt_library'},
}
WRITE_SERVICES=set().union(*ALLOWED_SERVICES.values())


def violations(source,filename):
    tree=ast.parse(source)
    errors=forbidden_assignments(tree)+forbidden_calls(tree)+forbidden_imports(tree)
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith(('world.rules.gm','world.maps.gm','world.quests.gm','world.narrative.gm')):
            errors.append('direct-owner-import')
        if isinstance(node,ast.Import):
            if any(alias.name.startswith(('world.rules.gm','world.maps.gm','world.quests.gm','world.narrative.gm')) for alias in node.names):
                errors.append('direct-owner-import')
        if isinstance(node,ast.Call):
            name=ast.unparse(node.func)
            if name in WRITE_SERVICES and name not in ALLOWED_SERVICES.get(filename,set()):
                errors.append(f'wrong-service:{name}')
    return errors


class WriterContractTests(unittest.TestCase):
    def test_transport_only_uses_owned_write_seams(self):
        for path in ROOT.glob('*.py'):
            if path.name=='dashboard.py':
                continue  # Read-only dashboard set.add is not a persistent writer.
            with self.subTest(path=path.name):
                self.assertEqual(violations(path.read_text(),path.name),[])

    def test_deliberately_forbidden_field_model_import_and_cross_transport_writes(self):
        for source in ('entity.db.wallet = 1','entity.wallet = 1','entity.attributes.add("x",1)','Model.objects.create(content={})','from world.narrative.memory import record_memory','from world.rules.gm import set_wallet','import world.maps.gm','snapshot.delete_save("x")','apply_raw("#1",[])'):
            with self.subTest(source=source):
                self.assertTrue(violations(source,'state_api.py'))
        for filename,services in ALLOWED_SERVICES.items():
            for service in services:
                self.assertEqual(violations(f'{service}(request)',filename),[])

    def test_registry_maps_four_owners_and_exact_fourteen_callable_names(self):
        import importlib
        self.assertEqual(len(VERBS),14)
        owners=set()
        for name,(module,fields) in VERBS.items():
            owners.add(module)
            self.assertTrue(callable(getattr(importlib.import_module(module),name)))
            self.assertIsInstance(fields,tuple)
        self.assertEqual(owners,{'world.rules.gm','world.maps.gm','world.quests.gm','world.narrative.gm'})
