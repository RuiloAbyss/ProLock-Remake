class Intermedio:
    """
    Clase encargada de la Generación de Código Intermedio (C3D)
    mediante la técnica de Cuádruplos.
    """
    def __init__(self, ast, tabla_simbolos):
        self.ast = ast
        self.tabla_simbolos = tabla_simbolos # Nota: esta variable se recibe pero no se usa en la generación
        self.contador_temp = 0      # Contador para variables temporales (t1, t2, ...)
        self.contador_etiqueta = 0     # Contador para etiquetas (L1, L2, ...)
        self.codigo_intermedio = []           # Lista para almacenar los cuádruplos generados

    def nueva_temporal(self):
        """Genera una nueva variable temporal (ej. t1, t2)."""
        self.contador_temp += 1
        return f't{self.contador_temp}'

    def nueva_etiqueta(self):
        """Genera una nueva etiqueta (ej. L1, L2)."""
        self.contador_etiqueta += 1
        return f'L{self.contador_etiqueta}'

    def emitir(self, op, arg1, arg2, resultado):
        """Añade un cuádruplo al código intermedio."""
        self.codigo_intermedio.append((op, arg1, arg2, resultado))

    def generar(self):
        """Función principal para iniciar la generación."""
        self.codigo_intermedio = []
        self.contador_temp = 0
        self.contador_etiqueta = 0
        self.visitar_programa(self.ast)
        return self.codigo_intermedio

    # --- Métodos de Visita para la Generación de C3D ---

    def visitar(self, node, scope='global'): 
        if not node: return
        node_type = node[0]
        method_name = f'visitar_{node_type}'
        visitor = getattr(self, method_name, self.visita_generica)
        return visitor(node, scope)

    def visita_generica(self, node, scope):
        if isinstance(node, (list, tuple)):
            for child in node[1:]: self.visitar(child, scope)
            
    # OPTIMIZACIÓNES --- 
    '''
    1. SEPARACIÓN DE BLOQUES DE ESPERA DE TIEMPO E INPUT EN EL BUCLE PRINCIPAL
    2. AHORA LOS WHEN DE ESPERA SE AGRUPAN EN UN SOLO WAITER EN VEZ DE ASIGNAR UNO POR CLAUSULA
    3. SE ELIMINA CÓDIGO MUERTO EN ASIGNACIONES DE VARIABLES NO USADAS MEDIANTE LA HERENCIA DE SCOPE 
       Y LA VISITA DE LA TABLA DE SÍMBOLOS
    '''
    def visitar_programa(self, node, scope='global'): 
        # 1. Declaraciones globales
        for decl in node[2]:
            if decl[0] != 'routine_declaration':
                self.visitar(decl, 'global') # <-- Pasamos el scope 'global'
        
        # 2. Bucle Principal
        self.emitir('LABEL', '', '', 'MAIN_LOOP')

        # 3. Recolectar acciones CON SU ÁMBITO
        time_actions = []
        input_actions = []
        for decl in node[2]:
            if decl[0] == 'routine_declaration':
                routine_name = decl[1] # <-- Este es el ÁMBITO de las acciones
                for action in decl[2]:
                    when_clause = action[2]
                    condition_node = when_clause[1]
                    # Guardamos la acción Y su ámbito
                    action_with_scope = (action, routine_name) 
                    if self._es_condicion_de_tiempo(condition_node):
                        time_actions.append(action_with_scope)
                    else:
                        input_actions.append(action_with_scope)

        # 4. === BLOQUE DE TIEMPO ===
        # Detecta el tipo de espera y agrupa todas las acciones de tiempo
        self.emitir('WAIT_TICK', '1s', '', '')
        for action, action_scope in time_actions:
            self.visitar(action, action_scope) 
        
        # 5. === BLOQUE DE INPUT ===
        self.emitir('WAIT_INPUT', '', '', '')
        for action, action_scope in input_actions:
            self.visitar(action, action_scope) 
        
        # 6. Salto de vuelta
        self.emitir('GOTO', '', '', 'MAIN_LOOP')

    def visitar_lock_declaration(self, node, scope):
        lock_name = node[1]
        for state_var in node[2]: 
            self.visitar(state_var, lock_name) 

    def visitar_clock_declaration(self, node, scope):
        clock_name = node[1]
        for state_var in node[2]: 
            self.visitar(state_var, clock_name) 
    
    def visitar_variable_declaration(self, node, scope):  
        # El nodo es: ('variable_declaration', tipo, nombre, valor, linea)
        var_name = node[2]
        value_node = node[3]
        
        # --- OPTIMIZACIÓN DE CÓDIGO MUERTO ---
        # 1. Consultar la tabla de símbolos para ver si la variable fue USADA.
        #    Usamos 'peek' para no alterar el estado de 'used'.
        symbol = self.tabla_simbolos.peek(var_name, scope)

        # 2. Si el símbolo existe pero su bandera 'used' es False, no generamos código.
        if symbol and not symbol.used:
            return  # <-- ¡No hacer nada! La asignación es código muerto.
        
        # 3. Si la variable sí fue usada (o no se encontró, lo cual es raro aquí),
        #    generamos el código de asignación como antes.
        if value_node is not None:
            source_location = self.visitar_expresion(value_node, scope) # Pasamos el scope
            
            if source_location != 'void':
                self.emitir('ASSIGN', source_location, '', var_name)

    def visitar_routine_declaration(self, node, scope):
        routine_name = node[1]
        for action in node[2]: self.visitar(action, routine_name)

    def visitar_action_declaration(self, node, scope):
        self.visitar(node[2], scope)

 # CONDICIONALES WHEN
    def visitar_when_clause(self, node, scope):
        condition_node = node[1]
        actions = node[2]
        
        # 1. Generar código para la expresión condicional
        condition_location = self.visitar_expresion(condition_node, scope)
        
        # 2. Etiquetas
        label_then = self.nueva_etiqueta()
        label_end = self.nueva_etiqueta()
        
        # 3. Salto Condicional
        self.emitir('IF', condition_location, '', label_then) 
        self.emitir('GOTO', '', '', label_end)
        
        # 4. Bloque de acciones
        self.emitir('LABEL', '', '', label_then)
        for action in actions:
            self.visitar_expresion(action, scope)
        self.emitir('LABEL', '', '', label_end)
    
