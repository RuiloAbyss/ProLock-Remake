import os
import tkinter as tk
from tkinter import font, filedialog, scrolledtext, ttk, messagebox
import lexico as ANLX
import sintactico as ANSX
import arbolSintaxis as ARSX
import semantico as ANSM 

try:
    from graphviz import Source
    from PIL import Image
    LIBRERIAS_GRAFICAS_OK = True
except ImportError:
    LIBRERIAS_GRAFICAS_OK = False

class CompilerGUI:
    def __init__(self, root):
#=========================================
# ESTETICA UI
#=========================================
        # --- Paleta de colores ---
        self.colors = {
            "background": "#F9F9F9",         # Fondo general en un gris muy claro (casi blanco)
            "editor_bg": "#FFFFFF",          # Fondo del editor en blanco puro
            "text": "#212121",               # Texto principal en un gris muy oscuro
            "cursor": "#000000",             # Cursor negro
            "selection": "#ADD8E6",         # Selección en azul claro estándar
            "line_numbers": "#9090A0",       # Números de línea en un gris medio
            "console_label": "#424242",      # Etiqueta de la consola en un gris más oscuro
            "success": "#2E7D32",             # Verde oscuro y sobrio
            "error": "#C62828",               # Rojo oscuro y sobrio
            "info": "#1565C0",                # Azul oscuro y sobrio
            "scrollbar_thumb": "#E5E5E5",         # Slider del scrollbar
            "scrollbar_thumb_active": "#E9E9E9" # Slider del scrollbar activo
        }

        # --- Definir el estilo para los TTK Widgets ---
        style = ttk.Style()
        style.theme_use('clam') # Usar un tema base que permita más personalización

        # Configurar el estilo para los scrollbars vertical y horizontal
        style.configure("Modern.Vertical.TScrollbar", 
                        troughcolor=self.colors["background"], 
                        background=self.colors["scrollbar_thumb"],
                        gripcount=0,
                        relief='flat')
        style.configure("Modern.Horizontal.TScrollbar", 
                        troughcolor=self.colors["background"], 
                        background=self.colors["scrollbar_thumb"],
                        gripcount=0,
                        relief='flat')
        
        # Cambiar el color del thumb cuando el mouse pasa por encima
        style.map("Modern.Vertical.TScrollbar",
                  background=[('active', self.colors["scrollbar_thumb_active"])])
        style.map("Modern.Horizontal.TScrollbar",
                  background=[('active', self.colors["scrollbar_thumb_active"])])
        style.map('Treeview.Heading',
                  background=[('active', self.colors["scrollbar_thumb_active"])])
        
        # --- ESTILO PARA LA TABLA DE TOKENS ---
        style.configure("Treeview",
                        background=self.colors["editor_bg"],
                        foreground=self.colors["text"],
                        fieldbackground=self.colors["editor_bg"],
                        rowheight=25, # Aumentar altura de fila para mejor espaciado
                        relief='flat')

        style.configure("Treeview.Heading",
                        background=self.colors["background"],
                        foreground=self.colors["console_label"],
                        font=('Helvetica', 10, 'bold'),
                        relief='flat')
