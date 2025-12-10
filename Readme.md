# 🔒 ProLock: Compilador de Cerraduras Inteligentes

ProLock es un lenguaje de dominio específico (DSL) diseñado para programar sistemas de seguridad inteligentes basados en Arduino (ATmega328P) de manera sencilla y declarativa. Permite definir rutinas, horarios y claves de acceso que se compilan automáticamente a un firmware `.hex` listo para simulación en Proteus.

## 📦 Instalación
Consulta el archivo `Dependencias.md` para instalar Python, las librerías necesarias y configurar `arduino-cli`.

## 📝 Guía de Sintaxis
Crea un archivo de texto (ej. `micasa.pro`) con tu código. La estructura básica es:

```prolock
program SmartHome {
    // 1. Definir la Puerta y su Clave
    lock front_door() {
       state:
          boolean is_locked = true
          $PASS = "1235"  // Clave de 4 dígitos
    }

    // 2. Configurar el Reloj y Horarios
    clock main_clock() {
       state:
          $TIME = <00:00>      // Hora inicial simulada
          moment lock_time = <22:00>
          moment unlock_time = <07:00>
    }

    // 3. Rutinas Automáticas
    routine daily_schedule {
       
       // Cerrar puerta automáticamente
       action night_lock {
          when: (main_clock.$TIME == main_clock.lock_time) -> front_door.force_lock
       }

       // Abrir puerta automáticamente
       action morning_unlock {
          when: (main_clock.$TIME == main_clock.unlock_time) -> front_door.force_unlock
       }
    }
}
```

| Componente | Pin Componente | Pin Arduino (Físico) | Puerto Lógico |
| :--- | :--- | :---: | :---: |
| **LCD (16x2)** | RS | 8 | `PB0` |
| | E | 9 | `PB1` |
| | D4 | 10 | `PB2` |
| | D5 | 11 | `PB3` |
| | D6 | 12 | `PB4` |
| | D7 | 13 | `PB5` |
| **Keypad (3x4)** | Fila 1 | 0 | `PD0` |
| | Fila 2 | 1 | `PD1` |
| | Fila 3 | 2 | `PD2` |
| | Fila 4 | 3 | `PD3` |
| | Col 1 | 4 | `PD4` |
| | Col 2 | 5 | `PD5` |
| | Col 3 | 6 | `PD6` |
| **Periféricos** | LED Rojo (Cerrado) | A0 | `PC0` |
| | LED Verde (Abierto) | A1 | `PC1` |
| | Botón Abrir | A2 | `PC2` |
| | Botón Cerrar | A3 | `PC3` |
| **Reloj RTC** | SDA | A4 | `PC4` |
| | SCL | A5 | `PC5` |
| **Memoria** | Lectura | 7 | `PD7` |


▶️ Compilación y Ejecución
Abre una terminal en la carpeta del proyecto.
Ejecuta el compilador indicando tu archivo de código:

Si la compilación es exitosa, podrás exportar tu código en un archivo .hex verás un mensaje como: [ÉXITO] Firmware generado: ./arduino_build/micasa.ino.hex

Abre Proteus, haz doble clic en tu placa Arduino y en la casilla Program File, selecciona el archivo .hex generado.

*¡Dale Play a la simulación!*