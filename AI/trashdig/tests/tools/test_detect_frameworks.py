import json
from unittest.mock import patch

from trashdig.tools.detect_frameworks import detect_frameworks


@patch("trashdig.tools.detect_frameworks._get_struct", autospec=True)
@patch("trashdig.tools.detect_frameworks._detect", autospec=True)
def test_detect_frameworks(mock_detect, mock_get_struct):
    mock_get_struct.return_value = ["package.json"]
    mock_detect.return_value = {"web": ["Express"]}
    res = detect_frameworks(".")
    assert json.loads(res) == {"web": ["Express"]}
