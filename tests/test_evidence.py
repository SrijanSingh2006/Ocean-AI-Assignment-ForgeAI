from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from forgeai.confidence import calibration_report
from forgeai.conflict_detector import numeric_conflicts
from forgeai.corpus import Corpus
from forgeai.factory import Agent, run_factory
from forgeai.model import LocalModel


class EvidenceTests(unittest.TestCase):
    def test_conflict_requires_review_and_resolution_restores_evidence(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "Policy-2024.md").write_text("# Annual leave\n\nAnnual leave is 18 days.\n")
            (root / "Policy-2025.md").write_text("# Annual leave\n\nAnnual leave is 22 days.\n")
            corpus = Corpus.load(root)
            clashes = numeric_conflicts(corpus)
            self.assertEqual(len(clashes), 1)
            self.assertEqual({row["version_hint"] for row in clashes[0]["claims"]}, {"2024", "2025"})
            result = run_factory("Cover annual leave.", root, root / "out", model=LocalModel(False))
            self.assertTrue(any(case["category"] == "conflict" for case in result["evals"]))
            agent = Agent(result["definition"], corpus)
            self.assertEqual(agent.answer("What is annual leave?")["status"], "clarify")
            first = clashes[0]["claims"][0]
            agent = Agent(result["definition"], corpus, resolutions={clashes[0]["id"]: first["passage_id"]})
            answer = agent.answer("What is annual leave?")
            self.assertEqual(answer["status"], "answered")
            self.assertEqual(answer["citations"][0]["document"], first["document"])
            self.assertEqual(answer["confidence"]["kind"], "heuristic")

    def test_calibration_requires_disjoint_labeled_data(self):
        train = [{"id": "train", "score": .9, "correct": True, "status": "answered"}]
        check = [{"id": "test", "score": .8, "correct": False, "status": "answered"}]
        report = calibration_report(train, check)
        self.assertEqual(report["false_answer_rate"], 1)
        self.assertEqual(report["brier_score"], 1)
        with self.assertRaisesRegex(ValueError, "disjoint"):
            calibration_report(train, train)

    def test_policy_conflicts_preserve_date_negation_and_conditions(self):
        from forgeai.conflict_detector import document_conflicts
        with TemporaryDirectory() as folder:
            root = Path(folder)
            texts = [
                ("Policy A.md", "# Remote work\n\nEmployees may work remotely.\n\n# Effective period\n\nPolicy effective on 2027-01-01.\n\n# Returns\n\nEmployees may submit returns when a supervisor approves."),
                ("Policy B.md", "# Remote work\n\nStaff are prohibited from working remotely.\n\n# Effective period\n\nPolicy effective on March 1, 2027.\n\n# Returns\n\nEmployees may not submit returns when a supervisor approves."),
                ("Exceptions.md", "# Remote work\n\nContractors may not work remotely when travelling."),
            ]
            for name, text in texts:
                (root / name).write_text(text)
            corpus = Corpus.load(root)
            clashes = document_conflicts(corpus)
            self.assertEqual({row["type"] for row in clashes}, {"effective_date", "permission", "conditional_policy"})
            self.assertTrue(all({c["document"] for c in row["claims"]} == {"Policy A.md", "Policy B.md"} for row in clashes))
            self.assertTrue(all(row["precedence"] is None for row in clashes))
            agent = run_factory("Cover remote work and returns.", root, root / "out", model=LocalModel(False))
            self.assertIn("source_conflicts", agent["requirements"])
