from datetime import timedelta
from types import SimpleNamespace

from app.agents.priority_manager import calculate_priority
from app.agents.request_analysis import analyze_text
from app.services.blood_rules import candidate_groups, normalize_blood_group
from app.utils.time import utcnow


def test_normalize_blood_group():
    assert normalize_blood_group("o neg") == "O-"
    assert normalize_blood_group("O-negative") == "O-"
    assert normalize_blood_group("ab +ve") == "AB+"
    assert normalize_blood_group("B positive") == "B+"
    assert normalize_blood_group("A") is None
    assert normalize_blood_group("xyz") is None


def test_demo_compatibility_rule():
    assert candidate_groups("O-") == ["O-"]
    assert set(candidate_groups("A+")) == {"A+", "A-", "O+", "O-"}


def test_priority_rules_are_explainable():
    req = SimpleNamespace(urgency="critical", units_requested=3, deadline=utcnow() + timedelta(hours=1))
    p = calculate_priority(req)
    assert p["priority"] == "critical" and p["score"] == 100
    assert "urgency 'critical'" in p["reason"]
    low = calculate_priority(SimpleNamespace(urgency="normal", units_requested=1,
                                             deadline=utcnow() + timedelta(days=3)))
    assert low["priority"] == "low"


def test_free_text_extraction_rules_fallback():
    out = analyze_text("RTA patient in ICU, need 2 O neg, maybe 3 if surgery runs long, before 6pm",
                       default_location="Faisalabad")
    f = out["fields"]
    assert out["source"] == "rules"
    assert f["blood_group"] == "O-" and f["units_requested"] == 2 and f["urgency"] == "critical"
    assert f["location"] == "Faisalabad" and "deadline" in f
    assert out["validation_status"] == "valid"


def test_missing_facts_are_not_invented():
    out = analyze_text("We need some blood please")
    assert "blood_group" in out["missing_fields"] and "units_requested" in out["missing_fields"]
    assert out["validation_status"] == "incomplete"


def test_llm_output_is_validated_and_gaps_filled(monkeypatch):
    """Simulates Vultr Inference returning partly-bad JSON: bad values are dropped, rules fill gaps."""
    from app.agents import request_analysis as ra

    monkeypatch.setattr(ra, "llm_json", lambda *a, **k: {
        "blood_group": "O negative", "units_requested": 99, "urgency": "critical",
        "location": "Faisalabad", "deadline": None, "notes": "possibly 3 units"})
    out = ra.analyze_text("need 2 O neg in Faisalabad ICU in 3 hours")
    f = out["fields"]
    assert out["source"] == "llm"
    assert f["blood_group"] == "O-"          # normalised
    assert f["units_requested"] == 2         # 99 rejected by validation, rule value used
    assert "deadline" in f                   # filled by rules ("in 3 hours")


def test_llm_failure_falls_back_to_rules(monkeypatch):
    from app.agents import request_analysis as ra

    monkeypatch.setattr(ra, "llm_json", lambda *a, **k: None)
    out = ra.analyze_text("need 3 units of B+ in Lahore tomorrow")
    assert out["source"] == "rules" and out["fields"]["blood_group"] == "B+"
    assert out["fields"]["units_requested"] == 3 and out["fields"]["location"] == "Lahore"
