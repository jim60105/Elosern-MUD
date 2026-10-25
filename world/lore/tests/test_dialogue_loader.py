"""Synthetic tests for authored dialogue YAML loader.

Covers:
- Safe direct-file scan and duplicate-key/tag/alias/document/path/UTF-8/size rejection.
- Stable sorted discovery order.
- Canonical profile/dialogue binding derivation and completeness.
- Invalid-neighbor all-or-nothing snapshot rejection.
- MappingProxyType read-only snapshot immutability.
- Equivalent YAML and JSON primitives validation parity.
"""

from dataclasses import FrozenInstanceError
import os
from pathlib import Path
import tempfile
import unittest

from world.lore.dialogue.codec import (
    StaticDialogueIdentity,
    dialogue_payload_schema,
    parse_dialogue,
)
from world.lore.dialogue.conditions import DialogueReferences
from world.lore.dialogue.loader import (
    MAX_DIALOGUE_FILE_BYTES,
    DialogueSourceError,
    load_dialogue_snapshot,
)
from world.lore.dialogue.shape import AuthoredDialogue

from tools.spec_traceability import covers_requirement


def _valid_dialogue_yaml(dialogue_key: str, *, greeting: str = "Welcome traveler.") -> str:
    """Return a minimal valid static dialogue YAML document."""
    return f"""schema_version: 1
greeting: {greeting}
topics:
  - topic_id: "{dialogue_key}.topic_01"
    keyword: "hello"
    label: "Say Hello"
    fallback:
      scene_id: "hello_scene"
      revision: "rev1"
      lines:
        - kind: "speech"
          speaker: "actor"
          text: "Hello there!"
        - kind: "speech"
          speaker: "host"
          text: "Greetings!"
"""


def _valid_dialogue_dict(dialogue_key: str, *, greeting: str = "Welcome traveler.") -> dict:
    """Return a minimal valid static dialogue payload dictionary."""
    return {
        "schema_version": 1,
        "greeting": greeting,
        "topics": [
            {
                "topic_id": f"{dialogue_key}.topic_01",
                "keyword": "hello",
                "label": "Say Hello",
                "fallback": {
                    "scene_id": "hello_scene",
                    "revision": "rev1",
                    "lines": [
                        {"kind": "speech", "speaker": "actor", "text": "Hello there!"},
                        {"kind": "speech", "speaker": "host", "text": "Greetings!"},
                    ],
                },
            }
        ],
    }


