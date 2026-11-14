# EEPROM: reading, persistence and preservation

HT66F002 has 32 bytes of nonvolatile data EEPROM, addresses 00h..1Fh.
It is separate from program Flash and the option area. The LED applications
do not use it. Applications can use data EEPROM for retained settings or
counters within the device's ratings and with appropriate application code.

This release **reads EEPROM and checks that Flash programming preserves it**.
It does not contain an EEPROM writer or an application EEPROM library.
An EEPROM write command must not be inferred from the Flash write command.

## Read your device

With the supplied Nano sketch installed and the documented wiring:

```sh
.venv/bin/python host/session.py 'q 0 32 512' x --port YOUR_PORT --output records/eeprom-read.json
```

The session first verifies the Nano identity. `q` reads all 32 bytes; `x`
returns the MCU to normal execution. It writes no target memories, but does
power-cycle the target. The JSON record stays in the Git-ignored `records/`
directory because EEPROM can contain private application data.

For individual-byte reads, use `q 2 1 512` for address 02h or `q 8 1 512`
for address 08h. Addresses are hexadecimal; count and dummy clocks are decimal.
Your chip's contents depend on its previous use; no particular test byte
is required for a successful read.

## Target transaction

| Parameter | Implemented value |
|---|---|
| Entry bytes | 48h 8Ah 5Ch 23h, MSB first |
| Expected entry response | E3h |
| Default dummy clocks | 512 |
| Byte-read command | Binary 110 followed by 9 address bits, MSB first |
| Data | 8 bits, MSB first |
| End of byte | 2 extra clocks |

Flash uses a different LSB-first address/data path and four-word grouping.
Use each memory's specified transaction.

## Verified observations

A known test pattern, 12h at address 02h and A5h at address 08h, was recovered
in three separate adapter reset sessions. Full reads, single-byte reads and
neighboring-byte reads agreed after commanded target power cycling. Those
verification sessions executed no EEPROM write commands. This confirms the
stored test bytes and the independent read path; it does not validate a writer
for arbitrary EEPROM values or devices.

Both 512 and 1018 dummy clocks returned the same data on the tested target.
The current host uses 512. Reads at 20h..3Fh mirrored 00h..1Fh on that sample;
use only the documented 00h..1Fh capacity in applications. The mirrored range
does not provide additional storage.

During application programming, the host reads EEPROM before erase and
compares all 32 bytes afterward. Tests preserved both a nonblank test pattern
and an all-FF sample. A newly fitted chip must not be judged by whether it
contains a previous chip's test pattern.

## Adding EEPROM writing

Add it as a separately validated capability: documented preparation and
write-enable behavior, byte addressing, write completion, preserved neighbors
and reset-persistent readback are required. Test nonblank patterns as well as
FFh. Keep endurance limits and application use within the data sheet's ratings.
