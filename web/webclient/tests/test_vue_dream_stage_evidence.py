"""Evidence bridge: run the Vue Vitest suites for the browser dream stage and
link each ``webclient-dream-stage`` main-spec requirement to an executed,
passing Vitest evidence record.

The dream stage (webclient-dream-avg-stage) is implemented and verified in the
Vue layer (``DreamPanel.vue``, ``tests/dream.test.js``). ``covers_requirement``
can only attach to a Python ``test_*`` function, so this module executes the
relevant Vitest files and asserts every test passes. Following the B1/B2
precedent, the ``@covers_requirement`` annotations linking this module to the
new ``webclient-dream-stage`` requirements were applied at this change's
archive, once the delta spec synced into the main spec put the requirement IDs
into the traceability index.
"""

from pathlib import Path
import re
import subprocess
import unittest

from tools.spec_traceability import covers_requirement
from web.webclient.tests._captured_output import without_ansi

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "web/webclient-app/tests"
DREAM_SUITE = TESTS_DIR / "dream.test.js"
MOTION_SUITE = TESTS_DIR / "motion_tokens.test.js"
FAREWELL_SUITE = TESTS_DIR / "dream_farewell.test.js"


def _run_vitest(*test_files, names=()):
    """Run the named Vitest files, restricted to the exact test names given."""
    args = [str(path) for path in test_files]
    if names:
        # Vitest matches against the full "<describe> > <test>" path.
        args += ["-t", "(" + "|".join(re.escape(name) for name in names) + ")$"]
    return without_ansi(
        subprocess.run(
            ["npx", "--no-install", "vitest", "run", *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
    )


def _assert_cases_pass(label, names, *extra_files, suites=(DREAM_SUITE,)):
    """Every named case of ``suites`` (and every case of ``extra_files``) runs and passes.

    The exact-name filter plus the expected count means a renamed or deleted
    case fails this bridge instead of silently narrowing the evidence.
    """
    result = _run_vitest(*suites, names=names)
    assert result.returncode == 0, f"{label} Vitest suite failed:\n{result.stdout}\n{result.stderr}"
    passed = re.search(r"Tests\s+(\d+) passed", result.stdout)
    assert passed and int(passed.group(1)) == len(names), (
        f"{label}: expected {len(names)} matching Vitest cases\n{result.stdout}"
    )
    for extra in extra_files:
        extra_result = _run_vitest(extra)
        assert extra_result.returncode == 0, f"{label} {extra.name} failed:\n{extra_result.stdout}"


class VueDreamStageEvidenceTest(unittest.TestCase):
    @covers_requirement(
        "webclient-dream-stage::the-dream-is-a-full-stage-avg-scene-over-its-official-artwork"
    )
    def test_full_stage_avg_scene_over_official_artwork(self):
        _assert_cases_pass(
            "dream stage regions and artwork fallback",
            (
                'server-authored dream surface > stages the dream with core button chrome, one decisive action, and a keepsake card',
                'server-authored dream surface > renders the server-resolved scene artwork, degrading on a failed load',
                'server-authored dream surface > shows the bundled dream when the preferred image is absent and the reached fact when every illustration is missing',
                'server-authored dream surface > recomputes a changed descriptor revision and ignores the retired callback',
                'server-authored dream surface > mirrors the strict panel schema and truthful command echoes',
                'dream stage review coverage > names the dialog by its visible title and shows the empty invitation',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::exchange-budget-and-goddess-excitement-have-visual-non-colour-only-forms"
    )
    def test_tracks_have_visual_non_colour_only_forms(self):
        _assert_cases_pass(
            "dream budget pips and excitement gauge",
            (
                'server-authored dream surface > stages the dream with core button chrome, one decisive action, and a keepsake card',
                'server-authored dream surface > reveals a response only on a live exchange increase',
                'dream stage review coverage > lights the gauge to the ordinal and marks the next pip while composing',
                'dream stage review coverage > keeps the next pip marked while a response is pending',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::narration-and-dialogue-are-paced-by-beats-that-only-animate-on-a-live-exchange"
    )
    def test_beats_animate_only_on_live_exchange(self):
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

    @covers_requirement(
        "webclient-dream-stage::the-reply-bar-sends-bounded-free-text-and-hands-it-back-on-failure"
    )
    def test_reply_bar_bounded_send_and_failure_handback(self):
        _assert_cases_pass(
            "dream reply bar",
            (
                'server-authored dream surface > stages the dream with core button chrome, one decisive action, and a keepsake card',
                'server-authored dream surface > submits exact bounded Unicode message parts on Enter but not Shift+Enter',
                'server-authored dream surface > ignores Enter while an IME composition is in progress',
                'server-authored dream surface > keeps draft and awakening usable at cap, during generation and after failure',
                'server-authored dream surface > hands the sent words back for a retry after a failed generation',
                'dream stage review coverage > disables every dream action while the transport is locked and keeps typed text',
                'dream stage review coverage > captions the converging and final exchange and focuses the confirm row on a live sixth exchange',
                'dream stage review coverage > keeps edited chips across a republish and new reply text across a failure',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::direction-confirmation-is-validated-locally-without-discarding-words"
    )
    def test_direction_confirmation_validated_locally(self):
        _assert_cases_pass(
            "dream local wish validation",
            (
                'server-authored dream surface > refuses an empty confirm locally and opens the edit sheet on the summary',
                'server-authored dream surface > blocks an over-length summary instead of truncating it',
                'dream stage review coverage > leaves a text field on Escape, focuses the summary on an empty confirm, and makes the stage inert under the sheet',
                'dream stage review coverage > protects an unsaved edit of the finalized wish and refuses an over-length draft',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::escape-never-awakens-and-awakening-protects-unsaved-local-words"
    )
    def test_escape_never_awakens_and_awaken_check(self):
        _assert_cases_pass(
            "dream Escape and awaken check",
            (
                'server-authored dream surface > keeps draft and awakening usable at cap, during generation and after failure',
                'server-authored dream surface > never awakens on Escape and confirms before discarding unsent words',
                'server-authored dream surface > edits preference chips and saves a draft that keeps the dream open',
                'dream stage review coverage > loads a saved finalized proposal on mount as unedited values',
                'dream stage review coverage > leaves a text field on Escape, focuses the summary on an empty confirm, and makes the stage inert under the sheet',
                'dream stage review coverage > protects an unsaved edit of the finalized wish and refuses an over-length draft',
                'dream stage review coverage > names what the awaken check would lose and that the wish is kept',
                'staged keepsake rows > opens the read-only view, asks before finalizing and drafts without content while conversing',
                'finalize confirmation > names the exchanges given up and rests focus on staying',
                'thread choice > dispatches a newly chosen thread and returns focus to the reply field',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::republished-drafts-rehydrate-without-overwriting-the-player-s-own-edits"
    )
    def test_republished_drafts_rehydrate_without_overwriting_edits(self):
        _assert_cases_pass(
            "dream proposal rehydration",
            (
                'server-authored dream surface > rehydrates a same-session external proposal change without clearing unsent chat',
                'server-authored dream surface > keeps an edited summary when the finalized proposal republishes',
                'dream stage review coverage > loads a saved finalized proposal on mount as unedited values',
                'dream stage review coverage > loads an unchanged proposal as unedited when the session becomes finalized',
                'dream stage review coverage > keeps edited chips across a republish and new reply text across a failure',
                'dream stage review coverage > lets unedited lists follow a republished finalized proposal',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::dream-confirmation-displays-the-frozen-experience-requirements"
    )
    def test_confirmation_displays_frozen_experience_requirements(self):
        _assert_cases_pass(
            "dream experience requirements",
            (
                'shown experience requirements > lists the rows with readable kind labels in the view and the sheet and sends exactly those rows',
                'shown experience requirements > shows republished rows without clearing unsent words',
                'finalized edit sheet > sends the same payload shape from both sheet controls',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::the-keepsake-card-shows-the-current-wish-and-stage-specific-rows"
    )
    def test_keepsake_card_shows_wish_and_stage_rows(self):
        _assert_cases_pass(
            "dream keepsake card and stage rows",
            (
                'server-authored dream surface > stages the dream with core button chrome, one decisive action, and a keepsake card',
                'staged keepsake rows > opens the read-only view, asks before finalizing and drafts without content while conversing',
                'staged keepsake rows > opens the edit sheet, drafts and confirms the form when finalized',
                'staged keepsake rows > holds the finalize row while a response is pending',
                'staged keepsake rows > activates rows by digit only outside text fields and without modifiers',
                'staged keepsake rows > marks the thread line locked and names the new, chosen or vanished thread',
                'staged keepsake rows > shows the draft toast only once a newer committed state reports a saved draft',
                'dream stage review coverage > captions the converging and final exchange and focuses the confirm row on a live sixth exchange',
                'dream stage review coverage > focuses the first row on a live sixth exchange without a summary',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::the-whole-wish-is-read-only-while-conversing"
    )
    def test_whole_wish_is_read_only_while_conversing(self):
        _assert_cases_pass(
            "dream whole-wish view",
            (
                'whole-wish view > renders every proposal field as plain text with placeholders and no form fields',
                'whole-wish view > closes the view and opens the finalize confirmation from its finalize control',
                'whole-wish view > follows a republished proposal while open',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::finalize-asks-before-giving-up-remaining-exchanges"
    )
    def test_finalize_asks_before_giving_up_exchanges(self):
        _assert_cases_pass(
            "dream finalize confirmation",
            (
                'finalize confirmation > names the exchanges given up and rests focus on staying',
                'finalize confirmation > cannot finalize and submit from a repeated key',
                'finalize confirmation > dispatches exactly one finalize from its explicit control',
                'finalize confirmation > opens the edit sheet when the session becomes finalized before the cap',
                'dream stage review coverage > captions the converging and final exchange and focuses the confirm row on a live sixth exchange',
                'dream stage review coverage > focuses the first row on a live sixth exchange without a summary',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::the-thread-choice-sits-above-the-reply-bar-before-the-first-message"
    )
    def test_thread_choice_sits_above_reply_bar(self):
        _assert_cases_pass(
            "dream thread choice",
            (
                'thread choice > dispatches a newly chosen thread and returns focus to the reply field',
                'thread choice > dispatches nothing when the chosen option is reselected',
                'thread choice > closes the list only when focus really moves elsewhere',
                'thread choice > sends only the message when the player speaks without choosing',
                'thread choice > is absent with nothing offered or once choosing is locked',
                'dream stage review coverage > disables every dream action while the transport is locked and keeps typed text',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::the-edit-sheet-edits-the-wish-only-when-finalized"
    )
    def test_edit_sheet_edits_wish_only_when_finalized(self):
        _assert_cases_pass(
            "dream finalized edit sheet",
            (
                'server-authored dream surface > edits preference chips and saves a draft that keeps the dream open',
                'server-authored dream surface > sends the latest committed revision from the finalized sheet',
                'finalized edit sheet > sends the same payload shape from both sheet controls',
                'finalized edit sheet > shows the chosen thread as fixed text with no control that changes it',
                'finalized edit sheet > releases an ended thread to a new story',
                'finalized edit sheet > cannot be reached while conversing',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::the-keepsake-card-reports-what-the-last-exchange-changed"
    )
    def test_keepsake_card_reports_last_exchange_changes(self):
        _assert_cases_pass(
            "dream keepsake change line",
            (
                'keepsake change line > names the changed fields with their added and removed counts',
                'keepsake change line > states that nothing changed in words different from a changed turn',
                'keepsake change line > renders no change line without a report',
                'keepsake change line > holds the wish and its line until the last beat has been read in full',
                'keepsake change line > announces a settled line once and not again on a republish of the same report',
                'keepsake change line > shows the committed report at once on mount',
                'keepsake change line > shows no change line once finalized',
                'keepsake change line > announces no change line when the exchange finalizes the session',
                'keepsake change line > settles a held wish when the player speaks again before reading it',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::the-whole-wish-view-marks-changes-and-names-removed-items"
    )
    def test_whole_wish_marks_changes_and_names_removed_items(self):
        _assert_cases_pass(
            "dream whole-wish change marks",
            (
                'whole-wish change marks > marks the changed field, the added item and names the removed one under it',
                'whole-wish change marks > names a removed requirement row under the requirement section',
                'whole-wish change marks > leaves untouched fields unmarked',
                'whole-wish change marks > marks a formed summary differently from a changed one',
            ),
        )

    @covers_requirement(
        "webclient-dream-stage::requirement-rows-are-editable-when-finalized"
    )
    def test_requirement_rows_are_editable_when_finalized(self):
        _assert_cases_pass(
            "dream editable requirement rows",
            (
                'editable requirement rows > adds, edits and removes rows and drafts exactly the remaining rows in order',
                'editable requirement rows > counts eight of eight and offers no add control at the limit',
                'editable requirement rows > blocks draft and confirm on a blank row, marks it and keeps every other value',
                'editable requirement rows > names an unsaved row edit in the awaken check',
                'editable requirement rows > lets unedited rows follow a republish and keeps edited ones',
            ),
        )

    def test_live_departure_plays_a_farewell_before_the_stage_releases(self):
        _assert_cases_pass(
            "dream farewell",
            (
                'dream farewell > replaces the controls with the farewell line',
                'dream farewell > dispatches nothing from a control and keeps Tab on the band',
                'dream farewell > releases when motion leaves full during the fade, and never after unmount',
                'dream farewell > presents the line even when the closed state still carries a failure',
                'dream farewell > completes the typing, then releases at full motion when the fade ends',
                'dream farewell > releases at full motion on a further activation or when the fade never ends',
                'dream farewell > shows the line at once and releases on activation at reduced motion',
                'dream farewell > shows the line at once and releases on activation at off motion',
                'dream farewell > names waking in the key hint once the line is shown in full',
                'dream farewell > plays no farewell for a departure without ending text',
                'dream farewell hold > holds a live departure of the same session that carries an ending',
                'dream farewell hold > does not hold a state that is already closed when first seen',
                'dream farewell hold > does not hold a closed state of a different session',
                'dream farewell hold > does not hold a departure without ending text',
                'dream farewell hold > keeps the hold unchanged when the same closed state republishes',
                'dream farewell hold > drops a held farewell on disconnect',
                'dream farewell hold > discards a held farewell when a new open dream is committed',
                'dream farewell hold > releases the stage on release()',
                'dream farewell hold > raises the store flag while a farewell is held and lowers it on release',
            ),
            suites=(DREAM_SUITE, FAREWELL_SUITE),
        )
