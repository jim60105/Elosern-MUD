"""Repository contract tests for the Vue frontend toolchain (A2).

Wraps the actual frontend gate execution for traceability: the Node
DOM-independent suite runs, the Vite production build reuses the preserved
UMD logic through CommonJS interop into the stable ``dist`` entry, the Vitest
component gate runs, and the committed quality workflow keeps every frontend
step required (webclient-vue-01-foundation).
"""

from pathlib import Path
import json
import re
import subprocess
import unittest

import yaml

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

NODE_GATE_COMMAND = "node --test web/static/webclient/js/tests/*.test.js"

# Offline artifact contract: functional remote-URL references in the built
# output. Inert string constants inside the locked runtime (XML namespace
# URIs, developer error-message hints) are not references, so only network
# call sites (bundle) and CSS url() references (stylesheet) are scanned; the
# Playwright origin check remains the runtime proof.
REMOTE_URL_CSS_RE = r'''url\(\s*['"]?https?://'''
REMOTE_URL_JS_RE = r'''(?:fetch|import|new\s+WebSocket)\s*\(\s*['"]https?://|\.open\(\s*['"][A-Z]+['"]\s*,\s*['"]https?://'''


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def setUpModule() -> None:
    # pnpm is installed directly rather than fetched by corepack at run time;
    # it self-manages to the packageManager pin however it was installed.
    pinned = json.loads(_read("package.json"))["packageManager"]
    probe = _run(["pnpm", "--version"])
    assert probe.returncode == 0, (
        f"pnpm must be on PATH (install it with `npm install --global {pinned}`):"
        f"\n{probe.stdout}\n{probe.stderr}"
    )
    # One deterministic locked install per execution; the individual tests
    # below then exercise the build/test gates exactly like the CI frontend
    # job does.
    result = _run(["pnpm", "install", "--frozen-lockfile"])
    assert result.returncode == 0, (
        "pnpm install --frozen-lockfile failed (Node 24 + the committed pnpm-lock.yaml are "
        f"required):\n{result.stdout}\n{result.stderr}"
    )


class NodeGateAndInteropTests(unittest.TestCase):
    @covers_requirement(
        "webclient-browser-verification::dom-independent-client-behavior-has-an-executable-node-test-gate"
    )
    def test_node_gate_runs_the_dom_independent_suite(self):
        result = _run(NODE_GATE_COMMAND.split(" "))
        self.assertEqual(
            result.returncode,
            0,
            f"the Node DOM-independent gate must pass:\n{result.stderr}",
        )

    @covers_requirement(
        "webclient-browser-verification::dom-independent-client-behavior-has-an-executable-node-test-gate"
    )
    def test_vite_build_reuses_the_preserved_logic_via_commonjs_interop(self):
        result = _run(["pnpm", "run", "build"])
        self.assertEqual(
            result.returncode,
            0,
            f"the Vite production build must pass (CJS interop over "
            f"web/static/webclient/js/elosern/*):\n{result.stdout}\n{result.stderr}",
        )
        dist = REPO_ROOT / "web/static/webclient/app/dist"
        entry_js = dist / "index.js"
        entry_css = dist / "index.css"
        self.assertTrue(entry_js.is_file() and entry_js.stat().st_size > 0)
        self.assertTrue(entry_css.is_file() and entry_css.stat().st_size > 0)
        # The bundle genuinely carries the preserved UMD reducer, not a stub.
        bundle = entry_js.read_text(encoding="utf-8")
        self.assertIn("PANEL_ALLOWLIST", bundle)
        self.assertIn("createStore", bundle)
        # The built artifact is offline-complete (the ``dist`` is excluded
        # from the authored-source remote-URL scan, so the generated output
        # is guarded here instead of not at all).
        stylesheet = entry_css.read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(REMOTE_URL_CSS_RE, stylesheet),
            "the entry stylesheet references a remote URL",
        )
        self.assertIsNone(
            re.search(REMOTE_URL_JS_RE, bundle),
            "the bundle opens a remote transport connection",
        )

    @covers_requirement(
        "webclient-browser-verification::dom-independent-client-behavior-has-an-executable-node-test-gate"
    )
    def test_losern_lib_wrappers_exist_for_every_preserved_module(self):
        app_lib = REPO_ROOT / "web/webclient-app/lib"
        for wrapper in (
            "protocol.js",
            "keyboard_router.js",
            "narrative_markup.js",
            "local_map.js",
            "option_cards.js",
        ):
            path = app_lib / wrapper
            self.assertTrue(
                path.is_file(), f"ESM wrapper missing: web/webclient-app/lib/{wrapper}"
            )


