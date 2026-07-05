import os
import sys
from pathlib import Path
from typing import Optional
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox

# Ensure the parent directory is in the path to find the 'oppsie' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import oppsie

# Defining theme colors at the module level with NO indentation
COLORS = {
    "bg": "#0D0D0D",
    "surface": "#1A1A1A",
    "accent": "#00E5FF",
    "accent_hover": "#00B8D4",
    "text_main": "#E0E0E0",
    "text_dim": "#808080"
}

def load_image_from_path(path: str | os.PathLike) -> Image.Image:
    cleaned_path = Path(str(path).strip().strip('"').strip("'").strip()).resolve()
    if cleaned_path.suffix.lower() == ".oppsie":
        with open(cleaned_path, "rb") as handle:
            return oppsie.decode(handle.read())
    return Image.open(cleaned_path)

class OppsieViewerApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Oppsie | Image Viewer")
        self.root.geometry("1000x700")
        self.root.configure(bg=COLORS["bg"])
        
        self.image: Optional[Image.Image] = None
        self.photo = None
        self.zoom_scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_data = {"x": 0, "y": 0}
        self.status_var = tk.StringVar(value="Waiting for input...")
        
        self._build_ui()

    def _build_ui(self) -> None:
        self.header = tk.Frame(self.root, bg=COLORS["surface"], padx=20, pady=15)
        self.header.pack(fill=tk.X, side=tk.TOP)

        self.btn_open = tk.Label(
            self.header, text="📁 OPEN FILE", bg=COLORS["accent"], fg="#000000",
            font=("Segoe UI", 10, "bold"), padx=20, pady=8, cursor="hand2"
        )
        self.btn_open.pack(side=tk.LEFT)
        
        # Hover effect
        self.btn_open.bind("<Enter>", lambda e: self.btn_open.configure(bg=COLORS["accent_hover"]))
        self.btn_open.bind("<Leave>", lambda e: self.btn_open.configure(bg=COLORS["accent"]))
        self.btn_open.bind("<Button-1>", lambda e: self.open_file())

        self.canvas = tk.Canvas(self.root, bg=COLORS["bg"], highlightthickness=1, highlightbackground=COLORS["surface"])
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 10))
        
        # Bind mouse wheel for zooming and drag for panning
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)

        self.footer = tk.Label(
            self.root, textvariable=self.status_var, bg=COLORS["bg"], 
            fg=COLORS["text_dim"], font=("Consolas", 9), anchor=tk.W, padx=20, pady=10
        )
        self.footer.pack(fill=tk.X)

    def _on_drag_start(self, event: tk.Event) -> None:
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def _on_drag_motion(self, event: tk.Event) -> None:
        delta_x = event.x - self.drag_data["x"]
        delta_y = event.y - self.drag_data["y"]
        self.pan_x += delta_x
        self.pan_y += delta_y
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self._display_image()

    def _on_zoom(self, event: tk.Event) -> None:
        if not self.image: return
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom_scale *= factor
        self._display_image()

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Image or .oppsie file",
            filetypes=[("All supported", "*.png *.jpg *.jpeg *.bmp *.webp *.gif *.oppsie"), ("All files", "*.*")],
        )
        if not path: return
        try:
            self.image = load_image_from_path(path)
            self.zoom_scale = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self._display_image()
            self.status_var.set(f"Viewing: {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _display_image(self) -> None:
        if not self.image: return
        
        base_w, base_h = self.image.size
        new_w = max(1, int(base_w * self.zoom_scale))
        new_h = max(1, int(base_h * self.zoom_scale))
        
        display_img = self.image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(display_img)
        
        self.canvas.delete("all")
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        # Add pan offsets to the image position
        self.canvas.create_image(
            (canvas_w // 2) + self.pan_x, 
            (canvas_h // 2) + self.pan_y, 
            image=self.photo, anchor=tk.CENTER
        )

    def run(self) -> None:
        self.root.mainloop()

if __name__ == "__main__":
    app = OppsieViewerApp()
    app.run()