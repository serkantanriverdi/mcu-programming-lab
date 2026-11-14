# SPDX-License-Identifier: MIT
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from check_release import inspect


class ReleaseTests(unittest.TestCase):
    def test_vendor_file_is_blocked_even_if_explicitly_added(self):
        self.assertTrue(inspect(Path("sdk/device.inc"), b"text"))
        self.assertTrue(inspect(Path("decoded/profile.txt"), b"text"))

    def test_executable_with_misleading_extension_is_blocked(self):
        self.assertTrue(inspect(Path("docs/data.txt"), b"MZ" + b"x" * 40))

    def test_credential_detection_does_not_require_a_real_credential(self):
        sample = b"ghp_" + b"x" * 36
        self.assertIn("possible credential", inspect(Path("notes.txt"), sample))

    def test_original_example_hex_is_allowed(self):
        self.assertEqual(inspect(Path("examples/ht66f002/blink.hex"), b":00000001FF\n"), [])


if __name__ == "__main__":
    unittest.main()
