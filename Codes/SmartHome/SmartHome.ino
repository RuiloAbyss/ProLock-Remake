
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>

RTC_DS1307 rtc;
LiquidCrystal lcd(12, 11, 5, 4, 3, 2); // Pines D4-D7 del LCD a D5-D2 del uC

// --- PINES CORREGIDOS SEGÚN DIAGRAMA PROTEUS ---
const int PIN_LOCKED = A0;      // LED ROJO (D1) -> PC0/A0
const int PIN_UNLOCKED = A1;    // LED VERDE (D2) -> PC1/A1
const int PIN_BTN_OPEN = A2;    // BOTÓN ABRIR (R1) -> PC2/A2
const int PIN_BTN_CLOSE = A3;   // BOTÓN CERRAR (R4) -> PC3/A3

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


// Prototipo de función para el manejo serial (SOLUCIONA EL ERROR 'not declared in this scope')
void processInput(String input); 

// Funciones lógicas simples (DECLARADAS ANTES DE USARSE)
void force_lock() { is_locked = true; refreshUI(); }
void force_unlock() { is_locked = false; refreshUI(); }


String getCurrentTime() {
  // Lógica para obtener la hora del RTC (DS1307)
  DateTime now = rtc.now();
  char buffer[9];
  sprintf(buffer, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(buffer);
}

// --- ACTUALIZADOR DE INTERFAZ ---
void refreshUI() {
  // 1. Actualizar Hora
  String currentTime = getCurrentTime();
  // El tiempo se actualiza cada segundo (WAIT_TICK)
  if (currentTime != lastTimeDisplayed) { 
      lcd.setCursor(0, 0); 
      // Mostramos la hora en la primera línea
      lcd.print("Hora: " + currentTime);
      lastTimeDisplayed = currentTime;
  }

  // 2. Actualizar LEDs y Estado LCD (LED HIGH = Encendido)
  if (is_locked) {
      digitalWrite(PIN_LOCKED, HIGH);
      digitalWrite(PIN_UNLOCKED, LOW);
  } else {
      digitalWrite(PIN_LOCKED, LOW);
      digitalWrite(PIN_UNLOCKED, HIGH);
  }

  // 3. Actualizar mensaje de estado solo si cambia
  if (is_locked != lastLockState) {
      lcd.setCursor(0, 1);
      if (is_locked) lcd.print("CERRADO         ");
      else           lcd.print("ABIERTO         ");
      lastLockState = is_locked;
  }
}

// --- CHEQUEO DE BOTONES (SIN CONDICIONES - FUERZA BRUTA) ---
void checkButtons() {
  // Los botones R1 y R4 están cableados como PULL-DOWN en el diagrama (conectados a VCC a través de la resistencia)
  // Por lo tanto, se leen HIGH cuando se presionan.
  
  // Botón ABRIR (R1)
  if (digitalRead(PIN_BTN_OPEN) == HIGH) {
      Serial.println("[DIAGNOSTICO] Boton ABRIR detectado");
      force_unlock(); // Llama a la acción de apertura
      delay(500);        
  }
  
  // Botón CERRAR (R4)
  if (digitalRead(PIN_BTN_CLOSE) == HIGH) {
      Serial.println("[DIAGNOSTICO] Boton CERRAR detectado");
      force_lock(); // Llama a la acción de cierre
      delay(500);        
  }
}

// --- ESPERA INTELIGENTE ---
void smartDelay(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
      refreshUI();
      checkButtons(); 
      
      // Chequear Terminal
      if (Serial.available() > 0) {
          // Usamos el valor numérico ASCII para evitar errores de escape.
          String raw = Serial.readStringUntil(13); 
          if (Serial.peek() == 10) Serial.read(); 
          processInput(raw);
      }
  }
} 


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
  
  // ASEGÚRATE QUE ESTAS LÍNEAS ESTÉN AQUÍ DENTRO DE processInput:
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
  pinMode(A0, OUTPUT); pinMode(A1, OUTPUT);
  pinMode(A2, INPUT); pinMode(A3, INPUT);
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
