# MCU Programming Lab

Practical microcontroller programming tools using an Arduino Nano, with
documented MCU parameters, verified example programs and full Flash readback.

[Türkçe](README.tr.md) · [MCU parameters](docs/parameters.md) ·
[Wiring](docs/wiring.md) · [EEPROM](docs/eeprom.md) · [License notices](NOTICE.md)

**First bench-tested target: Holtek HT66F002, using an Arduino Nano.**
The project is designed to grow through separately verified target profiles.
Other Holtek chips, HT66F0021, HT66F0025, OTP parts and other manufacturers'
devices are not supported by this release.

This release was uploaded to a Nano and used to program the dimmer example.
All 1024 Flash words matched, options and EEPROM were preserved as specified,
and a fresh host/reset session confirmed readback and application execution.
See the recorded [validation scope](docs/validation.md).

## What works

- Read and erase the HT66F002's 1024 × 14-bit program words.
- Write four-word pages and compare the entire Flash image afterward.
- Preserve the option/trim region used by the tested erase sequence.
- Initialize the option-word encoding needed to run the application.
- Read 32 bytes of EEPROM and check that programming did not change it.
- Run PA1/pin 6 blink and PWM dimmer examples; observe a PA0 heartbeat.

EEPROM writing, analog oscillator calibration and a full C compiler are not
implemented. A programming ACK alone is never reported as a successful write.

## Hardware

The wiring below is for **HT66F002 SOP8**, viewed from above:

| Nano | MCU pin | Purpose |
|---|---|---|
| GND |8| VSS |
| D2 |4 / PA7| Programming clock |
| D3 |7 / PA0| Programming data / application heartbeat |
| D4 |1| Switched target supply |
| LED anode |6 / PA1| Application output |
| LED cathode →330Ω→GND |8| LED return |

Use this pinout only with the stated target. See [wiring and power
limitations](docs/wiring.md) before adapting the circuit to another board.

## Quick start

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
arduino-cli core install arduino:avr@1.8.8
arduino-cli compile --fqbn arduino:avr:nano --output-dir build/nano_programmer firmware/nano_programmer
arduino-cli upload --fqbn arduino:avr:nano:cpu=atmega328old --port YOUR_PORT --input-dir build/nano_programmer --verify firmware/nano_programmer
```

Replace `YOUR_PORT` with your Nano's serial port, such as `/dev/ttyUSB0`,
`/dev/cu.usbserial-...` or `COM3`. The tested Nano uses the old bootloader.
Its firmware identity is `MCULAB_HT66F002_V1`.

Generate the PWM dimmer image:

```sh
.venv/bin/python host/assemble.py examples/ht66f002/led_pa1_dimmer.asm --check pwm
```

Program it **only after checking the target model and wiring**:

```sh
.venv/bin/python host/program.py --port YOUR_PORT --image examples/ht66f002/led_pa1_dimmer.json --runtime-check
```

Programming erases the existing application. The host first records a
checkpoint under `records/`, requires the expected Nano identity, verifies
erase and options, compares all 1024 words, checks EEPROM preservation,
and finally leaves the target running. Checkpoints can contain your device's
private program/data; `records/` is excluded from Git.

To compare an already programmed chip without writing its memories:

```sh
.venv/bin/python host/program.py --port YOUR_PORT --image examples/ht66f002/led_pa1_dimmer.json --verify-only --runtime-check
```

Verification still power-cycles the target. `--runtime-check` expects the
PA0 signal produced by the blink/dimmer examples; omit it for other programs.

## Examples and tools

| Path | Purpose |
|---|---|
| `firmware/nano_programmer/` | Project-authored Nano adapter source |
| `host/program.py` | Checkpoint, program, verify and run |
| `host/assemble.py` | Limited assembler and instruction-level behavior check |
| `host/targets/ht66f002.py` | Minimal project-maintained target facts |
| `host/session.py` | Identity-checked low-level serial sessions |
| `examples/ht66f002/led_pa1.asm` | Blink; build with `--check blink` |
| `examples/ht66f002/led_pa1_dimmer.asm` | Automatic brightness sweep; build with `--check pwm` |
| `examples/ht66f002/led_pa1_on.asm` | Constant output; build with `--check steady` |
| `docs/parameters.md` | MCU capacities, addressing, options and supported operations |
| `docs/eeprom.md` | Read commands, persistence, preservation and current write support |
| `docs/protocol.md` | Implemented serial and target transactions |
| `docs/method.md` | Adding and validating another MCU profile |
| `validation/` | Sanitized results; no full device backups or vendor dumps |

The assembler emits little-endian program bytes, Intel HEX, a listing and
a JSON image used by the host. It supports only the instruction subset
needed by these examples. It is not a complete Holtek assembler/toolchain.

## Checks

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/check_release.py
```

The checks cover option encoding, known application images, destructive-operation
guards and the release's excluded file categories. They do not emulate the
electrical target. Hardware validation and its limits are described separately
in [validation](docs/validation.md).

## Rights and support

MIT covers this project's original code and documentation. No manufacturer
binary, SDK, manual PDF or logo is distributed here. No manufacturer software
is required to run the published example pipeline. References and third-party
notices are in [NOTICE.md](NOTICE.md).

Holtek and Arduino names identify third-party hardware. This project is
independent and is not sponsored, endorsed or approved by those companies.

Contributions should add a documented MCU profile with hardware validation.
See [CONTRIBUTING.md](CONTRIBUTING.md).
