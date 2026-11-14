# SPDX-License-Identifier: MIT
"""Check the option encoding against a successful device readback digest."""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "host"))
from targets.ht66f002 import option_high_byte


class OptionEncodingTests(unittest.TestCase):
    def test_matches_observed_user_option_prefix(self):
        prefix = bytes(byte for i in range(16) for byte in (0, option_high_byte(i)))
        self.assertEqual(
            hashlib.sha256(prefix).hexdigest(),
            "31703d6e6b4855f97ab05a52b9d82c21ca1c2927d69a44ab47a3e62936dc74dd",
        )

    def test_rejects_indices_outside_user_options(self):
        for index in (-1, 16, 32):
            with self.subTest(index=index), self.assertRaises(ValueError):
                option_high_byte(index)


if __name__ == "__main__":
    unittest.main()
