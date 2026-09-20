"""Subprocess harness and path anchors for the ``test_env_overrides`` slices.

Module-level constants, helpers, and the shared base moved verbatim from the
original flat module (not a collected test module).
"""
import ast


import os


import re


import subprocess


import sys


import unittest


from server.conf.llm_knobs import llm_env_names, llm_global_env_names


from tools.spec_traceability import covers_requirement


REPO_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    )
)


SETTINGS_PATH = os.path.join(REPO_ROOT, "server", "conf", "settings.py")


TEST_SETTINGS_PATH = os.path.join(REPO_ROOT, "server", "conf", "test_settings.py")


ENV_EXAMPLE_PATH = os.path.join(REPO_ROOT, ".env.example")


GUIDE_PATH = os.path.join(REPO_ROOT, "docs", "development", "settings-and-environment.md")


SIDEBAR_PATH = os.path.join(REPO_ROOT, "docs", "_sidebar.md")


PROMPTS_DOC_PATH = os.path.join(REPO_ROOT, "docs", "gm", "prompts.md")


# The env-backed inventory: 27 same-named variables plus the URL knob whose
# variable name is fixed by the internal-art-worker spec.
ENV_BACKED: dict[str, str] = {
    "ART_SD_BASE_URL": "SD_WEBUI_BASE_URL",
    "ART_SD_TIMEOUT_SECONDS": "ART_SD_TIMEOUT_SECONDS",
    "ART_SD_STEPS": "ART_SD_STEPS",
    "ART_SD_CFG_SCALE": "ART_SD_CFG_SCALE",
    "ART_SD_SAMPLER": "ART_SD_SAMPLER",
    "ART_SD_SCHEDULER": "ART_SD_SCHEDULER",
    "ART_SD_CHECKPOINT": "ART_SD_CHECKPOINT",
    "ART_SD_STYLES": "ART_SD_STYLES",
    "ART_SD_MODULES": "ART_SD_MODULES",
    "ART_SD_SCENE_WIDTH": "ART_SD_SCENE_WIDTH",
    "ART_SD_SCENE_HEIGHT": "ART_SD_SCENE_HEIGHT",
    "ART_SD_PORTRAIT_WIDTH": "ART_SD_PORTRAIT_WIDTH",
    "ART_SD_PORTRAIT_HEIGHT": "ART_SD_PORTRAIT_HEIGHT",
    "ART_SD_MAX_RESPONSE_BYTES": "ART_SD_MAX_RESPONSE_BYTES",
    "ART_SD_MAX_IMAGE_DIMENSIONS": "ART_SD_MAX_IMAGE_DIMENSIONS",
    "ART_SD_MAX_IMAGE_PIXELS": "ART_SD_MAX_IMAGE_PIXELS",
    "ART_SD_PREPIN_SAMPLES_FORMAT": "ART_SD_PREPIN_SAMPLES_FORMAT",
    "ART_SD_OUTPUT_FORMAT": "ART_SD_OUTPUT_FORMAT",
    "ART_SD_OUTPUT_QUALITY": "ART_SD_OUTPUT_QUALITY",
    "ART_SD_PRESERVE_GENERATION_METADATA": "ART_SD_PRESERVE_GENERATION_METADATA",
    "ART_SD_PROBE_TIMEOUT_MS": "ART_SD_PROBE_TIMEOUT_MS",
    "ART_SD_PROBE_CACHE_SECONDS": "ART_SD_PROBE_CACHE_SECONDS",
    "ART_REMBG_ENABLED": "ART_REMBG_ENABLED",
    "ART_REMBG_MODEL": "ART_REMBG_MODEL",
    "ART_REMBG_DOWNLOAD_ENABLED": "ART_REMBG_DOWNLOAD_ENABLED",
    "ART_REMBG_ALLOWANCE_SECONDS": "ART_REMBG_ALLOWANCE_SECONDS",
    "ART_REMBG_THREADS": "ART_REMBG_THREADS",
    "ART_SCHEDULER_ENABLED": "ART_SCHEDULER_ENABLED",
    "ART_SCHEDULER_INTERVAL_SECONDS": "ART_SCHEDULER_INTERVAL_SECONDS",
    "ART_SCHEDULER_LIMIT": "ART_SCHEDULER_LIMIT",
    "ELOSERN_VUE_CLIENT": "ELOSERN_VUE_CLIENT",
    "MAX_NR_CHARACTERS": "ELOSERN_MAX_CHARACTERS",
    "DEFEAT_ADULT_SCENES": "DEFEAT_ADULT_SCENES",
}


