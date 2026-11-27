"""Exercise enterprise persistence workflows with local sources and the shared agent."""

import tempfile
import unittest
from pathlib import Path

from forgeai.corpus import Corpus
from forgeai.factory import Agent, generate_definition, ingest_requirements
from forgeai.feedback import approved_cases, list_feedback, review_feedback, submit_feedback
from forgeai.model import LocalModel


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        documents = self.root / "documents"
        documents.mkdir()
        (documents / "policy.md").write_text("# Remote work\n\nRemote work is available two days each week.\n")
        self.corpus = Corpus.load(documents)
        model = LocalModel(enabled=False)
        req = ingest_requirements("An assistant covering remote work.", self.corpus, model)
        self.definition = generate_definition(req, model)
        self.question = "What is the remote work policy?"
        self.response = Agent(self.definition, self.corpus).answer(self.question)
        self.store = self.root / "store"

    def test_feedback_renders_a_verified_case_and_records_the_review(self):
        entry = submit_feedback(self.store, run_id="demo", question=self.question, response=self.response,
                                category="Wrong citation", comment="Please review", agent_version="one", actor="member")
        self.assertEqual(list_feedback(self.store, state="pending")[0]["id"], entry["id"])
        with self.assertRaisesRegex(ValueError, "Expected facts"):
            review_feedback(self.store, entry["id"], approve=True, reviewer="admin", corpus=self.corpus,
                            definition=self.definition, expected_status="answered",
                            anchors=[{"passage_id": self.corpus.passages[0]["id"], "key_facts": ["Made-up policy"]}])
        self.assertEqual(approved_cases(self.store, "demo"), [])
        reviewed = review_feedback(self.store, entry["id"], approve=True, reviewer="admin", corpus=self.corpus,
                                   definition=self.definition, expected_status="answered",
                                   anchors=[self.corpus.passages[0]["id"]])
        self.assertTrue(reviewed["evaluation"]["passed"])
        self.assertEqual(approved_cases(self.store, "demo"), [reviewed["case"]])
        self.assertEqual(approved_cases(self.store, "other"), [])
        self.assertEqual(approved_cases(self.store, "demo", suite="development"), [])
        with self.assertRaisesRegex(ValueError, "already reviewed"):
            review_feedback(self.store, entry["id"], approve=False, reviewer="admin")

    def test_feedback_repair_is_scored_without_applying_the_patch(self):
        entry = submit_feedback(self.store, run_id="demo", question="?", response={
            "status": "refused", "answer": "No evidence", "tool": None, "citations": [],
        }, category="incorrect_refusal")
        anchor = self.corpus.passages[0]
        prior = [{
            "id": "prior", "category": "answerable", "question": self.question,
            "expected_status": "answered", "expected_grounding": [{
                "passage_id": anchor["id"], "document": anchor["document"], "key_facts": [anchor["text"]],
            }],
        }]
        review = review_feedback(self.store, entry["id"], approve=True, reviewer="admin", corpus=self.corpus,
                                 definition=self.definition, expected_status="clarify", prior_cases=prior)
        self.assertFalse(review["evaluation"]["passed"])
        self.assertEqual(review["suggested_repair"]["patch"], "clarify_vague")
        self.assertTrue(review["suggested_repair"]["passes_regression_gate"])
        self.assertFalse(self.definition["policy"]["clarify_vague"])
