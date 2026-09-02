"""Pure rendering tests for the observability facade line format."""

import unittest

from world.observability.render import format_exception_chain, render_context, render_line


def _raise_inner() -> Exception:
    try:
        raise ValueError("bad token")
    except ValueError as inner:
        try:
            raise RuntimeError("outer failed") from inner
        except RuntimeError as outer:
            return outer


class RenderContextTests(unittest.TestCase):
    def test_keys_sorted_values_formatted(self) -> None:
        text = render_context({"z": 1, "a": "plain", "m": True})
        self.assertEqual(text, "a=plain m=True z=1")

    def test_strings_with_spaces_are_quoted(self) -> None:
        self.assertEqual(render_context({"k": "two words"}), 'k="two words"')

    def test_none_keys_and_values_omitted(self) -> None:
        self.assertEqual(render_context({"a": None, "b": 2}), "b=2")

    def test_containers_repr_truncated_to_200(self) -> None:
        big = {"k": list(range(100))}
        rendered = render_context(big)
        value = rendered.removeprefix("k=")
        self.assertEqual(len(value), 200)
        self.assertTrue(repr(list(range(100))).startswith(value))

    def test_float_verbatim(self) -> None:
        self.assertEqual(render_context({"f": 1.5}), "f=1.5")

    def test_broken_value_degrades_without_raising(self) -> None:
        class Broken:
            def __repr__(self) -> str:
                raise RuntimeError("no repr")

        self.assertEqual(render_context({"k": Broken()}), "k=<unrenderable>")

    def test_repr_with_newlines_stays_single_line(self) -> None:
        class Snake:
            def __repr__(self) -> str:
                return "first\nsecond\r\nthird"

        text = render_context({"k": Snake()})
        self.assertNotIn("\n", text)
        self.assertNotIn("\r", text)
        self.assertIn("\\n", text)


class FormatChainTests(unittest.TestCase):
    def test_chain_outermost_first_with_cause(self) -> None:
        outer = _raise_inner()
        text = format_exception_chain(outer)
        parts = text.split(" <- ")
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[0].startswith("RuntimeError: outer failed @ "))
        self.assertTrue(parts[1].startswith("ValueError: bad token @ "))

    def test_bare_exception_single_link(self) -> None:
        try:
            raise KeyError("miss")
        except KeyError as exc:
            text = format_exception_chain(exc)
        self.assertTrue(text.startswith("KeyError: 'miss' @ "))
        self.assertNotIn(" <- ", text)


class RenderLineTests(unittest.TestCase):
    def test_line_shape_and_single_line(self) -> None:
        line = render_line(
            "warn", "startup\ndegraded", "mod.func:7", {"room": 3}, "A: x @ f:1"
        )
        self.assertEqual(line, '[warn] startup\\ndegraded | mod.func:7 | room=3 | tb: A: x @ f:1')

    def test_absent_segments_omitted(self) -> None:
        self.assertEqual(render_line("info", "evt", "m.f:1", None, None), "[info] evt | m.f:1")


if __name__ == "__main__":
    unittest.main()
