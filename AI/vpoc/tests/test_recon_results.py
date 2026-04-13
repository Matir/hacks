import os
import tempfile
import json
from core.models import ReconResult
from core.storage import StorageManager

def test_recon_result_crud():
    """Verifies add and retrieve operations for ReconResult."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = StorageManager(db_path)

        result = ReconResult(
            project_id="test_proj",
            file_path="routes.py",
            result_type="ENTRY_POINT",
            description="API routes mapping",
            priority="HIGH",
            metadata_json=json.dumps({"methods": ["GET", "POST"]})
        )
        
        stored = manager.add_recon_result(result)
        assert stored.id is not None
        assert stored.project_id == "test_proj"
        
        results = manager.get_recon_results("test_proj")
        assert len(results) == 1
        assert results[0].file_path == "routes.py"
        assert results[0].result_type == "ENTRY_POINT"
        assert results[0].priority == "HIGH"
        
        # Verify non-existent project returns empty list
        assert manager.get_recon_results("other_proj") == []
