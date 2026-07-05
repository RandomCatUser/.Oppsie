import struct
from PIL import Image

def decode(data: bytes) -> Image.Image:
    """
    Decodes .oppsie bytes back into a PIL.Image.
    
    :param data: The .oppsie byte sequence
    :return: A PIL.Image (RGB or RGBA)
    """
    if len(data) < 15:
        raise ValueError("Invalid OPPSIE file: too short")
        
    # Header: Magic(4s), Width(I), Height(I), Channels(B), Colorspace(B), Flags(B)
    magic, width, height, channels, colorspace, flags = struct.unpack(">4sIIBBB", data[:15])
    
    if magic != b"OPPS":
        raise ValueError("Invalid OPPSIE file: invalid magic signature")
        
    if channels not in (3, 4):
        raise ValueError(f"Invalid OPPSIE file: invalid channel count ({channels})")
        
    total_pixels = width * height
    pixels = [None] * total_pixels
    
    palette = [(0, 0, 0, 0)] * 64
    prev_r, prev_g, prev_b, prev_a = 0, 0, 0, 255
    
    offset = 15
    p_idx = 0
    
    # We do a while loop until all pixels are decoded
    while p_idx < total_pixels:
        if offset >= len(data):
            raise ValueError(f"Truncated OPPSIE file: decoded {p_idx} of {total_pixels} pixels")
            
        byte = data[offset]
        offset += 1
        
        if byte == 0xFE:  # OPPS_RGB
            if offset + 3 > len(data):
                raise ValueError("Truncated OPPS_RGB chunk")
            r = data[offset]
            g = data[offset+1]
            b = data[offset+2]
            a = prev_a
            offset += 3
            
            prev_r, prev_g, prev_b, prev_a = r, g, b, a
            palette[(r * 3 + g * 5 + b * 7 + a * 11) & 63] = (r, g, b, a)
            pixels[p_idx] = (r, g, b) if channels == 3 else (r, g, b, a)
            p_idx += 1
            
        elif byte == 0xFF:  # OPPS_RGBA
            if offset + 4 > len(data):
                raise ValueError("Truncated OPPS_RGBA chunk")
            r = data[offset]
            g = data[offset+1]
            b = data[offset+2]
            a = data[offset+3]
            offset += 4
            
            prev_r, prev_g, prev_b, prev_a = r, g, b, a
            palette[(r * 3 + g * 5 + b * 7 + a * 11) & 63] = (r, g, b, a)
            pixels[p_idx] = (r, g, b) if channels == 3 else (r, g, b, a)
            p_idx += 1
            
        elif (byte & 0xC0) == 0xC0:  # OPPS_RUN
            run_len = (byte & 0x3F) + 1
            if p_idx + run_len > total_pixels:
                raise ValueError(f"Invalid run length {run_len} at pixel {p_idx} (total {total_pixels})")
                
            pixel_val = (prev_r, prev_g, prev_b) if channels == 3 else (prev_r, prev_g, prev_b, prev_a)
            for _ in range(run_len):
                pixels[p_idx] = pixel_val
                p_idx += 1
                
        elif (byte & 0xC0) == 0x80:  # OPPS_LUMA
            if offset >= len(data):
                raise ValueError("Truncated OPPS_LUMA chunk")
            byte2 = data[offset]
            offset += 1
            
            dg = (byte & 0x3F) - 32
            dr_dg = ((byte2 >> 4) & 0x0F) - 8
            db_dg = (byte2 & 0x0F) - 8
            
            dr = dr_dg + dg
            db = db_dg + dg
            
            r = (prev_r + dr) & 0xFF
            g = (prev_g + dg) & 0xFF
            b = (prev_b + db) & 0xFF
            a = prev_a
            
            prev_r, prev_g, prev_b, prev_a = r, g, b, a
            palette[(r * 3 + g * 5 + b * 7 + a * 11) & 63] = (r, g, b, a)
            pixels[p_idx] = (r, g, b) if channels == 3 else (r, g, b, a)
            p_idx += 1
            
        elif (byte & 0xC0) == 0x40:  # OPPS_DIFF
            dr = ((byte >> 4) & 0x03) - 2
            dg = ((byte >> 2) & 0x03) - 2
            db = (byte & 0x03) - 2
            
            r = (prev_r + dr) & 0xFF
            g = (prev_g + dg) & 0xFF
            b = (prev_b + db) & 0xFF
            a = prev_a
            
            prev_r, prev_g, prev_b, prev_a = r, g, b, a
            palette[(r * 3 + g * 5 + b * 7 + a * 11) & 63] = (r, g, b, a)
            pixels[p_idx] = (r, g, b) if channels == 3 else (r, g, b, a)
            p_idx += 1
            
        else:  # OPPS_INDEX (byte & 0xC0 == 0x00)
            idx = byte & 0x3F
            r, g, b, a = palette[idx]
            
            prev_r, prev_g, prev_b, prev_a = r, g, b, a
            pixels[p_idx] = (r, g, b) if channels == 3 else (r, g, b, a)
            p_idx += 1

    # Consume end marker (8 null bytes) if present
    if offset + 8 <= len(data) and data[offset:offset+8] == b"\x00\x00\x00\x00\x00\x00\x00\x00":
        offset += 8
        
    exif_data = None
    # Parse metadata sections
    while offset + 8 <= len(data):
        meta_sig = data[offset:offset+4]
        meta_len = struct.unpack(">I", data[offset+4:offset+8])[0]
        if offset + 8 + meta_len <= len(data):
            payload = data[offset+8:offset+8+meta_len]
            if meta_sig == b"EXIF":
                exif_data = payload
            offset += 8 + meta_len
        else:
            break

    img = Image.new("RGBA" if channels == 4 else "RGB", (width, height))
    img.putdata(pixels)
    
    if exif_data is not None:
        img.info["exif"] = exif_data
        
    return img

