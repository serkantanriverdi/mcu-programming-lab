# SPDX-License-Identifier: MIT
"""Assemble and behavior-check our HT66F002 examples using a project ISA subset.

No vendor SDK, include files, database, firmware image or DLL is required.
This limited assembler is not a complete Holtek development toolchain.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("source", type=Path)
p.add_argument("--led-bit",type=int,choices=[1,2],default=1,help="PA bit observed by the independent decoder")
p.add_argument("--check",choices=["blink","steady","pwm"],default="blink",help="Expected behavior in the software decoder")
p.add_argument("--max-steps",type=int,default=12000000)
a = p.parse_args()
root = Path(__file__).resolve().parent.parent
from targets.ht66f002 import FORMS, SYMBOLS

profile_path=Path(__file__).resolve().parent / "targets/ht66f002.py"
forms=dict(FORMS)
symbols=dict(SYMBOLS)

def include_symbols(text):
    for line in text.splitlines():
        m = re.match(r"\s*(\w+)\s+EQU\s+\[([0-9a-f]+)h\](?:\.(\d))?", line, re.I)
        if m:
            symbols[m[1].upper()] = (int(m[2], 16), int(m[3]) if m[3] is not None else None)

include_symbols(a.source.read_text())
labels = {}
instructions = []
pc = 0

def number(text):
    text = text.strip().upper()
    if text in labels:
        return labels[text]
    return int(text[:-1], 16) if text.endswith("H") else int(text, 0)

for line_no, original in enumerate(a.source.read_text().splitlines(), 1):
    line = original.split(";", 1)[0].strip()
    if not line or re.search(r"\bEQU\b", line, re.I):
        continue
    if line.endswith(":"):
        name = line[:-1].upper()
        assert name not in labels, name
        labels[name] = pc
    elif line.upper().startswith("ORG "):
        pc = number(line[4:])
    else:
        assert 0 <= pc < 1024
        instructions.append((pc, line_no, line))
        pc += 1

image = [0] * 1024
listing = []
occupied = set()

def encode(text):
    op, _, rest = text.upper().partition(" ")
    rest = rest.strip()
    if op == "CLR" and rest == "WDT":
        form, value = "clr wdt", 0
    elif op in ("NOP", "RET"):
        form, value = op.lower(), 0
    elif op in ("JMP", "CALL"):
        value = number(rest)
        assert 0 <= value <= 0x3ff
        form = op.lower() + " &3"
    elif op == "MOV":
        left, right = (s.strip() for s in rest.split(","))
        if left == "A":
            if right in symbols:
                value, bit = symbols[right]
                assert bit is None
                form = "mov a, &1"
            else:
                form, value = "mov a, &2", number(right)
                assert 0 <= value <= 255
        else:
            assert right == "A"
            value, bit = symbols[left]
            assert bit is None and 0 <= value <= 0x7f
            form = "mov &1, a"
    elif op == "SUB":
        left,right=(s.strip() for s in rest.split(","))
        assert left=="A"
        value,bit=symbols[right]
        assert bit is None
        form="sub a, &1"
    elif op in ("CLR", "SET", "SDZ","SIZ","SZ"):
        address, bit = symbols[rest]
        assert 0 <= address <= 0x7f
        assert bit is None or 0 <= bit <= 7
        form = op.lower() + (" &4" if bit is not None else " &1")
        value = address | ((bit << 7) if bit is not None else 0)
    else:
        raise ValueError(f"Unsupported instruction: {text}")
    base, mask = forms[form]
    word = base | value
    assert word <= 0x3fff and word & mask == base
    return word

for address, line_no, text in instructions:
    assert address not in occupied
    occupied.add(address)
    image[address] = encode(text)
    listing.append(f"{address:03X}  {image[address]:04X}  {text}")

# Decode the resulting words by the project ISA masks, independently of
# the source labels and assembler operand dispatch.
ram = [0] * 128
ram[0x15] = 255
pc = acc = cycles = steps = 0
stack = []
edges = []
last_led = 0
heartbeat_edges=[]
last_heartbeat=1
pwm_samples=[]
pwm_duty=0
pwm_total=pwm_on=0
edge_count=heartbeat_edge_count=0
def more_steps():
    if a.check=="pwm":return len(pwm_samples)<511
    return len(edges)<5 if a.check=="blink" else steps<10000
while more_steps() and steps < a.max_steps:
    previous_cycles=cycles
    previous_output=((ram[0x14]>>a.led_bit)&1) if not ram[0x15]&(1<<a.led_bit) else 0
    word = image[pc]
    pc = (pc + 1) & 0x3ff
    steps += 1
    cycles += 1
    if word == forms["nop"][0] or word == forms["clr wdt"][0]:
        pass
    elif word == forms["ret"][0]:
        assert stack
        pc = stack.pop()
        cycles += 1
    elif word & forms["mov a, &2"][1] == forms["mov a, &2"][0]:
        acc = word & 255
    elif word & forms["mov &1, a"][1] == forms["mov &1, a"][0]:
        ram[word & 127] = acc
    elif word & forms["mov a, &1"][1] == forms["mov a, &1"][0]:
        acc=ram[word&127]
    elif word & forms["sub a, &1"][1] == forms["sub a, &1"][0]:
        acc=(acc-ram[word&127])&255
    elif word & forms["sz &1"][1] == forms["sz &1"][0]:
        if ram[word&127]==0:
            pc=(pc+1)&0x3ff
            cycles+=1
    elif word & forms["siz &1"][1] == forms["siz &1"][0]:
        address=word&127
        ram[address]=(ram[address]+1)&255
        if ram[address]==0:
            pc=(pc+1)&0x3ff
            cycles+=1
    elif word & forms["sdz &1"][1] == forms["sdz &1"][0]:
        address = word & 127
        ram[address] = (ram[address] - 1) & 255
        if ram[address] == 0:
            pc = (pc + 1) & 0x3ff
            cycles += 1
    elif word & forms["clr &1"][1] == forms["clr &1"][0]:
        ram[word & 127] = 0
    elif word & forms["set &4"][1] == forms["set &4"][0]:
        ram[word & 127] |= 1 << ((word >> 7) & 7)
    elif word & forms["clr &4"][1] == forms["clr &4"][0]:
        ram[word & 127] &= ~(1 << ((word >> 7) & 7))
    elif word & forms["call &3"][1] == forms["call &3"][0]:
        stack.append(pc)
        assert len(stack) <= 2
        pc = word & 1023
        cycles += 1
    elif word & forms["jmp &3"][1] == forms["jmp &3"][0]:
        pc = word & 1023
        cycles += 1
    else:
        raise RuntimeError(f"Unimplemented decoded word: {word:04x}")
    led = (ram[0x14] >> a.led_bit) & 1
    heartbeat=1 if ram[0x15]&1 else (ram[0x14]&1)
    if heartbeat!=last_heartbeat:
        heartbeat_edge_count+=1
        if a.check!="pwm" or len(heartbeat_edges)<32:
            heartbeat_edges.append({"cycles":cycles,"level":heartbeat})
        last_heartbeat=heartbeat
    if led != last_led and not ram[0x15] & (1 << a.led_bit):
        edge_count+=1
        if a.check!="pwm" or len(edges)<32:
            edges.append({"cycles": cycles, "level": led, "seconds_at_8mhz": cycles / 2000000})
        last_led = led
    if a.check=="pwm":
        elapsed=cycles-previous_cycles
        pwm_total+=elapsed
        pwm_on+=elapsed*previous_output
        duty=ram[symbols['DUTY'][0]]
        if duty!=pwm_duty:
            if pwm_total>1000:
                pwm_samples.append(dict(duty=pwm_duty,cycles=pwm_total,on_cycles=pwm_on,
                                        on_percent=100*pwm_on/pwm_total,end_cycles=cycles))
            pwm_duty=duty
            pwm_total=pwm_on=0
if a.check=="blink":
    assert len(edges) == 5 and [e["level"] for e in edges] == [1, 0, 1, 0, 1]
    assert len(heartbeat_edges)>=3 and heartbeat_edges[0]["cycles"]>16000
    assert [e["level"] for e in heartbeat_edges[:2]]==[0,1]
    assert 16000<heartbeat_edges[1]["cycles"]-heartbeat_edges[0]["cycles"]<17000
    assert all(e["level"]==edges[i+1]["level"] for i,e in enumerate(heartbeat_edges[2:]))
elif a.check=="steady":
    assert len(edges)==1 and edges[0]["level"]==1 and last_led==1
else:
    assert len(pwm_samples)==511
    assert [x['duty'] for x in pwm_samples[:256]]==list(range(256))
    assert [x['duty'] for x in pwm_samples[256:]]==list(range(255,0,-1))
    brightness=[x['on_percent'] for x in pwm_samples]
    assert brightness[0]==0 and brightness[255]>99.5
    assert all(x<y for x,y in zip(brightness[:255],brightness[1:256]))
    assert all(x>y for x,y in zip(brightness[256:-1],brightness[257:]))
assert ram[0x19] == 0xa8 and ram[0xb] == 1 and ram[0x26] == 0
assert not ram[0x15] & (1 << a.led_bit) and ram[0xe] == ram[0xf] == 0
intervals = [b["cycles"] - aa["cycles"] for aa, b in zip(edges, edges[1:])] if a.check!="pwm" else []
assert all(c>0 for c in intervals), intervals
if intervals: assert max(intervals)-min(intervals)<=32, intervals
program_words = ((max(occupied) + 4) // 4) * 4
binary = b"".join(word.to_bytes(2, "little") for word in image[:program_words])
hex_lines = []
for offset in range(0, len(binary), 16):
    data = binary[offset:offset + 16]
    frame = bytes([len(data), offset >> 8, offset & 255, 0]) + data
    hex_lines.append(":" + (frame + bytes([-sum(frame) & 255])).hex().upper())
hex_lines.append(":00000001FF")
a.source.with_suffix(".hex").write_text("\n".join(hex_lines) + "\n")
a.source.with_suffix(".bin").write_bytes(binary)
a.source.with_suffix(".lst").write_text("\n".join(listing) + "\n")
result = {"device": "HT66F002", "method": __doc__,"led_pa_bit":a.led_bit,"behavior_check":a.check,
          "source_sha256": hashlib.sha256(a.source.read_bytes()).hexdigest(),
          "isa_definition_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
          "binary_sha256": hashlib.sha256(binary).hexdigest(),
          "program_words": program_words, "flash_words": image,
          "programming_commands": ["w " + f"{address:x} " + " ".join(f"{w:04x}" for w in image[address:address + 4])
                                   for address in range(0, program_words, 4)],
          "simulated_led_edges": edges, "cycles_per_half_period": intervals,
          "simulated_open_drain_pa0":heartbeat_edges,
          "pwm_level_samples":pwm_samples,"simulated_led_edge_count":edge_count,
          "simulated_pa0_edge_count":heartbeat_edge_count,
          "timing_note": "Predicted using HIRC 8MHz and 4 clocks/instruction cycle; not measured on target"}
a.source.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"program_words": program_words, "instructions": len(instructions),
                  "half_period_seconds_at_8mhz": [x / 2000000 for x in intervals],
                  "pwm_levels_checked":len(pwm_samples),
                  "binary_sha256": result["binary_sha256"]}))