# repr() of each effective default, exactly as test_art_settings.py pins them.
DEFAULT_REPR: dict[str, str] = {
    "ART_SD_BASE_URL": "'http://127.0.0.1:7860'",
    "ART_SD_TIMEOUT_SECONDS": "600",
    "ART_SD_STEPS": "30",
    "ART_SD_CFG_SCALE": "7.0",
    "ART_SD_SAMPLER": "''",
    "ART_SD_SCHEDULER": "''",
    "ART_SD_CHECKPOINT": "''",
    "ART_SD_STYLES": "''",
    "ART_SD_MODULES": "''",
    "ART_SD_SCENE_WIDTH": "1344",
    "ART_SD_SCENE_HEIGHT": "768",
    "ART_SD_PORTRAIT_WIDTH": "768",
    "ART_SD_PORTRAIT_HEIGHT": "1024",
    "ART_SD_MAX_RESPONSE_BYTES": "52428800",
    "ART_SD_MAX_IMAGE_DIMENSIONS": "4096",
    "ART_SD_MAX_IMAGE_PIXELS": "16777216",
    "ART_SD_PREPIN_SAMPLES_FORMAT": "False",
    "ART_SD_OUTPUT_FORMAT": "'png'",
    "ART_SD_OUTPUT_QUALITY": "80",
    "ART_SD_PRESERVE_GENERATION_METADATA": "True",
    "ART_SD_PROBE_TIMEOUT_MS": "5000",
    "ART_SD_PROBE_CACHE_SECONDS": "300",
    "ART_REMBG_ENABLED": "False",
    "ART_REMBG_MODEL": "'bria-rmbg'",
    "ART_REMBG_DOWNLOAD_ENABLED": "True",
    "ART_REMBG_ALLOWANCE_SECONDS": "120",
    "ART_REMBG_THREADS": "0",
    "ART_SCHEDULER_ENABLED": "True",
    "ART_SCHEDULER_INTERVAL_SECONDS": "30",
    "ART_SCHEDULER_LIMIT": "4",
    "ELOSERN_VUE_CLIENT": "True",
    "MAX_NR_CHARACTERS": "5",
}


