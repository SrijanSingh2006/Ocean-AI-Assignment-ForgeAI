import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from forgeai.corpus import Corpus
from forgeai.embeddings import Embeddings
from forgeai.factory import Agent, generate_definition, ingest_requirements
from forgeai.model import LocalModel
from forgeai.model_tournament import compare_languages, compare_models


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        path = Path(self.folder.name)
        (path / "leave.md").write_text("# Leave\n\nAnnual leave is 18 days.\n")
        self.corpus = Corpus.load(path)
        offline = LocalModel(False)
        req = ingest_requirements("Cover annual leave.", self.corpus, offline)
        self.definition = generate_definition(req, offline)

    def test_embedding_rank_uses_normalized_vectors(self):
        service = Embeddings("http://localhost:8760/v1", "configured-model")
        with patch.object(service, "encode", return_value=[[1, 0], [1, 0]]) as encode:
            hits = service.search("Holiday", self.corpus, None)
        self.assertEqual(hits[0][2]["document"], "leave.md")
        self.assertEqual(encode.call_args.args[0][0], "Holiday")

    def test_unavailable_models_do_not_win(self):
        candidate = {"id": "unavailable", "url": "http://localhost:8760/v1", "model": "missing"}
        with patch.object(LocalModel, "probe", return_value=False):
            report = compare_models(self.definition, self.corpus, [], [candidate])
        self.assertEqual(report["models"][0]["status"], "unavailable")
        self.assertIsNone(report["recommended"])

    def test_language_suite_reports_unavailable_instead_of_passes(self):
        passage = self.corpus.passages[0]
        case = {"id": "E01", "category": "answerable", "question": "What is annual leave?",
                "expected_status": "answered", "expected_grounding": [{"document": "leave.md", "passage_id": passage["id"],
                                                                       "key_facts": [passage["text"]]}]}
        report = compare_languages(Agent(self.definition, self.corpus), [case], None)
        self.assertEqual(report["languages"]["en"]["passed"], 1)
        self.assertEqual(report["languages"]["hi"]["scored"], 0)
        self.assertEqual(report["languages"]["ta"]["scored"], 0)
