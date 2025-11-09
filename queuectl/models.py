import json
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any

class JobState(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"

class Job:
    def __init__(
        self,
        id: str,
        command: str,
        state: str = JobState.PENDING,
        attempts: int = 0,
        max_retries: int = 3,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        next_retry_at: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.id = id
        self.command = command
        self.state = state
        self.attempts = attempts
        self.max_retries = max_retries
        self.created_at = created_at or datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.updated_at = updated_at or datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.next_retry_at = next_retry_at
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "command": self.command,
            "state": self.state,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "next_retry_at": self.next_retry_at,
            "error_message": self.error_message,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        return cls(
            id=data["id"],
            command=data["command"],
            state=data.get("state", JobState.PENDING),
            attempts=data.get("attempts", 0),
            max_retries=data.get("max_retries", 3),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            next_retry_at=data.get("next_retry_at"),
            error_message=data.get("error_message"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Job":
        return cls.from_dict(json.loads(json_str))

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

class Config:
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_BASE = 2
    DEFAULT_DB_PATH = ".queuectl.db"

    def __init__(self, max_retries: int = None, backoff_base: int = None, db_path: str = None):
        self.max_retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        self.backoff_base = backoff_base if backoff_base is not None else self.DEFAULT_BACKOFF_BASE
        self.db_path = db_path if db_path is not None else self.DEFAULT_DB_PATH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "backoff_base": self.backoff_base,
            "db_path": self.db_path,
        }
