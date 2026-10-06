"""Evidence bridge: run the Vue Vitest suites for the browser dream stage and
link each ``webclient-dream-stage`` main-spec requirement to an executed,
passing Vitest evidence record.

The dream stage (webclient-dream-avg-stage) is implemented and verified in the
Vue layer (``DreamPanel.vue``, ``tests/dream.test.js``). ``covers_requirement``
can only attach to a Python ``test_*`` function, so this module executes the
relevant Vitest files and asserts every test passes. The capability is new in
that change: its canonical requirement IDs exist only once the archive's delta
sync creates ``openspec/specs/webclient-dream-stage/spec.md``, and the
``covers_requirement`` annotations are attached to the methods below at that
point (the ID each method will carry is named in its comment).
"""

from pathlib import Path
import re
import subprocess
import unittest

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "web/webclient-app/tests"
DREAM_SUITE = TESTS_DIR / "dream.test.js"
MOTION_SUITE = TESTS_DIR / "motion_tokens.test.js"


def _run_vitest(*test_files, names=()):
    """Run the named Vitest files, restricted to the exact test names given."""
    args = [str(path) for path in test_files]
    if names:
        # Vitest matches against the full "<describe> > <test>" path.
        args += ["-t", "(" + "|".join(re.escape(name) for name in names) + ")$"]
    return subprocess.run(
        ["npx", "--no-install", "vitest", "run", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )


def _assert_cases_pass(label, names, *extra_files):
    """Every named dream case (and every case of ``extra_files``) runs and passes.

    The exact-name filter plus the expected count means a renamed or deleted
    case fails this bridge instead of silently narrowing the evidence.
    """
    result = _run_vitest(DREAM_SUITE, names=names)
    assert result.returncode == 0, f"{label} Vitest suite failed:\n{result.stdout}\n{result.stderr}"
    passed = re.search(r"Tests\s+(\d+) passed", result.stdout)
    assert passed and int(passed.group(1)) == len(names), (
        f"{label}: expected {len(names)} matching Vitest cases\n{result.stdout}"
    )
    for extra in extra_files:
        extra_result = _run_vitest(extra)
        assert extra_result.returncode == 0, f"{label} {extra.name} failed:\n{extra_result.stdout}"


class VueDreamStageEvidenceTest(unittest.TestCase):
    def test_full_stage_avg_scene_over_official_artwork(self):
        # webclient-dream-stage::the-dream-is-a-full-stage-avg-scene-over-its-official-artwork
        _assert_cases_pass(
            "dream stage regions and artwork fallback",
            (
                'server-authored dream surface > stages the dream with core button chrome, one decisive action, and a keepsake card',
                'server-authored dream surface > renders the server-resolved scene artwork, degrading on a failed load',
                'dream stage review coverage > names the dialog, shows the empty invitation, orders rows and maps digits 2 and 3',
            ),
        )

    def test_tracks_have_visual_non_colour_only_forms(self):
        # webclient-dream-stage::exchange-budget-and-goddess-excitement-have-visual-non-colour-only-forms
        _assert_cases_pass(
            "dream budget pips and excitement gauge",
            (
                'server-authored dream surface > stages the dream with core button chrome, one decisive action, and a keepsake card',
                'server-authored dream surface > reveals a response only on a live exchange increase',
                'dream stage review coverage > lights the gauge to the ordinal and marks the next pip while composing',
            ),
        )

    def test_beats_animate_only_on_live_exchange(self):
        # webclient-dream-stage::narration-and-dialogue-are-paced-by-beats-that-only-animate-on-a-live-exchange
        _assert_cases_pass(
            "dream beat pacing",
            (
                'server-authored dream surface > types the opening on arrival and shows a rejoined exchange in full',
                'server-authored dream surface > reveals a response only on a live exchange increase',
                'dream stage review coverage > types a live reveal at full motion and completes, then advances, on activation',
                'dream stage review coverage > announces a response, pending and failure once each',
            ),
            MOTION_SUITE,
        )

    def test_reply_bar_bounded_send_and_failure_handback(self):
        # webclient-dream-stage::the-reply-bar-sends-bounded-free-text-and-hands-it-back-on-failure
        _assert_cases_pass(
            "dream reply bar",
            (
                'server-authored dream surface > submits exact bounded Unicode message parts on Enter but not Shift+Enter',
                'server-authored dream surface > ignores Enter while an IME composition is in progress',
                'server-authored dream surface > keeps confirm/draft/awakening usable at cap, during generation and after failure',
                'server-authored dream surface > hands the sent words back for a retry after a failed generation',
                'dream stage review coverage > disables every dream action while the transport is locked and keeps typed text',
                'dream stage review coverage > captions the converging and final exchange and focuses the carry-out row on a live sixth exchange',
                'dream stage review coverage > keeps edited thread and chips across a republish and new reply text across a failure',
            ),
        )

    def test_keepsake_card_and_distinct_exits(self):
        # webclient-dream-stage::the-keepsake-card-shows-the-念頭-that-would-be-carried-out-and-offers-distinct-exits
        _assert_cases_pass(
            "dream keepsake card and exits",
            (
                'server-authored dream surface > stages the dream with core button chrome, one decisive action, and a keepsake card',
                'server-authored dream surface > labels the 念頭 provenance and activates rows by digit outside text fields',
                'server-authored dream surface > keeps confirm/draft/awakening usable at cap, during generation and after failure',
                'dream stage review coverage > captions the converging and final exchange and focuses the carry-out row on a live sixth exchange',
                'dream stage review coverage > names the dialog, shows the empty invitation, orders rows and maps digits 2 and 3',
            ),
        )

    def test_direction_sheet_flat_modal_layer(self):
        # webclient-dream-stage::the-念頭-sheet-edits-the-direction-in-one-flat-modal-layer
        _assert_cases_pass(
            "dream 念頭 sheet",
            (
                'server-authored dream surface > filters a long thread list and keeps an orphaned saved thread selectable',
                'server-authored dream surface > uses the latest server revision after reconnect and retains explicit direction for draft/confirm',
                'server-authored dream surface > edits preference chips and saves a draft that keeps the dream open',
                'dream stage review coverage > leaves a text field on Escape, focuses the summary on an empty confirm, and makes the stage inert under the sheet',
            ),
        )

    def test_direction_confirmation_validated_locally(self):
        # webclient-dream-stage::direction-confirmation-is-validated-locally-without-discarding-words
        _assert_cases_pass(
            "dream local direction validation",
            (
                'server-authored dream surface > refuses an empty carry-out locally and opens the 念頭 sheet',
                'server-authored dream surface > blocks an over-length summary instead of truncating it',
                'dream stage review coverage > leaves a text field on Escape, focuses the summary on an empty confirm, and makes the stage inert under the sheet',
                'dream stage review coverage > protects an unsaved 念頭 edit and refuses an over-length draft',
            ),
        )

    def test_escape_never_awakens_and_awaken_check(self):
        # webclient-dream-stage::escape-never-awakens-and-awakening-protects-unsaved-local-words
        _assert_cases_pass(
            "dream Escape and awaken check",
            (
                'server-authored dream surface > keeps confirm/draft/awakening usable at cap, during generation and after failure',
                'server-authored dream surface > never awakens on Escape and confirms before discarding unsent words',
                'server-authored dream surface > edits preference chips and saves a draft that keeps the dream open',
                'dream stage review coverage > leaves a text field on Escape, focuses the summary on an empty confirm, and makes the stage inert under the sheet',
                'dream stage review coverage > protects an unsaved 念頭 edit and refuses an over-length draft',
            ),
        )

    def test_republished_drafts_rehydrate_without_overwriting_edits(self):
        # webclient-dream-stage::republished-drafts-rehydrate-without-overwriting-the-player-s-own-edits
        _assert_cases_pass(
            "dream draft rehydration",
            (
                'server-authored dream surface > rehydrates a same-session external draft change without clearing unsent chat',
                'server-authored dream surface > keeps an unsent direction edit when an exchange republishes the authored direction',
                'dream stage review coverage > loads saved draft preferences on mount as already saved',
                'dream stage review coverage > keeps edited thread and chips across a republish and new reply text across a failure',
            ),
        )
