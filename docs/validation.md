# Validation scope

The public `MCULAB_HT66F002_V1` sketch was compiled, uploaded to an Arduino
Nano with upload verification, and used to program an HT66F002 SOP8.

The PWM dimmer run passed the full 1024-word Flash comparison, option
readback, preservation of the upper option/trim bytes, EEPROM preservation
and six PA0 application edges. A separate host session reset the Nano,
read the target again without writing its memories, and passed the same
comparisons and execution check. Each target read includes a commanded
power cycle. The target was left running the dimmer.

Sanitized results are in [hardware.json](../validation/hardware.json).
[Checks and build information](../validation/checks.json) records the
source-code tests and Nano memory usage. Full device backups remain local.

## Application images

| Example | Program words | SHA-256 of program bytes |
|---|---|---|
| Blink |80| `f8cc815f78a9356bf3562f21a2545bdf1c8b373c346909157a8e22744530ebf5` |
| PWM dimmer |96| `b0aee3aa5345263dbaf1c3667514c95f559ad3852087a63b72d382f0eed17868` |
| Constant output |48| `46d25dc6127367e639e237f14798d2a0a1b3cc72fdfa0b3b12eb2f4b88a7a32b` |

Blink and dimmer applications have run on physical HT66F002 devices.
This exact release was tested with the dimmer. Constant output was checked
in software. The dimmer behavior check executes a full 511-level up/down
sweep through the generated machine words and checks endpoints and monotonic
on-time progression. It uses a separate instruction decoder.

## EEPROM

A separate read-only check confirmed known EEPROM test bytes across three
adapter reset sessions, using full and individual-byte reads. Both tested
dummy-clock counts produced the same data. This validates the read path and
persistence of those bytes; the release does not implement EEPROM writing.
See [EEPROM usage and limits](eeprom.md).

## Measurement limits

The heartbeat is sampled by Nano digital input. It is not a calibrated
logic-analyzer or oscilloscope measurement. Commanded D4 power transitions
are not independent voltage measurements. The LED resistor value used on
the physical bench was not independently measured.

Oscillator recalibration, voltage/temperature timing margins, arbitrary
nonzero option combinations and production endurance have not been
characterized. No additional supported devices are implied.
