import os

class ArduinoGenerator:
    def __init__(self, intermediate_code, output_dir="arduino_build"):
        self.intermediate_code = intermediate_code
        self.output_dir = output_dir
        self.variables = set() 
        self.arduino_code = ""

    def map_operator(self, op):
        """Traduce operadores de C3D a C++."""
        mapping = {
            '==': '==', '!=': '!=', '>': '>', '<': '<', '>=': '>=', '<=': '<=',
            '+': '+', '-': '-', '*': '*', '/': '/',
            'ASSIGN': '=', 'AND': '&&', 'OR': '||'
        }
        return mapping.get(op, op)

    def get_header(self):
        return """
#include <Wire.h>
#include <RTClib.h> // Necesitas instalar esta libreria en Arduino IDE o agregarla en Proteus

RTC_DS1307 rtc;

// --- CONFIGURACIÓN DE PINES ---
const int PIN_LOCKED = 13;   // LED Rojo
const int PIN_UNLOCKED = 12; // LED Verde
const int PIN_MANUAL = 8;    // Interruptor Manual de Emergencia

// Variables Globales del Sistema
String inputString = "";
boolean stringComplete = false;
boolean manual_override = false;

// Variables Generadas por el Compilador
VAR_DECLARATIONS

// --- FUNCIONES AUXILIARES ---

// Obtener hora actual en formato "HH:MM"
String getCurrentTime() {
  DateTime now = rtc.now();
  char buffer[6];
  sprintf(buffer, "%02d:%02d", now.hour(), now.minute());
  return String(buffer);
}

// Acciones de la Cerradura
void force_lock() {
  digitalWrite(PIN_LOCKED, HIGH);
  digitalWrite(PIN_UNLOCKED, LOW);
  Serial.println("[ACCION] Puerta BLOQUEADA (LED ROJO)");
}

void force_unlock() {
  digitalWrite(PIN_LOCKED, LOW);
  digitalWrite(PIN_UNLOCKED, HIGH);
  Serial.println("[ACCION] Puerta DESBLOQUEADA (LED VERDE)");
}

void setup() {
  Serial.begin(9600); // Comunicación Serial para el Teclado
  
  pinMode(PIN_LOCKED, OUTPUT);
  pinMode(PIN_UNLOCKED, OUTPUT);
  pinMode(PIN_MANUAL, INPUT); // Botón con resistencia Pull-Down
  
  if (!rtc.begin()) {
    Serial.println("No se encontro RTC");
    while (1);
  }
  
  if (!rtc.isrunning()) {
    Serial.println("RTC no esta corriendo, ajustando hora...");
    // Ajustar a la fecha y hora de compilación
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  // Estado Inicial
  force_lock();
  Serial.println("--- SISTEMA PROLOCK INICIADO ---");
  Serial.println("Escriba la contraseña en el Terminal Virtual...");
}

void loop() {
  // 1. Revisar Interruptor Manual (Prioridad Alta)
  if (digitalRead(PIN_MANUAL) == HIGH) {
      Serial.println("[MANUAL] Interruptor activado: Abriendo puerta...");
      force_unlock();
      delay(1000);
      return; // Saltar el resto del ciclo
  }

  // 2. Lógica Generada por el Compilador
  /* INICIO DE CODIGO COMPILADO */
"""

    def generate(self, ruta_personalizada=None):
        code_body = ""
        indent = "  "
        
        # 1. Detectar variables temporales para declararlas
        for quad in self.intermediate_code:
            op, arg1, arg2, res = quad
            if res and res.startswith('t'): 
                 self.variables.add(res)

        # 2. Traducir Cuádruplos a C++
        for quad in self.intermediate_code:
            op, arg1, arg2, res = quad
            
            if op == 'LABEL':
                if res == 'MAIN_LOOP': 
                    code_body += f"\n{indent}// --- BUCLE PRINCIPAL ---\n"
                else:
                    code_body += f"{res}:\n"
            
            elif op == 'GOTO':
                if res == 'MAIN_LOOP':
                    code_body += f"{indent}return; // Reiniciar loop() de Arduino\n"
                else:
                    code_body += f"{indent}goto {res};\n"

            elif op == 'IF':
                # IF t1 GOTO L1
                code_body += f"{indent}if ({arg1}) goto {res};\n"

            elif op == 'ASSIGN':
                # Mapeo de valores especiales
                val = arg1
                if 'main_clock.TIME' in str(arg1): val = 'getCurrentTime()'
                if 'front_door.PASS' in str(arg1): val = 'inputString'
                
                # Limpiar nombres de objetos (front_door.is_locked -> is_locked)
                target = res.split('.')[-1] if '.' in res else res
                
                code_body += f"{indent}{target} = {val};\n"

            elif op == 'WAIT_TICK':
                code_body += f"{indent}delay(1000); // Esperar 1 segundo\n"

            elif op == 'WAIT_INPUT':
                # Lógica no bloqueante para leer del puerto serial
                code_body += f"{indent}if (Serial.available() > 0) {{\n"
                code_body += f"{indent}   inputString = Serial.readStringUntil('\\n');\n"
                code_body += f"{indent}   inputString.trim(); // Quitar espacios extra\n"
                code_body += f"{indent}   Serial.print(\"Input recibido: \"); Serial.println(inputString);\n"
                code_body += f"{indent}}}\n"

            elif op == 'CALL':
                code_body += f"{indent}{res}();\n"

            elif op == 'PRINT':
                val = arg1.replace('"', '')
                if '.' in val: val = val.split('.')[-1]
                code_body += f"{indent}Serial.println({val});\n"
            
            elif op == 'CHECK':
                 # Usado para actualizar valores antes de comparar
                 val = arg1
                 if 'main_clock.TIME' in str(arg1): val = 'getCurrentTime()'
                 code_body += f"{indent}{res} = {val};\n"

            else:
                # Operaciones binarias (==, !=, etc)
                cpp_op = self.map_operator(op)
                # Limpiar argumentos (quitar nombres de objetos)
                c_arg1 = arg1.split('.')[-1] if '.' in arg1 else arg1
                c_arg2 = arg2.split('.')[-1] if '.' in arg2 else arg2
                
                # Manejo de Strings en C++
                code_body += f"{indent}{res} = ({c_arg1} {cpp_op} {c_arg2});\n"

        # 3. Construir Declaraciones de Variables
        var_decl = ""
        
        # Variables temporales (t1, t2...)
        for var in sorted(list(self.variables)):
             var_decl += f"boolean {var} = false;\n"

        # 4. Ensamblar Archivo Final (AQUÍ ESTABA EL ERROR, AHORA SÍ DEFINIMOS final_ino)
        final_ino = self.get_header().replace('VAR_DECLARATIONS', var_decl)
        final_ino += code_body
        final_ino += "}\n"

        # 5. Guardar
        if ruta_personalizada:
            filepath = ruta_personalizada
        else:
            os.makedirs(self.output_dir, exist_ok=True)
            filepath = os.path.join(self.output_dir, "SmartHome.ino")

        with open(filepath, "w") as f:
            f.write(final_ino)
        
        return filepath