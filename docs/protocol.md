# Implemented HT66F002 interface

These transactions are implemented by the Nano adapter for HT66F002.
Use the exact target profile and [documented wiring](wiring.md).

## Entry and transfer

The adapter commands target power off for 100 ms, then on, waits 5 ms and
enters the programming interface. Entry bytes are `48 8A 5C xx`, MSB first.
The mode and data-memory flag determine `xx`; its response is 8 bits.

| Operation | Entry byte | Expected response |
|---|---|---|
| Option read |01|C1|
| Program read |03|C3|
| Option/control write |0D|CD|
| Program write |0F|CF|
| Erase |19|D9|
| Native EEPROM read |23|E3|

For program/options, a successful entry is followed by 512 dummy clocks and
a 20-bit address sent least-significant bit first. Data is grouped in 8 bytes,
equivalent to four 14-bit program words stored as little-endian 16-bit values.
There are two extra clocks per group. Data bits are LSB first.

The implementation preserves the tested turnaround at the final address
bit and in the write tail. The Nano uses a 3000 µs write/erase wait. This
value worked on the tested circuit; it is not a full timing characterization.

## Erase and options

The normal erase wrapper reads and compares 32 bytes of option/trim state
starting at option word 10h, enables the control register, performs the
erase clocks and restores/verifies those 32 bytes. On the tested target,
erased program words read 0000.

After writing the program pages, the option area also needs initialization.
The high bytes of its first 16 words follow an address-dependent pattern.
`option_high_byte()` in the project target module generates it algebraically.
The firmware writes the control at 80040h and then the 64-byte option area
at 80000h, preserving the upper 32 bytes. It reads the result back and compares.

Complete this option step before starting the application. No analog
HIRC/LVR recalibration is performed. The host accepts only the known
blank/zero-user-option patterns before erase.

## EEPROM and execution

EEPROM uses a separate MSB-first command/address path with 9 address bits,
8 data bits and two tail clocks. 512 dummy clocks worked; EEPROM writing
is not implemented. The host compares EEPROM before and after programming.

The application starts through a target power/reset cycle with clock/data
released. A separate PA0 signal distinguishes code execution from mere
readback. Blink is about half a second per state on the tested chips;
PWM dimmer uses a nominal 1.93 kHz software PWM and approximately 4.26 s sweep
at 8 MHz. Actual speed depends on the uncalibrated oscillator.

## Host serial interface

115200 baud, ASCII, LF line endings. Firmware ID: `MCULAB_HT66F002_V1`.
Addresses/data are hex; counts are decimal.

| Command | Purpose |
|---|---|
| `v` | Firmware identity |
| `p icp` | Select the implemented profile |
| `r 1 0 8` | Read 8 program words |
| `r 0 80000 32` | Read 64 option bytes as 32 words |
| `w 0 2820 0 0 0` | Write one aligned four-word page |
| `e` | Erase with option/trim preservation |
| `o` | Initialize and verify the known option encoding |
| `q 0 32 512` | Read 32 EEPROM bytes |
| `m` | Sample up to 6 PA0 edges or 6 seconds |
| `x` | Reset into normal execution |

Additional low-level diagnostic commands are for adapter development.
Other chips need separately implemented and validated profiles.
