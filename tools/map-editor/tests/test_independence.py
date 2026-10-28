"""The editor environment runs without the game framework or its readers."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

from conftest import make_config

from elosern_map_core import discover_source_paths
from elosern_map_editor.__main__ import parse_config
from elosern_map_editor.app import create_app, service_of
from elosern_map_editor.confinement import ConfinedWorkspace

PACKAGE = Path(__file__).resolve().parent.parent / "elosern_map_editor"
#: Core readers that follow links or read before bounding; the editor must use
#: its confined reader instead.
UNCONFINED_CORE_READERS = {
    "read_source_document",
    "discover_source_documents",
    "discover_source_paths",
    "check_workspace_freshness",
}


def test_game_framework_is_not_installed_in_the_editor_environment():
    assert importlib.util.find_spec("evennia") is None
    assert importlib.util.find_spec("django") is None


def test_starting_the_service_imports_no_game_module(workspace):
    service = service_of(create_app(make_config(workspace)))
    assert service.preview_state == "current"
    game = sorted(
        name
        for name in sys.modules
        if name.split(".")[0] in {"evennia", "django", "world", "typeclasses", "commands", "server", "web"}
    )
    assert game == []


def test_the_service_never_calls_unconfined_core_readers():
    used: set[str] = set()
    for source in PACKAGE.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                used.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.Name):
                used.add(node.id)
    assert used & UNCONFINED_CORE_READERS == set()


def test_confined_discovery_finds_the_same_plain_source_set_as_the_core(workspace):
    (workspace / "content/maps/settlements/notes.txt").write_text("ignored", encoding="utf-8")
    rows = ConfinedWorkspace(workspace).discover_world()
    assert all(refusal is None for _, refusal in rows)
    assert tuple(path for path, _ in rows) == discover_source_paths(workspace)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.0.2.10", "example.invalid", "::"])
def test_the_launcher_refuses_a_non_loopback_bind(workspace, host, capsys):
    with pytest.raises(SystemExit) as raised:
        parse_config(["--workspace", str(workspace), "--host", host])
    assert raised.value.code == 2
    assert "loopback" in capsys.readouterr().err


def test_the_launcher_refuses_an_ephemeral_port(workspace):
    with pytest.raises(SystemExit):
        parse_config(["--workspace", str(workspace), "--port", "0"])


def test_the_launcher_accepts_loopback_addresses(workspace):
    for host in ("127.0.0.1", "localhost", "::1"):
        config = parse_config(["--workspace", str(workspace), "--host", host, "--port", "9100"])
        assert config.host == host
        assert f"[::1]:9100" in config.allowed_hosts
