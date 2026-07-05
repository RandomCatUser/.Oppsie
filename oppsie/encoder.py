import struct
from PIL import Image

def encode(image: Image.Image, lossy_level: int = 0) -> bytes:
    """
    Encodes a PIL.Image into .oppsie bytes.
    
    :param image: PIL.Image to encode
    :param lossy_level: 0 (lossless) or 1-7 (quantization level: clears lower N bits of color channels)
    :return: Bytes of the .oppsie image
    """
    # 1. Convert to RGB or RGBA based on presence of transparency
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        channels = 4
        img = image.convert("RGBA")
    else:
        channels = 3
        img = image.convert("RGB")

    width, height = img.size
    pixels = list(img.getdata())
    
    # Colorspace: 0 for sRGB, 1 for linear. Default to 0.
    colorspace = 0
    flags = lossy_level & 0x07
    
    # 15-byte header
    header = struct.pack(">4sIIBBB", b"OPPS", width, height, channels, colorspace, flags)
    out = bytearray(header)
    
    # Palette initialized to 64 pixels of (0,0,0,0)
    palette = [(0, 0, 0, 0)] * 64
    
    # Previous pixel initialized to (0, 0, 0, 255)
    prev_r, prev_g, prev_b, prev_a = 0, 0, 0, 255
    
    run_len = 0
    
    # Apply quantization for lossy mode if specified
    if flags > 0:
        mask = 256 - (1 << flags)
        # Apply quantization to RGB, keep alpha unchanged (or set to 255 for RGB mode)
        if channels == 4:
            pixels = [(p[0] & mask, p[1] & mask, p[2] & mask, p[3]) for p in pixels]
        else:
            pixels = [(p[0] & mask, p[1] & mask, p[2] & mask, 255) for p in pixels]
    else:
        if channels == 3:
            pixels = [(p[0], p[1], p[2], 255) for p in pixels]
            
    total_pixels = len(pixels)
    
    for i, p in enumerate(pixels):
        r, g, b, a = p
        
        # Check for run
        if r == prev_r and g == prev_g and b == prev_b and a == prev_a:
            run_len += 1
            if run_len == 62:
                out.append(0xC0 + 61) # 0xFD
                run_len = 0
        else:
            if run_len > 0:
                out.append(0xC0 + (run_len - 1))
                run_len = 0
            
            # Check running palette
            idx = (r * 3 + g * 5 + b * 7 + a * 11) & 63
            if palette[idx] == (r, g, b, a):
                out.append(idx)
            else:
                palette[idx] = (r, g, b, a)
                
                # Check for differences
                if a == prev_a:
                    # Modulo 256 signed difference:
                    dr = (r - prev_r) & 0xFF
                    if dr >= 128: dr -= 256
                    
                    dg = (g - prev_g) & 0xFF
                    if dg >= 128: dg -= 256
                    
                    db = (b - prev_b) & 0xFF
                    if db >= 128: db -= 256
                    
                    dr_dg = (dr - dg) & 0xFF
                    if dr_dg >= 128: dr_dg -= 256
                    
                    db_dg = (db - dg) & 0xFF
                    if db_dg >= 128: db_dg -= 256
                    
                    if -2 <= dr <= 1 and -2 <= dg <= 1 and -2 <= db <= 1:
                        # OPPS_DIFF chunk
                        out.append(0x40 | ((dr + 2) << 4) | ((dg + 2) << 2) | (db + 2))
                    elif -32 <= dg <= 31 and -8 <= dr_dg <= 7 and -8 <= db_dg <= 7:
                        # OPPS_LUMA chunk (2 bytes)
                        out.append(0x80 | (dg + 32))
                        out.append(((dr_dg + 8) << 4) | (db_dg + 8))
                    else:
                        # OPPS_RGB chunk
                        out.append(0xFE)
                        out.append(r)
                        out.append(g)
                        out.append(b)
                else:
                    # OPPS_RGBA chunk
                    out.append(0xFF)
                    out.append(r)
                    out.append(g)
                    out.append(b)
                    out.append(a)
            
            prev_r, prev_g, prev_b, prev_a = r, g, b, a
            
    # Handle trailing run
    if run_len > 0:
        out.append(0xC0 + (run_len - 1))
        
    # End marker (8 null bytes)
    out.extend(b"\x00\x00\x00\x00\x00\x00\x00\x00")
    
    # Optional EXIF metadata passthrough
    exif = image.info.get("exif")
    if exif is not None:
        out.extend(b"EXIF")
        out.extend(struct.pack(">I", len(exif)))
        out.extend(exif)
        
    return bytes(out)