# One valid override per env-backed setting: (setting, variable, raw,
# expected repr). The repr comparison pins the Python type as well as the
# value, so a hard-coded literal, a missing int()/float() coercion, or a
# stringified bool fails the assertion.
VALID_OVERRIDES: list[tuple[str, str, str, str]] = [
    ("ART_SD_BASE_URL", "SD_WEBUI_BASE_URL", "http://sd.internal:7861", "'http://sd.internal:7861'"),
    ("ART_SD_TIMEOUT_SECONDS", "ART_SD_TIMEOUT_SECONDS", " 120 ", "120"),
    ("ART_SD_STEPS", "ART_SD_STEPS", "12", "12"),
    ("ART_SD_CFG_SCALE", "ART_SD_CFG_SCALE", "1.5", "1.5"),
    ("ART_SD_SAMPLER", "ART_SD_SAMPLER", "Euler a", "'Euler a'"),
    ("ART_SD_SCHEDULER", "ART_SD_SCHEDULER", "karras", "'karras'"),
    (
        "ART_SD_CHECKPOINT",
        "ART_SD_CHECKPOINT",
        "anima/animaika_v43.safetensors",
        "'anima/animaika_v43.safetensors'",
    ),
    ("ART_SD_STYLES", "ART_SD_STYLES", "cinematic, portrait", "'cinematic, portrait'"),
    (
        "ART_SD_MODULES",
        "ART_SD_MODULES",
        "te.safetensors,vae.safetensors",
        "'te.safetensors,vae.safetensors'",
    ),
    ("ART_SD_SCENE_WIDTH", "ART_SD_SCENE_WIDTH", "1024", "1024"),
    ("ART_SD_SCENE_HEIGHT", "ART_SD_SCENE_HEIGHT", "576", "576"),
    ("ART_SD_PORTRAIT_WIDTH", "ART_SD_PORTRAIT_WIDTH", "896", "896"),
    ("ART_SD_PORTRAIT_HEIGHT", "ART_SD_PORTRAIT_HEIGHT", "1152", "1152"),
    ("ART_SD_MAX_RESPONSE_BYTES", "ART_SD_MAX_RESPONSE_BYTES", "1048576", "1048576"),
    ("ART_SD_MAX_IMAGE_DIMENSIONS", "ART_SD_MAX_IMAGE_DIMENSIONS", "2048", "2048"),
    ("ART_SD_MAX_IMAGE_PIXELS", "ART_SD_MAX_IMAGE_PIXELS", "4194304", "4194304"),
    ("ART_SD_PREPIN_SAMPLES_FORMAT", "ART_SD_PREPIN_SAMPLES_FORMAT", "true", "True"),
    ("ART_SD_OUTPUT_FORMAT", "ART_SD_OUTPUT_FORMAT", "WEBP", "'webp'"),
    ("ART_SD_OUTPUT_FORMAT", "ART_SD_OUTPUT_FORMAT", " jpeg ", "'jpeg'"),
    ("ART_SD_OUTPUT_QUALITY", "ART_SD_OUTPUT_QUALITY", "60", "60"),
    ("ART_SD_OUTPUT_QUALITY", "ART_SD_OUTPUT_QUALITY", "1", "1"),
    ("ART_SD_OUTPUT_QUALITY", "ART_SD_OUTPUT_QUALITY", "100", "100"),
    (
        "ART_SD_PRESERVE_GENERATION_METADATA",
        "ART_SD_PRESERVE_GENERATION_METADATA",
        "off",
        "False",
    ),
    ("ART_SD_PROBE_TIMEOUT_MS", "ART_SD_PROBE_TIMEOUT_MS", "2000", "2000"),
    ("ART_SD_PROBE_TIMEOUT_MS", "ART_SD_PROBE_TIMEOUT_MS", "1000", "1000"),
    ("ART_SD_PROBE_TIMEOUT_MS", "ART_SD_PROBE_TIMEOUT_MS", "60000", "60000"),
    ("ART_SD_PROBE_CACHE_SECONDS", "ART_SD_PROBE_CACHE_SECONDS", "60", "60"),
    ("ART_SD_PROBE_CACHE_SECONDS", "ART_SD_PROBE_CACHE_SECONDS", "5", "5"),
    ("ART_SD_PROBE_CACHE_SECONDS", "ART_SD_PROBE_CACHE_SECONDS", "3600", "3600"),
    ("ART_REMBG_ENABLED", "ART_REMBG_ENABLED", "on", "True"),
    ("ART_REMBG_MODEL", "ART_REMBG_MODEL", "ISNET-ANIME", "'isnet-anime'"),
    ("ART_REMBG_DOWNLOAD_ENABLED", "ART_REMBG_DOWNLOAD_ENABLED", "off", "False"),
    ("ART_REMBG_ALLOWANCE_SECONDS", "ART_REMBG_ALLOWANCE_SECONDS", "300", "300"),
    ("ART_REMBG_THREADS", "ART_REMBG_THREADS", "8", "8"),
    ("ART_SCHEDULER_ENABLED", "ART_SCHEDULER_ENABLED", "0", "False"),
    ("ART_SCHEDULER_INTERVAL_SECONDS", "ART_SCHEDULER_INTERVAL_SECONDS", "15", "15"),
    ("ART_SCHEDULER_LIMIT", "ART_SCHEDULER_LIMIT", "8", "8"),
    ("ELOSERN_VUE_CLIENT", "ELOSERN_VUE_CLIENT", "off", "False"),
    ("MAX_NR_CHARACTERS", "ELOSERN_MAX_CHARACTERS", "1", "1"),
    ("MAX_NR_CHARACTERS", "ELOSERN_MAX_CHARACTERS", "10", "10"),
    ("MAX_NR_CHARACTERS", "ELOSERN_MAX_CHARACTERS", " 5 ", "5"),
]


