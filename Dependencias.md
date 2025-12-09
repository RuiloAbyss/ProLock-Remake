Prolock :D

##Dependencias python para ejecutar en terminal ##
pip install 
- graphviz 
- pillow
- ply

**NOTA**: Instalar graphviz en tu ordenador (opcional si deseas generar árboles sintácticos con grafos)
Descarga arduino-cli

comandos (En la raíz del proyecto con arduino-cli descargado)
.\arduino-cli config init
.\arduino-cli core update-index
.\arduino-cli core install arduino:avr
.\arduino-cli.exe lib install "RTClib"
.\arduino-cli.exe lib install "LiquidCrystal"