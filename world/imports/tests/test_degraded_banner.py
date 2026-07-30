import io
from unittest import TestCase
from unittest.mock import patch

from world.imports.tests.helpers import EXAMPLE_PATH
from world.imports.validate import main, validate_batch


class DegradedBannerTests(TestCase):
    def test_banner_is_first_on_clean_degraded_run(self):
        output = io.StringIO()
        with patch("sys.stdout", output), patch(
            "world.imports.validate._resolve_skill_registry", return_value=None
        ):
            self.assertEqual(main([str(EXAMPLE_PATH)]), 0)
        text = output.getvalue()
        self.assertTrue(text.startswith("=" * 80))
        self.assertLess(text.index("skill-registry"), text.index("\nVALID "))

    def test_no_banner_or_degraded_check_when_registry_exists(self):
        with patch(
            "world.imports.validate._resolve_skill_registry",
            return_value={"body_enhancement": 1, "elf_longevity": 1},
        ):
            report = validate_batch([EXAMPLE_PATH])
        self.assertFalse(report.degraded_checks)
