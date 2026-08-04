"""Repository-level tests for the container and Evennia skeleton contracts."""

from pathlib import Path
import re
import unittest

import yaml

from tools.spec_traceability import covers_requirement


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def _stage(containerfile: str, name: str) -> str:
    match = re.search(
        rf"^FROM\s+\S+\s+AS\s+{re.escape(name)}\s*$",
        containerfile,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if match is None:
        raise AssertionError(f"Containerfile stage {name!r} is missing")
    next_stage = re.search(
        r"^FROM\s+\S+(?:\s+AS\s+\S+)?\s*$",
        containerfile[match.end():],
        flags=re.MULTILINE | re.IGNORECASE,
    )
    end = match.end() + next_stage.start() if next_stage else len(containerfile)
    return containerfile[match.start():end]


class ContainerContractTests(unittest.TestCase):
    @covers_requirement("container-image::multi-stage-containerfile")
    def test_containerfile_separates_verified_download_build_layout_and_runtime(self):
        containerfile = _read("Containerfile")
        stage_names = re.findall(
            r"^FROM\s+\S+\s+AS\s+(\S+)\s*$",
            containerfile,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        self.assertEqual(stage_names, ["download", "builder", "app-layout", "final"])

        download = _stage(containerfile, "download")
        builder = _stage(containerfile, "builder")
        final = _stage(containerfile, "final")
        self.assertIn("sha256sum --check", download)
        self.assertRegex(builder, r"uv sync\s+--locked\s+--no-dev")
        self.assertRegex(builder, r"id=uv-\$TARGETARCH\$TARGETVARIANT")
        self.assertRegex(builder, r"COPY[^\n]*pyproject\.toml uv\.lock")
        self.assertRegex(final, r"COPY --link[^\n]*--from=builder /venv /venv")
        self.assertRegex(final, r"COPY --link[^\n]*--from=download /dumb-init")
        self.assertRegex(final, r"COPY --link[^\n]*--from=app-layout /app /app")
        self.assertNotRegex(final, r"apt-get|/root/\.cache/uv|\b(?:gcc|g\+\+|make)\b")

    @covers_requirement("container-image::non-root-arbitrary-uid-capable-runtime")
    def test_runtime_user_and_writable_mounts_support_arbitrary_uid_with_root_group(self):
        containerfile = _read("Containerfile")
        layout = _stage(containerfile, "app-layout")
        final = _stage(containerfile, "final")
        writable_paths = {
            "/app/server/db",
            "/app/server/logs",
            "/app/server/.static",
            "/app/server/.media",
            "/app/server/.art",
        }

        self.assertRegex(
            containerfile,
            re.compile(r"^ARG UID=([1-9]\d*)$", flags=re.MULTILINE),
            "default UID must be non-root",
        )
        self.assertIn("--groups root", final)
        self.assertRegex(
            final,
            re.compile(r"^USER \$UID$", flags=re.MULTILINE),
            "runtime must drop root",
        )
        volume_match = re.search(r'^VOLUME \[(.+)\]$', final, flags=re.MULTILINE)
        self.assertIsNotNone(volume_match)
        self.assertEqual(set(re.findall(r'"([^"]+)"', volume_match.group(1))), writable_paths)
        for path in writable_paths:
            self.assertRegex(
                layout,
                rf"install -d -m 775 -o root -g 0 {re.escape(path)}",
                f"{path} must be group-0 writable",
            )
        self.assertIn("find /app -type f -exec chmod 0644", layout)

    @covers_requirement("container-image::compose-yaml-for-local-and-networked-gpu-services")
    def test_compose_exposes_ports_persists_state_and_keeps_gpu_services_external(self):
        compose = yaml.safe_load(_read("compose.yaml"))
        services = compose["services"]
        evennia = services["evennia"]
        bootstrap = services["bootstrap"]

        self.assertEqual(set(services), {"evennia", "bootstrap"})
        self.assertEqual(set(evennia["ports"]), {"4000:4000", "4001:4001", "4002:4002"})
        self.assertEqual(
            set(evennia["volumes"]),
            {
                "evennia-db:/app/server/db",
                "evennia-art:/app/server/.art",
                "evennia-logs:/app/server/logs",
                "evennia-static:/app/server/.static",
                "evennia-media:/app/server/.media",
            },
        )
        self.assertEqual(
            set(compose["volumes"]),
            {"evennia-db", "evennia-art", "evennia-logs", "evennia-static", "evennia-media"},
        )
        self.assertIn("host.containers.internal", evennia["environment"]["OLLAMA_BASE_URL"])
        self.assertIn("host.containers.internal", evennia["environment"]["SD_WEBUI_BASE_URL"])
        self.assertEqual(bootstrap["profiles"], ["bootstrap"])
        self.assertTrue(bootstrap["stdin_open"])
        self.assertTrue(bootstrap["tty"])
        self.assertEqual(bootstrap["volumes"], ["evennia-db:/app/server/db"])
        self.assertIn("evennia createsuperuser", " ".join(bootstrap["command"]))

    @covers_requirement("container-image::container-ignore-file-excludes-non-build-context-files")
    def test_containerignore_excludes_repository_secrets_caches_and_development_paths(self):
        patterns = {
            line.strip()
            for line in _read(".containerignore").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        required = {
            ".git/",
            ".env",
            ".venv/",
            "venv/",
            "env/",
            "__pycache__/",
            "**/__pycache__/",
            "tmp/",
            "server/conf/secret_settings.py",
        }
        self.assertTrue(required <= patterns, f"missing ignore patterns: {sorted(required - patterns)}")


class EvenniaSkeletonContractTests(unittest.TestCase):
    @covers_requirement("evennia-project-skeleton::runnable-evennia-project-skeleton")
    def test_skeleton_has_evennia_settings_entrypoint_and_extension_directories(self):
        expected_directories = {
            "commands",
            "typeclasses",
            "web",
            "world",
            "world/lore",
            "world/rules",
            "world/quests",
            "world/ai",
            "world/imports",
            "world/art",
        }
        self.assertFalse(
            [name for name in sorted(expected_directories) if not (REPO_ROOT / name).is_dir()]
        )
        self.assertTrue((REPO_ROOT / "server/conf/settings.py").is_file())
        final = _stage(_read("Containerfile"), "final")
        self.assertEqual(
            re.search(r'^CMD \["([^"]+)"\]$', final, flags=re.MULTILINE).group(1),
            "/app/docker-entrypoint.sh",
        )
        self.assertEqual(_read("docker-entrypoint.sh").splitlines()[-1], "exec evennia start --log")

    @covers_requirement(
        "evennia-project-skeleton::first-run-database-initialization-is-a-runtime-action-not-a-build-time-artifact"
    )
    def test_database_bootstrap_and_migrations_are_runtime_operations(self):
        containerfile = _read("Containerfile")
        compose = yaml.safe_load(_read("compose.yaml"))
        entrypoint_commands = [
            line.strip()
            for line in _read("docker-entrypoint.sh").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        self.assertNotIn("evennia migrate", containerfile)
        self.assertNotRegex(containerfile, r"(?i)COPY[^\n]*\.(?:db|db3|sqlite3)\b")
        self.assertEqual(
            entrypoint_commands[-2:],
            ["evennia migrate --noinput", "exec evennia start --log"],
        )
        bootstrap = compose["services"]["bootstrap"]
        self.assertEqual(bootstrap["profiles"], ["bootstrap"])
        self.assertTrue(bootstrap["stdin_open"] and bootstrap["tty"])
        self.assertEqual(bootstrap["volumes"], ["evennia-db:/app/server/db"])
        self.assertRegex(" ".join(bootstrap["command"]), r"evennia migrate --noinput.*evennia createsuperuser")

    @covers_requirement("evennia-project-skeleton::secret-settings-are-never-baked-into-the-image")
    def test_secret_settings_are_excluded_and_never_generated_during_build(self):
        containerfile = _read("Containerfile")
        ignored = set(_read(".containerignore").splitlines())

        self.assertIn("server/conf/secret_settings.py", ignored)
        self.assertNotIn("secret_settings.py", containerfile)
        self.assertNotRegex(containerfile, r"(?i)RUN[^\n]*(?:evennia init|secret[_-]?key)")


if __name__ == "__main__":
    unittest.main()
