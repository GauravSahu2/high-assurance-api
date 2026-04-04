import pytest
from unittest.mock import patch
from main import init_db

def test_init_db_exception_triggers_rollback():
    """Ensure that database initialization failures trigger a safe rollback."""
    with patch("main.SessionLocal") as mock_session:
        mock_db = mock_session.return_value
        # Force the database query to fail, triggering the except block
        mock_db.query.side_effect = Exception("Simulated DB Init Error")
        init_db()
        # Verify the safety net caught it
        mock_db.rollback.assert_called_once()
