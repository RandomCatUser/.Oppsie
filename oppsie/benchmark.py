import os
import sys
import time
import io
from PIL import Image, ImageDraw

# Ensure the root package is visible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import oppsie

def generate_benchmark_images():
    """Generates three types of images programmatically to avoid external assets."""
    images = {}
    
    # 1. Flat Graphic (logo/flag style) - 512x512
    flat_img = Image.new("RGB", (512, 512), (30, 41, 59))
    draw = ImageDraw.Draw(flat_img)
    draw.rectangle([50, 50, 462, 462], fill=(234, 179, 8))
    draw.ellipse([128, 128, 384, 384], fill=(239, 68, 68))
    draw.rectangle([200, 200, 312, 312], fill=(59, 130, 246))
    images["Flat Graphic"] = flat_img
    
    # 2. Gradient/Photo style - 512x512
    grad_img = Image.new("RGB", (512, 512))
    pixels = []
    for y in range(512):
        for x in range(512):
            r = (x * 255) // 512
            g = (y * 255) // 512
            b = ((x + y) * 255) // 1024
            pixels.append((r, g, b))
    grad_img.putdata(pixels)
    images["Gradient Photo"] = grad_img
    
    # 3. Pixel Art style (RGBA) - 512x512
    pixel_img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    colors = [
        (255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255),
        (255, 255, 0, 255), (0, 255, 255, 255), (255, 0, 255, 255)
    ]
    for i in range(128):
        for j in range(128):
            if (i // 8 + j // 8) % 2 == 0:
                pixel_img.putpixel((i, j), colors[(i // 8) % len(colors)])
            else:
                pixel_img.putpixel((i, j), (0, 0, 0, 0))
                
    images["Pixel Art"] = pixel_img.resize((512, 512), Image.Resampling.NEAREST)
    return images

def run_benchmarks():
    images = generate_benchmark_images()
    
    formats = [
        ("OPPSIE (Lossless)", lambda img: oppsie.encode(img, 0), lambda d: oppsie.decode(d)),
        ("OPPSIE (Lossy L3)", lambda img: oppsie.encode(img, 3), lambda d: oppsie.decode(d)),
        ("OPPSIE (Lossy L5)", lambda img: oppsie.encode(img, 5), lambda d: oppsie.decode(d)),
        ("PNG", lambda img: save_to_mem(img, "PNG"), lambda d: load_from_mem(d)),
        ("JPEG", lambda img: save_to_mem(img.convert("RGB"), "JPEG", quality=80), lambda d: load_from_mem(d)),
        ("WebP (Lossless)", lambda img: save_to_mem(img, "WEBP", lossless=True), lambda d: load_from_mem(d)),
        ("WebP (Lossy)", lambda img: save_to_mem(img.convert("RGB"), "WEBP", quality=80), lambda d: load_from_mem(d)),
    ]
    
    print("=" * 88)
    print(f"{'IMAGE TYPE / FORMAT':<25} | {'SIZE (KB)':<12} | {'ENCODE (ms)':<15} | {'DECODE (ms)':<15} |")
    print("=" * 88)
    
    for img_name, img in images.items():
        print(f"--- {img_name} ({img.width}x{img.height}, {img.mode}) ---")
        for fmt_name, encode_fn, decode_fn in formats:
            # We run once to warm up (JIT/caching)
            try:
                encode_fn(img)
            except Exception:
                continue
                
            # Perform multiple runs to average out timing noise
            runs = 3
            sizes = []
            encode_times = []
            decode_times = []
            
            for _ in range(runs):
                t0 = time.perf_counter()
                data = encode_fn(img)
                t_enc = (time.perf_counter() - t0) * 1000.0
                
                t0 = time.perf_counter()
                decoded = decode_fn(data)
                t_dec = (time.perf_counter() - t0) * 1000.0
                
                sizes.append(len(data))
                encode_times.append(t_enc)
                decode_times.append(t_dec)
                
            avg_size = sum(sizes) / len(sizes) / 1024.0
            avg_encode = sum(encode_times) / len(encode_times)
            avg_decode = sum(decode_times) / len(decode_times)
            
            print(f"{fmt_name:<25} | {avg_size:>10.2f} KB | {avg_encode:>12.2f} ms | {avg_decode:>12.2f} ms |")
        print("-" * 88)

def save_to_mem(img, fmt, **kwargs):
    out = io.BytesIO()
    img.save(out, format=fmt, **kwargs)
    return out.getvalue()

def load_from_mem(data):
    return Image.open(io.BytesIO(data))

if __name__ == "__main__":
    run_benchmarks()
