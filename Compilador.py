# Dependencias estándar
import os
import re
import csv
import tkinter as tk
from tkinter import font, filedialog, scrolledtext, ttk, messagebox

# Dependencias internas
import arbolSintaxis as ARSX 

# Módulos del compilador
import lexico as ANLX # Fase 1: Análisis Léxico
import sintactico as ANSX # Fase 2: Análisis Sintáctico
import semantico as ANSM # Fase 3: Análisis Semántico
import intermedio as GNCI # Fase 4: Generación de Código Intermedio
import backend as GNCO # Fase 5: Código Objeto (Backend)

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
            "background": "#F9F9F9",
            "editor_bg": "#FFFFFF",
            "text": "#212121",
            "cursor": "#000000",
            "selection": "#ADD8E6",
            "line_numbers": "#9090A0",
            "console_label": "#424242",
            "success": "#2E7D32",
            "error": "#C62828",
            "info": "#1565C0",
            "scrollbar_thumb": "#E5E5E5",
            "scrollbar_thumb_active": "#E9E9E9"
        }

        # --- Definir el estilo para los TTK Widgets ---
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("Modern.Vertical.TScrollbar", troughcolor=self.colors["background"], background=self.colors["scrollbar_thumb"], gripcount=0, relief='flat')
        style.configure("Modern.Horizontal.TScrollbar", troughcolor=self.colors["background"], background=self.colors["scrollbar_thumb"], gripcount=0, relief='flat')
        style.map("Modern.Vertical.TScrollbar", background=[('active', self.colors["scrollbar_thumb_active"])])
        style.map("Modern.Horizontal.TScrollbar", background=[('active', self.colors["scrollbar_thumb_active"])])
        style.map('Treeview.Heading', background=[('active', self.colors["scrollbar_thumb_active"])])
        style.configure("Treeview", background=self.colors["editor_bg"], foreground=self.colors["text"], fieldbackground=self.colors["editor_bg"], rowheight=25, relief='flat')
        style.configure("Treeview.Heading", background=self.colors["background"], foreground=self.colors["console_label"], font=('Helvetica', 10, 'bold'), relief='flat')

