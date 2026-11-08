import shutil
import sqlite3
from datetime import datetime

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import DATABASE_URL, DB_PATH
from app.models.models import Base

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record):
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


def _backup_legacy_database() -> None:
    """The v1/v2 database has a different schema. Instead of crashing with 'no such column',
    move it aside (keeping the data) and let a fresh, correctly-shaped database be created."""
    if not DB_PATH.exists():
        return
    con = sqlite3.connect(DB_PATH)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(students)")]
    finally:
        con.close()
    if cols and "roll_number" not in cols:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        for suffix in ("", "-wal", "-shm"):
            p = DB_PATH.parent / (DB_PATH.name + suffix)
            if p.exists():
                shutil.move(str(p), str(p) + f".old-schema-{stamp}.bak")
        print(f"[TalentHub] Old-schema database moved aside as {DB_PATH.name}.old-schema-{stamp}.bak")


async def init_db() -> None:
    _backup_legacy_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight forward migration for existing v3 SQLite databases.
        def migrate(sync_conn):
            cols = [
                row[1]
                for row in sync_conn.exec_driver_sql(
                    "PRAGMA table_info(job_listings)"
                ).fetchall()
            ]
            if "selection_rounds" not in cols:
                sync_conn.exec_driver_sql(
                    "ALTER TABLE job_listings ADD COLUMN selection_rounds TEXT NOT NULL DEFAULT '[]'"
                )
            # Preserve the explicit all-branches meaning from earlier releases.
            sync_conn.exec_driver_sql(
                "UPDATE job_listings SET allowed_branches='*' "
                "WHERE allowed_branches IS NULL OR allowed_branches=''"
            )
        await conn.run_sync(migrate)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
