import os
from unittest.mock import patch

import pytest
from src.config import get_secret


def test_get_secret_vault_success():
    """Test get_secret when Vault returns a valid value."""
    with patch("hvac.Client") as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.secrets.kv.v2.read_secret_version.return_value = {"data": {"data": {"MY_KEY": "vault_val"}}}

        # Manually set VAULT envs to trigger the logic
        with patch.dict(os.environ, {"VAULT_ADDR": "http://vault:8200", "VAULT_TOKEN": "root"}):
            import src.config

            src.config.VAULT_ADDR = "http://vault:8200"
            src.config.VAULT_TOKEN = "root"
            val = get_secret("MY_KEY")
            assert val == "vault_val"


def test_get_secret_vault_failure_fallback():
    """Test get_secret when Vault fails but Env exists."""
    with patch("hvac.Client") as mock_client:
        mock_client.side_effect = Exception("Connection Refused")

        with patch.dict(
            os.environ,
            {"VAULT_ADDR": "http://vault:8200", "VAULT_TOKEN": "root", "FALLBACK_KEY": "env_val"},
        ):
            val = get_secret("FALLBACK_KEY")
            assert val == "env_val"


def test_get_secret_missing_raises_error():
    """Test get_secret raises ValueError when key is totally missing."""
    with patch.dict(os.environ, {}, clear=True):
        import src.config

        src.config.VAULT_ADDR = None
        src.config.VAULT_TOKEN = None
        # We need to clear defaults for this test
        with pytest.raises(ValueError, match="Missing required configuration key"):
            get_secret("TOTALLY_MISSING_KEY")
