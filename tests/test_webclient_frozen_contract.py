"""Repository-wide contract for the Phase-0 frozen WebClient contract audit.

Change ``webclient-vue-00-audit-and-design-docs`` (roadmap A1) freezes, as its
committed deliverable at ``docs/development/webclient-vue-frozen-contract-audit.md``,
(a) the exact ``window.Elosern.*`` façade-bridge surface the browser bridge must
expose and (b) the complete, non-overlapping ``MODIFIED``/``RENAMED`` delta list
for the implementation-bound ``webclient-*`` requirements. This test verifies
that deliverable: it exists, declares the bridge change as its binding
consumer, freezes exactly the four façades with their members, and carries a
delta list that is structurally complete, non-overlapping, scoped to real
current main-spec requirements, and assigned to real applying changes.
"""

from pathlib import Path
import json
import re
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT = REPO_ROOT / "docs" / "development" / "webclient-vue-frozen-contract-audit.md"
SPECS_ROOT = REPO_ROOT / "openspec" / "specs"

FROZEN_FACADES = ("Protocol", "KeyboardRouter", "narrativeInput", "actions")
DELTA_LIST_KEY = "frozen-delta-list"
FACADE_KEY = "frozen-facade-surface"
APPLYING_CHANGES = {
    "webclient-vue-08-wire-bridge-contracts",
    "webclient-vue-10-wire-views-browser",
}
DELTA_KINDS = {"MODIFIED", "RENAMED", "RENAMED+MODIFIED"}
CLASSIFICATION_BUCKETS = {
    "PRESERVE-VIA-BRIDGE",
    "PRESERVE-SAME-HOOK",
    "REMAP-TO-TESTID",
    "RETIRED-WITH-SHELL",
    "HARNESS-REMAP",
    "DELTA",
}
DELTA_ID_PREFIXES = {
    "webclient-vue-08-wire-bridge-contracts": "C2",
    "webclient-vue-10-wire-views-browser": "C4",
}
LOGIN_PAGE_EXEMPT = {"id_username", "id_password"}
# ARIA / attribute selectors the managed suite uses only for assertions; they
# are not contract hooks, so they are exempt from the frozen-list completeness
# check.
ATTRIBUTE_EXEMPT = {"role", "aria-expanded", "disabled", "data-testid^"}
# Probe selectors the suite uses only to assert an element is absent — not
# contract hooks, so they are exempt from the completeness check.
HELPER_EXEMPT = {"missing-el"}
# Known distinct-hook pairs where one hook name is a strict prefix of the other
# without a `-`/`__` separator (the field id and its wrapper class).
OVERLAP_EXEMPT = {("inputfield", "inputfieldwrapper")}

EXPECTED_PROTOCOL_COUNT = 142
EXPECTED_PROTOCOL_CREATE_STORE_MEMBERS = (
    "getState",
    "subscribe",
    "setConnected",
    "beginTransport",
    "receive",
)
EXPECTED_PROTOCOL_ENVELOPE_NAMES = (
    "ui_sync",
    "ui_action",
    "ui_snapshot",
    "ui_update",
    "ui_action_result",
    "ui_protocol_error",
    "connection_open",
)
EXPECTED_KEYBOARDROUTER_MEMBERS = (
    "ARROW_UP",
    "ARROW_DOWN",
    "ARROW_LEFT",
    "ARROW_RIGHT",
    "ENTER",
    "ESCAPE",
    "SPACE",
    "SLASH",
    "menuItem",
    "createRouter",
)
EXPECTED_KEYBOARDROUTER_INSTANCE_MEMBERS = (
    "pushMenu",
    "replaceMenu",
    "popMenu",
    "reset",
    "depth",
    "currentItem",
    "currentMenu",
    "setMutationInFlight",
    "isMutationInFlight",
    "setAwaitingRevision",
    "isAwaitingRevision",
    "clearRepeatGuard",
    "press",
    "handle",
    "focus",
    "focusItemByKey",
    "confirm",
    "trail",
    "rootMenu",
)
EXPECTED_NARRATIVEINPUT_MEMBERS = (
    "appendInput",
    "mountChoicePoint",
    "replaceChoicePoint",
    "unmountChoicePoint",
)
EXPECTED_ACTIONS_MEMBERS = (
    "client",
    "sync",
    "submit",
    "handleActionResult",
    "handlePresentation",
    "handleReconnect",
    "handleTransportReset",
    "requestResync",
    "resetResyncEpisode",
)
EXPECTED_ACTIONS_CLIENT_MEMBERS = (
    "sync",
    "submit",
    "onActionResult",
    "onPresentationAccepted",
    "onReconnect",
    "onDetached",
    "onTransportReset",
    "isLocked",
    "isInFlight",
    "inFlightRequestId",
    "uncertain",
    "lastResult",
)


