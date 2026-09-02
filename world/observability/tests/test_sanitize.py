"""Credential-free rendering of configured endpoint URLs for log contexts."""

import unittest

from world.observability.sanitize import safe_endpoint


class SafeEndpointTests(unittest.TestCase):
    def test_userinfo_and_port_survive_without_credentials(self) -> None:
        self.assertEqual(
            safe_endpoint("https://sd.internal:7860"), "https://sd.internal:7860"
        )

    def test_userinfo_password_is_stripped(self) -> None:
        self.assertEqual(
            safe_endpoint("https://user:password@sd.internal:7860/path"),
            "https://sd.internal:7860/path",
        )

    def test_query_and_fragment_credentials_are_dropped(self) -> None:
        self.assertEqual(
            safe_endpoint("http://h/?api_key=abc123#frag"), "http://h/"
        )

    def test_relative_configured_path_keeps_origin(self) -> None:
        self.assertEqual(
            safe_endpoint("http://127.0.0.1:11434/v1/chat/completions"),
            "http://127.0.0.1:11434/v1/chat/completions",
        )

    def test_unparseable_url_degrades_to_a_fixed_placeholder(self) -> None:
        self.assertEqual(safe_endpoint("http://[::1"), "[unparseable-url]")

    def test_non_string_values_are_stringified(self) -> None:
        self.assertEqual(safe_endpoint(None), "None")
