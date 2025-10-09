import tkinter as tk
from tkinter import font, filedialog, scrolledtext, ttk
import lexico as AL
import sintactico as AS

class CompilerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador Léxico y Sintáctico")
        self.root.geometry("800x600")
        
        # Almacena los tokens de la última compilación
        self.tokens_identificados = []

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

        # --- Frame principal ---
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        self.scrollbar = tk.Scrollbar(frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Numeración
        self.line_numbers = tk.Text(frame, width=4, padx=5, takefocus=0, font=self.text_font,
                                    bg="#f0f0f0", state=tk.DISABLED)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # Área de texto
        self.text_area = tk.Text(frame, wrap=tk.NONE, font=self.text_font, undo=True,
                                 yscrollcommand=self.sync_scroll)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar.config(command=self.scroll_both)

        # Eventos
        self.text_area.bind("<KeyRelease>", self.update_line_numbers)
        self.text_area.bind("<MouseWheel>", self.sync_mouse_wheel)
        self.line_numbers.bind("<MouseWheel>", self.sync_mouse_wheel)
        self.text_area.bind("<Configure>", self.update_line_numbers)


        # --- Consola ---
        tk.Label(self.root, text="Consola de Resultados", font=("Helvetica", 12, "bold")).pack(pady=(10, 0))
        self.console_area = scrolledtext.ScrolledText(self.root, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.console_area.pack(pady=10, fill=tk.X, padx=10)

        # Zoom
        self.root.bind("<Control-plus>", self.zoom_in)
        self.root.bind("<Control-minus>", self.zoom_out)

        # Inicializar numeración
        self.update_line_numbers()

    # ---------------- Funciones GUI ----------------
    def sync_scroll(self, *args):
        self.line_numbers.yview_moveto(args[0])
        self.scrollbar.set(*args)
        self.update_line_numbers()

    def scroll_both(self, *args):
        self.text_area.yview(*args)
        self.line_numbers.yview(*args)
        self.update_line_numbers()

    def sync_mouse_wheel(self, event):
        self.text_area.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.line_numbers.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.update_line_numbers()
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

    def abrir_archivo(self):
        archivo = filedialog.askopenfilename(defaultextension=".txt", filetypes=[("Archivos de texto", "*.txt")])
        if archivo:
            with open(archivo, "r") as file:
                codigo = file.read()
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, codigo)
            self.update_line_numbers()

    def guardar_archivo(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Archivos de texto", "*.txt")])
        if archivo:
            with open(archivo, "w") as file:
                file.write(self.text_area.get("1.0", tk.END))
    
    def compilar(self):
        self.console_area.config(state=tk.NORMAL)
        self.console_area.delete("1.0", tk.END)
        
        codigo = self.text_area.get("1.0", tk.END)

        # 1. Análisis Léxico
        # La función 'analisis' ahora limpia sus propias listas y devuelve los resultados
        AL.analisis(codigo)
        self.tokens_identificados = AL.tokens_identificados
        errores_lexicos = AL.lista_errores_lexicos

        has_errors = False
        if errores_lexicos:
            has_errors = True
            for error in errores_lexicos:
                self.console_area.insert(tk.END, f"[Error Léxico] {error}\n")
        
        # Si hay errores léxicos, no tiene sentido continuar con el sintáctico
        if has_errors:
            self.console_area.insert(tk.END, "[Compilación fallida] Se encontraron errores léxicos.\n")
            self.console_area.config(state=tk.DISABLED)
            return

        # 2. Análisis Sintáctico
        # Limpiar lista de errores sintácticos antes de cada análisis
        AS.limpiar_errores_sintacticos()
        
        # Parsear el código
        try:
            resultadosSintactico = AS.parser.parse(codigo, lexer=AL.lexer)
            errores_sintacticos = AS.errores_Sinc_Desc
            
            if errores_sintacticos:
                 has_errors = True
                 for error in errores_sintacticos:
                    self.console_area.insert(tk.END, f"[Error Sintáctico] {error}\n")

        except Exception as e:
            has_errors = True
            self.console_area.insert(tk.END, f"[Error Crítico del Parser] {str(e)}\n")

        # 3. Mostrar resultado final
        if not has_errors:
             self.console_area.insert(tk.END, "¡Compilación exitosa! No se encontraron errores léxicos ni sintácticos.\n")
        else:
            self.console_area.insert(tk.END, "[Compilación finalizada con errores]\n")

        self.console_area.config(state=tk.DISABLED)
        
    def ver_tokens(self):
        if not self.tokens_identificados:
            tk.messagebox.showinfo("Tokens", "Aún no se ha compilado ningún código.")
            return

        tokens_window = tk.Toplevel(self.root)
        tokens_window.title("Tokens Identificados")
        tokens_window.geometry("400x450")
        
        table_frame = tk.Frame(tokens_window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ('Valor', 'Tipo', 'Línea', 'Columna')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', yscrollcommand=scrollbar.set)
        tree.pack(fill=tk.BOTH, expand=True)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=90, anchor='center')

        # Llenar la tabla con los tokens (usando la lista de la instancia)
        for token in self.tokens_identificados:
            tree.insert('', tk.END, values=token)
            
        scrollbar.config(command=tree.yview)

if __name__ == "__main__":
    root = tk.Tk()
    app = CompilerGUI(root)
    root.mainloop()