from unittest.mock import patch, MagicMock
from trashdig.main import main

@patch("trashdig.main.TrashDigApp")
@patch("trashdig.main.load_config")
def test_main(mock_load_config, mock_app_class):
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config
    
    mock_app = MagicMock()
    mock_app_class.return_value = mock_app
    
    main()
    
    mock_load_config.assert_called_once()
    mock_app_class.assert_called_once_with(config=mock_config)
    mock_app.run.assert_called_once()
