; SPDX-License-Identifier: MIT
; HT66F002 SOP8 pin6/PA1 continuously HIGH. Cathode via330ohms to pin8/VSS.
; Assemble: .venv/bin/python host/assemble.py examples/ht66f002/led_pa1_on.asm --check steady
; Generated and checked in software; this variant was not flashed in the session.
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
    MOV A, 002h
    MOV PA, A
    CLR PAC1
again:
    CLR WDT
    JMP again
