
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>
#include <Keypad.h>

RTC_DS1307 rtc;

// --- CONFIGURACIÓN LCD (PUERTO B) ---
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
boolean necesitaLimpiar = true; // Nueva bandera para controlar la UI

// --- LOGICA DE KEYPAD Y ARRAY ---
const char PASS_MAESTRA[] = "1235"; // <--- OJO: Puse 1235 como pediste
char entradaArray[5];               
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
void mostrarEstadoPuerta(); // Nueva función auxiliar

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
  
  if (currentTime != lastTimeDisplayed) { 
      lcd.setCursor(0, 0); 
      lcd.print("Hora: " + currentTime);
      lastTimeDisplayed = currentTime;
  }

  if (is_locked) {
      digitalWrite(PIN_LOCKED, HIGH);
      digitalWrite(PIN_UNLOCKED, LOW);
  } else {
      digitalWrite(PIN_LOCKED, LOW);
      digitalWrite(PIN_UNLOCKED, HIGH);
  }

  // Solo actualizamos el texto de estado si NO estamos escribiendo una clave
  if (is_locked != lastLockState && indiceArray == 0) {
      mostrarEstadoPuerta();
      lastLockState = is_locked;
  }
}

void mostrarEstadoPuerta() {
   lcd.setCursor(0, 1);
   if (is_locked) lcd.print("CERRADO         ");
   else           lcd.print("ABIERTO         ");
   necesitaLimpiar = true; // Prepara para borrar cuando se toque una tecla
}

// --- LÓGICA DEL KEYPAD (Array) ---
void handleKeypad() {
  char tecla = teclado.getKey();

  if (tecla) {
    // CASO 1: BORRAR TODO (#)
    if (tecla == '#') {
      limpiarEntrada();
      lcd.setCursor(0, 1);
      lcd.print("Cancelado       "); // Mensaje temporal
      delay(500); // Breve pausa
      mostrarEstadoPuerta(); // Regresar a estado original
    }
    
    // CASO 2: RETROCESO (*)
    else if (tecla == '*') {
      if (indiceArray > 0) {
        indiceArray--;           
        entradaArray[indiceArray] = 0;
        lcd.setCursor(indiceArray, 1); 
        lcd.print(" ");     
        lcd.setCursor(indiceArray, 1); 
      } else {
         // Si borramos todo, volver a mostrar el estado "CERRADO/ABIERTO"
         limpiarEntrada();
         mostrarEstadoPuerta();
      }
    }
    
    // CASO 3: NÚMEROS
    else {
      // Si es el PRIMER número y venimos de mostrar "CERRADO", limpiamos la línea
      if (necesitaLimpiar) {
          lcd.setCursor(0, 1);
          lcd.print("                "); // Borrado visual completo
          lcd.setCursor(0, 1);
          necesitaLimpiar = false;
      }

      if (indiceArray < 4) {
        entradaArray[indiceArray] = tecla; 
        lcd.print(tecla); // Mostrar numero
        indiceArray++; 
        
        // AUTO-VALIDACIÓN
        if (indiceArray == 4) {
          entradaArray[4] = '\0'; 
          delay(100); // Pausa mínima para ver el último número      
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
    force_unlock(); // Cambia is_locked a false
    delay(1000);    // 1 segundo solamente
  } else {
    lcd.setCursor(0, 1);
    lcd.print("ERROR CLAVE     ");
    delay(1000);    // 1 segundo de castigo
  }
  
  // Restaurar la UI
  limpiarEntrada();
  mostrarEstadoPuerta(); // Volver a poner "CERRADO/ABIERTO"
}


// --- CHEQUEO DE HARDWARE ---
void checkInputs() {
  handleKeypad(); 

  // Lector de Memoria (Simulado)
  if (digitalRead(PIN_MEMORY) == HIGH) {
      lcd.setCursor(0, 1); 
      lcd.print("Leyendo Mem...");
      delay(500); 
      // Inyectamos la contraseña maestra correcta
      strcpy(entradaArray, PASS_MAESTRA); 
      verificarPassword();
      while(digitalRead(PIN_MEMORY) == HIGH); 
  }

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
