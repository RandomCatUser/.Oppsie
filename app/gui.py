import os
import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import oppsie


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

        self.image: Optional[Image.Image] = None
        self.photo = None

        self._build_ui()

    def _build_ui(self) -> None:
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="Open...", command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menu.add_cascade(label="File", menu=file_menu)

        toolbar = tk.Frame(self.root, padx=8, pady=8)
        toolbar.pack(fill=tk.X)
        tk.Button(toolbar, text="Open .oppsie / Image", command=self.open_file).pack(side=tk.LEFT)

        self.canvas = tk.Canvas(self.root, bg="#111111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Open an image or .oppsie file to begin")
        tk.Label(self.root, textvariable=self.status_var, anchor=tk.W, padx=8, pady=6).pack(fill=tk.X)

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Image or .oppsie file",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.webp *.gif"),
                ("OPPSIE files", "*.oppsie"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            self.image = load_image_from_path(path)
            self._display_image()
            self.status_var.set(f"Loaded: {Path(path).name}")
        except Exception as exc:  # pragma: no cover - UI error path
            messagebox.showerror("Open failed", str(exc))
            self.status_var.set(f"Error: {exc}")

    def _display_image(self) -> None:
        if self.image is None:
            return
        img = self.image.convert("RGB")
        max_w = self.root.winfo_width() - 40 if self.root.winfo_width() > 1 else 800
        max_h = self.root.winfo_height() - 120 if self.root.winfo_height() > 1 else 600
        width, height = img.size
        scale = min(max_w / width, max_h / height, 1.0)
        if scale < 1.0:
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(max_w // 2, max_h // 2, image=self.photo)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = OppsieViewerApp()
    app.run()


if __name__ == "__main__":
    main()
