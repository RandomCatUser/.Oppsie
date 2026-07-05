import os
import sys
import glob
import argparse
from typing import List, Tuple

# Ensure the root package is visible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from converter.to_oppsie import convert_to_oppsie
from converter.from_oppsie import convert_from_oppsie

def batch_convert(src_dir: str, dest_dir: str, to_format: str, lossy_level: int = 0) -> List[Tuple[str, str, bool, str]]:
    """
    Converts a whole folder of images.
    
    :param src_dir: Source directory containing images
    :param dest_dir: Target directory for converted images
    :param to_format: "oppsie" to convert to .oppsie, or "png", "jpeg", "webp", "bmp" to convert from .oppsie
    :param lossy_level: Lossy level when converting to .oppsie
    :return: List of tuples (src_file, dest_file, success, error_message)
    """
    os.makedirs(dest_dir, exist_ok=True)
    results = []
    
    # Supported input formats when converting to oppsie
    to_oppsie_exts = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif")
    
    if to_format.lower() == "oppsie":
        files = []
        for ext in to_oppsie_exts:
            files.extend(glob.glob(os.path.join(src_dir, f"*{ext}")))
            files.extend(glob.glob(os.path.join(src_dir, f"*{ext.upper()}")))
            
        # De-duplicate paths
        files = list(set(os.path.abspath(f) for f in files))
        
        for f in files:
            base = os.path.splitext(os.path.basename(f))[0]
            dest_file = os.path.join(dest_dir, f"{base}.oppsie")
            try:
                convert_to_oppsie(f, dest_file, lossy_level)
                results.append((f, dest_file, True, ""))
            except Exception as e:
                results.append((f, dest_file, False, str(e)))
    else:
        # Converting from oppsie
        files = glob.glob(os.path.join(src_dir, "*.oppsie"))
        files.extend(glob.glob(os.path.join(src_dir, "*.OPPSIE")))
        files = list(set(os.path.abspath(f) for f in files))
        
        out_ext = f".{to_format.lower()}"
        for f in files:
            base = os.path.splitext(os.path.basename(f))[0]
            dest_file = os.path.join(dest_dir, f"{base}{out_ext}")
            try:
                convert_from_oppsie(f, dest_file)
                results.append((f, dest_file, True, ""))
            except Exception as e:
                results.append((f, dest_file, False, str(e)))
                
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch convert images to/from .oppsie format")
    parser.add_argument("src_dir", help="Source directory containing images")
    parser.add_argument("dest_dir", help="Destination directory for converted images")
    parser.add_argument("format", help="Target format (oppsie, png, jpeg, webp, bmp)")
    parser.add_argument("--lossy", type=int, default=0, choices=range(0, 8),
                        help="Lossy level (1-7) when converting to .oppsie")
    args = parser.parse_args()
    
    print(f"Batch converting files in {args.src_dir} to {args.dest_dir} in format {args.format}...")
    results = batch_convert(args.src_dir, args.dest_dir, args.format, args.lossy)
    
    success_count = sum(1 for r in results if r[2])
    fail_count = len(results) - success_count
    
    print(f"\nBatch conversion complete. Success: {success_count}, Failed: {fail_count}")
    for src, dest, success, err in results:
        status = "SUCCESS" if success else f"FAILED: {err}"
        print(f"  {os.path.basename(src)} -> {os.path.basename(dest)}: {status}")
        
    if fail_count > 0:
        sys.exit(1)
