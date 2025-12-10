import os
import subprocess
import sys

# === CONFIGURACIÓN DE PINES ===
# LCD (Puerto B): 8, 9, 10, 11, 12, 13
# Keypad (Puerto D): 0, 1, 2, 3 (Filas), 4, 5, 6 (Columnas)
# I2C: A4, A5
# Periféricos: A0, A1, A2, A3

PIN_LOCKED_LOGIC = "A0"      
PIN_UNLOCKED_LOGIC = "A1"    
PIN_BTN_OPEN_LOGIC = "A2"    
PIN_BTN_CLOSE_LOGIC = "A3"   
PIN_MEMORY_LOGIC = "7"       

class ArduinoGenerator:
    def __init__(self, intermediate_code, output_dir="arduino_build"):
        self.intermediate_code = intermediate_code
        self.output_dir = output_dir
        self.variables = set()       
        self.global_vars = set()     
        self.internal_vars = set()
        self.uses_clock = False 

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
        if clean_arg == "TIME" or clean_arg == "$TIME": 
            return "getLogicTime()" 
        return clean_arg

    def _analyze_variables(self):
        self.global_vars.clear()
        self.internal_vars.clear()
        self.variables.clear()
        self.uses_clock = False
        
        def is_literal_or_constant(token):
            if not isinstance(token, str) or len(token) == 0: return True
            if token[0].isdigit(): return True
            if token.startswith('"') and token.endswith('"'): return True
            if token.startswith('<') and token.endswith('>'): return True 
            if token.endswith('s') and token[:-1].isdigit(): return True
            if token.endswith('ms') and token[:-2].isdigit(): return True
            if token in ['true', 'false']: return True
            return False

        for quad in self.intermediate_code:
            op, arg1, arg2, res = quad
            if "TIME" in str(arg1) or "TIME" in str(arg2) or "TIME" in str(res):
                self.uses_clock = True
            if op == 'ASSIGN' and res:
                res_clean = res.split('.')[-1]
                if not is_literal_or_constant(res_clean) and not res_clean.startswith('t'):
                    if '.' in res: self.internal_vars.add(res_clean)
                    else: self.global_vars.add(res_clean)
            for arg in [arg1, arg2]:
                if arg and not arg.startswith('t'):
                    arg_clean = arg.split('.')[-1]
                    if not is_literal_or_constant(arg_clean):
                        if arg_clean not in self.internal_vars:
                            self.global_vars.add(arg_clean) 
            if res and res.startswith('t'): self.variables.add(res)

    def get_template_head(self):
        clock_def = "const boolean ENABLE_CLOCK = true;" if self.uses_clock else "const boolean ENABLE_CLOCK = false;"

        return f"""
#include <Wire.h>
#include <RTClib.h> 
#include <LiquidCrystal.h>
#include <Keypad.h>

RTC_DS1307 rtc;
LiquidCrystal lcd(8, 9, 10, 11, 12, 13); 

const byte FILAS = 4; 
const byte COLUMNAS = 3; 
char keys[FILAS][COLUMNAS] = {{
  {{'1','2','3'}},
  {{'4','5','6'}},
  {{'7','8','9'}},
  {{'*','0','#'}}
}};
byte pinesFilas[FILAS] = {{0, 1, 2, 3}};    
byte pinesColumnas[COLUMNAS] = {{4, 5, 6}}; 
Keypad teclado = Keypad(makeKeymap(keys), pinesFilas, pinesColumnas, FILAS, COLUMNAS);

const int PIN_LOCKED = {PIN_LOCKED_LOGIC};      
const int PIN_UNLOCKED = {PIN_UNLOCKED_LOGIC};    
const int PIN_BTN_OPEN = {PIN_BTN_OPEN_LOGIC};    
const int PIN_BTN_CLOSE = {PIN_BTN_CLOSE_LOGIC};   
const int PIN_MEMORY = {PIN_MEMORY_LOGIC}; 

{clock_def}
boolean is_locked = true; 
boolean lastLockState = false; 
unsigned long lastClockUpdate = 0; 
boolean necesitaLimpiar = true;
unsigned long messageTimer = 0; 
boolean showingMessage = false;

char entradaArray[5];               
byte indiceArray = 0;

// VARIABLES DEL COMPILADOR
VAR_DECLARATIONS

// Prototipos
void limpiarEntrada();
void verificarPassword();
void mostrarEstadoPuerta();
void refreshUI();
void showMessage(String msg, int duration);
void force_lock() {{ is_locked = true; refreshUI(); }}
void force_unlock() {{ is_locked = false; refreshUI(); }} 

// TIEMPO (HH:MM:SS)
String getDisplayTime() {{
  DateTime now = rtc.now();
  char buffer[9];
  sprintf(buffer, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  return String(buffer);
}}

// TIEMPO LOGICA (HH:MM)
String getLogicTime() {{
  DateTime now = rtc.now();
  char buffer[6];
  sprintf(buffer, "%02d:%02d", now.hour(), now.minute());
  return String(buffer);
}}

// --- UI TURBO (SIMULACION LENTA) ---
void refreshUI() {{
  unsigned long currentMillis = millis();

  // 1. Mensajes Temporales
  if (showingMessage) {{
      if (currentMillis >= messageTimer) {{
          showingMessage = false; 
          mostrarEstadoPuerta(); 
      }}
      return; 
  }}

  // 2. Reloj ULTRA RÁPIDO para compensar simulación lenta
  // Se actualiza cada 125ms lógicos, que serán aprox 1 seg real en tu Proteus
  if (ENABLE_CLOCK) {{
      if (currentMillis - lastClockUpdate >= 125) {{ 
          lcd.setCursor(0, 0); 
          lcd.print("Hora: " + getDisplayTime());
          lastClockUpdate = currentMillis;
      }}
  }}

  // 3. LEDs
  if (is_locked) {{
      digitalWrite(PIN_LOCKED, HIGH); digitalWrite(PIN_UNLOCKED, LOW);
  }} else {{
      digitalWrite(PIN_LOCKED, LOW); digitalWrite(PIN_UNLOCKED, HIGH);
  }}

  // 4. Texto Estado Base
  if (is_locked != lastLockState && indiceArray == 0) {{
      mostrarEstadoPuerta();
      lastLockState = is_locked;
  }}
}}

void mostrarEstadoPuerta() {{
   lcd.setCursor(0, 1);
   if (is_locked) lcd.print("CERRADO         ");
   else           lcd.print("ABIERTO         ");
   necesitaLimpiar = true; 
}}

void showMessage(String msg, int duration) {{
    lcd.setCursor(0, 1);
    lcd.print(msg + "                "); 
    showingMessage = true;
    messageTimer = millis() + duration; 
}}

// --- KEYPAD ---
void handleKeypad() {{
  char tecla = teclado.getKey(); 

  if (tecla) {{
    if (showingMessage) {{
        showingMessage = false;
        mostrarEstadoPuerta();
    }}
    
    if (tecla == '#') {{
      limpiarEntrada();
      showMessage("Cancelado", 100); // 100ms
    }}
    else if (tecla == '*') {{
      if (indiceArray > 0) {{
        indiceArray--;           
        entradaArray[indiceArray] = 0;
        lcd.setCursor(indiceArray, 1); lcd.print(" "); lcd.setCursor(indiceArray, 1); 
      }} else {{
         limpiarEntrada();
         mostrarEstadoPuerta();
      }}
    }}
    else {{
      if (necesitaLimpiar) {{
          lcd.setCursor(0, 1); lcd.print("                "); lcd.setCursor(0, 1);
          necesitaLimpiar = false;
      }}

      if (indiceArray < 4) {{
        entradaArray[indiceArray] = tecla; 
        lcd.print(tecla); 
        indiceArray++; 
        
        if (indiceArray == 4) {{
          entradaArray[4] = '\\0'; 
          verificarPassword(); 
        }}
      }}
    }}
  }}
}}

void limpiarEntrada() {{
  memset(entradaArray, 0, sizeof(entradaArray)); 
  indiceArray = 0;                          
}}

void verificarPassword() {{
  if (strcmp(entradaArray, PASS.c_str()) == 0) {{
    force_unlock(); 
    showMessage("BIENVENIDO!", 250); // Mensaje super corto (simulado)
  }} else {{
    showMessage("ERROR CLAVE", 250);
  }}
  limpiarEntrada();
}}

void checkInputs() {{
  handleKeypad(); 

  if (digitalRead(PIN_MEMORY) == HIGH) {{
      showMessage("Leyendo Mem...", 200);
      if (PASS.length() < 5) strcpy(entradaArray, PASS.c_str());
      verificarPassword();
      while(digitalRead(PIN_MEMORY) == HIGH); 
  }}

  if (digitalRead(PIN_BTN_OPEN) == HIGH) {{ force_unlock(); delay(10); }}
  if (digitalRead(PIN_BTN_CLOSE) == HIGH) {{ force_lock(); delay(10); }}
}}

// Delay inteligente ULTRA CORTO
void smartDelay(unsigned long ms) {{
  // Dividimos todo el tiempo entre 8 para compensar lag
  unsigned long adjusted_ms = ms / 8; 
  if (adjusted_ms < 1) adjusted_ms = 1;
  
  unsigned long start = millis();
  while (millis() - start < adjusted_ms) {{
      refreshUI(); 
      checkInputs(); 
  }}
}} 
"""
    
    def generate(self, ruta_personalizada=None):
        self._analyze_variables()
        known_internals = {"is_locked", "PASS", "lock_time", "unlock_time", "report_time"}
        self.internal_vars.update(known_internals)
        self.global_vars = self.global_vars - self.internal_vars
        
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
                if val and val.startswith('<') and val.endswith('>'):
                    val = '"' + val[1:-1] + '"'
                if val == '' or val is None: val = '""'
                target = res.split('.')[-1] if '.' in res else res
                logic_body += f"{indent}{target} = {val};\n"
            
            # DELAYS AJUSTADOS AUTOMÁTICAMENTE
            elif op == 'WAIT_TICK':
                logic_body += f"{indent}smartDelay(1000); // Se dividirá entre 8 en smartDelay\n" 
            elif op == 'WAIT_INPUT':
                logic_body += f"{indent}smartDelay(100);\n"

            elif op == 'CALL': logic_body += f"{indent}{res}();\n"
            
            elif op == 'PRINT':
                val = arg1.replace('"', '')
                if '.' in val: val = val.split('.')[-1]
                logic_body += f"{indent}showMessage(\"{val}\", 250);\n"
                
            else:
                cpp_op = self.map_operator(op)
                c_arg1 = self._clean_and_map(arg1)
                c_arg2 = self._clean_and_map(arg2)
                logic_body += f"{indent}{res} = ({c_arg1} {cpp_op} {c_arg2});\n"
        
        logic_body += "\n  return;\n}\n"

        var_decl = ""
        for g_var in sorted(list(self.global_vars)): var_decl += f"String {g_var} = \"\";\n"
        for i_var in sorted(list(self.internal_vars)):
            if i_var != "is_locked" and i_var not in self.global_vars: 
                var_decl += f"String {i_var} = \"\";\n"
        for var in sorted(list(self.variables)): var_decl += f"boolean {var} = false;\n"

        final_ino = self.get_template_head().replace('VAR_DECLARATIONS', var_decl)
        
        final_ino += "void processInput(String input) { return; }\n"
        final_ino += logic_body
        
        final_ino += "\nvoid setup() {\n"
        final_ino += "  lcd.begin(16, 2);\n  lcd.print(\"SISTEMA LISTO\"); delay(50); lcd.clear();\n"
        
        final_ino += f"  pinMode({PIN_LOCKED_LOGIC}, OUTPUT); pinMode({PIN_UNLOCKED_LOGIC}, OUTPUT);\n"
        final_ino += f"  pinMode({PIN_BTN_OPEN_LOGIC}, INPUT); pinMode({PIN_BTN_CLOSE_LOGIC}, INPUT);\n"
        final_ino += f"  pinMode({PIN_MEMORY_LOGIC}, INPUT);\n" 
        
        final_ino += "  if (ENABLE_CLOCK) {\n"
        final_ino += "    if (!rtc.begin()) { lcd.setCursor(0,1); lcd.print(\"ERROR RTC\"); }\n"
        final_ino += "    if (!rtc.isrunning()) { rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); }\n"
        final_ino += "  }\n"
        
        final_ino += "  is_locked = true;\n  limpiarEntrada();\n  refreshUI();\n}\n"
        
        final_ino += """
void loop() {
  checkInputs();
  checkLogic();
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