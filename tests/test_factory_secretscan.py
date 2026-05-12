from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
SCAN_PY = SCRIPTS / "factory_secretscan.py"


def _write(path: Path, content: str):
    path.write_text(content)


def test_clean_file():
    doc = Path("/tmp/test_clean.json")
    _write(doc, json.dumps({"body": "hello world"}))
    r = subprocess.run(
        [sys.executable, str(SCAN_PY), str(doc)],
        capture_output=True, text=True,
    )
    doc.unlink(missing_ok=True)
    assert r.returncode == 0
    assert "no secrets" in r.stdout


def test_aws_key():
    doc = Path("/tmp/test_aws.json")
    _write(doc, json.dumps({"body": "My key is AKIAIOSFODNN7EXAMPLE"}))
    r = subprocess.run(
        [sys.executable, str(SCAN_PY), str(doc)],
        capture_output=True, text=True,
    )
    doc.unlink(missing_ok=True)
    assert r.returncode == 1
    assert "AWS Access Key" in r.stderr


def test_private_key():
    doc = Path("/tmp/test_pk.json")
    _write(doc, json.dumps({"body": "-----BEGIN RSA PRIVATE KEY-----\nABCD\n-----END RSA PRIVATE KEY-----"}))
    r = subprocess.run(
        [sys.executable, str(SCAN_PY), str(doc)],
        capture_output=True, text=True,
    )
    doc.unlink(missing_ok=True)
    assert r.returncode == 1
    assert "Private Key" in r.stderr


def test_github_token():
    doc = Path("/tmp/test_gh.json")
    _write(doc, json.dumps({"body": "token is ghp_abc123def456ghi789jkl012mno345pqr678"}))
    r = subprocess.run(
        [sys.executable, str(SCAN_PY), str(doc)],
        capture_output=True, text=True,
    )
    doc.unlink(missing_ok=True)
    assert r.returncode == 1
    assert "GitHub Token" in r.stderr


def test_jwt():
    doc = Path("/tmp/test_jwt.json")
    _write(doc, json.dumps({"body": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.dGFsbA"}))
    r = subprocess.run(
        [sys.executable, str(SCAN_PY), str(doc)],
        capture_output=True, text=True,
    )
    doc.unlink(missing_ok=True)
    assert r.returncode == 1
    assert "JWT Token" in r.stderr


def test_json_output():
    doc = Path("/tmp/test_json.json")
    _write(doc, json.dumps({"body": "ghp_abc123def456ghi789jkl012mno345pqr678"}))
    r = subprocess.run(
        [sys.executable, str(SCAN_PY), str(doc), "--json"],
        capture_output=True, text=True,
    )
    doc.unlink(missing_ok=True)
    data = json.loads(r.stdout)
    assert data["secrets_found"] > 0


def test_yaml_file():
    doc = Path("/tmp/test_secret.yaml")
    _write(doc, "body: 'password = SuperSecret123!'")
    r = subprocess.run(
        [sys.executable, str(SCAN_PY), str(doc)],
        capture_output=True, text=True,
    )
    doc.unlink(missing_ok=True)
    assert r.returncode == 1
    assert "Secret" in r.stderr or "password" in r.stderr.lower()