class DialogueLoaderTests(unittest.TestCase):
    """Test suite for load_dialogue_snapshot."""

    def setUp(self) -> None:
        self.references = DialogueReferences.empty()

    def test_missing_and_nondirectory_content_dir_rejected(self) -> None:
        """Missing path raises FileNotFoundError; non-directory raises NotADirectoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "nonexistent"
            with self.assertRaises(FileNotFoundError):
                load_dialogue_snapshot(
                    missing,
                    profiles=frozenset(),
                    bindings={},
                    references=self.references,
                )

            a_file = Path(tmpdir) / "not_a_dir.yaml"
            a_file.write_text("dummy", encoding="utf-8")
            with self.assertRaises(NotADirectoryError):
                load_dialogue_snapshot(
                    a_file,
                    profiles=frozenset(),
                    bindings={},
                    references=self.references,
                )

    @covers_requirement("authored-dialogue-sources::static-dialogue-discovery-derives-owner-from-profile-key-filename")
    def test_sorted_discovery_order(self) -> None:
        """Files are discovered and processed in stable filename order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create files in deliberately non-alphabetical order
            names = ["charlie_host", "alpha_host", "bravo_host"]
            profiles = frozenset(names)
            bindings = {f"{n}_diag": n for n in names}

            for name in ["bravo_host", "charlie_host", "alpha_host"]:
                (root / f"{name}.yaml").write_text(
                    _valid_dialogue_yaml(f"{name}_diag"), encoding="utf-8"
                )

            snapshot = load_dialogue_snapshot(
                root,
                profiles=profiles,
                bindings=bindings,
                references=self.references,
            )

            # Keys are returned in deterministic discovery order
            self.assertEqual(list(snapshot.keys()), ["alpha_host_diag", "bravo_host_diag", "charlie_host_diag"])
            self.assertEqual(set(snapshot.keys()), {"alpha_host_diag", "bravo_host_diag", "charlie_host_diag"})
            for k in snapshot:
                self.assertIsInstance(snapshot[k], AuthoredDialogue)

    @covers_requirement("authored-dialogue-sources::static-dialogue-discovery-derives-owner-from-profile-key-filename")
    def test_non_yaml_files_ignored(self) -> None:
        """Supporting files (e.g. .txt, .md, .json) in content_dir are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("Some notes", encoding="utf-8")
            (root / "metadata.json").write_text("{}", encoding="utf-8")
            (root / ".hidden").write_text("secret", encoding="utf-8")

            # One valid host
            (root / "test_host.yaml").write_text(
                _valid_dialogue_yaml("test_dialogue"), encoding="utf-8"
            )

            snapshot = load_dialogue_snapshot(
                root,
                profiles=frozenset(["test_host"]),
                bindings={"test_dialogue": "test_host"},
                references=self.references,
            )
            self.assertEqual(list(snapshot.keys()), ["test_dialogue"])

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_symlink_file_rejected(self) -> None:
        """A .yaml entry that is a symlink is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "real_file.txt"
            target.write_text(_valid_dialogue_yaml("link_diag"), encoding="utf-8")
            link = root / "link_host.yaml"
            try:
                os.symlink(target, link)
            except OSError:
                self.skipTest("Symlinks not supported on this filesystem")

            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["link_host"]),
                    bindings={"link_diag": "link_host"},
                    references=self.references,
                )
            self.assertIn("symlink", str(ctx.exception).lower())

    def test_yaml_directory_entry_rejected(self) -> None:
        """A directory ending with .yaml is rejected as non-regular file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subdir = root / "fake_host.yaml"
            subdir.mkdir()

            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["fake_host"]),
                    bindings={"fake_diag": "fake_host"},
                    references=self.references,
                )
            self.assertIn("not a regular file", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_file_size_limits(self) -> None:
        """File at exact 262144 bytes is accepted; 262145 bytes is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_content = _valid_dialogue_yaml("bound_diag")

            # Create file with exact size 262144 bytes by appending comments
            pad_len = MAX_DIALOGUE_FILE_BYTES - len(base_content.encode("utf-8"))
            exact_content = base_content + "#" * pad_len
            self.assertEqual(len(exact_content.encode("utf-8")), MAX_DIALOGUE_FILE_BYTES)

            (root / "bound_host.yaml").write_text(exact_content, encoding="utf-8")

            snapshot = load_dialogue_snapshot(
                root,
                profiles=frozenset(["bound_host"]),
                bindings={"bound_diag": "bound_host"},
                references=self.references,
            )
            self.assertIn("bound_diag", snapshot)

            # Now exceed by 1 byte
            over_content = exact_content + "x"
            (root / "bound_host.yaml").write_text(over_content, encoding="utf-8")

            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["bound_host"]),
                    bindings={"bound_diag": "bound_host"},
                    references=self.references,
                )
            self.assertIn("exceeds maximum", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_invalid_utf8_rejected(self) -> None:
        """Invalid UTF-8 byte sequences are rejected with an error naming the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bad_file = root / "utf8_host.yaml"
            bad_file.write_bytes(b"\xff\xfe\x00\x00 invalid utf8 bytes")

            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["utf8_host"]),
                    bindings={"utf8_diag": "utf8_host"},
                    references=self.references,
                )
            self.assertIn("utf8_host.yaml", str(ctx.exception))
            self.assertIn("not valid utf-8", str(ctx.exception).lower())

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_duplicate_mapping_keys_rejected(self) -> None:
        """Duplicate mapping keys at root or nested levels are strictly rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Root duplicate key
            dup_root = """schema_version: 1
greeting: "hi"
greeting: "duplicate"
topics: []
"""
            (root / "dup_host.yaml").write_text(dup_root, encoding="utf-8")
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["dup_host"]),
                    bindings={"dup_diag": "dup_host"},
                    references=self.references,
                )
            self.assertIn("duplicate mapping key", str(ctx.exception).lower())

            # Nested duplicate key inside topics
            dup_nested = """schema_version: 1
greeting: "hi"
topics:
  - topic_id: "dup_diag.topic_01"
    keyword: "k1"
    keyword: "k2"
    label: "L"
    fallback:
      scene_id: "s1"
      revision: "r1"
      lines:
        - kind: "speech"
          speaker: "actor"
          text: "hi"
"""
            (root / "dup_host.yaml").write_text(dup_nested, encoding="utf-8")
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["dup_host"]),
                    bindings={"dup_diag": "dup_host"},
                    references=self.references,
                )
            self.assertIn("duplicate mapping key", str(ctx.exception).lower())

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_yaml_aliases_and_anchors_rejected(self) -> None:
        """YAML anchors (&) and aliases (*) are strictly rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with_anchor = """schema_version: 1
