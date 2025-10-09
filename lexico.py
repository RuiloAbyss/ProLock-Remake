import ply.lex as lex

# Variables globales para almacenar resultados de la última ejecución
tokens_identificados = []
lista_errores_lexicos = []

# Palabras reservadas (mapeo de palabra a tipo de token)
RESERVADA = {
    'nodo': 'NODO',
    'tiene': 'TIENE',
    'puede': 'PUEDE',
    'ciclo': 'CICLO',
    'si': 'SI',
    'no': 'NO',
    'ent': 'ENT',
    'dec': 'DEC',
    'bin': 'BIN',
    'false': 'FALSE',
    'true': 'TRUE',
    'eje': 'EJE',
    'motorx': 'MOTORX',
    'motory': 'MOTORY',
    'reloj': 'RELOJ',
    'tempo': 'TEMPO',
    'contador': 'CONTADOR',
    'rutina': 'RUTINA',
    'programa': 'PROG' # Añadido para consistencia
}

# Lista completa de tokens (se añaden los valores del diccionario RESERVADA)
tokens = [
    'IDENTIFICADOR', 'APERTURA', 'CIERRE', 'NUMERO', 'LPAREN', 'RPAREN',
    'CADENA', 'COMENTARIO', 'OBJETO', 'opLOGICO', 'opARITMETICO', 
    'IGUAL', 'COMA', 'PROG'
] + list(RESERVADA.values())

# Reglas para tokens simples
t_APERTURA = r'\:'
t_CIERRE = r'\.'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_COMA = r','
t_IGUAL = r'='
t_opLOGICO = r'(==|>=|<=|>|<)'
t_opARITMETICO = r'(\+|-|\*|/|%)'

# Ignorar espacios y tabs, pero no saltos de línea
t_ignore = ' \t\r'

# Reglas con acciones (funciones)

def t_OBJETO(t):
    r'\b(reloj|tempo|motor|memo)\b'
    return t

def t_NUMERO(t):
    r'-?\d+(\.\d+)?'
    t.value = float(t.value) if '.' in t.value else int(t.value)
    return t

def t_IDENTIFICADOR(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    # Revisa si el identificador es una palabra reservada
    t.type = RESERVADA.get(t.value.lower(), 'IDENTIFICADOR')
    return t

def t_CADENA(t):
    r'"([^"\\]|\\.)*"'
    t.value = t.value[1:-1]  # Quitar comillas
    return t

def t_COMENTARIO(t):
    r'//.*'
    pass  # Ignorar comentarios, no hacer nada

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Manejo de errores léxicos
def t_error(t):
    # Calcular la columna del error
    inicio_linea = t.lexer.lexdata.rfind('\n', 0, t.lexpos) + 1
    columna = (t.lexpos - inicio_linea) + 1
    error_msg = f"Símbolo no válido '{t.value[0]}' en la línea {t.lineno}, columna {columna}"
    lista_errores_lexicos.append(error_msg)
    t.lexer.skip(1)

# Construir el analizador léxico
lexer = lex.lex()

def analisis(cadena):
    """
    Realiza el análisis léxico del código fuente.
    Limpia las listas de tokens y errores antes de cada ejecución.
    """
    # Limpiar resultados de análisis anteriores
    tokens_identificados.clear()
    lista_errores_lexicos.clear()
    
    lexer.input(cadena)
    lexer.lineno = 1  # Iniciar contador de líneas en 1

    while True:
        tok = lexer.token()
        if not tok:
            break  # Fin de la entrada
        
        # Calcular columna
        inicio_linea = cadena.rfind('\n', 0, tok.lexpos) + 1
        columna = (tok.lexpos - inicio_linea) + 1
        
        tokens_identificados.append((tok.value, tok.type, tok.lineno, columna))