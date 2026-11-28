import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from forgeai import privacy, web
from forgeai.factory import write_json


class AccessTests(unittest.TestCase):
    def test_workspace_and_document_permissions_are_enforced_by_api(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "auth.json"
            phrase = "fixture-passphrase"
            credential = privacy.password_hash(phrase)
            self.assertTrue(privacy.verify_password(phrase, credential))
            self.assertFalse(privacy.verify_password("elsewhere", credential))
            config.write_text(json.dumps({"users": {
                "staff": {"password_hash": credential, "workspace": "team", "role": "user"},
                "limited": {"password_hash": credential, "workspace": "team", "role": "user", "documents": ["public.txt"]},
            }}))
            run_id = "0123456789ab"
            target = root / run_id
            (target / "documents").mkdir(parents=True)
            (target / "documents" / "private.txt").write_text("Private context.")
            write_json(target / "status.json", {"id": run_id, "workspace": "another-team", "status": "complete", "created": "now"})
            with patch.dict("os.environ", {"FORGE_AUTH_CONFIG": str(config)}), patch.object(web, "RUNS", root), TestClient(web.app) as client:
                self.assertEqual(client.get("/api/health").status_code, 200)
                self.assertEqual(client.get("/api/runs").status_code, 401)
                response = client.post("/api/session", json={"username": "staff", "password": phrase})
                self.assertEqual(response.status_code, 200)
                self.assertIn("HttpOnly", response.headers["set-cookie"])
                self.assertEqual(client.get(f"/api/runs/{run_id}").status_code, 404)
                self.assertEqual(client.post("/api/chat", json={"run_id": run_id, "question": "Private?"}).status_code, 404)
                self.assertEqual(client.get("/api/runs/people-ops/download").status_code, 403)
                self.assertNotIn("result", client.get("/api/runs/people-ops").json())
                self.assertEqual(client.delete("/api/session").status_code, 200)
                write_json(target / "status.json", {"id": run_id, "workspace": "team", "status": "complete", "created": "now"})
                self.assertEqual(client.post("/api/session", json={"username": "limited", "password": phrase}).status_code, 200)
                self.assertEqual(client.get(f"/api/runs/{run_id}").status_code, 404)
                self.assertEqual(client.get("/api/runs").json(), [])


class ReviewerDemoTests(unittest.TestCase):
    def test_dashboard_uses_recorded_sample_evaluations(self):
        with patch.object(web, "REVIEW_DEMO", True), TestClient(web.app) as client:
            samples = client.get("/api/runs").json()
            runs = [client.get(f"/api/runs/{sample['id']}").json()["result"] for sample in samples]
            cases = [case for run in runs for case in run["results"]]
            response = client.get("/api/dashboard")
            self.assertEqual(response.status_code, 200)
            dashboard = response.json()
            self.assertEqual(dashboard["recent"], samples)
            self.assertEqual(dashboard["generated_agents"], len(runs))
            self.assertEqual(dashboard["evaluation_cases"], len(cases))
            self.assertGreater(dashboard["evaluation_cases"], 0)
            self.assertEqual(dashboard["average_score"], round(sum(run["scorecard"]["score"] for run in runs) / len(runs), 1))
            self.assertEqual(dashboard["grounding_rate"], round(sum(case["checks"]["grounded"] for case in cases) / len(cases), 3))

    def test_public_sample_access_is_read_only_and_does_not_store_questions(self):
        with TemporaryDirectory() as folder, patch.object(web, "REVIEW_DEMO", True), patch.object(web, "RUNS", Path(folder)):
            with TestClient(web.app) as client:
                self.assertTrue(client.get("/api/session").json()["review_demo"])
                self.assertEqual(client.get("/api/runs").status_code, 200)
                self.assertEqual(client.get("/api/runs/123456abcdef").status_code, 403)
                self.assertEqual(client.post("/api/session", json={"username": "demo", "password": "demo"}).status_code, 403)
                self.assertEqual(client.post("/api/runs").status_code, 403)
                self.assertEqual(client.get("/api/runs/people-ops/traces").status_code, 403)
                answer = client.post("/api/chat", json={"run_id": "people-ops", "question": "How many annual leave days does a full-time employee receive?"}).json()
                self.assertEqual(answer["status"], "answered")
                self.assertIn("22 paid annual leave days", answer["answer"])
                self.assertEqual(answer["citations"][0]["document"], "Leave-Handbook.md")
                self.assertNotIn("trace_id", answer)
                result = client.post("/api/chat", json={"run_id": "123456abcdef", "question": "Annual leave?"})
                self.assertEqual(result.status_code, 404)
                weather = client.get("/api/workspace").json()["tools"]["weather"]
                self.assertIsNone(weather["example"])
                with patch("forgeai.registry.urlopen") as weather_provider:
                    response = client.post("/api/chat", json={
                        "run_id": "operations-lab", "question": "Weather at 18.94, 72.83",
                    }).json()
                    weather_provider.assert_not_called()
                self.assertEqual(response["status"], "error")
                self.assertEqual(response["answer"], weather["description"])
                self.assertFalse(list(Path(folder).iterdir()))
