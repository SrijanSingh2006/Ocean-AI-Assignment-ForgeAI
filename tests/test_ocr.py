from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import shutil
import unittest
from unittest.mock import patch

from forgeai.corpus import Corpus

HAS_OCR = shutil.which("tesseract") and shutil.which("pdftoppm") and importlib.util.find_spec("PIL")


class OCRTests(unittest.TestCase):
    @unittest.skipUnless(HAS_OCR, "Tesseract, Poppler, and Pillow are required for the scanned fixture.")
    def test_actual_scanned_pdf_has_page_and_coordinate_provenance(self):
        from PIL import Image, ImageDraw, ImageFont

        with TemporaryDirectory() as folder, patch.dict("os.environ", {"FORGE_OCR": "1"}):
            path = Path(folder) / "scanned.pdf"
            image = Image.new("RGB", (900, 180), "white")
            font = ImageFont.truetype("DejaVuSans.ttf", 46)
            ImageDraw.Draw(image).text((25, 45), "Annual leave is 18 days.", font=font, fill="black")
            image.save(path)
            corpus = Corpus.load(path.parent)
            passage = corpus.passages[0]
            self.assertIn("18 days", passage["text"])
            self.assertIn("page 1", passage["locator"])
            self.assertEqual(passage["extraction"]["coordinate_unit"], "pixels")
            self.assertGreater(passage["extraction"]["confidence"], 0.5)
