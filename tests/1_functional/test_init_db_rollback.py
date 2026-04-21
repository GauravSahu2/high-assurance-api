from unittest.mock import patch

import pytest

from main import init_db


def test_init_db_exception_triggers_rollback():
    """Ensure that database initialization failures trigger a safe rollback."""
    with patch("main.SessionLocal") as mock_session:
        mock_db = mock_session.return_value
        # Force the database query to fail
        mock_db.query.side_effect = Exception("Simulated DB Init Error")

        # Verify the exception propagates
        with pytest.raises(Exception, match="Simulated DB Init Error"):
            init_db()

        # Verify rollback was called before the exception was raised
        mock_db.rollback.assert_called_once()
