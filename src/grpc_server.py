import os
import sys
import time
from concurrent import futures

import grpc

# Add generated directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "generated"))

import internal_audit_pb2
import internal_audit_pb2_grpc


class InternalAuditServicer(internal_audit_pb2_grpc.InternalAuditServiceServicer):
    def StreamAuditEvents(self, request, context):
        """Mock implementation of audit event streaming."""
        events = [
            {
                "event_id": "audit-001",
                "timestamp": "2026-04-27T10:00:00Z",
                "user_id": "admin",
                "action": "LOGIN",
                "status": "SUCCESS",
                "detail": "Admin logged in from 192.168.1.1",
            },
            {
                "event_id": "audit-002",
                "timestamp": "2026-04-27T10:05:00Z",
                "user_id": "user_1",
                "action": "TRANSFER",
                "status": "SUCCESS",
                "detail": "Transferred 500.00 to user_2",
            },
        ]

        for event_data in events:
            yield internal_audit_pb2.AuditEvent(**event_data)
            time.sleep(0.5)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    internal_audit_pb2_grpc.add_InternalAuditServiceServicer_to_server(InternalAuditServicer(), server)
    server.add_insecure_port("[::]:50051")
    print("gRPC Internal Audit Server started on port 50051")
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":  # pragma: no cover
    serve()
