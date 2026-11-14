# SPDX-License-Identifier: MIT
"""Minimal project-maintained HT66F002 interoperability facts.

This is an instruction/register subset used by our examples, not a vendor
include file or complete chip database. Only HT66F002 has been bench tested.
"""

DEVICE = "HT66F002"
FLASH_WORDS = 1024
WORD_MASK = 0x3FFF
FIRMWARE_ID = "MCULAB_HT66F002_V1"

REGISTERS = {
    "SMOD": 0x0B,
    "INTC0": 0x0E,
    "INTC1": 0x0F,
    "MFI0": 0x11,
    "PA": 0x14,
    "PAC": 0x15,
    "WDTC": 0x19,
    "SADC0": 0x22,
    "PASR": 0x26,
}
SYMBOLS = {name: (address, None) for name, address in REGISTERS.items()}
for port in ("PA", "PAC"):
    for bit in range(8):
        SYMBOLS[f"{port}{bit}"] = (REGISTERS[port], bit)

# Numeric instruction encodings for the subset implemented by our assembler.
# Keys describe operands: &1=register, &2=literal, &3=address, &4=register bit.
FORMS = {
    "nop": (0x0000, 0x3FFF),
    "clr wdt": (0x0001, 0x3FFF),
    "ret": (0x0003, 0x3FFF),
    "mov &1, a": (0x0080, 0x3F80),
    "sub a, &1": (0x0200, 0x3F80),
    "mov a, &1": (0x0700, 0x3F80),
    "mov a, &2": (0x0F00, 0x3F00),
    "sz &1": (0x1080, 0x3F80),
    "siz &1": (0x1680, 0x3F80),
    "sdz &1": (0x1780, 0x3F80),
    "clr &1": (0x1F00, 0x3F80),
    "set &1": (0x1F80, 0x3F80),
    "call &3": (0x2000, 0x3C00),
    "jmp &3": (0x2800, 0x3C00),
    "set &4": (0x3000, 0x3C00),
    "clr &4": (0x3400, 0x3C00),
    "sz &4": (0x3C00, 0x3C00),
}


def option_high_byte(index):
    """Generate the option-word pattern required by the tested device.

    The folded address bits generate the observed pattern algebraically;
    no extracted ROM table is loaded or distributed.
    """
    if not 0 <= index < 16:
        raise ValueError("Option word index must be in 0..15")
    folded = (index & 7) ^ (7 if index & 8 else 0)
    return ((0x15 if folded & 1 else 0)
            ^ (0x2A if folded & 2 else 0)
            ^ (0x07 if folded & 4 else 0))
