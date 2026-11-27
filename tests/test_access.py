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
