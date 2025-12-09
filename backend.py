import os

class ArduinoGenerator:
    def __init__(self, intermediate_code, output_dir="arduino_build"):
        self.intermediate_code = intermediate_code
        self.output_dir = output_dir
        self.variables = set() # Para declarar variables globales en C++
        self.arduino_code = ""

    def map_operator(self, op):
        """Traduce operadores de C3D a C++."""
        mapping = {
            '==': '==', '!=': '!=', '>': '>', '<': '<', '>=': '>=', '<=': '<=',
            '+': '+', '-': '-', '*': '*', '/': '/',
            'ASSIGN': '=', 'AND': '&&', 'OR': '||'
        }
        return mapping.get(op, op)

    def get_arduino_template(self):
        """Plantilla base del código Arduino (Setup y configuración)."""
        return """
#include <Wire.h>
#include <RTClib.h>

RTC_DS1307 rtc;
String inputString = "";
boolean stringComplete = false;

// Definición de Pines
const int PIN_LOCKED = 13;   // LED Rojo
const int PIN_UNLOCKED = 12; // LED Verde
const int PIN_MANUAL = 8;    // Interruptor Manual

// Variables del Sistema (Generadas)
VAR_DECLARATIONS

// Funciones Auxiliares
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

void setup() {
  Serial.begin(9600);
  pinMode(PIN_LOCKED, OUTPUT);
  pinMode(PIN_UNLOCKED, OUTPUT);
  pinMode(PIN_MANUAL, INPUT);
  
  if (!rtc.begin()) {
    Serial.println("No se encontro RTC");
    while (1);
  }
  if (!rtc.isrunning()) {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }
  
  // Estado inicial
  force_lock();
  Serial.println("--- Sistema ProLock Iniciado ---");
}

void loop() {
  // Bucle Principal generado por el Compilador
  
  /* CÓDIGO GENERADO A PARTIR DE AQUÍ */
"""

    def generate(self):
        code_body = ""
        indent = "  "
        
        # 1. Primera pasada: Detectar variables para declararlas
        for quad in self.intermediate_code:
            op, arg1, arg2, res = quad
            # Si el resultado es una temporal (t1...) o variable, la registramos
            if res and not res.startswith('L') and op != 'LABEL' and op != 'GOTO' and op != 'IF':
                 # Filtramos miembros de objetos (ej. main_clock.TIME)
                if '.' not in res: 
                    self.variables.add(res)

        # 2. Generar cuerpo del loop
        for quad in self.intermediate_code:
            op, arg1, arg2, res = quad
            
            # --- TRADUCCIÓN DE INSTRUCCIONES ---
            
            if op == 'LABEL':
                if res == 'MAIN_LOOP': 
                    code_body += f"\n{indent}// Inicio del ciclo principal\n"
                else:
                    code_body += f"{res}:\n"
            
            elif op == 'GOTO':
                # En C++ goto funciona igual, pero Arduino loop() ya es un ciclo.
                # Si va a MAIN_LOOP, usamos 'return' para que loop() reinicie.
                if res == 'MAIN_LOOP':
                    code_body += f"{indent}return;\n"
                else:
                    code_body += f"{indent}goto {res};\n"

            elif op == 'IF':
                # IF t1 GOTO L1 -> if (t1) goto L1;
                code_body += f"{indent}if ({arg1}) goto {res};\n"

            elif op == 'ASSIGN':
                # Manejo especial para lecturas de Hardware simuladas
                if arg1 == 'true': arg1 = 'true'
                elif arg1 == 'false': arg1 = 'false'
                
                # Mapeo de objetos del lenguaje a funciones de Arduino
                if 'main_clock.TIME' in str(arg1): arg1 = 'getCurrentTime()'
                if 'front_door.PASS' in str(arg1): arg1 = 'inputString' # Lo que se escribió en el teclado
                
                # Limpiar nombres de objetos para C++ (ej. front_door.is_locked -> is_locked)
                clean_res = res.split('.')[-1] if '.' in res else res
                
                # Declarar si es asignación directa
                code_body += f"{indent}{clean_res} = {arg1};\n"

            elif op == 'WAIT_TICK':
                # Simular espera de 1 segundo (Tick del reloj)
                code_body += f"{indent}delay(1000); // WAIT_TICK (Sincronizacion de reloj)\n"

            elif op == 'WAIT_INPUT':
                # Esperar entrada serial (simulando espera de input QWERTY)
                code_body += f"{indent}// WAIT_INPUT: Revisar buffer serial sin bloquear todo el flujo\n"
                code_body += f"{indent}if (Serial.available() > 0) {{\n"
                code_body += f"{indent}   inputString = Serial.readStringUntil('\\n');\n"
                code_body += f"{indent}   inputString.trim();\n"
                code_body += f"{indent}   Serial.print(\"Entrada recibida: \"); Serial.println(inputString);\n"
                code_body += f"{indent}}}\n"

            elif op == 'CALL':
                # Llamadas a funciones nativas (force_lock, etc)
                func_name = res
                code_body += f"{indent}{func_name}();\n"

            elif op == 'PRINT':
                # Salida a consola serial
                val = arg1.replace('"', '') # Quitar comillas extra
                if '.' in val: # Si es una variable de objeto
                     val = val.split('.')[-1]
                code_body += f"{indent}Serial.println({val});\n"
            
            elif op == 'CHECK':
                 # CHECK main_clock.TIME -> t1
                 # Esto se resuelve mayormente en ASSIGN, pero si aparece:
                 val = arg1
                 if 'main_clock.TIME' in val: val = 'getCurrentTime()'
                 code_body += f"{indent}{res} = {val};\n"

            else:
                # Operaciones binarias (==, +, etc)
                cpp_op = self.map_operator(op)
                
                # Limpieza de argumentos
                c_arg1 = arg1.split('.')[-1] if '.' in arg1 else arg1
                c_arg2 = arg2.split('.')[-1] if '.' in arg2 else arg2
                
                code_body += f"{indent}{res} = ({c_arg1} {cpp_op} {c_arg2});\n"

        # 3. Ensamblar todo
        var_decl_str = ""
        for var in self.variables:
            # Inferencia de tipos muy básica para C++
            ctype = "String" 
            if var.startswith('t'): ctype = "boolean" # Temporales lógicas suelen ser bool
            var_decl_str += f"{ctype} {var};\n"
        
        # Variables de estado fijas que sabemos que existen por el código fuente
        var_decl_str += "boolean is_locked = true;\n"
        var_decl_str += "String PASS = \"my_secret_key\";\n"
        var_decl_str += "String lock_time = \"22:00\";\n"
        var_decl_str += "String unlock_time = \"07:00\";\n"
        var_decl_str += "String report_time = \"08:00\";\n"
        var_decl_str += "String inputPass = \"\";\n" # Variable global para input

        final_code = self.get_arduino_template().replace('VAR_DECLARATIONS', var_decl_str)
        final_code += code_body
        final_code += "}\n" # Cerrar loop
        
        # 4. Guardar archivo
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, "SmartHome.ino")
        with open(filepath, "w") as f:
            f.write(final_code)
        
        return filepath