# (env var, raw value, extra expected stderr substring) per fail-closed family.
INVALID_VALUES: list[tuple[str, str, str]] = [
    ("ART_SD_STEPS", " twelve ", "expected a positive integer"),
    ("ART_SD_STEPS", "twelve", "expected a positive integer"),
    ("ART_SD_STEPS", "0", "expected a positive integer"),
    ("ART_SD_STEPS", "-3", "expected a positive integer"),
    ("ART_SD_MAX_IMAGE_PIXELS", "0", "expected a positive integer"),
    ("ART_SCHEDULER_INTERVAL_SECONDS", "-1", "expected a positive integer"),
    ("ART_SCHEDULER_LIMIT", "0", "expected a positive integer"),
    ("ART_SD_CFG_SCALE", "fast", "expected a positive float"),
    ("ART_SD_CFG_SCALE", "0", "expected a positive float"),
    ("ART_SD_CFG_SCALE", "-1.5", "expected a positive float"),
    ("ART_SD_CFG_SCALE", "nan", "expected a positive float"),
    ("ART_SD_CFG_SCALE", "inf", "expected a positive float"),
    ("ART_SCHEDULER_ENABLED", "maybe", "1/true/yes/on/0/false/no/off"),
    ("ART_SD_PREPIN_SAMPLES_FORMAT", "2", "1/true/yes/on/0/false/no/off"),
    ("ELOSERN_VUE_CLIENT", "TRUE!", "1/true/yes/on/0/false/no/off"),
    ("ART_SD_PORTRAIT_WIDTH", "777", "expected a positive multiple of 8"),
    ("ART_SD_SCENE_WIDTH", "1001", "expected a positive multiple of 8"),
    ("ART_SD_SCENE_HEIGHT", "0", "expected a positive multiple of 8"),
    ("ART_SD_PORTRAIT_HEIGHT", "-16", "expected a positive multiple of 8"),
    ("ART_SD_OUTPUT_FORMAT", "heic", "expected one of png/webp/jpeg/avif (case-insensitive)"),
    ("ART_SD_OUTPUT_FORMAT", "pngs", "expected one of png/webp/jpeg/avif (case-insensitive)"),
    ("ART_SD_OUTPUT_QUALITY", "0", "expected an integer between 1 and 100"),
    ("ART_SD_OUTPUT_QUALITY", "101", "expected an integer between 1 and 100"),
    ("ART_SD_OUTPUT_QUALITY", "twelve", "expected an integer between 1 and 100"),
    ("ART_SD_PRESERVE_GENERATION_METADATA", "maybe", "1/true/yes/on/0/false/no/off"),
    ("ART_SD_PROBE_TIMEOUT_MS", "999", "expected an integer between 1000 and 60000"),
    ("ART_SD_PROBE_TIMEOUT_MS", "60001", "expected an integer between 1000 and 60000"),
    ("ART_SD_PROBE_TIMEOUT_MS", "twelve", "expected an integer between 1000 and 60000"),
    ("ART_SD_PROBE_CACHE_SECONDS", "4", "expected an integer between 5 and 3600"),
    ("ART_SD_PROBE_CACHE_SECONDS", "3601", "expected an integer between 5 and 3600"),
    ("ART_SD_PROBE_CACHE_SECONDS", "0", "expected an integer between 5 and 3600"),
    ("ELOSERN_MAX_CHARACTERS", "0", "expected an integer between 1 and 10"),
    ("ELOSERN_MAX_CHARACTERS", "11", "expected an integer between 1 and 10"),
    ("ELOSERN_MAX_CHARACTERS", "-1", "expected an integer between 1 and 10"),
    ("ELOSERN_MAX_CHARACTERS", "twelve", "expected an integer between 1 and 10"),
    ("ART_REMBG_ALLOWANCE_SECONDS", "5", "expected an integer between 10 and 1800"),
    ("ART_REMBG_ALLOWANCE_SECONDS", "2000", "expected an integer between 10 and 1800"),
    ("ART_REMBG_ALLOWANCE_SECONDS", "twelve", "expected an integer between 10 and 1800"),
    ("ART_REMBG_THREADS", "-1", "expected an integer between 0 and 256"),
    ("ART_REMBG_THREADS", "257", "expected an integer between 0 and 256"),
    ("ART_REMBG_THREADS", "twelve", "expected an integer between 0 and 256"),
    ("ART_REMBG_MODEL", "segment-anything", "expected one of bria-rmbg/isnet-anime/isnet-general-use/u2net/u2netp (case-insensitive)"),
    ("ART_REMBG_ENABLED", "maybe", "1/true/yes/on/0/false/no/off"),
]


