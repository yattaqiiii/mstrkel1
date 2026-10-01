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

void loop() {
  float suhu = dht.readTemperature();
  float kelembapan = dht.readHumidity();
  int nilaiLDR = analogRead(LDR_PIN);

  int persenCahaya = map(nilaiLDR, 0, 1023, 0, 100);
  persenCahaya = constrain(persenCahaya, 0, 100);

  if (isnan(suhu) || isnan(kelembapan)) {
    Serial.println("Gagal membaca DHT11");
    lcd.setCursor(0, 0);
    lcd.print("DHT11 Error!    ");
    lcd.setCursor(0, 1);
    lcd.print("Periksa Kabel   ");
  } else {
    // 1. Kirim data ke Python Web Dashboard (Format Tetap)
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
    // Baris 1: "T:29.2C  H:63%"
    lcd.setCursor(0, 0);
    lcd.print("T:");
    lcd.print(suhu, 1);
    lcd.print((char)223); // Simbol derajat °
    lcd.print("C  H:");
    lcd.print((int)kelembapan);
    lcd.print("%   ");

    // Baris 2: "LDR:54  Lux: 5%"
    lcd.setCursor(0, 1);
    lcd.print("LDR:");
    lcd.print(nilaiLDR);
    lcd.print("  Lux:");
    lcd.print(persenCahaya);
    lcd.print("%   ");
  }

  delay(2000);
}
