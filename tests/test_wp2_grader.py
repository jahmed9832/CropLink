import io
import base64
import numpy as np
import pytest
from PIL import Image
from app.ml.grader import synth_image, Grader, compute_defect_pct


def test_garbage_empty_pdf_to_grade_returns_422(client, farmer_headers):
    payloads = [
        ("empty", b""),
        ("garbage", b"not an image at all just random bytes 12345"),
        ("pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"),
    ]

    for name, data in payloads:
        # Test /grade (multipart upload)
        files = {"file": ("test.jpg", data, "image/jpeg")}
        res = client.post("/grade", files=files, headers=farmer_headers)
        assert res.status_code == 422, f"/grade expected 422 for {name}, got {res.status_code}: {res.text}"
        assert "B" != res.json().get("grade") or res.status_code != 200

        # Test /grade-json
        b64 = base64.b64encode(data).decode()
        res_json = client.post("/grade-json", json={"photo_base64": b64, "crop": "tomato"}, headers=farmer_headers)
        assert res_json.status_code == 422, f"/grade-json expected 422 for {name}, got {res_json.status_code}: {res_json.text}"


def test_dark_brown_png_visible_defect_pct_bounded():
    # 200x200 dark-brown image
    img = Image.new("RGB", (200, 200), (60, 30, 10))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    g = Grader()
    res = g.grade_bytes(data, crop="tomato")
    assert 0 <= res["visible_defect_pct"] <= 100.0, f"Defect pct out of bounds: {res['visible_defect_pct']}"


def test_valid_synthetic_jpeg_still_grades(client, farmer_headers):
    rng = np.random.default_rng(42)
    img = synth_image("A", rng)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    data = buf.getvalue()

    # Direct grader test
    g = Grader()
    res = g.grade_bytes(data, crop="tomato")
    assert res["grade"] in ("A", "B", "C")
    assert res["confidence"] > 0
    assert res["crop"] == "tomato"

    # API /grade
    files = {"file": ("test.jpg", data, "image/jpeg")}
    res_api = client.post("/grade", files=files, headers=farmer_headers)
    assert res_api.status_code == 200
    assert res_api.json()["grade"] in ("A", "B", "C")
    assert res_api.json()["crop"] == "tomato"

    # API /grade-json
    b64 = base64.b64encode(data).decode()
    res_json = client.post("/grade-json", json={"photo_base64": b64, "crop": "potato"}, headers=farmer_headers)
    assert res_json.status_code == 200
    assert res_json.json()["grade"] in ("A", "B", "C")
    assert res_json.json()["crop"] == "potato"