greeting: &greet "Hello"
topics: []
"""
            (root / "anc_host.yaml").write_text(with_anchor, encoding="utf-8")
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["anc_host"]),
                    bindings={"anc_diag": "anc_host"},
                    references=self.references,
                )
            self.assertIn("yaml anchors are forbidden", str(ctx.exception).lower())

            with_alias = """schema_version: 1
greeting: "Hi"
topics:
  - *missing_anchor
"""
            (root / "anc_host.yaml").write_text(with_alias, encoding="utf-8")
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["anc_host"]),
                    bindings={"anc_diag": "anc_host"},
                    references=self.references,
                )
            self.assertIn("yaml aliases are forbidden", str(ctx.exception).lower())

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_yaml_merge_keys_rejected(self) -> None:
        """YAML merge keys (<<) are strictly rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with_merge = """schema_version: 1
<<: {greeting: "hi"}
topics: []
"""
            (root / "merge_host.yaml").write_text(with_merge, encoding="utf-8")
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["merge_host"]),
                    bindings={"merge_diag": "merge_host"},
                    references=self.references,
                )
            self.assertIn("yaml merge keys", str(ctx.exception).lower())

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_unsafe_tags_rejected(self) -> None:
        """Custom and object-construction YAML tags are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with_tag = """schema_version: 1
