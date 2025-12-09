
#include <Wire.h>
#include <RTClib.h> 

RTC_DS1307 rtc;

const int PIN_LOCKED = 13;   
const int PIN_UNLOCKED = 12; 
const int PIN_MANUAL = 8;    

String inputString = "";
boolean stringComplete = false;
boolean manual_override = false;

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
  char buffer[6];
  sprintf(buffer, "%02d:%02d", now.hour(), now.minute());
  return String(buffer);
}

void force_lock() {
  digitalWrite(PIN_LOCKED, HIGH);
  digitalWrite(PIN_UNLOCKED, LOW);
  Serial.println("[ACCION] Puerta BLOQUEADA");
}

void force_unlock() {
  digitalWrite(PIN_LOCKED, LOW);
  digitalWrite(PIN_UNLOCKED, HIGH);
  Serial.println("[ACCION] Puerta DESBLOQUEADA");
}

void processInput(String input) {
  input.trim();
  int separatorIndex = input.indexOf('=');
  
  // Si no hay '=', es una entrada normal (contraseña)
  if (separatorIndex == -1) {
      inputString = input;
      Serial.println("[INPUT] Recibido: " + inputString);
      return;
  }

  // Si hay '=', es un comando de sistema
  String varName = input.substring(0, separatorIndex);
  String varValue = input.substring(separatorIndex + 1);
  varName.trim(); varValue.trim();
  Serial.println("[ERROR] No hay variables globales modificables en este programa.");
}

void setup() {
  Serial.begin(9600);
  pinMode(PIN_LOCKED, OUTPUT); pinMode(PIN_UNLOCKED, OUTPUT); pinMode(PIN_MANUAL, INPUT);
  if (!rtc.begin()) { Serial.println("No RTC"); while(1); }
  if (!rtc.isrunning()) { rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); }
  force_lock();
  Serial.println("--- PROLOCK SYSTEM ---");
}
void loop() {
  if (digitalRead(PIN_MANUAL) == HIGH) { force_unlock(); delay(1000); return; }
  inputPass = "";
  is_locked = true;
  PASS = 1235;

  // BUCLE PRINCIPAL
  delay(1000);
  if (Serial.available() > 0) {
     String rawInput = Serial.readStringUntil('\n');
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
