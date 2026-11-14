# Adding another MCU profile

A supported target needs a complete parameter set, an implementation and
hardware validation. Start with [the existing MCU parameters](parameters.md)
and the manufacturer's current documentation for the exact new part.

## Define the target

Record the full model and package, programming pinout, supply and signal
limits, reset/power requirements, Flash word count and width, page size,
EEPROM/RAM capacities, option regions and calibration preservation rules.
Similar model names do not establish compatibility.

Separate MCU properties from adapter settings. A capacity is a property of
the target; a Nano GPIO number or programmer's internal dispatch number is
an implementation choice. Record wire addresses and their units explicitly:
word addresses, byte addresses and control addresses are different concepts.

## Implement the profile

Keep target facts in a small, project-maintained module under the host's
target directory. Implement the required entry sequence, bit order, data
direction, group size, extra clocks, waits, erase preparation and option
preservation in the adapter. The existing sketch is specific to HT66F002;
changing only the device name does not add another target.

Require the correct adapter identity and select the target explicitly.
Validate image width, size, page alignment and digest before opening the port.
Read and save program, options, calibration state and EEPROM before changing
memories. Keep device backups local.

## Validate it on hardware

1. Read critical areas repeatedly and compare the results.
2. Verify the erase preparation and the regions it must preserve.
3. Write a known program; compare the entire Flash, including unused words.
4. Compare options and EEPROM against the expected preserved contents.
5. Repeat readback after target power cycling and a fresh adapter/host session.
6. Confirm execution using a small application with observable GPIO behavior.

An entry ACK confirms a transaction response. Readback after reset confirms
persistence; GPIO behavior confirms execution. Record all three separately.

Publish a sanitized result with target/package, adapter source identity,
application digest, checks performed and measurement limits. Clearly mark
features as supported, read-only, experimental or untested. See
[validation](validation.md) and [contributing](../CONTRIBUTING.md).
