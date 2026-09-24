import sqlite3
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


def ensure_sqlite_schema(db_url: str | None = None) -> None:
    """Backfill missing SQLite columns for older DB files created before schema updates."""
    if db_url is None:
        db_url = settings.DATABASE_URL

    if "sqlite" not in db_url:
        return

    db_path = db_url.replace("sqlite+aiosqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]

    if not db_path:
        return

    try:
        with sqlite3.connect(db_path) as conn:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(test_runs)").fetchall()]
            if "blocked_tests" not in cols:
                conn.execute("ALTER TABLE test_runs ADD COLUMN blocked_tests INTEGER NOT NULL DEFAULT 0")
            if "error_message" not in cols:
                conn.execute("ALTER TABLE test_runs ADD COLUMN error_message TEXT")
            result_cols = [row[1] for row in conn.execute("PRAGMA table_info(test_results)").fetchall()]
            if result_cols and "result_validity" not in result_cols:
                conn.execute("ALTER TABLE test_results ADD COLUMN result_validity TEXT NOT NULL DEFAULT 'VALID'")
            if result_cols and "attempt_number" not in result_cols:
                conn.execute("ALTER TABLE test_results ADD COLUMN attempt_number INTEGER NOT NULL DEFAULT 1")
            conn.commit()
    except sqlite3.Error:
        # The table may not exist yet; create_all() will handle that on the next startup step.
        return


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    ensure_sqlite_schema()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
