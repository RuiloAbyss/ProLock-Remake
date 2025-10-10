import ply.lex as lex
import re

# Variables globales para almacenar resultados
tokens_identificados = []
lista_errores_lexicos = []

# Palabras reservadas
RESERVADA = {
    'program': 'PROGRAM', 'lock': 'LOCK', 'clock': 'CLOCK', 'routine': 'ROUTINE',
    'state': 'STATE', 'action': 'ACTION', 'when': 'WHEN', 'boolean': 'BOOLEAN',
    'string': 'STRING', 'time': 'TIME', 'moment': 'MOMENT', 'true': 'TRUE',
    'false': 'FALSE', 'show': 'SHOW', 'current_time': 'CURRENT_TIME', 'check': 'CHECK'
}

# Lista de tokens
tokens = [
    'IDENTIFICADOR', 'NUMERO', 'CADENA', 'COMENTARIO',
    'APERTURA_LLAVE', 'CIERRE_LLAVE',                   # { }
    'LPAREN', 'RPAREN',                                 # ( )
    'PUNTO', 'COMA', 'IGUAL', 'DOS_PUNTOS',             # . , = :
    'FLECHA', 'opLOGICO',                               # -> ==
    'TIEMPO',                                           # <HH:MM>
    'NATIVA'                                            # $VARIABLE
] + list(RESERVADA.values())

# --- Token TIEMPO con validación de formato 24h ---
def t_TIEMPO(t):
    r'\<([01]\d|2[0-3]):[0-5]\d\>'
    return t

# --- Token NATIVO para variables que no requieren definir su tipo de dato Y pertenecen a objetos por defecto
def t_NATIVA(t):
    r'\$[a-zA-Z_][a-zA-Z_0-9]*'
    t.value = t.value[1:] # Guardamos el nombre sin el '$'
    return t

# Reglas de tokens simples
t_APERTURA_LLAVE = r'\{'
t_CIERRE_LLAVE = r'\}'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_PUNTO = r'\.'
t_COMA = r','
t_IGUAL = r'='
t_DOS_PUNTOS = r'\:'
t_FLECHA = r'->'
t_opLOGICO = r'=='
t_ignore = ' \t\r'

# Reglas con acciones
def t_IDENTIFICADOR(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = RESERVADA.get(t.value.lower(), 'IDENTIFICADOR')
    return t

def t_NUMERO(t):
    r'-?\d+(\.\d+)?'
    t.value = float(t.value) if '.' in t.value else int(t.value)
    return t

def t_CADENA(t):
    r'\"([^\"\\]|\\.)*\"'
    t.value = t.value[1:-1]
    return t

def t_COMENTARIO(t):
    r'//.*'
    pass

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# ==========================================================
# ERROR
# ==========================================================
def t_error(t):
    """
    Esta función ahora captura la palabra inválida completa.
    1.  Calcula la posición inicial del error.
    2.  Escanea hacia adelante para encontrar el final de la palabra.
    3.  Crea un mensaje de error y un token de ERROR con la palabra completa.
    4.  Avanza el lexer después de la palabra inválida.
    5.  Retorna el token de error.
    """
    # 1. Calcular la columna inicial del error
    inicio_linea = t.lexer.lexdata.rfind('\n', 0, t.lexpos) + 1
    columna = 0
    posicion_actual = inicio_linea
    tabsize = 3
    while posicion_actual < t.lexpos:
        if t.lexer.lexdata[posicion_actual] == '\t':
            columna += tabsize - (columna % tabsize)
        else:
            columna += 1
        posicion_actual += 1
    columna += 1

    # 2. Encuentra el final de la palabra inválida buscando el próximo espacio en blanco, tabulador o salto de línea
    match = re.search(r'\s', t.value)
    if match:
        # Si se encuentra un espacio, la palabra termina ahí
        end_pos = match.start()
    else:
        # Si no, la palabra va hasta el final de la cadena
        end_pos = len(t.value)
    
    # La palabra inválida es la subcadena desde el inicio hasta el límite
    invalid_word = t.value[:end_pos]

    # 3. Registrar el mensaje y configurar el token de ERROR con la palabra completa
    error_msg = f"Símbolo o palabra no reconocida '{invalid_word}' en la línea {t.lineno}, columna {columna}"
    lista_errores_lexicos.append(error_msg)
    
    # El valor del token ahora es la palabra completa
    t.type = 'ERROR'
    t.value = invalid_word

    # 4. Avanza el lexer para saltar TODA la palabra inválida
    t.lexer.lexpos += len(invalid_word)
    
    # 5. Retornar el token para que se añada a la lista
    return t

# Construir el analizador léxico
lexer = lex.lex()

def analisis(cadena):
    """
    Realiza el análisis léxico. Ahora, la lista 'tokens_identificados'
    incluirá tanto los tokens válidos como los de tipo 'ERROR'.
    """
    tokens_identificados.clear()
    lista_errores_lexicos.clear()
    
    lexer.input(cadena)
    lexer.lineno = 1

    while True:
        tok = lexer.token()
        if not tok:
            break
        
        # Calcular columna para TODOS los tokens (incluidos los de error)
        inicio_linea = cadena.rfind('\n', 0, tok.lexpos) + 1
        columna = (tok.lexpos - inicio_linea) + 1
        
        tokens_identificados.append((tok.value, tok.type, tok.lineno, columna))