_IMPORT = "import server.conf.settings as s"


BOOL_SETTINGS = [
    "ART_SD_PREPIN_SAMPLES_FORMAT",
    "ART_SD_PRESERVE_GENERATION_METADATA",
    "ART_REMBG_ENABLED",
    "ART_REMBG_DOWNLOAD_ENABLED",
    "ART_SCHEDULER_ENABLED",
    "ELOSERN_VUE_CLIENT",
]


def _settings_repr(names: list[str]) -> str:
    """Subprocess snippet printing `NAME <repr(value)>` for each setting."""
    lines = [_IMPORT]
    for name in names:
        lines.append(f"print({name!r}, repr(s.{name}))")
    return "\n".join(lines)


def _printed_map(stdout: str, expected: set[str]) -> dict[str, str]:
    """Parse `NAME <repr>` lines, ignoring the benign `secret_settings.py
    file not found` line that the settings import prints to stdout."""
    printed = {}
    for line in stdout.splitlines():
        name, _, value = line.partition(" ")
        if name in expected:
            printed[name] = value
    return printed


# Every case pre-seeds an EMPTY synthetic secret_settings module so a
# developer's gitignored server/conf/secret_settings.py can never shift the
# effective values under test (the precedence test overwrites this entry with
# a populated module via plain assignment). The production import structure
# is unchanged: settings.py still executes `from server.conf.secret_settings
# import *` at the bottom; the synthetic module simply defines nothing.
_SECRET_ISOLATION_PRELUDE = (
    "import sys\n"
    "import types\n"
    "sys.modules.setdefault(\n"
    "    'server.conf.secret_settings',\n"
    "    types.ModuleType('server.conf.secret_settings'),\n"
    ")\n"
)


class _SubprocessSettingsTests(unittest.TestCase):
    """Shared harness: bare interpreter, curated environment, repo cwd."""

    def _base_env(self) -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if key != "DJANGO_SETTINGS_MODULE"
            and not key.startswith("ART_")
            and key not in (
                "SD_WEBUI_BASE_URL",
                "ELOSERN_VUE_CLIENT",
                "ELOSERN_MAX_CHARACTERS",
            )
        }

    def _run(self, code: str, **overrides: str) -> subprocess.CompletedProcess[str]:
        env = self._base_env()
        env.update(overrides)
        code = _SECRET_ISOLATION_PRELUDE + code
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )


