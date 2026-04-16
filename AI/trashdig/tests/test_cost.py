import pytest
from unittest.mock import patch, MagicMock
from trashdig.services.cost import CostTracker

@pytest.fixture
def mock_pricing():
    """Mocks the pricing fetch to return stable values for testing."""
    with patch("urllib.request.urlopen") as mock_url:
        # Return a mock response object
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"gemini-2.0-flash": {"input_cost_per_token": 0.00000015, "output_cost_per_token": 0.00000060}, "gemini-2.0-pro-exp": {"input_cost_per_token": 0.00000125, "output_cost_per_token": 0.00000500}}'
        mock_response.__enter__.return_value = mock_response
        mock_url.return_value = mock_response
        yield mock_url

def test_cost_tracker_initial_cost(mock_pricing):
    tracker = CostTracker()
    assert tracker.get_total_cost() == 0.0
    assert tracker.total_input_tokens == 0
    assert tracker.total_output_tokens == 0

def test_cost_tracker_record_usage_flash(mock_pricing):
    tracker = CostTracker()
    # gemini-2.0-flash: $0.15/1M input, $0.60/1M output
    # 1,000,000 input = $0.15
    # 1,000,000 output = $0.60
    tracker.record_usage("gemini-2.0-flash", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == pytest.approx(0.75)
    assert tracker.total_input_tokens == 1_000_000
    assert tracker.total_output_tokens == 1_000_000

def test_cost_tracker_record_usage_pro(mock_pricing):
    tracker = CostTracker()
    # gemini-2.0-pro-exp: $1.25/1M input, $5.00/1M output
    tracker.record_usage("gemini-2.0-pro-exp", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == pytest.approx(6.25)
    assert tracker.total_input_tokens == 1_000_000
    assert tracker.total_output_tokens == 1_000_000

def test_cost_tracker_record_usage_multiple(mock_pricing):
    tracker = CostTracker()
    tracker.record_usage("gemini-2.0-flash", 1_000_000, 0) # $0.15
    tracker.record_usage("gemini-2.0-pro-exp", 0, 1_000_000) # $5.00
    assert tracker.get_total_cost() == pytest.approx(5.15)
    assert tracker.total_input_tokens == 1_000_000
    assert tracker.total_output_tokens == 1_000_000

def test_cost_tracker_unknown_model(mock_pricing):
    tracker = CostTracker()
    tracker.record_usage("unknown-model", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == 0.0
    # Still records tokens even if unknown model (for tracking purposes)
    assert tracker.total_input_tokens == 1_000_000
    assert tracker.total_output_tokens == 1_000_000

def test_cost_tracker_prefix_match(mock_pricing):
    tracker = MagicMock() # We need a clean tracker or mock the specific call
    # Let's just use the real one but ensure prefix match works with our mock data
    tracker = CostTracker()
    # gemini-2.0-flash-001 should match gemini-2.0-flash in prefix logic
    tracker.record_usage("gemini-2.0-flash-001", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == pytest.approx(0.75)

def test_cost_tracker_custom_rates(mock_pricing):
    custom_rates = {
        "custom-model": {"input": 1.0, "output": 2.0}
    }
    tracker = CostTracker(rates=custom_rates)
    tracker.record_usage("custom-model", 1_000_000, 1_000_000)
    assert tracker.get_total_cost() == pytest.approx(3.0)
