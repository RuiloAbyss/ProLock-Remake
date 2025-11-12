# Ya no se necesitan 'csv' ni 'os' en este archivo
# import csv
# import os

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

    def visitar(self, node):
        if not node: return
        node_type = node[0]
        method_name = f'visitar_{node_type}'
        visitor = getattr(self, method_name, self.visita_generica)
        return visitor(node)

    def visita_generica(self, node):
        if isinstance(node, (list, tuple)):
            for child in node[1:]: self.visitar(child)
            
    def visitar_programa(self, node):
        # 1. Declaraciones
        for decl in node[2]:
            if decl[0] != 'routine_declaration':
                self.visitar(decl)
        
        # 2. Generar el Bucle Principal
        self.emitir('LABEL', '', '', 'MAIN_LOOP')
        
        # 3. Visitar todas las rutinas
        for decl in node[2]:
            if decl[0] == 'routine_declaration':
                self.visitar(decl)
                
        # 4. Salto de vuelta
        self.emitir('GOTO', '', '', 'MAIN_LOOP')

    def visitar_lock_declaration(self, node):
        for state_var in node[2]: self.visitar(state_var)

    def visitar_clock_declaration(self, node):
        for state_var in node[2]: self.visitar(state_var)
    
    def visitar_variable_declaration(self, node):
        var_name = node[2]
        value_node = node[3]
        
        if value_node is not None:
            source_location = self.visitar_expresion(value_node)
            
            if source_location != 'void':
                self.emitir('ASSIGN', source_location, '', var_name)

    def visitar_routine_declaration(self, node):
        for action in node[2]: self.visitar(action)

    def visitar_action_declaration(self, node):
        self.visitar(node[2])

 # CONDICIONALES WHEN
    def visitar_when_clause(self, node):
        condition_node = node[1]
        actions = node[2]
        
        if self._es_condicion_de_tiempo(condition_node):
            # Si la condición usa 'main_clock.TIME', es una espera de tiempo.
            self.emitir('WAIT_TICK', '1s', '', '') # Espera 1 segundo
        else:
            # Si no, asumimos que es una espera de entrada.
            # (Una mejora sería identificar la variable de entrada específica TENTATIVO)
            self.emitir('WAIT_INPUT', '', '', '') # Espera por una entrada externa

        condition_location = self.visitar_expresion(condition_node)
        
        label_then = self.nueva_etiqueta()
        label_end = self.nueva_etiqueta()
        
        # IF t1 GOTO L_THEN
        self.emitir('IF', condition_location, '', label_then) 
        self.emitir('GOTO', '', '', label_end)
        
        self.emitir('LABEL', '', '', label_then)
        
        for action in actions:
            self.visitar_expresion(action)
            
        self.emitir('LABEL', '', '', label_end)
    
# WHEN TIPO "TIEMPO"
    def _es_condicion_de_tiempo(self, nodo_condicion):
        """
        Función auxiliar recursiva para determinar si una condición
        """
        if not isinstance(nodo_condicion, (list, tuple)):
            return False
        
        # Caso base: ('member_access', ('identifier', 'main_clock', ...), '$TIME', ...)
        if nodo_condicion[0] == 'member_access':
            obj_name = nodo_condicion[1][1]
            member_name = nodo_condicion[2]
            if obj_name == 'main_clock' and member_name == '$TIME':
                return True
        
        # Búsqueda recursiva en los hijos del nodo
        for hijo in nodo_condicion[1:]:
            if self._es_condicion_de_tiempo(hijo):
                return True
        return False

# WHEN TIPO "ENTRADA"


    def visitar_expresion(self, node):
        if not isinstance(node, (tuple, list)):
            if node == 'true' or node == 'false': return node
            if isinstance(node, (int, float, str)): return str(node)
            return str(node)
        
        node_type = node[0]
        
        if node_type == 'binary_op':
            op, left_node, right_node = node[1], node[2], node[3]
            
            left_loc = self.visitar_expresion(left_node)
            right_loc = self.visitar_expresion(right_node)
            
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
            source_loc = self.visitar_expresion(expression_node)
            self.emitir('ASSIGN', source_loc, '', var_name)
            return 'assignment'

        elif node_type == 'member_assignment':
            member_access_node, expression_node = node[1], node[2]
            target_loc = self.visitar_expresion(member_access_node)
            source_loc = self.visitar_expresion(expression_node)
            self.emitir('ASSIGN', source_loc, '', target_loc)
            return 'member_assignment'

        elif node_type == 'action_call':
            object_name, action_name = node[1], node[2]
            self.emitir('CALL', object_name, '', action_name)
            return 'action_call'
            
        elif node_type == 'show_call':
            arg_loc = self.visitar_expresion(node[1])
            self.emitir('PRINT', arg_loc, '', '')
            return 'show_call'
            
        elif node_type == 'method_call':
            expression_node, method_name = node[1], node[2]
            base_loc = self.visitar_expresion(expression_node)
            result_temp = self.nueva_temporal()
            self.emitir(method_name.upper(), base_loc, '', result_temp)
            return result_temp
            
        return 'unknown'
    