greeting: !custom "hello"
topics: []
"""
            (root / "tag_host.yaml").write_text(with_tag, encoding="utf-8")
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["tag_host"]),
                    bindings={"tag_diag": "tag_host"},
                    references=self.references,
                )
            self.assertIn("could not determine a constructor", str(ctx.exception).lower())

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_multi_document_stream_rejected(self) -> None:
        """YAML files containing multiple documents are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            multi_doc = f"""{_valid_dialogue_yaml("doc1_diag")}
---
schema_version: 1
greeting: "Doc 2"
topics: []
"""
            (root / "doc_host.yaml").write_text(multi_doc, encoding="utf-8")
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["doc_host"]),
                    bindings={"doc1_diag": "doc_host"},
                    references=self.references,
                )
            self.assertIn("expected a single document", str(ctx.exception).lower())

    @covers_requirement("authored-dialogue-sources::static-dialogue-discovery-derives-owner-from-profile-key-filename")
    def test_filename_stem_not_in_registered_profiles_rejected(self) -> None:
        """Discovered file whose stem is not a registered NpcProfile.key rejects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "unregistered_npc.yaml").write_text(
                _valid_dialogue_yaml("some_diag"), encoding="utf-8"
            )

            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["registered_npc"]),
                    bindings={"some_diag": "registered_npc"},
                    references=self.references,
                )
            self.assertIn("unregistered_npc.yaml", str(ctx.exception))
            self.assertIn("not a registered profile key", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::static-dialogue-discovery-derives-owner-from-profile-key-filename")
    def test_filename_using_dialogue_key_or_display_name_rejected(self) -> None:
        """Filename using dialogue alias instead of profile key rejects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Suppose profile is fixture_profile, dialogue_key alias is fixture_alias
            (root / "fixture_alias.yaml").write_text(
                _valid_dialogue_yaml("fixture_alias"), encoding="utf-8"
            )

            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["fixture_profile"]),
                    bindings={"fixture_alias": "fixture_profile"},
                    references=self.references,
                )
            self.assertIn("not a registered profile key", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_orphan_binding_without_file_rejected(self) -> None:
        """A canonical binding without a corresponding discovered file rejects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # No files created
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["missing_host"]),
                    bindings={"missing_diag": "missing_host"},
                    references=self.references,
                )
            self.assertIn("missing_diag", str(ctx.exception))
            self.assertIn("has no discovered file", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_discovered_file_without_binding_rejected(self) -> None:
        """A discovered file whose profile has no binding rejects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "unbound_host.yaml").write_text(
                _valid_dialogue_yaml("unbound_diag"), encoding="utf-8"
            )

            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["unbound_host"]),
                    bindings={},
                    references=self.references,
                )
            self.assertIn("no canonical dialogue binding", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_binding_mapping_to_unregistered_profile_rejected(self) -> None:
        """A binding mapping to a profile not in registered profiles is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "known_profile.yaml").write_text(
                _valid_dialogue_yaml("some_diag"), encoding="utf-8"
            )
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["known_profile"]),
                    bindings={"some_diag": "unknown_profile"},
                    references=self.references,
                )
            self.assertIn("unknown profile 'unknown_profile'", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_duplicate_canonical_bindings_rejected(self) -> None:
        """Two dialogue keys bound to the same profile key reject."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bindings = {
                "diag_a": "shared_profile",
                "diag_b": "shared_profile",
            }
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["shared_profile"]),
                    bindings=bindings,
                    references=self.references,
                )
            self.assertIn("duplicate canonical binding", str(ctx.exception).lower())

    @covers_requirement("authored-dialogue-sources::static-dialogue-discovery-derives-owner-from-profile-key-filename")
    def test_forbidden_explicit_owner_field_rejected(self) -> None:
        """Explicit owner fields in YAML root (npc_id, profile_key, owner) are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for forbidden_field in ("npc_id", "profile_key", "owner", "dialogue_key"):
                content = f"""schema_version: 1
{forbidden_field}: "some_owner"
greeting: "hello"
topics: []
"""
                (root / "owner_host.yaml").write_text(content, encoding="utf-8")
                with self.assertRaises(DialogueSourceError) as ctx:
                    load_dialogue_snapshot(
                        root,
                        profiles=frozenset(["owner_host"]),
                        bindings={"owner_diag": "owner_host"},
                        references=self.references,
                    )
                self.assertIn("forbidden explicit owner field", str(ctx.exception))

    def test_schema_version_type_strictness(self) -> None:
        """schema_version must be exact int 1; bool or float rejects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for bad_ver in ("true", "1.0", "yes"):
                content = f"""schema_version: {bad_ver}
greeting: "hello"
topics: []
"""
                (root / "ver_host.yaml").write_text(content, encoding="utf-8")
                with self.assertRaises(DialogueSourceError) as ctx:
                    load_dialogue_snapshot(
                        root,
                        profiles=frozenset(["ver_host"]),
                        bindings={"ver_diag": "ver_host"},
                        references=self.references,
                    )
                self.assertIn("schema_version must be integer 1", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_all_or_nothing_snapshot_rejection(self) -> None:
        """One invalid neighbor rejects the entire load atomically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create 3 valid files
            valid_names = ["host_1", "host_2", "host_3"]
            for name in valid_names:
                (root / f"{name}.yaml").write_text(
                    _valid_dialogue_yaml(f"{name}_diag"), encoding="utf-8"
                )

            # Create 1 invalid file (broken schema: invalid topic_id format)
            invalid_content = """schema_version: 1
greeting: "hi"
topics:
  - topic_id: "INVALID_TOPIC_CAPS"
    keyword: "hello"
    label: "Hello"
    fallback:
      scene_id: "scene1"
      revision: "rev1"
      lines:
        - kind: "speech"
          speaker: "actor"
          text: "hello"
"""
            (root / "host_bad.yaml").write_text(invalid_content, encoding="utf-8")

            all_names = [*valid_names, "host_bad"]
            bindings = {f"{n}_diag": n for n in all_names}
            profiles = frozenset(all_names)

            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=profiles,
                    bindings=bindings,
                    references=self.references,
                )
            self.assertIn("host_bad.yaml", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_snapshot_immutability(self) -> None:
        """Returned snapshot is a MappingProxyType and cannot be mutated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "immut_host.yaml").write_text(
                _valid_dialogue_yaml("immut_diag"), encoding="utf-8"
            )

            snapshot = load_dialogue_snapshot(
                root,
                profiles=frozenset(["immut_host"]),
                bindings={"immut_diag": "immut_host"},
                references=self.references,
            )

            with self.assertRaises(TypeError):
                snapshot["new_key"] = None  # type: ignore[index]

            with self.assertRaises(TypeError):
                del snapshot["immut_diag"]  # type: ignore[arg-type]

            dialogue = snapshot["immut_diag"]
            with self.assertRaises(FrozenInstanceError):
                dialogue.greeting = "Mutated"  # type: ignore[misc]

            # Nested tuple mutation is forbidden
            self.assertIsInstance(dialogue.topics, tuple)
            with self.assertRaises(AttributeError):
                dialogue.topics.append(None)  # type: ignore[attr-defined]

            # Multiple calls produce independent snapshots with no cross-call mutation or caching
            snapshot_two = load_dialogue_snapshot(
                root,
                profiles=frozenset(["immut_host"]),
                bindings={"immut_diag": "immut_host"},
                references=self.references,
            )
            self.assertIsNot(snapshot, snapshot_two)
            self.assertEqual(snapshot, snapshot_two)

    def test_unregistered_profile_with_no_file_and_no_binding_is_accepted(self) -> None:
        """Profiles that ship no dialogue table are not bindings and need no file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "active_host.yaml").write_text(
                _valid_dialogue_yaml("active_diag"), encoding="utf-8"
            )

            # silent_profile is in profiles, but has no binding and no file
            snapshot = load_dialogue_snapshot(
                root,
                profiles=frozenset(["active_host", "silent_profile"]),
                bindings={"active_diag": "active_host"},
                references=self.references,
            )
            self.assertEqual(list(snapshot.keys()), ["active_diag"])

    @covers_requirement("authored-dialogue-sources::static-dialogue-discovery-derives-owner-from-profile-key-filename")
    def test_distinct_service_alias_and_profile_key_distinction(self) -> None:
        """Binding with distinct dialogue alias (e.g. service key) maps to profile key file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Profile is fixture_master, bound to dialogue_key fixture_staff
            (root / "fixture_master.yaml").write_text(
                _valid_dialogue_yaml("fixture_staff"), encoding="utf-8"
            )

            snapshot = load_dialogue_snapshot(
                root,
                profiles=frozenset(["fixture_master"]),
                bindings={"fixture_staff": "fixture_master"},
                references=self.references,
            )
            self.assertIn("fixture_staff", snapshot)
            self.assertNotIn("fixture_master", snapshot)
            self.assertEqual(snapshot["fixture_staff"].topics[0].topic_id, "fixture_staff.topic_01")

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_unknown_condition_reference_rejects(self) -> None:
        """A dialogue condition referencing an unknown key against DialogueReferences rejects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # File with a condition referencing unknown race
            content = """schema_version: 1
