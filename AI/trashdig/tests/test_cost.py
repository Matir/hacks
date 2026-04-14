import pytest
from trashdig.services.cost import CostTracker

def test_cost_tracker_initial_cost():
    tracker = CostTracker()
    assert tracker.get_total_cost() == 0.0

def test_cost_tracker_record_usage_flash():
    tracker = CostTracker()
    # gemini-2.0-flash: $0.15/1M input, $0.60/1M output
    # 1,000,000 input = $0.15
    # 1,000,000 output = $0.60
    tracker.record_usage("gemini-2.0-flash", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == pytest.approx(0.75)

def test_cost_tracker_record_usage_pro():
    tracker = CostTracker()
    # gemini-2.0-pro-exp: $1.25/1M input, $5.00/1M output
    tracker.record_usage("gemini-2.0-pro-exp", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == pytest.approx(6.25)

def test_cost_tracker_record_usage_multiple():
    tracker = CostTracker()
    tracker.record_usage("gemini-2.0-flash", 1_000_000, 0) # $0.15
    tracker.record_usage("gemini-2.0-pro-exp", 0, 1_000_000) # $5.00
    assert tracker.get_total_cost() == pytest.approx(5.15)

def test_cost_tracker_unknown_model():
    tracker = CostTracker()
    tracker.record_usage("unknown-model", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == 0.0

def test_cost_tracker_prefix_match():
    tracker = CostTracker()
    # gemini-2.0-flash-001 should match gemini-2.0-flash
    tracker.record_usage("gemini-2.0-flash-001", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == pytest.approx(0.75)

def test_cost_tracker_custom_rates():
    custom_rates = {
        "custom-model": {"input": 1.0, "output": 2.0}
    }
    tracker = CostTracker(rates=custom_rates)
    tracker.record_usage("custom-model", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == pytest.approx(3.0)
