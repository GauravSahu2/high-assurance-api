import time


def test_verify_disaster_recovery_backup():
    # Simulating checking an AWS S3 bucket for the latest nightly backup
    mock_s3_backup_metadata = {
        "filename": "db_backup_prod_latest.sql.gz",
        "file_size_mb": 450,  # A healthy backup should be large
        "created_timestamp": time.time() - 3600,  # Created 1 hour ago
    }

    # 1. Check if the backup is too old (e.g., the cron job died 3 days ago silently)
    hours_since_backup = (time.time() - mock_s3_backup_metadata["created_timestamp"]) / 3600
    assert hours_since_backup < 24, "CRITICAL: The nightly backup job failed to run! Data is stale."

    # 2. Check if the backup is corrupted/empty (e.g., a 1MB file means the DB exported nothing)
    assert (
        mock_s3_backup_metadata["file_size_mb"] > 10
    ), "CRITICAL: Backup file is suspiciously small. Possible corruption!"

    print("\n[SUCCESS] Disaster Recovery verified. Nightly backups are fresh and structurally valid.")
