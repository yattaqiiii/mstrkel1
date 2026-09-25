#include <DHT.h>

#define DHTPIN 7
#define DHTTYPE DHT11
#define LDR_PIN A0

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();

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
  } else {
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
  }

  delay(2000);
}
