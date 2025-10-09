import ply.yacc as yacc
from lexico import tokens

# Variable global para almacenar errores sintácticos
errores_Sinc_Desc = []

def limpiar_errores_sintacticos():
    """Limpia la lista de errores antes de un nuevo análisis."""
    global errores_Sinc_Desc
    errores_Sinc_Desc.clear()

# --- Definición de la Gramática ---

def p_programa(p):
    """
    programa : PROG IDENTIFICADOR APERTURA bloque_codigo CIERRE
    """
    p[0] = ('programa', p[2], p[4])

def p_bloque_codigo(p):
    """
    bloque_codigo : declaracion
                  | bloque_codigo declaracion
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_declaracion(p):
    """
    declaracion : constructor_base
                | modificador_caracteristica
                | rutina
    """
    p[0] = p[1]

def p_constructor_base(p):
    """
    constructor_base : NODO IDENTIFICADOR OBJETO APERTURA bloque_caracteristicas CIERRE
    """
    p[0] = ('constructor_base', p[2], p[3], p[5])

def p_bloque_caracteristicas(p):
    """
    bloque_caracteristicas : caracteristica
                           | bloque_caracteristicas caracteristica
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_caracteristica(p):
    """
    caracteristica : TIENE APERTURA bloque_tiene CIERRE
                   | PUEDE APERTURA bloque_puede CIERRE
    """
    p[0] = (p[1], p[3])
    
def p_bloque_tiene(p):
    """
    bloque_tiene : asignacion
                 | bloque_tiene asignacion
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_asignacion(p):
    """
    asignacion : assign_type IDENTIFICADOR IGUAL NUMERO
    """
    p[0] = ('asignacion', p[1], p[2], p[4])

def p_assign_type(p):
    """
    assign_type : IDENTIFICADOR
                | EJE
                | MOTORX
                | MOTORY
    """
    p[0] = p[1]

def p_bloque_puede(p):
    """
    bloque_puede : funcion
                 | bloque_puede funcion
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_rutina(p):
    """
    rutina : RUTINA IDENTIFICADOR APERTURA bloque_puede CIERRE
    """
    p[0] = ('rutina', p[2], p[4])

def p_funcion(p):
    """
    funcion : IDENTIFICADOR LPAREN argumentos RPAREN
    """
    p[0] = ('funcion', p[1], p[3])

def p_argumentos(p):
    """
    argumentos : argumento
               | argumentos COMA argumento
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[1].append(p[3])
        p[0] = p[1]

def p_argumento(p):
    """
    argumento : IDENTIFICADOR
              | NUMERO
    """
    p[0] = p[1]

def p_modificador_caracteristica(p):
    """
    modificador_caracteristica : IDENTIFICADOR TIENE APERTURA bloque_tiene CIERRE
                               | IDENTIFICADOR PUEDE APERTURA bloque_puede CIERRE
    """
    p[0] = ('modificador', p[1], p[2], p[4])

# Manejo de errores sintácticos
def p_error(p):
    global errores_Sinc_Desc
    if p:
        # Calcular la columna del error
        inicio_linea = p.lexer.lexdata.rfind('\n', 0, p.lexpos) + 1
        columna = (p.lexpos - inicio_linea) + 1
        msg = f"Error de sintaxis en '{p.value}' (línea {p.lineno}, columna {columna})"
        errores_Sinc_Desc.append(msg)
    else:
        errores_Sinc_Desc.append("Error de sintaxis: Fin de archivo inesperado (EOF)")

# Construir el analizador
parser = yacc.yacc()