def _fenced_json_blocks(text: str) -> list[dict[str, object]]:
    blocks = []
    for match in re.finditer(r"```json\n(.*?)```", text, re.DOTALL):
        blocks.append(json.loads(match.group(1)))
    return blocks


def _css_hooks(selector: str) -> set[str]:
    """Extract the checkable hook tokens from a CSS selector string.

    Handles id fragments (``#id``), class fragments (``.class``), attribute
    selectors (``[data-item-key]``), and element-prefixed hooks
    (``img.participant-frame__portrait``). Non-hook attributes (``role``,
    ``aria-expanded``, ``disabled``) are returned so the caller can exempt them.
    """
    hooks: set[str] = set()
    sel = selector.strip()
    if sel.startswith("["):
        attr = sel.strip("[]").split("=")[0]
        hooks.add(attr)
        return hooks
    if sel.startswith("#"):
        for fragment in sel.split():
            frag = fragment.split(":", 1)[0].split("[", 1)[0]
            if frag.startswith("#"):
                hooks.add(frag.lstrip("#"))
            elif frag.startswith("."):
                hooks.add(frag.lstrip("."))
        return hooks
    if sel.startswith("."):
        hooks.add(sel.split(":", 1)[0].split("[", 1)[0].lstrip("."))
        return hooks
    if sel.startswith("img.") or sel.startswith("svg."):
        hooks.add(sel.split(".", 1)[1].split(":", 1)[0].split("[", 1)[0])
        return hooks
    return hooks


class WebClientFrozenContractAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.text = AUDIT.read_text(encoding="utf-8")
        blocks = _fenced_json_blocks(cls.text)
        cls.facade_block = next(
            (block for block in blocks if FACADE_KEY in block), None
        )
        cls.delta_block = next(
            (block for block in blocks if DELTA_LIST_KEY in block), None
        )

    @covers_requirement(
        "webclient-browser-verification::the-implementation-bound-public-contract-is-frozen-before-the-shell-is-swapped",
    )
    def test_frozen_contract_audit_exists_and_declares_the_binding_consumer(self):
        self.assertTrue(AUDIT.is_file())
        self.assertIn("webclient-vue-08-wire-bridge-contracts", self.text)
        self.assertIn("binding consumer", self.text.lower())

    @covers_requirement(
        "webclient-browser-verification::the-implementation-bound-public-contract-is-frozen-before-the-shell-is-swapped",
    )
    def test_frozen_facade_surface_freezes_exactly_the_four_facades(self):
        self.assertIsNotNone(self.facade_block, "frozen-facade-surface JSON block")
        surface = self.facade_block[FACADE_KEY]
        self.assertEqual(
            set(surface),
            set(FROZEN_FACADES),
            "exactly the four frozen façades, no more",
        )
        for facade in FROZEN_FACADES:
            members = surface[facade].get("members")
            self.assertIsInstance(members, list)
            self.assertTrue(members)
            self.assertTrue(
                all(isinstance(item, str) and item for item in members), facade
            )
            self.assertEqual(
                len(members),
                len(set(members)),
                f"duplicate members frozen for {facade}",
            )
        protocol = surface["Protocol"]
        self.assertEqual(
            len(protocol["members"]),
            EXPECTED_PROTOCOL_COUNT,
            "the frozen Protocol member count drifted from the Phase-0 snapshot",
        )
        for member in ("PROTOCOL_VERSION", "createStore", "validateSnapshot"):
            self.assertIn(member, protocol["members"])
        self.assertEqual(
            sorted(protocol["create_store_members"]),
            sorted(EXPECTED_PROTOCOL_CREATE_STORE_MEMBERS),
        )
        for member in protocol["create_store_members"]:
            self.assertNotIn(member, protocol["members"])
        self.assertEqual(
            sorted(protocol["envelope_names"]),
            sorted(EXPECTED_PROTOCOL_ENVELOPE_NAMES),
        )
        self.assertEqual(
            sorted(surface["KeyboardRouter"]["members"]),
            sorted(EXPECTED_KEYBOARDROUTER_MEMBERS),
        )
        self.assertEqual(
            sorted(surface["KeyboardRouter"]["router_instance_members"]),
            sorted(EXPECTED_KEYBOARDROUTER_INSTANCE_MEMBERS),
        )
        self.assertEqual(
            sorted(surface["narrativeInput"]["members"]),
            sorted(EXPECTED_NARRATIVEINPUT_MEMBERS),
        )
        self.assertEqual(
            sorted(surface["actions"]["members"]),
            sorted(EXPECTED_ACTIONS_MEMBERS),
        )
        self.assertEqual(
            sorted(surface["actions"]["client_members"]),
            sorted(EXPECTED_ACTIONS_CLIENT_MEMBERS),
        )

    @covers_requirement(
        "webclient-browser-verification::the-implementation-bound-public-contract-is-frozen-before-the-shell-is-swapped",
    )
    def test_delta_list_structure_and_non_overlap(self):
        self.assertIsNotNone(self.delta_block, "frozen-delta-list JSON block")
        entries = self.delta_block[DELTA_LIST_KEY]
        self.assertIsInstance(entries, list)
        self.assertTrue(entries)
        seen_pairs: set[tuple[str, str]] = set()
        for entry in entries:
            with self.subTest(delta_id=entry.get("delta_id")):
                for field in (
                    "delta_id",
                    "kind",
                    "capability",
                    "requirement",
                    "applying_change",
                    "directive",
                    "rationale",
                ):
                    self.assertIn(field, entry)
                    self.assertTrue(str(entry[field]).strip())
                self.assertIn(entry["kind"], DELTA_KINDS)
                self.assertIn(entry["applying_change"], APPLYING_CHANGES)
                prefix = DELTA_ID_PREFIXES[entry["applying_change"]]
                self.assertTrue(
                    str(entry["delta_id"]).startswith(f"{prefix}-"),
                    f"delta_id {entry['delta_id']} does not match its applying change {prefix}",
                )
                if entry["kind"] in ("RENAMED", "RENAMED+MODIFIED"):
                    self.assertIn("rename_to", entry)
                    self.assertTrue(str(entry["rename_to"]).strip())
                pair = (entry["capability"], entry["requirement"])
                self.assertNotIn(pair, seen_pairs, "overlapping delta entry")
                seen_pairs.add(pair)
        self.assertEqual(len({entry["delta_id"] for entry in entries}), len(entries))

    def test_delta_entries_reference_current_main_spec_requirements(self):
        entries = self.delta_block[DELTA_LIST_KEY]
        for entry in entries:
            spec = SPECS_ROOT / entry["capability"] / "spec.md"
            with self.subTest(delta_id=entry["delta_id"]):
                self.assertTrue(spec.is_file(), f"unknown capability {spec}")
                source = spec.read_text(encoding="utf-8")
                self.assertIn(
                    f"### Requirement: {entry['requirement']}\n",
                    source,
                    "delta names a requirement not present in the current main spec",
                )

    @covers_requirement(
        "webclient-browser-verification::the-implementation-bound-public-contract-is-frozen-before-the-shell-is-swapped",
    )
    def test_classification_table_covers_every_contract_in_one_bucket(self):
        section = self.text.split("## 2. Classification", 1)[1].split(
            "## 3. Delta list", 1
        )[0]
        header_cells = {
            "Identifier",
            "Hook",
            "Key / constant",
            "Contract",
            "Global",
            "What it is",
            "Current owner",
            "Decider",
            "Bucket",
            "Evidence",
            "Rationale",
        }
        row_count = 0
        for line in section.splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 3 or set(cells) <= {"", "---", ":---"}:
                continue
            if any(cell in header_cells for cell in cells):
                continue
            buckets = {cell for cell in cells if cell in CLASSIFICATION_BUCKETS}
            self.assertEqual(
                len(buckets),
                1,
                f"each classification row must carry exactly one bucket: {line}",
            )
            row_count += 1
        self.assertGreater(
            row_count,
            20,
            "the classification section must assign every contract to a bucket",
        )
        for bucket in (
            "PRESERVE-VIA-BRIDGE",
            "PRESERVE-SAME-HOOK",
            "REMAP-TO-TESTID",
            "RETIRED-WITH-SHELL",
            "HARNESS-REMAP",
            "DELTA",
        ):
            with self.subTest(bucket=bucket):
                self.assertIn(bucket, section)

    @covers_requirement(
        "webclient-browser-verification::the-implementation-bound-public-contract-is-frozen-before-the-shell-is-swapped",
    )
    def test_every_key_contract_family_is_classified(self):
        for family in (
            "façades",
            "Keyboard / plugin key-event path",
            "DOM identifiers",
            "Layout-persistence keys",
            "Input path",
        ):
            with self.subTest(family=family):
                self.assertIn(family, self.text.split("## 2. Classification", 1)[1])

    @covers_requirement(
        "webclient-browser-verification::the-implementation-bound-public-contract-is-frozen-before-the-shell-is-swapped",
    )
    def test_every_managed_browser_target_is_frozen(self):
        section = self.text.split("### 2.3 ", 1)[1].split("### 2.4 ", 1)[0]
        exact: set[str] = set()
        prefixes: set[str] = set()
        for token in re.findall(r"`([^`]+)`", section):
            # Normalize the token so CSS class hooks (`.dock-menu-item`) and id
            # hooks (`#action-dock`) compare equal to the bare identifier the
            # managed suite targets.
            norm = token.lstrip(".#")
            if "<" in token:
                prefixes.add(norm.split("<", 1)[0])
            else:
                exact.add(norm)
        browser_root = REPO_ROOT / "web" / "tests" / "browser"
        targets: set[str] = set()
        for path in sorted(browser_root.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            for match in re.finditer(
                r"getElementById\(\s*['\"]([\w-]+)['\"]", source
            ):
                targets.add(match.group(1))
            for match in re.finditer(r"['\"]#(\w[\w-]*)['\"]", source):
                targets.add(match.group(1))
            # C4 re-map: the Vue surfaces carry the legacy identifier string
            # as a `data-testid`; the managed-browser slices retarget to
            # `document.querySelector('[data-testid="..."]')`.
            for match in re.finditer(
                r"data-testid=['\"]([\w-]+)['\"]", source
            ):
                targets.add(match.group(1))
            # H6 renewal: CSS class hooks targeted through `page.locator("...")`
            # are re-mapped to stable hooks listed in the renewed §2.3.
            for match in re.finditer(r"\.locator\(\s*['\"]([^'\"]+)['\"]", source):
                for hook in _css_hooks(match.group(1)):
                    targets.add(hook)
        self.assertGreater(
            len(targets),
            20,
            "the managed-browser target scan should find the suite's id universe",
        )
        for identifier in sorted(targets):
            with self.subTest(identifier=identifier):
                covered = (
                    identifier in exact
                    or any(identifier.startswith(prefix) for prefix in prefixes)
                    or identifier in LOGIN_PAGE_EXEMPT
                    or identifier in ATTRIBUTE_EXEMPT
                    or identifier in HELPER_EXEMPT
                )
                self.assertTrue(
                    covered,
                    f"browser-suite target #{identifier} is not in the renewed "
                    "frozen audit §2.3 list (or an explicit exemption)",
                )

    def test_renewed_identifier_list_is_complete_and_non_overlapping(self):
        """The re-frozen re-mapped `data-testid` set (the H1–H5 re-map table) is
        the complete required hook set: no hook is listed twice, and no two hooks
        shadow each other without a `-`/`__` family separator."""
        section = self.text.split("### 2.3 ", 1)[1].split("### 2.4 ", 1)[0]
        # Scope the check to the re-mapped `data-testid` table — the re-frozen
        # set H6 owns. The preserved-hooks and CSS-class tables are context and
        # may legitimately reference the same hooks, so they are excluded here.
        start = section.index("**Re-mapped `data-testid` set (H1–H5)**")
        end = section.index("**CSS class hooks the managed browser suite targets**")
        remap_block = section[start:end]
        # Collect hook entries from the table rows only; the block's prose and
        # heading mention the word `data-testid` but are not hook entries.
        tokens = [
            match.group(1)
            for line in remap_block.splitlines()
            if line.lstrip().startswith("|")
            for match in re.finditer(r"`([^`]+)`", line)
        ]
        # Normalize for comparison (strip a leading `#`/`.` if present).
        def norm(t: str) -> str:
            return t.lstrip(".#")

        # No hook family is listed twice within the re-mapped set.
        seen: set[str] = set()
        for token in tokens:
            key = norm(token)
            with self.subTest(token=token):
                self.assertNotIn(
                    key,
                    seen,
                    f"hook family `{key}` is listed twice in the re-mapped set",
                )
                seen.add(key)
        # No two exact hooks shadow each other without a `-`/`__` separator.
        exact_tokens = [t for t in tokens if "<" not in t]
        for i, a in enumerate(exact_tokens):
            for b in exact_tokens[i + 1:]:
                na, nb = norm(a), norm(b)
                if na == nb or not nb.startswith(na):
                    continue
                continuation = nb[len(na):]
                separator_ok = continuation.startswith("-") or continuation.startswith(
                    "__"
                )
                exempt = (na, nb) in OVERLAP_EXEMPT or (nb, na) in OVERLAP_EXEMPT
                with self.subTest(pair=(a, b)):
                    self.assertTrue(
                        separator_ok or exempt,
                        f"hook `{nb}` shadows `{na}` without a `-`/`__` family "
                        "separator and no exemption",
                    )

    @covers_requirement(
        "webclient-browser-verification::the-implementation-bound-public-contract-is-frozen-before-the-shell-is-swapped",
    )
    def test_c2_delta_specs_match_the_frozen_list(self):
        """The C2 change's delta specs apply exactly the frozen C2 entries.

        Every entry in the frozen list whose ``applying_change`` is
        ``webclient-vue-08-wire-bridge-contracts`` must have its delta spec
        present under the change's ``specs/`` tree, re-expressing the frozen
        requirement by name; the ADDED ``webclient-vue-application`` spec
        (the bridge-façade requirement) is applied in the same change. Any C2
        capability missing a delta spec surfaces here (a C2 omission in the
        A1 net), and a delta spec for a C4 (or unknown) capability fails the
        exact-set assertion.
        """
        entries = self.delta_block[DELTA_LIST_KEY]
        c2_entries = [
            entry
            for entry in entries
            if entry["applying_change"] == "webclient-vue-08-wire-bridge-contracts"
        ]
        self.assertTrue(c2_entries, "the frozen list must carry C2 delta entries")
        change = "webclient-vue-08-wire-bridge-contracts"
        active_dir = REPO_ROOT / "openspec" / "changes" / change / "specs"
        if active_dir.is_dir():
            specs_dir = active_dir
        else:
            archive_root = REPO_ROOT / "openspec" / "changes" / "archive"
            archived = sorted(archive_root.glob(f"*-{change}"))
            self.assertTrue(
                archived,
                "the C2 change must exist either active or archived under openspec/changes",
            )
            self.assertEqual(
                len(archived),
                1,
                "exactly one dated archive directory may exist for the C2 change",
            )
            specs_dir = archived[0] / "specs"
        delta_files = sorted(path.parent.name for path in specs_dir.glob("*/spec.md"))
        self.assertEqual(
            delta_files,
            sorted({entry["capability"] for entry in c2_entries} | {"webclient-vue-application"}),
            "the C2 delta spec set must equal the frozen list's C2 capabilities plus the ADDED webclient-vue-application spec",
        )
        for entry in c2_entries:
            with self.subTest(delta_id=entry["delta_id"]):
                spec = specs_dir / entry["capability"] / "spec.md"
                source = spec.read_text(encoding="utf-8")
                self.assertIn(
                    f"### Requirement: {entry['requirement']}\n",
                    source,
                    f"C2 delta spec must re-express the frozen requirement {entry['requirement']}",
                )
