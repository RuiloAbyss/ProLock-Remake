
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>
#include <Keypad.h>

RTC_DS1307 rtc;
LiquidCrystal lcd(8, 9, 10, 11, 12, 13); 

const byte FILAS = 4; 
const byte COLUMNAS = 3; 
char keys[FILAS][COLUMNAS] = {
  {'1','2','3'},
  {'4','5','6'},
  {'7','8','9'},
  {'*','0','#'}
};
byte pinesFilas[FILAS] = {0, 1, 2, 3};    
byte pinesColumnas[COLUMNAS] = {4, 5, 6}; 
Keypad teclado = Keypad(makeKeymap(keys), pinesFilas, pinesColumnas, FILAS, COLUMNAS);

const int PIN_LOCKED = A0;      
const int PIN_UNLOCKED = A1;    
const int PIN_BTN_OPEN = A2;    
const int PIN_BTN_CLOSE = A3;   
const int PIN_MEMORY = 7; 

const boolean ENABLE_CLOCK = true;
boolean is_locked = true; 
boolean lastLockState = false; 
unsigned long lastClockUpdate = 0; 
boolean necesitaLimpiar = true;
unsigned long messageTimer = 0; 
boolean showingMessage = false;

// Variable para controlar si el usuario esta escribiendo
boolean isTyping = false; 

char entradaArray[5];               
byte indiceArray = 0;

// VARIABLES DEL COMPILADOR
String TIME = "";
String front_door = "";
String inputPass = "";
String PASS = "";
String lock_time = "";
String report_time = "";
String unlock_time = "";
boolean t1 = false;
boolean t2 = false;
boolean t3 = false;


// Prototipos
void limpiarEntrada();
void verificarPassword();
void mostrarEstadoPuerta();
void refreshUI();
void showMessage(String msg, int duration);
void force_lock() { is_locked = true; refreshUI(); }
void force_unlock() { is_locked = false; refreshUI(); } 