#-------------------------------------------------------------------------------------------
        self.root = root
        self.root.title("Compilador de ProLock")
        self.root.geometry("800x600")
        self.root.config(bg=self.colors["background"])
        
        self.current_filepath = None #guardar los nombres de los archivos para copiar su nombre en otras exportaciones
        self.syntax_tree = None #

        # Fuente base
        self.text_font = font.Font(family="Consolas", size=12)
        
        # --- Menú ---
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0, bg=self.colors["background"], fg=self.colors["text"])
        tools_menu = tk.Menu(menu, tearoff=0, bg=self.colors["background"], fg=self.colors["text"])
        menu.add_cascade(label="Archivo", menu=file_menu)
        menu.add_cascade(label="Herramientas", menu=tools_menu)

        file_menu.add_command(label="Abrir", command=self.abrir_archivo)
        file_menu.add_command(label="Guardar", command=self.guardar_archivo)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)
        tools_menu.add_command(label="Compilar", command=self.compilar)
        tools_menu.add_command(label="Ver Tokens", command=self.ver_tokens)
        tools_menu.add_command(label="Ver Árbol Sintáctico", command=self.ver_arbol)

        # --- PanedWindow como contenedor principal ---
        main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=4, bg=self.colors["background"])
        main_pane.pack(fill=tk.BOTH, expand=True)

        # --- Frame principal ---
        frame = tk.Frame(main_pane)
        console_frame = tk.Frame(main_pane)

        # --- Frames para los paneles ---
        frame = tk.Frame(main_pane, bg=self.colors["background"])
        console_frame = tk.Frame(main_pane, bg=self.colors["background"])
        main_pane.add(frame, minsize=200)
        main_pane.add(console_frame, minsize=150)

        # Scrollbar Horizontal
        self.h_scrollbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, style="Modern.Horizontal.TScrollbar")
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Scrollbar vertical
        self.scrollbar = ttk.Scrollbar(frame, style="Modern.Vertical.TScrollbar")
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Numeración
        self.line_numbers = tk.Text(frame, width=4, padx=5, takefocus=0, font=self.text_font, 
                                    bg=self.colors["background"], fg=self.colors["line_numbers"], 
                                    state=tk.DISABLED, bd=0) # bd=0 para quitar el borde
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # Área de texto
        self.text_area = tk.Text(frame, wrap=tk.NONE, font=self.text_font, undo=True,
                                 yscrollcommand=self.sync_scroll,
                                 xscrollcommand=self.h_scrollbar.set,
                                 bg=self.colors["editor_bg"], fg=self.colors["text"],
                                 selectbackground=self.colors["selection"],
                                 insertbackground=self.colors["cursor"], bd=0) # bd=0 para quitar el borde
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_area.config(tabs=(self.text_font.measure(' ' * 3),))
        self.scrollbar.config(command=self.scroll_both)
        self.h_scrollbar.config(command=self.text_area.xview)

        # Eventos
        self.text_area.bind("<KeyRelease>", self.update_line_numbers)
        self.text_area.bind("<MouseWheel>", self.sync_mouse_wheel)
        self.line_numbers.bind("<MouseWheel>", self.sync_mouse_wheel)
        # Zoom
        self.root.bind("<Control-plus>", self.zoom_in)
        self.root.bind("<Control-minus>", self.zoom_out)

        # --- Consola ---
        tk.Label(console_frame, text="Consola de Resultados", font=("Helvetica", 12, "bold"),
                 bg=self.colors["background"], fg=self.colors["console_label"]).pack(pady=(5, 0))
        
        self.console_area = scrolledtext.ScrolledText(console_frame, height=12, wrap=tk.WORD, state=tk.DISABLED, 
                                                      font=("Consolas", 10), bg=self.colors["editor_bg"], 
                                                      fg=self.colors["text"], bd=0)
        self.console_area.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)

        # --- Definición de estilos (tags) para la consola ---
        self.console_area.tag_config('error', foreground=self.colors["error"])
        self.console_area.tag_config('success', foreground=self.colors["success"])
        self.console_area.tag_config('info', foreground=self.colors["info"])
        self.console_area.tag_config('warning', foreground="#FFA000") 

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
    

    # magico
    def compilar(self):
        """
        Orquesta el análisis léxico, sintáctico y semántico en fases.
        Guarda el árbol de sintaxis en self.syntax_tree si tiene éxito.
        """
        # 0. PREPARACIÓN
        self.console_area.config(state=tk.NORMAL)
        self.console_area.delete("1.0", tk.END)
        codigo = self.text_area.get("1.0", tk.END)
        self.syntax_tree = None # Reinicia el árbol en cada compilación

        if not codigo.strip():
            self.console_area.insert(tk.END, "El área de código está vacía.\n")
            self.console_area.config(state=tk.DISABLED)
            return

        # ==========================================================
        # FASE 1: ANÁLISIS LÉXICO
        # ==========================================================
        self.console_area.insert(tk.END, "--- Iniciando Fase 1: Análisis Léxico ---\n", 'info')
        ANLX.analisis(codigo)
        self.tokens_identificados = ANLX.tokens_identificados
        errores_lexicos = [token for token in self.tokens_identificados if token[1] == 'ERROR']
        
        if errores_lexicos:
            self.console_area.insert(tk.END, f"Análisis léxico fallido. Se encontraron {len(errores_lexicos)} errores:\n", 'error')
            for error in errores_lexicos:
                error_msg = f" - Símbolo no reconocido '{error[0]}' en línea {error[2]}, columna {error[3]}\n"
                self.console_area.insert(tk.END, error_msg, 'error')
            self.console_area.config(state=tk.DISABLED)
            return
        else:
            self.console_area.insert(tk.END, "Análisis léxico completado. Sin errores.\n\n", 'success')

        # ==========================================================
        # FASE 2: ANÁLISIS SINTÁCTICO
        # ==========================================================
        self.console_area.insert(tk.END, "--- Iniciando Fase 2: Análisis Sintáctico ---\n", 'info')
        ANSX.limpiar_errores_sintacticos()
        ANLX.lexer.lineno = 1
        
        # Aquí es donde se genera y se guarda el árbol
        self.syntax_tree = ANSX.parser.parse(codigo, lexer=ANLX.lexer)
        
        if ANSX.errores_sintacticos or not self.syntax_tree:
            self.console_area.insert(tk.END, "Análisis sintáctico fallido. La estructura del programa es incorrecta.\n", 'error')
            for error in ANSX.errores_sintacticos:
                self.console_area.insert(tk.END, f" - {error}\n", 'error')
            # Importante: Si falla, nos aseguramos que el árbol sea None
            self.syntax_tree = None
            self.console_area.config(state=tk.DISABLED)
            return
        else:
            self.console_area.insert(tk.END, "Análisis sintáctico completado. La estructura del programa es correcta.\n\n", 'success')

        # En Compilador.py, dentro de compilar, en la FASE 3

