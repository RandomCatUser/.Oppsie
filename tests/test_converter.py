import unittest
import os
import sys
import tempfile
import shutil
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from converter.to_oppsie import convert_to_oppsie
from converter.from_oppsie import convert_from_oppsie
from converter.batch_runner import batch_convert

class TestConverter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    def test_png_roundtrip(self):
        """Test converting PNG to OPPSIE and back to PNG."""
        # 1. Create a dummy PNG
        src_png = os.path.join(self.temp_dir, "test.png")
        img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
        # Draw a diagonal line
        pixels = list(img.getdata())
        for i in range(50):
            pixels[i * 50 + i] = (0, 255, 0, 255)
        img.putdata(pixels)
        img.save(src_png)
        
        # 2. Convert to OPPSIE
        oppsie_file = os.path.join(self.temp_dir, "test.oppsie")
        convert_to_oppsie(src_png, oppsie_file)
        
        self.assertTrue(os.path.exists(oppsie_file))
        self.assertGreater(os.path.getsize(oppsie_file), 0)
        
        # 3. Convert back to PNG
        out_png = os.path.join(self.temp_dir, "out.png")
        convert_from_oppsie(oppsie_file, out_png)
        
        self.assertTrue(os.path.exists(out_png))
        
        # 4. Check correctness
        img_out = Image.open(out_png)
        self.assertEqual(img.size, img_out.size)
        self.assertEqual(list(img.getdata()), list(img_out.getdata()))

    def test_batch_convert(self):
        """Test batch conversion of a directory."""
        # Create a few input images
        input_dir = os.path.join(self.temp_dir, "input")
        output_dir = os.path.join(self.temp_dir, "output")
        output_back_dir = os.path.join(self.temp_dir, "output_back")
        os.makedirs(input_dir)
        
        img1 = Image.new("RGB", (20, 20), (0, 0, 255))
        img1.save(os.path.join(input_dir, "img1.png"))
        img2 = Image.new("RGB", (30, 30), (255, 255, 0))
        img2.save(os.path.join(input_dir, "img2.jpg"))
        
        # Batch convert to oppsie
        results = batch_convert(input_dir, output_dir, "oppsie")
        self.assertEqual(len(results), 2)
        for _, dest, success, err in results:
            self.assertTrue(success, f"Failed: {err}")
            self.assertTrue(os.path.exists(dest))
            self.assertTrue(dest.endswith(".oppsie"))
            
        # Batch convert back to png
        results_back = batch_convert(output_dir, output_back_dir, "png")
        self.assertEqual(len(results_back), 2)
        for _, dest, success, err in results_back:
            self.assertTrue(success, f"Failed: {err}")
            self.assertTrue(os.path.exists(dest))
            self.assertTrue(dest.endswith(".png"))
            
if __name__ == "__main__":
    unittest.main()