// TIEMPO DISPLAY (HH:MM:SS)
String getDisplayTime() {
  DateTime now = rtc.now();
  char buffer[9];
  sprintf(buffer, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(buffer);
}

// TIEMPO LOGICA (HH:MM)
String getLogicTime() {
  DateTime now = rtc.now();
  char buffer[6];
  sprintf(buffer, "%02d:%02d", now.hour(), now.minute());
  return String(buffer);
}

// --- UI TURBO ---
void refreshUI() {
  unsigned long currentMillis = millis();

  // 1. Mensajes Temporales
  if (showingMessage) {
      if (currentMillis >= messageTimer) {
          showingMessage = false; 
          mostrarEstadoPuerta(); 
      }
      return; 
  }

  // 2. Reloj (SOLO SI NO ESTAMOS ESCRIBIENDO)
  // Esto evita que el reloj sobrescriba lo que escribes o bugee el cursor
  if (ENABLE_CLOCK && !isTyping) {
      if (currentMillis - lastClockUpdate >= 125) { 
          lcd.setCursor(0, 0); 
          lcd.print("Hora: " + getDisplayTime());
          lastClockUpdate = currentMillis;
      }
  }

  // 3. LEDs
  if (is_locked) {
      digitalWrite(PIN_LOCKED, HIGH); digitalWrite(PIN_UNLOCKED, LOW);
  } else {
      digitalWrite(PIN_LOCKED, LOW); digitalWrite(PIN_UNLOCKED, HIGH);
  }

  // 4. Estado Base
  if (is_locked != lastLockState && indiceArray == 0 && !isTyping) {
      mostrarEstadoPuerta();
      lastLockState = is_locked;
  }
}

void mostrarEstadoPuerta() {
   lcd.setCursor(0, 1);
   if (is_locked) lcd.print("CERRADO         ");
   else           lcd.print("ABIERTO         ");
   necesitaLimpiar = true; 
}

void showMessage(String msg, int duration) {
    lcd.setCursor(0, 1);
    lcd.print(msg + "                "); 
    showingMessage = true;
    messageTimer = millis() + duration; 
}

// --- KEYPAD ---
void handleKeypad() {
  char tecla = teclado.getKey(); 
  if (tecla) {
    // Si habia un mensaje, quitarlo
    if (showingMessage) { showingMessage = false; mostrarEstadoPuerta(); }
    
    if (tecla == '#') {
      limpiarEntrada();
      showMessage("Cancelado", 200); 
    }
    else if (tecla == '*') {
      if (indiceArray > 0) {
        indiceArray--;           
        entradaArray[indiceArray] = 0;
        lcd.setCursor(indiceArray, 1); lcd.print(" "); lcd.setCursor(indiceArray, 1); 
        
        // Si borro todo, salgo del modo escritura
        if (indiceArray == 0) {
             isTyping = false;
             lcd.setCursor(0,0);
             lcd.print("                "); // Borrar titulo de clave
             refreshUI(); // Forzar actualización inmediata del reloj
        }
        
      } else { 
         limpiarEntrada(); 
         mostrarEstadoPuerta(); 
      }
    }
    else {
        // SI ES UN NÚMERO
        
        // Si es el primer numero, activamos MODO ESCRITURA
        if (!isTyping) {
            isTyping = true;
            lcd.setCursor(0,0);
            lcd.print("CLAVE:          "); // Ocultamos el reloj
        }

      if (necesitaLimpiar) {
          lcd.setCursor(0, 1); lcd.print("                "); lcd.setCursor(0, 1);
          necesitaLimpiar = false;
      }
      if (indiceArray < 4) {
        entradaArray[indiceArray] = tecla; 
        lcd.print(tecla); 
        indiceArray++; 
        if (indiceArray == 4) { entradaArray[4] = '\0'; verificarPassword(); }
      }
    }
  }
}

void limpiarEntrada() { 
    memset(entradaArray, 0, sizeof(entradaArray)); 
    indiceArray = 0; 
    isTyping = false; // Al limpiar, salimos de modo escritura y vuelve el reloj
}

void verificarPassword() {
  if (strcmp(entradaArray, PASS.c_str()) == 0) {
    force_unlock(); showMessage("BIENVENIDO!", 500); 
  } else { showMessage("ERROR CLAVE", 500); }
  limpiarEntrada();
}

void checkInputs() {
  handleKeypad(); 
  if (digitalRead(PIN_MEMORY) == HIGH) {
      showMessage("Leyendo Mem...", 300);
      if (PASS.length() < 5) strcpy(entradaArray, PASS.c_str());
      verificarPassword();
      while(digitalRead(PIN_MEMORY) == HIGH); 
  }
  if (digitalRead(PIN_BTN_OPEN) == HIGH) { force_unlock(); delay(10); }
  if (digitalRead(PIN_BTN_CLOSE) == HIGH) { force_lock(); delay(10); }
}

void smartDelay(unsigned long ms) {
  unsigned long adjusted_ms = ms / 8; if (adjusted_ms < 1) adjusted_ms = 1;
  unsigned long start = millis();
  while (millis() - start < adjusted_ms) { refreshUI(); checkInputs(); }
} 
void processInput(String input) { return; }
void checkLogic() {
  inputPass = "";
  is_locked = true;
  PASS = 1010;
  TIME = "00:00";
  unlock_time = "22:26";
  lock_time = "22:27";

  smartDelay(10);
MAIN_LOOP:
  smartDelay(1000);
  t1 = (getLogicTime() == lock_time);
  if (t1) goto L1;
  goto L2;
L1:
  force_lock();
L2:
  t2 = (getLogicTime() == unlock_time);
  if (t2) goto L3;
  goto L4;
L3:
  force_unlock();
L4:
  smartDelay(100);
  t3 = (PASS == inputPass);
  if (t3) goto L5;
  goto L6;
L5:
  force_unlock();
  is_locked = true;
L6:
  goto MAIN_LOOP;

  return;
}

void setup() {
  lcd.begin(16, 2);
  lcd.print("SISTEMA LISTO"); delay(50); lcd.clear();
  pinMode(A0, OUTPUT); pinMode(A1, OUTPUT);
  pinMode(A2, INPUT); pinMode(A3, INPUT);
  pinMode(7, INPUT);
  if (ENABLE_CLOCK) {
    if (!rtc.begin()) { lcd.setCursor(0,1); lcd.print("ERROR RTC"); }
    if (!rtc.isrunning()) { rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); }
  }
  is_locked = true;
  limpiarEntrada();
  refreshUI();
}

void loop() {
  refreshUI(); 
  checkInputs();
  checkLogic();
}
