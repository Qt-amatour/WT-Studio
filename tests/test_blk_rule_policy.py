from __future__ import annotations

from _bootstrap import SRC_ROOT  # noqa: F401

import unittest

from app.services.blk_editor import requires_replace_texture_rule


class BLKRulePolicyTests(unittest.TestCase):
    def test_normal_and_ao_names_require_replace(self):
        for value in (
            "vehicle_body_n",
            "vehicle_body_n*",
            "vehicle_body_n.dds",
            "vehicle_body_n.dds*",
            "VEHICLE_BODY_N.TGA*",
            "vehicle_body_ao",
            "vehicle_body_ao*",
            "vehicle_body_ao.dds",
            "vehicle_body_ao.dds*",
            "VEHICLE_BODY_AO.TGA*",
        ):
            with self.subTest(value=value):
                self.assertTrue(requires_replace_texture_rule(value))

    def test_other_names_do_not_force_replace(self):
        for value in (
            "vehicle_body_c*",
            "vehicle_normal_detail*",
            "vehicle_n_damage*",
            "vehicle_ao_damage*",
            "vehicle_body_ambient*",
            "",
        ):
            with self.subTest(value=value):
                self.assertFalse(requires_replace_texture_rule(value))


if __name__ == "__main__":
    unittest.main()