class VueComponentGateTests(unittest.TestCase):
    @covers_requirement(
        "webclient-browser-verification::dom-independent-client-behavior-has-an-executable-node-test-gate",
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps",
        "webclient-component-showcase::the-component-showcase-is-completed-before-live-wiring-and-is-a-mandatory-ci-gate",
    )
    def test_vitest_component_suite_and_showcase_coverage_run(self):
        vitest = _run(["pnpm", "test"])
        self.assertEqual(
            vitest.returncode,
            0,
            f"the Vue component (Vitest) gate must pass:\n"
            f"{vitest.stdout}\n{vitest.stderr}",
        )
        coverage = _run(["pnpm", "run", "showcase-coverage"])
        self.assertEqual(
            coverage.returncode,
            0,
            f"the component-coverage check must pass:\n"
            f"{coverage.stdout}\n{coverage.stderr}",
        )

    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps"
    )
    def test_pnpm_manifest_and_lockfile_invariants(self):
        package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package.get("packageManager"), "pnpm@12.5.1")
        # The build-script allowlist moved to pnpm-workspace.yaml when the pin
        # reached pnpm 12; package.json must not carry a stale second copy.
        workspace = yaml.safe_load(_read("pnpm-workspace.yaml"))
        self.assertEqual(workspace.get("allowBuilds"), {"esbuild": True})
        self.assertNotIn("pnpm", package)
        self.assertNotIn("allowScripts", package)
        self.assertNotIn("dependencies", package)
        self.assertTrue(package.get("devDependencies"))
        self.assertIn("no runtime Node.js or pnpm dependency", package.get("description", ""))
        self.assertTrue(
            (REPO_ROOT / "pnpm-lock.yaml").is_file(),
            "pnpm-lock.yaml must exist as the committed lockfile",
        )
        self.assertFalse(
            (REPO_ROOT / "package-lock.json").exists(),
            "package-lock.json must be removed after migration to pnpm",
        )

    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps",
        "webclient-component-showcase::the-component-showcase-is-completed-before-live-wiring-and-is-a-mandatory-ci-gate",
    )
    def test_quality_workflow_builds_and_gates_the_vue_frontend(self):
        workflow = yaml.safe_load(_read(".github/workflows/quality-gate.yml"))
        jobs = workflow["jobs"]
        # Every job installs the pin package.json declares, so no job can drift
        # onto a different pnpm than the lockfile was resolved against.
        pinned_pnpm = json.loads(_read("package.json"))["packageManager"]
        frontend = jobs["frontend"]
        steps = {step["name"]: step for step in frontend["steps"]}

        pnpm_step = steps["Install locked pnpm toolchain"]["run"]
        self.assertIn(f"npm install --global {pinned_pnpm}", pnpm_step)
        self.assertIn("pnpm install --frozen-lockfile", pnpm_step)
        self.assertIn("pnpm run build", steps["Build Vue application with Vite"]["run"])
        self.assertIn("pnpm test", steps["Run Vue component tests with Vitest"]["run"])
        self.assertIn(
            "pnpm run build-storybook",
            steps["Build Storybook component showcase"]["run"],
        )
        self.assertIn(
            "pnpm run showcase-coverage",
            steps["Check component coverage"]["run"],
        )
        dist_check = steps["Verify dist artifact"]["run"]
        self.assertIn("web/static/webclient/app/dist/index.js", dist_check)
        self.assertIn("web/static/webclient/app/dist/index.css", dist_check)

        # The dist is built into each browser-test checkout so the portal
        # serves the bundle from the project origin (delta: "built in the
        # browser test workspaces").
        browser_steps = {step["name"]: step for step in jobs["browser"]["steps"]}
        dist_build = browser_steps["Build Vue dist in browser workspaces"]["run"]
        self.assertIn(f"npm install --global {pinned_pnpm}", dist_build)
        self.assertIn(
            "(cd w-a && pnpm install --frozen-lockfile && pnpm run build)",
            dist_build,
        )
        self.assertIn(
            "(cd w-b && pnpm install --frozen-lockfile && pnpm run build)",
            dist_build,
        )

        # The top-level contract tests execute the pnpm gates, so the job
        # needs the Node toolchain and Corepack enabled.
        top_level_step_names = [step["name"] for step in jobs["top-level"]["steps"]]
        self.assertIn("Install Node.js", top_level_step_names)
        self.assertIn("Install locked pnpm toolchain", top_level_step_names)

        # The evennia evidence bridges (web.webclient tests under the Evennia
        # runner) execute the Vue showcase gates as requirement evidence, so
        # every evennia shard job needs the locked Node toolchain too.
        evennia_steps = {step["name"]: step for step in jobs["evennia"]["steps"]}
        self.assertIn(
            "24",
            evennia_steps["Install Node.js"]["with"]["node-version"],
        )
        evennia_pnpm_step = evennia_steps["Install locked pnpm toolchain"]["run"]
        self.assertIn(f"npm install --global {pinned_pnpm}", evennia_pnpm_step)
        self.assertIn("pnpm install --frozen-lockfile", evennia_pnpm_step)


