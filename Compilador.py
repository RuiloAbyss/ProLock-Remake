import os
import tkinter as tk
from tkinter import font, filedialog, scrolledtext, ttk, messagebox
import lexico as AL
import sintactico as AS
import arbolSintaxis as DA

try:
    from graphviz import Source
    from PIL import Image
    LIBRERIAS_GRAFICAS_OK = True
except ImportError:
    LIBRERIAS_GRAFICAS_OK = False

class CompilerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Compilador de ProLock")
        self.root.geometry("800x600")
        
        self.current_filepath = None #guardar los nombres de los archivos para copiar su nombre en otras exportaciones

        # Fuente base
        self.text_font = font.Font(family="Consolas", size=12)
        

        # --- Menú ---
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0)
        tools_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Archivo", menu=file_menu)
        menu.add_cascade(label="Herramientas", menu=tools_menu)

        file_menu.add_command(label="Abrir", command=self.abrir_archivo)
        file_menu.add_command(label="Guardar", command=self.guardar_archivo)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)
        tools_menu.add_command(label="Compilar", command=self.compilar)
        tools_menu.add_command(label="Ver Tokens", command=self.ver_tokens)
        tools_menu.add_command(label="Ver Árbol Sintáctico", command=self.ver_arbol)

        # --- Frame principal ---
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        self.scrollbar = tk.Scrollbar(frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Zoom
        self.root.bind("<Control-plus>", self.zoom_in)
        self.root.bind("<Control-minus>", self.zoom_out)

        # Numeración
        self.line_numbers = tk.Text(frame, width=4, padx=5, takefocus=0, font=self.text_font, bg="#f0f0f0", state=tk.DISABLED)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # Área de texto
        self.text_area = tk.Text(frame, wrap=tk.NONE, font=self.text_font, undo=True,
                                 yscrollcommand=self.sync_scroll)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_area.config(tabs=(self.text_font.measure(' ' * 3),)) #Tabs de 3 caracters
        self.scrollbar.config(command=self.scroll_both)

        # Eventos
        self.text_area.bind("<KeyRelease>", self.update_line_numbers)
        self.text_area.bind("<MouseWheel>", self.sync_mouse_wheel)
        self.line_numbers.bind("<MouseWheel>", self.sync_mouse_wheel)

        # --- Consola ---
        tk.Label(self.root, text="Consola de Resultados", font=("Helvetica", 12, "bold")).pack(pady=(10, 0))
        self.console_area = scrolledtext.ScrolledText(self.root, height=8, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 10))
        self.console_area.pack(pady=10, fill=tk.X)

        # --- Definición de estilos (tags) para la consola ---
        self.console_area.tag_config('error', foreground='red')
        self.console_area.tag_config('success', foreground='green')

        # Inicializar numeración
        self.update_line_numbers()

    # ---------------- Funciones GUI ----------------
    def sync_scroll(self, *args):
        """Sincroniza scrollbar entre área de texto y numeración"""
        self.line_numbers.yview_moveto(args[0])
        self.scrollbar.set(*args)

    def scroll_both(self, *args):
        """Permite que el scroll controle ambas áreas"""
        self.text_area.yview(*args)
        self.line_numbers.yview(*args)

    def sync_mouse_wheel(self, event):
        """Desplazamiento sincronizado con la rueda del ratón"""
        self.text_area.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.line_numbers.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def update_line_numbers(self, event=None):
        """Actualiza los números de línea sin alterar la posición del scroll."""
        # Guardar la posición actual del scroll
        scroll_pos = self.text_area.yview()

        # Actualizar la numeración
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete("1.0", tk.END)
        total_lines = int(self.text_area.index('end-1c').split('.')[0])
        self.line_numbers.insert(tk.END, "\n".join(str(i) for i in range(1, total_lines + 1)))
        self.line_numbers.config(state=tk.DISABLED)

        # Restaurar posición de scroll
        self.line_numbers.yview_moveto(scroll_pos[0])

    def zoom_in(self, event=None):
        size = self.text_font.cget("size")
        if size < 60:
            self.text_font.config(size=size + 1)
            self.update_line_numbers()

    def zoom_out(self, event=None):
        size = self.text_font.cget("size")
        if size > 6:
            self.text_font.config(size=size - 1)
            self.update_line_numbers()

    def abrir_archivo(self):
        archivo = filedialog.askopenfilename(defaultextension=".txt", filetypes=[("Archivos de texto", "*.txt")])
        
        if archivo:
            self.current_filepath = archivo
            with open(archivo, "r") as file:
                codigo = file.read()
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, codigo)
            self.update_line_numbers()

    def guardar_archivo(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Archivos de texto", "*.txt")])
        if archivo:
            self.current_filepath = archivo
            with open(archivo, "w") as file:
                file.write(self.text_area.get("1.0", tk.END))
    

    def compilar(self):
        """
        Orquesta el análisis léxico y sintáctico en fases separadas.
        La fase sintáctica solo se ejecuta si la léxica es exitosa.
        """
        # 0. PREPARACIÓN
        self.console_area.config(state=tk.NORMAL)
        self.console_area.delete("1.0", tk.END)
        codigo = self.text_area.get("1.0", tk.END)

        # Validar si hay código para analizar
        if not codigo.strip():
            self.console_area.insert(tk.END, "El área de código está vacía.\n")
            self.console_area.config(state=tk.DISABLED)
            return

        # ==========================================================
        # FASE 1: ANÁLISIS LÉXICO
        # ==========================================================
        self.console_area.insert(tk.END, "--- Iniciando Fase 1: Análisis Léxico ---\n")
        
        AL.analisis(codigo) # El módulo léxico se encarga de llenar sus listas de tokens y errores
        
        errores_lexicos = AL.lista_errores_lexicos
        self.tokens_identificados = AL.tokens_identificados

        # CONDICIÓN DE FALLO: Si hay errores léxicos O no se encontró ningún token
        if errores_lexicos or not self.tokens_identificados:
            self.console_area.insert(tk.END, f"Análisis léxico fallido. Se encontraron problemas:\n", 'error')
            
            # Caso especial: no hay tokens, pero tampoco errores (código vacío o con solo comentarios)
            if not self.tokens_identificados and not errores_lexicos:
                self.console_area.insert(tk.END, " - Error: El código no contiene ningún token válido para analizar.\n", 'error')
            
            # Mostrar todos los errores léxicos encontrados
            for token in self.tokens_identificados:
                # Desempaquetamos la tupla del token para acceder a sus datos
                token_value, token_type, token_line, token_col = token
                
                # Si encontramos un token que fue marcado como ERROR...
                if token_type == 'ERROR':
                    # ...construimos el mensaje de error detallado y lo insertamos en la consola.
                    error_msg = f" - Símbolo no reconocido '{token_value}' en línea {token_line}, columna {token_col}\n"
                    self.console_area.insert(tk.END, error_msg, 'error')
        else:
            self.console_area.insert(tk.END, f" Análisis léxico completado. {len(self.tokens_identificados)} tokens encontrados.\n\n", 'success')

        # ==========================================================
        # FASE 2: ANÁLISIS SINTÁCTICO (Solo si la Fase 1 tuvo éxito)
        # ==========================================================
        self.console_area.insert(tk.END, "--- Iniciando Fase 2: Análisis Sintáctico ---\n")
        
        AL.lexer.lineno = 1 # Reiniciamos el contador de lineas después de haber cumplido la fase léxica
        AS.limpiar_errores_sintacticos() # Limpiar errores de una ejecución previa
        
        # El parser de YACC reutiliza el lexer y su estado
        global resultadosSintactico
        resultadosSintactico = AS.parser.parse(codigo, lexer=AL.lexer)
        
        errores_sintacticos = AS.errores_sintacticos

        # CONDICIÓN DE FALLO: Si hay errores sintácticos
        if errores_sintacticos:
            self.console_area.insert(tk.END, f"Análisis sintáctico fallido. Se encontraron problemas de estructura:\n")
            for error in errores_sintacticos:
                self.console_area.insert(tk.END, f" - {error}\n", 'error')
        else:
            self.console_area.insert(tk.END, "Análisis sintáctico completado. La estructura del programa es correcta.\n\n", 'success')
            self.console_area.insert(tk.END, "¡Análisis completado con éxito!\n")
        
        self.console_area.config(state=tk.DISABLED)

    # ... (La función ver_tokens y las otras permanecen igual) ...
    def ver_tokens(self):
        if not hasattr(self, 'tokens_identificados') or not self.tokens_identificados:
            # Mensaje por si se intenta abrir la tabla sin haber analizado
            from tkinter import messagebox
            messagebox.showinfo("Información", "Debes ejecutar el análisis primero para generar la tabla de tokens.")
            return

        tokens_window = tk.Toplevel(self.root)
        tokens_window.title("Tabla de Tokens Generados")
        tokens_window.geometry("500x450")

        # Columnas mejoradas
        columns = ('Valor', 'Tipo', 'Línea', 'Columna')
        tree = ttk.Treeview(tokens_window, columns=columns, show='headings')
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Definir encabezados y tamaño de columnas
        tree.heading('Valor', text='Valor')
        tree.column('Valor', width=150)
        tree.heading('Tipo', text='Tipo de Token')
        tree.column('Tipo', width=150)
        tree.heading('Línea', text='Línea')
        tree.column('Línea', width=50, anchor='center')
        tree.heading('Columna', text='Columna')
        tree.column('Columna', width=60, anchor='center')

        # Configurar una etiqueta (tag) para colorear las filas de error
        tree.tag_configure('error_token', background='#FFDDDD', foreground='red')

        # Llenar la tabla con los tokens
        for token in self.tokens_identificados:
            token_value, token_type, token_line, token_col = token
            
            # Si el token es de tipo ERROR, usa la etiqueta de estilo
            if token_type == 'ERROR':
                tree.insert('', tk.END, values=(token_value, token_type, token_line, token_col), tags=('error_token',))
            else:
                tree.insert('', tk.END, values=(token_value, token_type, token_line, token_col))

    def ver_arbol(self):
        """
        Genera y muestra el árbol de sintaxis, guardando la imagen
        en una subcarpeta llamada 'diagrams'.
        """
        if not LIBRERIAS_GRAFICAS_OK:
            messagebox.showerror("Librerías Faltantes", 
                                "Para ver el árbol, necesitas instalar 'graphviz' y 'pillow'.\n"
                                "Ejecuta en la terminal: pip install graphviz pillow")
            return

        codigo = self.text_area.get("1.0", tk.END)
        
        # Análisis previo y obtención del árbol (sin cambios)
        AL.analisis(codigo)
        AS.limpiar_errores_sintacticos() 
        syntax_tree = AS.parser.parse(codigo, lexer=AL.lexer)
        
        if not syntax_tree or AS.errores_sintacticos:
            messagebox.showerror("Error de Sintaxis", 
                                "No se puede generar el árbol porque el código tiene errores.\n"
                                "Usa 'Analizar Código' para ver los detalles.")
            return

        try:
            # Lógica para obtener el nombre base del archivo (sin cambios)
            output_base_name = "arbol_sin_nombre"
            if self.current_filepath:
                base = os.path.basename(self.current_filepath)
                output_base_name = os.path.splitext(base)[0]
            elif isinstance(syntax_tree, tuple) and len(syntax_tree) > 1:
                output_base_name = syntax_tree[1]

            # 1. Definir el nombre de la subcarpeta y asegurarse de que exista.
            diagram_dir = "diagrams"
            os.makedirs(diagram_dir, exist_ok=True) # <-- Crea la carpeta si no existe

            # 2. Construir la ruta completa del archivo, incluyendo la subcarpeta.
            #    os.path.join es la forma correcta de unir rutas de carpetas y archivos.
            output_filepath = os.path.join(diagram_dir, output_base_name)
            output_image_filepath = f"{output_filepath}.png"
            
            graphviz_code = DA.ply_tree_to_graphviz(syntax_tree)
            graph = Source(graphviz_code)
            
            # Renderizar y abrir usando la nueva ruta completa
            graph.render(output_filepath, format='png', cleanup=True)
            image = Image.open(output_image_filepath)
            image.show()
            
            self.console_area.config(state=tk.NORMAL)
            self.console_area.insert(tk.END, f"[INFO] Árbol para '{output_base_name}' guardado en la carpeta '{diagram_dir}'.\n", 'info')
            self.console_area.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Error de Graphviz", 
                                f"No se pudo renderizar el árbol. ¿Instalaste Graphviz y lo añadiste al PATH?\n\nError: {e}")

# --- Código para correr la aplicación ---
if __name__ == "__main__":
    root = tk.Tk()
    app = CompilerGUI(root)
    root.mainloop()
