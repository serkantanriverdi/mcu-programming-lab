; SPDX-License-Identifier: MIT
; HT66F002 SOP8 pin6 = PA1; LED cathode via 330 ohms to pin8/VSS.
; Assemble: .venv/bin/python host/assemble.py examples/ht66f002/led_pa1.asm --led-bit 1
; Project ISA subset; PASR=0 selects GPIO, PAC1=0 enables output.
; Entire PA latch writes keep PA0 low while its direction toggles open drain.
; PA0/ICPDA stays input through a short initial delay for programmer entry.

COUNT0 EQU [040h]
COUNT1 EQU [041h]
COUNT2 EQU [042h]

ORG 000h
    JMP start

ORG 020h
start:
    MOV A, 0A8h
    MOV WDTC, A
    MOV A, 001h
    MOV SMOD, A
    CLR INTC0
    CLR INTC1
    CLR MFI0
    CLR SADC0
    CLR PASR
    CLR PA
    CLR PAC1
    CALL short_delay
    CLR PAC0
    CALL short_delay
    SET PAC0
    CALL delay_visible
again:
    MOV A, 002h
    MOV PA, A
    SET PAC0
    CALL delay_visible
    CLR PA
    CLR PAC0
    CALL delay_visible
    JMP again

delay_visible:
    MOV A, 4
    MOV COUNT2, A
outer:
    MOV A, 0FFh
    MOV COUNT1, A
middle:
    MOV A, 0FFh
    MOV COUNT0, A
inner:
    CLR WDT
    SDZ COUNT0
    JMP inner
    SDZ COUNT1
    JMP middle
    SDZ COUNT2
    JMP outer
    RET

short_delay:
    MOV A, 16
    MOV COUNT1, A
short_outer:
    MOV A, 0FFh
    MOV COUNT0, A
short_inner:
    CLR WDT
    SDZ COUNT0
    JMP short_inner
    SDZ COUNT1
    JMP short_outer
    RET