class FrontendLayoutContractTests(unittest.TestCase):
    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps"
    )
    def test_base_html_xor_flag_loads_exactly_one_view_stack(self):
        template = _read("web/templates/webclient/base.html")
        self.assertIn("{% if webclient_vue_enabled %}", template)
        # The Vue branch loads the stable dist entries (CSS + module script).
        vue_branch = template.split("{% if webclient_vue_enabled %}", 1)[1].split(
            "{% else %}", 1
        )[0]
        self.assertIn("webclient/app/dist/index.css", vue_branch)
        self.assertNotIn("jquery-3.2.1.min.js", vue_branch)
        self.assertNotIn("goldenlayout.min.js", vue_branch)
        # The legacy branch loads no view stack at all (C4 removed the jQuery /
        # GoldenLayout / plugin loads); it never carries the Vue dist entries.
        legacy_branch = (
            template.split("{% else %}", 1)[1].split("{% endif %}", 1)[0]
        )
        self.assertNotIn("jquery-3.2.1.min.js", legacy_branch)
        self.assertNotIn("goldenlayout.min.js", legacy_branch)
        self.assertNotIn("webclient/app/dist/index.js", legacy_branch)
        # The D10 text console and the $(document).ready shim are shared (loaded
        # outside the XOR, in both branches).
        self.assertIn(
            '{% static "webclient/js/text_console.js" %}',
            template,
        )
        self.assertNotIn(
            "text_console.js",
            vue_branch + legacy_branch,
            "the text console must not live inside either XOR branch",
        )
        # evennia.js's load-time bootstrap needs the $(document).ready shim in
        # both branches (C4: the legacy fallback branch loads no jQuery).
        self.assertIn("jquery_ready_shim.js", template)
        self.assertNotIn(
            "jquery_ready_shim.js",
            vue_branch + legacy_branch,
            "the ready-shim is shared (both branches), not inside either XOR branch",
        )


if __name__ == "__main__":
    unittest.main()
