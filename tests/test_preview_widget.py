import os
import sys
import unittest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import PreviewWidget, load_image_from_path


class TestPreviewWidget(unittest.TestCase):
    def test_render_with_image_does_not_raise(self):
        widget = PreviewWidget("TEST PREVIEW")
        img = Image.new("RGB", (8, 8), (255, 0, 0))
        widget.set_image(img)

        rendered = widget.render()

        self.assertIsNotNone(rendered)
        self.assertGreater(len(rendered.plain), 0)

    def test_load_image_from_path_supports_oppsie(self):
        temp_dir = os.path.join(os.path.dirname(__file__), "tmp_oppsie_test")
        os.makedirs(temp_dir, exist_ok=True)
        try:
            src_path = os.path.join(temp_dir, "sample.png")
            img = Image.new("RGB", (6, 6), (10, 20, 30))
            img.save(src_path)

            oppsie_path = os.path.join(temp_dir, "sample.oppsie")
            from converter.to_oppsie import convert_to_oppsie
            convert_to_oppsie(src_path, oppsie_path)

            loaded = load_image_from_path(oppsie_path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.size, (6, 6))
        finally:
            for entry in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, entry))
            os.rmdir(temp_dir)


if __name__ == "__main__":
    unittest.main()