#-------------------------------------------------------------------------------------------
        self.root = root
        self.root.title("Compilador de ProLock")
        self.root.geometry("800x600")
        self.root.config(bg=self.colors["background"])
        
        self.current_filepath = None
        self.syntax_tree = None 
        self.intermediate_code_generator = None
        self.symbol_table = None

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
        tools_menu.add_command(label="Exportar C. Intermedio (CSV)", command=self.exportar_intermedio)
        tools_menu.add_command(label="Generar Código Arduino", command=self.generar_arduino)

        # --- PanedWindow ---
        main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=4, bg=self.colors["background"])
        main_pane.pack(fill=tk.BOTH, expand=True)

        frame = tk.Frame(main_pane, bg=self.colors["background"])
        console_frame = tk.Frame(main_pane, bg=self.colors["background"])
        main_pane.add(frame, minsize=200)
        main_pane.add(console_frame, minsize=150)

        # Scrollbars
        self.h_scrollbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, style="Modern.Horizontal.TScrollbar")
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.scrollbar = ttk.Scrollbar(frame, style="Modern.Vertical.TScrollbar")
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Numeración
        self.line_numbers = tk.Text(frame, width=4, padx=5, takefocus=0, font=self.text_font, 
                                    bg=self.colors["background"], fg=self.colors["line_numbers"], 
                                    state=tk.DISABLED, bd=0)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # Área de texto
        self.text_area = tk.Text(frame, wrap=tk.NONE, font=self.text_font, undo=True,
                                 yscrollcommand=self.sync_scroll,
                                 xscrollcommand=self.h_scrollbar.set,
                                 bg=self.colors["editor_bg"], fg=self.colors["text"],
                                 selectbackground=self.colors["selection"],
                                 insertbackground=self.colors["cursor"], bd=0)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_area.config(tabs=(self.text_font.measure(' ' * 3),))

        # ==========================================
        # CONFIGURACIÓN MINIMALISTA DE COLORES
        # ==========================================
        # Solo conservamos el estilo para comentarios
        self.text_area.tag_configure("comment", foreground="#9E9E9E", font=("Consolas", 12, "italic"))
        
        # Vinculamos a la función simple que solo busca //
        self.text_area.bind("<KeyRelease>", self.highlight_comments)

        self.scrollbar.config(command=self.scroll_both)
        self.h_scrollbar.config(command=self.text_area.xview)

        # Eventos
        self.text_area.bind("<KeyRelease>", self.update_line_numbers, add="+") # add=+ permite múltiples binds
        self.text_area.bind("<MouseWheel>", self.sync_mouse_wheel)
        self.line_numbers.bind("<MouseWheel>", self.sync_mouse_wheel)
        self.root.bind("<Control-plus>", self.zoom_in)
        self.root.bind("<Control-minus>", self.zoom_out)

        # --- Consola ---
        tk.Label(console_frame, text="Consola de Resultados", font=("Helvetica", 12, "bold"),
                 bg=self.colors["background"], fg=self.colors["console_label"]).pack(pady=(5, 0))
        
        self.console_area = scrolledtext.ScrolledText(console_frame, height=12, wrap=tk.WORD, state=tk.DISABLED, 
                                                      font=("Consolas", 10), bg=self.colors["editor_bg"], 
                                                      fg=self.colors["text"], bd=0)
        self.console_area.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)

        self.console_area.tag_config('error', foreground=self.colors["error"])
        self.console_area.tag_config('success', foreground=self.colors["success"])
        self.console_area.tag_config('info', foreground=self.colors["info"])
        self.console_area.tag_config('warning', foreground="#FFA000") 

        self.update_line_numbers()

    # ---------------- Funciones GUI ----------------
    def sync_scroll(self, *args):
        self.line_numbers.yview_moveto(args[0])
        self.scrollbar.set(*args)

    def scroll_both(self, *args):
        self.text_area.yview(*args)
        self.line_numbers.yview(*args)

    def sync_mouse_wheel(self, event):
        self.text_area.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.line_numbers.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def update_line_numbers(self, event=None):
        scroll_pos = self.text_area.yview()
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete("1.0", tk.END)
        total_lines = int(self.text_area.index('end-1c').split('.')[0])
        self.line_numbers.insert(tk.END, "\n".join(str(i) for i in range(1, total_lines + 1)))
        self.line_numbers.config(state=tk.DISABLED)
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

    # ---------------- COLOREADO SIMPLE SOLO COMENTARIOS ----------------
    def highlight_comments(self, event=None):
        self.text_area.tag_remove("comment", "1.0", tk.END)
        
        # Buscar patrón // hasta el final de la línea
        start = "1.0"
        while True:
            # count=tk.IntVar() guarda la longitud de lo encontrado
            count_var = tk.IntVar()
            pos = self.text_area.search(r'//.*', start, stopindex=tk.END, count=count_var, regexp=True)
            if not pos:
                break
            
            end = f"{pos}+{count_var.get()}c"
            self.text_area.tag_add("comment", pos, end)
            start = end

    # ---------------- ARCHIVOS PROLOCK ----------------
    def abrir_archivo(self):
        archivo = filedialog.askopenfilename(
            defaultextension=".pro", 
            filetypes=[("Archivos ProLock", "*.pro"), ("Archivos de texto", "*.txt"), ("Todos", "*.*")]
        )
        
        if archivo:
            self.current_filepath = archivo
            with open(archivo, "r") as file:
                codigo = file.read()
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, codigo)
            self.update_line_numbers()
            self.highlight_comments()

    def guardar_archivo(self):
        archivo = filedialog.asksaveasfilename(
            defaultextension=".pro", 
            filetypes=[("Archivos ProLock", "*.pro"), ("Archivos de texto", "*.txt"), ("Todos", "*.*")]
        )
        if archivo:
            self.current_filepath = archivo
            with open(archivo, "w") as file:
                file.write(self.text_area.get("1.0", tk.END))
            self.root.title(f"Compilador de ProLock - {os.path.basename(archivo)}")

    # ---------------- LÓGICA DE COMPILACIÓN ----------------
    def compilar(self):
        self.console_area.config(state=tk.NORMAL)
        self.console_area.delete("1.0", tk.END)
        codigo = self.text_area.get("1.0", tk.END)
        self.syntax_tree = None 

        if not codigo.strip():
            self.console_area.insert(tk.END, "El área de código está vacía.\n")
            self.console_area.config(state=tk.DISABLED)
            return

        # FASE 1: LÉXICO
        self.console_area.insert(tk.END, "--- Iniciando Fase 1: Análisis Léxico ---\n", 'info')
        ANLX.analisis(codigo)
        self.tokens_identificados = ANLX.tokens_identificados
        errores_lexicos = [token for token in self.tokens_identificados if token[1] == 'ERROR']
        
        if errores_lexicos:
            self.console_area.insert(tk.END, f"Análisis léxico fallido. Se encontraron {len(errores_lexicos)} errores:\n", 'error')
            for error in errores_lexicos:
                self.console_area.insert(tk.END, f" - Símbolo no reconocido '{error[0]}' en línea {error[2]}, columna {error[3]}\n", 'error')
            self.console_area.config(state=tk.DISABLED)
            return
        else:
            self.console_area.insert(tk.END, "Análisis léxico completado. Sin errores.\n\n", 'success')

        # FASE 2: SINTÁCTICO
        self.console_area.insert(tk.END, "--- Iniciando Fase 2: Análisis Sintáctico ---\n", 'info')
        ANSX.limpiar_errores_sintacticos()
        ANLX.lexer.lineno = 1
        
        self.syntax_tree = ANSX.parser.parse(codigo, lexer=ANLX.lexer)
        
        if ANSX.errores_sintacticos or not self.syntax_tree:
            self.console_area.insert(tk.END, "Análisis sintáctico fallido.\n", 'error')
            for error in ANSX.errores_sintacticos:
                self.console_area.insert(tk.END, f" - {error}\n", 'error')
            self.syntax_tree = None
            self.console_area.config(state=tk.DISABLED)
            return
        else:
            self.console_area.insert(tk.END, "Análisis sintáctico completado.\n\n", 'success')

        # FASE 3: SEMÁNTICO
        self.console_area.insert(tk.END, "--- Iniciando Fase 3: Análisis Semántico ---\n", 'info')
        resultados_semanticos = ANSM.analisis_semantico(self.syntax_tree, codigo)
        self.symbol_table = resultados_semanticos.get('symbol_table', None)

        errores = resultados_semanticos.get('errors', [])
        warnings = resultados_semanticos.get('warnings', [])

        if errores:
            self.console_area.insert(tk.END, f"Análisis semántico fallido ({len(errores)} errores):\n", 'error')
            for err in errores:
                error_msg = f" {err['message']}\n   > Línea {err['line']}: {err['content']}\n"
                self.console_area.insert(tk.END, error_msg, 'error')
            self.console_area.insert(tk.END, "\nCompilación detenida por errores semánticos.\n", 'error')
            self.console_area.config(state=tk.DISABLED)
            return
        else:
            self.console_area.insert(tk.END, "Análisis semántico completado.\n\n", 'success')

        if warnings:
            self.console_area.insert(tk.END, f"Advertencias ({len(warnings)}):\n", 'warning')
            for warn in warnings:
                warn_msg = f" {warn['message']}\n   > Línea {warn['line']}: {warn['content']}\n"
                self.console_area.insert(tk.END, warn_msg, 'warning')

        # FASE 4: CÓDIGO INTERMEDIO
        self.console_area.insert(tk.END, "\n--- Iniciando Fase 4: Generación de Código Intermedio ---\n", 'info')
        try:
            self.intermediate_code_generator = GNCI.Intermedio(self.syntax_tree, self.symbol_table)
            intermediate_code_list = self.intermediate_code_generator.generar()
            self.console_area.insert(tk.END, f"Generación de C3D completada. {len(intermediate_code_list)} cuádruplos.\n", 'success')
            self.console_area.insert(tk.END, "\n¡Compilación finalizada con éxito!\n", 'success')
            self.console_area.insert(tk.END, "Puede exportar el código en 'Herramientas'.\n", 'info')
        except Exception as e:
            self.console_area.insert(tk.END, f"Fase de GCI fallida. Error: {e}\n", 'error')
            self.intermediate_code_generator = None

        self.console_area.config(state=tk.DISABLED)

    # FASE 5: CÓDIGO OBJETO (BACKEND)
    def generar_arduino(self):
        if not hasattr(self, 'intermediate_code_generator') or not self.intermediate_code_generator:
             messagebox.showerror("Error", "Primero debes compilar el código exitosamente.")
             return
    
        # 1. Guardar el archivo .ino
        archivo_usuario = filedialog.asksaveasfilename(
            defaultextension=".ino",
            filetypes=[("Arduino Sketch", "*.ino"), ("Todos los archivos", "*.*")],
            title="Guardar Código Arduino",
            initialfile="SmartHome.ino"
        )

        if not archivo_usuario: return
        cuadruplos = self.intermediate_code_generator.codigo_intermedio
        try:
            # 2. Generar el código (.ino)
            generator = GNCO.ArduinoGenerator(cuadruplos) ######
            filepath = generator.generate(ruta_personalizada=archivo_usuario)
            # 3. PREGUNTAR si quiere compilar a .HEX de una vez
            resp = messagebox.askyesno("Compilación Automática", 
                                       f"Código .ino generado correctamente.\n\n"
                                       "¿Deseas generar también el archivo .HEX para Proteus automáticamente?\n"
                                       "(Requiere arduino-cli.exe en la carpeta del proyecto)")
            if resp:
                self.console_area.config(state=tk.NORMAL)
                self.console_area.insert(tk.END, "\n--- Iniciando Compilación Arduino (HEX) ---\n", 'info')
                self.console_area.update() # Forzar actualización visual
                # Llamar al backend para compilar a .HEX
                exito, mensaje = generator.compile_hex(filepath) #######
                
                if exito:
                    self.console_area.insert(tk.END, mensaje + "\n", 'success')
                    messagebox.showinfo("Éxito Total", "¡Archivo .HEX generado!\nAhora solo cárgalo en Proteus.")
                else:
                    self.console_area.insert(tk.END, mensaje + "\n", 'error')
                    messagebox.showerror("Error de Compilación", "No se pudo generar el .hex. Revisa la consola.")
                self.console_area.config(state=tk.DISABLED)
            else:
                 messagebox.showinfo("Éxito", f"Código guardado en: {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Falló la generación: {e}")

    def exportar_intermedio(self):
        if not hasattr(self, 'intermediate_code_generator') or self.intermediate_code_generator is None:
            messagebox.showerror("Error", "Debes compilar primero.")
            return
        codigo_intermedio = self.intermediate_code_generator.codigo_intermedio
        if not codigo_intermedio:
            messagebox.showinfo("Error", "Lista de código vacía.")
            return
        output_base_name = "codigo_intermedio"
        if self.current_filepath:
            base = os.path.basename(self.current_filepath)
            output_base_name = os.path.splitext(base)[0]
        directorio_salida = "CIs"
        os.makedirs(directorio_salida, exist_ok=True)
        nombre_archivo = os.path.join(directorio_salida, f"{output_base_name}_C3D.csv")
        
        encabezado = ['#', 'Operador', 'Argumento 1', 'Argumento 2', 'Resultado']
        try:
            with open(nombre_archivo, 'w', newline='', encoding='utf-8') as archivo_csv:
                escritor = csv.writer(archivo_csv, delimiter=',')
                escritor.writerow(encabezado)
                for i, cuadruplo in enumerate(codigo_intermedio):
                    fila = [i] + list(cuadruplo)
                    escritor.writerow(fila)
            messagebox.showinfo("Éxito", f"Exportado a:\n{nombre_archivo}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def ver_tokens(self):
        if not hasattr(self, 'tokens_identificados') or not self.tokens_identificados:
            messagebox.showinfo("Información", "Debes ejecutar el análisis primero para generar la tabla de tokens.")
            return

        tokens_window = tk.Toplevel(self.root)
        tokens_window.title("Tabla de Tokens Generados")
        tokens_window.geometry("600x450")
        tokens_window.config(bg=self.colors["background"])
        frame = tk.Frame(tokens_window, bg=self.colors["background"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(frame, style="Modern.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        columns = ('Valor', 'Tipo', 'Línea', 'Columna')
        tree = ttk.Treeview(frame, columns=columns, show='headings', 
                            yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) 
        scrollbar.config(command=tree.yview)

        tree.heading('Valor', text='Valor')
        tree.column('Valor', width=180)
        tree.heading('Tipo', text='Tipo de Token')
        tree.column('Tipo', width=150)
        tree.heading('Línea', text='Línea')
        tree.column('Línea', width=60, anchor='center')
        tree.heading('Columna', text='Columna')
        tree.column('Columna', width=60, anchor='center')

        tree.tag_configure('error_token', background='#FFEBEE', foreground='#C62828') 
        tree.tag_configure('evenrow', background='#FFFFFF')
        tree.tag_configure('oddrow', background='#F9F9F9')

        for i, token in enumerate(self.tokens_identificados):
            token_type = token[1]
            
            row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            
            if token_type == 'ERROR':
                final_tags = (row_tag, 'error_token')
            else:
                final_tags = (row_tag,)
                
            tree.insert('', tk.END, values=token, tags=final_tags)

    def ver_arbol(self):
        if not self.syntax_tree:
            messagebox.showinfo("Info", "Compila exitosamente primero.")
            return
        if not LIBRERIAS_GRAFICAS_OK:
            messagebox.showerror("Error", "Faltan graphviz/pillow.")
            return
        try:
            graphviz_code = ARSX.ply_tree_to_graphviz(self.syntax_tree)
            graph = Source(graphviz_code)
            graph.render("diagrams/arbol", format='png', cleanup=True, view=True)
        except Exception as e:
            messagebox.showerror("Error Graphviz", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = CompilerGUI(root)
    root.mainloop()