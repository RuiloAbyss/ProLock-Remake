import ply.yacc as yacc
from lexico import tokens

errores_sintacticos = [] # --- LISTA GLOBAL PARA ERRORES ---

def limpiar_errores_sintacticos():
    global errores_sintacticos
    errores_sintacticos.clear()

# ==========================================================
# LAS REGLAS (NO TOCAR)
# ==========================================================

def p_programa(p):
    'programa : PROGRAM IDENTIFICADOR APERTURA_LLAVE bloque_definiciones CIERRE_LLAVE'
    # Esta es una regla de ejemplo, puedes agregar acciones aquí.
    p[0] = ('programa', p[2], p[4])

# Bloque que permite múltiples definiciones
def p_bloque_definiciones(p):
    '''bloque_definiciones : bloque_definiciones definicion
                           | definicion'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_definicion(p):
    '''definicion : def_lock
                  | def_clock
                  | def_routine'''
    p[0] = p[1]

# Definición de LOCK y CLOCK
def p_def_lock(p):
    'def_lock : LOCK IDENTIFICADOR LPAREN RPAREN APERTURA_LLAVE bloque_estado CIERRE_LLAVE'
    p[0] = ('lock', p[2], p[6])

def p_def_clock(p):
    'def_clock : CLOCK IDENTIFICADOR LPAREN RPAREN APERTURA_LLAVE bloque_estado CIERRE_LLAVE'
    p[0] = ('clock', p[2], p[6])

# Bloque de estado y variables
def p_bloque_estado(p):
    'bloque_estado : STATE DOS_PUNTOS lista_variables'
    p[0] = ('state', p[3])

def p_lista_variables(p):
    '''lista_variables : lista_variables declaracion
                       | declaracion'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_declaracion(p):
    '''declaracion : declaracion_variable
                   | declaracion_nativa'''
    p[0] = p[1]

# Regla para variables estándar (tipo id = valor)
def p_declaracion_variable(p):
    'declaracion_variable : tipo IDENTIFICADOR IGUAL valor'
    p[0] = ('variable', p[1], p[2], p[4])

# Regla para variables nativas ($id = valor)
def p_declaracion_nativa(p):
    'declaracion_nativa : NATIVA IGUAL valor'
    p[0] = ('nativa', p[1], p[3]) # p[1] es el nombre (ej: 'PASS'), p[3] es el valor

def p_tipo(p):
    '''tipo : BOOLEAN
            | STRING
            | TIME
            | MOMENT'''
    p[0] = p[1]

def p_valor(p):
    '''valor : TRUE
             | FALSE
             | CADENA
             | valor_momento
             | CURRENT_TIME LPAREN RPAREN'''
    p[0] = p[1]

def p_valor_momento(p):
    'valor_momento : TIEMPO'
    p[0] = p[1]

# Definición de RUTINA y ACCIONES
def p_def_routine(p):
    'def_routine : ROUTINE IDENTIFICADOR APERTURA_LLAVE bloque_acciones CIERRE_LLAVE'
    p[0] = ('routine', p[2], p[4])

def p_bloque_acciones(p):
    '''bloque_acciones : bloque_acciones def_action
                       | def_action'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_def_action(p):
    'def_action : ACTION IDENTIFICADOR APERTURA_LLAVE clausula_when CIERRE_LLAVE'
    p[0] = ('action', p[2], p[4])

# Cláusula WHEN
def p_clausula_when(p):
    'clausula_when : WHEN DOS_PUNTOS LPAREN condicion RPAREN FLECHA consecuencia'
    p[0] = ('when', p[4], p[7])

def p_condicion(p):
    'condicion : expresion opLOGICO expresion'
    p[0] = (p[2], p[1], p[3])

def p_expresion(p):
    '''expresion : IDENTIFICADOR PUNTO nombre_variable PUNTO CHECK LPAREN RPAREN
                 | LPAREN IDENTIFICADOR RPAREN PUNTO CHECK LPAREN RPAREN'''
    if len(p) == 8: # Caso obj.var.check()
        p[0] = ('check', (p[1], p[3]))
    else: # Caso (obj).check()
        p[0] = ('check', p[2])

def p_nombre_variable(p):
    '''nombre_variable : IDENTIFICADOR
                       | NATIVA'''
    p[0] = p[1]

def p_consecuencia(p):
    '''consecuencia : llamada
                    | consecuencia COMA llamada'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

def p_llamada(p):
    '''llamada : SHOW LPAREN argumento_show RPAREN
               | IDENTIFICADOR PUNTO IDENTIFICADOR'''
    if len(p) == 5:
        p[0] = ('show', p[3])
    else:
        p[0] = ('call', p[1], p[3])

def p_argumento_show(p):
    '''argumento_show : CADENA
                      | expresion'''
    p[0] = p[1]

# Manejo de errores sintácticos
def p_error(p):
    """
    Función de manejo de errores sintácticos que ahora cuenta
    los tabs como un solo carácter para el puntero.
    """
    global errores_sintacticos
    if p:
        # 1. Obtener el código fuente completo
        codigo_fuente = p.lexer.lexdata
        
        # 2. Encontrar la línea del error, reemplazando tabs con UN solo espacio
        lineas = codigo_fuente.splitlines()
        linea_del_error = lineas[p.lineno - 1].replace('\t', ' ')

        # 3. Calcular la columna tratando cada carácter como si ocupara 1 espacio
        inicio_linea = codigo_fuente.rfind('\n', 0, p.lexpos) + 1
        columna = p.lexpos - inicio_linea

        # 4. Crear la cadena del puntero
        puntero = ' ' * columna + '↑'

        # 5. Construir el mensaje de error completo
        msg = (
            f"Error de Sintaxis en la línea {p.lineno}, columna {columna + 1}:\n"
            f"  {linea_del_error}\n"
            f"  {puntero}\n"
            f"  > Token inesperado '{p.value}' (tipo {p.type}). Se esperaba una estructura diferente."
        )
        errores_sintacticos.append(msg)
    else:
        errores_sintacticos.append("Error de sintaxis: Fin de archivo inesperado (EOF).")

# Construir el analizador
parser = yacc.yacc()