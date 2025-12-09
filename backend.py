import os
import subprocess
import sys

class ArduinoGenerator:
    def __init__(self, intermediate_code, output_dir="arduino_build"):
        self.intermediate_code = intermediate_code
        self.output_dir = output_dir
        self.variables = set()       
        self.global_vars = set()     
        self.internal_vars = set()   
        self.arduino_code = ""

    def map_operator(self, op):
        mapping = {
            '==': '==', '!=': '!=', '>': '>', '<': '<', '>=': '>=', '<=': '<=',
            '+': '+', '-': '-', '*': '*', '/': '/',
            'ASSIGN': '=', 'AND': '&&', 'OR': '||'
        }
        return mapping.get(op, op)

    def _clean_and_map(self, arg):
        # Evitar errores con None
        if arg is None: return '""'
        
        clean_arg = arg.split('.')[-1] if '.' in arg else arg
        if clean_arg == "inputPass": return "inputString" 
        if clean_arg == "TIME" or clean_arg == "$TIME": return "getCurrentTime()"
        return clean_arg

    def _analyze_variables(self):
        self.global_vars.clear()
        self.internal_vars.clear()
        self.variables.clear()

        for quad in self.intermediate_code:
            op, arg1, arg2, res = quad
            if op == 'ASSIGN':
                if '.' in res:
                    self.internal_vars.add(res.split('.')[-1])
                elif not res.startswith('t') and res != 'true' and res != 'false':
                    if res != 'inputPass': self.global_vars.add(res)
            if res and res.startswith('t'): self.variables.add(res)

    def get_template_head(self):
        return """
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
VAR_DECLARATIONS

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
"""

    def generate(self, ruta_personalizada=None):
        self._analyze_variables()
        
        # Limpieza de variables duplicadas
        known_internals = {"is_locked", "PASS", "lock_time", "unlock_time", "report_time"}
        self.internal_vars.update(known_internals)
        self.global_vars = self.global_vars - self.internal_vars
        
        code_body = ""
        indent = "  "
        
        # Generación del Loop Principal
        for quad in self.intermediate_code:
            op, arg1, arg2, res = quad
            if op == 'LABEL':
                if res == 'MAIN_LOOP': code_body += f"\n{indent}// BUCLE PRINCIPAL\n"
                else: code_body += f"{res}:\n"
            elif op == 'GOTO':
                if res == 'MAIN_LOOP': code_body += f"{indent}return;\n"
                else: code_body += f"{indent}goto {res};\n"
            elif op == 'IF':
                clean_arg1 = self._clean_and_map(arg1)
                code_body += f"{indent}if ({clean_arg1}) goto {res};\n"
            elif op == 'ASSIGN':
                val = self._clean_and_map(arg1)
                if val == '' or val is None: val = '""'
                target = res.split('.')[-1] if '.' in res else res
                code_body += f"{indent}{target} = {val};\n"
            elif op == 'WAIT_TICK':
                code_body += f"{indent}delay(1000);\n"
            elif op == 'WAIT_INPUT':
                code_body += f"{indent}if (Serial.available() > 0) {{\n"
                code_body += f"{indent}   String rawInput = Serial.readStringUntil('\\n');\n"
                code_body += f"{indent}   processInput(rawInput);\n"
                code_body += f"{indent}}}\n"
            elif op == 'CALL':
                code_body += f"{indent}{res}();\n"
            elif op == 'PRINT':
                val = arg1.replace('"', '')
                if '.' in val: val = val.split('.')[-1]
                code_body += f"{indent}Serial.println({val});\n"
            elif op == 'CHECK':
                 val = self._clean_and_map(arg1)
                 code_body += f"{indent}{res} = {val};\n"
            else:
                cpp_op = self.map_operator(op)
                c_arg1 = self._clean_and_map(arg1)
                c_arg2 = self._clean_and_map(arg2)
                code_body += f"{indent}{res} = ({c_arg1} {cpp_op} {c_arg2});\n"

        # Declaraciones de Variables
        var_decl = ""
        for g_var in sorted(list(self.global_vars)): var_decl += f"String {g_var} = \"\";\n"
        for i_var in sorted(list(self.internal_vars)):
            if i_var == "is_locked": var_decl += f"boolean {i_var} = true;\n"
            else: var_decl += f"String {i_var} = \"\";\n"
        var_decl += "String inputPass = \"\";\nString TIME = \"\";\n"
        for var in sorted(list(self.variables)): var_decl += f"boolean {var} = false;\n"

        # --- FUNCIÓN processInput (CORREGIDA) ---
        process_input_func = """
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
"""
        # Generación Dinámica de IFs
        first = True
        hay_variables_globales = False # Bandera de control

        for g_var in sorted(list(self.global_vars)):
            hay_variables_globales = True
            else_prefix = "else " if not first else ""
            process_input_func += f"""  {else_prefix}if (varName == "{g_var}") {{ {g_var} = varValue; Serial.println("[OK] Global actualizada."); }}\n"""
            first = False
        
        # LÓGICA DE CIERRE SEGURA
        if hay_variables_globales:
            # Si hubo IFs, cerramos con un ELSE
            process_input_func += """  else { Serial.println("[ERROR] Acceso denegado: Variable protegida o inexistente."); }\n}\n"""
        else:
            # Si NO hubo variables, no hubo IFs, por lo tanto NO ponemos ELSE.
            # Simplemente imprimimos error directo porque no hay nada que modificar.
            process_input_func += """  Serial.println("[ERROR] No hay variables globales modificables en este programa.");\n}\n"""

        # Ensamblar Final
        final_ino = self.get_template_head().replace('VAR_DECLARATIONS', var_decl)
        final_ino += process_input_func
        final_ino += "\nvoid setup() {\n  Serial.begin(9600);\n  pinMode(PIN_LOCKED, OUTPUT); pinMode(PIN_UNLOCKED, OUTPUT); pinMode(PIN_MANUAL, INPUT);\n"
        final_ino += "  if (!rtc.begin()) { Serial.println(\"No RTC\"); while(1); }\n  if (!rtc.isrunning()) { rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); }\n"
        final_ino += "  force_lock();\n  Serial.println(\"--- PROLOCK SYSTEM ---\");\n}\n"
        final_ino += "void loop() {\n  if (digitalRead(PIN_MANUAL) == HIGH) { force_unlock(); delay(1000); return; }\n"
        final_ino += code_body
        final_ino += "}\n"

        # Guardado
        if ruta_personalizada:
            ruta_personalizada = os.path.normpath(ruta_personalizada)
            nombre_archivo = os.path.basename(ruta_personalizada)
            nombre_sketch = os.path.splitext(nombre_archivo)[0]
            directorio_padre = os.path.dirname(ruta_personalizada)
            nueva_carpeta = os.path.join(directorio_padre, nombre_sketch)
            os.makedirs(nueva_carpeta, exist_ok=True)
            filepath = os.path.join(nueva_carpeta, nombre_archivo)
        else:
            os.makedirs(self.output_dir, exist_ok=True)
            filepath = os.path.join(self.output_dir, "SmartHome.ino")

        print(f"--- DEBUG: Escribiendo en: {filepath}")
        with open(filepath, "w") as f:
            f.write(final_ino)
        
        return filepath

    def compile_hex(self, ino_path):
        """Compila a HEX mostrando salida en tiempo real."""
        print(f"--- DEBUG: Iniciando Compilación HEX para: {ino_path}")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cli_path = os.path.join(base_dir, "arduino-cli.exe")
        
        if not os.path.exists(cli_path):
            return False, f"CRITICO: No se encuentra 'arduino-cli.exe' en {base_dir}"

        fqbn = "arduino:avr:uno" 
        cmd = [cli_path, "compile", "--fqbn", fqbn, "--export-binaries", ino_path]

        try:
            print("--- DEBUG: Ejecutando arduino-cli...")
            
            # USAMOS POPEN PARA TIEMPO REAL
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            full_log = ""
            for line in process.stdout:
                linea_limpia = line.strip()
                if linea_limpia:
                    print(f"[ARDUINO] {linea_limpia}") # Muestra progreso en consola
                    full_log += line
            
            process.wait()
            
            if process.returncode == 0:
                hex_path = ino_path + ".with_bootloader.hex"
                if not os.path.exists(hex_path):
                     hex_path = ino_path.replace(".ino", ".ino.hex")
                
                # Búsqueda profunda (backup)
                if not os.path.exists(hex_path):
                     build_path = os.path.join(os.path.dirname(ino_path), "build", "arduino.avr.uno", os.path.basename(ino_path) + ".hex")
                     if os.path.exists(build_path): hex_path = build_path

                print(f"--- DEBUG: HEX generado en: {hex_path}")
                return True, f"Compilación Exitosa.\nHEX: {hex_path}"
            else:
                return False, f"Error Arduino CLI:\n{full_log}"

        except Exception as e:
            print(f"--- DEBUG: Excepción Python: {e}")
            return False, f"Error sistema: {e}"