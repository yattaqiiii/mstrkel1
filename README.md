# IoT Dashboard Arduino v2

Fitur:
- suhu DHT11
- kelembapan DHT11
- lux estimasi dari LDR
- filter Real-time / 5 menit / 30 menit / 1 jam / 24 jam
- download PNG per grafik sesuai filter aktif
- penyimpanan CSV
- downsampling grafik agar tetap ringan

## Jalankan

1. Tutup Serial Monitor Arduino IDE.
2. Buka terminal di folder ini.
3. Jalankan:

```bash
pip install -r requirements.txt
python app.py
```

4. Buka:

```text
http://127.0.0.1:5000
```

## Jika COM tidak terdeteksi

Di `app.py` ubah:

```python
MANUAL_PORT = None
```

menjadi contoh:

```python
MANUAL_PORT = "COM5"
```

## Tentang Lux

Wiring diasumsikan:

```text
5V -> LDR -> A0 -> resistor 10k -> GND
```

Perhitungan:

```text
Vout = ADC * 5 / 1023
R_LDR = 10000 * ((5 - Vout) / Vout)
Lux = A * R_LDR^(-B)
```

Default:

```python
LUX_A = 500000.0
LUX_B = 1.0
LUX_CALIBRATED = False
```

Default ini hanya estimasi kasar. Setelah kalibrasi lux meter, ganti A/B dan ubah:

```python
LUX_CALIBRATED = True
```

Data tersimpan di:

```text
data/sensor_log.csv
```
