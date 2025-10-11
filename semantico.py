# semantico.py (Versión Final y Sincronizada)

import re

class Symbol:
    def __init__(self, name, symbol_type, scope, line, members=None):
        self.name = name
        self.type = symbol_type
        self.scope = scope
        self.line = line
        self.members = members if members is not None else {}
        self.used = False

class SymbolTable:
    def __init__(self):
        self.symbols = {}

    def define(self, symbol):
        scope_key = symbol.scope
        if scope_key not in self.symbols: self.symbols[scope_key] = {}
        if symbol.name in self.symbols[scope_key]:
            return f"El identificador '{symbol.name}' ya ha sido declarado."
        self.symbols[scope_key][symbol.name] = symbol
        return None

    def peek(self, name, scope):
        """Busca un símbolo sin marcarlo como usado (para la Pasada 1)."""
        if scope in self.symbols and name in self.symbols[scope]:
            return self.symbols[scope][name]
        if 'global' in self.symbols and name in self.symbols['global']:
            return self.symbols['global'][name]
        return None

    def lookup(self, name, scope):
        if scope in self.symbols and name in self.symbols[scope]:
            self.symbols[scope][name].used = True
            return self.symbols[scope][name]
        if 'global' in self.symbols and name in self.symbols['global']:
            self.symbols['global'][name].used = True
            return self.symbols['global'][name]
        return None
    
    def lookup_member(self, object_name, member_name):
        obj = self.lookup(object_name, 'global')
        if obj:
            clean_member_name = member_name.lstrip('$')
            if clean_member_name in obj.members:
                obj.members[clean_member_name].used = True
                return obj.members[clean_member_name]
        return None

