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
VAR_DECLARATIONS

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
          String raw = Serial.readStringUntil('\\r');
          if (Serial.peek() == '\\n') Serial.read();
          processInput(raw);
      }
  }
}

// Funciones lógicas simples
void force_lock() { is_locked = true; refreshUI(); }
void force_unlock() { is_locked = false; refreshUI(); }
"""

    def generate(self, ruta_personalizada=None):
        self._analyze_variables()
        known_internals = {"is_locked", "PASS", "lock_time", "unlock_time", "report_time"}
        self.internal_vars.update(known_internals)
        self.global_vars = self.global_vars - self.internal_vars
        
        # --- GENERACIÓN DE LÓGICA ---
        logic_body = "void checkLogic() {\n"
        indent = "  "
        for quad in self.intermediate_code:
            op, arg1, arg2, res = quad
            
            if op == 'LABEL':
                if res == 'MAIN_LOOP': logic_body += f"\n{indent}smartDelay(10);\n{res}:\n"
                else: logic_body += f"{res}:\n"
            elif op == 'GOTO':
                logic_body += f"{indent}goto {res};\n"
            elif op == 'IF':
                clean_arg1 = self._clean_and_map(arg1)
                logic_body += f"{indent}if ({clean_arg1}) goto {res};\n"
            elif op == 'ASSIGN':
                val = self._clean_and_map(arg1)
                if val == '' or val is None: val = '""'
                target = res.split('.')[-1] if '.' in res else res
                logic_body += f"{indent}{target} = {val};\n"
            
            # --- USO DE SMART DELAY ---
            elif op == 'WAIT_TICK':
                logic_body += f"{indent}smartDelay(1000);\n"
            elif op == 'WAIT_INPUT':
                logic_body += f"{indent}smartDelay(100);\n"

            elif op == 'CALL': logic_body += f"{indent}{res}();\n"
            elif op == 'CHECK':
                 val = self._clean_and_map(arg1)
                 logic_body += f"{indent}{res} = {val};\n"
            elif op == 'PRINT':
                val = arg1.replace('"', '')
                if '.' in val: val = val.split('.')[-1]
                logic_body += f"{indent}Serial.println({val});\n"
            else:
                cpp_op = self.map_operator(op)
                c_arg1 = self._clean_and_map(arg1)
                c_arg2 = self._clean_and_map(arg2)
                logic_body += f"{indent}{res} = ({c_arg1} {cpp_op} {c_arg2});\n"
        
        logic_body += "\n  return;\n}\n"

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
      smartDelay(500); 
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
        if hay_vars: process_input_func += """  else { Serial.println("[ERROR] Protegido."); }\n}\n"""
        else: process_input_func += """  Serial.println("[ERROR] Sin globales.");\n}\n"""

        final_ino = self.get_template_head().replace('VAR_DECLARATIONS', var_decl)
        final_ino += process_input_func
        final_ino += logic_body
        
        final_ino += "\nvoid setup() {\n  Serial.begin(9600);\n  Serial.setTimeout(50);\n"
        final_ino += "  lcd.begin(16, 2);\n  lcd.print(\"PROLOCK SYSTEM\");\n"
        final_ino += "  pinMode(PIN_LOCKED, OUTPUT); pinMode(PIN_UNLOCKED, OUTPUT);\n"
        final_ino += "  pinMode(PIN_BTN_OPEN, INPUT); pinMode(PIN_BTN_CLOSE, INPUT);\n"
        final_ino += "  if (!rtc.begin()) { lcd.setCursor(0,1); lcd.print(\"ERROR RTC\"); }\n"
        final_ino += "  if (!rtc.isrunning()) { rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); }\n"
        final_ino += "  is_locked = true;\n  refreshUI();\n}\n"
        
        # --- LOOP PRINCIPAL ESTABLE ---
        final_ino += """
void loop() {
  // 1. Revisar Botones Físicos (Prioridad)
  checkButtons();

  // 2. Ejecutar Lógica Automática
  checkLogic();
  
  // 3. Limpieza
  if (inputString != "") inputString = ""; 
}
"""
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
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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
            else: return False, "Error compilacion"
        except Exception as e: return False, f"Error: {e}"