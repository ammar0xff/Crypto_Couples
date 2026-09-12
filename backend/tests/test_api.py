"""End-to-end API tests through the FastAPI TestClient (in-process server)."""

from __future__ import annotations

import io
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from crypto_couples import make_demo_image, png_encode, to_rows


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _demo_png(scale: int = 4) -> bytes:
    bits = make_demo_image("PWA", scale=scale)
    return png_encode(to_rows(bits))


def _wait_terminal(client, op_id: str, retries: int = 400):
    for _ in range(retries):
        d = client.get(f"/api/operations/{op_id}").json()
        if d["status"] in ("completed", "failed", "cancelled", "expired"):
            return d
        time.sleep(0.05)
    raise AssertionError(f"operation {op_id} did not finish")


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ffmpeg_probe(client):
    r = client.get("/api/system/ffmpeg")
    assert r.status_code == 200
    assert "available" in r.json()


def test_root_ok(client):
    _DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if (_DIST / "index.html").is_file():
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
    else:
        assert client.get("/").json()["api"] == "/api"

def test_csp_header_present(client):
    r = client.get("/api/health")
    assert "Content-Security-Policy" in r.headers


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_image_split_reject_non_png(client):
    r = client.post(
        "/api/images/split",
        files=[("files", ("nope.txt", b"hello", "text/plain"))],
    )
    assert r.status_code == 400
    body = r.json()["error"]
    assert body["code"] == "INVALID_FILE_TYPE"


def test_image_split_needs_exactly_one(client):
    ping = _demo_png()
    r = client.post(
        "/api/images/split",
        files=[
            ("files", ("a.png", ping, "image/png")),
            ("files", ("b.png", ping, "image/png")),
        ],
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_FILE_TYPE" or \
        r.json()["error"]["code"] == "INVALID_PARAMETER"


def test_image_split_reveal_roundtrip(client):
    data = _demo_png()
    r = client.post(
        "/api/images/split",
        files=[("files", ("demo.png", io.BytesIO(data), "image/png"))],
        data={"options": '{"method":"stack","shares":2,"threshold":128}'},
    )
    assert r.status_code == 202, r.text
    op = r.json()
    assert op["status"] in ("queued", "uploading", "processing")

    done = _wait_terminal(client, op["id"])
    assert done["status"] == "completed", done
    assert len(done["result_files"]) == 2

    share = done["result_files"][0]["name"]
    raw = client.get(f"/api/operations/{op['id']}/download",
                     params={"name": share})
    assert raw.status_code == 200
    assert raw.content.startswith(b"\x89PNG")

    r2 = client.post(
        "/api/images/reveal",
        files=[
            ("files", (share, io.BytesIO(raw.content), "image/png")),
            ("files", (done["result_files"][1]["name"],
                       io.BytesIO(client.get(
                           f"/api/operations/{op['id']}/download",
                           params={"name": done["result_files"][1]["name"]}
                       ).content), "image/png")),
        ],
        data={"options": '{"method":"stack"}'},
    )
    assert r2.status_code == 202, r2.text
    revealed = _wait_terminal(client, r2.json()["id"])
    assert revealed["status"] == "completed", revealed
    assert len(revealed["result_files"]) == 1


def test_download_all_zip(client):
    data = _demo_png(scale=3)
    r = client.post(
        "/api/images/split",
        files=[("files", ("zipdemo.png", io.BytesIO(data), "image/png"))],
        data={"options": '{"method":"xor","shares":3}'},
    )
    done = _wait_terminal(client, r.json()["id"])
    assert done["status"] == "completed"
    z = client.get(f"/api/operations/{done['id']}/download-all")
    assert z.status_code == 200
    assert z.content[:2] == b"PK"


def test_files_split_reveal_roundtrip(client):
    payload = bytes(range(256)) * 40
    r = client.post(
        "/api/files/split",
        files=[("files", ("secret.bin", io.BytesIO(payload),
                          "application/octet-stream"))],
        data={"options": '{"method":"shamir","shares":3,"threshold":2}'},
    )
    assert r.status_code == 202, r.text
    done = _wait_terminal(client, r.json()["id"])
    assert done["status"] == "completed", done
    assert len(done["result_files"]) == 3

    names = [f["name"] for f in done["result_files"]]
    contents = {
        n: client.get(f"/api/operations/{done['id']}/download",
                      params={"name": n}).content
        for n in names
    }
    r2 = client.post(
        "/api/files/reveal",
        files=[("files", (n, io.BytesIO(contents[n]),
                          "application/octet-stream"))
               for n in (names[0], names[2])],  # k=2 of 3, non-contiguous
        data={"options": '{"method":"shamir"}'},
    )
    done2 = _wait_terminal(client, r2.json()["id"])
    assert done2["status"] == "completed", done2
    out = done2["result_files"][0]["name"]
    restored = client.get(f"/api/operations/{done2['id']}/download",
                          params={"name": out}).content
    assert restored == payload


def test_cancel_operation(client):
    r = client.get("/api/operations")
    assert r.status_code == 200
    assert "operations" in r.json()


def test_unknown_operation_404(client):
    r = client.get("/api/operations/op_missing")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "OPERATION_NOT_FOUND"


def test_history_recorded(client):
    data = _demo_png(scale=3)
    r = client.post(
        "/api/images/split",
        files=[("files", ("hist.png", io.BytesIO(data), "image/png"))],
    )
    op = r.json()
    _wait_terminal(client, op["id"])
    hist = client.get("/api/history").json()["history"]
    assert any(h["id"] == op["id"] for h in hist)
    assert client.delete(f"/api/history/{op['id']}").status_code == 200


def test_validation_error_envelope(client):
    r = client.post(
        "/api/images/split",
        files=[("files", ("v.png", io.BytesIO(_demo_png()), "image/png"))],
        data={"options": '{"shares": 99}'},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_PARAMETER"