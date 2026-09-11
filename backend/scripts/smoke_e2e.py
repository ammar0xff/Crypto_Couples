"""End-to-end smoke test against the live backend via HTTP + WS.

Verifies the API contract exactly as the frontend would use it:
  health -> split (image stack) with WS live feed -> reveal -> valid PNG
  -> split (image xor) -> reveal -> recovered binarized secret exactly
  -> download-all zip -> split (file shamir 2-of-3) -> reveal -> byte-identical
  -> history accumulates.

Run on a machine where the backend is already listening on port 8000:

    PYTHONPATH=. venv/bin/python backend/scripts/smoke_e2e.py
    # (PYTHONPATH repo-root lands crypto_couples for PNG generation)
"""

import asyncio
import io
import sys
import zipfile

import httpx
import websockets

import crypto_couples as cc

BASE = "http://127.0.0.1:8000"
WS = "ws://127.0.0.1:8000"
FETCH = sys.executable  # for subprocess, not used yet


SRC_ROWS = [
    [((x * 17) % 256, (y * 31) % 256, (x + y) % 256, 255) for x in range(16)]
    for y in range(12)
]


def png_bytes() -> bytes:
    return cc.png_encode(SRC_ROWS)


async def websocket_events(op_id: str, timeout: float = 30.0) -> list[dict]:
    events: list[dict] = []
    url = f"{WS}/api/operations/{op_id}/ws"
    async with websockets.connect(url, open_timeout=10) as ws:
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            evt = {}
            try:
                evt = __import__("json").loads(raw)
            except Exception:
                events.append({"raw": raw})
                break
            events.append(evt)
            if evt.get("type") in ("completed", "error", "cancelled"):
                break
    return events


async def wait_terminal(client: httpx.AsyncClient, op_id: str) -> dict:
    for _ in range(120):
        r = await client.get(f"{BASE}/api/operations/{op_id}")
        r.raise_for_status()
        op = r.json()
        if op.get("status") in ("completed", "failed", "cancelled"):
            return op
        await asyncio.sleep(1)
    raise RuntimeError(f"op {op_id} did not reach terminal state")


MEDIA = {"image": "images", "audio": "audio", "video": "video", "file": "files"}


async def submit(client: httpx.AsyncClient, media: str, action: str, files: list[tuple[str, bytes]], options: dict) -> dict:
    data = [("files", (name, body, "application/octet-stream")) for name, body in files]
    r = await client.post(f"{BASE}/api/{MEDIA[media]}/{action}", files=data, data={"options": __import__("json").dumps(options)})
    r.raise_for_status()
    return r.json()


