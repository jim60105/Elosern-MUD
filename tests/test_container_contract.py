"""Repository-level tests for the container and Evennia skeleton contracts."""

from pathlib import Path
import re
import unittest

import yaml

from server.conf.llm_knobs import llm_global_env_names
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
        self.assertEqual(
            stage_names, ["download", "builder", "vue-dist", "app-layout", "final"]
        )

        download = _stage(containerfile, "download")
        builder = _stage(containerfile, "builder")
        vue_dist = _stage(containerfile, "vue-dist")
        final = _stage(containerfile, "final")
        self.assertIn("sha256sum --check", download)
        self.assertRegex(builder, r"uv sync\s+--locked\s+--no-dev")
        self.assertRegex(builder, r"id=uv-\$TARGETARCH\$TARGETVARIANT")
        self.assertRegex(builder, r"COPY[^\n]*pyproject\.toml uv\.lock")
        self.assertRegex(vue_dist, r"npm ci")
        self.assertRegex(vue_dist, r"npm run build")
        self.assertRegex(
            _stage(containerfile, "app-layout"),
            r"COPY[^\n]*--from=vue-dist[^\n]*web/static/webclient/app/dist/",
        )
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
                "${PROMPTS_DIR:-./prompts}:/app/prompts:ro,z",
            },
        )
        self.assertEqual(
            set(compose["volumes"]),
            {"evennia-db", "evennia-art", "evennia-logs", "evennia-static", "evennia-media"},
        )
        self.assertIn("host.containers.internal", evennia["environment"]["LLM_BASE_URL"])
        self.assertNotIn("OLLAMA_BASE_URL", evennia["environment"])
        self.assertIn("host.containers.internal", evennia["environment"]["SD_WEBUI_BASE_URL"])
        self.assertEqual(bootstrap["profiles"], ["bootstrap"])
        self.assertTrue(bootstrap["stdin_open"])
        self.assertTrue(bootstrap["tty"])
        self.assertEqual(bootstrap["volumes"], ["evennia-db:/app/server/db"])
        self.assertIn("evennia createsuperuser", " ".join(bootstrap["command"]))

    @covers_requirement("container-image::compose-yaml-for-local-and-networked-gpu-services")
    def test_prompt_files_are_baked_and_mounted_read_only(self):
        compose = yaml.safe_load(_read("compose.yaml"))
        volumes = compose["services"]["evennia"]["volumes"]
        self.assertIn("${PROMPTS_DIR:-./prompts}:/app/prompts:ro,z", volumes)
        self.assertNotIn("/app/prompts:rw", " ".join(volumes))

        containerfile = _read("Containerfile")
        layout = _stage(containerfile, "app-layout")
        self.assertIn("COPY --chown=root:0 prompts/ /app/prompts/", layout)

        ignored = set(_read(".containerignore").splitlines())
        self.assertNotIn("prompts/", ignored)
        self.assertFalse(
            [line for line in ignored if "prompts" in line],
            "the build context must include the prompt data folder",
        )

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

    def test_vendored_name_corpus_is_baked_into_the_runtime_image(self):
        # world/lore/names.py parses third_party/fantasy-namegen at import
        # time, so a missing corpus turns every container start into a crash.
        layout = _stage(_read("Containerfile"), "app-layout")
        # Line-anchored on an ACTIVE instruction: a commented-out COPY must
        # not satisfy the contract.
        self.assertRegex(
            layout,
            r"(?m)^[ \t]*COPY[ \t]+--chown=root:0[ \t]+third_party/[ \t]+/app/third_party/[ \t]*$",
            "the app-layout stage must bake the vendored name corpus",
        )
        ignored = [
            line.strip()
            for line in _read(".containerignore").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertFalse(
            [line for line in ignored if "third_party" in line],
            "the build context must include the vendored name corpus",
        )

    @covers_requirement(
        "settings-environment-overrides::compose-forwards-optional-llm-knobs-without-host-or-literal-leakage"
    )
    def test_compose_forwards_optional_llm_knobs_with_blank_defaults(self):
        compose = yaml.safe_load(_read("compose.yaml"))
        environment = compose["services"]["evennia"]["environment"]
        global_names = set(llm_global_env_names())

        # Every LLM_-prefixed environment entry must be a declared knob —
        # a stale or misspelled forward cannot hide from the set check.
        self.assertEqual(
            {name for name in environment if name.startswith("LLM_")},
            global_names,
            "compose LLM environment must be exactly the declared knob set",
        )

        # LLM_BASE_URL keeps its host-gateway default; every other optional
        # global knob forwards through an empty-default interpolation so an
        # unset host variable arrives as the blank omit-sentinel.
        self.assertIn("host.containers.internal", environment["LLM_BASE_URL"])
        forwarded = {
            name: value
            for name, value in environment.items()
            if name.startswith("LLM_") and name != "LLM_BASE_URL"
        }
        self.assertEqual(
            set(forwarded),
            global_names - {"LLM_BASE_URL"},
            "every optional LLM knob must be forwarded",
        )
        for name, value in forwarded.items():
            self.assertEqual(
                value,
                "${%s:-}" % name,
                msg=f"{name} must forward with an empty default",
            )
        # The compose file itself never carries a secret literal.
        self.assertEqual(forwarded["LLM_API_KEY"], "${LLM_API_KEY:-}")
        key_lines = [
            line
            for line in _read("compose.yaml").splitlines()
            if re.match(r"^\s*LLM_API_KEY\s*:", line)
            and not re.match(r"^\s*LLM_API_KEY:\s*\$\{LLM_API_KEY:-\}\s*$", line)
        ]
        self.assertEqual(
            key_lines, [], "no non-empty LLM_API_KEY literal may exist in compose.yaml"
        )


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
            entrypoint_commands[-3:],
            [
                "evennia migrate --noinput",
                "evennia collectstatic --noinput",
                "exec evennia start --log",
            ],
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