# WHEN TIPO "TIEMPO"
    def _es_condicion_de_tiempo(self, nodo_condicion):
        """
        Función auxiliar recursiva para determinar si una condición
        depende de 'main_clock.TIME'.
        """
        if not isinstance(nodo_condicion, (list, tuple)):
            return False
        
        # Caso base: ('member_access', ('identifier', 'main_clock', ...), '$TIME', ...)
        if nodo_condicion[0] == 'member_access':
            # Asumimos que el nodo base es un identificador
            if nodo_condicion[1][0] == 'identifier':
                obj_name = nodo_condicion[1][1]
                member_name = nodo_condicion[2]
                if obj_name == 'main_clock' and member_name == '$TIME':
                    return True
        
        # OPTIMIZACIÓN ---- Búsqueda recursiva en los hijos del nodo
        for hijo in nodo_condicion[1:]:
            if self._es_condicion_de_tiempo(hijo):
                return True
        return False

    def visitar_expresion(self, node, scope):
        if not isinstance(node, (tuple, list)):
            if node == 'true' or node == 'false': return node
            if isinstance(node, (int, float, str)): return str(node)
            return str(node)
        
        node_type = node[0]
        
        if node_type == 'binary_op':
            op, left_node, right_node = node[1], node[2], node[3]
            
            left_loc = self.visitar_expresion(left_node, scope)
            right_loc = self.visitar_expresion(right_node, scope)
            
            result_temp = self.nueva_temporal()
            self.emitir(op, left_loc, right_loc, result_temp) # Antes decía selfum.emitir
            return result_temp
        
        elif node_type == 'member_access':
            object_name = node[1][1]
            member_name = node[2].lstrip('$')
            return f"{object_name}.{member_name}"

        elif node_type == 'identifier':
            return node[1]

        elif node_type == 'assignment':
            var_name, expression_node = node[1], node[2]
            source_loc = self.visitar_expresion(expression_node, scope)
            self.emitir('ASSIGN', source_loc, '', var_name)
            return 'assignment'

        elif node_type == 'member_assignment':
            member_access_node, expression_node = node[1], node[2]
            target_loc = self.visitar_expresion(member_access_node, scope)
            source_loc = self.visitar_expresion(expression_node, scope)
            self.emitir('ASSIGN', source_loc, '', target_loc)
            return 'member_assignment'

        elif node_type == 'action_call':
            object_name, action_name = node[1], node[2]
            self.emitir('CALL', object_name, '', action_name)
            return 'action_call'
            
        elif node_type == 'show_call':
            arg_loc = self.visitar_expresion(node[1], scope)
            self.emitir('PRINT', arg_loc, '', '')
            return 'show_call'
            
        elif node_type == 'method_call':
            expression_node, method_name = node[1], node[2]
            base_loc = self.visitar_expresion(expression_node, scope)
            result_temp = self.nueva_temporal()
            self.emitir(method_name.upper(), base_loc, '', result_temp)
            return result_temp
            
        return 'unknown'
    