from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from forgeai.corpus import Corpus, terms
from forgeai.factory import Agent, generate_definition, ingest_requirements, read_json
from forgeai.model import LocalModel
from forgeai.multilingual import detect_language, translate, translated_answer
from forgeai.policy_localizations import localize_evidence


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

    def test_translation_cannot_drop_paid_leave(self):
        model = Mock()
        model.ask.return_value = {"text": "कर्मचारियों को हर साल 14 दिन की छुट्टी मिलती है।"}
        self.assertIsNone(translated_answer("Employees receive 14 paid vacation days each year.", "en", "hi", model))

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

    def test_romanized_query_localizes_the_selected_revision(self):
        demo = Path(__file__).resolve().parents[1] / "demos" / "people-ops-revised"
        definition = read_json(demo / "artifacts" / "definition.json")
        retrieval = definition["retrieval"]
        corpus = Corpus.load(demo / "documents", retrieval["chunk_words"], retrieval["overlap_words"])
        reply = Agent(definition, corpus).answer("Annual leave kitne din hai?")
        self.assertEqual(reply["status"], "answered")
        self.assertEqual(reply["detected_language"], "hi-Latn")
        self.assertEqual(reply["translation_status"], "source_localization")
        self.assertIn("25", reply["answer"])
        self.assertIn("25 paid annual leave days", reply["citations"][0]["quote"])
        updated = reply["citations"][0]["quote"].replace("25 paid", "26 paid")
        self.assertIsNone(localize_evidence({"answer": updated, "citations": [{"quote": updated}]}, "hi"))

    def test_original_script_retrieval_requires_a_distinct_match(self):
        demo = Path(__file__).resolve().parents[1] / "demos" / "people-ops"
        definition = read_json(demo / "artifacts" / "definition.json")
        corpus = Corpus.load(demo / "documents")
        question = "பயிற்சி உதவித்தொகை எவ்வளவு?"
        training = next(p for p in corpus.passages if p["document"] == "Training-Benefit.pdf")
        embeddings = Mock()
        embeddings.search.return_value = [(0.85, 0.85, training), (0.80, 0.80, corpus.passages[0])]
        agent = Agent(definition, corpus, embeddings=embeddings)
        reply = agent.answer(question)
        self.assertEqual(embeddings.search.call_args.args[0], question)
        self.assertEqual(reply["status"], "answered")
        self.assertEqual(reply["citations"][0]["quote"], training["text"])
        self.assertIn("EUR 350", reply["answer"])
        embeddings.search.return_value[1] = (0.84, 0.84, corpus.passages[0])
        self.assertEqual(agent.answer(question)["status"], "refused")


class LocalTranslationIntegrityTests(unittest.TestCase):
    def test_semantic_round_trip_preserves_negation_and_temporal_conditions(self):
        from unittest.mock import Mock
        from forgeai.local_language import LocalTranslation

        model = LocalTranslation("/unused", Mock())
        model.embeddings.similarity.return_value = 0.97
        self.assertTrue(model.equivalent("Employees must file before Friday.", "Employees are required to file prior to Friday."))
        self.assertFalse(model.equivalent("Employees must not file before Friday.", "Employees must file before Friday."))
        self.assertFalse(model.equivalent("Employees must file before Friday.", "Employees must file after Friday."))
