# MCU Programming Lab

Arduino Nano ile mikrodenetleyici programlama araçları, MCU parametreleri
ve doğrulanmış uygulama örnekleri.
İlk doğrulanan hedef **Holtek HT66F002**, programlayıcı Arduino Nano'dur.
İsim jeneriktir; bu sürümün bütün MCU veya Holtek modellerini desteklediği
anlamına gelmez. HT66F0021 ve HT66F0025 bu sürümde desteklenmez.

Bu yayın sürümü Nano'ya yüklenip HT66F002 üzerinde denendi. Dimmer yazıldı,
1024 word tam eşleşti; seçenekler ve EEPROM doğrulandı. Ayrı reset/host
oturumunda kalıcı okuma ve çalışma sinyali yeniden doğrulandı.
Ayrıntılar [doğrulama belgesinde](docs/validation.md).

[English README ve komutlar](README.md) · [MCU parametreleri](docs/parameters.md) ·
[EEPROM](docs/eeprom.md) · [Lisans ve kaynaklar](NOTICE.md)

## Bağlantı

Nano GND → MCU 8, D2 → 4/PA7, D3 → 7/PA0, D4 → 1/VDD.
LED anodu 6/PA1'e; katodu 330 Ω üzerinden 8/GND'ye bağlanır.
Numaralar HT66F002 SOP8 üstten görünüş içindir.

## MCU parametreleri ve EEPROM

| Parametre | HT66F002 |
|---|---|
| Program Flash | 1024 × 14 bit word |
| Aktarım sayfası | 4 word / 8 bayt |
| Veri RAM | 64 bayt |
| Veri EEPROM | 32 bayt, 00h..1Fh |
| Seçenek aktarım alanı | 64 bayt; son 32 bayt korunur |

EEPROM okuma ve Flash yazılırken EEPROM'un korunması doğrulandı. Bu sürüm
EEPROM'a yazmaz. LED örnekleri EEPROM kullanmaz; mevcut veriler kontrol edilir.
EEPROM'u bağımsız okumak ve hedefi tekrar çalıştırmak için:

```sh
.venv/bin/python host/session.py 'q 0 32 512' x --port PORT_ADI --output records/eeprom-read.json
```

Tanınan test baytları ayrı reset oturumlarında kalıcı olarak okundu.
512 ve 1018 boş saatle aynı sonuç alındı; araç 512 kullanır. Bir örnekte
20h..3Fh adresleri ilk 32 baytı aynaladı; bu alan ek kapasite değildir.
Adresler hex, okuma sayısı ve boş saat sayısı ondalıktır.

## Kullanım

Önce README'deki komutlarla Nano yazılımını derleyip yükle. Yeni sürüm
kimliği `MCULAB_HT66F002_V1`. Port adını kendi bilgisayarına göre değiştir.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python host/assemble.py examples/ht66f002/led_pa1_dimmer.asm --check pwm
.venv/bin/python host/program.py --port PORT_ADI --image examples/ht66f002/led_pa1_dimmer.json --runtime-check
```

Son komut mevcut MCU programını silip yazar. Önce checkpoint alır;
Flash'ın 1024 word'ünü ve seçeneklerini karşılaştırır, EEPROM'un
değişmediğini kontrol eder ve hedefi çalıştırır. `--verify-only` eklemek
belleklere yazmadan karşılaştırır; yine hedef gücü kapatılıp açılır.

Dimmer 8 bit yazılımsal PWM ile parlaklığı otomatik artırıp azaltır.
Nominal 8 MHz'de PWM yaklaşık 1,93 kHz; bütün tarama yaklaşık 4,26 s.
Gerçek hız HIRC toleransına bağlıdır; analog HIRC kalibrasyonu yapılmaz.
Blink ve sürekli açık LED örnekleri de bulunur.

## Paylaşım kapsamı

MIT lisansı kendi kodumuz ve belgelerimiz içindir. Üretici yazılımları,
SDK, kılavuz PDF'leri veya logoları dağıtılmaz. Yayınlanan araçları ve
örnekleri kullanmak için Holtek yazılımı gerekmez.

Holtek adı yalnız desteklenen donanımı belirtir. Projenin Holtek ile
resmî bağlantısı veya Holtek tarafından onaylandığı iddiası yoktur.

Yeni bir çipte aynı yöntemi kullanabiliriz; farklı adres, sayfa, voltaj,
giriş, seçenek ve trim gereksinimleri ayrıca doğrulanmalıdır.
ACK almak, kalıcı yazmayı ve kodun çalışmasını tek başına kanıtlamaz.
