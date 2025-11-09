import tkinter as tk

# Configuración del banner
banner_height = 150  # alto del banner en píxeles
banner_color = "#FF000080"  # rojo semitransparente
frame_thickness = 5
message = "¡Alerta de prueba!"
font_family = "Arial"
font_size = 40
font_weight = "bold"
duration_seconds = 5  # duración del banner

# Crear ventana principal
root = tk.Tk()
root.attributes('-topmost', True)  # siempre encima
root.overrideredirect(True)        # sin bordes

# Ajustar a todo el ancho de pantalla
screen_width = root.winfo_screenwidth()
root.geometry(f"{screen_width}x{banner_height}+0+0")  # posicion y tamaño del banner

# Crear marco
frame = tk.Frame(root, bg=banner_color)
frame.pack(fill="both", expand=True)
frame.config(highlightbackground=banner_color, highlightthickness=frame_thickness)

# Mensaje centrado vertical y horizontalmente dentro del banner
label = tk.Label(frame, text=message,
                 font=(font_family, font_size, font_weight),
                 bg=banner_color,
                 fg="white")
label.pack(expand=True)

# Cerrar automáticamente después de duración
root.after(duration_seconds * 1000, root.destroy)

root.mainloop()
