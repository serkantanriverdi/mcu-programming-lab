# SPDX-License-Identifier: MIT
"""Exercise failure paths before a destructive target command is allowed."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "host"))
import program


class FakeSerial:
    def __init__(self, identity=program.IDENTITY, options=None, incomplete_flash=False):
        self.identity = identity
        self.options = options or [0] * 32
        self.incomplete_flash = incomplete_flash
        self.commands = []
        self.pending = b""
        self._dtr = False

    def __enter__(self): return self
    def __exit__(self, *args): return False
    @property
    def dtr(self): return self._dtr
    @dtr.setter
    def dtr(self, value):
        self._dtr = value
        if value: self.pending = (self.identity + "\n").encode()
    def reset_input_buffer(self): self.pending = b""
    def read(self, count):
        result, self.pending = self.pending, b""
        return result
    def write(self, data):
        command = data.decode().strip()
        self.commands.append(command)
        if command == "v": result = self.identity
        elif command == "p icp": result = "TYPE6 PROFILE HT66F002_ICP"
        elif command == "r 0 80000 32":
            result = "TYPE6 MODE=0 ACK=C1 WORDS=" + " ".join(f"{w:04X}" for w in self.options)
        elif command == "q 0 32 512": result = "TYPE6 EEPROM ACK=E3 DATA=" + "FF " * 32
        elif command.startswith("r 1 ") and self.incomplete_flash:
            result = "TYPE6 MODE=1 ACK=C3 WORDS=" + "0000 " * 63
        else: raise AssertionError("Unexpected target command: " + command)
        self.pending = (result + "\n").encode()


class GuardTests(unittest.TestCase):
    def invoke(self, image, board, extra=()):
        with tempfile.TemporaryDirectory() as temp:
            image_path = Path(temp) / "image.json"
            image_path.write_text(json.dumps(image))
            argv = ["program.py", "--port", "TEST_ONLY", "--image", str(image_path),
                    "--output", str(Path(temp) / "record.json"), *extra]
            with patch.object(sys, "argv", argv), patch.object(program.serial, "Serial", return_value=board) as serial_mock, patch.object(program.time, "sleep"), contextlib.redirect_stderr(io.StringIO()):
                try: program.main()
                finally: self.serial_calls = serial_mock.call_count

    def setUp(self):
        self.image = json.loads((ROOT / "examples/ht66f002/led_pa1_dimmer.json").read_text())

    def test_wrong_device_rejected_before_serial_open(self):
        self.image["device"] = "HT66F0021"
        with self.assertRaises(SystemExit): self.invoke(self.image, FakeSerial())
        self.assertEqual(self.serial_calls, 0)

    def test_bad_word_rejected_before_serial_open(self):
        self.image["flash_words"][0] = 0x4000
        with self.assertRaises(SystemExit): self.invoke(self.image, FakeSerial())
        self.assertEqual(self.serial_calls, 0)

    def test_bad_digest_rejected_before_serial_open(self):
        self.image["flash_words"][0] ^= 1
        with self.assertRaises(SystemExit): self.invoke(self.image, FakeSerial())
        self.assertEqual(self.serial_calls, 0)

    def test_wrong_nano_identity_sends_no_target_command(self):
        board = FakeSerial(identity="UNRELATED_SKETCH")
        with self.assertRaisesRegex(RuntimeError, "Unexpected Nano sketch"): self.invoke(self.image, board)
        self.assertEqual(board.commands, ["v"])

    def test_unknown_user_options_stop_before_erase(self):
        board = FakeSerial(options=[1] + [0] * 31)
        with self.assertRaisesRegex(RuntimeError, "Unrecognized user options"): self.invoke(self.image, board)
        self.assertEqual(board.commands, ["v", "p icp", "r 0 80000 32", "q 0 32 512"])

    def test_incomplete_flash_read_is_not_verification_success(self):
        board = FakeSerial(incomplete_flash=True)
        with self.assertRaisesRegex(RuntimeError, "Incomplete Flash read"): self.invoke(self.image, board, ["--verify-only"])
        self.assertFalse(any(c == "e" or c == "o" or c.startswith("w ") for c in board.commands))


if __name__ == "__main__":
    unittest.main()
