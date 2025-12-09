
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>

RTC_DS1307 rtc;
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

// --- PINES ---
const int PIN_LOCKED = A0;      // LED ROJO
const int PIN_UNLOCKED = A1;    // LED VERDE
const int PIN_BTN_OPEN = A2;    // BOTÓN ABRIR
const int PIN_BTN_CLOSE = A3;   // BOTÓN CERRAR

String inputString = "";
boolean lastLockState = false; 
String lastTimeDisplayed = "";

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

// --- ACTUALIZADOR DE INTERFAZ ---
void refreshUI() {
  // 1. Actualizar Hora
  String currentTime = getCurrentTime();
  if (currentTime != lastTimeDisplayed) {
      lcd.setCursor(0, 0); 
      lcd.print("Hora: " + currentTime);
      lastTimeDisplayed = currentTime;
  }

  // 2. Actualizar LEDs y Estado LCD
  if (is_locked) {
      digitalWrite(PIN_LOCKED, HIGH);
      digitalWrite(PIN_UNLOCKED, LOW);
  } else {
      digitalWrite(PIN_LOCKED, LOW);
      digitalWrite(PIN_UNLOCKED, HIGH);
  }

  if (is_locked != lastLockState) {
      lcd.setCursor(0, 1);
      if (is_locked) lcd.print("CERRADO         ");
      else           lcd.print("ABIERTO         ");
      lastLockState = is_locked;
  }
}

// --- CHEQUEO DE BOTONES (SIN CONDICIONES - FUERZA BRUTA) ---
void checkButtons() {
  // Botón ABRIR
  if (digitalRead(PIN_BTN_OPEN) == HIGH) {
      // Imprimimos SIEMPRE para saber que el botón funciona físicamente
      Serial.println("[DIAGNOSTICO] Boton ABRIR detectado");
      
      is_locked = false; // Forzar estado
      refreshUI();       // Actualizar visuales
      delay(500);        // Pausa para evitar rebote
  }
  
  // Botón CERRAR
  if (digitalRead(PIN_BTN_CLOSE) == HIGH) {
      // Imprimimos SIEMPRE para saber que el botón funciona físicamente
      Serial.println("[DIAGNOSTICO] Boton CERRAR detectado");
      
      is_locked = true;  // Forzar estado
      refreshUI();       // Actualizar visuales
      delay(500);        // Pausa para evitar rebote
  }
}

// --- ESPERA INTELIGENTE ---
void smartDelay(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
      refreshUI();
      checkButtons(); // Revisar botones constantemente
      
      // Chequear Terminal
      if (Serial.available() > 0) {
          String raw = Serial.readStringUntil('\r');
          if (Serial.peek() == '\n') Serial.read();
          processInput(raw);
      }
  }
}

// Funciones lógicas simples
void force_lock() { is_locked = true; refreshUI(); }
void force_unlock() { is_locked = false; refreshUI(); }

void processInput(String input) {
  input.trim();
  int separatorIndex = input.indexOf('=');
  if (separatorIndex == -1) {
      inputString = input;
      Serial.println("[INPUT] Recibido: " + inputString);
      lcd.setCursor(0, 1); lcd.print("Pass: " + inputString + "    ");
      smartDelay(500); 
      return;
  }
  String varName = input.substring(0, separatorIndex);
  String varValue = input.substring(separatorIndex + 1);
  varName.trim(); varValue.trim();
  Serial.println("[ERROR] Sin globales.");
}
void checkLogic() {
  inputPass = "";
  is_locked = false;
  PASS = 1235;

  smartDelay(10);
MAIN_LOOP:
  smartDelay(1000);
  smartDelay(100);
  t1 = (PASS == inputString);
  if (t1) goto L1;
  goto L2;
L1:
  force_unlock();
  is_locked = false;
L2:
  goto MAIN_LOOP;

  return;
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(50);
  lcd.begin(16, 2);
  lcd.print("PROLOCK SYSTEM");
  pinMode(PIN_LOCKED, OUTPUT); pinMode(PIN_UNLOCKED, OUTPUT);
  pinMode(PIN_BTN_OPEN, INPUT); pinMode(PIN_BTN_CLOSE, INPUT);
  if (!rtc.begin()) { lcd.setCursor(0,1); lcd.print("ERROR RTC"); }
  if (!rtc.isrunning()) { rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); }
  is_locked = true;
  refreshUI();
}

void loop() {
  // 1. Revisar Botones Físicos (Prioridad)
  checkButtons();

  // 2. Ejecutar Lógica Automática
  checkLogic();
  
  // 3. Limpieza
  if (inputString != "") inputString = ""; 
}
