# HT66F002 wiring and run state

This profile is for the 8-pin SOP HT66F002. Confirm the dot/notch before
counting pins; the diagram is a top view.

```text
             HT66F002
Nano D4 → 1 ┌────────┐ 8 ← GND
       PA6 2 │        │ 7 ← Nano D3 / PA0 / ICPDA
       PA5 3 │        │ 6 → LED anode / PA1
Nano D2 → 4 └────────┘ 5   PA2
          PA7 / ICPCK

LED cathode → 330 ohm → GND
```

Pin 6 is shared with analog/reference/timer functions. The example clears
the relevant ADC and pin-sharing controls, then clears PAC1 to make PA1
an output. In this MCU a port-control bit of 0 means output, 1 means input.

PA0 is programming data. The examples hold its output latch low and change
its direction, giving an open-drain-like heartbeat. The Nano enables a
pull-up only when sampling this signal. PA7 is programming clock and is
released as an input when the application runs.

The prototype switches the small target's supply using Nano D4. It has
not characterized voltage/current margins for arbitrary attached boards.
Provide the target's recommended local decoupling. External supplies,
large capacitors or extra circuitry can change the power-off/reset behavior.
Check the target's pinout and electrical requirements before connecting it.

`x` powers the target down for 100 ms, releases clock/data, then turns power
on. Most low-level read/write commands leave it off afterward; finish a
manual session with `x` if you want the application running. The high-level
programmer does this automatically on success.

Recorded D4 transitions are commanded power cycles; they are not an
independent measurement of the target's actual supply voltage.
