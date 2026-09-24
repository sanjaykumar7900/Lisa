import sqlite3

from app.db.database import ensure_sqlite_schema


def test_ensure_sqlite_schema_adds_missing_test_run_columns(tmp_path):
    db_path = tmp_path / "lisa.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE test_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            run_number TEXT NOT NULL,
            autonomy_level INTEGER NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            total_tests INTEGER NOT NULL,
            passed_tests INTEGER NOT NULL,
            failed_tests INTEGER NOT NULL,
            error_message TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    ensure_sqlite_schema(str(db_path))

    conn = sqlite3.connect(db_path)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(test_runs)").fetchall()]
    conn.close()

    assert "blocked_tests" in columns
    assert "error_message" in columns