class SemanticAnalyzer:
    def __init__(self, ast, source_code):
        self.ast = ast
        self.symbol_table = SymbolTable()
        self.errors = []
        self.warnings = []
        self.source_code = source_code
        self.source_lines = source_code.splitlines()

        # Diccionario de reservadas
        self.predefined_natives = {
            'TIME': 'time', 
            'PASS': 'string'
            }
        
        #Diccionario de acciones reservadas
        self.predefined_actions = {
            'lock': ['force_lock', 'force_unlock'],
            'clock': [], # Los relojes no tienen acciones predefinidas por ahora
        }

    def _format_diagnostic(self, identifier, line_num, message):
        line_content = self.source_lines[line_num - 1]
        clean_identifier = identifier.lstrip('$')
        match = re.search(r'\b' + re.escape(clean_identifier) + r'\b', line_content)
        col = match.start() if match else line_content.find(clean_identifier)
        
        pointer = ' ' * col + '^' * len(clean_identifier)
        return {"message": message, "line": line_num, "content": line_content.strip(), "pointer": pointer}

    def analyze(self):
        self.visit(self.ast, pass_num=1)
        if not self.errors:
            self.visit(self.ast, pass_num=2)
        if not self.errors:
            self._check_for_unused_symbols()
        return {'errors': self.errors, 'warnings': self.warnings}

    def _check_for_unused_symbols(self):
        for scope_name, symbols in self.symbol_table.symbols.items():
            for symbol_name, symbol in symbols.items():
                if symbol.type in ['program', 'action']: continue
                
                if not symbol.used:
                    msg = f"Advertencia: El {symbol.type} '{symbol.name}' fue declarado pero nunca se utilizó."
                    self.warnings.append(self._format_diagnostic(symbol.name, symbol.line, msg))
                
                if symbol.members:
                    for member_name, member_symbol in symbol.members.items():
                       if not member_symbol.used and member_symbol.type != 'action':
                            msg = f"Advertencia: La variable '{member_name}' en '{symbol.name}' fue declarada pero nunca se utilizó."
                            warning = self._format_diagnostic(member_name, member_symbol.line, msg)
                            self.warnings.append(warning)
    
    def _types_are_compatible(self, type1, type2):
        if type1 == type2: return True
        compatible_pairs = {('time', 'moment')}
        return (type1, type2) in compatible_pairs or (type2, type1) in compatible_pairs

    def visit(self, node, scope='global', pass_num=1):
        if not node: return
        node_type = node[0]
        method_name = f'visit_{node_type}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node, scope, pass_num)

    def generic_visit(self, node, scope, pass_num):
        if isinstance(node, (list, tuple)):
            for child in node[1:]: self.visit(child, scope, pass_num)

    def visit_program(self, node, scope, pass_num):
        prog_symbol = Symbol(node[1], 'program', 'global', 1)
        self.symbol_table.define(prog_symbol)
        for decl in node[2]: self.visit(decl, 'global', pass_num)

    def visit_lock_declaration(self, node, scope, pass_num):
        if pass_num != 1: return
        lock_name, states, line_num = node[1], node[2], node[3]
        lock_symbol = Symbol(lock_name, 'lock', scope, line_num)
        err = self.symbol_table.define(lock_symbol)
        if err: self.errors.append(self._format_diagnostic(lock_name, line_num, err))
        for state_var in states: self.visit(state_var, lock_name, pass_num)

    def visit_clock_declaration(self, node, scope, pass_num):
        if pass_num != 1: return
        clock_name, states, line_num = node[1], node[2], node[3]
        clock_symbol = Symbol(clock_name, 'clock', scope, line_num)
        err = self.symbol_table.define(clock_symbol)
        if err: self.errors.append(self._format_diagnostic(clock_name, line_num, err))
        for state_var in states: self.visit(state_var, clock_name, pass_num)

    def visit_routine_declaration(self, node, scope, pass_num):
        routine_name, actions, line_num = node[1], node[2], node[3]
        if pass_num == 1:
            routine_symbol = Symbol(routine_name, 'routine', scope, line_num)
            err = self.symbol_table.define(routine_symbol)
            if err: self.errors.append(self._format_diagnostic(routine_name, line_num, err))
        for action in actions: self.visit(action, routine_name, pass_num)

    def visit_variable_declaration(self, node, scope, pass_num):
        parent_symbol = self.symbol_table.lookup(scope, 'global') 
        if pass_num != 1: return
        var_type, var_name, _, line_num = node[1], node[2], node[3], node[4]
        
        final_type = var_type
        if var_type == 'native':
            if var_name in self.predefined_natives:
                final_type = self.predefined_natives[var_name]
            else:
                err = f"La variable nativa '${var_name}' no está predefinida."
                self.errors.append(self._format_diagnostic(var_name, line_num, err))
                final_type = 'error'
        
        if scope == 'global':
            # Si el scope es global, la definimos como un símbolo global.
            symbol = Symbol(var_name, final_type, 'global', line_num)
            err = self.symbol_table.define(symbol)
            if err:
                self.errors.append(self._format_diagnostic(var_name, line_num, err))
        else:
            # Si el scope no es global (ej. 'front_door'), es un miembro de un objeto.
            member_symbol = Symbol(var_name, final_type, scope, line_num)
            parent_symbol = self.symbol_table.peek(scope, 'global')
            if parent_symbol:
                parent_symbol.members[var_name] = member_symbol
            else:
                # Este caso no debería ocurrir si el parser funciona bien
                err = f"Error interno: No se encontró el objeto padre '{scope}'."
                self.errors.append(self._format_diagnostic(var_name, line_num, err))

    def visit_action_declaration(self, node, scope, pass_num):
        action_name, when_clause, line_num = node[1], node[2], node[3]
        if pass_num == 1:
            parent_symbol = self.symbol_table.lookup(scope, 'global')
            if parent_symbol:
                parent_symbol.members[action_name] = Symbol(action_name, 'action', scope, line_num)
        else: # pass_num == 2
            self.visit(when_clause, scope, pass_num)

    def visit_when_clause(self, node, scope, pass_num):
        if pass_num != 2: return
        self.get_expression_type(node[1], scope)
        for action in node[2]: self.get_expression_type(action, scope)

    def get_expression_type(self, node, scope):
        if not isinstance(node, (tuple, list)):
            if isinstance(node, str) and node.startswith('<') and node.endswith('>'): return 'moment'
            if isinstance(node, str): return 'string'
            if isinstance(node, bool): return 'boolean'
            return 'unknown'
        
        node_type = node[0]
        
        if node_type == 'binary_op':
            op, left_node, right_node = node[2], node[1], node[3]
            left_type = self.get_expression_type(left_node, scope)
            right_type = self.get_expression_type(right_node, scope)
            if op == '==':
                if left_type != 'error' and right_type != 'error' and not self._types_are_compatible(left_type, right_type):
                    err = f"No se puede comparar '{left_type}' con '{right_type}'."
                    # El error se origina en el nodo derecho
                    err_name = right_node[1] if right_node[0] == 'identifier' else str(right_node)
                    self.errors.append(self._format_diagnostic(err_name, 0, err)) # Line num es difícil aquí, pasamos 0
                return 'boolean'
        
        elif node_type == 'member_access':
            base_node, member_name = node[1], node[2]
            base_type = self.get_expression_type(base_node, scope)
            if base_type == 'error': return 'error'
            object_name = base_node[1]
            member_symbol = self.symbol_table.lookup_member(object_name, member_name)
            if not member_symbol:
                err = f"El miembro '{member_name}' no existe en el objeto '{object_name}'."
                self.errors.append(self._format_diagnostic(member_name, 0, err))
                return 'error'
            return member_symbol.type
            
        elif node_type == 'method_call':
            expression_node, method_name = node[1], node[2]
            var_type = self.get_expression_type(expression_node, scope)
            if method_name == 'check':
                if var_type in ['routine', 'action']:
                    err = f"El método '.check()' no se puede aplicar a un tipo '{var_type}'."
                    self.errors.append(self._format_diagnostic(method_name, 0, err))
                    return 'error'
                return var_type
            else:
                err = f"Método desconocido '{method_name}'."
                self.errors.append(self._format_diagnostic(method_name, 0, err))
                return 'error'
        
        elif node_type == 'identifier':
            identifier_name = node[1]
            symbol = self.symbol_table.lookup(identifier_name, scope)
            if not symbol:
                err = f"El objeto '{identifier_name}' no ha sido declarado."
                self.errors.append(self._format_diagnostic(identifier_name, 0, err))
                return 'error'
            return symbol.type
        
        elif node_type == 'show_call':
            self.get_expression_type(node[1], scope)
            return 'void'
        
        elif node_type == 'action_call':
            object_name, action_name = node[1], node[2]
            
            # Verificamos que el objeto exista
            obj_symbol = self.symbol_table.lookup(object_name, scope)
            if not obj_symbol:
                err = f"El objeto '{object_name}' no ha sido declarado."
                self.errors.append(self._format_diagnostic(object_name, 0, err))
                return 'error'

            # Verificamos que la acción sea válida para el tipo de objeto
            obj_type = obj_symbol.type
            if obj_type in self.predefined_actions:
                if action_name not in self.predefined_actions[obj_type]:
                    err = f"La acción '{action_name}' no es válida para un objeto de tipo '{obj_type}'."
                    self.errors.append(self._format_diagnostic(action_name, 0, err))
                    return 'error'
            else:
                # El tipo de objeto no soporta acciones predefinidas (ej. 'routine')
                err = f"No se pueden ejecutar acciones predefinidas en un objeto de tipo '{obj_type}'."
                self.errors.append(self._format_diagnostic(object_name, 0, err))
                return 'error'
                
            return 'action'

        elif node_type == 'assignment':
            var_name, expression_node = node[1], node[2]
            
            # Buscamos la variable en todos los scopes. La asignación puede ser a una variable global o de miembro.
            var_symbol = self.symbol_table.lookup(var_name, scope)
            if not var_symbol:
                 # Si no está en el scope local, puede ser miembro de un objeto
                 for s in self.symbol_table.symbols.values():
                     if var_name in s:
                         var_symbol = s[var_name]
                         break
            
            if not var_symbol:
                err = f"Intento de asignar a una variable no declarada: '{var_name}'."
                self.errors.append(self._format_diagnostic(var_name, 0, err))
                return 'error'

            # Obtenemos el tipo de la expresión a la derecha
            expr_type = self.get_expression_type(expression_node, scope)

            # Comparamos los tipos
            if expr_type != 'error' and not self._types_are_compatible(var_symbol.type, expr_type):
                err = f"Error de tipo: No se puede asignar un valor de tipo '{expr_type}' a la variable '{var_name}' que es de tipo '{var_symbol.type}'."
                self.errors.append(self._format_diagnostic(var_name, 0, err))
                return 'error'
            
            var_symbol.used = True # Marcar la variable como usada en la asignación
            return 'assignment'

def analisis_semantico(ast, source_code):
    if not ast:
        return {'errors': [{"message": "No se pudo generar el árbol sintáctico.", "line": 0, "content": "", "pointer": ""}], 'warnings': []}
    
    analyzer = SemanticAnalyzer(ast, source_code)
    return analyzer.analyze()