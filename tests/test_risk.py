from app.services.risk import classify_risk

def test_high_risk_phrase_is_flagged():
    assert classify_risk("Please transfer money now") == "high"

def test_regular_task_is_unclassified():
    assert classify_risk("Research market structure") == "unclassified"
