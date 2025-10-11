# sintactico.py (Versión Completa y Corregida)

import ply.yacc as yacc
from lexico import tokens

errores_sintacticos = []

def limpiar_errores_sintacticos():
    global errores_sintacticos
    errores_sintacticos.clear()

# ==========================================================
# REGLAS DE GRAMÁTICA (ESTRUCTURA GENERAL)
# ==========================================================

def p_programa(p):
    'programa : PROGRAM IDENTIFICADOR APERTURA_LLAVE bloque_definiciones CIERRE_LLAVE'
    p[0] = ('program', p[2], p[4])

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
                  | def_routine
                  | declaracion_variable'''
    p[0] = p[1]

# Definición de LOCK y CLOCK
def p_def_lock(p):
    'def_lock : LOCK IDENTIFICADOR LPAREN RPAREN APERTURA_LLAVE bloque_estado CIERRE_LLAVE'
    p[0] = ('lock_declaration', p[2], p[6], p.lineno(1))

def p_def_clock(p):
    'def_clock : CLOCK IDENTIFICADOR LPAREN RPAREN APERTURA_LLAVE bloque_estado CIERRE_LLAVE'
    p[0] = ('clock_declaration', p[2], p[6], p.lineno(1))

# Bloque de estado y variables
def p_bloque_estado(p):
    'bloque_estado : STATE DOS_PUNTOS lista_variables'
    p[0] = p[3] # Pasamos la lista de variables directamente

def p_lista_variables(p):
    '''lista_variables : lista_variables declaracion_variable
                       | declaracion_variable'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_declaracion_variable(p):
    '''declaracion_variable : tipo IDENTIFICADOR IGUAL valor
                            | NATIVA IGUAL valor'''
    if len(p) == 5:
        # variable estándar: boolean is_locked = true
        p[0] = ('variable_declaration', p[1], p[2], p[4], p.lineno(2))
    else:
        # variable nativa: $PASS = "secret"
        p[0] = ('variable_declaration', 'native', p[1], p[3], p.lineno(1))


def p_tipo(p):
    '''tipo : BOOLEAN
            | STRING
            | TIME
            | MOMENT
            | NUMBER'''
    p[0] = p[1]

def p_valor(p):
    '''valor : TRUE
             | FALSE
             | CADENA
             | TIEMPO
             | NUMERO 
             | CURRENT_TIME LPAREN RPAREN'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('current_time_call',)

# Definición de RUTINA y ACCIONES
def p_def_routine(p):
    'def_routine : ROUTINE IDENTIFICADOR APERTURA_LLAVE bloque_acciones CIERRE_LLAVE'
    p[0] = ('routine_declaration', p[2], p[4], p.lineno(1))

def p_bloque_acciones(p):
    '''bloque_acciones : bloque_acciones def_action
                       | def_action'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_def_action(p):
    'def_action : ACTION IDENTIFICADOR APERTURA_LLAVE clausula_when CIERRE_LLAVE'
    p[0] = ('action_declaration', p[2], p[4], p.lineno(1))

# Cláusula WHEN
def p_clausula_when(p):
    'clausula_when : WHEN DOS_PUNTOS LPAREN condicion RPAREN FLECHA consecuencia'
    p[0] = ('when_clause', p[4], p[7])

# ==========================================================
# REGLAS DE EXPRESIÓN (LÓGICA CORREGIDA Y UNIFICADA)
# ==========================================================

def p_condicion(p):
    'condicion : expresion opLOGICO expresion'
    p[0] = ('binary_op', p[2], p[1], p[3])

def p_expresion(p):
    '''expresion : llamada_metodo
                 | acceso_miembro
                 | identificador_simple
                 | valor_literal'''
    p[0] = p[1]

def p_identificador_simple(p):
    'identificador_simple : IDENTIFICADOR'
    p[0] = ('identifier', p[1])

def p_valor_literal(p):
    '''valor_literal : CADENA
                     | TRUE
                     | FALSE
                     | TIEMPO
                     | NUMERO'''
    p[0] = p[1]

def p_acceso_miembro(p):
    '''acceso_miembro : expresion PUNTO NATIVA
                      | expresion PUNTO IDENTIFICADOR'''
    p[0] = ('member_access', p[1], f'${p[3]}' if p.slice[2].type == 'NATIVA' else p[3])

def p_llamada_metodo(p):
    '''llamada_metodo : expresion PUNTO CHECK LPAREN RPAREN
                      | LPAREN expresion RPAREN PUNTO CHECK LPAREN RPAREN'''
    if len(p) == 6:
        p[0] = ('method_call', p[1], p[3])
    else:
        p[0] = ('method_call', p[2], p[5])
    
def p_consecuencia(p):
    '''consecuencia : enunciado_accion
                    | consecuencia COMA enunciado_accion'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

def p_enunciado_accion(p):
    '''enunciado_accion : asignacion
                       | llamada_accion
                       | llamada_show'''
    p[0] = p[1]

def p_asignacion(p):
    '''asignacion : IDENTIFICADOR PUNTO IDENTIFICADOR IGUAL expresion
                  | IDENTIFICADOR IGUAL expresion'''
    if len(p) == 6:
        # Asignación a miembro: front_door.is_locked = true
        member_access_node = ('member_access', ('identifier', p[1]), p[3])
        p[0] = ('member_assignment', member_access_node, p[5])
    else:
        # Asignación a variable global: inputPass = "new_pass"
        p[0] = ('assignment', p[1], p[3])

def p_llamada_accion(p):
    'llamada_accion : IDENTIFICADOR PUNTO IDENTIFICADOR'
    # Llamada a acción: front_door.force_unlock
    p[0] = ('action_call', p[1], p[3])

def p_llamada_show(p):
    'llamada_show : SHOW LPAREN expresion RPAREN'
    # Llamada a show: show("hola")
    p[0] = ('show_call', p[3])

# ==========================================================
# MANEJO DE ERRORES
# ==========================================================
def p_error(p):
    global errores_sintacticos
    if p:
        codigo_fuente = p.lexer.lexdata
        lineas = codigo_fuente.splitlines()
        if p.lineno - 1 < len(lineas):
            linea_del_error = lineas[p.lineno - 1].replace('\t', ' ')
            inicio_linea = codigo_fuente.rfind('\n', 0, p.lexpos) + 1
            columna = p.lexpos - inicio_linea
            puntero = ' ' * columna + '↑'
            msg = (
                f"Error de Sintaxis en línea {p.lineno}, columna {columna + 1}:\n"
                f"  {linea_del_error}\n"
                f"  {puntero}\n"
                f"  > Token inesperado '{p.value}' (tipo {p.type})."
            )
        else:
            msg = f"Error de Sintaxis cerca del final del archivo. Token inesperado '{p.value}'."
        errores_sintacticos.append(msg)
    else:
        errores_sintacticos.append("Error de sintaxis: Fin de archivo inesperado (EOF).")

# Construir el analizador
parser = yacc.yacc()