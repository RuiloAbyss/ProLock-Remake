# ¿Cómo instalar Prolock en tu ordenador? #

## Dependencias Externas ##
- **Proteus**: Para simular entornos con Arduino (Esquema Incluído en el proyecto **Lockers/Prolock Locker Test**).
- **Arduino**: Aquí se cargan los códigos que vas a generar.
- **arduini-cli** (Ya incluído en la raíz del proyecto).

## Dependencias python para ejecutar en terminal ##

```bash
pip install 
- graphviz 
- pillow
- ply
```
**NOTA**: Instalar graphviz en tu ordenador (opcional si deseas generar árboles sintácticos con grafos)

comandos (En la raíz del proyecto con arduino-cli descargado)
.\arduino-cli config init
.\arduino-cli core update-index
.\arduino-cli core install arduino:avr
.\arduino-cli.exe lib install "RTClib"
.\arduino-cli.exe lib install "LiquidCrystal"

## 🛠️ Dependencias del Proyecto ProLock ##

Para ejecutar este compilador y generar el firmware para tu simulación, necesitas instalar las siguientes herramientas.

## Python (Entorno del Compilador)
Asegúrate de tener Python instalado y ejecuta en tu terminal:

```bash
pip install graphviz pillow ply

# 1. Inicializar configuración
.\arduino-cli config init

# 2. Actualizar índice de núcleos
.\arduino-cli core update-index

# 3. Instalar el núcleo AVR (para ATmega328P)
.\arduino-cli core install arduino:avr

# 4. Instalar librerías necesarias para el LCD y el Reloj
.\arduino-cli lib install "RTClib"
.\arduino-cli lib install "LiquidCrystal"
.\arduino-cli lib install "Keypad"
.\arduino-cli lib install "Adafruit BusIO"
.\arduino-cli lib install "SPI"
.\arduino-cli lib install "Wire"
```