# ==========================================================
# FASE 3: ANÁLISIS SEMÁNTICO
# ==========================================================
        self.console_area.insert(tk.END, "--- Iniciando Fase 3: Análisis Semántico ---\n", 'info')
        # --- Pasamos el código fuente como argumento ---
        resultados_semanticos = ANSM.analisis_semantico(self.syntax_tree, codigo)

        errores = resultados_semanticos.get('errors', [])
        warnings = resultados_semanticos.get('warnings', [])

        if errores:
            self.console_area.insert(tk.END, f"Análisis semántico fallido. Se encontraron {len(errores)} problemas de lógica:\n", 'error')
            for err in errores:
                # Imprimimos el error formateado
                error_msg = f" {err['message']}\n" + \
                            f"   > Línea {err['line']}: {err['content']}\n" + \
                            f"     {err['pointer']}\n"
                self.console_area.insert(tk.END, error_msg, 'error')
        else:
            self.console_area.insert(tk.END, "Análisis semántico completado. La lógica del programa es correcta.\n\n", 'success')
            if not warnings: # Solo muestra éxito total si no hay advertencias
                self.console_area.insert(tk.END, "¡Compilación finalizada con éxito!\n", 'success')

        if warnings:
            self.console_area.insert(tk.END, f"Se encontraron {len(warnings)} advertencias:\n", 'warning')
            for warn in warnings:
                # Imprimimos la advertencia formateada
                warn_msg = f" {warn['message']}\n" + \
                        f"   > Línea {warn['line']}: {warn['content']}\n" + \
                        f"     {warn['pointer']}\n"
                self.console_area.insert(tk.END, warn_msg, 'warning')

        self.console_area.config(state=tk.DISABLED)

    # ... (La función ver_tokens y las otras permanecen igual) ...
    def ver_tokens(self):
        if not hasattr(self, 'tokens_identificados') or not self.tokens_identificados:
            messagebox.showinfo("Información", "Debes ejecutar el análisis primero para generar la tabla de tokens.")
            return

        tokens_window = tk.Toplevel(self.root)
        tokens_window.title("Tabla de Tokens Generados")
        tokens_window.geometry("500x450")
        tokens_window.config(bg=self.colors["background"])

        # Frame principal para padding y contenido
        frame = tk.Frame(tokens_window, bg=self.colors["background"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar vertical (hijo de frame)
        scrollbar = ttk.Scrollbar(frame, style="Modern.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview (CORRECCIÓN 1: El padre ahora es 'frame')
        columns = ('Valor', 'Tipo', 'Línea', 'Columna')
        tree = ttk.Treeview(frame, columns=columns, show='headings', 
                            yscrollcommand=scrollbar.set) # <-- El padre es 'frame'
        
        # Se empaqueta a la izquierda del frame
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) 

        # Configurar el Scrollbar para que controle el Treeview
        scrollbar.config(command=tree.yview)

        # Definir encabezados y tamaño de columnas
        tree.heading('Valor', text='Valor')
        tree.column('Valor', width=150)
        tree.heading('Tipo', text='Tipo de Token')
        tree.column('Tipo', width=150)
        tree.heading('Línea', text='Línea')
        tree.column('Línea', width=50, anchor='center')
        tree.heading('Columna', text='Columna')
        tree.column('Columna', width=60, anchor='center')

        # Configurar etiquetas (tags) con la paleta de colores
        tree.tag_configure('error_token', background='#FFEBEE', foreground=self.colors["error"])
        tree.tag_configure('evenrow', background=self.colors["editor_bg"])
        tree.tag_configure('oddrow', background=self.colors["background"])

        # Llenar la tabla con los tokens y aplicar los estilos de fila
        for i, token in enumerate(self.tokens_identificados):
            token_value, token_type, token_line, token_col = token
            row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            
            if token_type == 'ERROR':
                final_tags = (row_tag, 'error_token')
            else:
                final_tags = (row_tag,)
                
            tree.insert('', tk.END, values=(token_value, token_type, token_line, token_col), tags=final_tags)

    def _generar_arbol_sintactico(self):
        """
        Realiza el análisis léxico y sintáctico para generar el AST.
        Devuelve el árbol si tiene éxito, o None si falla.
        """
        codigo = self.text_area.get("1.0", tk.END)
        if not codigo.strip():
            return None

        # Realizar análisis léxico y sintáctico
        ANLX.analisis(codigo)
        ANSX.limpiar_errores_sintacticos()
        ANLX.lexer.lineno = 1 # Es crucial reiniciar el lexer
        
        syntax_tree = ANSX.parser.parse(codigo, lexer=ANLX.lexer)
        
        # Si hay errores o el árbol no se creó, es un fallo
        if ANSX.errores_sintacticos or not syntax_tree:
            return None
        
        return syntax_tree

    def ver_arbol(self):
        """
        Dibuja y muestra el árbol de sintaxis si ya fue generado por el compilador.
        """
        # 1. VERIFICAR SI EL ÁRBOL YA EXISTE
        if not self.syntax_tree:
            messagebox.showinfo("Árbol no disponible",
                                "Debes compilar el código de FORMA EXITOSA primero para generar el árbol sintáctico.")
            return

        if not LIBRERIAS_GRAFICAS_OK:
            messagebox.showerror("Librerías Faltantes",
                                "Para ver el árbol, necesitas instalar 'graphviz' y 'pillow'.\n"
                                "Ejecuta: pip install graphviz pillow")
            return

        # 2. SI EL ÁRBOL EXISTE, PROCEDE A DIBUJARLO
        try:
            output_base_name = "arbol_sin_nombre"
            if self.current_filepath:
                base = os.path.basename(self.current_filepath)
                output_base_name = os.path.splitext(base)[0]
            
            diagram_dir = "diagrams"
            os.makedirs(diagram_dir, exist_ok=True)
            
            output_filepath = os.path.join(diagram_dir, output_base_name)
            
            # Usa self.syntax_tree directamente
            graphviz_code = ARSX.ply_tree_to_graphviz(self.syntax_tree)
            graph = Source(graphviz_code)
            
            # Renderiza la imagen
            output_image_filepath = graph.render(output_filepath, format='png', cleanup=True)
            
            image = Image.open(output_image_filepath)
            image.show()
            
            self.console_area.config(state=tk.NORMAL)
            self.console_area.insert(tk.END, f"[INFO] Árbol para '{output_base_name}' guardado en '{diagram_dir}'.\n", 'info')
            self.console_area.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Error de Graphviz",
                                f"No se pudo renderizar el árbol. Revisa tu instalación de Graphviz.\n\nError: {e}")

# --- Código para correr la aplicación ---
if __name__ == "__main__":
    root = tk.Tk()
    app = CompilerGUI(root)
    root.mainloop()
