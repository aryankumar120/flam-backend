import sqlite3
import json
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from .models import Job, JobState, Config

class Storage:
    def __init__(self, db_path: str = ".queuectl.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    command TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    next_retry_at TEXT,
                    error_message TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_next_retry ON jobs(next_retry_at)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save_job(self, job: Job) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO jobs
                (id, command, state, attempts, max_retries, created_at, updated_at, next_retry_at, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.command,
                job.state,
                job.attempts,
                job.max_retries,
                job.created_at,
                job.updated_at,
                job.next_retry_at,
                job.error_message,
            ))
            conn.commit()
            return cursor.rowcount > 0

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()

            if row:
                return Job.from_dict(dict(row))
            return None

    def get_jobs_by_state(self, state: str) -> List[Job]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE state = ? ORDER BY created_at", (state,))
            return [Job.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_all_jobs(self) -> List[Job]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY created_at")
            return [Job.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_retryable_jobs(self, current_time: str) -> List[Job]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM jobs
                WHERE state = ?
                AND next_retry_at IS NOT NULL
                AND next_retry_at <= ?
                ORDER BY next_retry_at
            """, (JobState.FAILED, current_time))
            return [Job.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_pending_job(self) -> Optional[Job]:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("BEGIN IMMEDIATE")

            cursor.execute("""
                SELECT * FROM jobs
                WHERE state = ?
                ORDER BY created_at
                LIMIT 1
            """, (JobState.PENDING,))

            row = cursor.fetchone()
            if row:
                job = Job.from_dict(dict(row))

                job.state = JobState.PROCESSING
                job.update_timestamp()

                cursor.execute("""
                    UPDATE jobs
                    SET state = ?, updated_at = ?
                    WHERE id = ?
                """, (job.state, job.updated_at, job.id))

                conn.commit()
                return job
            else:
                conn.commit()
                return None

    def update_job_state(self, job_id: str, state: str, error_message: Optional[str] = None) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs
                SET state = ?, updated_at = ?, error_message = ?
                WHERE id = ?
            """, (state, Job(id="", command="").updated_at, error_message, job_id))
            conn.commit()
            return cursor.rowcount > 0

    def increment_job_attempts(self, job_id: str, next_retry_at: Optional[str] = None) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs
                SET attempts = attempts + 1, updated_at = ?, next_retry_at = ?
                WHERE id = ?
            """, (Job(id="", command="").updated_at, next_retry_at, job_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_job(self, job_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_job_counts(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT state, COUNT(*) as count FROM jobs GROUP BY state")
            return {row["state"]: row["count"] for row in cursor.fetchall()}

    def save_config(self, key: str, value: Any):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO config (key, value)
                VALUES (?, ?)
            """, (key, json.dumps(value)))
            conn.commit()

    def get_config(self, key: str, default: Any = None) -> Any:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()

            if row:
                return json.loads(row["value"])
            return default

    def load_config(self) -> Config:
        return Config(
            max_retries=self.get_config("max_retries", Config.DEFAULT_MAX_RETRIES),
            backoff_base=self.get_config("backoff_base", Config.DEFAULT_BACKOFF_BASE),
            db_path=self.db_path,
        )

    def save_full_config(self, config: Config):
        self.save_config("max_retries", config.max_retries)
        self.save_config("backoff_base", config.backoff_base)
