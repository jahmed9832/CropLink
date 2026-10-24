import io
import pytest
from PIL import Image


def _make_dummy_jpeg():
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color="red").save(buf, format="JPEG")
    return buf.getvalue()


def test_buyer_calling_get_farmer_gets_no_phone(client, farmer_auth, buyer_auth, admin_auth):
    farmer_id = farmer_auth["user_id"]
    buyer_headers = buyer_auth["headers"]
    farmer_headers = farmer_auth["headers"]
    admin_headers = admin_auth["headers"]

    # Buyer view: no phone
    resp = client.get(f"/farmers/{farmer_id}", headers=buyer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "phone" not in data
    assert "name" in data
    assert "location" in data

    # Owner view: gets phone
    owner_resp = client.get(f"/farmers/{farmer_id}", headers=farmer_headers)
    assert owner_resp.status_code == 200
    assert "phone" in owner_resp.json()

    # Admin view: gets phone
    admin_resp = client.get(f"/farmers/{farmer_id}", headers=admin_headers)
    assert admin_resp.status_code == 200
    assert "phone" in admin_resp.json()


def test_from_photo_with_no_farmer_id_stores_token_farmer_id(client, farmer_auth):
    farmer_headers = farmer_auth["headers"]
    farmer_id = farmer_auth["user_id"]
    jpeg_bytes = _make_dummy_jpeg()

    resp = client.post(
        "/batches/from-photo",
        data={"crop": "tomato", "quantity_kg": 100, "district": "Bogura"},
        files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
        headers=farmer_headers,
    )
    assert resp.status_code == 200
    batch = resp.json()["batch"]
    assert batch["farmer_id"] == farmer_id


def test_from_photo_for_another_farmer_returns_403(client, farmer_auth, farmer2_auth):
    farmer_headers = farmer_auth["headers"]
    other_farmer_id = farmer2_auth["user_id"]
    jpeg_bytes = _make_dummy_jpeg()

    resp = client.post(
        "/batches/from-photo",
        data={"farmer_id": other_farmer_id, "crop": "tomato", "quantity_kg": 100, "district": "Bogura"},
        files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
        headers=farmer_headers,
    )
    assert resp.status_code == 403


def test_post_farmers_and_buyers_restricted_to_admin(client, farmer_auth, admin_auth):
    farmer_headers = farmer_auth["headers"]
    admin_headers = admin_auth["headers"]

    # Non-admin creates farmer profile -> 403
    resp = client.post("/farmers", json={"name": "New Farmer", "phone": "01799999999"}, headers=farmer_headers)
    assert resp.status_code == 403

    # Admin creates farmer profile -> 200
    resp_adm = client.post("/farmers", json={"name": "New Admin Farmer", "phone": "01799999999"}, headers=admin_headers)
    assert resp_adm.status_code == 200
