import os
import sys
from pathlib import Path
from typing import Optional
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox

# Assuming the library setup remains the same
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import oppsie

# --- Theme Configuration ---
COLORS = {
    "bg": "#121212",
    "surface": "#1e1e1e",
    "primary": "#bb86fc",
    "text": "#e0e0e0",
    "accent": "#333333",
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
        self.root.title(".oppsie Image Viewer")
        self.root.geometry("900x650")
        self.root.configure(bg=COLORS["bg"])

        self.image: Optional[Image.Image] = None
        self.photo = None

        self._build_ui()

    def _build_ui(self) -> None:
        # Toolbar
        self.toolbar = tk.Frame(self.root, bg=COLORS["surface"], padx=15, pady=10)
        self.toolbar.pack(fill=tk.X, side=tk.TOP)

        btn_style = {"bg": COLORS["accent"], "fg": COLORS["text"], "activebackground": COLORS["primary"], "relief": tk.FLAT, "padx": 15, "pady": 5}
        tk.Button(self.toolbar, text="📂 Open Image / .oppsie", command=self.open_file, **btn_style).pack(side=tk.LEFT)

        # Canvas for Image
        self.canvas = tk.Canvas(self.root, bg=COLORS["bg"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Footer
        self.status_var = tk.StringVar(value="Ready.")
        self.footer = tk.Label(self.root, textvariable=self.status_var, bg=COLORS["bg"], fg="#888888", anchor=tk.W, padx=10, pady=5)
        self.footer.pack(fill=tk.X)

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Image or .oppsie file",
            filetypes=[("All supported", "*.png *.jpg *.jpeg *.bmp *.webp *.gif *.oppsie"), ("All files", "*.*")],
        )
        if not path: return
        try:
            self.image = load_image_from_path(path)
            self._display_image()
            self.status_var.set(f"Viewing: {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _display_image(self) -> None:
        if not self.image: return
        
        # Calculate aspect ratio
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        img_w, img_h = self.image.size
        
        scale = min((canvas_w - 20) / img_w, (canvas_h - 20) / img_h, 1.0)
        new_size = (max(1, int(img_w * scale)), max(1, int(img_h * scale)))
        
        display_img = self.image.resize(new_size, Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(display_img)
        
        self.canvas.delete("all")
        self.canvas.create_image(canvas_w // 2, canvas_h // 2, image=self.photo, anchor=tk.CENTER)

    def run(self) -> None:
        self.root.mainloop()

if __name__ == "__main__":
    app = OppsieViewerApp()
    app.run()