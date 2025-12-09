
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>

RTC_DS1307 rtc;

// --- NUEVA CONFIGURACIÓN DE PINES (LCD + BOTONES) ---
// LCD: RS=12, E=11, D4=5, D5=4, D6=3, D7=2
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

const int PIN_LOCKED = A0;    // LED ROJO (Pin físico 23)
const int PIN_UNLOCKED = A1;  // LED VERDE (Pin físico 24)
const int PIN_SWITCH_OPEN = A2; // SWITCH ABRIR (Pin físico 25)
const int PIN_BTN_CLOSE = A3;   // BOTÓN CERRAR (Pin físico 26)

String inputString = "";
unsigned long previousMillis = 0;
const long interval = 1000;

// Variables Generadas
String PASS = "";
boolean is_locked = true;
String lock_time = "";
String report_time = "";
String unlock_time = "";
String inputPass = "";
String TIME = "";
boolean t1 = false;


String getCurrentTime() {
  DateTime now = rtc.now();
  char buffer[9];
  sprintf(buffer, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(buffer);
}

void updateLCD(String status) {
  lcd.setCursor(0, 0);
  lcd.print("Hora: " + getCurrentTime());
  lcd.setCursor(0, 1);
  lcd.print(status);
}

void force_lock() {
  digitalWrite(PIN_LOCKED, HIGH);
  digitalWrite(PIN_UNLOCKED, LOW);
  updateLCD("Estado: CERRADO ");
}

void force_unlock() {
  digitalWrite(PIN_LOCKED, LOW);
  digitalWrite(PIN_UNLOCKED, HIGH);
  updateLCD("Estado: ABIERTO ");
}

void processInput(String input) {
  input.trim();
  int separatorIndex = input.indexOf('=');
  if (separatorIndex == -1) {
      inputString = input;
      Serial.println("[INPUT] Recibido: " + inputString);
      lcd.setCursor(0, 1); lcd.print("Pass: " + inputString + "    ");
      return;
  }
  String varName = input.substring(0, separatorIndex);
  String varValue = input.substring(separatorIndex + 1);
  varName.trim(); varValue.trim();
  Serial.println("[ERROR] Sin globales.");
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(50);
  lcd.begin(16, 2);
  lcd.print("PROLOCK SYSTEM");
  pinMode(PIN_LOCKED, OUTPUT); pinMode(PIN_UNLOCKED, OUTPUT);
  pinMode(PIN_SWITCH_OPEN, INPUT); pinMode(PIN_BTN_CLOSE, INPUT);
  if (!rtc.begin()) { lcd.setCursor(0,1); lcd.print("ERROR RTC"); }
  if (!rtc.isrunning()) { rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); }
  force_lock();
}
void loop() {
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
      previousMillis = currentMillis;
      lcd.setCursor(0, 0); lcd.print("Hora: " + getCurrentTime());
  }
  if (digitalRead(PIN_SWITCH_OPEN) == HIGH) {
      force_unlock(); delay(200); return;
  }
  if (digitalRead(PIN_BTN_CLOSE) == HIGH) {
      force_lock(); delay(500); return;
  }
  inputPass = "";
  is_locked = true;
  PASS = 1235;

  // BUCLE PRINCIPAL
  for(int k=0; k<5; k++) { // Espera fragmentada
      if(digitalRead(PIN_SWITCH_OPEN) == HIGH) return;
      if(digitalRead(PIN_BTN_CLOSE) == HIGH) return;
      delay(200);
  }
  if (Serial.available() > 0) {
     String rawInput = Serial.readStringUntil('\r');
     // Limpiar buffer de caracteres extra como \n
     if (Serial.peek() == '\n') Serial.read();
     processInput(rawInput);
  }
  t1 = (PASS == inputString);
  if (t1) goto L1;
  goto L2;
L1:
  force_unlock();
  is_locked = false;
L2:
  return;
}
