#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

#define DHTPIN 2
#define DHTTYPE DHT11
#define LDR_PIN A0

// Alamat default modul I2C biasanya 0x27 (atau 0x3F untuk beberapa modul)
LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();

  // Inisialisasi LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("IoT Monitor Init");
  lcd.setCursor(0, 1);
  lcd.print("Loading sensor..");
  delay(1500);
  lcd.clear();

  Serial.println("Monitoring dimulai...");
  Serial.println("Suhu | Kelembapan | LDR | Cahaya");
}

// Konstanta konversi Lux sesuai dokumen rencana (R_FIXED = 10k ohm)
const float VCC = 5.0;
const float R_FIXED = 10000.0;
const float LUX_A = 500000.0;
const float LUX_B = 1.0;

void loop() {
  float suhu = dht.readTemperature();
  float kelembapan = dht.readHumidity();
  int nilaiLDR = analogRead(LDR_PIN);

  // Perhitungan persen cahaya untuk kompatibilitas serial
  int persenCahaya = map(nilaiLDR, 0, 1023, 0, 100);
  persenCahaya = constrain(persenCahaya, 0, 100);

  // Perhitungan Estimasi Lux (Vout -> R_LDR -> Lux = A * R_LDR^-B)
  float luxEstimate = 0.0;
  if (nilaiLDR > 0) {
    float vout = (float)nilaiLDR * VCC / 1023.0;
    if (vout > 0.001) {
      float r_ldr = R_FIXED * ((VCC - vout) / vout);
      if (r_ldr > 0.0) {
        luxEstimate = LUX_A * pow(r_ldr, -LUX_B);
      }
    }
  }

  if (isnan(suhu) || isnan(kelembapan)) {
    Serial.println("Gagal membaca DHT11");
    lcd.setCursor(0, 0);
    lcd.print("DHT11 Error!    ");
    lcd.setCursor(0, 1);
    lcd.print("Periksa Kabel   ");
  } else {
    // 1. Kirim data ke Python Web Dashboard (Format Serial tetap)
    Serial.print("Suhu: ");
    Serial.print(suhu);
    Serial.print(" C | ");

    Serial.print("Kelembapan: ");
    Serial.print(kelembapan);
    Serial.print(" % | ");

    Serial.print("LDR: ");
    Serial.print(nilaiLDR);
    Serial.print(" | ");

    Serial.print("Cahaya: ");
    Serial.print(persenCahaya);
    Serial.println(" %");

    // 2. Tampilkan di LCD 1602 (16 kolom x 2 baris)
    // Baris 1: "T:29.2°C H:63% "
    lcd.setCursor(0, 0);
    lcd.print("T:");
    lcd.print(suhu, 1);
    lcd.print((char)223); // Simbol derajat °
    lcd.print("C H:");
    lcd.print((int)kelembapan);
    lcd.print("%   ");

    // Baris 2: "LDR:54 Lux:2.9lx" (Menggunakan rumus estimasi Lux)
    lcd.setCursor(0, 1);
    lcd.print("LDR:");
    lcd.print(nilaiLDR);
    lcd.print(" Lux:");
    if (luxEstimate >= 100.0) {
      lcd.print((int)luxEstimate);
    } else {
      lcd.print(luxEstimate, 1);
    }
    lcd.print("lx   ");
  }

  delay(2000);
}
