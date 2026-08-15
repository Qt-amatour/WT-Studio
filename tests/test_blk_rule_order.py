from __future__ import annotations

from _bootstrap import SRC_ROOT  # noqa: F401

import tempfile
import unittest
from pathlib import Path

from app.services.blk_editor import BLKEditor


class BLKRuleOrderTests(unittest.TestCase):
    def test_regular_rule_order_is_preserved_on_save(self):
        source = (
            'name:t="user"\r\n\r\n'
            'replace_tex{\r\n'
            '  from:t="first_c*"\r\n'
            '  to:t="first_c.dds"\r\n'
            '  param:t="camo_skin_tex"\r\n'
            '}\r\n\r\n'
            'replace_tex{\r\n'
            '  from:t="second_n*"\r\n'
            '  to:t="second_n.dds"\r\n'
            '  param:t="camo_skin_tex"\r\n'
            '}\r\n'
        )

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'order.blk'
            path.write_bytes(source.encode('utf-8'))

            editor = BLKEditor()
            document = editor.load(path)
            document.entries[0], document.entries[1] = (
                document.entries[1],
                document.entries[0],
            )

            editor.save_in_place(document)
            result = path.read_bytes().decode('utf-8')

            self.assertLess(
                result.index('second_n*'),
                result.index('first_c*'),
            )


if __name__ == '__main__':
    unittest.main()
