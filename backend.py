import os
import subprocess
import sys

# === CONFIGURACIÓN DE PINES CORREGIDA BASADA EN EL DIAGRAMA ===
# U1 (DS1307) usa A4 (SDA) y A5 (SCL) automáticamente con la librería Wire/RTClib.
# El LCD está bien cableado, PERO tus LEDs y Botones están en los pines analógicos.
# El mapeo de pines analógicos en Arduino es A0, A1, A2, A3, etc.
PIN_LOCKED_CORRECT = 14  # Pin D0 (PD0/RXD) <-- El pin 14 es el PC0/ADC0. Mejor usar A0 si están en A
PIN_UNLOCKED_CORRECT = 15 # Pin D1 (PD1/TXD) <-- El pin 15 es el PC1/ADC1. Mejor usar A1
PIN_BTN_OPEN_CORRECT = 16 # Pin D2 (PD2/INT0) <-- El pin 16 es el PC2/ADC2. Mejor usar A2
PIN_BTN_CLOSE_CORRECT = 17 # Pin D3 (PD3/INT1) <-- El pin 17 es el PC3/ADC3. Mejor usar A3

# Nota sobre el diagrama: Los pines 23-26 del ATmega328P son PC0-PC3. 
# En Arduino IDE, estos se nombran A0, A1, A2, A3. Usaremos A0-A3 para mayor claridad.
# LED_ROJO (D1) va a PC0 (Pin 23) -> A0
# LED_VERDE (D2) va a PC1 (Pin 24) -> A1
# BOTÓN CERRAR (R4) va a PC3 (Pin 26) -> A3
# BOTÓN ABRIR (R1) va a PC2 (Pin 25) -> A2

