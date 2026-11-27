from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from forgeai.corpus import Corpus
from forgeai.factory import Agent, generate_definition, ingest_requirements
from forgeai.model import LocalModel


class FigureTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("tesseract"), "Install Tesseract to verify the chart image.")
    def test_embedded_chart_values_and_page_figure_citation(self):
        from PIL import Image, ImageDraw, ImageFont

        with TemporaryDirectory() as folder, patch.dict("os.environ", {"FORGE_FIGURES": "1", "FORGE_OCR": "0"}):
            root = Path(folder)
            image = Image.new("RGB", (960, 520), "white")
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("DejaVuSans.ttf", 29)
            draw.text((460, 50), "Regional shipments", anchor="mm", font=font, fill="black")
            draw.line((150, 400, 835, 400), fill="black", width=2)
            for center, name, value, color in [(250, "East", 20, "#4a47cc"), (480, "West", 40, "#008a88"), (710, "North", 30, "#b94185")]:
                top = 400 - value * 6
                draw.rectangle((center - 42, top, center + 42, 399), fill=color)
                draw.text((center, top - 18), str(value), anchor="mm", font=font, fill="black")
                draw.text((center, 430), name, anchor="mm", font=font, fill="black")
            image.save(root / "Regional Shipments.pdf", "PDF", resolution=100)
            corpus = Corpus.load(root)
            source = corpus.passages[0]
            self.assertEqual(source["locator"], "page 1, figure 1")
            self.assertEqual(source["extraction"]["values"], [
                {"label": "East", "value": 20}, {"label": "West", "value": 40}, {"label": "North", "value": 30},
            ])
            definition = generate_definition(ingest_requirements("Cover regional shipments.", corpus, LocalModel(False)), LocalModel(False))
            answer = Agent(definition, corpus).answer("Which region has the highest shipments?")
            self.assertEqual(answer["status"], "answered")
            self.assertIn("maximum): West at 40", answer["answer"])
            self.assertEqual(answer["citations"][0]["locator"], "page 1, figure 1")
