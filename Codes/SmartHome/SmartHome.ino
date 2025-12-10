
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>
#include <Keypad.h>

RTC_DS1307 rtc;

// --- LCD (Puerto B) ---
LiquidCrystal lcd(8, 9, 10, 11, 12, 13); 

// --- KEYPAD (Puerto D) ---
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

// --- PINES ---
const int PIN_LOCKED = A0;      
const int PIN_UNLOCKED = A1;    
const int PIN_BTN_OPEN = A2;    
const int PIN_BTN_CLOSE = A3;   
const int PIN_MEMORY = 7; 

// --- VARIABLES DE SISTEMA ---
const boolean ENABLE_CLOCK = true;
String inputString = "";
boolean lastLockState = false; 
unsigned long lastClockUpdate = 0; 
boolean firstRun = true; 
boolean necesitaLimpiar = true;
unsigned long eventMessageTimer = 0; 
boolean showingEvent = false;

// --- BUFFER DE ENTRADA ---
char entradaArray[5];               
byte indiceArray = 0;

// Variables Generadas por el compilador
String TIME = "";
String front_door = "";
String inputPass = "";
String PASS = "";
boolean is_locked = true;
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
void showEvent(String msg);

// Funciones lógicas
void force_lock() { is_locked = true; refreshUI(); }
void force_unlock() { is_locked = false; refreshUI(); } 

// TIEMPO PARA PANTALLA (HH:MM:SS)
String getDisplayTime() {
  DateTime now = rtc.now();
  char buffer[9];
  sprintf(buffer, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(buffer);
}

// TIEMPO PARA LOGICA (HH:MM) - Para comparar con <22:00>
String getLogicTime() {
  DateTime now = rtc.now();
  char buffer[6];
  sprintf(buffer, "%02d:%02d", now.hour(), now.minute());
  return String(buffer);
}

// --- UI ---
void refreshUI() {
  unsigned long currentMillis = millis();

  // 1. Actualizar Reloj CADA SEGUNDO (1000 ms)
  if (ENABLE_CLOCK) {
      if (firstRun || (currentMillis - lastClockUpdate > 1000)) { 
          lcd.setCursor(0, 0); 
          lcd.print("Hora: " + getDisplayTime());
          lastClockUpdate = currentMillis;
          firstRun = false; 
      }
  }

  // 2. Control de LEDs
  if (is_locked) {
      digitalWrite(PIN_LOCKED, HIGH);
      digitalWrite(PIN_UNLOCKED, LOW);
  } else {
      digitalWrite(PIN_LOCKED, LOW);
      digitalWrite(PIN_UNLOCKED, HIGH);
  }

  // 3. Texto de Estado o Evento
  if (showingEvent) {
      if (currentMillis - eventMessageTimer > 2000) {
          showingEvent = false; 
          mostrarEstadoPuerta(); 
      }
  } 
  else if (is_locked != lastLockState && indiceArray == 0) {
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

void showEvent(String msg) {
    lcd.setCursor(0, 1);
    lcd.print(msg + "                "); 
    showingEvent = true;
    eventMessageTimer = millis();
}

// --- LÓGICA DEL KEYPAD ---
void handleKeypad() {
  char tecla = teclado.getKey(); 

  if (tecla) {
    if (showingEvent) {
        showingEvent = false;
        mostrarEstadoPuerta();
    }
    
    // NOTA: Ya NO reseteamos lastClockUpdate aquí para que el reloj siga corriendo
    // aunque escribas, así se siente más "vivo".

    if (tecla == '#') {
      limpiarEntrada();
      lcd.setCursor(0, 1);
      lcd.print("Cancelado       ");
      delay(500); 
      mostrarEstadoPuerta(); 
    }
    else if (tecla == '*') {
      if (indiceArray > 0) {
        indiceArray--;           
        entradaArray[indiceArray] = 0;
        lcd.setCursor(indiceArray, 1); 
        lcd.print(" ");     
        lcd.setCursor(indiceArray, 1); 
      } else {
         limpiarEntrada();
         mostrarEstadoPuerta();
      }
    }
    else {
      if (necesitaLimpiar) {
          lcd.setCursor(0, 1);
          lcd.print("                "); 
          lcd.setCursor(0, 1);
          necesitaLimpiar = false;
      }

      if (indiceArray < 4) {
        entradaArray[indiceArray] = tecla; 
        lcd.print(tecla); 
        indiceArray++; 
        
        if (indiceArray == 4) {
          entradaArray[4] = '\0'; 
          delay(100);       
          verificarPassword();
        }
      }
    }
  }
}

void limpiarEntrada() {
  memset(entradaArray, 0, sizeof(entradaArray)); 
  indiceArray = 0;                          
}

void verificarPassword() {
  if (strcmp(entradaArray, PASS.c_str()) == 0) {
    lcd.setCursor(0, 1);
    lcd.print("CORRECTO!       ");
    force_unlock(); 
    delay(1000);    
  } else {
    lcd.setCursor(0, 1);
    lcd.print("ERROR CLAVE     ");
    delay(1000);    
  }
  limpiarEntrada();
  mostrarEstadoPuerta(); 
}

void checkInputs() {
  handleKeypad(); 

  if (digitalRead(PIN_MEMORY) == HIGH) {
      lcd.setCursor(0, 1); 
      lcd.print("Leyendo Mem...");
      delay(500); 
      if (PASS.length() < 5) {
         strcpy(entradaArray, PASS.c_str());
      }
      verificarPassword();
      while(digitalRead(PIN_MEMORY) == HIGH); 
  }

  if (digitalRead(PIN_BTN_OPEN) == HIGH) { force_unlock(); delay(200); }
  if (digitalRead(PIN_BTN_CLOSE) == HIGH) { force_lock(); delay(200); }
}

void smartDelay(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
      refreshUI(); 
      checkInputs(); 
  }
} 
void processInput(String input) { return; }
void checkLogic() {
  inputPass = "";
  is_locked = true;
  PASS = 1010;
  TIME = "00:00";
  lock_time = "22:00";
  unlock_time = "07:00";

  smartDelay(10);
MAIN_LOOP:
  smartDelay(100);
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
  lcd.print("SISTEMA LISTO"); delay(100); lcd.clear();
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
  checkInputs();
  checkLogic();
}