# Mapeo a pines lógicos de Arduino (A0, A1, A2, A3)
PIN_LOCKED_LOGIC = "A0"
PIN_UNLOCKED_LOGIC = "A1"
PIN_BTN_OPEN_LOGIC = "A2"
PIN_BTN_CLOSE_LOGIC = "A3"

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
        # --- AÑADIDA DECLARACIÓN ANTICIPADA DE processInput ---
        return f"""
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>

RTC_DS1307 rtc;
LiquidCrystal lcd(12, 11, 5, 4, 3, 2); // Pines D4-D7 del LCD a D5-D2 del uC

// --- PINES CORREGIDOS SEGÚN DIAGRAMA PROTEUS ---
const int PIN_LOCKED = {PIN_LOCKED_LOGIC};      // LED ROJO (D1) -> PC0/A0
const int PIN_UNLOCKED = {PIN_UNLOCKED_LOGIC};    // LED VERDE (D2) -> PC1/A1
const int PIN_BTN_OPEN = {PIN_BTN_OPEN_LOGIC};    // BOTÓN ABRIR (R1) -> PC2/A2
const int PIN_BTN_CLOSE = {PIN_BTN_CLOSE_LOGIC};   // BOTÓN CERRAR (R4) -> PC3/A3

String inputString = "";
boolean inputReady = false;
boolean lastLockState = false; 
String lastTimeDisplayed = "";

// Variables Generadas
VAR_DECLARATIONS

// Prototipo de función para el manejo serial (SOLUCIONA EL ERROR 'not declared in this scope')
void processInput(String input); 

// Funciones lógicas simples (DECLARADAS ANTES DE USARSE)
void force_lock() {{ is_locked = true; refreshUI(); }}
void force_unlock() {{ is_locked = false; refreshUI(); }}


String getCurrentTime() {{
  // Lógica para obtener la hora del RTC (DS1307)
  DateTime now = rtc.now();
  char buffer[9];
  sprintf(buffer, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(buffer);
}}

// --- ACTUALIZADOR DE INTERFAZ ---
void refreshUI() {{
  // 1. Actualizar Hora
  String currentTime = getCurrentTime();
  // El tiempo se actualiza cada segundo (WAIT_TICK)
  if (currentTime != lastTimeDisplayed) {{ 
      lcd.setCursor(0, 0); 
      // Mostramos la hora en la primera línea
      lcd.print("Hora: " + currentTime);
      lastTimeDisplayed = currentTime;
  }}

  // 2. Actualizar LEDs y Estado LCD (LED HIGH = Encendido)
  if (is_locked) {{
      digitalWrite(PIN_LOCKED, HIGH);
      digitalWrite(PIN_UNLOCKED, LOW);
  }} else {{
      digitalWrite(PIN_LOCKED, LOW);
      digitalWrite(PIN_UNLOCKED, HIGH);
  }}

  // 3. Actualizar mensaje de estado solo si cambia
  if (is_locked != lastLockState) {{
      lcd.setCursor(0, 1);
      if (is_locked) lcd.print("CERRADO         ");
      else           lcd.print("ABIERTO         ");
      lastLockState = is_locked;
  }}
}}

// --- CHEQUEO DE BOTONES (SIN CONDICIONES - FUERZA BRUTA) ---
void checkButtons() {{
  // Los botones R1 y R4 están cableados como PULL-DOWN en el diagrama (conectados a VCC a través de la resistencia)
  // Por lo tanto, se leen HIGH cuando se presionan.
  
  // Botón ABRIR (R1)
  if (digitalRead(PIN_BTN_OPEN) == HIGH) {{
      Serial.println("[DIAGNOSTICO] Boton ABRIR detectado");
      force_unlock(); // Llama a la acción de apertura
      delay(500);        
  }}
  
  // Botón CERRAR (R4)
  if (digitalRead(PIN_BTN_CLOSE) == HIGH) {{
      Serial.println("[DIAGNOSTICO] Boton CERRAR detectado");
      force_lock(); // Llama a la acción de cierre
      delay(500);        
  }}
}}

// --- ESPERA INTELIGENTE ---
void smartDelay(unsigned long ms) {{
  unsigned long start = millis();
  while (millis() - start < ms) {{
      refreshUI();
      checkButtons(); 
      
      // Chequear Terminal
      if (Serial.available() > 0) {{
          // Usamos el valor numérico ASCII para evitar errores de escape.
          String raw = Serial.readStringUntil(13); 
          if (Serial.peek() == 10) Serial.read(); 
          processInput(raw);
      }}
  }}
}} 
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
      // Añadimos la lógica de control de longitud, por ejemplo, 4 caracteres
      if (inputString.length() >= 4) { // CAMBIO CLAVE: Checar longitud
          Serial.println("[INPUT] Recibido y listo para procesar: " + inputString);
          inputReady = true; // Establecer bandera
          lcd.setCursor(0, 1); lcd.print("Procesando...   ");
          smartDelay(500); 
      } else {
          Serial.println("[ERROR] Entrada incompleta.");
      }
      return;
  }
  
  // ASEGÚRATE QUE ESTAS LÍNEAS ESTÉN AQUÍ DENTRO DE processInput:
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

        # --- ENSAMBLAJE FINAL ---
        final_ino = self.get_template_head().replace('VAR_DECLARATIONS', var_decl)
        
        # AÑADIMOS la llave de cierre de smartDelay() que faltaba al final del get_template_head
        final_ino += "\n" 
        
        final_ino += process_input_func
        final_ino += logic_body
        
        final_ino += "\nvoid setup() {\n  Serial.begin(9600);\n  Serial.setTimeout(50);\n"
        final_ino += "  lcd.begin(16, 2);\n  lcd.print(\"PROLOCK SYSTEM\");\n"
        
        # --- CONFIGURACIÓN DE PINES EN SETUP ---
        final_ino += f"  pinMode({PIN_LOCKED_LOGIC}, OUTPUT); pinMode({PIN_UNLOCKED_LOGIC}, OUTPUT);\n"
        final_ino += f"  pinMode({PIN_BTN_OPEN_LOGIC}, INPUT); pinMode({PIN_BTN_CLOSE_LOGIC}, INPUT);\n"
        
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
  if (inputReady) inputReady = false; // <-- LIMPIAR LA BANDERA DESPUÉS DE LA LÓGICA
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