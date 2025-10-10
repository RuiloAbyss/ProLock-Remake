def ply_tree_to_graphviz(tree):
    """
    Convierte un árbol de sintaxis de PLY (tuplas/listas) a código Graphviz.
    """
    # Se definen como variables locales para esta función.
    node_counter = 0
    dot_string = 'digraph AST {\n'
    dot_string += '  node [shape=box, style="rounded,filled", fillcolor="lightblue"];\n'
    dot_string += '  edge [color="gray40"];\n'

    def visit(node, parent_id=None):
        """
        Función recursiva para recorrer el árbol y generar el código DOT.
        """
        # 'nonlocal' ahora encuentra las variables en la función externa 'ply_tree_to_graphviz'.
        nonlocal node_counter, dot_string
        current_id = node_counter
        node_counter += 1

        # Si el nodo es una tupla (ej. ('programa', 'nombre', ...))
        if isinstance(node, tuple):
            node_label = str(node[0])
            dot_string += f'  node{current_id} [label="{node_label}"];\n'
            if parent_id is not None:
                dot_string += f'  node{parent_id} -> node{current_id};\n'
            for child in node[1:]:
                visit(child, current_id)

        # Si el nodo es una lista (ej. una secuencia de declaraciones)
        elif isinstance(node, list):
            for item in node:
                visit(item, parent_id)
        
        # Si es un nodo hoja (un valor como un string o un número)
        else:
            node_label = str(node).replace('"', '\\"')
            dot_string += f'  node{current_id} [label="{node_label}", shape=ellipse, fillcolor="lightyellow"];\n'
            if parent_id is not None:
                dot_string += f'  node{parent_id} -> node{current_id};\n'

    visit(tree)
    dot_string += '}'
    return dot_string