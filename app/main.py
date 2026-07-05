import os
import sys
import time
import struct
from pathlib import Path
from PIL import Image

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, DirectoryTree, Label, RadioSet, RadioButton, Select, Button, ProgressBar, Static, Input
from textual.reactive import reactive
from textual.worker import get_current_worker
from rich.text import Text

# Ensure root package is visible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import oppsie
from converter.to_oppsie import convert_to_oppsie
from converter.from_oppsie import convert_from_oppsie
from converter.batch_runner import batch_convert


def load_image_from_path(path: str | os.PathLike) -> Image.Image:
    cleaned_str = str(path).strip().strip('"').strip("'").strip()
    cleaned_path = Path(cleaned_str).resolve()

    if cleaned_path.suffix.lower() == ".oppsie":
        with open(cleaned_path, "rb") as handle:
            return oppsie.decode(handle.read())

    return Image.open(cleaned_path)


class ImageDirectoryTree(DirectoryTree):
    def filter_paths(self, paths):
        valid_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".oppsie"}
        return [
            p for p in paths 
            if p.is_dir() or p.suffix.lower() in valid_extensions
        ]

class PreviewWidget(Static):
    scan_line_active = reactive(False)
    scan_line_y = reactive(0)
    reveal_rows = reactive(0)
    
    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.img = None
        self.image_rows = 0
        self.image_cols = 0
        
    def on_mount(self) -> None:
        self.set_interval(0.08, self.advance_scan_line)
        self.set_interval(0.03, self.advance_reveal)
        
    def set_image(self, img: Image.Image):
        self.img = img
        self.scan_line_active = False
        self.reveal_rows = 0  # Trigger progressive CRT reveal
        self.refresh()
        
    def start_scan(self):
        self.scan_line_active = True
        self.scan_line_y = 0
        self.reveal_rows = 99999
        self.refresh()
        
    def stop_scan(self):
        self.scan_line_active = False
        self.refresh()
        
    def advance_scan_line(self):
        if self.scan_line_active and self.image_rows > 0:
            self.scan_line_y = (self.scan_line_y + 1) % self.image_rows
            self.refresh()
            
    def advance_reveal(self):
        if self.img is not None and self.reveal_rows < self.image_rows:
            self.reveal_rows += 1
            self.refresh()
            
    def render(self) -> Text:
        if self.img is None:
            t = Text(f"\n\n\n\n[ {self.title} ]\n\nNo Image Loaded\n\nSelect a file\nfrom the browser", justify="center")
            t.stylize("bold dim color(10)")
            return t
            
        max_w = 34
        max_h = 24
        
        w, h = self.img.size
        aspect = w / h
        
        if w > h:
            new_w = max_w
            new_h = int(2 * new_w / aspect)
            if new_h > max_h * 2:
                new_h = max_h * 2
                new_w = int(new_h * aspect / 2)
        else:
            new_h = max_h * 2
            new_w = int(new_h * aspect / 2)
            if new_w > max_w:
                new_w = max_w
                new_h = int(2 * new_w / aspect)
                
        new_h = (new_h // 2) * 2
        if new_h < 2: new_h = 2
        if new_w < 1: new_w = 1
        
        resized = self.img.convert("RGB").resize((new_w, new_h), Image.Resampling.BILINEAR)
        
        self.image_rows = new_h // 2
        self.image_cols = new_w
        
        text = Text()
        text.append(f"┌─ {self.title} ({w}x{h}) ─┐\n", style="bold green")
        
        for r_idx in range(self.image_rows):
            if r_idx > self.reveal_rows:
                # CRT faint grid row lines
                text.append("░" * new_w, style="#1e1e2e")  # matches Catppuccin Base background
                text.append("\n")
                continue
                
            if self.scan_line_active and r_idx == self.scan_line_y:
                text.append("▒" * new_w, style="bold color(10) blink")
                text.append("\n")
                continue
                
            y = r_idx * 2
            for x in range(new_w):
                r1, g1, b1 = resized.getpixel((x, y))
                r2, g2, b2 = resized.getpixel((x, y + 1))
                
                # Format hexadecimal strings directly for Rich rendering style properties
                hex_top = f"#{r1:02x}{g1:02x}{b1:02x}"
                hex_bottom = f"#{r2:02x}{g2:02x}{b2:02x}"
                
                text.append("▄", style=f"{hex_bottom} on {hex_top}")
            text.append("\n")
            
        text.append("└" + "─" * new_w + "┘\n", style="bold green")
        return text

class BootScreen(Screen):
    BOOT_LOG = [
        "OPPSIE BIOS v1.0.0 (C) 2026 ANTIGRAVITY CORP.",
        "CPU: AGY-9000 @ 4.77MHz",
        "RAM: 640KB BASE MEMORY",
        "SYSTEM DIAGNOSTIC: PASS",
        "MOUNTING HOST SYSTEM DIRECTORIES... OK",
        "LOADING CODECS:",
        "  - OPPSIE CORE DECODER v1.0 [LOADED]",
        "  - OPPSIE CORE ENCODER v1.0 [LOADED]",
        "  - PIL IMAGE WRAPPERS     [LOADED]",
        "ESTABLISHING CRT PREVIEW GRID... OK",
        "INITIALIZING INTERFACE ENGINE...",
        "MOUNTING DASHBOARD CONTROLS...",
        "SYSTEMS ONLINE. BOOT SUCCESSFUL."
    ]
    
    ASCII_LOGO = r"""
  ____  ____  ____  ____  ____  ____ 
 /  _ \/  __\/  __\/  __\/  _ \/  __\
 | / \||  \/||  \/||  \/|| / \||  \/|
 | \_/||  __/|  __/|  __/| \_/||  __/
 \____/\_/   \_/   \_/   \____/\_/   
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("", id="boot_log"),
            classes="boot_container"
        )

    def on_mount(self) -> None:
        self.log_idx = 0
        self.current_text = ""
        self.set_interval(0.12, self.advance_boot)
        
        if "--test-boot" in sys.argv:
            self.set_timer(2.0, self.app.exit)

    def advance_boot(self):
        boot_log_widget = self.query_one("#boot_log")
        
        if self.log_idx < len(self.BOOT_LOG):
            line = self.BOOT_LOG[self.log_idx]
            self.current_text += line + "\n"
            boot_log_widget.update(Text(self.current_text, style="green"))
            self.log_idx += 1
        elif self.log_idx == len(self.BOOT_LOG):
            self.current_text += "\n" + self.ASCII_LOGO + "\nPress Enter or wait to start...\n"
            boot_log_widget.update(Text(self.current_text, style="bold green"))
            self.log_idx += 1
            if "--test-boot" not in sys.argv:
                self.set_timer(1.5, self.go_main)

    def go_main(self):
        self.app.switch_screen(MainScreen())

    def on_key(self, event) -> None:
        if event.key in ("enter", "return", "space"):
            self.go_main()

class ConvertModal(ModalScreen):
    """Centering pop-up modal containing all conversion parameters."""
    
    def __init__(self, src_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.src_path = src_path

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("[*] CONVERSION SETTINGS", id="modal_title"),
            
            Label("Source File (Anypath):", classes="modal_label"),
            Input(value=str(self.src_path), id="modal_src_path", placeholder="Input file path..."),
            
            Label("Save Destination (Anypath):", classes="modal_label"),
            Input(placeholder="Type output path...", id="modal_dest_path"),
            
            Label("Target Format:", classes="modal_label"),
            RadioSet(
                RadioButton("OPPSIE (.oppsie)", value=True, id="modal_fmt_oppsie"),
                RadioButton("PNG (.png)", id="modal_fmt_png"),
                RadioButton("JPEG (.jpeg)", id="modal_fmt_jpg"),
                RadioButton("WebP (.webp)", id="modal_fmt_webp"),
                RadioButton("BMP (.bmp)", id="modal_fmt_bmp"),
                id="modal_target_fmt"
            ),
            
            Label("Lossy Level (Quantization):", classes="modal_label"),
            Select(
                options=[
                    ("0 (Lossless)", 0),
                    ("1 (Minimal Lossy)", 1),
                    ("2", 2),
                    ("3 (Balanced Lossy)", 3),
                    ("4", 4),
                    ("5 (Extra Savings)", 5),
                    ("6", 6),
                    ("7 (Maximum Size Savings)", 7)
                ],
                value=0,
                allow_blank=False,
                id="modal_lossy_level"
            ),
            
            Horizontal(
                Button("CONVERT [Enter]", variant="success", id="modal_btn_convert"),
                Button("BATCH CONVERT", variant="primary", id="modal_btn_batch"),
                Button("CANCEL [ESC]", variant="error", id="modal_btn_cancel"),
                id="modal_buttons"
            ),
            id="modal_panel"
        )

    def on_mount(self) -> None:
        self.update_dest_path()
        self.query_one("#modal_dest_path").focus()

    def update_dest_path(self):
        try:
            target_fmt_set = self.query_one("#modal_target_fmt")
            selected_rad = target_fmt_set.pressed_button
            target_fmt = "oppsie"
            if selected_rad:
                id_to_fmt = {
                    "modal_fmt_oppsie": "oppsie",
                    "modal_fmt_png": "png",
                    "modal_fmt_jpg": "jpeg",
                    "modal_fmt_webp": "webp",
                    "modal_fmt_bmp": "bmp"
                }
                target_fmt = id_to_fmt.get(selected_rad.id, "oppsie")
                
            dest_ext = ".oppsie" if target_fmt == "oppsie" else f".{target_fmt}"
            src_str = self.query_one("#modal_src_path").value.strip().strip('"').strip("'").strip()
            src_path = Path(src_str).resolve()
            dest_name = src_path.stem + "_converted" + dest_ext
            dest_path = src_path.parent / dest_name
            self.query_one("#modal_dest_path").value = str(dest_path)
        except Exception:
            pass

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self.update_dest_path()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "modal_src_path":
            # Real-time update output file path while typing input file path
            self.update_dest_path()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal_btn_cancel":
            self.dismiss(None)
        else:
            action = "convert" if event.button.id == "modal_btn_convert" else "batch"
            src = self.query_one("#modal_src_path").value.strip().strip('"').strip("'").strip()
            dest = self.query_one("#modal_dest_path").value.strip().strip('"').strip("'").strip()
            
            target_fmt_set = self.query_one("#modal_target_fmt")
            selected_rad = target_fmt_set.pressed_button
            target_fmt = "oppsie"
            if selected_rad:
                id_to_fmt = {
                    "modal_fmt_oppsie": "oppsie",
                    "modal_fmt_png": "png",
                    "modal_fmt_jpg": "jpeg",
                    "modal_fmt_webp": "webp",
                    "modal_fmt_bmp": "bmp"
                }
                target_fmt = id_to_fmt.get(selected_rad.id, "oppsie")
                
            lossy = self.query_one("#modal_lossy_level").value
            
            self.dismiss({
                "action": action,
                "src": src,
                "dest": dest,
                "target_fmt": target_fmt,
                "lossy_level": lossy
            })

class OpenPathModal(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("OPEN FILE", id="open_modal_title"),
            Label("Enter an image or .oppsie path:", classes="modal_label"),
            Input(placeholder="C:/path/to/file.png", id="open_path_input"),
            Horizontal(
                Button("OPEN", variant="success", id="open_path_btn"),
                Button("CANCEL", variant="error", id="cancel_open_btn"),
                id="modal_buttons"
            ),
            id="modal_panel"
        )

    def on_mount(self) -> None:
        self.query_one("#open_path_input").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_open_btn":
            self.dismiss(None)
        else:
            self.dismiss(self.query_one("#open_path_input").value)


class MainScreen(Screen):
    BINDINGS = [
        ("o", "focus_browser", "Focus Browser"),
        ("p", "open_file_prompt", "Open File"),
        ("c", "popup_convert", "Convert Settings [C]"),
        ("q", "quit", "Quit"),
    ]
    
    selected_file = reactive(None)
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            Vertical(
                Label("[+] FILE BROWSER", classes="panel_title"),
                ImageDirectoryTree(os.getcwd(), id="dir_tree"),
                id="left_panel"
            ),
            Vertical(
                Horizontal(
                    PreviewWidget("ORIGINAL PREVIEW", id="orig_preview", classes="preview_container"),
                    PreviewWidget("CONVERTED PREVIEW", id="conv_preview", classes="preview_container"),
                    id="previews_area"
                ),
                Vertical(
                    Label("[>] CONSOLE PROMPT", classes="panel_title"),
                    Horizontal(
                        Label("> Select a file to begin.", id="status_text"),
                        Button("OPEN [P]", variant="primary", id="open_btn"),
                        Button("CONVERT [C]", variant="success", id="convert_btn"),
                        id="console_controls"
                    ),
                    ProgressBar(total=100, show_percentage=True, id="progress_bar"),
                    id="status_bar"
                ),
                id="center_panel"
            ),
            id="workspace"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#progress_bar").display = False
        self.call_after_refresh(self.try_open_cli_path)
        
    def action_focus_browser(self):
        self.query_one("#dir_tree").focus()

    def action_open_file_prompt(self) -> None:
        self.app.push_screen(OpenPathModal(), callback=self.on_open_path_modal_dismissed)

    def try_open_cli_path(self) -> None:
        for arg in sys.argv[1:]:
            if arg.startswith("-"):
                continue
            candidate = Path(arg).expanduser()
            if candidate.exists() and candidate.is_file():
                self.selected_file = candidate.resolve()
                self.load_preview_from_path(candidate)
                return

    def on_open_path_modal_dismissed(self, result) -> None:
        if not result:
            return

        try:
            self.selected_file = Path(str(result).strip().strip('"').strip("'").strip()).resolve()
            self.load_preview_from_path(self.selected_file)
            self.update_status(f"> Opened file: {self.selected_file.name}")
        except Exception as exc:
            self.update_status(f"> Error opening file: {exc}", is_error=True)

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.selected_file = event.path
        self.update_status(f"> Loaded file: {self.selected_file.name} ({self.get_file_size_str(self.selected_file)})")
        self.load_preview_from_path(self.selected_file)

    def load_preview_from_path(self, path: Path):
        try:
            img = load_image_from_path(path)
            self.selected_file = Path(path).resolve()
            self.query_one("#orig_preview").set_image(img)
            self.query_one("#conv_preview").set_image(None)
        except Exception as e:
            self.update_status(f"> Error loading preview: {e}", is_error=True)

    def action_popup_convert(self) -> None:
        self.trigger_popup()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open_btn":
            self.action_open_file_prompt()
        elif event.button.id == "convert_btn":
            self.trigger_popup()

    def trigger_popup(self):
        if not self.selected_file:
            self.update_status("> Error: Please select an image in the browser first.", is_error=True)
            return
            
        self.app.push_screen(ConvertModal(self.selected_file), callback=self.on_modal_dismissed)

    def on_modal_dismissed(self, result) -> None:
        if result is None:
            # Cancelled by user
            return
            
        action = result["action"]
        src_path_str = result["src"]
        dest_path_str = result["dest"]
        target_fmt = result["target_fmt"]
        lossy_level = result["lossy_level"]
        
        try:
            src_path = Path(src_path_str).resolve()
        except Exception as e:
            self.update_status(f"> Error parsing input path: {e}", is_error=True)
            return

        if action == "convert":
            try:
                dest_path = Path(dest_path_str).resolve()
            except Exception as e:
                self.update_status(f"> Error parsing output path: {e}", is_error=True)
                return
                
            if not src_path.exists() or not src_path.is_file():
                self.update_status(f"> Error: Input file does not exist: {src_path_str}", is_error=True)
                return
                
            if dest_path.is_dir() or dest_path_str.endswith(("/", "\\")):
                dest_ext = ".oppsie" if target_fmt == "oppsie" else f".{target_fmt}"
                dest_path = dest_path / (src_path.stem + "_converted" + dest_ext)
                
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.update_status(f"> Error creating output folder: {e}", is_error=True)
                return
                
            self.update_status(f"> Encoding {src_path.name} to {dest_path.name}...")
            self.query_one("#orig_preview").start_scan()
            self.query_one("#conv_preview").start_scan()
            
            pbar = self.query_one("#progress_bar")
            pbar.display = True
            pbar.progress = 10
            
            self.run_worker(
                self.async_convert(src_path, dest_path, target_fmt, lossy_level),
                name="convert_worker",
                group="conversions"
            )
        else:  # batch convert
            src_dir = src_path.parent
            dest_dir = src_dir / "oppsie_batch_out"
            
            self.update_status(f"> Initiating batch convert in folder: {src_dir.name} -> {dest_dir.name}...")
            self.query_one("#progress_bar").display = True
            self.query_one("#progress_bar").progress = 0
            
            self.run_worker(
                self.async_batch_convert(src_dir, dest_dir, target_fmt, lossy_level),
                name="batch_worker"
            )

    async def async_convert(self, src_path: Path, dest_path: Path, target_fmt: str, lossy_level: int):
        t0 = time.perf_counter()
        pbar = self.query_one("#progress_bar")
        pbar.progress = 30
        
        try:
            if target_fmt == "oppsie":
                convert_to_oppsie(str(src_path), str(dest_path), lossy_level=lossy_level)
            else:
                convert_from_oppsie(str(src_path), str(dest_path))
                
            pbar.progress = 80
            time.sleep(0.2)
            elapsed = (time.perf_counter() - t0) * 1000.0
            
            if dest_path.suffix.lower() == ".oppsie":
                with open(dest_path, "rb") as f:
                    decoded_img = oppsie.decode(f.read())
            else:
                decoded_img = Image.open(dest_path)
                
            pbar.progress = 100
            self.call_after_refresh(self.conversion_complete, src_path, dest_path, decoded_img, elapsed)
        except Exception as e:
            self.call_after_refresh(self.conversion_failed, str(e))

    def conversion_complete(self, src_path: Path, dest_path: Path, decoded_img: Image.Image, elapsed: float):
        self.query_one("#orig_preview").stop_scan()
        self.query_one("#conv_preview").stop_scan()
        self.query_one("#progress_bar").display = False
        
        self.query_one("#conv_preview").set_image(decoded_img)
        self.query_one("#dir_tree").reload()
        
        try:
            src_size = src_path.stat().st_size
            dest_size = dest_path.stat().st_size
            ratio = (dest_size / src_size) * 100.0 if src_size > 0 else 0
            size_info = f"({self.get_file_size_str(src_path)}) -> ({self.get_file_size_str(dest_path)}) | Ratio: {ratio:.1f}%"
        except Exception:
            size_info = ""
            
        self.update_status(
            f"> CONVERSION COMPLETE: {src_path.name} -> {dest_path.name} | {size_info} | Time: {elapsed:.1f} ms"
        )

    def conversion_failed(self, error_msg: str):
        self.query_one("#orig_preview").stop_scan()
        self.query_one("#conv_preview").stop_scan()
        self.query_one("#progress_bar").display = False
        self.update_status(f"> Conversion failed: {error_msg}", is_error=True)

    async def async_batch_convert(self, src_dir: Path, dest_dir: Path, target_fmt: str, lossy_level: int):
        try:
            to_oppsie_exts = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif")
            if target_fmt == "oppsie":
                files = []
                for ext in to_oppsie_exts:
                    files.extend(src_dir.glob(f"*{ext}"))
                    files.extend(src_dir.glob(f"*{ext.upper()}"))
            else:
                files = list(src_dir.glob("*.oppsie")) + list(src_dir.glob("*.OPPSIE"))
                
            files = list(set(files))
            total = len(files)
            
            if total == 0:
                self.call_after_refresh(self.batch_complete, [], "No convertible files found.")
                return
                
            results = []
            for idx, f in enumerate(files):
                self.call_after_refresh(self.update_status, f"> Batch: converting {f.name}... ({idx+1}/{total})")
                pbar = self.query_one("#progress_bar")
                self.call_after_refresh(setattr, pbar, "progress", int((idx / total) * 100))
                
                if target_fmt == "oppsie":
                    dest_file = dest_dir / f"{f.stem}.oppsie"
                    try:
                        convert_to_oppsie(str(f), str(dest_file), lossy_level)
                        results.append((f, dest_file, True, ""))
                    except Exception as e:
                        results.append((f, dest_file, False, str(e)))
                else:
                    dest_file = dest_dir / f"{f.stem}.{target_fmt}"
                    try:
                        convert_from_oppsie(str(f), str(dest_file))
                        results.append((f, dest_file, True, ""))
                    except Exception as e:
                        results.append((f, dest_file, False, str(e)))
                        
                time.sleep(0.1)
                
            pbar = self.query_one("#progress_bar")
            self.call_after_refresh(setattr, pbar, "progress", 100)
            self.call_after_refresh(self.batch_complete, results, "")
        except Exception as e:
            self.call_after_refresh(self.conversion_failed, f"Batch error: {e}")

    def batch_complete(self, results, error_msg):
        self.query_one("#progress_bar").display = False
        self.query_one("#dir_tree").reload()
        
        if error_msg:
            self.update_status(f"> Batch process ended: {error_msg}", is_error=True)
            return
            
        successes = sum(1 for r in results if r[2])
        self.update_status(f"> BATCH DONE: Processed {len(results)} files. Success: {successes}, Failed: {len(results)-successes}.")

    def update_status(self, text: str, is_error: bool = False):
        self.status_target_text = text
        self.status_is_error = is_error
        self.status_current_idx = 0
        self.status_displayed_text = ""
        
        if hasattr(self, "typing_timer"):
            try:
                self.typing_timer.stop()
            except Exception:
                pass
        self.typing_timer = self.set_interval(0.012, self.type_status_char)

    def type_status_char(self):
        status_label = self.query_one("#status_text")
        target = self.status_target_text
        
        if self.status_current_idx < len(target):
            char = target[self.status_current_idx]
            self.status_displayed_text += char
            self.status_current_idx += 1
            
            style = "bold red" if self.status_is_error else "bold green"
            status_label.update(Text(self.status_displayed_text + "█", style=style))
        else:
            style = "bold red" if self.status_is_error else "bold green"
            status_label.update(Text(self.status_displayed_text, style=style))
            self.typing_timer.stop()

    def get_file_size_str(self, path: Path) -> str:
        try:
            cleaned_str = str(path).strip().strip('"').strip("'").strip()
            size = Path(cleaned_str).stat().st_size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size/1024:.1f} KB"
            else:
                return f"{size/(1024*1024):.1f} MB"
        except Exception:
            return "Unknown size"

class OppsieApp(App):
    CSS = """
    Screen {
        background: #1e1e2e;
        color: #cdd6f4;
    }


    Header {
        background: #11111b;
        color: #a6e3a1;
        border-bottom: double #a6e3a1;
    }

    Footer {
        background: #11111b;
        color: #b4befe;
    }

    .panel_title {
        background: #313244;
        color: #cdd6f4;
        text-style: bold;
        padding: 0 1;
        width: 100%;
        text-align: center;
    }

    #workspace {
        layout: horizontal;
        height: 1fr;
    }

    #left_panel {
        width: 32;
        border: solid #313244;
        background: #181825;
    }
    #left_panel:focus-within {
        border: double #b4befe;
    }

    #center_panel {
        width: 1fr;
        height: 1fr;
        border: solid #313244;
        background: #1e1e2e;
    }
    #center_panel:focus-within {
        border: double #b4befe;
    }

    #previews_area {
        layout: horizontal;
        height: 1fr;
    }

    .preview_container {
        width: 1fr;
        height: 1fr;
        align: center middle;
        background: #181825;
        margin: 1 1;
    }

    #status_bar {
        height: 8;
        border-top: double #313244;
        background: #11111b;
        padding: 0 2;
    }

    #console_controls {
        layout: horizontal;
        height: 3;
        align: center middle;

        margin-top: 1;
    }

    #status_text {
        width: 1fr;
        height: 2;
    }

    #open_btn {
        width: 12;
    }

    #convert_btn {
        width: 16;
    }

    #progress_bar {
        width: 100%;
        margin-bottom: 1;
    }

    /* Modal Styling */
    ConvertModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.65);
    }

    #modal_panel {
        width: 54;
        height: auto;
        border: double #b4befe;
        background: #1e1e2e;
        padding: 1 2;
    }

    #modal_title {
        background: #89b4fa;
        color: #11111b;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
        height: 3;
        content-align: center middle;
    }

    #open_modal_title {
        background: #89b4fa;
        color: #11111b;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
        height: 3;
        content-align: center middle;
    }

    .modal_label {
        color: #b4befe;
        text-style: bold;
        margin-top: 1;
    }

    #modal_buttons {
        margin-top: 2;
        height: auto;
    }

    #modal_buttons Button {
        width: 1fr;
        margin: 0 1;
    }

    Input {
        background: #181825;
        color: #cdd6f4;
        border: tall #313244;
        padding: 0 1;
        height: 3;
        margin-bottom: 1;
    }
    Input:focus {
        border: tall #b4befe;
    }

    /* Boot Splash screen styling */
    .boot_container {
        align: center middle;
        height: 100%;
        background: #11111b;
    }

    #boot_log {
        width: 80;
        height: 24;
        border: double #a6e3a1;
        background: #11111b;
        padding: 1 2;
    }
    """

    def on_mount(self) -> None:
        self.title = ".oppsie Converter Dashboard"
        self.push_screen(BootScreen())

if __name__ == "__main__":
    app = OppsieApp()
    app.run()
