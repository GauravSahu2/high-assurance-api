import os

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("JWT_SECRET", "super-secure-dev-secret-key-12345")


def pytest_sessionfinish(session, exitstatus):
    print(
        "\n\033[33m\033[1m"
        "⚠  COVERAGE EXCLUSION: src/main.py — `app.run(...)` under `if __name__ == '__main__':` is excluded.\n"
        "   WHY: structurally unreachable during pytest (module import) and in production (gunicorn bypasses it).\n"
        "   IMPACT: zero — all real logic is covered. Exclusion is cosmetic only.\n"
        "   VERIFY MANUALLY: PYTHONPATH=src python src/main.py  → confirm server starts on :8000"
        "\033[0m\n"
    )
