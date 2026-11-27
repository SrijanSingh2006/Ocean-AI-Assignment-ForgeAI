from pathlib import Path
from tempfile import TemporaryDirectory
import io
import json
import time
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from fastapi.testclient import TestClient

from forgeai import web


class EnterpriseAPIWorkflowTests(unittest.TestCase):
    def submit(self, client, first, second):
        response = client.post("/api/runs", data={
            "brief": "Build an assistant for reviewers. Cover annual leave.", "model": "false",
            "blind": "true", "security_audit": "true", "tournament": "false",
        }, files=[
            ("files", ("Policy-One.md", f"# Annual leave\n\nAnnual leave is {first} days.", "text/markdown")),
            ("files", ("Policy-Two.md", f"# Annual leave\n\nAnnual leave is {second} days.", "text/markdown")),
        ])
        self.assertEqual(response.status_code, 202, response.text)
        run_id = response.json()["id"]
        for _ in range(120):
            state = client.get(f"/api/runs/{run_id}").json()
            if state["status"] in {"complete", "failed"}:
                break
            time.sleep(.025)
        self.assertEqual(state["status"], "complete", state)
        return run_id, state["result"]

    def test_real_run_conflict_feedback_and_release_restore(self):
        with TemporaryDirectory() as folder, patch.object(web, "RUNS", Path(folder)), TestClient(web.app) as client:
            original, report = self.submit(client, 18, 22)
            self.assertEqual(len(report["evals"]), 24)
            self.assertEqual(report["blind"]["scorecard"]["total"], 8)
            base = f"/api/runs/{original}"
            self.assertEqual(client.get(base + "/artifact/blind_results.json").status_code, 200)
            self.assertEqual(client.get(base + "/security").json()["method"], "fixed_defensive_conformance")

            self.assertEqual(client.post("/api/chat", json={"run_id": original, "question": "What is annual leave?"}).json()["status"], "clarify")
            conflict = client.get(base + "/conflicts").json()["conflicts"][0]
            chosen = conflict["claims"][0]
            self.assertEqual(client.post(base + f"/conflicts/{conflict['id']}", json={
                "passage_id": chosen["passage_id"], "reason": "Verified against the fixture authority.",
            }).status_code, 200)
            resolved = client.get(base + "/conflicts").json()["regression_cases"][conflict["id"]]
            self.assertTrue(resolved["verified"])
            self.assertEqual(resolved["case"]["expected_grounding"][0]["passage_id"], chosen["passage_id"])
            reply = client.post("/api/chat", json={"run_id": original, "question": "What is annual leave?"}).json()
            self.assertEqual(reply["status"], "answered")
            self.assertIn("18", reply["answer"])
            trace = client.get(base + f"/traces/{reply['trace_id']}").json()
            self.assertTrue(any(event["stage"] == "retrieval" for event in trace["events"]))
            feedback = client.post(base + "/feedback", json={"trace_id": reply["trace_id"], "category": "helpful"})
            self.assertEqual(feedback.status_code, 200, feedback.text)
            feedback_id = feedback.json()["id"]
            review = client.post(base + f"/feedback/{feedback_id}/review", json={
                "approve": True, "expected_status": "answered", "anchors": [chosen["passage_id"]],
            })
            self.assertEqual(review.status_code, 200, review.text)
            self.assertEqual(client.get(base + "/feedback").json()[0]["state"], "approved")

            older_release = client.post(base + "/releases", json={"label": "Original leave policy"}).json()
            self.assertEqual(older_release["label"], "Original leave policy")
            older = older_release["id"]
            self.assertEqual(client.post(base + f"/releases/{older}/approve").status_code, 200)
            self.assertEqual(client.post(base + f"/releases/{older}/activate").status_code, 200)
            revised, _ = self.submit(client, 20, 20)
            impact = client.post(f"/api/runs/{revised}/impact", json={"previous_run_id": original, "full_regression": True})
            self.assertEqual(impact.status_code, 200, impact.text)
            self.assertTrue(impact.json()["graph"]["edges"])
            newer = client.post(base + "/releases", json={"source_run_id": revised}).json()["id"]
            self.assertEqual(client.post(base + f"/releases/{newer}/approve").status_code, 200)
            self.assertEqual(client.post(base + f"/releases/{newer}/activate").status_code, 200)
            newer_answer = client.post("/api/chat", json={"run_id": original, "question": "What is annual leave?"}).json()
            self.assertIn("20", newer_answer["answer"])
            self.assertEqual(client.post(base + f"/releases/{older}/rollback").status_code, 200)
            answer = client.post("/api/chat", json={"run_id": original, "question": "What is annual leave?"}).json()
            self.assertIn("18", answer["answer"])
            self.assertEqual(answer["agent_version"], older)
            package = client.get(base + "/deployment")
            self.assertEqual(package.status_code, 200, package.text[:500])
            with ZipFile(io.BytesIO(package.content)) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn("Dockerfile", archive.namelist())
                self.assertIn("18 days", archive.read("documents/Policy-One.md").decode())
            self.assertEqual(client.get("/api/dashboard").json()["generated_agents"], 2)
