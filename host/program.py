# SPDX-License-Identifier: MIT
"""Program or verify an HT66F002 image with the MCU Programming Lab Nano sketch.

The default image is the PA1/pin6 PWM dimmer image. Records a checkpoint,
requires successful erase, compares the entire Flash and option area, checks
EEPROM preservation and leaves the target running. It never writes EEPROM.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

import serial

from targets.ht66f002 import DEVICE, FIRMWARE_ID, option_high_byte

IDENTITY = FIRMWARE_ID
CODES = bytes(option_high_byte(i) for i in range(16))
ROOT = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path, default=ROOT / "examples/ht66f002/led_pa1_dimmer.json")
    p.add_argument("--port", required=True, help="Serial port of the Nano programmer")
    p.add_argument("--output", type=Path)
    p.add_argument("--verify-only", action="store_true")
    p.add_argument("--runtime-check", action="store_true", help="Require six PA0 edges; use with the supplied blink or dimmer image")
    a = p.parse_args()
    image = json.loads(a.image.read_text())
    if image.get("device") != DEVICE:
        p.error("Only the HT66F002 target profile is supported")
    expected = image["flash_words"]
    count = image["program_words"]
    if len(expected) != 1024 or not 4 <= count <= 1024 or count % 4:
        p.error("Expected 1024 Flash words and a page-aligned program size")
    if any(type(w) is not int or not 0 <= w <= 0x3fff for w in expected):
        p.error("Flash values must be 14-bit words")
    if any(expected[count:]):
        p.error("Image outside the programmed range must have zero fill")
    binary = b"".join(w.to_bytes(2, "little") for w in expected[:count])
    if hashlib.sha256(binary).hexdigest() != image["binary_sha256"]:
        p.error("Image digest does not match its Flash words")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = a.output or ROOT / f"records/program_ht66f002_{stamp}.json"
    record = dict(timestamp_utc=stamp, port=a.port, image=str(a.image.resolve()),
                  image_sha256=image["binary_sha256"], identity_expected=IDENTITY,
                  verify_only=a.verify_only, results=[], success=False,
                  voltage_note="Nano D4 commands VDD off/on; voltage not independently measured")

    def save():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, indent=2) + "\n")

    def receive(s, timeout):
        end = time.monotonic() + timeout
        buf = bytearray()
        while time.monotonic() < end:
            buf.extend(s.read(4096))
            if buf.endswith(b"\n"):
                return buf.decode("ascii").strip()
        raise RuntimeError(f"Serial response timeout: {buf[:80]!r}")

    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    def parsed_words(answer, ack):
        require(f"ACK={ack} " in answer and "WORDS=" in answer, "Read did not succeed")
        return [int(w, 16) for w in answer.split("WORDS=", 1)[1].split()]

    save()
    try:
        with serial.Serial(a.port, 115200, timeout=0.2, exclusive=True) as s:
            s.dtr = False
            time.sleep(0.1)
            s.reset_input_buffer()
            s.dtr = True
            time.sleep(2.5)
            record["boot"] = s.read(4096).decode("ascii", errors="replace").strip()
            s.write(b"v\n")
            record["identity"] = receive(s, 2)
            require(record["identity"] == IDENTITY, "Unexpected Nano sketch; no target command sent")

            def command(cmd):
                s.write((cmd + "\n").encode("ascii"))
                answer = receive(s, 10 if cmd == "m" else 3)
                record["results"].append(dict(command=cmd, response=answer))
                save()
                require(answer.startswith("TYPE6 "), f"Unexpected reply to {cmd}")
                return answer

            def read_flash():
                result = []
                for address in range(0, 1024, 64):
                    words = parsed_words(command(f"r 1 {address:x} 64"), "C3")
                    require(len(words) == 64, "Incomplete Flash read")
                    result.extend(words)
                return result

            def read_options():
                words = parsed_words(command("r 0 80000 32"), "C1")
                require(len(words) == 32, "Incomplete option read")
                return b"".join(w.to_bytes(2, "little") for w in words)

            def read_eeprom():
                answer = command("q 0 32 512")
                require("ACK=E3 DATA=" in answer, "EEPROM read failed")
                data = bytes.fromhex(answer.split("DATA=", 1)[1])
                require(len(data) == 32, "Incomplete EEPROM read")
                return data

            require(command("p icp") == "TYPE6 PROFILE HT66F002_ICP", "Profile selection failed")
            options = read_options()
            encoded = bytearray(64)
            encoded[1:32:2] = CODES
            encoded[32:] = options[32:]
            eeprom = read_eeprom()
            if not a.verify_only:
                require(options[:32] in (bytes(32), bytes(encoded[:32])),
                        "Unrecognized user options; stopped before erase")
                record["flash_checkpoint"] = read_flash()
                print("Checkpoint saved; programming Flash", flush=True)
                erased = command("e")
                require("STAGE=8 " in erased and "SENT=1 OPTIONS_MATCH=1 " in erased,
                        "Erase or preserved-option verification failed")
                for address in range(0, count, 4):
                    cmd = f"w {address:x} " + " ".join(f"{w:04x}" for w in expected[address:address + 4])
                    require("ACK=CF SENT" in command(cmd), f"Page write failed at {address:x}")
                initialized = command("o")
                require("STAGE=6 " in initialized and "SENT=1 MATCH=1 " in initialized,
                        "Option encoding initialization failed")
            actual = read_flash()
            require(actual == expected, "Flash readback differs from image")
            require(read_options() == encoded, "Option readback differs; trim must remain unchanged")
            require(read_eeprom() == eeprom, "EEPROM changed")
            record["flash_words_compared"] = 1024
            record["flash_mismatches"] = 0
            record["option_encoding_matches"] = True
            record["trim_preserved"] = True
            record["eeprom_preserved"] = True
            if a.runtime_check:
                runtime = command("m")
                require(re.search(r" EDGES=6 ", runtime), "Expected six PA0 runtime edges")
                record["runtime"] = runtime
            require(command("x") == "TYPE6 RUN VDD=ON CK=INPUT DA=INPUT", "Target start failed")
            record["success"] = True
            print(f"PASS: 1024 Flash words, options and EEPROM verified; target running. Record: {output}")
    except Exception as exc:
        record["error"] = str(exc)
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
