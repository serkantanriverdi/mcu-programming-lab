; SPDX-License-Identifier: MIT
; HT66F002 SOP8 pin6 / PA1, LED cathode via330ohms to pin8 / VSS.
; Build: .venv/bin/python host/assemble.py examples/ht66f002/led_pa1_dimmer.asm --check pwm
; 8-bit software PWM, approximately1.9kHz at nominal8MHz HIRC.
; 16frames per brightness level; 0..255..0, approximately4.3seconds/cycle.
; PA0 mirrors the PWM through input/output switching with its latch kept0.
; No extra wiring or potentiometer required for automatic brightness sweep.

COUNT0 EQU [040h]
COUNT1 EQU [041h]
FRAMES EQU [042h]
DUTY EQU [043h]

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
ramp:
    CLR DUTY
up:
    CALL pwm_level
    SIZ DUTY
    JMP up
    MOV A, 0FFh
    MOV DUTY, A
down:
    CALL pwm_level
    SDZ DUTY
    JMP down
    JMP ramp

pwm_level:
    MOV A, 16
    MOV FRAMES, A
pwm_frame:
    MOV A, DUTY
    MOV COUNT0, A
    SZ DUTY
    JMP do_on
    JMP off_setup
do_on:
    MOV A, 002h
    MOV PA, A
    SET PAC0
on_loop:
    CLR WDT
    SDZ COUNT0
    JMP on_loop
off_setup:
    MOV A, 0FFh
    SUB A, DUTY
    MOV COUNT0, A
    SZ COUNT0
    JMP do_off
    JMP frame_end
do_off:
    CLR PA
    CLR PAC0
off_loop:
    CLR WDT
    SDZ COUNT0
    JMP off_loop
frame_end:
    SDZ FRAMES
    JMP pwm_frame
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
