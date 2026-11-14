# MCU parameters

These are parameters for the exact target. Confirm the complete model and
package before wiring. The
[manufacturer data sheet](https://www.holtek.com/webapi/116711/HT66F002_0025_003_004v230.pdf)
is the reference for electrical ratings and the complete register map.

## HT66F002 SOP8

| Parameter | Value / release behavior |
|---|---|
| Program Flash | 1024 words |
| Instruction width | 14 bits; values 0000h..3FFFh |
| File/transfer representation | 2 bytes per word, low byte first |
| Flash page transferred by this adapter | 4 words / 8 bytes |
| Flash address unit and range | Word addresses, 000h..3FFh |
| Last four-word page start | 3FCh |
| Blank Flash after the implemented erase | Reads 0000h on tested devices |
| Data RAM | 64 bytes; no live RAM debugger in this release |
| Data EEPROM | 32 bytes, byte addresses 00h..1Fh |
| EEPROM operations in this release | Read and preservation check |
| Option transfer area | 64 bytes / 32 words at wire address 80000h |
| Option bytes retained during initialization | Bytes 32..63 |
| Programming clock | SOP8 pin 4 / PA7 |
| Programming data | SOP8 pin 7 / PA0 |
| Supply / ground | Pin 1 / VDD, pin 8 / VSS |
| Example output | Pin 6 / PA1; PA0 also supplies a run signal |
| Example CPU clock assumption | Nominal 8 MHz HIRC; not recalibrated |
| Adapter write/erase wait | 3000 microseconds, bench-tested timing |
| Target power command | Off for 100 ms, then on; 5 ms startup wait |

The GPIO-powered prototype was checked only with the small target circuit
described in [wiring](wiring.md). Use the data sheet's electrical ratings
when designing a separate power supply or another adapter. No measured
target supply voltage is claimed here.

## Operation support

| Operation | Status |
|---|---|
| Full Flash read and comparison | Implemented and hardware-tested |
| Flash erase and four-word writes | Implemented and hardware-tested |
| Known user-option initialization | Implemented and hardware-tested |
| Upper option/trim-byte preservation | Compared before/after on tested samples |
| EEPROM read | Implemented and hardware-tested |
| EEPROM preservation during Flash programming | Implemented and hardware-tested |
| EEPROM write | Not implemented |
| Runtime RAM access / breakpoints | Not implemented |
| Analog oscillator / voltage calibration | Not implemented |
| Lock configuration / protected-image readout | Not implemented |
| Automatic physical MCU identification | Not implemented; check the part marking |

The Nano identity handshake identifies the adapter firmware. The image's
device field selects the intended target. Neither independently proves the
model physically connected to the wires.

## Address and option handling

Flash uses 20 address bits on the wire even though this chip's program
space contains 1024 words. EEPROM uses a different command and 9 address
bits; respect its actual 32-byte capacity.

The erase sequence saves option words 10h..1Fh using the option path at wire
address 10h. Full option reads use 80000h; option initialization enables the
control at 80040h. These are operation-specific wire addresses, separate
from the application's Flash image. See [protocol](protocol.md).

The host accepts only the known blank or initialized zero-user-option
patterns before erase. Other user options cause it to stop. Raw preservation
does not characterize the analog meaning of the retained bytes or provide
an oscillator calibration service.

## Peripheral configuration in the examples

The examples explicitly set clock/watchdog state, disable interrupts,
clear relevant ADC/pin-sharing controls and configure PA1 as an output.
For these ports a control bit of 0 selects output and 1 selects input.
PA0 holds a low output latch and changes direction to provide its run signal;
the Nano supplies an input pull-up only while sampling it.

The assembler contains only the register and instruction subset needed by
the examples. Other peripherals require additional verified definitions and
application code. Another MCU needs its own [target profile](method.md).
