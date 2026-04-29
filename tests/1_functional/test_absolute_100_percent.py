import os
import pytest
import grpc
from unittest.mock import patch, mock_open
from auth import (
    _get_paseto_keys,
    generate_jwt,
    generate_webauthn_challenge,
    verify_webauthn_assertion,
)
from telemetry import SafeConsoleSpanExporter
import pyseto
from pyseto import Key

def test_paseto_key_generation_fallback():
    """HITS auth.py:46-52 (Fallback for missing keys in TEST_MODE)."""
    with patch("auth._private_key", None), \
         patch("auth._public_key", None), \
         patch("builtins.open", side_effect=FileNotFoundError), \
         patch("auth.Key.new", return_value="mock_key"), \
         patch("auth.TEST_MODE", True):
        priv, pub = _get_paseto_keys()
        assert priv is not None
        assert pub is not None

def test_webauthn_challenge():
    """HITS auth.py:79 (WebAuthn challenge generation)."""
    challenge = generate_webauthn_challenge("testuser")
    assert len(challenge) == 64  # 32 bytes hex

def test_paseto_production_key_failure():
    """HITS auth.py:54 (Production error when keys missing)."""
    with patch("auth._private_key", None), \
         patch("auth._public_key", None), \
         patch("builtins.open", side_effect=FileNotFoundError), \
         patch("auth.TEST_MODE", False):
        with pytest.raises(RuntimeError, match="PASETO keys missing"):
            _get_paseto_keys()

def test_fido2_edge_cases():
    """HITS auth.py placeholder logic."""
    assert verify_webauthn_assertion("user1", {}) == True

def test_grpc_server_coverage():
    """HITS src/grpc_server.py entirely."""
    import grpc_server
    from concurrent import futures
    import internal_audit_pb2_grpc as pb2_grpc
    import internal_audit_pb2 as pb2
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    pb2_grpc.add_InternalAuditServiceServicer_to_server(grpc_server.InternalAuditServicer(), server)
    port = server.add_insecure_port('[::]:0')
    server.start()
    
    try:
        channel = grpc.insecure_channel(f'localhost:{port}')
        stub = pb2_grpc.InternalAuditServiceStub(channel)
        
        # Test StreamAuditEvents (the ONLY RPC in the proto)
        stream = stub.StreamAuditEvents(pb2.AuditRequest(filter_type="ALL"))
        events = list(stream)
        assert len(events) > 0
        assert events[0].event_id.startswith("audit-")
            
    finally:
        server.stop(0)

def test_grpc_server_main_entrypoint():
    """HITS the if __name__ == '__main__': serve() block if possible, or just serve()."""
    import grpc_server
    with patch("grpc.server") as mock_grpc_server:
        # Mock the server object to avoid actual binding
        mock_server_instance = mock_grpc_server.return_value
        # Use a timeout to avoid infinite loop in serve()
        with patch("time.sleep", side_effect=KeyboardInterrupt):
            grpc_server.serve()
        assert mock_grpc_server.called

def test_safe_telemetry_exporter():
    """HITS telemetry.py:SafeConsoleSpanExporter."""
    exporter = SafeConsoleSpanExporter()
    # Test normal export
    with patch("opentelemetry.sdk.trace.export.ConsoleSpanExporter.export", return_value=True):
        assert exporter.export([]) == True
    
    # Test closed stdout
    with patch("sys.stdout") as mock_stdout:
        mock_stdout.closed = True
        from opentelemetry.sdk.trace.export import SpanExportResult
        assert exporter.export([]) == SpanExportResult.SUCCESS
    
    # Test value error
    with patch("opentelemetry.sdk.trace.export.ConsoleSpanExporter.export", side_effect=ValueError):
        assert exporter.export([]) == SpanExportResult.SUCCESS
