import pytest
from src.dlp_processor import dlp_redactor
from unittest.mock import MagicMock

def test_dlp_redactor_exception_coverage():
    """Trigger the try-except block in dlp_redactor for 100% coverage."""
    # Create a mock string-like object that raises an error on sub
    class Exploder(str):
        def __getattr__(self, name):
            raise Exception("Force coverage")
            
    logger = MagicMock()
    # We pass a dictionary with a value that is technically a string but will fail regex sub
    # Actually, re.sub checks for string type specifically.
    # Let's just mock EMAIL_PATTERN.sub to raise an exception.
    import src.dlp_processor as dlp
    original = dlp.EMAIL_PATTERN
    dlp.EMAIL_PATTERN = MagicMock()
    dlp.EMAIL_PATTERN.sub.side_effect = Exception("Force coverage")
    
    try:
        event = {"msg": "test@example.com"}
        # This will hit line 30: except Exception
        result = dlp_redactor(logger, "test", event)
        assert result["msg"] == "test@example.com" # Should remain unchanged
    finally:
        dlp.EMAIL_PATTERN = original
