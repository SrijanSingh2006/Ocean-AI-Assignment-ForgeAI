"""Exercise enterprise persistence workflows with local sources and the shared agent."""

import tempfile
import unittest
from pathlib import Path

from forgeai.corpus import Corpus
from forgeai.factory import Agent, generate_definition, ingest_requirements
from forgeai.feedback import approved_cases, list_feedback, review_feedback, submit_feedback
from forgeai.model import LocalModel


class ServiceTests(unittest.TestCase):
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


class FeedbackTests(ServiceTests):
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


class ImpactTests(ServiceTests):
    def test_impact_links_verified_provenance_across_file_order_changes(self):
        from forgeai.impact import analyze_impact

        old = self.root / "documents"
        (old / "untouched.md").write_text("# Hybrid glossary\n\nA work week has five weekdays.\n")
        corpus = Corpus.load(old)
        remote = next(p for p in corpus.passages if p["document"] == "policy.md")
        answer = Agent(self.definition, corpus).answer(self.question)
        new = self.root / "updated"
        new.mkdir()
        (new / "another.md").write_text("# New policy\n\nThe office has visitor parking.\n")
        (new / "policy.md").write_text("# Remote work\n\nRemote work is available three days each week.\n")
        (new / "untouched.md").write_bytes((old / "untouched.md").read_bytes())
        cases = [{
            "id": "old-allowance", "category": "answerable", "question": self.question,
            "expected_status": "answered", "expected_grounding": [{
                "passage_id": remote["id"], "document": remote["document"], "key_facts": ["two days"],
            }],
        }]
        result = analyze_impact(
            old, new, prior_cases=cases, prior_answers=[
                {"id": "recorded-answer", "agent_id": "demo", "case_id": "old-allowance", "response": answer},
                {"id": "invalid-citation", "citations": [{**answer["citations"][0], "quote": "unverified"}]},
            ],
            agent_id="demo", definition=self.definition, full_regression=True,
        )
        self.assertEqual(result["impacted_cases"], ["old-allowance"])
        self.assertEqual(result["impacted_answers"], ["recorded-answer"])
        self.assertEqual(result["impacted_agents"], ["demo"])
        self.assertEqual(result["reused_documents"], ["untouched.md"])
        self.assertEqual(result["reindexed_documents"], ["another.md", "policy.md"])
        self.assertEqual(result["targeted_regression"]["scorecard"]["passed"], 0)
        self.assertEqual(result["full_regression"]["scorecard"]["total"], 1)
        self.assertTrue(any(edge["relation"] == "evaluated_response" for edge in result["graph"]["edges"]))

    def test_impact_reports_removed_corpus_without_inventing_results(self):
        from forgeai.impact import analyze_impact

        new = self.root / "empty"
        new.mkdir()
        result = analyze_impact(self.root / "documents", new, agent_id="demo", definition=self.definition)
        self.assertEqual(result["changes"]["documents"][0]["kind"], "deleted")
        self.assertEqual(result["changes"]["sections"][0]["kind"], "deleted")
        self.assertEqual(result["impacted_agents"], ["demo"])
        self.assertNotIn("targeted_regression", result)


class ReleaseTests(ServiceTests):
    def setUp(self):
        super().setUp()
        from forgeai.factory import write_json

        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        write_json(self.artifacts / "definition.json", self.definition)
        write_json(self.artifacts / "scorecards.json", {"final": {"passed": 21, "total": 24}})
        (self.artifacts / ".env").write_text("AN_EXAMPLE_SECRET=outside-snapshot")

    def test_release_approval_snapshot_and_rollback(self):
        from forgeai.factory import read_json, write_json
        from forgeai.versioning import (
            activate_release, approve_release, compare_releases, create_release,
            list_releases, release_history, release_paths, rollback_release,
        )

        first = create_release(self.store, "agent", self.artifacts, self.root / "documents", actor="owner")
        with self.assertRaisesRegex(ValueError, "approved"):
            activate_release(self.store, "agent", first["id"])
        approve_release(self.store, "agent", first["id"], actor="reviewer")
        activate_release(self.store, "agent", first["id"], actor="owner")

        (self.root / "documents" / "policy.md").write_text("# Remote work\n\nRemote work is available three days each week.")
        write_json(self.artifacts / "definition.json", {**self.definition, "tone": "Direct"})
        write_json(self.artifacts / "scorecards.json", {"final": {"passed": 24, "total": 24}})
        second = create_release(self.store, "agent", self.artifacts, self.root / "documents")
        approve_release(self.store, "agent", second["id"])
        activate_release(self.store, "agent", second["id"])
        self.assertEqual(list_releases(self.store, "agent")[0]["id"], second["id"])
        comparison = compare_releases(self.store, "agent", first["id"], second["id"])
        self.assertEqual(comparison["changed_fields"], ["tone"])
        self.assertEqual(comparison["sources"]["modified"], ["policy.md"])
        self.assertEqual(comparison["score_after"]["passed"], 24)
        self.assertEqual(first["evaluation"]["passed"], 21)

        rollback_release(self.store, "agent", first["id"], actor="owner")
        artifacts, docs = release_paths(self.store, "agent")
        self.assertEqual(read_json(artifacts / "definition.json"), self.definition)
        self.assertIn("two days", Agent(self.definition, Corpus.load(docs)).answer(self.question)["answer"])
        self.assertFalse((artifacts / ".env").exists())
        self.assertEqual(release_history(self.store, "agent")[-1]["previous_id"], second["id"])

    def test_release_detects_tampering_and_rejects_traversal(self):
        from forgeai.versioning import create_release, release_paths

        with self.assertRaisesRegex(ValueError, "Invalid agent ID"):
            create_release(self.store, "../outside", self.artifacts, self.root / "documents")
        version = create_release(self.store, "agent", self.artifacts, self.root / "documents")
        _, docs = release_paths(self.store, "agent", version["id"])
        (docs / "policy.md").write_text("Tampered text")
        with self.assertRaisesRegex(ValueError, "integrity"):
            release_paths(self.store, "agent", version["id"])
