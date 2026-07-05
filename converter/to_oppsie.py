import os
import sys
import argparse
from PIL import Image

# Ensure the root package is visible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import oppsie

def convert_to_oppsie(src_path: str, dest_path: str, lossy_level: int = 0) -> str:
    """
    Converts PNG, JPEG, BMP, WebP, GIF (first frame) to .oppsie.
    
    :param src_path: Path to the source image file
    :param dest_path: Path to the output .oppsie file
    :param lossy_level: Lossy quantization level (0 to 7)
    :return: Path to the generated .oppsie file
    """
    img = Image.open(src_path)
    
    # pillow loads the first frame of multi-frame formats like GIF automatically,
    # but we can explicitly select it just to be safe.
    if hasattr(img, "seek"):
        img.seek(0)
        
    oppsie_bytes = oppsie.encode(img, lossy_level=lossy_level)
    
    with open(dest_path, "wb") as f:
        f.write(oppsie_bytes)
        
    return dest_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert images to .oppsie format")
    parser.add_argument("input", help="Input image path (PNG, JPEG, WebP, BMP, GIF)")
    parser.add_argument("output", help="Output .oppsie image path")
    parser.add_argument("--lossy", type=int, default=0, choices=range(0, 8),
                        help="Lossy quantization level (1-7, 0 is lossless)")
    args = parser.parse_args()
    
    try:
        convert_to_oppsie(args.input, args.output, args.lossy)
        print(f"Successfully converted {args.input} to {args.output} (lossy level: {args.lossy})")
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)
