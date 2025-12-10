
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>
#include <Keypad.h>

RTC_DS1307 rtc;

// --- CONFIGURACIÓN LCD (PUERTO B) ---
// RS=8, E=9, D4=10, D5=11, D6=12, D7=13
LiquidCrystal lcd(8, 9, 10, 11, 12, 13); 

// --- CONFIGURACIÓN KEYPAD (PUERTO D) ---
const byte FILAS = 4; 
const byte COLUMNAS = 3; 
char keys[FILAS][COLUMNAS] = {
  {'1','2','3'},
  {'4','5','6'},
  {'7','8','9'},
  {'*','0','#'}
};
// Pines: D0, D1, D2, D3 (Filas) - D4, D5, D6 (Columnas)
byte pinesFilas[FILAS] = {0, 1, 2, 3};    
byte pinesColumnas[COLUMNAS] = {4, 5, 6}; 

Keypad teclado = Keypad(makeKeymap(keys), pinesFilas, pinesColumnas, FILAS, COLUMNAS);

// --- PINES DE PERIFÉRICOS ---
const int PIN_LOCKED = A0;      
const int PIN_UNLOCKED = A1;    
const int PIN_BTN_OPEN = A2;    
const int PIN_BTN_CLOSE = A3;   
const int PIN_MEMORY = 7; 

// --- VARIABLES DEL SISTEMA ---
String inputString = "";
boolean lastLockState = false; 
String lastTimeDisplayed = "";

// --- LOGICA DE KEYPAD Y ARRAY ---
const char PASS_MAESTRA[] = "1234"; // Contraseña Hardcodeada en Arduino
char entradaArray[5];               // Buffer para 4 digitos + NULL
byte indiceArray = 0;

// Variables Generadas por el compilador
String front_door = "";
String inputPass = "";
String PASS = "";
boolean is_locked = true;
String lock_time = "";
String report_time = "";
String unlock_time = "";
String TIME = "";
boolean t1 = false;


// Prototipos
void processInput(String input); 
void limpiarEntrada();
void verificarPassword();

// Funciones lógicas simples
void force_lock() { is_locked = true; refreshUI(); }
void force_unlock() { is_locked = false; refreshUI(); } 

String getCurrentTime() {
  DateTime now = rtc.now();
  char buffer[9];
  sprintf(buffer, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(buffer);
}

// --- UI ---
void refreshUI() {
  String currentTime = getCurrentTime();
  
  // Actualizar hora solo si cambió (Línea 0)
  if (currentTime != lastTimeDisplayed) { 
      lcd.setCursor(0, 0); 
      lcd.print("Hora: " + currentTime);
      lastTimeDisplayed = currentTime;
  }

  // Control de LEDs
  if (is_locked) {
      digitalWrite(PIN_LOCKED, HIGH);
      digitalWrite(PIN_UNLOCKED, LOW);
  } else {
      digitalWrite(PIN_LOCKED, LOW);
      digitalWrite(PIN_UNLOCKED, HIGH);
  }

  // Actualizar estado en LCD (Línea 1, parte derecha) si cambió
  if (is_locked != lastLockState) {
       // No borramos toda la linea para no borrar lo que el usuario escribe
       // Solo actualizamos si no se está escribiendo nada
       if (indiceArray == 0) {
          lcd.setCursor(0, 1);
          if (is_locked) lcd.print("CERRADO         ");
          else           lcd.print("ABIERTO         ");
       }
      lastLockState = is_locked;
  }
}

// --- LÓGICA DEL KEYPAD (Array) ---
void handleKeypad() {
  char tecla = teclado.getKey();

  if (tecla) {
    // CASO 1: BORRAR TODO (#)
    if (tecla == '#') {
      limpiarEntrada();
      lcd.setCursor(0, 1);
      lcd.print("Borrado...      ");
      delay(500);
      lcd.setCursor(0, 1);
      if (is_locked) lcd.print("CERRADO         ");
      else           lcd.print("ABIERTO         ");
    }
    
    // CASO 2: RETROCESO (*)
    else if (tecla == '*') {
      if (indiceArray > 0) {
        indiceArray--;           
        entradaArray[indiceArray] = 0;
        
        // Efecto visual de borrar caracter
        lcd.setCursor(indiceArray, 1); 
        lcd.print(" ");     
        lcd.setCursor(indiceArray, 1); 
      }
    }
    
    // CASO 3: NÚMEROS
    else {
      if (indiceArray < 4) {
        entradaArray[indiceArray] = tecla; 
        
        // Mostrar asterisco o numero (Visual)
        lcd.setCursor(indiceArray, 1); 
        lcd.print(tecla);        
        
        indiceArray++; 
        
        // AUTO-VALIDACIÓN AL LLEGAR A 4
        if (indiceArray == 4) {
          entradaArray[4] = '\0'; 
          delay(200);        
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
  // Compara el array escrito con la maestra
  if (strcmp(entradaArray, PASS_MAESTRA) == 0) {
    lcd.setCursor(0, 1);
    lcd.print("CORRECTO!       ");
    force_unlock(); // Cambia la variable global is_locked
    delay(1500);
  } else {
    lcd.setCursor(0, 1);
    lcd.print("ERROR CLAVE     ");
    delay(1500);
  }
  
  // Restaurar la UI
  limpiarEntrada();
  lcd.setCursor(0, 1);
  if (is_locked) lcd.print("CERRADO         ");
  else           lcd.print("ABIERTO         ");
}


// --- CHEQUEO DE HARDWARE ---
void checkInputs() {
  
  handleKeypad(); // Revisar el teclado en cada ciclo

  // Lector de Memoria (Pin 7)
  if (digitalRead(PIN_MEMORY) == HIGH) {
      lcd.setCursor(0, 1); 
      lcd.print("Leyendo Mem...");
      delay(800); 
      // Inyectamos contraseña maestra via software
      strcpy(entradaArray, "1234");
      verificarPassword();
      while(digitalRead(PIN_MEMORY) == HIGH); 
  }

  // Botones Físicos (Manuales)
  if (digitalRead(PIN_BTN_OPEN) == HIGH) {
      force_unlock();
      delay(200);        
  }
  
  if (digitalRead(PIN_BTN_CLOSE) == HIGH) {
      force_lock(); 
      delay(200);        
  }
}

// --- ESPERA INTELIGENTE ---
void smartDelay(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
      refreshUI();
      checkInputs(); 
      // (Nota: Se eliminó Serial para liberar Pines 0 y 1 para el Keypad)
  }
} 
void processInput(String input) { return; }
void checkLogic() {
  inputPass = "";
  is_locked = false;
  PASS = 1235;

  smartDelay(10);
MAIN_LOOP:
  smartDelay(1000);
  smartDelay(100);
  t1 = (PASS == inputPass);
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
  lcd.begin(16, 2);
  lcd.print("SISTEMA LISTO"); delay(1000); lcd.clear();
  pinMode(A0, OUTPUT); pinMode(A1, OUTPUT);
  pinMode(A2, INPUT); pinMode(A3, INPUT);
  pinMode(7, INPUT);
  if (!rtc.begin()) { lcd.setCursor(0,1); lcd.print("ERROR RTC"); }
  if (!rtc.isrunning()) { rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); }
  is_locked = true;
  limpiarEntrada();
  refreshUI();
}

void loop() {
  checkInputs();
  checkLogic();
}