def _env_read_names(path: str) -> set[str]:
    """Every environment-variable name literal read in a settings module."""
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    names: set[str] = set()
    helper_calls = {
        "_env_str",
        "_env_typed",
        "_env_int",
        "_env_int_bounded",
        "_env_dimension",
        "_env_float",
        "_env_choice",
        "_env_bool",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        fname = (
            func.id
            if isinstance(func, ast.Name)
            else (func.attr if isinstance(func, ast.Attribute) else None)
        )
        if fname in helper_calls and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                names.add(first.value)
        # os.environ.get("NAME", ...) and os.environ.pop("NAME", None)
        if fname in ("get", "pop") and isinstance(func, ast.Attribute):
            base = func.value
            if (
                isinstance(base, ast.Attribute)
                and base.attr == "environ"
                and isinstance(base.value, ast.Name)
                and base.value.id == "os"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                names.add(node.args[0].value)
        # os.environ["NAME"]
        if isinstance(func, ast.Subscript) and isinstance(func.value, ast.Attribute):
            base = func.value
            if (
                base.attr == "environ"
                and isinstance(base.value, ast.Name)
                and base.value.id == "os"
            ):
                index = func.slice
                if isinstance(index, ast.Constant) and isinstance(index.value, str):
                    names.add(index.value)
    return names


def _test_settings_popped_names() -> set[str]:
    tree = ast.parse(open(TEST_SETTINGS_PATH, encoding="utf-8").read())
    popped: set[str] = set()
    dynamic_llm_sweep = False
    for node in ast.walk(tree):
        # Second sanitize loop: os.environ.pop(<loop var>) where the loop
        # iterates over llm_env_names() — the generated-name sweep (an AST
        # extractor cannot enumerate its names, only prove it exists — and
        # prove it binds: the loop target must be a plain name and the pop's
        # first positional argument must be that same name (second argument
        # None), so a decoy loop popping unrelated names never passes.
        if (
            isinstance(node, ast.For)
            and isinstance(node.target, ast.Name)
            and isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "llm_env_names"
            and any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "pop"
                and isinstance(call.func.value, ast.Attribute)
                and call.func.value.attr == "environ"
                and len(call.args) == 2
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id == node.target.id
                and isinstance(call.args[1], ast.Constant)
                and call.args[1].value is None
                for call in ast.walk(node)
            )
        ):
            dynamic_llm_sweep = True
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "_ENV_OVERRIDES"
                for target in node.targets
            )
            and isinstance(node.value, (ast.Tuple, ast.List))
        ):
            popped = {
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant)
                and isinstance(element.value, str)
            }
    if not popped:
        raise AssertionError("_ENV_OVERRIDES tuple not found in test_settings.py")
    if not dynamic_llm_sweep:
        raise AssertionError("llm_env_names() sanitize loop not found in test_settings.py")
    popped.add("<LLM_KNOB_SWEEP>")
    return popped


def _active_env_example_keys() -> set[str]:
    keys = set()
    with open(ENV_EXAMPLE_PATH, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
            if match:
                keys.add(match.group(1))
    return keys


# Reviewed key-to-reader allow-list for keys .env.example may advertise that
# are read OUTSIDE server/conf/settings.py (launcher, compose, harness, CI).
EXTERNAL_READERS: dict[str, str] = {
    "PROMPTS_DIR": "compose.yaml bind mount interpolation",
    "ART_SEED_DIR": "compose.yaml bind mount interpolation",
    "CONTAINER_UID": "Containerfile build ARG",
    "IMAGE_TAG": "compose.yaml image tag interpolation",
    "VERSION": "Containerfile/OCI label build ARG",
    "RELEASE": "Containerfile/OCI label build ARG",
    "WEBSOCKET_CLIENT_PROXY_PORT": "evennia.web.utils.general_context",
    "MUD_TEST_SETTINGS": "server/conf/test_settings.py import guard",
    "DJANGO_SETTINGS_MODULE": "evennia launcher / Django bootstrap",
    "TEST_DB_PATH": "evennia.settings_default test database name",
    "OPENSPEC_TEST_EVIDENCE": "tools/spec_traceability evidence records",
    "COVERAGE_FILE": ".github/workflows/quality-gate.yml coverage data file",
}


EXTERNAL_READERS_PREFIXES: dict[str, str] = {
    "EVENNIA_SUPERUSER_": "evennia launcher non-interactive superuser bootstrap",
    "ELOSERN_BROWSER_": "web/tests/browser/ managed browser-test harness",
}


def _env_example_lines() -> list[str]:
    with open(ENV_EXAMPLE_PATH, encoding="utf-8") as handle:
        return handle.read().splitlines()


def _guide_rows() -> list[str]:
    with open(GUIDE_PATH, encoding="utf-8") as handle:
        return [line for line in handle if line.lstrip().startswith("|")]


