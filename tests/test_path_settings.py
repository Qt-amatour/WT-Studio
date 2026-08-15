from __future__ import annotations

from _bootstrap import SRC_ROOT  # noqa: F401

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.path_settings import PathSettings


class PathSettingsSessionTests(unittest.TestCase):
    def tearDown(self):
        PathSettings._session_working_directory = None
        PathSettings._session_output_directory = None
        PathSettings._session_output_explicit = False

    def test_clean_session_starts_from_user_skins(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            with patch.object(
                PathSettings,
                "user_skins_path",
                return_value=base,
            ):
                PathSettings.reset_session_paths()

            self.assertEqual(
                PathSettings.session_working_directory(),
                base,
            )
            self.assertEqual(
                PathSettings.session_output_directory(),
                base,
            )

    def test_working_directory_drives_output_until_export_is_chosen(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            base = Path(first)
            working = Path(second)

            with patch.object(
                PathSettings,
                "user_skins_path",
                return_value=base,
            ):
                PathSettings.reset_session_paths()

            PathSettings.set_session_working_directory(working)

            self.assertEqual(
                PathSettings.session_working_directory(),
                working.resolve(),
            )
            self.assertEqual(
                PathSettings.session_output_directory(),
                working.resolve(),
            )

    def test_explicit_output_stays_independent_for_current_session(self):
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
            tempfile.TemporaryDirectory() as third,
        ):
            base = Path(first)
            output = Path(second)
            later_working = Path(third)

            with patch.object(
                PathSettings,
                "user_skins_path",
                return_value=base,
            ):
                PathSettings.reset_session_paths()

            PathSettings.set_session_output_directory(output)
            PathSettings.set_session_working_directory(later_working)

            self.assertEqual(
                PathSettings.session_working_directory(),
                later_working.resolve(),
            )
            self.assertEqual(
                PathSettings.session_output_directory(),
                output.resolve(),
            )

    def test_reset_for_new_clean_session_forgets_previous_output(self):
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            base = Path(first)
            previous_output = Path(second)

            with patch.object(
                PathSettings,
                "user_skins_path",
                return_value=base,
            ):
                PathSettings.reset_session_paths()
                PathSettings.set_session_output_directory(previous_output)
                PathSettings.reset_session_paths()

            self.assertEqual(
                PathSettings.session_output_directory(),
                base,
            )


if __name__ == "__main__":
    unittest.main()
