# SPDX-License-Identifier: MIT
"""Rebuild original examples without a vendor SDK and check known code hashes."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class ImageTests(unittest.TestCase):
    def test_rebuild_examples_without_vendor_files(self):
        cases = [
            ("led_pa1", "blink", "f8cc815f78a9356bf3562f21a2545bdf1c8b373c346909157a8e22744530ebf5"),
            ("led_pa1_on", "steady", "46d25dc6127367e639e237f14798d2a0a1b3cc72fdfa0b3b12eb2f4b88a7a32b"),
            ("led_pa1_dimmer", "pwm", "b0aee3aa5345263dbaf1c3667514c95f559ad3852087a63b72d382f0eed17868"),
        ]
        with tempfile.TemporaryDirectory() as temp:
            for name, behavior, expected in cases:
                with self.subTest(example=name):
                    source = Path(temp) / (name + ".asm")
                    shutil.copy2(ROOT / "examples/ht66f002" / source.name, source)
                    subprocess.run([sys.executable, str(ROOT / "host/assemble.py"), str(source), "--check", behavior],
                                   cwd=temp, check=True, capture_output=True)
                    result = json.loads(source.with_suffix(".json").read_text())
                    self.assertEqual(hashlib.sha256(source.with_suffix(".bin").read_bytes()).hexdigest(), expected)
                    self.assertEqual(result["binary_sha256"], expected)
                    self.assertEqual(result["flash_words"], json.loads((ROOT / "examples/ht66f002" / (name + ".json")).read_text())["flash_words"])
                    if behavior == "pwm":
                        self.assertEqual(len(result["pwm_level_samples"]), 511)


if __name__ == "__main__":
    unittest.main()
