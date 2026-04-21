# tests/6_database_state/test_transaction_rollback.py
import sqlite3  # Using SQLite for local simulation, replace with psycopg2 for PostgreSQL


def test_atomic_rollback_on_failure():
    # 1. Connect to an in-memory database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # 2. Setup initial state: User A has $100, User B has $50
    cursor.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY, balance REAL)")
    cursor.execute("INSERT INTO accounts VALUES ('UserA', 100.0), ('UserB', 50.0)")
    conn.commit()

    # 3. Simulate a flawed transaction (Money leaves A, but inserting to B causes an error)
    try:
        # Start transaction
        conn.execute("BEGIN TRANSACTION")

        # Deduct from A
        cursor.execute("UPDATE accounts SET balance = balance - 50.0 WHERE id = 'UserA'")

        # INTENTIONAL FAILURE: Typo in the column name ('balanc' instead of 'balance')
        cursor.execute("UPDATE accounts SET balanc = balance + 50.0 WHERE id = 'UserB'")

        conn.commit()  # This will never run
    except sqlite3.OperationalError:
        # 4. THE ROLLBACK: The system caught the crash and must revert the deduction from User A
        conn.rollback()

    # 5. THE ASSERTION: Verify User A still has their original $100. No money was lost in the void.
    cursor.execute("SELECT balance FROM accounts WHERE id = 'UserA'")
    final_balance_a = cursor.fetchone()[0]

    assert (
        final_balance_a == 100.0
    ), "CRITICAL: ACID properties violated. Data corruption occurred!"
    print("\n[SUCCESS] Transaction rolled back safely. Database state remains uncorrupted.")
