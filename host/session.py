# SPDX-License-Identifier: MIT
"""Recorded session against a specifically identified Nano sketch."""
import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import serial

p=argparse.ArgumentParser()
p.add_argument("commands",nargs="+")
p.add_argument("--port",required=True)
p.add_argument("--identity",default="MCULAB_HT66F002_V1")
p.add_argument("--output",required=True)
p.add_argument("--quiet",action="store_true")
a=p.parse_args()
sketch_path=Path(__file__).resolve().parent.parent / "firmware/nano_programmer/nano_programmer.ino"
sketch_hash_at_start=hashlib.sha256(sketch_path.read_bytes()).hexdigest()
for cmd in a.commands:
    if not re.fullmatch(r"p icp|r [01] [0-9a-fA-F]{1,5} (4|8|12|16|20|24|28|32|36|40|44|48|52|56|60|64)|t [01] [0-9a-fA-F]{1,5}|[ghexmo]|[wu] [0-9a-fA-F]{1,3}( [0-3]?[0-9a-fA-F]{1,3}){4}|q [0-9a-fA-F]{1,3} ([1-9]|[1-5][0-9]|6[0-4]) (512|1018)",cmd):
        p.error("Unsupported command or malformed arguments")
results=[]
def receive(s,seconds):
    end=time.monotonic()+seconds; data=bytearray()
    while time.monotonic()<end:
        data.extend(s.read(4096))
        if data.endswith(b"\n"): break
    return data.decode("ascii",errors="replace").strip()
with serial.Serial(a.port,115200,timeout=0.2,exclusive=True) as s:
    s.dtr=False
    time.sleep(0.1)
    s.reset_input_buffer()
    s.dtr=True
    time.sleep(2.5)
    boot=s.read(4096).decode("ascii",errors="replace").strip()
    s.write(b"v\n"); identity=receive(s,2)
    print("BOOT",boot,"IDENTITY",identity,flush=True)
    if identity!=a.identity: raise RuntimeError("Unexpected Nano firmware; no target command sent")
    for cmd in a.commands:
        s.write((cmd+"\n").encode()); answer=receive(s,10 if cmd=="m" else 3)
        if not answer.startswith("TYPE6 "): raise RuntimeError(f"Unexpected response: {answer!r}")
        results.append(dict(command=cmd,response=answer))
        print(cmd,"=>",answer[:100]+("..." if len(answer)>100 else "") if a.quiet else answer,flush=True)
record=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),port=a.port,identity=identity,
            boot=boot,reset_method="Nano DTR false/true, 100ms pulse, 2.5s boot wait",
            sketch_sha256=sketch_hash_at_start,results=results)
Path(a.output).parent.mkdir(parents=True,exist_ok=True)
Path(a.output).write_text(json.dumps(record,indent=2)+"\n")
