from __future__ import annotations

from _bootstrap import SRC_ROOT  # noqa: F401

import tempfile
import unittest
from pathlib import Path

from app.services.blk_editor import (
    BLKDocument,
    BLKEditor,
    BLKEditorError,
    BLKEntryType,
    BLKTextureEntry,
)


class BLKEmptySaveGuardTests(unittest.TestCase):
    def test_empty_save_is_rejected_and_original_file_is_untouched(self):
        original = 'name:t="user"\r\n\r\n'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.blk"
            path.write_bytes(original.encode("utf-8"))

            editor = BLKEditor()
            document = editor.load(path)
            self.assertEqual(document.entries, [])

            with self.assertRaises(BLKEditorError):
                editor.save_in_place(document)

            self.assertEqual(
                path.read_bytes().decode("utf-8"),
                original,
            )

    def test_first_rules_added_to_zero_rule_document_do_not_duplicate_name(self):
        original = 'name:t="user"\r\n\r\n'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.blk"
            path.write_bytes(original.encode("utf-8"))

            editor = BLKEditor()
            document = editor.load(path)
            document.entries = [
                BLKTextureEntry(
                    entry_type=BLKEntryType.REPLACE,
                    from_value="body_c*",
                    to_value="body_c",
                    has_param=True,
                    is_camo=False,
                ),
                BLKTextureEntry(
                    entry_type=BLKEntryType.REPLACE,
                    from_value="body_n*",
                    to_value="body_n",
                    has_param=True,
                    is_camo=False,
                ),
            ]

            editor.save_in_place(document)
            result = path.read_bytes().decode("utf-8")

            self.assertEqual(result.count('name:t="user"'), 1)
            self.assertEqual(result.count("replace_tex{"), 2)

    def test_rebuild_zero_rule_document_uses_single_text_segment_only_once(self):
        editor = BLKEditor()
        document = BLKDocument(
            path=Path("dummy.blk"),
            original_text='name:t="user"\r\n\r\n',
            name_value="user",
            entries=[
                BLKTextureEntry(
                    entry_type=BLKEntryType.REPLACE,
                    from_value="body_c*",
                    to_value="body_c",
                    has_param=True,
                    is_camo=False,
                )
            ],
            newline="\r\n",
            text_segments=['name:t="user"\r\n\r\n'],
        )

        result = editor._rebuild_document(document)

        self.assertEqual(result.count('name:t="user"'), 1)
        self.assertEqual(result.count("replace_tex{"), 1)


if __name__ == "__main__":
    unittest.main()
