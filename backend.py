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
                if '.' in res: self.internal_vars.add(res.split('.')[-1])
                elif not res.startswith('t') and res != 'true' and res != 'false':
                    if res != 'inputPass': self.global_vars.add(res)
            if res and res.startswith('t'): self.variables.add(res)

    def get_template_head(self):
        return """
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>

RTC_DS1307 rtc;

// --- NUEVA CONFIGURACIÓN DE PINES (LCD + BOTONES) ---
// LCD: RS=12, E=11, D4=5, D5=4, D6=3, D7=2
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

const int PIN_LOCKED = A0;    // LED ROJO (Pin físico 23)
const int PIN_UNLOCKED = A1;  // LED VERDE (Pin físico 24)
const int PIN_SWITCH_OPEN = A2; // SWITCH ABRIR (Pin físico 25)
const int PIN_BTN_CLOSE = A3;   // BOTÓN CERRAR (Pin físico 26)

String inputString = "";
unsigned long previousMillis = 0;
const long interval = 1000;

// Variables Generadas
VAR_DECLARATIONS

String getCurrentTime() {
  DateTime now = rtc.now();
  char buffer[9];
  sprintf(buffer, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(buffer);
}

void updateLCD(String status) {
  lcd.setCursor(0, 0);
  lcd.print("Hora: " + getCurrentTime());
  lcd.setCursor(0, 1);
  lcd.print(status);
}

void force_lock() {
  digitalWrite(PIN_LOCKED, HIGH);
  digitalWrite(PIN_UNLOCKED, LOW);
  updateLCD("Estado: CERRADO ");
}

void force_unlock() {
  digitalWrite(PIN_LOCKED, LOW);
  digitalWrite(PIN_UNLOCKED, HIGH);
  updateLCD("Estado: ABIERTO ");
}
"""

    def generate(self, ruta_personalizada=None):
        self._analyze_variables()
        known_internals = {"is_locked", "PASS", "lock_time", "unlock_time", "report_time"}
        self.internal_vars.update(known_internals)
        self.global_vars = self.global_vars - self.internal_vars
        
        code_body = ""
        indent = "  "
        
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
                code_body += f"{indent}for(int k=0; k<5; k++) {{ // Espera fragmentada\n"
                code_body += f"{indent}    if(digitalRead(PIN_SWITCH_OPEN) == HIGH) return;\n"
                code_body += f"{indent}    if(digitalRead(PIN_BTN_CLOSE) == HIGH) return;\n"
                code_body += f"{indent}    delay(200);\n"
                code_body += f"{indent}}}\n"
            elif op == 'WAIT_INPUT':
                code_body += f"{indent}if (Serial.available() > 0) {{\n"
                code_body += f"{indent}   String rawInput = Serial.readStringUntil('\\r');\n" # DETECTAR ENTER CORRECTAMENTE
                code_body += f"{indent}   // Limpiar buffer de caracteres extra como \\n\n"
                code_body += f"{indent}   if (Serial.peek() == '\\n') Serial.read();\n" 
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

        var_decl = ""
        for g_var in sorted(list(self.global_vars)): var_decl += f"String {g_var} = \"\";\n"
        for i_var in sorted(list(self.internal_vars)):
            if i_var == "is_locked": var_decl += f"boolean {i_var} = true;\n"
            else: var_decl += f"String {i_var} = \"\";\n"
        var_decl += "String inputPass = \"\";\nString TIME = \"\";\n"
        for var in sorted(list(self.variables)): var_decl += f"boolean {var} = false;\n"

        process_input_func = """
void processInput(String input) {
  input.trim();
  int separatorIndex = input.indexOf('=');
  if (separatorIndex == -1) {
      inputString = input;
      Serial.println("[INPUT] Recibido: " + inputString);
      lcd.setCursor(0, 1); lcd.print("Pass: " + inputString + "    ");
      return;
  }
  String varName = input.substring(0, separatorIndex);
  String varValue = input.substring(separatorIndex + 1);
  varName.trim(); varValue.trim();
"""
        first = True
        hay_vars = False
        for g_var in sorted(list(self.global_vars)):
            hay_vars = True
            else_prefix = "else " if not first else ""
            process_input_func += f"""  {else_prefix}if (varName == "{g_var}") {{ {g_var} = varValue; Serial.println("[OK] Actualizado."); }}\n"""
            first = False
        
        if hay_vars:
            process_input_func += """  else { Serial.println("[ERROR] Protegido/No existe."); }\n}\n"""
        else:
            process_input_func += """  Serial.println("[ERROR] Sin globales.");\n}\n"""

        final_ino = self.get_template_head().replace('VAR_DECLARATIONS', var_decl)
        final_ino += process_input_func
        final_ino += "\nvoid setup() {\n  Serial.begin(9600);\n  Serial.setTimeout(50);\n"
        final_ino += "  lcd.begin(16, 2);\n  lcd.print(\"PROLOCK SYSTEM\");\n"
        final_ino += "  pinMode(PIN_LOCKED, OUTPUT); pinMode(PIN_UNLOCKED, OUTPUT);\n"
        final_ino += "  pinMode(PIN_SWITCH_OPEN, INPUT); pinMode(PIN_BTN_CLOSE, INPUT);\n"
        final_ino += "  if (!rtc.begin()) { lcd.setCursor(0,1); lcd.print(\"ERROR RTC\"); }\n"
        final_ino += "  if (!rtc.isrunning()) { rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); }\n"
        final_ino += "  force_lock();\n}\n"
        
        final_ino += "void loop() {\n"
        # Actualización de pantalla
        final_ino += "  unsigned long currentMillis = millis();\n"
        final_ino += "  if (currentMillis - previousMillis >= interval) {\n"
        final_ino += "      previousMillis = currentMillis;\n"
        final_ino += "      lcd.setCursor(0, 0); lcd.print(\"Hora: \" + getCurrentTime());\n"
        final_ino += "  }\n"
        
        # Botones Manuales
        final_ino += "  if (digitalRead(PIN_SWITCH_OPEN) == HIGH) {\n"
        final_ino += "      force_unlock(); delay(200); return;\n"
        final_ino += "  }\n"
        final_ino += "  if (digitalRead(PIN_BTN_CLOSE) == HIGH) {\n"
        final_ino += "      force_lock(); delay(500); return;\n"
        final_ino += "  }\n"
        
        final_ino += code_body
        final_ino += "}\n"

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
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cli_path = os.path.join(base_dir, "arduino-cli.exe")
        
        if not os.path.exists(cli_path): return False, "Falta arduino-cli.exe"

        fqbn = "arduino:avr:uno" 
        cmd = [cli_path, "compile", "--fqbn", fqbn, "--export-binaries", ino_path]

        try:
            print("--- DEBUG: Compilando con arduino-cli...")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
            for line in process.stdout:
                if line.strip(): print(f"[ARDUINO] {line.strip()}")
            process.wait()
            
            if process.returncode == 0:
                hex_path = ino_path + ".with_bootloader.hex"
                if not os.path.exists(hex_path): hex_path = ino_path.replace(".ino", ".ino.hex")
                if not os.path.exists(hex_path):
                     build_path = os.path.join(os.path.dirname(ino_path), "build", "arduino.avr.uno", os.path.basename(ino_path) + ".hex")
                     if os.path.exists(build_path): hex_path = build_path
                return True, f"EXITO. HEX: {hex_path}"
            else:
                return False, "Error compilacion"
        except Exception as e:
            return False, f"Error: {e}"