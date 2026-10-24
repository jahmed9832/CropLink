import pytest
from unittest.mock import patch
from app.engine.assistant import parse
from app.engine.loss import assess


def test_assistant_parse_word_boundaries():
    # 1. "What is the price today?" -> intent price, crop is NOT rice
    p1 = parse("What is the price today?")
    assert p1["crop"] is None
    assert p1["intent"] == "price"

    # 2. "value of my crop" -> crop is NOT potato
    p2 = parse("value of my crop")
    assert p2["crop"] is None

    # 3. "this is great" -> intent is NOT greeting
    p3 = parse("this is great")
    assert p3["intent"] != "greeting"

    # 4. "in 2 months" -> quantity is NOT 80 kg
    p4 = parse("in 2 months")
    assert p4["quantity_kg"] is None


def test_loss_assess_boundary_and_validation():
    # Negative inputs raise ValueError
    with pytest.raises(ValueError):
        assess("tomato", -5, 30, 20)
    with pytest.raises(ValueError):
        assess("tomato", 5, 30, -10)
    with pytest.raises(ValueError):
        assess("tomato", 5, 30, 20, hours_to_deadline=-1)

    # Extreme temperature (1000 C) does not produce complex numbers or error
    res = assess("tomato", 10, 1000, 50)
    assert 0 <= res["expected_loss_pct"] <= 100


def test_price_intent_bypasses_gemini(client, farmer_auth):
    headers = farmer_auth["headers"]
    from app.config import settings
    settings.GEMINI_API_KEY = "dummy-test-key"

    with patch("app.engine.assistant.ask_gemini") as mock_gemini:
        # A price intent should be answered by the real forecaster engine, never Gemini
        resp = client.post("/assistant/chat", json={"text": "টমেটোর আজকের দাম কত?"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "rule_based"
        assert "data" in data
        # Ensure ask_gemini was NEVER called for price intent
        mock_gemini.assert_not_called()

        # A general greeting query with Gemini key SHOULD invoke ask_gemini
        mock_gemini.return_value = "Hello from stubbed Gemini!"
        resp_greet = client.post("/assistant/chat", json={"text": "hello"}, headers=headers)
        assert resp_greet.status_code == 200
        greet_data = resp_greet.json()
        assert greet_data["source"] == "gemini"
        assert greet_data["reply"] == "Hello from stubbed Gemini!"
        mock_gemini.assert_called_once()


def test_loss_intent_prompts_user_when_params_missing(client, farmer_auth):
    headers = farmer_auth["headers"]
    # When asking about spoilage/loss without hours/dist/temp, the assistant should prompt the user
    resp = client.post("/assistant/chat", json={"text": "টমেটো পচে যাচ্ছে"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "rule_based"
    assert "ঘণ্টা" in data["reply"] or "hours" in data["reply"]
    assert data.get("data") is None
