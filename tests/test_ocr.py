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

    @unittest.skipUnless(HAS_OCR, "Tesseract and Pillow are required for the embedded image fixture.")
    def test_native_docx_text_and_embedded_image_have_independent_provenance(self):
        from docx import Document
        from PIL import Image, ImageDraw, ImageFont

        with TemporaryDirectory() as folder, patch.dict("os.environ", {"FORGE_OCR": "1"}):
            path = Path(folder)
            image = Image.new("RGB", (900, 180), "white")
            font = ImageFont.truetype("DejaVuSans.ttf", 46)
            ImageDraw.Draw(image).text((25, 45), "Badge registration closes at 16:30.", font=font, fill="black")
            source = path / "notice.png"
            image.save(source)
            document = Document()
            document.add_heading("Visitor badges", 1)
            document.add_paragraph("Submit the visitor request at reception.")
            document.add_picture(str(source))
            document.save(path / "notice.docx")
            source.unlink()
            passages = Corpus.load(path).passages
            native = next(p for p in passages if "reception" in p["text"])
            extracted = next(p for p in passages if "16:30" in p["text"])
            self.assertNotIn("extraction", native)
            self.assertEqual(extracted["heading"], "Visitor badges")
            self.assertIn("block 3, image 1", extracted["locator"])
            self.assertEqual(extracted["extraction"]["method"], "tesseract_ocr")
