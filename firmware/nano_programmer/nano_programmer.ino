// SPDX-License-Identifier: MIT
// MCU Programming Lab: original Nano adapter for the HT66F002 ICP interface.
// Nano D2 -> SOP8 pin4 CK; D3 -> pin7 DA; D4 -> pin1 VDD; GND -> pin8.
// Interoperability behavior is described in docs/protocol.md; no vendor firmware is embedded.
// v: identity; r <mode 0|1> <wire address hex> <word count, multiple of 4>
#include <Arduino.h>
#include <avr/io.h>
#include <avr/interrupt.h>

static const char BUILD_ID[] = "MCULAB_HT66F002_V1";
// The first target profile implements only the tested HT66F002 ICP wire path.
// A 3 ms write wait worked on the development circuit.
// Timing margins and the vendor programmer's physical timing remain unmeasured.
static const uint16_t WRITE_WAIT_US=3000;
static inline void ck0() { PORTD &= ~_BV(2); }
static inline void ck1() { PORTD |= _BV(2); }
static inline void da0() { PORTD &= ~_BV(3); }
static inline void da1() { PORTD |= _BV(3); }
static inline void daOut() { DDRD |= _BV(3); }
static inline void daIn() { DDRD &= ~_BV(3); PORTD &= ~_BV(3); }
static inline uint8_t sample() { return (PIND >> 3) & 1; }
static inline void pulse() {
  ck0(); delayMicroseconds(1); ck1(); delayMicroseconds(1);
}
static void off() { DDRD |= _BV(2); da0(); daOut(); ck0(); PORTD &= ~_BV(4); }
static void runTarget() {
  off(); delay(100);
  daIn(); PORTD &= ~_BV(2); DDRD &= ~_BV(2);
  PORTD |= _BV(4); delay(5);
}
static void watchRuntime() {
  runTarget(); PORTD |= _BV(3); delayMicroseconds(10); // input pullup for open-drain PA0
  uint32_t times[6]; uint8_t levels[6],count=0,initial=sample(),last=initial;
  uint32_t started=micros();
  while (count<6 && uint32_t(micros()-started)<6000000UL) {
    uint8_t level=sample();
    if (level!=last) { times[count]=micros()-started; levels[count++]=level; last=level; }
  }
  Serial.print(F("TYPE6 RUNTIME INITIAL=")); Serial.print(initial);
  Serial.print(F(" EDGES=")); Serial.print(count); Serial.print(F(" US="));
  for (uint8_t n=0;n<count;++n) { Serial.print(levels[n]); Serial.print(':'); Serial.print(times[n]); Serial.print(' '); }
  Serial.println(F("VDD=ON"));
}
static void powerCycle() {
  off(); delay(100); PORTD |= _BV(4); delay(5);
}
static uint8_t enter(uint8_t mode, uint8_t *dummySamples=NULL, uint8_t b3=0, uint16_t dummyCount=512) {
  ck0(); da1(); daOut(); delayMicroseconds(150);
  ck1(); delayMicroseconds(50);
  const uint8_t key[4] = {0x48, 0x8a, 0x5c, uint8_t((mode << 1) | 1 | (b3?0x20:0))};
  for (uint8_t n=0; n<4; ++n) {
    uint8_t value = key[n];
    for (uint8_t b=0; b<8; ++b) {
      ck1(); if (value & 0x80) da1(); else da0();
      delayMicroseconds(1); ck0(); delayMicroseconds(1);
      value <<= 1;
    }
  }
  daIn();
  delayMicroseconds(1); ck1(); delayMicroseconds(1);
  uint8_t ack=0;
  for (uint8_t b=0; b<8; ++b) {
    ck0(); delayMicroseconds(1); ack=(ack << 1) | sample(); ck1();
  }
  if (ack == uint8_t(0xc0 + key[3])) {
    for (uint16_t n=0; n<dummyCount; ++n) {
      ck0(); delayMicroseconds(1);
      if (dummySamples) {
        if (!(n&7)) dummySamples[n>>3]=0;
        dummySamples[n>>3] |= sample() << (n&7);
      }
      ck1(); delayMicroseconds(1);
    }
  }
  return ack;
}
static void address20(uint32_t address) {
  daOut();
  for (uint8_t b=0; b<20; ++b) {
    if (address & 1) da1(); else da0(); delayMicroseconds(1);
    ck0(); delayMicroseconds(1);
    if (b==19) daIn();
    ck1(); delayMicroseconds(1); delayMicroseconds(1); address >>= 1;
  }
}
static uint8_t read8() {
  uint8_t value=0;
  for (uint8_t b=0; b<8; ++b) {
    ck0(); delayMicroseconds(1); value |= sample() << b; ck1();
  }
  return value;
}
static void readGroups(uint8_t *data, uint8_t bytes) {
  daIn();
  for (uint8_t group=0; group<bytes/8; ++group) {
    ck0(); delayMicroseconds(3);
    for (uint8_t b=0; b<8; ++b) data[group*8+b]=read8();
    pulse(); pulse();
  }
}
// Eight bytes LSB first; release data during the low clock phase,
// then issue one clock, the write wait, and a final clock.
static void writeGroup(const uint8_t *data) {
  daOut();
  for (uint8_t n=0; n<8; ++n) {
    uint8_t value=data[n];
    for (uint8_t b=0; b<8; ++b) {
      if (value&1) da1(); else da0(); delayMicroseconds(1);
      ck0(); delayMicroseconds(1); ck1(); delayMicroseconds(1); value>>=1;
    }
  }
  ck0(); delayMicroseconds(1);
  daIn();
  ck1(); delayMicroseconds(1);
  delayMicroseconds(WRITE_WAIT_US);
  pulse();
}
static bool controlRegister(uint32_t address, uint8_t value, uint8_t &ack) {
  uint8_t bytes[8]={value,0,0,0,0,0,0,0};
  ack=enter(6);
  if (ack!=0xcd) return false;
  address20(address); writeGroup(bytes); return true;
}
static bool control41(uint8_t value, uint8_t &ack) { return controlRegister(0x41,value,ack); }
static uint8_t optionHighByte(uint8_t index) {
  uint8_t folded=(index&7)^((index&8)?7:0);
  return ((folded&1)?0x15:0)^((folded&2)?0x2a:0)^((folded&4)?0x07:0);
}
// Initialize high bytes of the user option words, enable control 80040h,
// and write the 64-byte option area at 80000h in eight groups.
// Accept only an all-zero user option area; retain bytes 32..63 exactly.
// Analog HIRC/LVR calibration is not implemented by this command.
static void initializeOptionEncoding() {
  static uint8_t before[64],expected[64],after[64];
  uint8_t stage=0,ack=0,controlAck=0; bool sent=false,match=false;
  memset(before,0x5a,64); memset(after,0xa5,64);
  powerCycle(); uint8_t saved=SREG; cli();
  do {
    stage=1; ack=enter(0); if (ack!=0xc1) break;
    address20(0x80000); readGroups(before,64);
    stage=2; ack=enter(0); if (ack!=0xc1) break;
    address20(0x80000); readGroups(after,64);
    if (memcmp(before,after,64)) break;
    bool blank=true; for (uint8_t n=0;n<32;++n) if (before[n]) blank=false;
    if (!blank) break;
    memcpy(expected,before,64);
    for (uint8_t n=0;n<16;++n) expected[2*n+1]=optionHighByte(n);
    stage=3; if (!controlRegister(0x80040,1,controlAck)) break;
    stage=4; ack=enter(6); if (ack!=0xcd) break;
    address20(0x80000);
    for (uint8_t n=0;n<8;++n) writeGroup(expected+8*n);
    sent=true;
    stage=5; ack=enter(0); if (ack!=0xc1) break;
    address20(0x80000); readGroups(after,64);
    match=!memcmp(expected,after,64); stage=6;
  } while (false);
  SREG=saved; off();
  Serial.print(F("TYPE6 OPTIONS STAGE=")); Serial.print(stage);
  Serial.print(F(" ACK=")); hex2(ack); Serial.print(F(" CONTROL_ACK=")); hex2(controlAck);
  Serial.print(F(" SENT=")); Serial.print(sent); Serial.print(F(" MATCH=")); Serial.print(match);
  Serial.print(F(" BEFORE=")); for (uint8_t n=0;n<64;++n) hex2(before[n]);
  Serial.print(F(" AFTER=")); for (uint8_t n=0;n<64;++n) hex2(after[n]); Serial.println();
}
// Preserve and re-read 32 option bytes before enabling erase at control 40h.
// Restore the saved bytes afterward and verify the entire preserved range.
// Raw preservation retains all bits. Host checkpoint contains the whole image.
static void erasePreservingOptions() {
  static uint8_t before[32],second[32],after[32];
  uint8_t stage=0,ack=0,controlAck=0; bool erased=false,verified=false;
  memset(before,0x5a,32); memset(second,0xa5,32); memset(after,0x69,32);
  powerCycle(); uint8_t saved=SREG; cli();
  do {
    stage=1; ack=enter(0); if (ack!=0xc1) break;
    address20(0x10); readGroups(before,32);
    stage=2; ack=enter(0); if (ack!=0xc1) break;
    address20(0x10); readGroups(second,32);
    if (memcmp(before,second,32)) break;
    stage=3; if (!controlRegister(0x40,1,controlAck)) break;
    stage=4; ack=enter(12); if (ack!=0xd9) break;
    address20(0); da0(); daOut();
    for (uint8_t n=0;n<64;++n) pulse();
    pulse(); delayMicroseconds(WRITE_WAIT_US); pulse(); erased=true;
    stage=5; if (!controlRegister(0x40,1,controlAck)) break;
    stage=6; ack=enter(6); if (ack!=0xcd) break;
    address20(0x10);
    for (uint8_t n=0;n<4;++n) writeGroup(before+8*n);
    stage=7; ack=enter(0); if (ack!=0xc1) break;
    address20(0x10); readGroups(after,32);
    verified=!memcmp(before,after,32); stage=8;
  } while (false);
  SREG=saved; off();
  Serial.print(F("TYPE6 ERASE STAGE=")); Serial.print(stage);
  Serial.print(F(" ACK=")); hex2(ack); Serial.print(F(" CONTROL_ACK=")); hex2(controlAck);
  Serial.print(F(" SENT=")); Serial.print(erased);
  Serial.print(F(" OPTIONS_MATCH=")); Serial.print(verified);
  Serial.print(F(" BEFORE=")); for (uint8_t n=0;n<32;++n) hex2(before[n]);
  Serial.print(F(" AFTER=")); for (uint8_t n=0;n<32;++n) hex2(after[n]); Serial.println();
}
static void gatedRead(bool unlock=false) {
  static uint8_t data[64]; uint8_t a=0,b=0,c=0;
  powerCycle(); uint8_t saved=SREG; cli();
  uint8_t unlockAck=0;
  if (unlock) controlRegister(0x40,1,unlockAck);
  bool ok=control41(1,a);
  if (ok) { b=enter(0); ok=b==0xc1; }
  if (ok) { address20(0); readGroups(data,64); }
  bool closed=control41(0,c);
  SREG=saved; off();
  Serial.print(F("TYPE6 GATE ACK=")); hex2(a); Serial.print('/'); hex2(b); Serial.print('/'); hex2(c);
  if (unlock) { Serial.print(F(" CONTROL40=")); hex2(unlockAck); }
  Serial.print(closed?F(" CLOSED"):F(" CLOSE_FAIL"));
  if (!ok) { Serial.println(F(" FAIL")); return; }
  Serial.print(F(" WORDS="));
  for (uint8_t w=0; w<32; ++w) { hex2(data[2*w+1]); hex2(data[2*w]); Serial.print(' '); }
  Serial.println();
}
static void programGroup(uint16_t address, const uint16_t *words, bool unlock=false) {
  if (address>0x3fc || (address&3)) { Serial.println(F("TYPE6 WRITE ERR address")); return; }
  uint8_t bytes[8];
  for (uint8_t n=0; n<4; ++n) {
    if (words[n]>0x3fff) { Serial.println(F("TYPE6 WRITE ERR word")); return; }
    bytes[2*n]=words[n]; bytes[2*n+1]=words[n]>>8;
  }
  powerCycle(); uint8_t saved=SREG; cli();
  uint8_t unlockAck=0;
  bool ready=!unlock || controlRegister(0x40,1,unlockAck);
  uint8_t ack=ready?enter(7):0;
  if (ack==0xcf) { address20(address); writeGroup(bytes); }
  SREG=saved; off();
  Serial.print(F("TYPE6 WRITE ADDR=")); Serial.print(address,HEX);
  Serial.print(F(" ACK=")); hex2(ack); Serial.println(ack==0xcf?F(" SENT"):F(" FAIL"));
}
static void hex2(uint8_t value) { if (value<16) Serial.print('0'); Serial.print(value, HEX); }
// Native EEPROM: read command 2 (110), nine address bits MSB first,
// followed by eight MSB data bits and two tail clocks.
static void eepromCommand9(uint8_t command, uint16_t address) {
  daOut();
  uint16_t frame=(uint16_t(4|command)<<9)|(address&0x1ff);
  for (int8_t b=11;b>=0;--b) {
    if ((frame>>b)&1) da1(); else da0(); delayMicroseconds(1);
    ck0(); delayMicroseconds(1); if (!b) daIn(); ck1(); delayMicroseconds(1);
  }
}
static uint8_t eepromRead8() {
  uint8_t value=0;
  for (uint8_t n=0;n<8;++n) {
    ck0(); delayMicroseconds(1); value=(value<<1)|sample(); ck1(); delayMicroseconds(1);
  }
  pulse(); pulse(); return value;
}
static void eepromRead(uint16_t address, uint8_t count, uint16_t dummyCount) {
  if (address>0x1ff || !count || count>64 || (dummyCount!=512 && dummyCount!=1018)) return;
  // The independently verified native EEPROM routine uses its original key.
  static uint8_t data[64]; memset(data,0x5a,sizeof(data));
  powerCycle(); uint8_t saved=SREG; cli();
  uint8_t ack=enter(1,NULL,1,dummyCount);
  if (ack==0xe3) {
    for (uint8_t n=0;n<count;++n) { eepromCommand9(2,address+n); data[n]=eepromRead8(); }
  }
  SREG=saved; off();
  Serial.print(F("TYPE6 EEPROM ADDR=")); Serial.print(address,HEX);
  Serial.print(F(" DUMMY=")); Serial.print(dummyCount); Serial.print(F(" ACK=")); hex2(ack);
  if (ack!=0xe3) { Serial.println(F(" FAIL")); return; }
  Serial.print(F(" DATA="));
  for (uint8_t n=0;n<count;++n) { hex2(data[n]); if (n+1<count) Serial.print(' '); }
  Serial.println();
}
static void traceRead(uint8_t mode, uint32_t address) {
  if (mode>1 || address>0xfffffUL) return;
  static uint8_t dummy[64],raw[33];
  memset(raw,0,sizeof(raw));
  powerCycle(); uint8_t saved=SREG; cli();
  uint8_t ack=enter(mode,dummy);
  if (ack==uint8_t(0xc1+(mode<<1))) {
    address20(address); daIn(); ck0(); delayMicroseconds(3);
    for (uint16_t n=0;n<264;++n) {
      ck0(); delayMicroseconds(1); raw[n>>3] |= sample() << (n&7); ck1();
    }
  }
  SREG=saved; off();
  Serial.print(F("TYPE6 TRACE MODE=")); Serial.print(mode); Serial.print(F(" ADDR=")); Serial.print(address,HEX);
  Serial.print(F(" ACK=")); hex2(ack);
  Serial.print(F(" DUMMY512_LSB=")); for (uint8_t n=0;n<64;++n) hex2(dummy[n]);
  Serial.print(F(" STREAM264_LSB=")); for (uint8_t n=0;n<33;++n) hex2(raw[n]); Serial.println();
}
static void readWords(uint8_t mode, uint32_t address, uint8_t count) {
  if (mode>1 || !count || count>64 || count%4 || address>0xfffffUL) {
    Serial.println(F("ERR r <0|1> <address hex <=fffff> <words 4..64, multiple of 4>")); return;
  }
  static uint8_t data[128];
  powerCycle();
  uint8_t saved=SREG; cli();
  uint8_t ack=enter(mode);
  if (ack == uint8_t(0xc1 + (mode << 1))) {
    address20(address);
    readGroups(data,count*2);
  }
  SREG=saved; off();
  Serial.print(F("TYPE6 MODE=")); Serial.print(mode);
  Serial.print(F(" ADDR=")); Serial.print(address, HEX);
  Serial.print(F(" ACK=")); hex2(ack);
  if (ack != uint8_t(0xc1 + (mode << 1))) { Serial.println(F(" FAIL")); return; }
  Serial.print(F(" RAW="));
  for (uint8_t b=0; b<count*2; ++b) { hex2(data[b]); if (b+1<count*2) Serial.print(' '); }
  Serial.print(F(" WORDS="));
  for (uint8_t w=0; w<count; ++w) {
    hex2(data[w*2+1]); hex2(data[w*2]); if (w+1<count) Serial.print(' ');
  }
  Serial.println();
}
void setup() {
  DDRD |= _BV(2) | _BV(4); off();
  Serial.begin(115200); Serial.println(BUILD_ID);
  // Normal target execution survives host serial close / Nano auto-reset.
  // Every programming command explicitly powers off and reclaims CK/DA.
  runTarget();
}
void loop() {
  static char line[80]; static uint8_t n=0;
  while (Serial.available()) {
    char c=Serial.read();
    if (c=='\r') continue;
    if (c!='\n') { if (n<sizeof(line)-1) line[n++]=c; continue; }
    line[n]=0; n=0;
    if (line[0]=='v' && line[1]==0) { Serial.println(BUILD_ID); continue; }
    if (line[0]=='x' && line[1]==0) { runTarget(); Serial.println(F("TYPE6 RUN VDD=ON CK=INPUT DA=INPUT")); continue; }
    if (line[0]=='m' && line[1]==0) { watchRuntime(); continue; }
    if (line[0]=='g' && line[1]==0) { gatedRead(); continue; }
    if (line[0]=='h' && line[1]==0) { gatedRead(true); continue; }
    if (line[0]=='e' && line[1]==0) { erasePreservingOptions(); continue; }
    if (line[0]=='o' && line[1]==0) { initializeOptionEncoding(); continue; }
    char *p=strtok(line," \t");
    if (p && !strcmp(p,"p")) {
      p=strtok(NULL," \t");
      if (!p || strcmp(p,"icp")) continue;
      off();
      Serial.println(F("TYPE6 PROFILE HT66F002_ICP"));
      continue;
    }
    if (p && !strcmp(p,"q")) {
      p=strtok(NULL," \t"); if (!p) continue; uint16_t address=strtoul(p,NULL,16);
      p=strtok(NULL," \t"); if (!p) continue; uint8_t count=strtoul(p,NULL,10);
      p=strtok(NULL," \t"); if (!p) continue; uint16_t dummy=strtoul(p,NULL,10);
      eepromRead(address,count,dummy); continue;
    }
    if (p && !strcmp(p,"t")) {
      p=strtok(NULL," \t"); if (!p) continue; uint8_t mode=strtoul(p,NULL,10);
      p=strtok(NULL," \t"); if (!p) continue; uint32_t address=strtoul(p,NULL,16);
      traceRead(mode,address); continue;
    }
    if (p && (!strcmp(p,"w") || !strcmp(p,"u"))) {
      bool unlock=p[0]=='u';
      p=strtok(NULL," \t"); if (!p) continue; uint16_t address=strtoul(p,NULL,16);
      uint16_t words[4]; bool complete=true;
      for (uint8_t k=0;k<4;++k) { p=strtok(NULL," \t"); if (!p) { complete=false; break; } words[k]=strtoul(p,NULL,16); }
      if (complete) programGroup(address,words,unlock); continue;
    }
    if (!p || strcmp(p,"r")) { Serial.println(F("ERR command")); continue; }
    p=strtok(NULL," \t"); if (!p) continue; uint8_t mode=strtoul(p,NULL,10);
    p=strtok(NULL," \t"); if (!p) continue; uint32_t address=strtoul(p,NULL,16);
    p=strtok(NULL," \t"); if (!p) continue; uint8_t count=strtoul(p,NULL,10);
    readWords(mode,address,count);
  }
}
