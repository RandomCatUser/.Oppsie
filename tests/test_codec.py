import unittest
import sys
import os
import random
from PIL import Image

# Ensure the root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from oppsie import encode, decode

class TestOppsieCodec(unittest.TestCase):
    
    def test_solid_rgb(self):
        """Test roundtrip of a solid RGB image (100x100)."""
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        encoded = encode(img)
        decoded = decode(encoded)
        
        self.assertEqual(img.size, decoded.size)
        self.assertEqual(decoded.mode, "RGB")
        self.assertEqual(list(img.getdata()), list(decoded.getdata()))

    def test_solid_rgba(self):
        """Test roundtrip of a solid RGBA image (100x100)."""
        img = Image.new("RGBA", (100, 100), (0, 255, 0, 128))
        encoded = encode(img)
        decoded = decode(encoded)
        
        self.assertEqual(img.size, decoded.size)
        self.assertEqual(decoded.mode, "RGBA")
        self.assertEqual(list(img.getdata()), list(decoded.getdata()))

    def test_gradient_rgb(self):
        """Test roundtrip of a smooth RGB gradient (256x256)."""
        img = Image.new("RGB", (256, 256))
        pixels = []
        for y in range(256):
            for x in range(256):
                pixels.append((x, y, (x + y) // 2))
        img.putdata(pixels)
        
        encoded = encode(img)
        decoded = decode(encoded)
        
        self.assertEqual(img.size, decoded.size)
        self.assertEqual(decoded.mode, "RGB")
        self.assertEqual(list(img.getdata()), list(decoded.getdata()))

    def test_random_rgba(self):
        """Test roundtrip of a random noise RGBA image (32x32)."""
        # Small dimensions so index hits and random differences test all path branches
        random.seed(42)
        img = Image.new("RGBA", (32, 32))
        pixels = []
        for _ in range(32 * 32):
            pixels.append((
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            ))
        img.putdata(pixels)
        
        encoded = encode(img)
        decoded = decode(encoded)
        
        self.assertEqual(img.size, decoded.size)
        self.assertEqual(decoded.mode, "RGBA")
        self.assertEqual(list(img.getdata()), list(decoded.getdata()))

    def test_lossy_mode(self):
        """Test lossy encoding runs and reduces image depth correctly."""
        img = Image.new("RGB", (10, 10))
        # Create pixels with non-zero lower bits
        pixels = [(13, 57, 125)] * 100
        img.putdata(pixels)
        
        # Lossy level 3 (clears lower 3 bits, i.e., masks with 0xF8)
        encoded = encode(img, lossy_level=3)
        decoded = decode(encoded)
        
        # Get decoded pixel
        decoded_pixels = list(decoded.getdata())
        # Check that the lower 3 bits of decoded pixels are 0
        for p in decoded_pixels:
            self.assertEqual(p[0] & 0x07, 0)
            self.assertEqual(p[1] & 0x07, 0)
            self.assertEqual(p[2] & 0x07, 0)
            
            # The value should be close to 13, 57, 125 (specifically 13 & 0xF8 = 8, 57 & 0xF8 = 56, 125 & 0xF8 = 120)
            self.assertEqual(p[0], 13 & 0xF8)
            self.assertEqual(p[1], 57 & 0xF8)
            self.assertEqual(p[2], 125 & 0xF8)

if __name__ == "__main__":
    unittest.main()
