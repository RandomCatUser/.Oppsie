import os
import sys
import argparse
from PIL import Image

# Ensure the root package is visible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import oppsie

def convert_from_oppsie(src_path: str, dest_path: str) -> str:
    """
    Converts .oppsie to PNG, JPEG, WebP, BMP.
    
    :param src_path: Path to the .oppsie file
    :param dest_path: Path to the output image file
    :return: Path to the converted file
    """
    with open(src_path, "rb") as f:
        data = f.read()
        
    img = oppsie.decode(data)
    
    # Save image. Pillow determines format from file extension.
    save_args = {}
    ext = os.path.splitext(dest_path)[1].lower()
    
    if ext in (".jpg", ".jpeg"):
        # JPEG doesn't support RGBA, so convert to RGB
        if img.mode == "RGBA":
            img = img.convert("RGB")
        if "exif" in img.info:
            save_args["exif"] = img.info["exif"]
    elif ext in (".png", ".webp", ".bmp"):
        if "exif" in img.info:
            save_args["exif"] = img.info["exif"]
            
    img.save(dest_path, **save_args)
    return dest_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert .oppsie images to other formats")
    parser.add_argument("input", help="Input .oppsie image path")
    parser.add_argument("output", help="Output image path (PNG, JPEG, WebP, BMP)")
    args = parser.parse_args()
    
    try:
        convert_from_oppsie(args.input, args.output)
        print(f"Successfully converted {args.input} to {args.output}")
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)
