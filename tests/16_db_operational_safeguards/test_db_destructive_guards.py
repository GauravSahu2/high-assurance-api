import time


# Mocking a Database Execution Engine
class SecureDBProxy:
    def __init__(self):
        self.last_snapshot_time = 0

    def take_snapshot(self):
        self.last_snapshot_time = time.time()
        return "Snapshot created."

    def execute_query(self, query):
        query_upper = query.upper()

        # Detect highly destructive commands
        is_destructive = (
            "DROP " in query_upper
            or "TRUNCATE " in query_upper
            or ("DELETE FROM" in query_upper and "WHERE" not in query_upper)
        )

        if is_destructive:
            # Enforce the Snapshot Rule: Must have a snapshot from the last 5 minutes (300 seconds)
            time_since_snapshot = time.time() - self.last_snapshot_time
            if time_since_snapshot > 300:
                return "BLOCKED: Destructive action attempted without a recent backup!"
            return "SUCCESS: Query executed. Backup exists."

        return "SUCCESS: Safe query executed."


def test_prevent_intern_mistakes():
    db = SecureDBProxy()

    # 1. An intern accidentally tries to wipe the users table without a backup
    response = db.execute_query("DELETE FROM users;")
    assert "BLOCKED" in response, "CRITICAL FAIL: System allowed a mass deletion without a backup!"

    # 2. A Senior Engineer takes a snapshot first, then runs a necessary migration
    db.take_snapshot()
    response = db.execute_query("DROP TABLE old_legacy_logs;")
    assert "SUCCESS" in response, "CRITICAL FAIL: System blocked a safe, backed-up operation."

    print("\n[SUCCESS] Operational Guardrails active. Destructive DB actions require fresh snapshots.")
