import csv
import math
import re
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request
import serial
from serial.tools import list_ports

app = Flask(__name__)

BAUD_RATE = 9600
MANUAL_PORT = None

VCC = 5.0
R_FIXED_OHMS = 10000.0

# Estimasi kasar. Setelah kalibrasi lux meter, ganti A/B dan ubah flag ke True.
LUX_A = 500000.0
LUX_B = 1.0
LUX_CALIBRATED = False

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
CSV_FILE = DATA_DIR / "sensor_log.csv"
SESSION_START = datetime.now()

latest = {
    "connected": False,
    "port": None,
    "temperature": None,
    "humidity": None,
    "ldr": None,
    "vout": None,
    "ldr_resistance_ohm": None,
    "lux": None,
    "lux_calibrated": LUX_CALIBRATED,
    "timestamp": None,
    "message": "Menunggu koneksi Arduino..."
}
data_lock = threading.Lock()

LINE_PATTERN = re.compile(
    r"Suhu:\s*([0-9.]+)\s*C\s*\|\s*"
    r"Kelembapan:\s*([0-9.]+)\s*%\s*\|\s*"
    r"LDR:\s*(\d+)\s*\|\s*"
    r"Cahaya:\s*(\d+)\s*%"
)

CSV_FIELDS = [
    "timestamp", "temperature_c", "humidity_percent",
    "ldr_adc", "vout_volt", "ldr_resistance_ohm", "lux_estimate"
]

def ensure_csv_header():
    if not CSV_FILE.exists():
        with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()

def adc_to_lux(adc_value):
    adc_value = max(0, min(1023, int(adc_value)))
    if adc_value <= 0:
        return None, None, None

    vout = adc_value * VCC / 1023.0
    if vout <= 0:
        return vout, None, None

    # Wiring: 5V -> LDR -> A0 -> 10k -> GND
    r_ldr = R_FIXED_OHMS * ((VCC - vout) / vout)

    if r_ldr <= 0:
        return vout, r_ldr, None

    lux = LUX_A * (r_ldr ** (-LUX_B))
    if not math.isfinite(lux):
        lux = None

    return vout, r_ldr, lux

def append_csv(row):
    ensure_csv_header()
    with CSV_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow({
            "timestamp": row["timestamp"],
            "temperature_c": row["temperature"],
            "humidity_percent": row["humidity"],
            "ldr_adc": row["ldr"],
            "vout_volt": row["vout"],
            "ldr_resistance_ohm": row["ldr_resistance_ohm"],
            "lux_estimate": row["lux"]
        })

def detect_arduino_port():
    if MANUAL_PORT:
        return MANUAL_PORT

    ports = list(list_ports.comports())
    if not ports:
        return None

    keywords = ("arduino", "ch340", "ch341", "usb serial", "usb-serial", "wch")
    for p in ports:
        desc = (p.description or "").lower()
        if any(k in desc for k in keywords):
            return p.device

    if len(ports) == 1:
        return ports[0].device

    return None

def set_status(**kwargs):
    with data_lock:
        latest.update(kwargs)

def serial_reader():
    while True:
        ser = None
        try:
            port = detect_arduino_port()
            if not port:
                set_status(
                    connected=False,
                    port=None,
                    message="Arduino belum terdeteksi. Pastikan USB terpasang dan Serial Monitor ditutup."
                )
                time.sleep(2)
                continue

            set_status(connected=False, port=port, message=f"Mencoba membuka {port}...")
            ser = serial.Serial(port, BAUD_RATE, timeout=1)
            time.sleep(2)

            set_status(connected=True, port=port, message=f"Terhubung ke {port}")

            while True:
                raw = ser.readline().decode("utf-8", errors="ignore").strip()
                if not raw:
                    continue

                match = LINE_PATTERN.search(raw)
                if not match:
                    continue

                temperature = float(match.group(1))
                humidity = float(match.group(2))
                ldr = int(match.group(3))

                vout, r_ldr, lux = adc_to_lux(ldr)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                row = {
                    "temperature": temperature,
                    "humidity": humidity,
                    "ldr": ldr,
                    "vout": None if vout is None else round(vout, 4),
                    "ldr_resistance_ohm": None if r_ldr is None else round(r_ldr, 2),
                    "lux": None if lux is None else round(lux, 2),
                    "timestamp": timestamp
                }

                with data_lock:
                    latest.update({
                        **row,
                        "connected": True,
                        "port": port,
                        "lux_calibrated": LUX_CALIBRATED,
                        "message": f"Terhubung ke {port}"
                    })

                append_csv(row)

        except serial.SerialException as e:
            set_status(connected=False, message=f"Koneksi serial terputus: {e}")
            time.sleep(2)
        except Exception as e:
            set_status(connected=False, message=f"Error: {e}")
            time.sleep(2)
        finally:
            if ser and ser.is_open:
                try:
                    ser.close()
                except Exception:
                    pass

def parse_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None

def load_csv_rows():
    ensure_csv_header()
    rows = []

    with CSV_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            try:
                ts = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

            rows.append({
                "dt": ts,
                "timestamp": r["timestamp"],
                "temperature": parse_float(r.get("temperature_c")),
                "humidity": parse_float(r.get("humidity_percent")),
                "ldr": parse_float(r.get("ldr_adc")),
                "lux": parse_float(r.get("lux_estimate"))
            })

    return rows

def range_start(range_name):
    now = datetime.now()

    if range_name == "5m":
        return now - timedelta(minutes=5)
    if range_name == "30m":
        return now - timedelta(minutes=30)
    if range_name == "1h":
        return now - timedelta(hours=1)
    if range_name == "24h":
        return now - timedelta(hours=24)

    return SESSION_START

def downsample_average(rows, max_points=600):
    if len(rows) <= max_points:
        return rows

    bucket_size = math.ceil(len(rows) / max_points)
    sampled = []

    for i in range(0, len(rows), bucket_size):
        bucket = rows[i:i + bucket_size]
        mid = bucket[len(bucket) // 2]

        def avg(key):
            vals = [x[key] for x in bucket if x[key] is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        sampled.append({
            "dt": mid["dt"],
            "timestamp": mid["timestamp"],
            "temperature": avg("temperature"),
            "humidity": avg("humidity"),
            "ldr": avg("ldr"),
            "lux": avg("lux")
        })

    return sampled

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def api_data():
    with data_lock:
        return jsonify(dict(latest))

@app.route("/api/history")
def api_history():
    range_name = request.args.get("range", "realtime")
    if range_name not in {"realtime", "5m", "30m", "1h", "24h"}:
        range_name = "realtime"

    rows = load_csv_rows()
    start = range_start(range_name)
    filtered = [r for r in rows if r["dt"] >= start]
    filtered = downsample_average(filtered, max_points=600)

    return jsonify({
        "range": range_name,
        "count": len(filtered),
        "session_start": SESSION_START.strftime("%Y-%m-%d %H:%M:%S"),
        "rows": [{
            "timestamp": r["timestamp"],
            "temperature": r["temperature"],
            "humidity": r["humidity"],
            "ldr": r["ldr"],
            "lux": r["lux"]
        } for r in filtered]
    })

if __name__ == "__main__":
    ensure_csv_header()

    reader_thread = threading.Thread(target=serial_reader, daemon=True)
    reader_thread.start()

    print("=" * 60)
    print("IoT Dashboard Arduino v2")
    print("Buka browser: http://127.0.0.1:5000")
    print("PENTING: tutup Serial Monitor Arduino IDE.")
    print(f"Lux calibrated: {LUX_CALIBRATED}")
    print("=" * 60)

    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
