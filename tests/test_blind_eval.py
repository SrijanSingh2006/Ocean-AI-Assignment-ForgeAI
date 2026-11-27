from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from forgeai.blind_eval import stratified_holdout
from forgeai import factory
from forgeai.model import LocalModel, ROOT


class BlindEvaluationTests(unittest.TestCase):
    def test_stratification_is_reproducible_and_disjoint(self):
        cases = [
            {"id": f"{kind}{i}", "category": kind, "question": f"Question {i}?"}
            for kind in ("answerable", "refusal", "ambiguous", "multi_document") for i in range(8)
        ]
        dev, blind = stratified_holdout(cases)
        self.assertEqual((len(dev), len(blind)), (24, 8))
        self.assertEqual(set(Counter(case["category"] for case in blind).values()), {2})
        self.assertFalse({case["id"] for case in dev} & {case["id"] for case in blind})
        self.assertEqual((dev, blind), stratified_holdout(cases))

    def test_blind_cases_are_only_scored_after_repairs(self):
        pack = ROOT / "demos" / "people-ops"
        calls = []

        def record(definition, corpus, cases, model, iteration):
            calls.append({case["id"] for case in cases})
            return score(definition, corpus, cases, model, iteration)

        score = factory.score_agent
        with TemporaryDirectory() as out, patch.object(factory, "score_agent", side_effect=record):
            result = factory.run_factory((pack / "brief.txt").read_text(), pack / "documents", out,
                                         model=LocalModel(False), blind=True)
            self.assertTrue((Path(out) / "blind_evals.json").is_file())
            self.assertTrue((Path(out) / "blind_results.json").is_file())
        self.assertEqual(result["blind"]["corpus_origin"], "same_corpus")
        self.assertEqual(len(calls[-1]), 8)
        self.assertTrue(all(len(active) == 24 and not active & calls[-1] for active in calls[:-1]))