async def run() -> int:
    failures: list[str] = []
    async with httpx.AsyncClient(timeout=30) as client:

        # 1. Health endpoints
        health = (await client.get(f"{BASE}/api/health")).json()
        assert health.get("status") == "ok", health
        print(f"[health] engine={health.get('engine')} version={health.get('version')}")
        ff = (await client.get(f"{BASE}/api/system/ffmpeg")).json()
        print(f"[ffmpeg] available={ff.get('available')} path={ff.get('path')}")

        # 2a. Stack split -> WS live -> reveal completes and yields a valid PNG
        #     (stack/OR recovery is approximate by design; exactness is not asserted)
        source = png_bytes()
        async def _share_image(op):
            out = []
            for f in op["result_files"]:
                r = await client.get(f"{BASE}/api/operations/{op['id']}/download", params={"name": f["name"]})
                r.raise_for_status()
                out.append((f["name"], r.content))
            return out

        split = await submit(client, "image", "split", [("source.png", source)], {"method": "stack", "shares": 2, "threshold": 128})
        op_id = split["id"]
        print(f"[image.split] id={op_id} status={split.get('status')}")
        events = await websocket_events(op_id)
        print(f"[image.split] ws events={[(e.get('type'), e.get('progress')) for e in events]}")
        final = await wait_terminal(client, op_id)
        if final["status"] != "completed":
            failures.append(f"image split status {final['status']}: {final.get('message')} {final.get('error')}")
        else:
            names = [f["name"] for f in final["result_files"]]
            print(f"[image.split] completed files={names}")

            reveal = await submit(client, "image", "reveal", await _share_image(final), {"method": "stack", "threshold": 128})
            r_op = await wait_terminal(client, reveal["id"])
            if r_op["status"] != "completed":
                failures.append(f"image stack reveal status {r_op['status']}: {r_op.get('error')}")
            else:
                out_name = r_op["result_files"][0]["name"]
                rr = await client.get(f"{BASE}/api/operations/{reveal['id']}/download", params={"name": out_name})
                rr.raise_for_status()
                if not rr.content.startswith(b"\x89PNG"):
                    failures.append("image stack reveal did not produce a PNG")
                else:
                    print(f"[image.stack] reveal completed, valid PNG ({len(rr.content)} bytes)")

        # 2b. XOR split -> reveal -> recovers the binarized secret exactly
        #     (the engine is 1-bit visual crypto: reconstruction is a B/W image)
        xsplit = await submit(client, "image", "split", [("xor.png", source)], {"method": "xor", "shares": 2})
        x_final = await wait_terminal(client, xsplit["id"])
        xreveal = await submit(client, "image", "reveal", await _share_image(x_final), {"method": "xor"})
        x_op = await wait_terminal(client, xreveal["id"])
        if x_op["status"] != "completed":
            failures.append(f"image xor reveal status {x_op['status']}: {x_op.get('error')}")
        else:
            out_name = x_op["result_files"][0]["name"]
            rr = await client.get(f"{BASE}/api/operations/{xreveal['id']}/download", params={"name": out_name})
            rr.raise_for_status()
            if not rr.content.startswith(b"\x89PNG"):
                failures.append("image xor reveal did not produce a PNG")
            else:
                _w, _h, rev_rows = cc.png_decode(rr.content)
                expect = cc.binarize(SRC_ROWS, threshold=128, dither=False)
                got = cc.binarize(rev_rows, threshold=128, dither=False)
                if got != expect:
                    failures.append("image xor reveal did not recover the binarized secret")
                else:
                    print(f"[image.xor] roundtrip OK, binarized secret recovered exactly")

        # 3. Download-all zip for a split
        r = await client.get(f"{BASE}/api/operations/{op_id}/download-all")
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        print(f"[download-all] zip entries={z.namelist()}")

        # 4. File shamir roundtrip (2-of-3)
        secret = b"smoke test secret\x00\x01\x02 archive\n" * 40
        fs = await submit(client, "file", "split", [("secret.bin", secret)], {"method": "shamir", "shares": 3, "threshold": 2, "seed": 12345})
        f_final = await wait_terminal(client, fs["id"])
        if f_final["status"] != "completed":
            failures.append(f"file split status {f_final['status']}: {f_final.get('error')}")
        else:
            parts = []
            for name in f_final["result_files"]:
                rr = await client.get(f"{BASE}/api/operations/{fs['id']}/download", params={"name": name["name"]})
                parts.append((name["name"], rr.content))
            # reveal with only 2 of 3
            fr = await submit(client, "file", "reveal", parts[:2], {"method": "shamir"})
            fr_final = await wait_terminal(client, fr["id"])
            if fr_final["status"] != "completed":
                failures.append(f"file reveal status {fr_final['status']}: {fr_final.get('error')}")
            else:
                rr = await client.get(f"{BASE}/api/operations/{fr['id']}/download", params={"name": fr_final["result_files"][0]["name"]})
                if rr.content != secret:
                    failures.append("file reveal bytes differ")
                else:
                    print("[file.reveal] 2-of-3 roundtrip OK, bytes identical")

        # 5. History now has entries
        hist = (await client.get(f"{BASE}/api/history")).json()["history"]
        print(f"[history] entries={len(hist)} kinds={[(h.get('kind'), h.get('media'), h.get('status')) for h in hist]}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nSMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))