greeting: "Greetings"
topics:
  - topic_id: "ref_diag.topic_01"
    keyword: "secret"
    label: "Secret Talk"
    requires:
      kind: "race_is"
      race_key: "unknown_race"
    fallback:
      scene_id: "secret_scene"
      revision: "rev1"
      lines:
        - kind: "speech"
          speaker: "actor"
          text: "Tell me secrets."
        - kind: "speech"
          speaker: "host"
          text: "Only to elves."
"""
            (root / "ref_host.yaml").write_text(content, encoding="utf-8")
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["ref_host"]),
                    bindings={"ref_diag": "ref_host"},
                    references=DialogueReferences.empty(),
                )
            self.assertIn("ref_host.yaml", str(ctx.exception))
            self.assertIn("unknown_race", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_catalog_backed_reference_publishes_and_unknown_key_names_its_identity(self):
        """A real catalog key publishes; an unlisted one rejects naming profile and dialog."""
        references = DialogueReferences.empty().child(
            "race", {"t_known_race": "合成種族"}
        )
        topic = """topics:
  - topic_id: "{key}.topic_01"
    keyword: "who"
    label: "Who"
    requires:
      kind: "race_is"
      race_key: "{race}"
    fallback:
      scene_id: "who_scene"
      revision: "rev1"
      lines:
        - kind: "speech"
          speaker: "actor"
          text: "Who goes there?"
        - kind: "speech"
          speaker: "host"
          text: "A traveler."
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "catalog_host.yaml").write_text(
                'schema_version: 1\ngreeting: "Hello"\n'
                + topic.format(key="catalog_diag", race="t_known_race"),
                encoding="utf-8",
            )
            snapshot = load_dialogue_snapshot(
                root,
                profiles=frozenset(["catalog_host"]),
                bindings={"catalog_diag": "catalog_host"},
                references=references,
            )
            self.assertEqual(
                snapshot["catalog_diag"].topics[0].requires.race_key, "t_known_race"
            )

            (root / "catalog_host.yaml").write_text(
                'schema_version: 1\ngreeting: "Hello"\n'
                + topic.format(key="catalog_diag", race="t_unlisted_race"),
                encoding="utf-8",
            )
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["catalog_host"]),
                    bindings={"catalog_diag": "catalog_host"},
                    references=references,
                )
            self.assertEqual(ctx.exception.profile_key, "catalog_host")
            self.assertEqual(ctx.exception.dialogue_key, "catalog_diag")
            self.assertIn("t_unlisted_race", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_out_of_range_exposure_bound_rejects_before_publication(self):
        """An exposure ordinal outside the canonical vocabulary rejects the candidate."""
        from world.lore.sexual_vocab import EXPOSURE_LEVELS

        content = f"""schema_version: 1
greeting: "Hello"
topics:
  - topic_id: "bound_diag.topic_01"
    keyword: "dress"
    label: "Dress"
    fallback:
      scene_id: "dress_scene"
      revision: "rev1"
      lines:
        - kind: "speech"
          speaker: "actor"
          text: "How does this look?"
        - kind: "speech"
          speaker: "host"
          text: "Boldly."
    variants:
      - variant_id: "out_of_range"
        priority: 10
        when:
          kind: "exposure"
          minimum: {len(EXPOSURE_LEVELS)}
        scene:
          scene_id: "dress_variant_scene"
          revision: "rev1"
          lines:
            - kind: "speech"
              speaker: "actor"
              text: "Well?"
            - kind: "speech"
              speaker: "host"
              text: "Very."
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "bound_host.yaml").write_text(content, encoding="utf-8")
            with self.assertRaises(DialogueSourceError) as ctx:
                load_dialogue_snapshot(
                    root,
                    profiles=frozenset(["bound_host"]),
                    bindings={"bound_diag": "bound_host"},
                    references=DialogueReferences.empty(),
                )
            self.assertEqual(ctx.exception.profile_key, "bound_host")
            self.assertIn("EXPOSURE_LEVELS", str(ctx.exception))

    @covers_requirement("authored-dialogue-sources::static-dialogue-discovery-derives-owner-from-profile-key-filename")
    def test_new_valid_registered_profile_discovered_with_no_file_index_edit(self) -> None:
        """Adding a new file for a new registered profile & binding succeeds dynamically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "new_npc.yaml").write_text(
                _valid_dialogue_yaml("new_diag"), encoding="utf-8"
            )
            snapshot = load_dialogue_snapshot(
                root,
                profiles=frozenset(["new_npc"]),
                bindings={"new_diag": "new_npc"},
                references=self.references,
            )
            self.assertIn("new_diag", snapshot)

    @covers_requirement("authored-dialogue-sources::unsafe-or-invalid-content-rejects-the-whole-candidate-snapshot")
    def test_yaml_and_json_primitives_validation_parity(self) -> None:
        """Equivalent primitives from YAML and direct JSON-dict produce identical AuthoredDialogue."""
        diag_key = "parity_diag"
        yaml_text = _valid_dialogue_yaml(diag_key, greeting="Shared greeting")
        json_dict = _valid_dialogue_dict(diag_key, greeting="Shared greeting")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "parity_host.yaml").write_text(yaml_text, encoding="utf-8")

            snapshot = load_dialogue_snapshot(
                root,
                profiles=frozenset(["parity_host"]),
                bindings={diag_key: "parity_host"},
                references=self.references,
            )
            yaml_result = snapshot[diag_key]

        json_result = parse_dialogue(
            json_dict,
            identity=StaticDialogueIdentity(profile_key="parity_host", dialogue_key=diag_key),
            references=self.references,
        )

        self.assertEqual(yaml_result, json_result)
