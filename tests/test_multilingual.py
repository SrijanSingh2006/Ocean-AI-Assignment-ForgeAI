from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from forgeai.corpus import Corpus, terms
from forgeai.factory import Agent, generate_definition, ingest_requirements
from forgeai.model import LocalModel
from forgeai.multilingual import detect_language, translate


class MultilingualTests(unittest.TestCase):
    def test_detect_and_tokenize_scripts(self):
        self.assertEqual(detect_language("छुट्टी कब मिलेगी?"), "hi")
        self.assertEqual(detect_language("leave விடுப்பு எப்போது?"), "ta-en")
        self.assertEqual(detect_language("Kitna leave milta hai?"), "hi-Latn")
        self.assertIn("छुट्टी", terms("छुट्टी"))

    def test_translation_cannot_change_numbers(self):
        model = Mock()
        model.ask.return_value = {"text": "वार्षिक छुट्टी 30 दिन है।"}
        self.assertIsNone(translate("Annual leave is 18 days.", "hi", model))

    def test_verified_reply_retains_original_citations(self):
        with TemporaryDirectory() as folder:
            p = Path(folder)
            source = "Annual leave is 18 days."
            (p / "leave.txt").write_text(source, encoding="utf-8")
            corpus = Corpus.load(p)
            base = LocalModel(False)
            definition = generate_definition(ingest_requirements("Cover annual leave.", corpus, base), base)
            model = Mock()
            model.ask.side_effect = [
                {"text": "How long is annual leave?"},
                {"text": "वार्षिक छुट्टी 18 दिन है।"},
                {"text": source},
            ]
            agent = Agent(definition, corpus, translator=model)
            reply = agent.answer("वार्षिक छुट्टी कितनी है?")
            self.assertEqual(reply["status"], "answered")
            self.assertEqual(reply["translation_status"], "verified_roundtrip")
            self.assertEqual(reply["citations"][0]["quote"], source)
            self.assertEqual(Agent(definition, corpus).answer("वार्षिक छुट्टी कितनी है?")["status"], "clarify")
